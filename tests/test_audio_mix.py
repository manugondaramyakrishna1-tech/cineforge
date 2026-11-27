"""Unit tests for CineForge timeline audio mixing."""
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from cineforge.audio_mix import mix_timeline, _read_wav


def write_wav(path, samples, rate=8000):
    pcm = (np.asarray(samples, dtype=np.float32).clip(-1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())


class AudioMixTests(unittest.TestCase):
    def test_single_scene_narration_has_expected_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "voice.wav"
            output = Path(tmp) / "mix.wav"
            write_wav(source, np.full(4000, 0.2), 8000)
            mix_timeline([source], [1.0], output, sample_rate=8000)
            audio, rate = _read_wav(output)
            self.assertEqual(rate, 8000)
            self.assertEqual(len(audio), 8000)
            self.assertGreater(float(np.max(np.abs(audio))), 0.1)

    def test_bilingual_tracks_are_sequenced_in_one_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            en = Path(tmp) / "en.wav"
            te = Path(tmp) / "te.wav"
            output = Path(tmp) / "mix.wav"
            write_wav(en, np.full(1000, 0.2), 8000)
            write_wav(te, np.full(1000, -0.2), 8000)
            mix_timeline([[en, te]], [1.0], output, sample_rate=8000)
            audio, _ = _read_wav(output)
            self.assertEqual(len(audio), 8000)
            self.assertGreater(float(np.mean(audio[:900])), 0.1)
            self.assertLess(float(np.mean(audio[3200:4100])), -0.1)

    def test_narration_overrun_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "long.wav"
            output = Path(tmp) / "mix.wav"
            write_wav(source, np.full(9000, 0.1), 8000)
            with self.assertRaisesRegex(ValueError, "exceeds"):
                mix_timeline([source], [1.0], output, sample_rate=8000)

    def test_missing_track_leaves_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mix.wav"
            mix_timeline([None], [0.5], output, sample_rate=8000)
            audio, _ = _read_wav(output)
            self.assertEqual(len(audio), 4000)
            self.assertAlmostEqual(float(np.max(np.abs(audio))), 0.0, places=5)


    def test_crossfade_shortens_audio_timeline_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.wav"
            second = Path(tmp) / "second.wav"
            output = Path(tmp) / "mix.wav"
            write_wav(first, np.full(2000, 0.15), 8000)
            write_wav(second, np.full(2000, -0.15), 8000)
            mix_timeline([first, second], [1.0, 1.0], output,
                         sample_rate=8000, transition_seconds=0.25)
            audio, rate = _read_wav(output)
            self.assertEqual(rate, 8000)
            self.assertEqual(len(audio), 14000)

    def test_crossfade_cannot_equal_shortest_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mix.wav"
            with self.assertRaisesRegex(ValueError, "shorter than every scene"):
                mix_timeline([None, None], [1.0, 0.5], output,
                             sample_rate=8000, transition_seconds=0.5)


if __name__ == "__main__":
    unittest.main()
