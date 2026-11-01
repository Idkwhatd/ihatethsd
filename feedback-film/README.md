# FEEDBACK — a video essay on psychedelic and surreal video

A school video essay (currently **v3, 24:07**, 1280×720, 24 fps, English narration with burned-in captions).
Everything needed to rebuild it lives here except media: footage, renders and the final MP4 stay out of git.

- `collab/` — how Claude sessions and ChatGPT work together: **start with `collab/PROTOCOL.md`**.
- `pipeline/` — the code that builds the film.
- `outputs/` — small build artifacts from the current cut (timeline, captions, archive metadata).

## Build (from scratch)

Working folder for media and renders: `export FX_ROOT=/some/folder` (defaults to `/tmp/fx`).

| Step | Command (run inside `pipeline/`) | Notes |
| --- | --- | --- |
| 1 | `python fetch_footage.py` | Public-domain films (all first published before 1931) from the Internet Archive, ~2.7 GB |
| 2 | `python tts.py $FX_ROOT/vo2` | Kokoro TTS, voice `af_heart`. Needs its own venv (Python 3.12, `kokoro`, `numpy==1.26.4`, `scipy<1.15`, spaCy `en_core_web_sm`) |
| 3 | `python timeline.py $FX_ROOT/vo2 $FX_ROOT/timeline.json` | Beat timing; other segments keep their length when beats are added |
| 4 | `python music2.py $FX_ROOT/timeline.json $FX_ROOT/music.wav` | Whole score is generated in code |
| 5 | `python dream.py 170` | DeepDream frames (PyTorch + torchvision GoogLeNet) |
| 6 | `python render.py run "" "" 4` | Renders `$FX_ROOT/segs/seg_NNN.mp4`; existing files are reused, delete one to re-render it. Render the mosh segment before the montage that uses its still |
| 7 | `python mix.py $FX_ROOT/timeline.json $FX_ROOT/music.wav $FX_ROOT/vo2 $FX_ROOT/mix.wav $FX_ROOT/captions.ass $FX_ROOT/captions.srt` | Narration ducking, loudness −16 LUFS, two-line captions |
| 8 | `sh assemble.sh /path/FEEDBACK.mp4` | Concatenate, burn captions, encode |
| 9 | `python flashcheck.py /path/FEEDBACK.mp4` | Photosensitivity screen (flags >3 large flashes per second) |

Main env (Python 3.12): `numpy pillow scipy soundfile torch torchvision`. FFmpeg with libx264 and libass.

## Swapping in real clips

Copy `pipeline/slots.example.json` to `$FX_ROOT/slots.json`, fill `file` (absolute path) and `start` (seconds) for any
recreated work, then rebuild from step 3. The clip plays for the slot's length, its label loses "recreated in code",
and the generated score plays under it (clip audio is not used yet). Clip files never go in git.
