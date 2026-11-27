import unittest
from types import SimpleNamespace
from cineforge.project_state import apply_project_settings, project_settings_payload, reorder_scenes_by_titles


class ProjectStateTests(unittest.TestCase):
    def test_settings_round_trip(self):
        values = {"voice_mode": "Telugu only", "fps": 30, "ignored": "x"}
        payload = {"original_prompt": "A film", "story_prompt": "Expanded", "character_continuity": "Hero",
                   "cineforge_settings": project_settings_payload(values)}
        state = {}
        apply_project_settings(state, payload)
        self.assertEqual(state["voice_mode"], "Telugu only")
        self.assertEqual(state["fps"], 30)
        self.assertEqual(state["prompt"], "A film")
        self.assertTrue(state["restore_project_pending"])

    def test_scene_order(self):
        scenes = [SimpleNamespace(title="A"), SimpleNamespace(title="B"), SimpleNamespace(title="C")]
        self.assertEqual([s.title for s in reorder_scenes_by_titles(scenes, ["C", "A"])], ["C", "A", "B"])


if __name__ == "__main__":
    unittest.main()
