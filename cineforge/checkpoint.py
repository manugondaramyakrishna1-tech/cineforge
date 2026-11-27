"""Persist render progress so a generation can be inspected and resumed."""
import json
from pathlib import Path
from datetime import datetime, timezone

def save_checkpoint(path, project_prompt, scenes, completed, clips, failed=None):
    data={"project_prompt":project_prompt,"updated_at":datetime.now(timezone.utc).isoformat(),
          "completed_scene_indices":list(completed),"clip_paths":[str(p) for p in clips],
          "failed_scene_indices":list(failed or []),
          "scenes":[{"title":s.title,"prompt":s.prompt,"seconds":s.seconds,"narration":s.narration,"camera":s.camera} for s in scenes]}
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2),encoding="utf-8")
    return path
def load_checkpoint(path):
    path=Path(path)
    if not path.exists(): raise FileNotFoundError(path)
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("completed_scene_indices"),list): raise ValueError("Invalid checkpoint")
    return data
