"""Tests for the combined cinematic quality gate."""
import unittest
from cineforge.quality_gate import quality_gate

class GateTests(unittest.TestCase):
    def test_clean_inputs_ready(self):
        v={"valid":True,"audio_silent":False}
        a={"clipping_detected":False,"mostly_silent":False}
        r=quality_gate(v,a,scene_count=3,expected_scene_count=3)
        self.assertTrue(r["ready_to_publish"])
        self.assertEqual(r["score"],100)

    def test_silent_audio_requires_review(self):
        v={"valid":True,"audio_silent":True}
        a={"clipping_detected":False,"mostly_silent":True}
        r=quality_gate(v,a,scene_count=2,expected_scene_count=2)
        self.assertFalse(r["ready_to_publish"])
        self.assertIn("Final export audio signal is silent or nearly silent.",r["issues"])

    def test_scene_count_shortfall(self):
        v={"valid":True,"audio_silent":False}
        a={"clipping_detected":False,"mostly_silent":False}
        r=quality_gate(v,a,scene_count=2,expected_scene_count=4)
        self.assertFalse(r["checks"]["scene_completeness"])

    def test_clip_warnings_require_review(self):
        v={"valid":True,"audio_silent":False}
        a={"clipping_detected":False,"mostly_silent":False}
        r=quality_gate(v,a,scene_count=2,expected_scene_count=2,clip_issues=["clip warning"])
        self.assertFalse(r["ready_to_publish"])

if __name__=="__main__":
    unittest.main()
