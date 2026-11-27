"""Export preset definitions and resolution helpers."""
PRESETS = {
    "Vertical Shorts (1080x1920)": {"width":1080,"height":1920,"fps":30,"format":"mp4"},
    "Vertical Shorts (720x1280)": {"width":720,"height":1280,"fps":30,"format":"mp4"},
    "Landscape HD (1920x1080)": {"width":1920,"height":1080,"fps":30,"format":"mp4"},
    "Landscape 720p (1280x720)": {"width":1280,"height":720,"fps":30,"format":"mp4"},
    "Square (1080x1080)": {"width":1080,"height":1080,"fps":30,"format":"mp4"},
}
def get_preset(name):
    if name not in PRESETS: raise ValueError("Unknown export preset")
    return dict(PRESETS[name])
