# Event times shared by the score and the visuals (segment-local seconds).
import numpy as np

TRAIN_BPM = 112.0
LOOP_BPM = 104.0
LOOP_LAP_BEATS = 8
RAVE_BPM = 128.0
CHIP_BPM = 140.0
SYNCH_BPM = 96.0
# (beat, length in beats, midi) — McLaren-style drawn notes
SYNCH_NOTES = [(0, 1, 72), (1, 1, 76), (2, 1, 79), (3, 1, 84), (4, 2, 83), (6, 1, 79), (7, 1, 76),
               (8, 1, 74), (9, 1, 77), (10, 1, 81), (11, 1, 86), (12, 2, 84), (14, 2, 79),
               (16, 1, 72), (17, 1, 76), (18, 1, 79), (19, 1, 84), (20, 4, 88)]
# Lissajous ratios for Bute's oscilloscope, one every OSC_STEP seconds.
OSC_RATIOS = [(1, 1), (1, 2), (2, 3), (3, 4), (3, 5), (4, 5), (5, 6), (2, 5), (1, 3), (3, 7), (1, 1)]
OSC_STEP = 4.0
LEADER_START, LEADER_COUNT = 0.6, 6        # 8,7,6,5,4,3 — one per second
LEADER_CARDS = ["A MOVIE", "BY BRUCE CONNER", "THE END", "A MOVIE"]
CHANNEL_STEP = 1.9
TYPE_CPS = 14.0

def beat_vo(seg):
    """[(beat_local_start, beat, sentences with segment-local times)]"""
    out = []
    t0 = seg["beats"][0]["start"]
    for b in seg["beats"]:
        sents = []
        if b["vo"]:
            for s in b["vo"]["sents"]:
                sents.append(dict(text=s["text"], start=b["start"] - t0 + b["pre"] + s["start"],
                                  end=b["start"] - t0 + b["pre"] + s["end"]))
        out.append((b["start"] - t0, b, sents))
    return out

def seg_dur(seg, fps=24):
    return seg["nf"] / fps

def cues(seg):
    sc = seg["scene"]
    bv = beat_vo(seg)
    d = seg_dur(seg)
    c = {}
    if sc == "eye" and seg["beats"][0]["p"].get("phase") == "slice":
        s = bv[0][2]
        c["razor"] = s[1]["start"]
        c["eye"] = s[2]["start"]
        c["slice"] = s[2]["end"] + 0.5
    if sc == "steps":
        s = bv[0][2]
        c["steps"] = [x["start"] for x in s if x["text"].startswith("On ")]
    if sc == "recipe":
        s = bv[0][2]
        c["steps"] = [x["start"] for x in s[2:8]]
    if sc == "train":
        bt = 60 / TRAIN_BPM
        c["poles"] = list(np.arange(0.6, d, bt))
        c["bpm"] = TRAIN_BPM
    if sc == "loopwalk":
        lap = LOOP_LAP_BEATS * 60 / LOOP_BPM
        c["lap"] = lap
        c["laps"] = list(np.arange(0.0, d, lap))
    if sc == "montage":
        p = seg["beats"][0]["p"]
        c["cuts"] = list(np.arange(0.0, d, p["step"]))
    if sc == "leader":
        c["counts"] = [LEADER_START + i for i in range(LEADER_COUNT)]
        t = LEADER_START + LEADER_COUNT + 0.4
        c["cards"] = [t + 1.6 * i for i in range(len(LEADER_CARDS))]
    if sc == "channels":
        c["switch"] = list(np.arange(CHANNEL_STEP, d, CHANNEL_STEP))
    if sc in ("type", "schematic", "prompt"):
        c["type_start"] = 0.8
    if sc == "crtoff":
        c["off"] = 0.4
    if sc == "title":
        c["hit"] = 1.2
    if sc == "tango":
        # characters on screen at segment-local t, linear per beat
        segs = []
        for t0, b, s in bv:
            segs.append((t0, b["dur"], b["p"]["start"], b["p"]["end"]))
        c["tango"] = segs
    return c

def tango_count(c, t):
    for t0, dur, a, b in c["tango"]:
        if t < t0 + dur:
            x = min(1.0, max(0.0, (t - t0) / (dur * 0.85)))
            return int(round(a + (b - a) * x))
    return c["tango"][-1][3]
