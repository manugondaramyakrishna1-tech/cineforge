"""Rule-based scene direction with shot diversity, pacing and continuity cues."""
from dataclasses import dataclass, asdict
CAMERA_PRESETS = {
 "Establishing wide": "wide establishing shot, slow crane or gentle aerial drift",
 "Tracking shot": "smooth tracking camera following subject movement",
 "Dolly-in": "slow cinematic dolly-in, gradual emotional emphasis",
 "Orbit": "controlled camera orbit around subject",
 "Close-up": "cinematic close-up, shallow depth of field, subtle camera movement",
 "Low angle": "low-angle cinematic composition, slow upward camera movement",
 "Overhead": "overhead view, slow reveal",
 "Static composition": "locked camera, carefully composed frame"}
LOOK_PRESETS = {
 "Natural film": "natural cinematic color, balanced contrast, subtle film grain",
 "Warm cinema": "warm highlights, golden cinematic color grade, soft contrast",
 "Cool cinema": "cool blue-gray palette, controlled contrast, atmospheric lighting",
 "Dreamlike": "soft luminous palette, gentle bloom, dreamy cinematic color grade",
 "High contrast": "rich contrast, deep shadows, dramatic cinematic lighting"}
SHOT_ARCS = ["Establishing wide","Tracking shot","Close-up","Dolly-in","Orbit","Low angle","Overhead","Static composition"]
BEATS = [
 ("Opening wide shot","Establish the setting and mood.","Introduce the world."),
 ("Subject reveal","Reveal the subject naturally.","Introduce the main subject."),
 ("Discovery","Show a meaningful action or discovery.","Move the story forward."),
 ("Closing shot","Create a memorable cinematic resolution.","Close the story."),
 ("Detail shot","Focus on a meaningful visual detail.","Add an emotional detail."),
 ("Final reveal","Reveal something visually striking.","End with a payoff.")]
@dataclass
class Scene:
 title: str
 prompt: str
 seconds: int
 narration: str
 camera: str = "Tracking shot"

def plan(prompt: str, scene_count: int=4, style: str="cinematic photorealism", character: str="the central subject"):
 count=max(2,min(6,int(scene_count))); scenes=[]
 continuity=f"Character continuity: {character}. Maintain wardrobe, features, props and environment consistency."
 for i in range(count):
  title,beat,narration=BEATS[i%len(BEATS)]
  camera=SHOT_ARCS[i%len(SHOT_ARCS)]
  pacing=["measured opening","steady progression","brief dramatic emphasis","gentle resolution"][i%4]
  full=(f"{prompt}. Scene {i+1}: {beat} {continuity} {style}. "
        f"Shot design: {CAMERA_PRESETS[camera]}. Pacing: {pacing}. "
        "Keep screen direction and character identity consistent with previous scenes; "
        "use a distinct composition, purposeful camera movement, believable motion, cinematic lighting and depth. No text or watermark.")
  scenes.append(Scene(title,full,5,narration,camera))
 return scenes

def analyze_scene_plan(scenes):
 issues=[]; cameras=[s.camera for s in scenes]; titles=[s.title for s in scenes]
 if len(scenes)<2: issues.append("Plan needs at least two scenes.")
 if len(set(cameras))<min(2,len(cameras)): issues.append("Shot diversity is limited.")
 if any(not s.prompt.strip() for s in scenes): issues.append("A scene prompt is empty.")
 if any(int(s.seconds)<=0 for s in scenes): issues.append("Scene duration must be positive.")
 return {"scene_count":len(scenes),"camera_sequence":cameras,
         "distinct_camera_count":len(set(cameras)),
         "shot_diversity":len(set(cameras))/max(1,len(cameras)),
         "titles":titles,"issues":issues,
         "status":"REVIEW_REQUIRED" if issues else "READY"}
def export_script(prompt,style,character,scenes):
 return {"project":"CineForge AI","story_prompt":prompt,"visual_style":style,"character_continuity":character,"scenes":[asdict(s) for s in scenes]}
