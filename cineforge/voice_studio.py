"""Voiceover utilities for per-scene narration and voice profiles."""
from pathlib import Path

VOICE_PROFILES = {
    "Natural": {"rate": 165, "volume": 1.0},
    "Energetic": {"rate": 185, "volume": 1.0},
    "Calm cinematic": {"rate": 145, "volume": 0.95},
    "Documentary": {"rate": 155, "volume": 1.0},
}


def create_scene_voice(scene, output_dir, profile="Natural"):
    from .voice import synthesize
    settings = VOICE_PROFILES.get(profile, VOICE_PROFILES["Natural"])
    text = str(getattr(scene, "narration", "")).strip()
    if not text:
        return None
    path = Path(output_dir) / f"scene_{getattr(scene, 'number', 1)}_voice.wav"
    return synthesize(text, path, rate=settings["rate"], volume=settings["volume"])


def narration_text(scenes):
    return "\n\n".join(str(scene.narration).strip() for scene in scenes if str(scene.narration).strip())
