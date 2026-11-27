import tempfile, unittest
from cineforge.project_workspace import initialize_workspace, read_manifest, WORKSPACE_LAYOUT

class ProjectWorkspaceTests(unittest.TestCase):
    def test_layout_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=initialize_workspace(tmp, "Film 1")
            self.assertTrue(all((p/f).is_dir() for f in WORKSPACE_LAYOUT))
            self.assertEqual(read_manifest(p)["slug"], "Film_1")
            self.assertIsNotNone(read_manifest(p))

if __name__ == "__main__":
    unittest.main()
