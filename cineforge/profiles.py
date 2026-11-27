"""CineForge project presets and reusable settings."""
PRESETS = {
 "YouTube Shorts (9:16)": {"width":720,"height":1280,"fps":24,"description":"Vertical short-form"},
 "YouTube Landscape (16:9)": {"width":1280,"height":720,"fps":24,"description":"Landscape video"},
 "Square Social (1:1)": {"width":1080,"height":1080,"fps":24,"description":"Square social video"},
 "Cinematic 4K (16:9)": {"width":1920,"height":1080,"fps":24,"description":"HD cinematic production (rendered output depends on workflow)"}
}
def get_preset(name):
    return PRESETS.get(name, PRESETS["YouTube Shorts (9:16)"])
