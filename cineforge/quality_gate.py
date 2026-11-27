"""Combined pre-publish checks for video and optional audio metrics."""
def quality_gate(validation, audio_quality=None, scene_count=None, expected_scene_count=None, clip_issues=None):
    issues = list(clip_issues or [])
    validation_ok = bool(validation and validation.get("valid"))
    if not validation_ok:
        issues.append("Video validation did not pass.")
    if validation and validation.get("audio_silent"):
        issues.append("Final export audio signal is silent or nearly silent.")
    if audio_quality:
        if audio_quality.get("clipping_detected"):
            issues.append("Clipping detected in audio.")
        if audio_quality.get("mostly_silent"):
            issues.append("Audio is mostly silent or quiet.")
    scenes_ok = (scene_count is None or expected_scene_count is None or scene_count >= expected_scene_count)
    if not scenes_ok:
        issues.append(f"Scene count is incomplete ({scene_count}/{expected_scene_count}).")
    checks = {
        "video_validation": validation_ok,
        "audio_signal": bool(audio_quality and not audio_quality.get("clipping_detected") and not audio_quality.get("mostly_silent") and not (validation and validation.get("audio_silent"))),
        "scene_completeness": scenes_ok,
        "clip_warnings": not bool(clip_issues),
    }
    passed = all(checks.values())
    return {"status": "READY" if passed else "REVIEW_REQUIRED",
            "ready_to_publish": passed, "checks": checks,
            "issues": issues, "score": round(100 * sum(checks.values()) / len(checks))}
