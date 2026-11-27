"""Persistent, bounded retry and recovery state for individual scene renders."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar
from cineforge.reliability import atomic_write_json, recover_json
T = TypeVar("T")

def _empty_state():
    return {"schema_version": 1, "scenes": {}}

class SceneRecoveryStore:
    """Track per-scene attempts and outcomes in an atomically-written JSON file."""
    def __init__(self, path):
        self.path = Path(path)
        self.state = recover_json(self.path, _empty_state())
        if not isinstance(self.state, dict) or not isinstance(self.state.get("scenes"), dict):
            self.state = _empty_state()

    def _save(self):
        atomic_write_json(self.path, self.state)

    def get_scene(self, scene_number):
        return dict(self.state["scenes"].get(str(int(scene_number)), {}))

    def record(self, scene_number, status, *, attempt=None, error=None):
        number = int(scene_number)
        if number < 1:
            raise ValueError("Scene number must be positive.")
        record = self.state["scenes"].setdefault(str(number), {"attempts": 0, "status": "pending", "history": []})
        if attempt is not None:
            record["attempts"] = max(int(record.get("attempts", 0)), int(attempt))
        record["status"] = str(status)
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        event = {"status": str(status), "at": record["updated_at"]}
        if attempt is not None:
            event["attempt"] = int(attempt)
        if error is not None:
            event["error"] = str(error)[:1000]
            record["last_error"] = str(error)[:1000]
        record.setdefault("history", []).append(event)
        record["history"] = record["history"][-20:]
        self._save()
        return dict(record)

    def run_with_retry(self, scene_number, operation: Callable[[], T], *, max_attempts=3,
                       delay_seconds=1.0, on_attempt=None):
        if not 1 <= int(max_attempts) <= 5:
            raise ValueError("max_attempts must be between 1 and 5.")
        if not 0 <= float(delay_seconds) <= 5:
            raise ValueError("delay_seconds must be between 0 and 5.")
        import time
        previous = self.get_scene(scene_number)
        first_attempt = int(previous.get("attempts", 0)) + 1
        last_error = None
        for offset in range(int(max_attempts)):
            attempt = first_attempt + offset
            self.record(scene_number, "rendering", attempt=attempt)
            if on_attempt:
                on_attempt(attempt, int(max_attempts))
            try:
                result = operation()
                self.record(scene_number, "complete", attempt=attempt)
                return result
            except Exception as exc:
                last_error = exc
                self.record(scene_number, "retrying" if offset + 1 < int(max_attempts) else "failed",
                            attempt=attempt, error=exc)
                if offset + 1 < int(max_attempts) and delay_seconds:
                    time.sleep(float(delay_seconds) * (2 ** offset))
        raise RuntimeError(f"Scene {int(scene_number)} failed after {int(max_attempts)} attempt(s): {last_error}") from last_error

    def summary(self):
        records = list(self.state["scenes"].values())
        return {"scene_count": len(records),
                "complete": sum(item.get("status") == "complete" for item in records),
                "failed": sum(item.get("status") == "failed" for item in records),
                "retrying": sum(item.get("status") == "retrying" for item in records),
                "total_attempts": sum(int(item.get("attempts", 0)) for item in records)}
