import os
import sys
import unittest

import numpy as np

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.dirname(TESTS_DIR))

from helpers import SR, peak_f0, stream_in_chunks, voice_like  # noqa: E402
from deep_voice.dsp import PhaseVocoderPitchShifter, offline_pitch_shift  # noqa: E402


class PhaseVocoderTests(unittest.TestCase):
    def test_offline_shift_lowers_pitch_by_five_semitones(self):
        x = voice_like(2.0)
        y = offline_pitch_shift(x, semitones=-5.0, sample_rate=SR)
        self.assertEqual(len(y), len(x))
        f0 = peak_f0(y[SR // 2: SR * 3 // 2])
        self.assertAlmostEqual(f0, 150.0 * 2 ** (-5 / 12), delta=2.5)

    def test_streaming_in_uneven_chunks_matches_single_call(self):
        x = voice_like(1.5)
        whole = PhaseVocoderPitchShifter(SR, semitones=-5.0).process(x)
        shifter = PhaseVocoderPitchShifter(SR, semitones=-5.0)
        sizes = [50, 1200, 333, 7, 999, 512, 1, 2047, 129]  # fixed, uneven chunk sizes
        pieces, i, k = [], 0, 0
        while i < len(x):
            n = sizes[k % len(sizes)]
            k += 1
            pieces.append(shifter.process(x[i:i + n]))
            i += n
        streamed = np.concatenate(pieces)
        self.assertEqual(len(streamed), len(x))
        np.testing.assert_allclose(streamed, whole, atol=1e-5)

    def test_latency_is_one_frame(self):
        self.assertEqual(PhaseVocoderPitchShifter(SR, semitones=0.0).latency_samples, 2048)

    def test_output_length_matches_input_for_any_block_size(self):
        shifter = PhaseVocoderPitchShifter(SR, semitones=-5.0)
        for n in [1, 17, 512, 1023, 4096]:
            out = shifter.process(np.zeros(n, dtype=np.float32))
            self.assertEqual(out.shape, (n,))
            self.assertEqual(out.dtype, np.float32)

    def test_zero_shift_reproduces_input_after_latency(self):
        x = voice_like(1.0)
        shifter = PhaseVocoderPitchShifter(SR, semitones=0.0)
        pad = np.zeros(shifter.latency_samples, dtype=np.float32)
        y = shifter.process(np.concatenate([x, pad]))
        aligned = y[shifter.latency_samples:shifter.latency_samples + len(x)]
        corr = float(np.dot(aligned, x) / (np.linalg.norm(aligned) * np.linalg.norm(x) + 1e-12))
        self.assertGreater(corr, 0.98)

    def test_output_is_finite_and_not_clipping(self):
        x = voice_like(2.0)
        y = offline_pitch_shift(x, semitones=-8.0, sample_rate=SR)
        self.assertTrue(np.all(np.isfinite(y)))
        self.assertLess(float(np.max(np.abs(y))), 1.0)

    def test_stream_helper_matches_process(self):
        x = voice_like(0.5)
        a = PhaseVocoderPitchShifter(SR, semitones=-3.0)
        b = PhaseVocoderPitchShifter(SR, semitones=-3.0)
        np.testing.assert_allclose(stream_in_chunks(a.process, x, 256), b.process(x), atol=1e-5)


if __name__ == "__main__":
    unittest.main()
