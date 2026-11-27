import tempfile
import unittest
from pathlib import Path
from cineforge.asset_manager import scan_assets, summarize_assets


class AssetManagerTests(unittest.TestCase):
    def test_scan_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"scene1.png").write_bytes(b"image")
            (root/"audio.wav").write_bytes(b"audio")
            (root/"notes.txt").write_text("ignore")
            items=scan_assets(root)
            self.assertEqual(len(items),2)
            self.assertEqual(summarize_assets(items)["by_type"], {"image":1,"audio":1})

    def test_missing_folder(self):
        self.assertEqual(scan_assets("/path/that/does/not/exist"), [])

    def test_nested_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"scene1").mkdir()
            (root/"scene1"/"clip.mp4").write_bytes(b"clip")
            self.assertEqual(scan_assets(root)[0]["type"], "video")


if __name__ == "__main__":
    unittest.main()
