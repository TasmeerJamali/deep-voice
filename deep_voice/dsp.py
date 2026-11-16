"""Streaming pitch shifter: a phase vocoder written in numpy.

Why this exists: pedalboard 0.9.26's PitchShift goes silent after the first
block when it is streamed with reset=False (upstream PR #486 tracks the bug).
Offline it works, so this module does the streaming version itself.

Pitch only goes down here (semitones <= 0). Each spectral bin k moves to bin
round(k * ratio); with ratio <= 1 no target bin is left empty. Output is the
input delayed by one frame (2048 samples, about 43 ms at 48 kHz).
"""
import numpy as np

FRAME_SIZE = 2048
HOP_SIZE = 512


class PhaseVocoderPitchShifter:
    def __init__(self, sample_rate=48000, semitones=0.0, frame_size=FRAME_SIZE, hop_size=HOP_SIZE):
        frame_size = int(frame_size)
        hop_size = int(hop_size)
        if hop_size <= 0 or frame_size % hop_size or frame_size // hop_size < 2:
            raise ValueError("frame_size must be a multiple of hop_size, with at least 2 hops per frame")
        self.sample_rate = int(sample_rate)
        self.frame = frame_size
        self.hop = hop_size
        self._bins = frame_size // 2 + 1
        self._k = np.arange(self._bins, dtype=np.float64)
        self._expected_advance = 2.0 * np.pi * self._k * hop_size / frame_size
        n = np.arange(frame_size)
        self._window = 0.5 - 0.5 * np.cos(2.0 * np.pi * n / frame_size)
        self._ola_gain = float(np.sum(self._window ** 2) / hop_size)  # 1.5 for Hann at 75% overlap
        self._semitones = 0.0
        self._map = (1.0, np.arange(self._bins))  # (ratio, target bin per source bin), swapped in one step
        self.set_semitones(semitones)
        self.reset()

    @property
    def latency_samples(self):
        return self.frame

    @property
    def semitones(self):
        return self._semitones

    def set_semitones(self, semitones):
        s = float(semitones)
        if not -24.0 <= s <= 0.0:
            raise ValueError("semitones must be between -24 and 0 (this shifter only lowers pitch)")
        ratio = 2.0 ** (s / 12.0)
        self._semitones = s
        self._map = (ratio, np.rint(self._k * ratio).astype(np.int64))

    def reset(self):
        self._history = np.zeros(self.frame, dtype=np.float64)
        self._pending = np.zeros(0, dtype=np.float64)
        self._prev_phase = np.zeros(self._bins, dtype=np.float64)
        self._out_phase = np.zeros(self._bins, dtype=np.float64)
        self._overlap = np.zeros(self.frame, dtype=np.float64)
        self._fifo = np.zeros(self.hop, dtype=np.float64)

    def process(self, x):
        """Take any number of input samples; return the same number of output samples."""
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        n = x.shape[0]
        if n:
            self._pending = np.concatenate([self._pending, x])
        while self._pending.shape[0] >= self.hop:
            block = self._pending[:self.hop]
            self._pending = self._pending[self.hop:]
            self._fifo = np.concatenate([self._fifo, self._hop_step(block)])
        out = self._fifo[:n]
        self._fifo = self._fifo[n:]
        return out.astype(np.float32)

    def _hop_step(self, block):
        self._history = np.concatenate([self._history[self.hop:], block])
        spectrum = np.fft.rfft(self._history * self._window)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)

        deviation = phase - self._prev_phase - self._expected_advance
        self._prev_phase = phase
        deviation = np.mod(deviation + np.pi, 2.0 * np.pi) - np.pi
        true_bin = self._k + deviation * (self.frame / (2.0 * np.pi * self.hop))

        ratio, dest = self._map
        mag_out = np.zeros(self._bins, dtype=np.float64)
        np.maximum.at(mag_out, dest, magnitude)
        freq_out = self._k.copy()
        keep = magnitude == mag_out[dest]
        freq_out[dest[keep]] = true_bin[keep] * ratio

        self._out_phase = np.mod(self._out_phase + 2.0 * np.pi * freq_out * self.hop / self.frame, 2.0 * np.pi)
        synth = mag_out * np.exp(1j * self._out_phase)
        frame_out = np.fft.irfft(synth, n=self.frame) * self._window / self._ola_gain

        self._overlap = self._overlap + frame_out
        out = self._overlap[:self.hop].copy()
        self._overlap = np.concatenate([self._overlap[self.hop:], np.zeros(self.hop)])
        return out


def offline_pitch_shift(x, semitones, sample_rate=48000, frame_size=FRAME_SIZE, hop_size=HOP_SIZE):
    """Pitch-shift a whole array; output has the same length and no latency offset."""
    shifter = PhaseVocoderPitchShifter(sample_rate, semitones, frame_size, hop_size)
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    lat = shifter.latency_samples
    y = shifter.process(np.concatenate([x, np.zeros(lat, dtype=np.float32)]))
    return y[lat:lat + len(x)].copy()
