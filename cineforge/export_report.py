"""Export validation report formatting and persistence helpers."""
from pathlib import Path
import json
from datetime import datetime, timezone

def build_report(validation, *, expected=None, warnings=None, quality_gate=None):
    expected = expected or {}
    warnings = list(warnings or [])
    if quality_gate:
        for issue in quality_gate.get("issues", []):
            if issue not in warnings:
                warnings.append(issue)
    return {
        "status": "PASS" if validation.get("valid") else "FAIL",
        "publishing_status": (
            quality_gate.get("status", "UNKNOWN") if quality_gate
            else "NOT_ASSESSED"
        ),
        "ready_to_publish": (
            bool(quality_gate.get("ready_to_publish", False)) if quality_gate
            else False
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation": dict(validation),
        "quality_gate": dict(quality_gate) if quality_gate else None,
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
           "**Status:** "+str(report.get("status","UNKNOWN")),
           "**Publishing readiness:** "+str(report.get("publishing_status","NOT_ASSESSED")),"",
           "## Video","",
           f"- Resolution: {v.get('width','?')} × {v.get('height','?')}",
           f"- FPS: {v.get('fps','?')}",
           f"- Duration: {v.get('duration_seconds','?')} seconds",
           f"- Decoded video frames: {v.get('video_frames_decoded','?')}",
           f"- Decoded audio frames: {v.get('audio_frames_decoded','?')}",
           f"- Audio present: {v.get('audio_present','?')}",
           f"- Audio RMS: {v.get('audio_rms','?')}",
           f"- Audio silent: {v.get('audio_silent','?')}",
           f"- File size: {v.get('file_size_bytes','?')} bytes","",
           "## Warnings",""]
    lines += ["- "+str(w) for w in report.get("warnings",[])] or ["- None"]
    return "\n".join(lines)
