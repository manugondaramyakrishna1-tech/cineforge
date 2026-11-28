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


def add_scene(scenes, scene_factory, index=None):
    """Insert a new scene made by scene_factory; returns a new list."""
    updated = list(scenes)
    new_scene = scene_factory()
    if index is None:
        updated.append(new_scene)
    else:
        if index < 0 or index > len(updated):
            raise IndexError("Insertion index out of range.")
        updated.insert(index, new_scene)
    return updated


def duplicate_scene(scenes, index):
    """Duplicate one scene using dataclass replacement; return a new list."""
    if index < 0 or index >= len(scenes):
        raise IndexError("Scene index out of range.")
    updated = list(scenes)
    updated.insert(index + 1, replace(scenes[index]))
    return updated


def remove_scene(scenes, index):
    """Remove a scene; refuse to remove the final remaining scene."""
    if index < 0 or index >= len(scenes):
        raise IndexError("Scene index out of range.")
    if len(scenes) <= 1:
        raise ValueError("A storyboard must retain at least one scene.")
    updated = list(scenes)
    del updated[index]
    return updated
