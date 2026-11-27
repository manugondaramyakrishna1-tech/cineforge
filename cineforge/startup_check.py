"""Basic startup checks for CineForge dependencies and workspace folders."""
from pathlib import Path
import importlib


def run_checks():
    report = {}
    for module in ("streamlit", "av", "numpy"):
        try:
            importlib.import_module(module)
            report[module] = "available"
        except Exception as exc:
            report[module] = f"missing/unavailable: {exc.__class__.__name__}"
    for folder in (Path("outputs"), Path("projects")):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            report[str(folder)] = "ready"
        except OSError as exc:
            report[str(folder)] = f"not writable: {exc.__class__.__name__}"
    return report
