"""Sound mixing helpers for optional soundtrack and narration tracks."""
from pathlib import Path


def validate_audio_tracks(narration=None, music=None):
    issues = []
    tracks = []
    for label, candidate in (("narration", narration), ("music", music)):
        if candidate is None:
            continue
        path = Path(candidate)
        if not path.exists() or not path.is_file():
            issues.append(f"{label} file is missing")
            continue
        try:
            import av
            with av.open(str(path)) as container:
                if not any(s.type == "audio" for s in container.streams):
                    issues.append(f"{label} has no audio stream")
                    continue
            tracks.append(path)
        except Exception as exc:
            issues.append(f"{label} could not be inspected: {exc}")
    return tracks, issues


def mix_settings(narration_volume=1.0, music_volume=0.25, fade_seconds=1.5):
    return {"narration_volume": max(0.0, min(1.0, float(narration_volume))),
            "music_volume": max(0.0, min(1.0, float(music_volume))),
            "fade_seconds": max(0.0, min(10.0, float(fade_seconds)))}
