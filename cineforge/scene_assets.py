"""Per-scene asset manifest with replacement history and active clip selection."""
import json
from pathlib import Path
from datetime import datetime, timezone


def _read(path):
    target = Path(path)
    if not target.exists():
        return {"schema_version": 1, "scenes": {}}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema_version": 1, "scenes": {}}
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), dict):
        return {"schema_version": 1, "scenes": {}}
    return data


def _write(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(target)


def register_scene_asset(manifest_path, scene_number, asset_path, asset_type="video", activate=False):
    asset = Path(asset_path).resolve()
    if not asset.is_file():
        raise ValueError("Scene asset must be an existing file.")
    if asset_type not in {"image", "video", "audio"}:
        raise ValueError("Unsupported scene asset type.")
    number = int(scene_number)
    if number < 1:
        raise ValueError("Scene number must be positive.")
    data = _read(manifest_path)
    scene = data["scenes"].setdefault(str(number), {"assets": [], "active_video": None})
    record = {"path": str(asset), "type": asset_type,
              "registered_at": datetime.now(timezone.utc).isoformat()}
    scene["assets"].append(record)
    if asset_type == "video" and (activate or not scene.get("active_video")):
        scene["active_video"] = str(asset)
    _write(manifest_path, data)
    return record


def set_active_scene_video(manifest_path, scene_number, asset_path):
    asset = Path(asset_path).resolve()
    if not asset.is_file():
        raise ValueError("Selected scene video does not exist.")
    data = _read(manifest_path)
    scene = data["scenes"].get(str(int(scene_number)))
    if not scene or not any(item.get("path") == str(asset) and item.get("type") == "video" for item in scene.get("assets", [])):
        raise ValueError("Video is not registered for this scene.")
    scene["active_video"] = str(asset)
    _write(manifest_path, data)
    return asset


def resolve_scene_videos(manifest_path, original_clips):
    data = _read(manifest_path)
    resolved = list(original_clips)
    for key, scene in data["scenes"].items():
        try:
            index = int(key) - 1
        except (TypeError, ValueError):
            continue
        active = Path(scene.get("active_video") or "")
        if 0 <= index < len(resolved) and active.is_file():
            resolved[index] = active
    return resolved


def scene_asset_inventory(manifest_path):
    data = _read(manifest_path)
    return [{"scene": int(number), **asset, "active": asset.get("type") == "video" and asset.get("path") == scene.get("active_video")}
            for number, scene in data["scenes"].items()
            for asset in scene.get("assets", [])]
