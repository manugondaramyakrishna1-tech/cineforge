"""CineForge release readiness checklist and audit helpers."""
from pathlib import Path
import json

REQUIRED_SOURCE_FILES = [\n    "cineforge/assembly.py",\n    "cineforge/assembly_checks.py",\n    "cineforge/audio_mix.py",\n    "cineforge/transitions.py",\n    "cineforge/export_report.py",\n]\n\nREQUIRED_TEST_FILES = [
    "tests/test_transitions.py",
    "tests/test_audio_sync_regressions.py",
    "tests/test_pyav_export_integration.py",
    "tests/test_assembly_frame_regressions.py",
    "tests/test_export_report.py",
]

def audit_repo(root="."):
    root=Path(root)
    missing=[p for p in REQUIRED_TEST_FILES if not (root/p).exists()]
    return {"status":"PASS" if not missing else "FAIL",
            "required_test_files":REQUIRED_TEST_FILES,
            "missing_files":missing,
            "actions_triggered":False}

def save_audit(audit,path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(audit,indent=2),encoding="utf-8")
    return path
