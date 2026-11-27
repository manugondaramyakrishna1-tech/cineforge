"""Safe, pure helpers for scene preview data."""


def preview_rows(scenes):
    rows = []
    offset = 0
    for index, scene in enumerate(scenes, 1):
        seconds = max(0, int(scene.seconds))
        rows.append({
            "number": index,
            "title": str(scene.title),
            "start": offset,
            "end": offset + seconds,
            "seconds": seconds,
            "camera": str(scene.camera),
            "prompt": str(scene.prompt),
            "narration": str(scene.narration),
        })
        offset += seconds
    return rows


def to_csv(rows):
    import csv
    import io
    buffer = io.StringIO()
    fields = ["number", "title", "start", "end", "seconds", "camera", "prompt", "narration"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
