"""Audio helpers: timeline mixing of scene narration and optional looping music."""
from pathlib import Path
import wave
import numpy as np

def _read_wav(path):
    with wave.open(str(path), 'rb') as w:
        channels, rate, width, frames = w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(frames)
    if width == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    elif width == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f'Unsupported WAV sample width: {width}')
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data, rate

def _resample(data, src_rate, target_rate):
    if src_rate == target_rate or not len(data):
        return data
    new_len = max(1, round(len(data) * target_rate / src_rate))
    old_x = np.arange(len(data), dtype=np.float64)
    new_x = np.linspace(0, len(data)-1, new_len)
    return np.interp(new_x, old_x, data).astype(np.float32)

def mix_timeline(narration_paths, durations, output_wav, soundtrack=None, music_volume=0.18, voice_volume=1.0, sample_rate=44100, fade_seconds=0.0, transition_seconds=0.0):
    """Place narration at scene starts on a timeline shortened by visual overlaps."""
    durations = [float(value) for value in durations]
    if not durations or any(value <= 0 for value in durations):
        raise ValueError("Scene durations must be a non-empty list of positive numbers.")
    if len(narration_paths) != len(durations):
        raise ValueError("Narration tracks and scene durations must have equal lengths.")
    overlap = float(transition_seconds)
    if overlap < 0 or (len(durations) > 1 and overlap >= min(durations)):
        raise ValueError("Transition duration must be non-negative and shorter than every scene.")
    total_seconds = sum(durations) - overlap * max(0, len(durations) - 1)
    total = max(1, round(total_seconds * sample_rate))
    mix = np.zeros(total, dtype=np.float32)
    cursor = 0
    for scene_audio, seconds in zip(narration_paths, durations):
        tracks = scene_audio if isinstance(scene_audio, (list, tuple)) else [scene_audio]
        scene_cursor = cursor
        scene_end = min(total, cursor + round(seconds * sample_rate))
        for path in tracks:
            if path and Path(path).exists():
                audio, rate = _read_wav(path)
                audio = _resample(audio, rate, sample_rate) * float(voice_volume)
                if scene_cursor + len(audio) > scene_end:
                    raise ValueError(
                        f"Scene narration exceeds its {seconds:g}-second duration. "
                        "Shorten the narration or increase the scene duration."
                    )
                end = scene_cursor + len(audio)
                if end > scene_cursor:
                    mix[scene_cursor:end] += audio
                scene_cursor = end + round(0.25 * sample_rate)
        cursor += round((seconds - overlap) * sample_rate)
    if soundtrack and Path(soundtrack).exists():
        music, rate = _read_wav(soundtrack)
        music = _resample(music, rate, sample_rate)
        if len(music):
            mix += np.resize(music, total) * float(music_volume)
    fade_samples = min(max(0, int(float(fade_seconds) * sample_rate)), total // 2)
    if fade_samples:
        ramp = np.linspace(0.0, 1.0, fade_samples, endpoint=True, dtype=np.float32)
        mix[:fade_samples] *= ramp
        mix[-fade_samples:] *= ramp[::-1]
    mix = np.clip(mix, -0.98, 0.98)
    pcm = (mix * 32767).astype(np.int16)
    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        out.writeframes(pcm.tobytes())
    return output_wav
