"""Project workspace lifecycle and manifest helpers."""
import json
from pathlib import Path
from datetime import datetime, timezone
from .workspace import workspace_name, workspace_path

WORKSPACE_LAYOUT = ("assets", "scenes", "audio", "renders", "exports", "checkpoints", "reports")


def initialize_workspace(root, name):
    path = workspace_path(root, name)
    for folder in WORKSPACE_LAYOUT:
        (path / folder).mkdir(exist_ok=True)
    manifest_path = path / "project.json"
    if not manifest_path.exists():
        manifest = {"name": str(name).strip() or "project", "slug": workspace_name(name),
                    "created_at": datetime.now(timezone.utc).isoformat(), "schema_version": 1}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def read_manifest(path):
    manifest_path = Path(path) / "project.json"
    if not manifest_path.exists():
        return None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported or invalid project manifest.")
    return data
