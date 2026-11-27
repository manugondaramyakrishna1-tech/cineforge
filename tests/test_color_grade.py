"""Tests for deterministic CineForge color-grade presets."""
import unittest
import numpy as np

from cineforge.assembly import apply_color_grade


class ColorGradeTests(unittest.TestCase):
    def test_none_returns_identical_copy(self):
        source = np.full((2, 2, 3), 100, dtype=np.uint8)
        result = apply_color_grade(source, "none")
        np.testing.assert_array_equal(result, source)
        self.assertIsNot(result, source)

    def test_presets_preserve_shape_and_uint8(self):
        source = np.full((4, 5, 3), 120, dtype=np.uint8)
        for preset in ("cinematic", "warm", "cool"):
            with self.subTest(preset=preset):
                result = apply_color_grade(source, preset)
                self.assertEqual(result.shape, source.shape)
                self.assertEqual(result.dtype, np.uint8)
                self.assertFalse(np.array_equal(result, source))

    def test_unknown_preset_is_rejected(self):
        source = np.zeros((1, 1, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "Unknown color grade"):
            apply_color_grade(source, "neon")

    def test_non_rgb_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RGB frame"):
            apply_color_grade(np.zeros((2, 2), dtype=np.uint8), "warm")


if __name__ == "__main__":
    unittest.main()
