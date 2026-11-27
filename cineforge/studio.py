"""Scene studio display helpers."""
from pathlib import Path


def scene_status(output_dir, scene_number):
    root = Path(output_dir)
    folder = root / f"final_scene_{scene_number}"
    if not folder.exists():
        return {"status": "Not rendered", "clips": []}
    clips = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".mp4", ".webm", ".mov"})
    return {"status": "Rendered" if clips else "Output folder empty", "clips": clips}


def scene_cards(scenes, output_dir="outputs"):
    cards = []
    for i, scene in enumerate(scenes, 1):
        info = scene_status(output_dir, i)
        cards.append({"number": i, "title": scene.title, "duration": scene.seconds,
                      "prompt": scene.prompt, "camera": scene.camera,
                      "narration": scene.narration, **info})
    return cards
