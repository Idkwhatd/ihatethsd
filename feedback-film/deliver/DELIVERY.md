# Hand-off from claude-cloud to the PC builder

Requested by claude-pc on 2026-11-01. Everything here is original or public domain.

## 1. "On seeing" interludes — `interludes/`

Picture only (no narration, no score, no label overlays), **1280×720**, 24 fps, H.264 (CRF 16). The pipeline draws at
1280×720 natively; upscale to 1080p in your edit if needed (Lanczos). Re-rendering at native 1080p would mean redrawing
every scene, so I didn't.

| Plays | File | Length | Stretch vs v3 |
| --- | --- | --- | --- |
| before I. RAZOR | `see1_picture.mp4` | 48 s | 1.27× |
| before II. DREAM | `see3_picture.mp4` | 54 s | 1.26× |
| before III. VISUAL MUSIC | `see2_picture.mp4` | 54 s | 1.28× |
| before IV | `see4_picture.mp4` | 36 s | 1.21× |
| before V | `see5_picture.mp4` | 38 s | 1.10× |
| before VIII | `see6_picture.mp4` | 58 s | 1.27× |

The animations follow the narration: each visual stage starts on a sentence. To lengthen the interludes, I stretched
every sentence time by the same factor, so **the new narration should start each sentence at the `start` times in
`interludes/cues.json`**. Those are the moments the picture changes: eye stages, fish → eye → colour chart, saccades →
blind-spot test → Muybridge, cave → shadows → "first movie theater", Blake → Huxley → Osmond → doors open on
"Psychedelic", and Descartes → regress zoom → feedback → "the brain predicts the picture".

- `*_narration_ref.wav` — the current voice placed at those re-timed starts, for timing only.
- `*_score_ref.flac` — the interlude cue regenerated at the new length, for reference.
- `cues.json` — per interlude: duration, sentence text with start/end, and the label text I removed from the picture
  (for example "The Horse in Motion · Eadweard Muybridge, 1878"), so you can set titles in your own style.
- Text inside the picture stays: stage names, "≈ 364,000 generations · Nilsson & Pelger, 1994", the blind-spot
  instructions, the Blake/Huxley/Osmond cards, "PSYCHEDELIC", and "the brain predicts the picture".

## 2. Score — `score/`

`v3_<act>.flac` is the v3 score for each v3 chapter, for reference (spans in `v3_spans.json`). Mapping to the new
chapters: `v3_dreams` (slow waltz; its Buñuel cue cuts to silence with the picture) suits I. RAZOR and II. DREAM;
`v3_vmusic` (minimalist marimba pulse) suits III. VISUAL MUSIC; `v3_tricks` (ragtime stride) goes with the optional
trick films. `v3_light`,
`v3_signal`, `v3_cut`, `v3_cyber` and `v3_noise` follow their v3 chapters, whose recreations differ from your real clips.

## 3. Early acts EDL — `early_acts_edl.json`

Source in/out points (seconds) for I. RAZOR / II. DREAM / III. VISUAL MUSIC against `pipeline/footage_list.json`; fetch
the sources with `pipeline/fetch_footage.py`. RAZOR follows the treatment (Buñuel, Dulac); the Méliès/Chomón/Cohl trick
films sit under `optional_trick_films` until the user places them. 26 cuts in total, all used in v3 and flash-checked, plus 12 unchecked alternates.
Two entries use `ranges` (two stretches back to back) to skip strobing passages. Notes per cut flag what to avoid:
the moment the razor touches the eye, the caricature dolls in *Entr'acte*, and the flicker in *Ballet Mécanique*,
*Le Retour à la raison* and Fischinger's *Study No. 6*.

Run `pipeline/flashcheck.py` on the finished cut. It flags any second with more than three large flashes.
