"""Project-scoped asset inventory and organizer."""
from pathlib import Path

ASSET_TYPES = {".mp4": "video", ".mov": "video", ".webm": "video",
               ".wav": "audio", ".mp3": "audio", ".m4a": "audio",
               ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
               ".json": "project", ".srt": "subtitle"}


def scan_assets(root):
    root = Path(root)
    items = []
    if not root.exists():
        return items
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        kind = ASSET_TYPES.get(path.suffix.lower())
        if kind:
            items.append({"path": str(path), "name": path.name, "type": kind,
                         "size_bytes": path.stat().st_size,
                         "folder": str(path.parent.relative_to(root))})
    return items


def summarize_assets(items):
    summary = {"total": len(items), "by_type": {}}
    for item in items:
        summary["by_type"][item["type"]] = summary["by_type"].get(item["type"], 0) + 1
    return summary
