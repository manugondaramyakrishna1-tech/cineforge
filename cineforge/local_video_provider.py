"""Compatibility facade for CineForge's local CogVideoX scene engine."""
from pathlib import Path
from cineforge.local_video import LocalCogVideoX, runtime_status


class LocalVideoProvider:
    """Provider-like facade that accepts prompt payloads, not workflow JSON."""

    def __init__(self, fps: int = 8, model_id: str | None = None):
        status = runtime_status()
        if not status.get("ready"):
            raise RuntimeError(status.get("message", "No supported accelerator detected."))
        self.engine = LocalCogVideoX(model_id=model_id, output_fps=fps)
        self._request = None

    def submit(self, payload: dict):
        if not isinstance(payload, dict):
            raise ValueError("Local render payload must be a dictionary.")
        self._request = dict(payload)
        return self.engine.submit(payload)

    def wait_for_outputs(self, job_id, status_box=None, timeout=3600):
        return self.engine.wait_for_outputs(job_id, status_box, timeout=timeout)

    def download_videos(self, prediction, folder):
        return self.engine.download_videos(prediction, Path(folder))
