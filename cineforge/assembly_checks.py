"""Assembly validation and metadata helpers."""
from pathlib import Path
import numpy as np


def validate_clips(clips):
    checked = []
    issues = []
    for i, item in enumerate(clips, 1):
        p = Path(item)
        if not p.exists() or not p.is_file():
            issues.append(f"Clip {i} missing: {p}")
            continue
        try:
            import av
            with av.open(str(p)) as container:
                stream = next((s for s in container.streams if s.type == "video"), None)
                if stream is None:
                    issues.append(f"Clip {i} has no video stream: {p.name}")
                else:
                    checked.append(p)
        except Exception as exc:
            issues.append(f"Clip {i} could not be inspected: {p.name} ({exc})")
    return checked, issues


def assembly_summary(clips, fps, fade_seconds, audio_path=None):
    return {"clip_count": len(clips), "fps": int(fps),
            "fade_seconds": float(fade_seconds),
            "audio_enabled": bool(audio_path),
            "clip_names": [Path(p).name for p in clips]}


def validate_final_video(path, expected_width, expected_height, expected_fps,
                         expected_duration=None, require_audio=True):
    """Inspect and decode a completed MP4; raise ValueError for invalid exports."""
    import av

    path = Path(path)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Final MP4 is missing or empty.")

    with av.open(str(path)) as container:
        video = next((stream for stream in container.streams if stream.type == "video"), None)
        audio = next((stream for stream in container.streams if stream.type == "audio"), None)
        if video is None:
            raise ValueError("Final MP4 has no video stream.")
        if require_audio and audio is None:
            raise ValueError("Final MP4 has no audio stream.")

        if int(video.width) != int(expected_width) or int(video.height) != int(expected_height):
            raise ValueError(
                f"Export resolution mismatch: expected {expected_width}x{expected_height}, "
                f"got {video.width}x{video.height}."
            )

        actual_fps = float(video.average_rate or video.base_rate or 0)
        if actual_fps <= 0 or abs(actual_fps - float(expected_fps)) > 0.5:
            raise ValueError(
                f"Export FPS mismatch: expected {expected_fps}, got {actual_fps:.3g}."
            )

        duration = None
        if video.duration is not None and video.time_base is not None:
            duration = float(video.duration * video.time_base)
        elif container.duration is not None:
            duration = float(container.duration / av.time_base)
        if duration is None or duration <= 0:
            raise ValueError("Final MP4 has no readable duration.")
        if expected_duration is not None:
            tolerance = max(0.5, 2.0 / max(float(expected_fps), 1.0))
            if abs(duration - float(expected_duration)) > tolerance:
                raise ValueError(
                    f"Export duration mismatch: expected about {expected_duration:.2f}s, "
                    f"got {duration:.2f}s."
                )

        video_frames = 0
        audio_frames = 0
        audio_duration = None
        if audio is not None and audio.duration is not None and audio.time_base is not None:\n            audio_duration = float(audio.duration * audio.time_base)\n        audio_square_sum = 0.0
        audio_sample_count = 0
        for packet in container.demux():
            if packet.dts is None:
                continue
            for decoded in packet.decode():
                if packet.stream.type == "video":
                    video_frames += 1
                elif packet.stream.type == "audio":
                    audio_frames += 1
                    samples = decoded.to_ndarray()
                    if samples.size:
                        if np.issubdtype(samples.dtype, np.integer):
                            scale = float(max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max))
                            samples = samples.astype(np.float64) / scale
                        else:
                            samples = samples.astype(np.float64)
                        audio_square_sum += float(np.sum(samples * samples))
                        audio_sample_count += int(samples.size)
        if video_frames == 0:
            raise ValueError("Final MP4 contains no decodable video frames.")
        if require_audio and audio_frames == 0:
            raise ValueError("Final MP4 audio stream contains no decodable audio frames.")
        audio_rms = (audio_square_sum / audio_sample_count) ** 0.5 if audio_sample_count else 0.0
        audio_silent = audio_sample_count > 0 and audio_rms < 1e-5\n        audio_duration_delta = (abs(audio_duration - duration) if audio_duration is not None else None)\n        duration_tolerance = max(0.5, 2.0 / max(float(expected_fps), 1.0))\n        if require_audio and audio_duration_delta is not None and audio_duration_delta > duration_tolerance:\n            raise ValueError(\n                f"Audio/video duration mismatch: audio {audio_duration:.2f}s, video {duration:.2f}s."\n            )

    return {
        "valid": True,
        "audio_rms": round(audio_rms, 8),
        "audio_silent": audio_silent,\n        "audio_duration_seconds": round(audio_duration, 3) if audio_duration is not None else None,\n        "audio_video_duration_delta_seconds": round(audio_duration_delta, 3) if audio_duration_delta is not None else None,
        "file_size_bytes": path.stat().st_size,
        "width": int(expected_width),
        "height": int(expected_height),
        "fps": round(actual_fps, 3),
        "duration_seconds": round(duration, 3),
        "video_frames_decoded": video_frames,
        "audio_frames_decoded": audio_frames,
        "audio_present": audio is not None,
    }
