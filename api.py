"""FastAPI job API for CineForge. Jobs are held in memory for this single-process demo."""
import uuid
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from model_pipeline import generate_video, MODEL_ID

app = FastAPI(title="CineForge Video API", version="1.0.0")
executor = ThreadPoolExecutor(max_workers=1)
jobs = {}
lock = threading.Lock()
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    model_id: str = MODEL_ID
    frames: int = Field(default=25, ge=17, le=49)
    steps: int = Field(default=25, ge=1, le=50)
    guidance: float = Field(default=6.0, ge=1.0, le=10.0)
    seed: int = Field(default=42, ge=0, le=9999999)

def worker(job_id, request):
    with lock:
        jobs[job_id]["status"] = "running"
    try:
        path = OUTPUT_DIR / f"{job_id}.mp4"
        generate_video(request.prompt, str(path), request.model_id,
                       request.frames, request.steps, request.guidance, request.seed)
        with lock:
            jobs[job_id].update(status="completed", output=str(path))
    except Exception as exc:
        with lock:
            jobs[job_id].update(status="failed", error=str(exc))

@app.get("/health")
def health():
    import torch
    return {"status": "ok", "cuda_available": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}

@app.post("/jobs", status_code=202)
def create_job(request: GenerateRequest):
    job_id = str(uuid.uuid4())
    with lock:
        jobs[job_id] = {"job_id": job_id, "status": "queued"}
    executor.submit(worker, job_id, request)
    return {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"}

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        result = dict(job)
    if result.get("status") == "completed":
        result["download_url"] = f"/jobs/{job_id}/video"
        result.pop("output", None)
    return result

@app.get("/jobs/{job_id}/video")
def download_video(job_id: str):
    with lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job["status"] != "completed":
            raise HTTPException(status_code=409, detail=f"Job is {job['status']}")
        path = job["output"]
    return FileResponse(path, media_type="video/mp4", filename=f"cineforge-{job_id}.mp4")
