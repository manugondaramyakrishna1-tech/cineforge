"""Input validation tests for the final video assembly entry point."""
import tempfile
import unittest
from pathlib import Path

from cineforge.assembly import assemble


class AssemblyInputTests(unittest.TestCase):
    def test_missing_clip_is_reported_instead_of_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing_scene.mp4"
            with self.assertRaisesRegex(FileNotFoundError, "missing_scene.mp4"):
                assemble([missing], Path(tmp) / "out.mp4")

    def test_trim_range_count_must_match_clip_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "scene.mp4"
            clip.touch()
            with self.assertRaisesRegex(ValueError, "Trim ranges must match"):
                assemble([clip], Path(tmp) / "out.mp4", trim_ranges=[(0, 1), (0, 1)])

    def test_empty_clip_list_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "No video clips"):
                assemble([], Path(tmp) / "out.mp4")


if __name__ == "__main__":
    unittest.main()
