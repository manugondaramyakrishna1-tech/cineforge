"""PyAV video assembly with per-clip fades and WAV muxing; no ffmpeg CLI."""
from pathlib import Path
import tempfile
import av
import numpy as np

def apply_color_grade(rgb, preset='none'):
    """Apply a deterministic RGB look to a uint8 frame without external executables."""
    frame = np.asarray(rgb)
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected an RGB frame with shape (height, width, 3).")
    if preset == 'none':
        return frame.copy()
    work = frame.astype(np.float32)
    if preset == 'cinematic':
        work = (work - 128.0) * 1.10 + 128.0
        work[:, :, 0] *= 1.04
        work[:, :, 2] *= 0.94
    elif preset == 'warm':
        work[:, :, 0] *= 1.08
        work[:, :, 2] *= 0.90
    elif preset == 'cool':
        work[:, :, 0] *= 0.92
        work[:, :, 2] *= 1.08
    else:
        raise ValueError(f"Unknown color grade: {preset}")
    return work.clip(0, 255).astype(np.uint8)


def _iter_clip_frames(path, width, height, fps, fade_seconds, color_grade, trim_start=0.0, trim_end=None):
    """Decode one clip onto the output FPS grid and yield standardized RGB frames."""
    with av.open(str(path)) as src:
        video = next((s for s in src.streams if s.type == 'video'), None)
        if video is None:
            return
        source_rate = video.average_rate or video.base_rate
        duration_seconds = None
        if video.duration and video.time_base:
            duration_seconds = float(video.duration * video.time_base)
        elif video.frames and source_rate:
            duration_seconds = float(video.frames / source_rate)
        trim_start = max(0.0, float(trim_start))
        effective_end = duration_seconds if trim_end is None else min(duration_seconds, max(trim_start, float(trim_end)))
        segment_duration = max(0.0, effective_end - trim_start) if duration_seconds is not None else 0.0
        target_frames = max(0, round(segment_duration * fps)) if segment_duration else 0
        fade_frames = min(max(0, int(fade_seconds * fps)), target_frames // 2) if target_frames else 0
        first_timestamp = None
        next_output_frame = 0
        previous_rgb = None

        def prepare(rgb, frame_index):
            factor = 1.0
            if fade_frames:
                if frame_index < fade_frames:
                    factor = min(factor, (frame_index + 1) / fade_frames)
                remaining = target_frames - frame_index
                if 0 < remaining <= fade_frames:
                    factor = min(factor, remaining / fade_frames)
            if factor < 0.999:
                rgb = (rgb.astype(np.float32) * factor).clip(0, 255).astype(np.uint8)
            return rgb

        for local_index, frame in enumerate(src.decode(video)):
            if frame.pts is not None and frame.time_base is not None:
                timestamp = float(frame.pts * frame.time_base)
            elif source_rate:
                timestamp = local_index / float(source_rate)
            else:
                timestamp = local_index / float(fps)
            if first_timestamp is None:
                first_timestamp = timestamp
            relative_timestamp = timestamp - first_timestamp
            if relative_timestamp < trim_start:
                continue
            if trim_end is not None and relative_timestamp > float(trim_end):
                break
            target_index = max(0, round((relative_timestamp - trim_start) * fps))
            if target_index < next_output_frame:
                continue
            while previous_rgb is not None and next_output_frame < target_index:
                yield prepare(previous_rgb, next_output_frame)
                next_output_frame += 1
            rgb = frame.reformat(width=width, height=height, format='rgb24').to_ndarray()
            rgb = apply_color_grade(rgb, color_grade)
            if target_index == next_output_frame:
                yield prepare(rgb, next_output_frame)
                next_output_frame += 1
            previous_rgb = rgb
        if previous_rgb is not None and target_frames:
            while next_output_frame < target_frames:
                yield prepare(previous_rgb, next_output_frame)
                next_output_frame += 1


def _assemble_video_only(clips, output: Path, fps: int, fade_seconds: float = 0.0, target_width=None, target_height=None, color_grade='none', transition_seconds: float = 0.0, trim_ranges=None):
    from cineforge.transitions import crossfade_clip_streams

    output.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(clips[0])) as first:
        first_video = next((s for s in first.streams if s.type == 'video'), None)
        if first_video is None:
            raise RuntimeError("First clip has no video stream.")
        width = int(target_width or first_video.width)
        height = int(target_height or first_video.height)
    if width < 2 or height < 2 or width % 2 or height % 2:
        raise ValueError("H.264 yuv420p output dimensions must be positive even numbers.")
    transition_seconds = float(transition_seconds)
    if transition_seconds < 0:
        raise ValueError("Transition duration cannot be negative.")
    transition_frames = round(transition_seconds * fps)
    if transition_frames:
        clip_frame_counts = []
        for clip_path in clips:
            with av.open(str(clip_path)) as source:
                video = next((item for item in source.streams if item.type == 'video'), None)
                if video is None:
                    raise RuntimeError(f"Clip has no video stream: {clip_path}")
                duration = None
                if video.duration is not None and video.time_base is not None:
                    duration = float(video.duration * video.time_base)
                elif video.frames and (video.average_rate or video.base_rate):
                    duration = float(video.frames / (video.average_rate or video.base_rate))
                if duration is None or duration <= 0:
                    raise ValueError(f"Unable to determine clip duration for transition validation: {clip_path}")
                clip_frame_counts.append(round(duration * fps))
        if len(clip_frame_counts) > 1 and transition_frames >= min(clip_frame_counts):
            raise ValueError("Transition duration must be shorter than every clip.")

    ranges = list(trim_ranges or [])
    if ranges and len(ranges) != len(clips):
        raise ValueError("Trim ranges must match the number of video clips.")
    streams = []
    for clip_index, path in enumerate(clips):
        trim_start, trim_end = ranges[clip_index] if ranges else (0.0, None)
        streams.append(
            _iter_clip_frames(
                path, width, height, fps, fade_seconds, color_grade,
                trim_start=trim_start, trim_end=trim_end,
            )
        )
    container = av.open(str(output), mode='w')
    stream = container.add_stream('libx264', rate=fps)
    stream.width, stream.height = width, height
    stream.pix_fmt = 'yuv420p'
    stream.options = {'preset':'medium','crf':'23'}
    index = 0
    try:
        for rgb in crossfade_clip_streams(streams, transition_frames):
            frame = av.VideoFrame.from_ndarray(rgb, format='rgb24')
            frame.pts = index
            frame.time_base = stream.time_base
            index += 1
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    if not index:
        output.unlink(missing_ok=True)
        raise RuntimeError('No frames decoded from clips.')
    return output

