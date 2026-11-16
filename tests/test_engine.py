import os
import sys
import unittest

import numpy as np

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.dirname(TESTS_DIR))

from helpers import SR, peak_f0, stream_in_chunks, voice_like  # noqa: E402
from deep_voice.chain import PRESETS  # noqa: E402
from deep_voice.engine import VoiceEngine  # noqa: E402


class EngineTests(unittest.TestCase):
    def test_bypass_is_the_dry_signal_delayed_by_latency(self):
        eng = VoiceEngine(SR, preset="Batman", enabled=False)
        x = voice_like(1.0)
        y = stream_in_chunks(eng.process, x, 512)
        latency = eng.latency_samples
        self.assertEqual(len(y), len(x))
        np.testing.assert_allclose(y[latency:], x[:len(x) - latency], atol=1e-6)
        self.assertTrue(np.allclose(y[:latency], 0.0))

    def test_enabled_lowers_pitch_by_the_preset_amount(self):
        eng = VoiceEngine(SR, preset="Batman", enabled=True)
        x = voice_like(3.0)
        y = stream_in_chunks(eng.process, x, 512)
        f0 = peak_f0(y[2 * SR:3 * SR])
        self.assertAlmostEqual(f0, 150.0 * 2 ** (-5 / 12), delta=4.0)

    def test_switching_on_ramps_over_about_20_ms(self):
        eng = VoiceEngine(SR, preset="Batman", enabled=False)
        eng.set_enabled(True)
        eng.process(np.zeros(480, dtype=np.float32))
        self.assertTrue(0.3 < eng.mix < 0.7)
        eng.process(np.zeros(1000, dtype=np.float32))
        self.assertEqual(eng.mix, 1.0)

    def test_chunk_size_does_not_change_the_output(self):
        x = voice_like(1.5)
        whole = VoiceEngine(SR, preset="Batman", enabled=True).process(x)
        chunked = stream_in_chunks(VoiceEngine(SR, preset="Batman", enabled=True).process, x, 512)
        np.testing.assert_allclose(chunked, whole, atol=1e-4)

    def test_every_preset_is_level_matched_and_never_overs(self):
        x = voice_like(4.0)
        for name in PRESETS:
            eng = VoiceEngine(SR, name, True)
            y = stream_in_chunks(eng.process, x, 512)
            rms_in = float(np.sqrt(np.mean(x[:2 * SR] ** 2)))
            rms_out = float(np.sqrt(np.mean(y[2 * SR:4 * SR] ** 2)))
            self.assertLess(abs(20 * np.log10(rms_out / rms_in)), 2.0, name)
            self.assertLessEqual(float(np.max(np.abs(y))), 0.98 + 1e-6, name)

    def test_presets_and_pitch_override(self):
        self.assertEqual(set(PRESETS), {"Batman", "Deep", "Giant"})
        eng = VoiceEngine(SR, preset="Giant")
        self.assertEqual(eng.semitones, -8.0)
        eng.set_semitones(-3.0)
        self.assertEqual(eng.semitones, -3.0)
        eng.set_preset("Deep")
        self.assertEqual(eng.semitones, PRESETS["Deep"]["semitones"])


if __name__ == "__main__":
    unittest.main()
