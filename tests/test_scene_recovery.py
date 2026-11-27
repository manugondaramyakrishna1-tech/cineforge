import tempfile
import unittest
from pathlib import Path
from cineforge.scene_recovery import SceneRecoveryStore

class SceneRecoveryTests(unittest.TestCase):
    def test_retries_transient_failure_then_completes(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SceneRecoveryStore(Path(folder) / "recovery.json")
            calls = {"count": 0}
            def operation():
                calls["count"] += 1
                if calls["count"] < 3:
                    raise OSError("temporary ComfyUI disconnect")
                return ["scene.mp4"]
            self.assertEqual(store.run_with_retry(1, operation, max_attempts=3, delay_seconds=0), ["scene.mp4"])
            self.assertEqual(calls["count"], 3)
            self.assertEqual(store.get_scene(1)["status"], "complete")
            self.assertEqual(store.get_scene(1)["attempts"], 3)

    def test_failure_persisted_after_retry_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recovery.json"
            store = SceneRecoveryStore(path)
            def fail():
                raise ValueError("bad workflow")
            with self.assertRaisesRegex(RuntimeError, "failed after 2 attempt"):
                store.run_with_retry(2, fail, max_attempts=2, delay_seconds=0)
            scene = SceneRecoveryStore(path).get_scene(2)
            self.assertEqual(scene["status"], "failed")
            self.assertEqual(scene["attempts"], 2)
            self.assertIn("bad workflow", scene["last_error"])

    def test_attempt_count_continues_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recovery.json"
            SceneRecoveryStore(path).record(3, "failed", attempt=2, error="offline")
            restored = SceneRecoveryStore(path)
            restored.run_with_retry(3, lambda: "ok", max_attempts=1, delay_seconds=0)
            self.assertEqual(restored.get_scene(3)["attempts"], 3)

    def test_invalid_retry_limits_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SceneRecoveryStore(Path(folder) / "recovery.json")
            with self.assertRaises(ValueError):
                store.run_with_retry(1, lambda: None, max_attempts=6)

    def test_summary_counts_states(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SceneRecoveryStore(Path(folder) / "recovery.json")
            store.record(1, "complete", attempt=1)
            store.record(2, "failed", attempt=2)
            self.assertEqual(store.summary(), {"scene_count": 2, "complete": 1, "failed": 1,
                                               "retrying": 0, "total_attempts": 3})

if __name__ == "__main__":
    unittest.main()
