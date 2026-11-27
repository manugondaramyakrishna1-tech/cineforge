"""Small synthetic PyAV integration tests for video assembly and audio muxing."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

try:
    import av
except ImportError:
    av = None

from cineforge.assembly import assemble
from cineforge.assembly_checks import validate_final_video


@unittest.skipIf(av is None, "PyAV is required for integration tests")
class PyAVExportIntegrationTests(unittest.TestCase):
    def _make_video(self, path, color, frames=12, fps=12):
        with av.open(str(path), "w") as container:
            stream = container.add_stream("libx264", rate=fps)
            stream.width = 64
            stream.height = 64
            stream.pix_fmt = "yuv420p"
            for index in range(frames):
                rgb = np.full((64, 64, 3), color, dtype=np.uint8)
                frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                frame.pts = index
                frame.time_base = stream.time_base
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)

    def _make_audio(self, path, seconds=1.0, rate=16000):
        import wave
        samples = np.zeros(int(seconds * rate), dtype=np.int16)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(samples.tobytes())

    def test_video_only_export_decodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            output = Path(tmp) / "assembled.mp4"
            self._make_video(source, (40, 120, 200))
            assemble([source], output, fps=12)
            result = validate_final_video(output, 64, 64, 12, require_audio=False)
            self.assertTrue(result["valid"])
            self.assertGreater(result["video_frames_decoded"], 0)
            self.assertGreater(result["file_size_bytes"], 0)

    def test_audio_mux_export_decodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            audio = Path(tmp) / "audio.wav"
            output = Path(tmp) / "final.mp4"
            self._make_video(source, (80, 100, 160))
            self._make_audio(audio, seconds=1.0)
            assemble([source], output, fps=12, audio_path=audio)
            result = validate_final_video(output, 64, 64, 12, require_audio=True)
            self.assertTrue(result["valid"])
            self.assertTrue(result["audio_present"])
            self.assertGreater(result["audio_frames_decoded"], 0)


if __name__ == "__main__":
    unittest.main()
