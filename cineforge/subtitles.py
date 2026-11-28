"""Generate SRT subtitles aligned to the edited, crossfaded scene timeline."""


def _stamp(seconds):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def create_srt(scenes, transition_seconds=0.0, trim_ranges=None):
    """Create scene narration cues using the same trimmed durations as video export."""
    durations = [max(1.0, float(getattr(scene, 'seconds', 1))) for scene in scenes]
    overlap = float(transition_seconds)
    if overlap < 0 or (len(durations) > 1 and overlap >= min(durations)):
        raise ValueError('Transition duration must be non-negative and shorter than every scene.')

    ranges = list(trim_ranges or [])
    if ranges and len(ranges) != len(scenes):
        raise ValueError('Trim ranges must match the number of scenes.')

    rows = []
    cursor = 0.0
    for i, (scene, duration) in enumerate(zip(scenes, durations), 1):
        trim_start, trim_end = ranges[i - 1] if ranges else (0.0, None)
        trim_start = max(0.0, float(trim_start))
        effective_end = duration if trim_end is None else min(duration, max(trim_start, float(trim_end)))
        effective_duration = max(0.0, effective_end - trim_start)
        text = getattr(scene, 'narration', '').strip()
        if text and effective_duration > 0:
            rows.extend([
                str(i),
                f'{_stamp(cursor)} --> {_stamp(cursor + effective_duration)}',
                text,
                '',
            ])
        cursor += effective_duration - overlap if i < len(scenes) else effective_duration
    return '\n'.join(rows)
