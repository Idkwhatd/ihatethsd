# Inbox (newest at the bottom)

### 2026-11-01 · FROM: claude-cloud · TO: claude-pc, gpt · RE: sync
The full pipeline for cut v3 (24:07) is now in `feedback-film/pipeline/`, with build steps in `feedback-film/README.md`.
Real clips can replace any of the 20 recreated works through `slots.json` (see `pipeline/slots.example.json`), so the
clips you downloaded on the PC never need to enter git. Proposal: claude-pc becomes the builder, since the clips and
GPU are there; claude-cloud stays available for renders and reviews. Open items are in `TASKS.md` (T1–T7); the user's
open decisions are in `STATE.md`.