def mux_audio(video_path, audio_path, output_path):
    """Mux AAC audio and constrain its sample count to the video duration."""
    from fractions import Fraction

    video_path, audio_path, output_path = map(Path, (video_path, audio_path, output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(video_path)) as vin, av.open(str(audio_path)) as ain, av.open(str(output_path), 'w') as out:
        vsrc = next((stream for stream in vin.streams if stream.type == 'video'), None)
        asrc = next((stream for stream in ain.streams if stream.type == 'audio'), None)
        if vsrc is None or asrc is None:
            raise ValueError('Mux requires video and audio streams.')

        video_duration = None
        if vsrc.duration is not None and vsrc.time_base is not None:
            video_duration = float(vsrc.duration * vsrc.time_base)
        elif vin.duration is not None:
            video_duration = float(vin.duration / av.time_base)
        if video_duration is None or video_duration <= 0:
            raise ValueError('Unable to determine final video duration; cannot synchronize audio.')

        vout = out.add_stream_from_template(vsrc)
        audio_rate = int(asrc.rate or 44100)
        aout = out.add_stream('aac', rate=audio_rate)
        aout.layout = 'mono'
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=audio_rate)
        target_samples = round(video_duration * audio_rate)
        written_samples = 0

        def write_audio(samples):
            nonlocal written_samples
            if samples.size == 0 or written_samples >= target_samples:
                return
            remaining = target_samples - written_samples
            samples = samples[:, :remaining]
            if samples.shape[1] == 0:
                return
            frame = av.AudioFrame.from_ndarray(samples.astype(np.float32, copy=False), format='fltp', layout='mono')
            frame.sample_rate = audio_rate
            frame.pts = written_samples
            frame.time_base = Fraction(1, audio_rate)
            written_samples += samples.shape[1]
            for encoded in aout.encode(frame):
                out.mux(encoded)

        # Copy the assembled video stream without changing its timestamps.
        for packet in vin.demux(vsrc):
            if packet.dts is None:
                continue
            for decoded in packet.decode():
                for encoded in vout.encode(decoded):
                    out.mux(encoded)
        for encoded in vout.encode():
            out.mux(encoded)

        # Resample narration/music, trimming any samples beyond video duration.
        for packet in ain.demux(asrc):
            if packet.dts is None:
                continue
            for decoded in packet.decode():
                for frame in resampler.resample(decoded):
                    write_audio(frame.to_ndarray())
        for frame in resampler.resample(None):
            write_audio(frame.to_ndarray())

        # Pad shorter audio with silence so the soundtrack reaches video end.
        silence_chunk = np.zeros((1, 4096), dtype=np.float32)
        while written_samples < target_samples:
            write_audio(silence_chunk)
        for encoded in aout.encode():
            out.mux(encoded)
    return output_path

def assemble(clips, output: Path, fps: int = 24, audio_path=None, fade_seconds: float = 0.0, target_width=None, target_height=None, color_grade='none', transition_seconds: float = 0.0, trim_ranges=None):
    clips = [Path(p) for p in clips if Path(p).exists()]
    if not clips: raise ValueError('No existing video clips provided.')
    output = Path(output)
    if audio_path is None:
        return _assemble_video_only(clips, output, fps, fade_seconds, target_width, target_height, color_grade, transition_seconds, trim_ranges)
    with tempfile.TemporaryDirectory(prefix='cineforge_') as tmp:
        temp_video = Path(tmp) / 'video_only.mp4'
        _assemble_video_only(clips, temp_video, fps, fade_seconds, target_width, target_height, color_grade, transition_seconds, trim_ranges)
        return mux_audio(temp_video, Path(audio_path), output)
