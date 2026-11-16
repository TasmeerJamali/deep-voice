# Deep Voice

A fun Windows project: a real-time "deep Batman" voice effect for your microphone.

Deep Voice takes your microphone, deepens your voice in real time, and sends it to your headphones or to a virtual microphone. Any PC app that records from that virtual microphone gets the deep voice: calls, voice notes, recordings. A hotkey, Ctrl+Alt+D, switches the effect on and off from any app.

This is a personal project. It approximates the effect from the film. It does not reproduce the film's exact processing, and it is not affiliated with the film or its studio.

## Features

- Real-time pitch drop (a phase vocoder written in numpy), a bass boost, a little grit and a small room
- Three presets: Batman (default), Deep (subtle) and Giant (extreme), plus a pitch slider
- Global hotkey, Ctrl+Alt+D
- Convert voice notes and recordings to a deep WAV: `.opus`, `.ogg`, `.wav`, `.flac`, `.mp3`, and `.m4a` with ffmpeg
- Command-line tools: list devices, convert, preview, and a terminal live mode

## Limits

- **Windows PC only.** Phone audio never passes through the PC, so phone calls and phone voice notes can't be changed live.
- **Only apps that record from the virtual microphone** get the effect (see Setup). Everything else still gets your normal voice.
- **Pitch only goes down.** The window goes down to -12 semitones. The engine accepts down to -24.
- **Delay:** about 43 ms from the pitch stage, plus your audio device's delay.
- **Texture:** the phase vocoder gives a slightly robotic, phasey sound. That is part of the effect.

## Requirements

- Windows 11 (tested). Windows 10 is untested.
- Python 3.10 or newer (tested with 3.13)
- A microphone
- VB-CABLE, a free virtual-microphone driver, for calls and other apps (see Setup)
- ffmpeg, optional, for `.m4a` and other formats the audio library can't open

## Setup

1. **Install Python.** Get it from python.org and tick **Add python.exe to PATH** in the installer.
2. **Install VB-CABLE.** Download `VBCABLE_Driver_Pack46.zip` (or the current pack) from <https://vb-audio.com/Cable/> only. Unzip it, right-click `VBCABLE_Setup_x64.exe`, and choose **Run as administrator**. Let it finish. The installer can look frozen for a few seconds. Restart the PC afterwards, because the driver needs a reboot.
   VB-CABLE is donationware by Vincent Burel. This project does not include it, and the author's license does not allow bundling it inside another installer without the author's agreement.
3. **Keep the folder path short.** Put this folder somewhere short, such as `C:\deep-voice`. Installs can fail under very long Windows paths.
4. **Run `setup.bat`** (double-click). It creates a `.venv` folder and installs `requirements.txt`.
5. **Run `run_app.bat`** (double-click). The window opens.

## Using the window

1. Set **Your microphone** to your real microphone. Set **Send voice to** to **CABLE Input** once VB-CABLE is installed. Until then, pick your headphones to hear the effect yourself.
2. Press **Start audio**.
3. Press **Ctrl+Alt+D**, or click the big button, to switch **VOICE ON** and **VOICE OFF**. When it is off, your normal voice passes through unchanged.
4. For calls and other apps, set the app's microphone to **CABLE Output (VB-Audio Virtual Cable)**. If the app has no microphone picker, set Windows' default recording device to CABLE Output (Settings, System, Sound, Input). Set it back afterwards, because that setting affects every app.
5. Choose a preset, or use the pitch slider.

Keep the window running while you want the effect. Closing the window stops the audio.

## Voice notes and recordings

- **In the window:** press **Convert a voice note or recording...**. The deep copy is saved next to the original as, for example, `note_batman.wav`.
- **From a terminal in the project folder:**

  ```
  .venv\Scripts\python.exe cli.py convert "note.opus"
  ```

  WhatsApp voice notes are `.opus` files and work directly. `.m4a` files need ffmpeg on the PATH.

## Command line

```
.venv\Scripts\python.exe cli.py devices
.venv\Scripts\python.exe cli.py convert IN [OUT] [--preset Giant] [--semitones=-6]
.venv\Scripts\python.exe cli.py preview IN [--preset Deep] [--compare]
.venv\Scripts\python.exe cli.py live [--input NAME] [--output NAME]
```

