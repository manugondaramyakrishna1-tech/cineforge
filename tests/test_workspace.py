import tempfile
import unittest
from pathlib import Path
from cineforge.workspace import workspace_name, workspace_path, scoped_path


class WorkspaceTests(unittest.TestCase):
    def test_sanitize_name(self):
        self.assertEqual(workspace_name("../bad name"), "bad_name")

    def test_workspace_created_and_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=workspace_path(tmp, "Movie One")
            self.assertTrue(path.is_dir())
            scoped=scoped_path(tmp, "Movie One", "clips", "scene.mp4")
            self.assertEqual(scoped.parent.name, "clips")

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                scoped_path(tmp, "project", "..", "escape.txt")


if __name__ == "__main__":
    unittest.main()
