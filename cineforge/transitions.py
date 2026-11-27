"""Frame-level transition helpers for CineForge's PyAV renderer."""
from collections import deque
from itertools import chain, islice
import numpy as np


def _validate_pair(outgoing, incoming):
    a = np.asarray(outgoing)
    b = np.asarray(incoming)
    if a.shape != b.shape or a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("Crossfade frames must have matching (height, width, 3) RGB shapes.")
    if a.dtype != np.uint8 or b.dtype != np.uint8:
        raise ValueError("Crossfade frames must use uint8 pixels.")
    return a, b


def crossfade_frames(outgoing, incoming):
    """Blend matching RGB frames halfway for a soft scene boundary."""
    a, b = _validate_pair(outgoing, incoming)
    return (a.astype(np.float32) * 0.5 + b.astype(np.float32) * 0.5).round().clip(0, 255).astype(np.uint8)


def crossfade_sequence(outgoing_frames, incoming_frames):
    """Create a gradual outgoing-to-incoming blend across equal-length frame lists."""
    outgoing, incoming = list(outgoing_frames), list(incoming_frames)
    if not outgoing or len(outgoing) != len(incoming):
        raise ValueError("Crossfade sequences must be non-empty and have equal lengths.")
    result = []
    count = len(outgoing)
    for index, (a, b) in enumerate(zip(outgoing, incoming)):
        a, b = _validate_pair(a, b)
        weight = (index + 1) / count
        result.append((a.astype(np.float32) * (1.0 - weight) + b.astype(np.float32) * weight).round().clip(0, 255).astype(np.uint8))
    return result


def crossfade_clip_streams(frame_streams, transition_frames):
    """Yield clip frames with bounded-memory overlaps; each stream yields uint8 RGB frames.

    At each boundary, the outgoing tail is blended with the incoming head. At most
    approximately two transition windows are buffered, independent of clip length.
    """
    streams = [iter(stream) for stream in frame_streams]
    window = int(transition_frames)
    if window < 0:
        raise ValueError("Transition frame count cannot be negative.")
    if not streams:
        return
    if window == 0:
        for stream in streams:
            yield from stream
        return

    current = streams[0]
    tail = deque()
    for frame in current:
        tail.append(frame)
        if len(tail) > window:
            yield tail.popleft()

    for next_stream in streams[1:]:
        head = list(islice(next_stream, window))
        overlap = min(len(tail), len(head))
        if overlap:
            for frame in list(tail)[:-overlap]:
                yield frame
            blended = crossfade_sequence(list(tail)[-overlap:], head[:overlap])
            yield from blended
        else:
            yield from tail
        tail.clear()
        # Preserve unblended incoming head frames as the beginning of the next clip.
        current = chain(head[overlap:], next_stream)
        for frame in current:
            tail.append(frame)
            if len(tail) > window:
                yield tail.popleft()

    yield from tail


def transition_timeline(scene_durations, transition_seconds=0.0):
    """Return scene start offsets and total runtime after overlapping transitions."""
    durations = [float(value) for value in scene_durations]
    if not durations or any(value <= 0 for value in durations):
        raise ValueError("Scene durations must be a non-empty list of positive numbers.")
    overlap = float(transition_seconds)
    if overlap < 0:
        raise ValueError("Transition duration cannot be negative.")
    if len(durations) > 1 and overlap >= min(durations):
        raise ValueError("Transition duration must be shorter than every scene.")
    starts, cursor = [], 0.0
    for index, duration in enumerate(durations):
        starts.append(cursor)
        cursor += duration
        if index < len(durations) - 1:
            cursor -= overlap
    return {"scene_starts": starts, "total_duration": cursor, "transition_seconds": overlap}
