"""Integration tests for CineForge's free-GPU bridge API.

Run: pip install -r requirements.txt -r requirements-dev.txt
     pytest -q
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api_module(tmp_path, monkeypatch):
    monkeypatch.setenv("CINEFORGE_FREE_GPU_BRIDGE_TOKEN", "test-bridge-secret")
    import api
    api = importlib.reload(api)
    api.DB_PATH = tmp_path / "jobs.sqlite3"
    api.OUTPUT_DIR = tmp_path / "outputs"
    api.OUTPUT_DIR.mkdir()
    api.jobs.clear()
    api.submitted.clear()
    api.init_db()
    api.ensure_columns()
    api.reload_jobs()
    api.gpu_report = lambda: {"cuda_available": False, "runtime_hint": "GPU unavailable"}
    api.backend_status = lambda: {"endpoint_configured": False}
    return api


@pytest.fixture()
def client(api_module):
    with TestClient(api_module.app) as test_client:
        yield test_client


def auth(token="test-bridge-secret"):
    return {"Authorization": f"Bearer {token}"}


def make_job(client):
    response = client.post("/jobs", json={"prompt": "A calm cinematic ocean at sunrise"})
    assert response.status_code == 202, response.text
    return response.json()["job_id"]


def test_bridge_requires_valid_token(client):
    response = client.post("/bridge/heartbeat", headers=auth("wrong"))
    assert response.status_code == 401


def test_heartbeat_marks_worker_online(client):
    response = client.post("/bridge/heartbeat", headers=auth())
    assert response.status_code == 200
    status = client.get("/bridge/status").json()
    assert status["enabled"] is True
    assert status["worker_online"] is True


def test_worker_claims_queued_job(client):
    job_id = make_job(client)
    response = client.post("/bridge/claim", headers=auth())
    assert response.status_code == 200
    assert response.json()["job"]["job_id"] == job_id
    assert client.get(f"/jobs/{job_id}").json()["status"] == "running"
    assert client.post("/bridge/claim", headers=auth()).json()["job"] is None


def test_worker_can_upload_mp4_and_complete_job(client):
    job_id = make_job(client)
    client.post("/bridge/claim", headers=auth())
    # Minimal MP4-like test fixture: ftyp box marker and sufficient payload length.
    mp4 = b"\x00\x00\x00\x18ftypisom" + (b"\x00" * 160)
    response = client.post(
        f"/bridge/result/{job_id}",
        headers=auth(),
        files={"video": ("test.mp4", mp4, "video/mp4")},
    )
    assert response.status_code == 200, response.text
    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert client.get(job["download_url"]).status_code == 200


def test_bridge_rejects_non_mp4_payload(client):
    job_id = make_job(client)
    client.post("/bridge/claim", headers=auth())
    response = client.post(
        f"/bridge/result/{job_id}",
        headers=auth(),
        files={"video": ("fake.mp4", b"not-an-mp4-" + b"x" * 160, "video/mp4")},
    )
    assert response.status_code == 400
    assert client.get(f"/jobs/{job_id}").json()["status"] == "running"


def test_worker_failure_is_recorded(client):
    job_id = make_job(client)
    client.post("/bridge/claim", headers=auth())
    response = client.post(
        f"/bridge/fail/{job_id}", headers=auth(), json={"error": "CUDA out of memory"}
    )
    assert response.status_code == 200
    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "CUDA out of memory" in job["error"]
