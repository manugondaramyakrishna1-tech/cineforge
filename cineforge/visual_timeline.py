"""Visual timeline data model for CineForge scene previews."""
from pathlib import Path


def build_visual_timeline(scenes, clip_paths=None, transition_seconds=0.0):
    """Return ordered scene blocks with timing, transition and media readiness."""
    if transition_seconds < 0:
        raise ValueError("transition_seconds cannot be negative")
    clips = list(clip_paths or [])
    rows = []
    cursor = 0.0
    for index, scene in enumerate(scenes, 1):
        seconds = float(scene.seconds)
        if seconds <= 0:
            raise ValueError(f"Scene {index} duration must be positive")
        clip = Path(clips[index - 1]) if index <= len(clips) and clips[index - 1] else None
        exists = bool(clip and clip.is_file())
        rows.append({
            "scene": index,
            "title": str(scene.title),
            "start": round(cursor, 3),
            "end": round(cursor + seconds, 3),
            "duration": seconds,
            "transition_after": float(transition_seconds) if index < len(scenes) else 0.0,
            "clip_path": str(clip) if clip else None,
            "clip_ready": exists,
            "status": "ready" if exists else "missing",
        })
        cursor += seconds - (float(transition_seconds) if index < len(scenes) else 0.0)
    return {
        "scenes": rows,
        "scene_count": len(rows),
        "transition_seconds": float(transition_seconds),
        "total_seconds": round(max(0.0, cursor), 3),
        "ready_count": sum(row["clip_ready"] for row in rows),
        "missing_count": sum(not row["clip_ready"] for row in rows),
    }
