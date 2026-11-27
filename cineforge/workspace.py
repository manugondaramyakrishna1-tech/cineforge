"""Workspace isolation helpers for project-scoped output paths."""
from pathlib import Path
import re


def workspace_name(value):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "project").strip()).strip("._-")
    return (name[:64] or "project")


def workspace_path(root, project_name):
    base = Path(root).resolve()
    target = (base / workspace_name(project_name)).resolve()
    if target == base or base not in target.parents:
        raise ValueError("Workspace path must remain inside the workspace root.")
    target.mkdir(parents=True, exist_ok=True)
    return target


def scoped_path(root, project_name, *parts):
    target = workspace_path(root, project_name)
    for part in parts:
        candidate = (target / str(part)).resolve()
        if target not in candidate.parents and candidate != target:
            raise ValueError("Asset path escapes the project workspace.")
        target = candidate
    target.parent.mkdir(parents=True, exist_ok=True)
    return target
