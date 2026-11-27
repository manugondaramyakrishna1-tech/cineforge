"""Basic decoded-audio quality metrics (peak, RMS, clipping and silence)."""
from pathlib import Path
import numpy as np


def analyze_audio(path, silence_threshold=0.001, clipping_threshold=0.999):
    """Decode audio via PyAV and report signal metrics; not a LUFS certification."""
    import av
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Audio file is missing or empty.")
    chunks = []
    with av.open(str(path)) as container:
        streams = [s for s in container.streams if s.type == "audio"]
        if not streams:
            raise ValueError("File has no audio stream.")
        for frame in container.decode(audio=0):
            samples = frame.to_ndarray()
            if samples.size == 0:
                continue
            if np.issubdtype(samples.dtype, np.integer):
                scale = float(max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max))
                samples = samples.astype(np.float64) / scale
            else:
                samples = samples.astype(np.float64)
            chunks.append(samples.reshape(-1))
    if not chunks:
        raise ValueError("Audio stream has no decodable samples.")
    data = np.concatenate(chunks)
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(data * data)))
    clipped = int(np.count_nonzero(np.abs(data) >= clipping_threshold))
    quiet = int(np.count_nonzero(np.abs(data) <= silence_threshold))
    return {
        "sample_count": int(data.size),
        "peak": round(peak, 6),
        "rms": round(rms, 6),
        "clipped_sample_count": clipped,
        "clipping_detected": clipped > 0,
        "quiet_sample_ratio": round(quiet / data.size, 6),
        "mostly_silent": quiet / data.size >= 0.95,
        "thresholds": {"silence": silence_threshold, "clipping": clipping_threshold},
        "note": "Signal metrics only; no perceptual loudness (LUFS) or sync certification.",
    }
