"""Deep Voice window: a big on/off switch, presets, a pitch slider, device pickers and a global hotkey."""
import os
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from deep_voice import audio
from deep_voice.chain import PRESETS
from deep_voice.engine import VoiceEngine
from deep_voice.files import convert_file, output_name

SAMPLE_RATE = 48000
HOTKEY = "ctrl+alt+d"
HOTKEY_LABEL = "Ctrl+Alt+D"
ON_COLOR = "#1f8a4c"
OFF_COLOR = "#3a3a3a"
AUDIO_TYPES = [("Voice notes and recordings", "*.opus *.ogg *.wav *.mp3 *.flac *.m4a *.aac"),
               ("All files", "*.*")]


class DeepVoiceApp:
    def __init__(self, root, register_hotkey=True):
        self.root = root
        self.engine = VoiceEngine(SAMPLE_RATE, preset="Batman", enabled=False)
        self.live = None
        self._closing = False
        self._keyboard = None
        self._hotkey_handle = None
        self._shown_error = None
        self.devices = audio.list_devices()
        self.inputs = audio.input_choices(self.devices)
        self.outputs = audio.output_choices(self.devices)
        self._build()
        self._select_defaults()
        if register_hotkey:
            self._register_hotkey()
        self._poll()
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ---- layout -----------------------------------------------------------
    def _build(self):
        root = self.root
        root.title("Deep Voice")
        root.resizable(False, False)
        root.configure(padx=16, pady=14)

        self.toggle_button = tk.Button(
            root, text="VOICE OFF", font=("Segoe UI", 22, "bold"), width=18, height=2,
            fg="white", bg=OFF_COLOR, activeforeground="white", activebackground=OFF_COLOR,
            relief="flat", cursor="hand2", command=self.toggle_voice)
        self.toggle_button.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.hotkey_label = tk.Label(root, text=f"Press {HOTKEY_LABEL} in any app to switch", fg="#666666")
        self.hotkey_label.grid(row=1, column=0, columnspan=2, pady=(0, 12))

        tk.Label(root, text="Preset").grid(row=2, column=0, sticky="w")
        self.preset_var = tk.StringVar(value="Batman")
        preset_box = ttk.Combobox(root, textvariable=self.preset_var, values=list(PRESETS),
                                  state="readonly", width=28)
        preset_box.grid(row=2, column=1, sticky="ew", pady=3)
        preset_box.bind("<<ComboboxSelected>>", self._on_preset)

        tk.Label(root, text="Pitch drop (semitones)").grid(row=3, column=0, sticky="w")
        self.pitch = tk.Scale(root, from_=-12, to=0, resolution=0.5, orient="horizontal",
                              length=210, command=self._on_pitch)
        self.pitch.set(PRESETS["Batman"]["semitones"])
        self.pitch.grid(row=3, column=1, sticky="ew")

        tk.Label(root, text="Your microphone").grid(row=4, column=0, sticky="w")
        self.in_box = ttk.Combobox(root, state="readonly", width=40,
                                   values=[d["name"] for d in self.inputs])
        self.in_box.grid(row=4, column=1, sticky="ew", pady=3)
        self.in_box.bind("<<ComboboxSelected>>", self._on_device_change)

        tk.Label(root, text="Send voice to").grid(row=5, column=0, sticky="w")
        self.out_box = ttk.Combobox(root, state="readonly", width=40,
                                    values=[d["name"] for d in self.outputs])
        self.out_box.grid(row=5, column=1, sticky="ew", pady=3)
        self.out_box.bind("<<ComboboxSelected>>", self._on_device_change)

        self.cable_label = tk.Label(root, text="", wraplength=380, justify="left")
        self.cable_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 6))

        self.audio_button = ttk.Button(root, text="Start audio", command=self.toggle_audio)
        self.audio_button.grid(row=7, column=0, columnspan=2, sticky="ew")
        ttk.Button(root, text="Convert a voice note or recording...",
                   command=self.convert_dialog).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        self.status_var = tk.StringVar(value="Pick your mic and output, then press Start audio.")
        tk.Label(root, textvariable=self.status_var, wraplength=380, justify="left",
                 fg="#333333").grid(row=9, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _select_defaults(self):
        if self.inputs:
            self.in_box.current(0)
        cable = [i for i, d in enumerate(self.outputs) if d["name"].upper().startswith("CABLE INPUT")]
        if cable:
            self.out_box.current(cable[0])
            self.cable_label.config(text="VB-CABLE found. Apps should record from CABLE Output.", fg=ON_COLOR)
        else:
            if self.outputs:
                self.out_box.current(0)
            self.cable_label.config(
                text="VB-CABLE not found yet. Install it (README step 1), or pick headphones to test.",
                fg="#b35c00")

    # ---- voice on/off and settings ------------------------------------------
    def toggle_voice(self):
        self.engine.set_enabled(not self.engine.enabled)

    def _on_preset(self, _event=None):
        self.engine.set_preset(self.preset_var.get())
        self.pitch.set(self.engine.semitones)

    def _on_pitch(self, value):
        self.engine.set_semitones(float(value))

    # ---- audio streams ------------------------------------------------------
    @staticmethod
    def _chosen(choices, box):
        index = box.current()
        return choices[index] if 0 <= index < len(choices) else None

    def toggle_audio(self):
        if self.live is not None:
            self.stop_audio()
        else:
            self.start_audio()

    def _on_device_change(self, _event=None):
        if self.live is not None:
            self.start_audio()

    def start_audio(self):
        self.stop_audio()
        mic = self._chosen(self.inputs, self.in_box)
        out = self._chosen(self.outputs, self.out_box)
        if mic is None or out is None:
            self._status("Pick a microphone and an output device first.")
            return
        try:
            live = audio.LiveVoice(self.engine, mic["index"], out["index"], SAMPLE_RATE)
            live.start()
        except Exception as exc:
            self._status(f"Could not start audio: {exc}")
            return
        self.live = live
        self._shown_error = None
        self.audio_button.config(text="Stop audio")
        self._status(f"Running: {mic['name']} to {out['name']}. Delay about "
                     f"{live.latency_seconds * 1000:.0f} ms plus the one-frame pitch delay of about 43 ms.")

    def stop_audio(self):
        if self.live is None:
            return
        try:
            self.live.stop()
        except Exception:
            pass
        self.live = None
        self.audio_button.config(text="Start audio")
        self._status("Audio stopped. Apps that record from CABLE Output will hear silence until you start again.")

    # ---- hotkey -------------------------------------------------------------
    def _register_hotkey(self):
        try:
            import keyboard
            self._keyboard = keyboard
            self._hotkey_handle = keyboard.add_hotkey(HOTKEY, self._hotkey_pressed)
        except Exception as exc:
            self.hotkey_label.config(text="Global hotkey unavailable. Use the switch above.")
            self._status(f"Hotkey not active: {exc}")

    def _hotkey_pressed(self):
        # Runs on the keyboard thread: only flip the flag; the window picks it up in _poll.
        self.engine.set_enabled(not self.engine.enabled)

    # ---- file conversion ----------------------------------------------------
    def convert_dialog(self):
        path = filedialog.askopenfilename(title="Pick a voice note or recording", filetypes=AUDIO_TYPES)
        if not path:
            return
        out = output_name(path, self.engine.preset)
        try:
            convert_file(path, out, preset=self.engine.preset, semitones=self.engine.semitones)
        except Exception as exc:
            messagebox.showerror("Deep Voice", f"Could not convert that file.\n\n{exc}")
            return
        self._status(f"Saved {os.path.basename(out)} next to the original.")

    # ---- window plumbing ----------------------------------------------------
    def _status(self, text):
        self.status_var.set(text)

    def _poll(self):
        if self._closing:
            return
        on = self.engine.enabled
        color = ON_COLOR if on else OFF_COLOR
        self.toggle_button.config(text="VOICE ON" if on else "VOICE OFF", bg=color, activebackground=color)
        if self.live is not None and self.live.callback_errors and self.live.last_error != self._shown_error:
            self._shown_error = self.live.last_error
            self._status(f"Audio problem: {self._shown_error}")
        self.root.after(150, self._poll)

    def close(self):
        self._closing = True
        self.stop_audio()
        if self._keyboard is not None and self._hotkey_handle is not None:
            try:
                self._keyboard.remove_hotkey(self._hotkey_handle)
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        DeepVoiceApp(root)
    except Exception:
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep-voice-error.txt")
        with open(log, "w", encoding="utf-8") as handle:
            handle.write(traceback.format_exc())
        messagebox.showerror("Deep Voice", f"Something went wrong while starting. Details are in:\n{log}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
