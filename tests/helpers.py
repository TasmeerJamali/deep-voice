"""Shared test signals and measurements."""
import numpy as np

SR = 48000


def voice_like(seconds, f0=150.0, sr=SR, amplitude=0.3):
    """Harmonic tone with a voice-like fundamental (1/k harmonic roll-off)."""
    t = np.arange(int(round(seconds * sr))) / sr
    y = np.zeros_like(t)
    for k in range(1, 30):
        y += (1.0 / k) * np.sin(2 * np.pi * f0 * k * t)
    y /= np.max(np.abs(y))
    return (amplitude * y).astype(np.float32)


def peak_f0(y, sr=SR, lo=60.0, hi=400.0):
    """Frequency of the strongest spectral peak inside [lo, hi] Hz."""
    y = np.asarray(y, dtype=np.float64) * np.hanning(len(y))
    n = 8 * len(y)
    spec = np.abs(np.fft.rfft(y, n=n))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = (freqs >= lo) & (freqs <= hi)
    return float(freqs[mask][np.argmax(spec[mask])])


def stream_in_chunks(process, x, chunk):
    """Feed x to a streaming process() in fixed-size chunks and join the outputs."""
    pieces = []
    for i in range(0, len(x), chunk):
        pieces.append(process(x[i:i + chunk]))
    return np.concatenate(pieces)
