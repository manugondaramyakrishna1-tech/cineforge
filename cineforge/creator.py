"""Creator-friendly duration and delivery presets."""
DURATIONS = {
 "Quick Short (30 sec)": 30,
 "Short (60 sec)": 60,
 "Mini film (2 min)": 120,
 "Story film (3 min)": 180,
 "Custom storyboard": None
}
def target_scene_count(total_seconds, per_scene=5):
    return max(2,min(6,round(total_seconds/max(1,per_scene))))
