"""Unit tests for CineForge clip and export validation helpers."""
import tempfile
import unittest
from pathlib import Path

from cineforge.assembly_checks import assembly_summary, validate_clips


class AssemblyCheckTests(unittest.TestCase):
    def test_missing_clip_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.mp4"
            checked, issues = validate_clips([missing])
            self.assertEqual(checked, [])
            self.assertEqual(len(issues), 1)
            self.assertIn("missing", issues[0].lower())

    def test_clip_with_no_decodable_frames_is_rejected(self):
        from unittest.mock import MagicMock, patch
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "blank.mp4"
            clip.touch()
            container = MagicMock()
            container.streams = [MagicMock(type="video")]
            container.decode.return_value = iter(())
            with patch("av.open", return_value=container):
                clips, issues = validate_clips([clip])
            self.assertEqual(clips, [])
            self.assertEqual(len(issues), 1)
            self.assertIn("no decodable video frames", issues[0])

    def test_summary_reports_clip_and_audio_settings(self):
        summary = assembly_summary(
            [Path("scene_01.mp4"), Path("scene_02.mp4")],
            fps=30,
            fade_seconds=0.5,
            audio_path=Path("mix.wav"),
        )
        self.assertEqual(summary["clip_count"], 2)
        self.assertEqual(summary["fps"], 30)
        self.assertTrue(summary["audio_enabled"])
        self.assertEqual(summary["clip_names"], ["scene_01.mp4", "scene_02.mp4"])

    def test_summary_without_audio(self):
        summary = assembly_summary([], fps=24, fade_seconds=0)
        self.assertFalse(summary["audio_enabled"])
        self.assertEqual(summary["clip_count"], 0)


    def test_final_video_validator_rejects_missing_file(self):
        from cineforge.assembly_checks import validate_final_video

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.mp4"
            with self.assertRaisesRegex(ValueError, "missing or empty"):
                validate_final_video(missing, 1280, 720, 30)

    def test_final_video_validator_rejects_empty_file(self):
        from cineforge.assembly_checks import validate_final_video

        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.mp4"
            empty.touch()
            with self.assertRaisesRegex(ValueError, "missing or empty"):
                validate_final_video(empty, 1280, 720, 30)


    def test_invalid_clip_prevents_partial_compacted_timeline(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "scene_1.mp4"
            missing = Path(tmp) / "scene_2.mp4"
            good.touch()
            with patch("av.open", side_effect=RuntimeError("invalid media")):
                clips, issues = validate_clips([good, missing])
            self.assertEqual(clips, [])
            self.assertEqual(len(issues), 2)
            self.assertIn("Clip 1 could not be inspected", issues[0])
            self.assertIn("Clip 2 missing", issues[1])


if __name__ == "__main__":
    unittest.main()
