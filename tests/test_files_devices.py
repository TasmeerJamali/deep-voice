import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.dirname(TESTS_DIR))

from helpers import peak_f0, voice_like  # noqa: E402
from deep_voice.audio import is_virtual_cable, pick_input, pick_output  # noqa: E402
from deep_voice.files import convert_file  # noqa: E402


def device(index, name, api="Windows WASAPI", inp=2, out=0):
    return {"index": index, "name": name, "hostapi_name": api,
            "max_input_channels": inp, "max_output_channels": out}


class FileConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_wav_at_44k_keeps_rate_and_length_and_lowers_pitch(self):
        x = voice_like(1.5, sr=44100)
        src = os.path.join(self.tmp, "in.wav")
        dst = os.path.join(self.tmp, "out.wav")
        sf.write(src, x, 44100, subtype="PCM_16")
        convert_file(src, dst, preset="Batman")
        y, sr = sf.read(dst, dtype="float32")
        self.assertEqual(sr, 44100)
        self.assertEqual(len(y), len(x))
        self.assertLessEqual(float(np.max(np.abs(y))), 1.0)
        f0 = peak_f0(y[int(0.5 * sr): int(1.2 * sr)], sr=sr)
        self.assertAlmostEqual(f0, 112.4, delta=4.0)

    def test_opus_voice_note_can_be_converted(self):
        x = voice_like(1.0, sr=48000)
        src = os.path.join(self.tmp, "note.opus")
        dst = os.path.join(self.tmp, "note_deep.wav")
        sf.write(src, x, 48000, format="OGG", subtype="OPUS")
        convert_file(src, dst, preset="Batman")
        y, sr = sf.read(dst, dtype="float32")
        self.assertEqual(sr, 48000)
        self.assertAlmostEqual(len(y) / sr, 1.0, delta=0.02)
        self.assertGreater(float(np.max(np.abs(y))), 0.01)


class ContainerFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is not installed")
    def test_m4a_recording_is_decoded_with_ffmpeg(self):
        x = voice_like(1.0, sr=48000)
        wav = os.path.join(self.tmp, "src.wav")
        m4a = os.path.join(self.tmp, "note.m4a")
        dst = os.path.join(self.tmp, "note_deep.wav")
        sf.write(wav, x, 48000, subtype="PCM_16")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "aac", "-b:a", "96k", m4a],
                       check=True)
        convert_file(m4a, dst, preset="Batman")
        y, sr = sf.read(dst, dtype="float32")
        self.assertAlmostEqual(len(y) / sr, 1.0, delta=0.05)


class DeviceSelectionTests(unittest.TestCase):
    def test_virtual_cables_are_never_picked_as_the_microphone(self):
        devices = [
            device(5, "CABLE Output (VB-Audio Virtual Cable)"),
            device(21, "Microphone (USB Audio Device)"),
            device(1, "Microphone (USB Audio Device)", api="MME"),
        ]
        self.assertEqual(pick_input(devices)["index"], 21)

    def test_named_virtual_cable_is_refused_as_the_microphone(self):
        devices = [device(5, "CABLE Output (VB-Audio Virtual Cable)")]
        with self.assertRaises(ValueError):
            pick_input(devices, name="CABLE Output (VB-Audio Virtual Cable)")

    def test_named_input_is_matched_exactly(self):
        devices = [
            device(21, "Microphone (USB Audio Device)"),
            device(24, "Microphone (High Definition Audio Device)"),
        ]
        picked = pick_input(devices, name="Microphone (High Definition Audio Device)")
        self.assertEqual(picked["index"], 24)

    def test_output_prefers_cable_input(self):
        devices = [
            device(18, "Headphones (Futura Ai-200)", inp=0, out=2),
            device(30, "CABLE Input (VB-Audio Virtual Cable)", inp=0, out=2),
        ]
        self.assertEqual(pick_output(devices)["index"], 30)

    def test_is_virtual_cable(self):
        self.assertTrue(is_virtual_cable("CABLE Input (VB-Audio Virtual Cable)"))
        self.assertTrue(is_virtual_cable("CABLE Output (VB-Audio Virtual Cable)"))
        self.assertFalse(is_virtual_cable("Microphone (USB Audio Device)"))


if __name__ == "__main__":
    unittest.main()
