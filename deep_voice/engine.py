"""VoiceEngine: pitch stage plus tone chain, with a bypass that stays in time with the wet path."""
import threading

import numpy as np

from .chain import PRESETS, build_post, build_pre
from .dsp import PhaseVocoderPitchShifter

RAMP_SECONDS = 0.02  # on/off crossfade length
SAFE_PEAK = 0.98     # hard ceiling on the output, a last line of defence against overs


class VoiceEngine:
    def __init__(self, sample_rate=48000, preset="Batman", enabled=True):
        self.sample_rate = int(sample_rate)
        self._lock = threading.Lock()  # guards settings the GUI thread changes while audio runs
        self._pitch = PhaseVocoderPitchShifter(self.sample_rate)
        self._pre = None
        self._post = None
        self._preset = None
        self._fresh = True
        self._target = 1.0 if enabled else 0.0
        self._mix = self._target
        self._ramp = max(1, int(round(RAMP_SECONDS * self.sample_rate)))
        self._dry_delay = np.zeros(self.latency_samples, dtype=np.float32)
        self.set_preset(preset)

    @property
    def latency_samples(self):
        return self._pitch.latency_samples

    @property
    def enabled(self):
        return self._target == 1.0

    @property
    def mix(self):
        return self._mix

    @property
    def semitones(self):
        return self._pitch.semitones

    @property
    def preset(self):
        return self._preset

    def set_enabled(self, on):
        self._target = 1.0 if on else 0.0

    def set_semitones(self, semitones):
        with self._lock:
            self._pitch.set_semitones(semitones)

    def set_preset(self, name):
        if name not in PRESETS:
            raise KeyError(f"unknown preset {name!r}; choose from {', '.join(PRESETS)}")
        preset = PRESETS[name]
        pre, post = build_pre(preset), build_post(preset)
        with self._lock:
            self._pre = pre
            self._post = post
            self._preset = name
            self._pitch.set_semitones(preset["semitones"])
            self._fresh = True

    def process(self, x):
        """Process one block of mono audio. Returns the same number of samples."""
        with self._lock:
            return self._process_locked(x)

    def _process_locked(self, x):
        x = np.asarray(x, dtype=np.float32).reshape(-1)
        n = x.shape[0]
        if n == 0:
            return np.zeros(0, dtype=np.float32)
        reset = self._fresh
        self._fresh = False
        sr = float(self.sample_rate)
        wet = self._pre.process(x.reshape(1, -1), sr, reset=reset)[0]
        wet = self._pitch.process(wet)
        wet = self._post.process(wet.reshape(1, -1), sr, reset=reset)[0]

        buffered = np.concatenate([self._dry_delay, x])
        dry = buffered[:n]
        self._dry_delay = buffered[n:]

        mix = self._mix_curve(n)
        out = mix * wet + (1.0 - mix) * dry
        return np.clip(out, -SAFE_PEAK, SAFE_PEAK).astype(np.float32)

    def _mix_curve(self, n):
        target = self._target
        if self._mix == target:
            return np.full(n, target, dtype=np.float32)
        direction = 1.0 if target > self._mix else -1.0
        steps = self._mix + direction * (np.arange(1, n + 1, dtype=np.float64) / self._ramp)
        curve = np.minimum(steps, target) if direction > 0 else np.maximum(steps, target)
        self._mix = float(curve[-1])
        return curve.astype(np.float32)
