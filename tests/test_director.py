"""Scene director and plan-analysis tests."""
import unittest
from cineforge.director import plan, analyze_scene_plan
class DirectorTests(unittest.TestCase):
 def test_scene_plan_uses_varied_camera_choices(self):
  scenes=plan("A city at night",4)
  self.assertGreaterEqual(len(set(s.camera for s in scenes)),2)
  self.assertEqual(len(scenes),4)
 def test_plan_analysis_reports_diversity(self):
  result=analyze_scene_plan(plan("A journey",4))
  self.assertEqual(result["status"],"READY")
  self.assertGreater(result["shot_diversity"],0)
 def test_empty_prompt_scene_detected(self):
  scenes=plan("A story",2)
  scenes[0].prompt=""
  self.assertIn("A scene prompt is empty.",analyze_scene_plan(scenes)["issues"])
 def test_scene_count_clamped(self):
  self.assertEqual(len(plan("A story",99)),6)
if __name__=="__main__": unittest.main()
