"""Tone presets. Pitch lives in dsp.py; everything else is pedalboard (streams fine)."""
from pedalboard import (Compressor, Distortion, Gain, HighpassFilter, Limiter,
                        LowShelfFilter, PeakFilter, Pedalboard, Reverb)

# semitones: pitch drop. highpass_hz: rumble cut before pitching.
# shelf_*: chest boost. presence_*: cut in the 2-3 kHz region for a darker sound.
# drive_db: soft grit. comp_*: evens out the voice. reverb_wet: small room.
PRESETS = {
    "Batman": dict(semitones=-5.0, highpass_hz=70.0, shelf_hz=120.0, shelf_db=5.0,
                   presence_hz=2800.0, presence_db=-4.0, drive_db=6.0,
                   comp_threshold_db=-20.0, comp_ratio=4.0, reverb_wet=0.04, gain_db=-6.0),
    "Deep": dict(semitones=-3.0, highpass_hz=80.0, shelf_hz=120.0, shelf_db=3.0,
                 presence_hz=2800.0, presence_db=0.0, drive_db=0.0,
                 comp_threshold_db=-20.0, comp_ratio=2.0, reverb_wet=0.0, gain_db=-0.7),
    "Giant": dict(semitones=-8.0, highpass_hz=60.0, shelf_hz=100.0, shelf_db=8.0,
                  presence_hz=3000.0, presence_db=-6.0, drive_db=12.0,
                  comp_threshold_db=-18.0, comp_ratio=6.0, reverb_wet=0.08, gain_db=-6.8),
}


def build_pre(preset):
    return Pedalboard([HighpassFilter(cutoff_frequency_hz=preset["highpass_hz"])])


def build_post(preset):
    plugins = [
        LowShelfFilter(cutoff_frequency_hz=preset["shelf_hz"], gain_db=preset["shelf_db"], q=0.7),
        PeakFilter(cutoff_frequency_hz=preset["presence_hz"], gain_db=preset["presence_db"], q=1.2),
    ]
    if preset["drive_db"] > 0:
        plugins.append(Distortion(drive_db=preset["drive_db"]))
    plugins.append(Compressor(threshold_db=preset["comp_threshold_db"], ratio=preset["comp_ratio"],
                              attack_ms=5.0, release_ms=120.0))
    if preset["reverb_wet"] > 0:
        plugins.append(Reverb(room_size=0.15, damping=0.7, wet_level=preset["reverb_wet"],
                              dry_level=1.0 - preset["reverb_wet"]))
    plugins.append(Gain(gain_db=preset["gain_db"]))
    plugins.append(Limiter(threshold_db=-1.0, release_ms=100.0))
    return Pedalboard(plugins)
