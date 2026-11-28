"""ComfyUI polling contract tests without a live server."""
import unittest
from unittest.mock import patch

from cineforge.comfy import ComfyUI


class StatusBox:
    def __init__(self):
        self.captions = []
    def caption(self, value):
        self.captions.append(value)


class ComfyPollingTests(unittest.TestCase):
    def test_returns_outputs_only_after_success_completion(self):
        client = ComfyUI("http://localhost:8188")
        responses = iter([
            {"job-1": {"outputs": {"node": {"videos": [{"filename": "clip.mp4"}]}}, "status": {"completed": False, "status_str": "running"}}},
            {"job-1": {"outputs": {"node": {"videos": [{"filename": "clip.mp4"}]}}, "status": {"completed": True, "status_str": "success"}}},
        ])
        client._request = lambda path: __import__("json").dumps(next(responses)).encode()
        status = StatusBox()
        with patch("cineforge.comfy.time.sleep", return_value=None), patch("cineforge.comfy.time.time", side_effect=[0, 1, 2]):
            outputs = client.wait_for_outputs("job-1", status, timeout=10, poll_interval=1)
        self.assertIn("node", outputs)
        self.assertTrue(status.captions)

    def test_execution_error_is_reported(self):
        client = ComfyUI("http://localhost:8188")
        payload = {"job-2": {"status": {"completed": False, "messages": [["execution_error", {"exception_message": "bad workflow"}]]}}}
        client._request = lambda path: __import__("json").dumps(payload).encode()
        with self.assertRaisesRegex(RuntimeError, "bad workflow"):
            client.wait_for_outputs("job-2", StatusBox(), timeout=10)

    def test_missing_prompt_id_is_rejected(self):
        client = ComfyUI("http://localhost:8188")
        with self.assertRaisesRegex(ValueError, "prompt ID"):
            client.wait_for_outputs("", StatusBox())

    def test_submit_rejects_node_validation_errors(self):
        client = ComfyUI("http://localhost:8188")
        client._request = lambda path, data=None: __import__("json").dumps({"node_errors": {"7": {"errors": [{"message": "missing model"}]}}}).encode()
        with self.assertRaisesRegex(RuntimeError, "rejected the workflow"):
            client.submit({"7": {"class_type": "Sampler", "inputs": {}}})

    def test_submit_requires_prompt_id(self):
        client = ComfyUI("http://localhost:8188")
        client._request = lambda path, data=None: b'{}'
        with self.assertRaisesRegex(RuntimeError, "did not queue"):
            client.submit({"1": {"class_type": "Test", "inputs": {}}})

    def test_submit_rejects_empty_workflow(self):
        client = ComfyUI("http://localhost:8188")
        with self.assertRaisesRegex(ValueError, "non-empty"):
            client.submit({})

    def test_completed_workflow_without_video_output_fails_clearly(self):
        client = ComfyUI("http://localhost:8188")
        payload = {"job-3": {"outputs": {"node": {"images": [{"filename": "frame.png"}]}}, "status": {"completed": True, "status_str": "success"}}}
        client._request = lambda path: __import__("json").dumps(payload).encode()
        with self.assertRaisesRegex(RuntimeError, "no downloadable video output"):
            client.wait_for_outputs("job-3", StatusBox(), timeout=10)

    def test_video_output_can_be_nested_in_history(self):
        self.assertTrue(ComfyUI._contains_video_output({"node": {"gifs": [{"filename": "movie.gif"}]}})
        self.assertFalse(ComfyUI._contains_video_output({"node": {"images": [{"filename": "frame.png"}]}})

if __name__ == "__main__":
    unittest.main()
