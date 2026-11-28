import unittest
from types import SimpleNamespace
from cineforge.video_engine import provider_status, prepare_scene_prompts, validate_workflow


class VideoEngineTests(unittest.TestCase):
    def test_status_without_provider(self):
        status = provider_status("", None)
        self.assertFalse(status.ready)
        self.assertIn("not configured", status.message.lower())

    def test_status_with_url_and_workflow(self):
        status = provider_status("http://localhost:8188", {"nodes": []})
        self.assertTrue(status.ready)

    def test_invalid_workflow(self):
        self.assertTrue(validate_workflow(None))
        self.assertTrue(validate_workflow({}))
        self.assertEqual(validate_workflow({"nodes": []}), [])

    def test_prompt_payload_is_bounded_and_formatted(self):
        scene = SimpleNamespace(title="Scene", prompt="A landscape", camera="wide", seconds=3)
        payload = prepare_scene_prompts([scene], {"wide": "wide-angle shot"}, {"cinematic": "film grain"}, "cinematic", "Vertical", 1080, 1920, "noise")
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["seconds"], 3)
        self.assertIn("wide-angle shot", payload[0]["prompt"])
        self.assertEqual(payload[0]["negative_prompt"], "noise")

    def test_scene_duration_clamped(self):
        scene = SimpleNamespace(title="Scene", prompt="A landscape", camera="wide", seconds=100)
        payload = prepare_scene_prompts([scene], {}, {}, "style", "preset", 640, 480)
        self.assertEqual(payload[0]["seconds"], 20)


if __name__ == "__main__":
    unittest.main()
