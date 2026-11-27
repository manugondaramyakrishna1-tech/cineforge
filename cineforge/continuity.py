"""Heuristic continuity checks across scene prompts and narration."""
import re
def _tokens(text):
 return set(re.findall(r"[a-z0-9]+",str(text).lower()))
def analyze_continuity(scenes, character_description="", visual_style=""):
 issues=[]; details=[]
 shared_tokens=_tokens(character_description)
 style_tokens=_tokens(visual_style)
 for i,scene in enumerate(scenes):
  prompt=_tokens(scene.prompt); narration=_tokens(scene.narration)
  missing_character=sorted(shared_tokens-prompt) if shared_tokens else []
  missing_style=sorted(style_tokens-prompt) if style_tokens else []
  entry={"scene":i+1,"title":scene.title,"character_reference_present":not missing_character,
         "style_reference_present":not missing_style,"prompt_word_count":len(prompt),
         "narration_word_count":len(narration)}
  details.append(entry)
  if shared_tokens and missing_character:
   issues.append(f"Scene {i+1}: prompt may omit character-description terms: {', '.join(missing_character[:8])}")
  if style_tokens and missing_style:
   issues.append(f"Scene {i+1}: prompt may omit style-description terms: {', '.join(missing_style[:8])}")
  if not prompt: issues.append(f"Scene {i+1}: prompt is empty.")
 for i in range(1,len(scenes)):
  previous=_tokens(scenes[i-1].prompt); current=_tokens(scenes[i].prompt)
  overlap=len(previous & current)/max(1,len(previous|current))
  details[i]["prompt_overlap_with_previous"]=round(overlap,3)
 return {"status":"REVIEW_REQUIRED" if issues else "CHECKS_PASSED",
         "scene_count":len(scenes),"issues":issues,"details":details,
         "note":"Lexical heuristic only; it cannot verify image-level character, prop, location or style consistency."}
