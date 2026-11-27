"""Regression tests for audio timeline alignment and mix boundaries."""
import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np

from cineforge.audio_mix import mix_timeline, _read_wav

def write_audio(path, seconds, rate=8000, amplitude=0.1):
    samples=np.full(round(seconds*rate), amplitude, dtype=np.float32)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((samples*32767).astype(np.int16).tobytes())

class AudioSyncRegressionTests(unittest.TestCase):
    def test_two_scene_timeline_duration_with_overlap(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.wav"; q=Path(td)/"b.wav"; out=Path(td)/"mix.wav"
            write_audio(p,.4); write_audio(q,.4,-8000 if False else 8000, amplitude=-.1)
            mix_timeline([p,q],[1,1],out,sample_rate=8000,transition_seconds=.25)
            data,rate=_read_wav(out)
            self.assertEqual(rate,8000)
            self.assertEqual(len(data),round(1.75*rate))

    def test_sample_rate_conversion_preserves_timeline_duration(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"voice.wav"; out=Path(td)/"mix.wav"
            write_audio(p,.25,rate=11025)
            mix_timeline([p],[1],out,sample_rate=8000)
            data,rate=_read_wav(out)
            self.assertEqual(rate,8000)
            self.assertEqual(len(data),8000)

    def test_fade_in_and_out_reduce_edge_amplitude(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"voice.wav"; out=Path(td)/"mix.wav"
            write_audio(p,.5,amplitude=.4)
            mix_timeline([p],[1],out,sample_rate=8000,fade_seconds=.1)
            data,_=_read_wav(out)
            self.assertLess(abs(float(data[0])),.01)
            self.assertLess(abs(float(data[-1])),.01)

    def test_missing_narration_file_is_silent_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"mix.wav"
            mix_timeline([Path(td)/"missing.wav"],[.25],out,sample_rate=8000)
            data,_=_read_wav(out)
            self.assertEqual(len(data),2000)
            self.assertAlmostEqual(float(np.max(np.abs(data))),0.0,places=5)

    def test_narration_list_with_gap_stays_within_scene(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"voice.wav"; out=Path(td)/"mix.wav"
            write_audio(p,.2)
            mix_timeline([[p,p]],[1],out,sample_rate=8000)
            data,_=_read_wav(out)
            self.assertEqual(len(data),8000)
            self.assertGreater(float(np.max(np.abs(data))),.1)

if __name__=="__main__":
    unittest.main()
