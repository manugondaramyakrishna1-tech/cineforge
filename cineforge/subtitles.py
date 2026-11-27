"""Generate SRT subtitles aligned to the crossfaded scene timeline."""
def _stamp(seconds):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def create_srt(scenes, transition_seconds=0.0):
    durations = [max(1, int(getattr(scene, 'seconds', 1))) for scene in scenes]
    overlap = float(transition_seconds)
    if overlap < 0 or (len(durations) > 1 and overlap >= min(durations)):
        raise ValueError('Transition duration must be non-negative and shorter than every scene.')
    rows = []
    cursor = 0.0
    for i, (scene, duration) in enumerate(zip(scenes, durations), 1):
        text = getattr(scene, 'narration', '').strip()
        if text:
            rows.extend([str(i), f'{_stamp(cursor)} --> {_stamp(cursor + duration)}', text, ''])
        cursor += duration - overlap
    return '\n'.join(rows)
