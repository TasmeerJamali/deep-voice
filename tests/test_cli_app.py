import contextlib
import io
import os
import sys
import tkinter as tk
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(TESTS_DIR)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, PROJECT)

import app as app_module  # noqa: E402
import cli  # noqa: E402


class AppWindowTests(unittest.TestCase):
    def test_window_builds_and_switch_and_preset_update_the_engine(self):
        root = tk.Tk()
        root.withdraw()
        ui = None
        try:
            ui = app_module.DeepVoiceApp(root, register_hotkey=False)
            root.update()
            self.assertEqual(ui.toggle_button.cget("text"), "VOICE OFF")
            ui.toggle_voice()
            ui._poll()
            self.assertEqual(ui.toggle_button.cget("text"), "VOICE ON")
            ui.preset_var.set("Giant")
            ui._on_preset()
            self.assertEqual(ui.engine.preset, "Giant")
            self.assertAlmostEqual(ui.engine.semitones, -8.0)
        finally:
            if ui is not None:
                ui.close()
            else:
                root.destroy()


class CommandLineTests(unittest.TestCase):
    def test_convert_accepts_a_preset_and_pitch_override(self):
        args = cli.build_parser().parse_args(["convert", "note.opus", "--preset", "Giant", "--semitones=-6"])
        self.assertEqual(args.command, "convert")
        self.assertEqual(args.preset, "Giant")
        self.assertEqual(args.semitones, -6.0)

    def test_unknown_preset_is_rejected(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.build_parser().parse_args(["live", "--preset", "Nope"])


if __name__ == "__main__":
    unittest.main()
