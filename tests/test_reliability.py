import json
import tempfile
import unittest
from pathlib import Path

from cineforge.reliability import atomic_write_json, recover_json, retry_call


class ReliabilityTests(unittest.TestCase):
    def test_atomic_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            atomic_write_json(path, {"status": "ok"})
            self.assertEqual(json.loads(path.read_text()), {"status": "ok"})

    def test_recover_invalid_json_returns_default(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            path.write_text("not-json")
            self.assertEqual(recover_json(path, {"safe": True}), {"safe": True})

    def test_retry_eventually_succeeds(self):
        count = {"n": 0}
        def operation():
            count["n"] += 1
            if count["n"] < 2:
                raise OSError("temporary")
            return "ok"
        self.assertEqual(retry_call(operation, attempts=2, delay_seconds=0), "ok")


import ast
import unittest
from pathlib import Path

from cineforge.timeline import move_item, validate_timeline
from cineforge.export_presets import PRESETS, get_preset
from cineforge.sound_studio import mix_settings


class CoreTests(unittest.TestCase):
    def test_timeline_reordering(self):
        self.assertEqual(move_item(["a", "b", "c"], 1, -1), ["b", "a", "c"])

    def test_timeline_boundary_move_is_safe(self):
        self.assertEqual(move_item(["a", "b"], 0, -1), ["a", "b"])

    def test_timeline_rejects_invalid_duration(self):
        with self.assertRaises(ValueError):
            validate_timeline([{"seconds": 0}])

    def test_timeline_duration_sum(self):
        self.assertEqual(validate_timeline([{"seconds": 2}, {"seconds": 3.5}]), 5.5)

    def test_export_presets_are_positive_dimensions(self):
        for preset in PRESETS.values():
            self.assertGreater(preset["width"], 0)
            self.assertGreater(preset["height"], 0)
            self.assertGreater(preset["fps"], 0)

    def test_unknown_export_preset_rejected(self):
        with self.assertRaises(ValueError):
            get_preset("not a preset")

    def test_sound_settings_clamp(self):
        result = mix_settings(2, -1, 20)
        self.assertEqual(result, {"narration_volume": 1.0, "music_volume": 0.0, "fade_seconds": 10.0})

    def test_python_source_syntax(self):
        root = Path(__file__).resolve().parents[1]
        sources = [root / "app.py"] + list((root / "cineforge").glob("*.py"))
        for source in sources:
            with self.subTest(file=source.name):
                ast.parse(source.read_text(encoding="utf-8"), filename=str(source))


\nif __name__ == "__main__":
    unittest.main()
