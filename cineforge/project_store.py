"""Persistence utilities for CineForge project files.

Uses JSON and atomic writes so a partial write doesn't corrupt the last save.
"""
import json
import os
from pathlib import Path

FORMAT_VERSION = 1


def save_project(project, path):
    if not isinstance(project, dict):
        raise TypeError("project must be a dictionary")
    payload = dict(project)
    payload.setdefault("format_version", FORMAT_VERSION)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def load_project(path):
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Project JSON root must be an object")
    if not isinstance(data.get("scenes", []), list):
        raise ValueError("Project scenes must be a list")
    return data


def list_projects(directory):
    folder = Path(directory)
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.json") if p.is_file())
