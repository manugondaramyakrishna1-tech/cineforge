"""Regression tests for assembly frame grading and parameter validation."""
import unittest
import numpy as np

from cineforge.assembly import apply_color_grade, _assemble_video_only


class AssemblyFrameTests(unittest.TestCase):
    def test_none_grade_returns_independent_copy(self):
        frame = np.full((3, 4, 3), 128, dtype=np.uint8)
        result = apply_color_grade(frame, "none")
        np.testing.assert_array_equal(result, frame)
        self.assertFalse(np.shares_memory(result, frame))

    def test_known_grade_preserves_shape_and_uint8(self):
        frame = np.full((4, 4, 3), 128, dtype=np.uint8)
        for preset in ("cinematic", "warm", "cool"):
            result = apply_color_grade(frame, preset)
            self.assertEqual(result.shape, frame.shape)
            self.assertEqual(result.dtype, np.uint8)
            self.assertTrue(np.all(result <= 255))

    def test_invalid_frame_shape_rejected(self):
        with self.assertRaisesRegex(ValueError, "RGB frame"):
            apply_color_grade(np.zeros((2, 2), dtype=np.uint8))

    def test_unknown_grade_rejected(self):
        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "Unknown color grade"):
            apply_color_grade(frame, "invalid")

    def test_invalid_output_dimensions_rejected(self):
        with self.assertRaisesRegex(ValueError, "even numbers"):
            _assemble_video_only(["not-opened"], __import__("pathlib").Path("unused.mp4"),
                                 fps=24, target_width=3, target_height=3)


if __name__ == "__main__":
    unittest.main()
