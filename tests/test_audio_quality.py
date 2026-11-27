"""Tests for audio quality signal metrics."""
import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np

try:
    import av
except ImportError:
    av = None

@unittest.skipIf(av is None, "PyAV not installed")
class AudioQualityTests(unittest.TestCase):
    def write_wav(self, path, samples, rate=8000):
        samples = np.asarray(samples, dtype=np.float32)
        pcm = np.clip(samples, -1, 1)
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
            f.writeframes((pcm * 32767).astype(np.int16).tobytes())

    def test_detects_quiet_signal(self):
        from cineforge.audio_quality import analyze_audio
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "quiet.wav"
            self.write_wav(p, np.zeros(8000))
            result = analyze_audio(p)
            self.assertTrue(result["mostly_silent"])
            self.assertFalse(result["clipping_detected"])

    def test_detects_clipping(self):
        from cineforge.audio_quality import analyze_audio
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "clip.wav"
            self.write_wav(p, np.full(8000, 1.0))
            result = analyze_audio(p)
            self.assertTrue(result["clipping_detected"])
            self.assertGreater(result["clipped_sample_count"], 0)

    def test_reports_normal_signal(self):
        from cineforge.audio_quality import analyze_audio
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "normal.wav"
            self.write_wav(p, np.full(8000, 0.2))
            result = analyze_audio(p)
            self.assertFalse(result["mostly_silent"])
            self.assertFalse(result["clipping_detected"])
            self.assertGreater(result["rms"], 0)

if __name__ == "__main__":
    unittest.main()
