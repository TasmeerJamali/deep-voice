"""Command line tools: list devices, deepen files, preview a file, or run the live effect from the terminal.

Examples:
  python cli.py devices
  python cli.py convert "voice note.opus"
  python cli.py convert "voice note.opus" deep.wav --preset Giant
  python cli.py preview "voice note.opus" --compare
  python cli.py live --output "CABLE Input"
"""
import argparse
import sys
import time

import numpy as np

from deep_voice import audio
from deep_voice.chain import PRESETS
from deep_voice.engine import VoiceEngine
from deep_voice.files import convert_file, output_name, read_mono

SAMPLE_RATE = 48000


def cmd_devices(args):
    for d in audio.list_devices():
        if d["hostapi_name"] != audio.WASAPI and not args.all:
            continue
        print(f"{d['index']:>3}  {d['name']}  [in {d['max_input_channels']} / out {d['max_output_channels']}]"
              f"  {d['hostapi_name']}")


def cmd_convert(args):
    out = args.output or output_name(args.input, args.preset)
    convert_file(args.input, out, preset=args.preset, semitones=args.semitones)
    print(f"Saved {out}")


def _processed(path, preset, semitones):
    mono, sr = read_mono(path)
    engine = VoiceEngine(sr, preset=preset, enabled=True)
    if semitones is not None:
        engine.set_semitones(semitones)
    lat = engine.latency_samples
    y = engine.process(np.concatenate([mono, np.zeros(lat, dtype=np.float32)]))
    return y[lat:lat + len(mono)], mono, sr


def cmd_preview(args):
    import sounddevice as sd

    deep, original, sr = _processed(args.input, args.preset, args.semitones)
    if args.compare:
        print("Original voice...")
        sd.play(original, sr)
        sd.wait()
        time.sleep(0.5)
    print(f"{args.preset} preset...")
    sd.play(deep, sr)
    sd.wait()


def cmd_live(args):
    devices = audio.list_devices()
    mic = audio.pick_input(devices, args.input)
    out = audio.pick_output(devices, args.output)
    if out is None:
        sys.exit("No output device found. Install VB-CABLE (see README) or pass --output.")
    engine = VoiceEngine(SAMPLE_RATE, preset=args.preset, enabled=False)
    live = audio.LiveVoice(engine, mic["index"], out["index"], SAMPLE_RATE)
    live.start()
    print(f"Running: {mic['name']} to {out['name']}.")
    print("Press Enter to switch the effect on or off. Type q and Enter to quit.")
    try:
        while True:
            line = input().strip().lower()
            if line == "q":
                break
            engine.set_enabled(not engine.enabled)
            print("Effect ON" if engine.enabled else "Effect OFF")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        live.stop()


def build_parser():
    parser = argparse.ArgumentParser(prog="cli.py", description="Deep voice effect tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dev = sub.add_parser("devices", help="list audio devices")
    p_dev.add_argument("--all", action="store_true", help="include MME, DirectSound and WDM-KS entries")
    p_dev.set_defaults(func=cmd_devices)

    p_conv = sub.add_parser("convert", help="deepen a voice note or recording file")
    p_conv.add_argument("input")
    p_conv.add_argument("output", nargs="?")
    p_conv.add_argument("--preset", default="Batman", choices=list(PRESETS))
    p_conv.add_argument("--semitones", type=float, help="override the preset pitch, e.g. --semitones=-6")
    p_conv.set_defaults(func=cmd_convert)

    p_prev = sub.add_parser("preview", help="play a file through your speakers, processed")
    p_prev.add_argument("input")
    p_prev.add_argument("--preset", default="Batman", choices=list(PRESETS))
    p_prev.add_argument("--semitones", type=float)
    p_prev.add_argument("--compare", action="store_true", help="play the original first")
    p_prev.set_defaults(func=cmd_preview)

    p_live = sub.add_parser("live", help="run the effect on your mic from the terminal")
    p_live.add_argument("--input", help="microphone name (default: first real mic)")
    p_live.add_argument("--output", help="output name (default: VB-CABLE Input)")
    p_live.add_argument("--preset", default="Batman", choices=list(PRESETS))
    p_live.set_defaults(func=cmd_live)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
