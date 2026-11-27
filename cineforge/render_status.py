"""Per-scene render status registry helpers."""
import json
from pathlib import Path


def read_registry(path):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_registry(path, registry):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    tmp.replace(p)


def set_scene_status(path, scene_number, status, detail=""):
    allowed = {"queued", "rendering", "complete", "failed", "preview"}
    if status not in allowed:
        raise ValueError("Unsupported scene status")
    registry = read_registry(path)
    registry[str(int(scene_number))] = {"status": status, "detail": str(detail)[:500]}
    write_registry(path, registry)
    return registry
