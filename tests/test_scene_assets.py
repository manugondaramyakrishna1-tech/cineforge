import tempfile
import unittest
from pathlib import Path
from cineforge.scene_assets import register_scene_asset, set_active_scene_video, resolve_scene_videos, scene_asset_inventory


class SceneAssetTests(unittest.TestCase):
    def test_history_and_active_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original.mp4"; original.write_bytes(b"one")
            replacement = root / "replacement.mp4"; replacement.write_bytes(b"two")
            manifest = root / "reports" / "scene_assets.json"
            register_scene_asset(manifest, 1, original, activate=True)
            register_scene_asset(manifest, 1, replacement)
            self.assertEqual(resolve_scene_videos(manifest, [original]), [original.resolve()])
            set_active_scene_video(manifest, 1, replacement)
            self.assertEqual(resolve_scene_videos(manifest, [original]), [replacement.resolve()])
            inventory = scene_asset_inventory(manifest)
            self.assertEqual(len(inventory), 2)
            self.assertEqual(sum(item["active"] for item in inventory), 1)

    def test_missing_asset_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                register_scene_asset(Path(tmp) / "assets.json", 1, Path(tmp) / "missing.mp4")


if __name__ == "__main__":
    unittest.main()
