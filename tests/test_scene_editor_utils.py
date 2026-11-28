import unittest
from dataclasses import dataclass
from cineforge.scene_editor_utils import add_scene, duplicate_scene, remove_scene

@dataclass
class Scene:
    title: str
    prompt: str
    seconds: int = 5
    narration: str = ""
    camera: str = "Tracking shot"

class SceneEditorHelperTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [Scene("One", "Prompt one"), Scene("Two", "Prompt two")]

    def test_duplicate_preserves_source_and_inserts_copy(self):
        result = duplicate_scene(self.scenes, 0)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[1], self.scenes[0])
        self.assertIsNot(result[1], self.scenes[0])
        self.assertEqual(len(self.scenes), 2)

    def test_remove(self):
        self.assertEqual(len(remove_scene(self.scenes, 0)), 1)

    def test_cannot_remove_last_scene(self):
        with self.assertRaises(ValueError):
            remove_scene([self.scenes[0]], 0)

    def test_add(self):
        result = add_scene(self.scenes, lambda: Scene("New", "New prompt"))
        self.assertEqual(result[-1].title, "New")
        self.assertEqual(len(self.scenes), 2)

if __name__ == "__main__":
    unittest.main()
