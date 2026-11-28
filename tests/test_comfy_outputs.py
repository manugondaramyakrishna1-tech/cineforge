"""ComfyUI output handling regression tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cineforge.comfy import ComfyUI


class ComfyOutputTests(unittest.TestCase):
    def test_rejects_output_paths(self):
        for name in ("../escape.mp4", "nested/clip.mp4", r"nested\\clip.mp4"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    ComfyUI._safe_output_name(name)

    def test_rejects_unknown_media_extension(self):
        with self.assertRaisesRegex(ValueError, "Unsupported generated video format"):
            ComfyUI._safe_output_name("clip.txt")

    def test_accepts_supported_video_extensions(self):
        self.assertEqual(ComfyUI._safe_output_name("clip.mp4"), "clip.mp4")
        self.assertEqual(ComfyUI._safe_output_name("preview.gif"), "preview.gif")

    def test_download_uses_unique_safe_names(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b"video-data"

        outputs = {"node": {"videos": [
            {"filename": "scene.mp4", "subfolder": "", "type": "output"},
            {"filename": "scene.mp4", "subfolder": "", "type": "output"},
        ]}}
        with tempfile.TemporaryDirectory() as tmp:
            client = ComfyUI("http://localhost:8188")
            with patch("urllib.request.urlopen", return_value=Response()):
                saved = client.download_videos(outputs, Path(tmp))
            self.assertEqual([p.name for p in saved], ["scene.mp4", "scene_2.mp4"])
            self.assertTrue(all(p.read_bytes() == b"video-data" for p in saved))


if __name__ == "__main__":
    unittest.main()
