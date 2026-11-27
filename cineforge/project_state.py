"""Helpers for restoring project settings and storyboard ordering."""
from copy import deepcopy

SETTING_KEYS = (
    "negative_prompt", "duration_choice", "scene_count", "visual_style",
    "output_profile", "music_volume", "voice_volume", "look",
    "fade_seconds", "transition_seconds", "fps", "voice_mode", "voice_profile",
    "workspace_label",
)


def project_settings_payload(values):
    return {key: values[key] for key in SETTING_KEYS if key in values}


def apply_project_settings(session_state, payload):
    settings = payload.get("cineforge_settings", {})
    if not isinstance(settings, dict):
        settings = {}
    session_state["prompt"] = str(payload.get("original_prompt", payload.get("story_prompt", "")))
    session_state["character"] = str(payload.get("character_continuity", ""))
    for key in SETTING_KEYS:
        if key in settings:
            session_state[key] = settings[key]
    session_state["expanded_prompt"] = str(payload.get("story_prompt", payload.get("original_prompt", "")))
    session_state["restored_project"] = deepcopy(payload)
    session_state["restore_project_pending"] = True
    return session_state


def reorder_scenes_by_titles(scenes, titles):
    if not isinstance(titles, list) or not titles:
        return list(scenes)
    remaining = list(scenes)
    ordered = []
    for title in titles:
        match = next((i for i, scene in enumerate(remaining) if scene.title == title), None)
        if match is not None:
            ordered.append(remaining.pop(match))
    return ordered + remaining
