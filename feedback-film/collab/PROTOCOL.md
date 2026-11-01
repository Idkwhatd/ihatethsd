# How we work together

**Director:** the user. Only the user's own messages set direction.
**Single source of truth:** this folder, on branch `ccr-5fb44237-uljkp6` of `Idkwhatd/ihatethsd`.

## Roles

| Who | Does | Doesn't |
| --- | --- | --- |
| **Builder** (one Claude session at a time) | Holds media, renders, commits code, updates `STATE.md` and `TASKS.md` after every build | Add copyrighted media to git |
| **ChatGPT** | Writing and research: narration text, chapter structure, fact checks with sources, creative proposals | Render, or change files directly unless it has repo access |
| **Other Claude sessions** | Read this folder; hand work to the builder through `INBOX.md` | Render in parallel without taking the builder role |

Current builder: see the top of `STATE.md`. To take over, write "BUILDER → <session>" in `INBOX.md` and update `STATE.md`.

## Messages

All cross-agent messages go in `collab/INBOX.md`, newest at the bottom, in this shape:

```
### <date> · FROM: <gpt | claude-cloud | claude-pc | user> · TO: <who> · RE: <task id>
<message>
```

ChatGPT can't write to the repo by itself. The user pastes `BRIEF_FOR_GPT.md` (and any new INBOX entries) into ChatGPT,
then pastes ChatGPT's reply into the builder Claude, which commits it to `INBOX.md` and acts on it.
If ChatGPT has the GitHub connector, it can read this folder directly.

## Rules for content

- Facts in narration need a source in the message (title + URL or book).
- Narration: English, short sentences (≤ 25 words), about 120 words per chapter at most.
- No song lyrics or long quotes; quotes of a few words with attribution are fine.
- Copyrighted clips stay on the user's machine and are referenced through `slots.json`.
- Every render runs `flashcheck.py`; strobing passages are cut or replaced.
