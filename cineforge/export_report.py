"""Export validation report formatting and persistence helpers."""
from pathlib import Path
import json
from datetime import datetime, timezone

def build_report(validation, *, expected=None, warnings=None):
    expected = expected or {}
    warnings = list(warnings or [])
    return {
        "status": "PASS" if validation.get("valid") else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation": dict(validation),
        "expected": dict(expected),
        "warnings": warnings,
    }

def save_report(report, path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return path

def report_markdown(report):
    v=report.get("validation",{})
    lines=["# CineForge Export Validation","",
           "**Status:** "+str(report.get("status","UNKNOWN")),"",
           "## Video","",
           f"- Resolution: {v.get('width','?')} × {v.get('height','?')}",
           f"- FPS: {v.get('fps','?')}",
           f"- Duration: {v.get('duration_seconds','?')} seconds",
           f"- Decoded video frames: {v.get('video_frames_decoded','?')}",
           f"- Decoded audio frames: {v.get('audio_frames_decoded','?')}",
           f"- Audio present: {v.get('audio_present','?')}",
           f"- File size: {v.get('file_size_bytes','?')} bytes","",
           "## Warnings",""]
    lines += ["- "+str(w) for w in report.get("warnings",[])] or ["- None"]
    return "\n".join(lines)
