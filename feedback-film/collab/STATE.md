# Current state

**Builder:** `claude-cloud` (session "Psychedelic video essay reminder") until handed over. Its container is temporary, so the
media and renders there can disappear; the code and docs here are the durable copy.
**Recommended builder from now on:** `claude-pc` (session "John Whitney Catalog 1961" on the user's PC), because the
user's downloaded clips and a GPU are there.

## Cut v3 — 24:07 (delivered to the user on 2026-11-01)

- Real public-domain footage (pre-1931) for acts I–III, plus Muybridge (1878) in interlude 3.
- Acts IV–VIII use code recreations for still-copyrighted works (labeled "recreated in code"); these are the 20 slots
  in `pipeline/slots.example.json`.
- Six "On seeing" interludes: 3 science (eye evolution, fish eye and colour vision, the brain builds the picture with a
  blind-spot test), 3 philosophy (Plato's cave, doors of perception, Descartes and the homunculus).
- Original generated score; narration is one short line per act plus the interludes (Kokoro voice `af_heart`).
- Known issue: one borderline flash frame at 10:45 (cut between two Vertov clips).

## Open decisions for the user

1. Portuguese (PT-BR) narration and captions, or keep English?
2. Keep 24 minutes, or trim to about 20?
3. When real clips go into slots: use their original audio, or keep the generated score under them?

## Structure (v3)

| Time | Act | Scene | Label | Kind |
| --- | --- | --- | --- | --- |
| 0:00 | open | feedback |  | feedback |
| 0:39 | open | montage |  | montage |
| 0:50 | open | title |  | title |
| 0:58 | see1 | eyeevo | On seeing 1 · The first eye | eyeevo |
| 1:35 | tricks | actcard |  | actcard |
| 1:39 | tricks | clip | The Man with the Rubber Head | real (PD) |
| 1:57 | tricks | clip | The Melomaniac | real (PD) |
| 2:17 | tricks | clip | A Trip to the Moon | real (PD) |
| 2:37 | tricks | clip | The Electric Hotel | real (PD) |
| 2:53 | tricks | clip | The Electric Hotel | real (PD) |
| 3:05 | tricks | clip | Fantasmagorie | real (PD) |
| 3:35 | see2 | fisheye | On seeing 2 · A fish's eye | fisheye |
| 4:18 | vmusic | actcard |  | actcard |
| 4:22 | vmusic | clip | Lichtspiel Opus I | real (PD) |
| 4:52 | vmusic | clip | Rhythmus 21 | real (PD) |
| 5:10 | vmusic | clip | Symphonie Diagonale | real (PD) |
| 5:34 | vmusic | clip | Lichtspiel Opus III | real (PD) |
| 5:54 | vmusic | clip | Lichtspiel Opus IV | real (PD) |
| 6:16 | vmusic | clip | Anémic Cinéma | real (PD) |
| 6:46 | vmusic | clip | Study No. 6 | real (PD) |
| 7:12 | vmusic | clip | Tusalava | real (PD) |
| 7:34 | see3 | perceive | On seeing 3 · The brain builds the picture | perceive |
| 8:16 | dreams | actcard |  | actcard |
| 8:20 | dreams | clip | Le Retour à la raison | real (PD) |
| 8:38 | dreams | clip | Ballet Mécanique | real (PD) |
| 9:04 | dreams | clip | Ballet Mécanique | real (PD) |
| 9:14 | dreams | clip | Entr'acte | real (PD) |
| 9:28 | dreams | clip | Emak-Bakia | real (PD) |
| 9:43 | dreams | clip | Ghosts Before Breakfast | real (PD) |
| 9:57 | dreams | clip | The Seashell and the Clergyman | real (PD) |
| 10:11 | dreams | clip | The Fall of the House of Usher | real (PD) |
| 10:28 | dreams | clip | Man with a Movie Camera | real (PD) |
| 10:44 | dreams | clip | Man with a Movie Camera | real (PD) |
| 11:00 | dreams | clip | Un Chien Andalou | real (PD) |
| 11:31 | dreams | black |  | black |
| 11:32 | dreams | clip | Un Chien Andalou | real (PD) |
| 11:49 | see4 | cave | On seeing 4 · The cave | cave |
| 12:18 | light | actcard |  | actcard |
| 12:22 | light | osc | Abstronic | recreation |
| 12:46 | light | dome | Vortex Concerts | recreation |
| 13:10 | light | whitney | Catalog | recreation |
| 13:30 | light | liquid | Liquid light shows | recreation |
| 13:58 | light | slitscan | 2001: A Space Odyssey | recreation |
| 14:16 | see5 | doors | On seeing 5 · The doors of perception | doors |
| 14:51 | signal | actcard |  | actcard |
| 14:55 | signal | tvwall | Exposition of Music – Electronic Television | recreation |
| 15:08 | signal | magnet | Magnet TV | recreation |
| 15:25 | signal | feedback | Video feedback | feedback |
| 15:39 | signal | colorizer | Paik–Abe Video Synthesizer | recreation |
| 15:57 | signal | beck | Direct Video Synthesizer | recreation |
| 16:13 | signal | ruttetra | Violin Power | recreation |
| 16:33 | signal | buddha | TV Buddha | recreation |
| 16:47 | cut | actcard |  | actcard |
| 16:51 | cut | pasdedeux | Pas de deux | recreation |
| 17:13 | cut | tango | Tango | recreation |
| 17:51 | cut | faces | Cry | recreation |
| 18:09 | cut | train | Star Guitar | recreation |
| 18:27 | cut | loopwalk | Come Into My World | recreation |
| 18:47 | cyber | actcard |  | actcard |
| 18:51 | cyber | psychedelia | Psychedelia | recreation |
| 19:13 | cyber | wiregrid | The Mind's Eye | recreation |
| 19:29 | cyber | mandel | Fractals | recreation |
| 19:53 | cyber | tunnel | VJ culture | tunnel |
| 20:09 | cyber | feedback | MilkDrop | recreation |
| 20:31 | cyber | flame | Electric Sheep | flame |
| 20:54 | see6 | homunculus | On seeing 6 · Who is watching? | homunculus |
| 21:40 | noise | actcard |  | actcard |
| 21:44 | noise | mosh | Datamosh | mosh |
| 22:10 | noise | dream | DeepDream | dream |
| 22:36 | noise | montage |  | montage |
| 23:07 | noise | feedback |  | feedback |
| 23:20 | epi | recipe |  | recipe |
| 23:36 | epi | crtoff |  | crtoff |
| 23:40 | epi | black |  | black |
| 23:44 | epi | credits |  | credits |