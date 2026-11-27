"""Helpers for managing replacement scene clips and manifest metadata."""
import json
from pathlib import Path


def replacement_manifest(path):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def record_replacement(path, scene_number, clip_path):
    clip = Path(clip_path)
    if not clip.exists() or not clip.is_file():
        raise ValueError("Replacement clip must be an existing file")
    manifest = replacement_manifest(path)
    manifest[str(int(scene_number))] = str(clip)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(target)
    return manifest


def clip_for_scene(path, scene_number, default_clip=None):
    clip = replacement_manifest(path).get(str(int(scene_number)))
    if clip and Path(clip).is_file():
        return Path(clip)
    return default_clip


def apply_replacements(original_clips, path):
    manifest = replacement_manifest(path)
    resolved = list(original_clips)
    for key, value in manifest.items():
        try:
            index = int(key) - 1
        except (ValueError, TypeError):
            continue
        replacement = Path(value)
        if 0 <= index < len(resolved) and replacement.is_file():
            resolved[index] = replacement
    return resolved
