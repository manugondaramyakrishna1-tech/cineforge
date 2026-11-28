"""Single-scene rendering helper for the in-process local CogVideoX engine.

This is an adapter layer for integrating local model renders into CineForge's
existing scene pipeline. It performs no network video-generation API calls.
"""
from pathlib import Path
from typing import Any

from cineforge.local_video import LocalCogVideoX


def render_local_scene(
    prompt: str,
    output_dir: str | Path,
    *,
    negative_prompt: str = "",
    frames: int = 49,
    steps: int = 30,
    seed: int | None = None,
    fps: int = 8,
    status_box: Any = None,
    model_id: str | None = None,
) -> list[Path]:
    """Generate and encode one scene, returning verified MP4 file paths."""
    if not str(prompt).strip():
        raise ValueError("Scene prompt must not be empty.")

    engine = LocalCogVideoX(model_id=model_id, output_fps=fps)
    request = {
        "prompt": str(prompt).strip(),
        "negative_prompt": str(negative_prompt).strip(),
        "num_frames": max(9, min(49, int(frames))),
        "steps": max(1, min(50, int(steps))),
        "seed": seed,
    }
    job_id = engine.submit(request)
    engine.wait_for_outputs(job_id, status_box)
    videos = engine.download_videos(request, Path(output_dir))

    verified = [Path(path) for path in videos if Path(path).is_file() and Path(path).stat().st_size > 0]
    if not verified:
        raise RuntimeError("Local renderer did not produce a non-empty video file.")
    return verified
