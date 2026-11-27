import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cineforge.visual_timeline import build_visual_timeline


class VisualTimelineTests(unittest.TestCase):
    def test_calculates_overlapping_transition_timing(self):
        scenes = [SimpleNamespace(title="Opening", seconds=5), SimpleNamespace(title="Reveal", seconds=7)]
        result = build_visual_timeline(scenes, transition_seconds=1.5)
        self.assertEqual(result["scenes"][0]["start"], 0)
        self.assertEqual(result["scenes"][1]["start"], 3.5)
        self.assertEqual(result["total_seconds"], 10.5)

    def test_reports_existing_and_missing_clips(self):
        scenes = [SimpleNamespace(title="One", seconds=4), SimpleNamespace(title="Two", seconds=4)]
        with tempfile.TemporaryDirectory() as directory:
            clip = Path(directory) / "scene.mp4"
            clip.write_bytes(b"video")
            result = build_visual_timeline(scenes, [clip, Path(directory) / "missing.mp4"])
        self.assertEqual(result["ready_count"], 1)
        self.assertEqual(result["missing_count"], 1)
        self.assertEqual([row["status"] for row in result["scenes"]], ["ready", "missing"])

    def test_rejects_non_positive_duration(self):
        with self.assertRaises(ValueError):
            build_visual_timeline([SimpleNamespace(title="Bad", seconds=0)])

    def test_rejects_negative_transition(self):
        with self.assertRaises(ValueError):
            build_visual_timeline([], transition_seconds=-0.1)


if __name__ == "__main__":
    unittest.main()
