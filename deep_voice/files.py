"""Offline conversion: deepen a recording or voice note file."""
import os
import shutil
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from .engine import VoiceEngine

SAMPLE_RATE_FALLBACK = 48000


def read_mono(path):
    try:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
    except Exception:
        data, sr = _decode_with_ffmpeg(path)
    return data.mean(axis=1).astype(np.float32), int(sr)


def _decode_with_ffmpeg(path):
    """Fallback for formats libsndfile cannot open, such as .m4a/.aac from phones."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("This file format needs ffmpeg. Convert it to WAV or OGG/Opus first.")
    with tempfile.TemporaryDirectory() as tmp:
        decoded = os.path.join(tmp, "decoded.wav")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", path, "-ac", "1",
                        "-ar", str(SAMPLE_RATE_FALLBACK), decoded], check=True)
        data, sr = sf.read(decoded, dtype="float32", always_2d=True)
    return data, sr


def convert_file(in_path, out_path, preset="Batman", semitones=None):
    """Read any format libsndfile can open (WAV, FLAC, MP3, OGG/Opus such as WhatsApp voice notes)
    and write the processed voice at the same sample rate and length."""
    mono, sr = read_mono(in_path)
    engine = VoiceEngine(sr, preset=preset, enabled=True)
    if semitones is not None:
        engine.set_semitones(semitones)
    lat = engine.latency_samples
    processed = engine.process(np.concatenate([mono, np.zeros(lat, dtype=np.float32)]))
    out = processed[lat:lat + len(mono)]
    sf.write(out_path, out, sr, subtype="PCM_16" if not out_path.lower().endswith(".flac") else None)
    return out_path


def output_name(in_path, preset):
    base, _ = os.path.splitext(in_path)
    return f"{base}_{preset.lower()}.wav"
