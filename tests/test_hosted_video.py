import unittest

from cineforge.hosted_video import ReplicateVideo, replace_placeholders, validate_workflow


class HostedVideoTests(unittest.TestCase):
    def test_valid_model_template(self):
        template = {"model": "example/video-model", "input": {"prompt": "__PROMPT__"}}
        self.assertEqual(validate_workflow(template), [])

    def test_rejects_template_without_prompt(self):
        template = {"model": "example/video-model", "input": {"seed": 42}}
        self.assertTrue(any("__PROMPT__" in issue for issue in validate_workflow(template)))

    def test_typed_placeholder_replacement(self):
        template = {"input": {"prompt": "__PROMPT__", "duration": "__DURATION__"}}
        result = replace_placeholders(template, {"__PROMPT__": "A cinematic scene", "__DURATION__": 6})
        self.assertEqual(result["input"]["prompt"], "A cinematic scene")
        self.assertEqual(result["input"]["duration"], 6)
        self.assertIsInstance(result["input"]["duration"], int)

    def test_collects_video_urls_from_nested_output(self):
        output = {"output": [{"url": "https://replicate.delivery/example.mp4"}]}
        self.assertEqual(
            ReplicateVideo._output_urls(output),
            ["https://replicate.delivery/example.mp4"],
        )


if __name__ == "__main__":
    unittest.main()
