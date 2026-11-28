"""Provider-neutral prompt-to-video orchestration helpers for CineForge.

This module prepares a scene batch and checks whether the configured ComfyUI
provider is ready. Actual video synthesis still requires an installed model and
an API workflow supported by that provider.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderStatus:
    configured: bool
    workflow_loaded: bool
    ready: bool
    message: str


def provider_status(server: str, workflow: Any) -> ProviderStatus:
    configured = bool((server or "").strip())
    loaded = workflow is not None and isinstance(workflow, dict)
    ready = configured and loaded
    if ready:
        message = "Provider URL and API workflow are configured. Model availability is checked when rendering."
    elif not configured and not loaded:
        message = "AI video provider and workflow are not configured. Prompt/storyboard tools remain available."
    elif not configured:
        message = "Workflow loaded, but no provider URL is configured."
    else:
        message = "Provider URL configured, but an API workflow JSON is required."
    return ProviderStatus(configured, loaded, ready, message)


def prepare_scene_prompts(scenes, camera_presets, look_presets, style, profile_name, width, height, negative_prompt=""):
    """Return bounded, provider-ready prompt payloads; no render is started."""
    payload = []
    for index, scene in enumerate(scenes, 1):
        camera = camera_presets.get(scene.camera, scene.camera)
        prompt = (
            f"{scene.prompt.strip()} Camera direction: {camera}. "
            f"Visual style: {style}. Color look: {look_presets.get(style, '')}. "
            f"Target format: {profile_name}, {width}x{height}."
        )
        payload.append({
            "scene_index": index,
            "title": str(scene.title)[:160],
            "seconds": max(2, min(20, int(scene.seconds))),
            "prompt": prompt[:12000],
            "negative_prompt": str(negative_prompt)[:4000],
        })
    return payload


def validate_workflow(workflow):
    if not isinstance(workflow, dict):
        return ["Workflow must be a JSON object."]
    if not workflow:
        return ["Workflow JSON is empty."]
    return []


def build_render_batch(scenes, camera_presets, look_presets, style, profile_name, width, height, negative_prompt="", max_scenes=6):
    """Build a bounded batch payload for the provider adapter; never submits jobs."""
    bounded = list(scenes)[:max_scenes]
    if not bounded:
        raise ValueError("At least one scene is required for a render batch.")
    return {
        "provider": "comfyui",
        "format": {"name": str(profile_name)[:80], "width": int(width), "height": int(height)},
        "style": str(style)[:200],
        "scene_count": len(bounded),
        "scenes": prepare_scene_prompts(bounded, camera_presets, look_presets, style, profile_name, width, height, negative_prompt),
    }


def validate_provider_inputs(server, workflow):
    """Return human-readable issues for render setup without making network calls."""
    issues = []
    url = (server or "").strip()
    if not url:
        issues.append("Provider URL is missing.")
    elif not (url.startswith("http://") or url.startswith("https://")):
        issues.append("Provider URL must begin with http:// or https://.")
    issues.extend(validate_workflow(workflow))
    if isinstance(workflow, dict) and workflow:
        nodes = workflow.get("nodes")
        if nodes is not None and not isinstance(nodes, (dict, list)):
            issues.append("Workflow 'nodes' must be an object or list when present.")
        if isinstance(nodes, list) and len(nodes) == 0:
            issues.append("Workflow has an empty nodes list; check that you exported an API workflow.")
    return issues
