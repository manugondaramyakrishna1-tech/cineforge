import json
from cineforge.export_report import build_report, save_report, report_markdown

def test_report_status_and_fields():
    report=build_report({"valid":True,"width":1280,"height":720,"fps":30,"duration_seconds":5,"video_frames_decoded":150,"audio_frames_decoded":160,"audio_present":True,"file_size_bytes":12345})
    assert report["status"]=="PASS"
    md=report_markdown(report)
    assert "1280 × 720" in md
    assert "Audio present: True" in md

def test_report_includes_warnings():
    report=build_report({"valid":False},warnings=["Optional soundtrack missing"])
    assert report["status"]=="FAIL"
    assert "Optional soundtrack missing" in report_markdown(report)


def test_report_includes_quality_gate_and_readiness():
    gate = {
        "status": "REVIEW_REQUIRED",
        "ready_to_publish": False,
        "score": 75,
        "issues": ["Audio is mostly silent or quiet."],
    }
    report = build_report({"valid": True}, quality_gate=gate)
    assert report["status"] == "PASS"
    assert report["publishing_status"] == "REVIEW_REQUIRED"
    assert report["ready_to_publish"] is False
    assert "Audio is mostly silent or quiet." in report["warnings"]
    md = report_markdown(report)
    assert "Publishing readiness: REVIEW_REQUIRED" in md

def test_report_without_quality_gate_is_not_publish_ready():
    report = build_report({"valid": True})
    assert report["publishing_status"] == "NOT_ASSESSED"
    assert report["ready_to_publish"] is False


def test_report_persists_as_valid_json(tmp_path):
    report=build_report({"valid":True,"width":640,"height":360})
    target=save_report(report,tmp_path/"nested"/"report.json")
    assert target.exists()
    loaded=json.loads(target.read_text(encoding="utf-8"))
    assert loaded["status"]=="PASS"
    assert loaded["validation"]["width"]==640

def test_report_markdown_handles_sparse_validation():
    md=report_markdown(build_report({"valid":False},warnings=[]))
    assert "FAIL" in md
    assert "- None" in md