- `devices` lists audio devices.
- `convert` writes a deep WAV next to the input, or to the output path you give.
- `preview` plays the result through your speakers. `--compare` plays the original first.
- `live` runs the effect in the terminal. Press Enter to toggle, and type `q` to quit.

## Troubleshooting

- **The other person hears nothing:** the window must show audio running (Start audio pressed), and the app's microphone must be **CABLE Output**.
- **Echo or squealing:** use headphones. Speakers can feed back into the microphone.
- **The hotkey does nothing:** the window shows a message if the global hotkey can't start. Use the big button instead.
- **"An Application Control policy has blocked" errors:** a Windows security policy is blocking a Python file. Ask whoever manages the PC. Don't switch the policy off to get around it.
- **Setup fails:** check that Python is on the PATH, and that the folder path is short.
- **Startup errors:** the app writes `deep-voice-error.txt` in the project folder.
- **Work calls:** the effect applies to every app that records from CABLE Output. Turn it off, or switch back to your real microphone, for work calls.

## How it works

Microphone, then a high-pass filter (cuts rumble), then the pitch stage (a phase vocoder in [`deep_voice/dsp.py`](deep_voice/dsp.py)), then the tone chain (pedalboard: bass shelf, presence cut, drive, compressor, small reverb, gain, limiter), then the output device.

Switching the effect off plays the same voice with the same delay, so switching never jumps in time. The switch crossfades over 20 ms.

**Why not pedalboard's PitchShift?** In pedalboard 0.9.26, its output goes silent after the first block when streamed with `reset=False`. The upstream report is [spotify/pedalboard pull request 486](https://github.com/spotify/pedalboard/pull/486). Its merge status was not checked here. The pitch stage in `dsp.py` avoids that code path.

## Project layout

| Path | What it is |
|---|---|
| `app.py` | The window: switch, presets, pitch slider, devices, hotkey, file conversion |
| `cli.py` | Command-line tools |
| `deep_voice/dsp.py` | Streaming pitch shifter (phase vocoder) |
| `deep_voice/chain.py` | Presets and the tone chain |
| `deep_voice/engine.py` | On/off switch, crossfade and latency alignment |
| `deep_voice/audio.py` | Device selection and the live audio stream |
| `deep_voice/files.py` | File conversion (libsndfile, with ffmpeg as a fallback) |
| `tests/` | Unit tests |
| `setup.bat`, `run_app.bat` | Windows setup and launch |
| `requirements.txt` | Python packages |

## Tests

```
.venv\Scripts\python.exe -m unittest discover -s tests -t tests
```

The tests cover pitch accuracy, streaming equivalence, latency alignment, the on/off bypass, level matching, file conversion (WAV, Opus and m4a), device selection, and the window's basic behavior.

## Design decisions

- **Scope:** Windows PC only. The effect applies to the PC's microphone input.
- **Virtual microphone:** VB-CABLE, because it is free and is the simplest system-wide route. Alternatives are Voicemeeter (free, more setup) and Voicemod (commercial).
- **Hotkey:** Ctrl+Alt+D.
- **Default preset:** Batman. Presets are level-matched to within about 1 dB of the dry voice, so switching doesn't jump in loudness.
- **Pitch range in the window:** 0 to -12 semitones. The engine accepts down to -24.
- **Latency:** one 2048-sample frame, about 43 ms at 48 kHz.
- **CPU:** a few percent of one core in testing.

## Credits

- [VB-CABLE](https://vb-audio.com/Cable/) by Vincent Burel (donationware). Not included in this project.
- [pedalboard](https://github.com/spotify/pedalboard) by Spotify
- [sounddevice](https://python-sounddevice.readthedocs.io/) and [soundfile](https://python-soundfile.readthedocs.io/)
- [numpy](https://numpy.org/)
- [keyboard](https://github.com/boppreh/keyboard) for the global hotkey
- [ffmpeg](https://ffmpeg.org/), optional, for m4a decoding

## License

No license has been chosen yet. Until one is added, the default copyright rules apply.
