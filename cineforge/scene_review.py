"""Scene-review utilities to flag storyboard issues before rendering."""
from dataclasses import dataclass

@dataclass
class ReviewItem:
    scene_index: int
    severity: str
    message: str


def review_scenes(scenes):
    """Return deterministic editorial checks for a sequence of scene objects."""
    findings = []
    if not scenes:
        return [ReviewItem(0, "error", "Storyboard has no scenes.")]
    for index, scene in enumerate(scenes, 1):
        title = str(getattr(scene, "title", "") or "").strip()
        prompt = str(getattr(scene, "prompt", "") or "").strip()
        narration = str(getattr(scene, "narration", "") or "").strip()
        seconds = int(getattr(scene, "seconds", 0) or 0)
        if not title:
            findings.append(ReviewItem(index, "warning", "Scene title is blank."))
        if len(prompt) < 40:
            findings.append(ReviewItem(index, "warning", "Visual prompt is very short; add subject, setting, action and lighting."))
        if not narration:
            findings.append(ReviewItem(index, "warning", "Narration is empty."))
        elif len(narration.split()) > max(18, seconds * 3):
            findings.append(ReviewItem(index, "warning", "Narration may be too dense for this scene duration."))
        if seconds < 2 or seconds > 20:
            findings.append(ReviewItem(index, "warning", "Scene duration is outside the suggested 2–20 second range."))
        if index > 1 and prompt.lower() == str(getattr(scenes[index-2], "prompt", "") or "").strip().lower():
            findings.append(ReviewItem(index, "warning", "Prompt duplicates the previous scene."))
    if not findings:
        findings.append(ReviewItem(0, "ok", "No basic storyboard issues detected."))
    return findings


def report_text(scenes):
    return "\\n".join(f"{item.severity.upper()} · {('Scene '+str(item.scene_index)) if item.scene_index else 'Storyboard'}: {item.message}" for item in review_scenes(scenes))
