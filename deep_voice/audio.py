"""Audio devices and the live stream that runs the voice engine.

Windows setup: VB-CABLE gives you a virtual microphone. The app plays your
processed voice into "CABLE Input", and apps record from "CABLE Output".
"""
import numpy as np

WASAPI = "Windows WASAPI"


def is_virtual_cable(name):
    upper = name.upper()
    return "VB-AUDIO" in upper or upper.startswith("CABLE ")


def input_choices(devices):
    """Microphones to offer in the app: Windows WASAPI inputs, virtual cables removed."""
    return [d for d in devices
            if d["max_input_channels"] > 0 and d["hostapi_name"] == WASAPI
            and not is_virtual_cable(d["name"])]


def output_choices(devices):
    return [d for d in devices if d["max_output_channels"] > 0 and d["hostapi_name"] == WASAPI]


def list_devices():
    import sounddevice as sd

    apis = sd.query_hostapis()
    devices = []
    for index, info in enumerate(sd.query_devices()):
        devices.append({
            "index": index,
            "name": info["name"],
            "hostapi_name": apis[info["hostapi"]]["name"],
            "max_input_channels": info["max_input_channels"],
            "max_output_channels": info["max_output_channels"],
            "default_samplerate": info["default_samplerate"],
        })
    return devices


def pick_input(devices, name=None):
    """Your real microphone. Virtual cables are refused to avoid a feedback loop."""
    if name is not None and is_virtual_cable(name):
        raise ValueError("A virtual cable cannot be the microphone. Pick your real mic.")
    candidates = input_choices(devices)
    if name is not None:
        matches = [d for d in candidates if d["name"] == name]
        if not matches:
            raise LookupError(f"No microphone named {name!r}")
        return matches[0]
    if not candidates:
        raise LookupError("No microphone found")
    return candidates[0]


def pick_output(devices, name=None):
    """Where the processed voice goes. Prefers VB-CABLE Input when present."""
    candidates = output_choices(devices)
    if name is not None:
        matches = [d for d in candidates if d["name"] == name]
        if not matches:
            raise LookupError(f"No output device named {name!r}")
        return matches[0]
    for d in candidates:
        if d["name"].upper().startswith("CABLE INPUT"):
            return d
    return candidates[0] if candidates else None


class LiveVoice:
    """Runs a VoiceEngine between a real microphone and an output device."""

    def __init__(self, engine, input_index, output_index, samplerate=48000, blocksize=512):
        import sounddevice as sd

        self.engine = engine
        self.samplerate = int(samplerate)
        self.callback_errors = 0
        self.last_error = None
        in_info = sd.query_devices(input_index)
        out_info = sd.query_devices(output_index)
        in_channels = max(1, min(2, int(in_info["max_input_channels"])))
        out_channels = max(1, min(2, int(out_info["max_output_channels"])))
        self._stream = sd.Stream(
            samplerate=self.samplerate,
            blocksize=blocksize,
            device=(input_index, output_index),
            channels=(in_channels, out_channels),
            dtype="float32",
            latency="low",
            callback=self._callback,
            extra_settings=(sd.WasapiSettings(auto_convert=True), sd.WasapiSettings(auto_convert=True)),
        )

    def _callback(self, indata, outdata, frames, time_info, status):
        try:
            mono = indata[:, 0] if indata.shape[1] == 1 else indata.mean(axis=1)
            outdata[:] = self.engine.process(np.ascontiguousarray(mono)).reshape(-1, 1)
        except Exception as exc:  # never let an exception kill the audio thread silently
            self.callback_errors += 1
            self.last_error = repr(exc)
            outdata[:] = 0

    def start(self):
        self._stream.start()

    def stop(self):
        self._stream.stop()
        self._stream.close()

    @property
    def latency_seconds(self):
        return float(self._stream.latency[0] + self._stream.latency[1])
