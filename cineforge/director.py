from dataclasses import dataclass, asdict

CAMERA_PRESETS = {
 "Establishing wide": "wide establishing shot, slow crane or gentle aerial drift",
 "Tracking shot": "smooth tracking camera following subject movement",
 "Dolly-in": "slow cinematic dolly-in, gradual emotional emphasis",
 "Orbit": "controlled camera orbit around subject",
 "Close-up": "cinematic close-up, shallow depth of field, subtle camera movement",
 "Low angle": "low-angle cinematic composition, slow upward camera movement",
 "Overhead": "overhead view, slow reveal",
 "Static composition": "locked camera, carefully composed frame"
}
LOOK_PRESETS = {
 "Natural film": "natural cinematic color, balanced contrast, subtle film grain",
 "Warm cinema": "warm highlights, golden cinematic color grade, soft contrast",
 "Cool cinema": "cool blue-gray palette, controlled contrast, atmospheric lighting",
 "Dreamlike": "soft luminous palette, gentle bloom, dreamy cinematic color grade",
 "High contrast": "rich contrast, deep shadows, dramatic cinematic lighting"
}
@dataclass
class Scene:
 title: str
 prompt: str
 seconds: int
 narration: str
 camera: str = "Tracking shot"

def plan(prompt: str, scene_count: int=4, style: str="cinematic photorealism", character: str="the central subject"):
 beats=[("Opening wide shot","Establish the setting and mood.","Introduce the world."),("Subject reveal","Reveal the subject naturally.","Introduce the main subject."),("Discovery","Show a meaningful action or discovery.","Move the story forward."),("Closing shot","Create a memorable cinematic resolution.","Close the story."),("Detail shot","Focus on a meaningful visual detail.","Add an emotional detail."),("Final reveal","Reveal something visually striking.","End with a payoff.")]
 count=max(2,min(6,int(scene_count))); scenes=[]
 continuity=f"Character continuity: {character}. Maintain wardrobe, features and location consistency."
 for i in range(count):
  title,beat,narration=beats[i%len(beats)]
  camera=list(CAMERA_PRESETS)[i%len(CAMERA_PRESETS)]
  full=f"{prompt}. Scene {i+1}: {beat} {continuity} {style}. {CAMERA_PRESETS[camera]}. Natural believable motion, cinematic lighting, rich depth, film-quality detail. No text or watermark."
  scenes.append(Scene(title,full,5,narration,camera))
 return scenes
def export_script(prompt,style,character,scenes):
 return {"project":"CineForge AI","story_prompt":prompt,"visual_style":style,"character_continuity":character,"scenes":[asdict(s) for s in scenes]}
