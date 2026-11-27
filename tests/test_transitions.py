"""Tests for frame-level scene transition helpers."""
import unittest
import numpy as np

from cineforge.transitions import crossfade_frames, crossfade_sequence, crossfade_clip_streams, transition_timeline


class TransitionTests(unittest.TestCase):
    def test_crossfade_frames_blends_matching_rgb_frames(self):
        outgoing = np.zeros((2, 3, 3), dtype=np.uint8)
        incoming = np.full((2, 3, 3), 200, dtype=np.uint8)
        result = crossfade_frames(outgoing, incoming)
        self.assertEqual(result.dtype, np.uint8)
        np.testing.assert_array_equal(result, np.full((2, 3, 3), 100, dtype=np.uint8))

    def test_sequence_moves_gradually_to_incoming_scene(self):
        outgoing = [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(3)]
        incoming = [np.full((1, 1, 3), 120, dtype=np.uint8) for _ in range(3)]
        result = crossfade_sequence(outgoing, incoming)
        values = [int(frame[0, 0, 0]) for frame in result]
        self.assertEqual(values, [40, 80, 120])

    def test_mismatched_lengths_are_rejected(self):
        frame = np.zeros((1, 1, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "equal lengths"):
            crossfade_sequence([frame], [frame, frame])

    def test_mismatched_frame_shapes_are_rejected(self):
        a = np.zeros((1, 1, 3), dtype=np.uint8)
        b = np.zeros((2, 1, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "matching"):
            crossfade_frames(a, b)


    def test_transition_timeline_overlaps_scene_starts(self):
        timeline = transition_timeline([10, 8, 6], 1.5)
        self.assertEqual(timeline["scene_starts"], [0.0, 8.5, 15.0])
        self.assertEqual(timeline["total_duration"], 21.0)

    def test_transition_must_be_shorter_than_each_scene(self):
        with self.assertRaisesRegex(ValueError, "shorter than every scene"):
            transition_timeline([2, 3], 2)


    def test_stream_compositor_overlaps_clip_boundary_and_shortens_runtime(self):
        a = [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(4)]
        b = [np.full((1, 1, 3), 100, dtype=np.uint8) for _ in range(4)]
        result = list(crossfade_clip_streams([iter(a), iter(b)], 2))
        self.assertEqual(len(result), 6)
        self.assertEqual([int(frame[0, 0, 0]) for frame in result], [0, 0, 50, 100, 100, 100])

    def test_zero_transition_keeps_all_frames(self):
        frames = [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(3)]
        self.assertEqual(len(list(crossfade_clip_streams([iter(frames)], 0))), 3)


if __name__ == "__main__":
    unittest.main()
