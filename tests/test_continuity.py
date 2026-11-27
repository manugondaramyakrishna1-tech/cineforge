import unittest
from cineforge.director import Scene
from cineforge.continuity import analyze_continuity
class ContinuityTests(unittest.TestCase):
 def test_character_terms_checked(self):
  scenes=[Scene("A","traveler green cloak",5,"hello","Wide"),Scene("B","traveler",5,"next","Close")]
  r=analyze_continuity(scenes,"traveler green cloak")
  self.assertTrue(r["details"][0]["character_reference_present"])
  self.assertFalse(r["details"][1]["character_reference_present"])
 def test_empty_prompt_flagged(self):
  r=analyze_continuity([Scene("A","",5,"","Wide")])
  self.assertIn("Scene 1: prompt is empty.",r["issues"])
 def test_style_terms_reported(self):
  r=analyze_continuity([Scene("A","fantasy traveler",5,"","Wide")],visual_style="fantasy cinematic")
  self.assertFalse(r["details"][0]["style_reference_present"])
if __name__=="__main__":unittest.main()
