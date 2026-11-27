"""Tests for subtitle timing when scenes overlap."""
import unittest
from types import SimpleNamespace
from cineforge.subtitles import create_srt


class SubtitleTimelineTests(unittest.TestCase):
    def test_second_scene_subtitle_starts_after_visual_overlap(self):
        scenes = [
            SimpleNamespace(narration="First scene", seconds=4),
            SimpleNamespace(narration="Second scene", seconds=3),
        ]
        srt = create_srt(scenes, transition_seconds=1)
        self.assertIn("00:00:03,000 --> 00:00:06,000", srt)
        self.assertIn("Second scene", srt)

    def test_invalid_transition_is_rejected(self):
        scenes = [SimpleNamespace(narration="Scene", seconds=1)]
        with self.assertRaisesRegex(ValueError, "non-negative"):
            create_srt(scenes, transition_seconds=-0.1)


if __name__ == "__main__":
    unittest.main()
