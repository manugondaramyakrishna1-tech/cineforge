"""CineForge release readiness checklist and audit helpers."""
from pathlib import Path
import json

REQUIRED_SOURCE_FILES = [
    "cineforge/assembly.py",
    "cineforge/assembly_checks.py",
    "cineforge/audio_mix.py",
    "cineforge/transitions.py",
    "cineforge/export_report.py",
]

REQUIRED_TEST_FILES = [
    "tests/test_transitions.py",
    "tests/test_audio_sync_regressions.py",
    "tests/test_pyav_export_integration.py",
    "tests/test_assembly_frame_regressions.py",
    "tests/test_export_report.py",
]

def audit_repo(root="."):
    root = Path(root)
    missing_tests = [p for p in REQUIRED_TEST_FILES if not (root / p).exists()]
    missing_sources = [p for p in REQUIRED_SOURCE_FILES if not (root / p).exists()]
    missing = missing_sources + missing_tests
    return {
        "status": "PASS" if not missing else "FAIL",
        "required_test_files": REQUIRED_TEST_FILES,
        "required_source_files": REQUIRED_SOURCE_FILES,
        "missing_test_files": missing_tests,
        "missing_source_files": missing_sources,
        "missing_files": missing,
        "actions_triggered": False,
    }

def save_audit(audit, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return path
