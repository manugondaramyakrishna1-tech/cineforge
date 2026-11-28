"""Scene editing helpers compatible with CineForge's director.Scene objects.

This module provides safe, pure helpers for editing, validating and serializing
scene sequences without depending on a video-generation provider.
"""
from dataclasses import asdict, replace


def validate_scenes(scenes):
    errors = []
    if not scenes:
        errors.append("Storyboard has no scenes.")
    for index, scene in enumerate(scenes, start=1):
        if not str(getattr(scene, "title", "") or "").strip():
            errors.append(f"Scene {index}: title is empty.")
        if not str(getattr(scene, "prompt", "") or "").strip():
            errors.append(f"Scene {index}: prompt is empty.")
        seconds = getattr(scene, "seconds", None)
        if not isinstance(seconds, int) or not 1 <= seconds <= 60:
            errors.append(f"Scene {index}: duration must be an integer from 1 to 60.")
    return errors


def scene_to_dict(scene):
    """Serialize a Scene dataclass to a JSON-compatible dictionary."""
    return asdict(scene)


def scenes_to_data(scenes):
    return [scene_to_dict(scene) for scene in scenes]


def update_scene(scenes, index, **changes):
    """Return a new scene list with one scene replaced; original list is untouched."""
    if index < 0 or index >= len(scenes):
        raise IndexError("Scene index out of range.")
    allowed = {"title", "prompt", "seconds", "narration", "camera"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError("Unsupported scene fields: " + ", ".join(sorted(unknown)))
    updated = list(scenes)
    updated[index] = replace(scenes[index], **changes)
    return updated
