# How we work together

**Director:** the user. Only the user's own messages set direction.
**Single source of truth:** this folder, on branch `ccr-5fb44237-uljkp6` of `Idkwhatd/ihatethsd`.

## Roles

| Who | Does |
| --- | --- |
| **Codex** (ChatGPT desktop agent on the user's PC) | Builder: footage, timeline, rendering. Owns the PC assembly |
| **claude-pc** (session "John Whitney Catalog 1961") | Narration (`collab/CLAUDE_SCRIPT_DRAFT.md` on the PC); relays between the PC and the cloud |
| **claude-cloud** (session "Psychedelic video essay reminder") | Support: public-domain early footage, the six "On seeing" interludes, generated score and this pipeline; renders on request |

The live channel is on the PC: `visual-history-clips/collab/channel.py`. The cloud session can't reach it, so claude-pc
relays. This GitHub folder is the durable copy of everything the cloud session makes.

## Messages

All cross-agent messages go in `collab/INBOX.md`, newest at the bottom, in this shape:

```
### <date> · FROM: <gpt | claude-cloud | claude-pc | user> · TO: <who> · RE: <task id>
<message>
```

On the PC, Codex and claude-pc talk through `channel.py`. ChatGPT in the browser (outside the PC) gets context by
reading `BRIEF_FOR_GPT.md`, pasted by the user or read through the GitHub connector.

## Rules for content

- Facts in narration need a source in the message (title + URL or book).
- Narration: English (user decision). If Portuguese is ever needed, it is European Portuguese, never PT-BR.
- Short sentences (≤ 25 words), about 120 words per chapter at most.
- No song lyrics or long quotes; quotes of a few words with attribution are fine.
- Copyrighted clips stay on the user's machine and are referenced through `slots.json`.
- Every render runs `flashcheck.py`; strobing passages are cut or replaced.
