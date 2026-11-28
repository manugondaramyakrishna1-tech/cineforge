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


    def test_trimmed_scene_subtitles_follow_edited_timeline(self):
        scenes = [
            SimpleNamespace(narration="First scene", seconds=4),
            SimpleNamespace(narration="Second scene", seconds=3),
        ]
        srt = create_srt(scenes, transition_seconds=0.5,
                         trim_ranges=[(1.0, 3.0), (0.5, 2.5)])
        self.assertIn("00:00:00,000 --> 00:00:02,000", srt)
        self.assertIn("00:00:01,500 --> 00:00:03,500", srt)

    def test_trim_range_count_must_match_scene_count(self):
        scenes = [SimpleNamespace(narration="Scene", seconds=2)]
        with self.assertRaisesRegex(ValueError, "match the number of scenes"):
            create_srt(scenes, trim_ranges=[(0.0, 1.0), (0.0, 1.0)])


if __name__ == "__main__":
    unittest.main()
