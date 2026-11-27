import tempfile
import unittest
from pathlib import Path
from PIL import Image
from cineforge.image_review import review_image, review_image_folder


class ImageReviewTests(unittest.TestCase):
    def test_review_valid_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.png"
            Image.new("RGB", (640, 480), (120, 130, 140)).save(path)
            report = review_image(path)
            self.assertTrue(report["valid"])
            self.assertEqual(report["width"], 640)

    def test_tiny_image_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiny.png"
            Image.new("RGB", (80, 80), (120, 120, 120)).save(path)
            self.assertTrue(review_image(path)["issues"])

    def test_invalid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.png"
            path.write_text("not an image")
            self.assertFalse(review_image(path)["valid"])

    def test_folder_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            Image.new("RGB", (320, 240), (80, 90, 100)).save(Path(tmp) / "one.jpg")
            report = review_image_folder(tmp)
            self.assertEqual(report["image_count"], 1)


if __name__ == "__main__":
    unittest.main()
