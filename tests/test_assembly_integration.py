"""Small real-container tests for PyAV video assembly."""
import tempfile
import unittest
from pathlib import Path

import av
import numpy as np

from cineforge.assembly import _assemble_video_only, mux_audio


def make_clip(path, value, frames=8, fps=8):
    with av.open(str(path), "w") as container:
        stream = container.add_stream("libx264", rate=fps)
        stream.width = 32
        stream.height = 32
        stream.pix_fmt = "yuv420p"
        for index in range(frames):
            pixels = np.full((32, 32, 3), value, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(pixels, format="rgb24")
            frame.pts = index
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def make_audio(path, seconds=2, rate=8000):
    samples = np.zeros((1, seconds * rate), dtype=np.float32)
    pcm = (samples * 32767).astype(np.int16)\n    frame = av.AudioFrame.from_ndarray(pcm, format="s16", layout="mono")
    frame.sample_rate = rate
    with av.open(str(path), "w") as container:
        stream = container.add_stream("pcm_s16le", rate=rate)
        stream.layout = "mono"
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


class AssemblyIntegrationTests(unittest.TestCase):
    def test_crossfade_export_has_expected_frame_count_and_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second, output = (Path(tmp) / name for name in ("a.mp4", "b.mp4", "out.mp4"))
            make_clip(first, 20)
            make_clip(second, 220)
            _assemble_video_only([first, second], output, fps=8, transition_seconds=0.5)
            with av.open(str(output)) as result:
                video = next(s for s in result.streams if s.type == "video")
                frames = list(result.decode(video))
                self.assertEqual(len(frames), 12)
                self.assertAlmostEqual(len(frames) / 8, 1.5, places=2)

    def test_transition_must_be_shorter_than_each_clip(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second, output = (Path(tmp) / name for name in ("a.mp4", "b.mp4", "out.mp4"))
            make_clip(first, 20, frames=8, fps=8)
            make_clip(second, 220, frames=8, fps=8)
            with self.assertRaisesRegex(ValueError, "shorter than every clip"):
                _assemble_video_only([first, second], output, fps=8, transition_seconds=1.0)

    def test_mux_audio_produces_video_and_audio_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip, audio, video_only, output = (Path(tmp) / name for name in ("clip.mp4", "audio.wav", "video.mp4", "final.mp4"))
            make_clip(clip, 100)
            make_audio(audio, seconds=1)
            _assemble_video_only([clip], video_only, fps=8)
            mux_audio(video_only, audio, output)
            with av.open(str(output)) as result:
                self.assertIsNotNone(next((s for s in result.streams if s.type == "video"), None))
                self.assertIsNotNone(next((s for s in result.streams if s.type == "audio"), None))


if __name__ == "__main__":
    unittest.main()
