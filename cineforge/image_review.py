"""Lightweight visual review of rendered scene image files.

Checks technical image properties only; it does not claim semantic or character recognition.
"""
from pathlib import Path
from PIL import Image, ImageStat


def review_image(path, min_width=256, min_height=256):
    path = Path(path)
    result = {"path": str(path), "valid": False, "issues": []}
    try:
        with Image.open(path) as source:
            image = source.convert("RGB")
            width, height = image.size
            stats = ImageStat.Stat(image.resize((64, 64)))
            brightness = sum(stats.mean) / 3.0
            contrast = sum(stats.stddev) / 3.0
            result.update({"valid": True, "width": width, "height": height,
                           "brightness": round(brightness, 2), "contrast": round(contrast, 2)})
            if width < min_width or height < min_height:
                result["issues"].append("Image resolution is below the review threshold.")
            if brightness < 12:
                result["issues"].append("Image is extremely dark; check visibility.")
            elif brightness > 245:
                result["issues"].append("Image is extremely bright; check exposure.")
            if contrast < 8:
                result["issues"].append("Image has very low contrast.")
    except Exception as exc:
        result["issues"].append(f"Image could not be opened: {exc}")
    return result


def review_image_folder(folder):
    folder = Path(folder)
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    results = [review_image(p) for p in files]
    return {"image_count": len(results), "results": results,
            "issue_count": sum(len(item["issues"]) for item in results)}
