import unittest
from types import SimpleNamespace
from cineforge.video_engine import provider_status, prepare_scene_prompts, validate_workflow, build_render_batch, validate_provider_inputs


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

    def test_batch_builder_caps_scene_count_and_formats_output(self):\n        scenes = [SimpleNamespace(title=f"Scene {i}", prompt="landscape", camera="wide", seconds=4) for i in range(8)]\n        batch = build_render_batch(scenes, {"wide": "wide shot"}, {}, "cinematic", "Vertical", 1080, 1920, max_scenes=5)\n        self.assertEqual(batch["scene_count"], 5)\n        self.assertEqual(len(batch["scenes"]), 5)\n        self.assertEqual(batch["format"]["width"], 1080)\n\n    def test_provider_input_validation(self):\n        self.assertTrue(validate_provider_inputs("", None))\n        self.assertTrue(validate_provider_inputs("ftp://invalid", {"nodes": []}))\n        self.assertTrue(validate_provider_inputs("http://localhost:8188", {"nodes": []}))\n        self.assertEqual(validate_provider_inputs("http://localhost:8188", {"nodes": [1]}), [])\n\n    def test_scene_duration_clamped(self):
        scene = SimpleNamespace(title="Scene", prompt="A landscape", camera="wide", seconds=100)
        payload = prepare_scene_prompts([scene], {}, {}, "style", "preset", 640, 480)
        self.assertEqual(payload[0]["seconds"], 20)


if __name__ == "__main__":
    unittest.main()
