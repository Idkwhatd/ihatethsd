"""Build the hand-off package for the PC builder (feedback-film/deliver/).

- interludes/: the six "On seeing" interludes, picture only, re-timed to the requested lengths, no label overlays
- interludes/*_narration_ref.wav: the current narration placed at the re-timed sentence starts (timing reference)
- interludes/*_score_ref.flac: the interlude score generated at the new length (reference)
- score/: v3 score per chapter (reference)
- interludes/cues.json: sentence text + re-timed start/end, on-screen label text
Usage: python deliver.py <out_dir>   (FX_ROOT points at the v3 working folder)
"""
import copy, json, os, subprocess, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
FX_ROOT = os.environ.get("FX_ROOT", "/tmp/fx")
import render
from fx import to_u8, W, H, FPS

TARGET = {"see1": 48.0, "see3": 54.0, "see2": 54.0, "see4": 36.0, "see5": 38.0, "see6": 58.0}  # play order
SR = 48000

def retime(seg, new_dur):
    s = copy.deepcopy(seg)
    k = new_dur / (seg["nf"] / FPS)
    t0 = seg["beats"][0]["start"]
    f = s["f0"]
    for b in s["beats"]:
        b["start"] = t0 + (b["start"] - t0) * k
        b["pre"] *= k
        b["dur"] *= k
        b["labels"] = []
        if b["vo"]:
            for x in b["vo"]["sents"]:
                x["start"] *= k; x["end"] *= k
    s["nf"] = int(round(new_dur * FPS))
    # beat frame counts follow the new starts
    starts = [round((b["start"] - t0) * FPS) for b in s["beats"]] + [s["nf"]]
    for i, b in enumerate(s["beats"]):
        b["f0"] = f + starts[i]; b["nf"] = starts[i + 1] - starts[i]
    return s, k

def encode(seg, path):
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    for fi, img in render.frames(seg):
        enc.stdin.write(to_u8(img).tobytes())
    enc.stdin.close(); enc.wait()

def narration_ref(seg, old, k, path):
    out = np.zeros(int(seg["nf"] / FPS * SR) + SR)
    for b_new, b_old in zip(seg["beats"], old["beats"]):
        if not b_old["vo"]:
            continue
        x, sr = sf.read(os.path.join(FX_ROOT, "vo2", b_old["key"] + ".wav"))
        x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x)
        for s_new, s_old in zip(b_new["vo"]["sents"], b_old["vo"]["sents"]):
            a, z = int(s_old["start"] * SR), int(s_old["end"] * SR)
            i = int((b_new["start"] - seg["beats"][0]["start"] + b_new["pre"] + s_new["start"]) * SR)
            piece = x[a:z]
            out[i:i + len(piece)] += piece[: len(out) - i]
    sf.write(path, (out[: int(seg["nf"] / FPS * SR)] * 0.9).astype(np.float32), SR, subtype="PCM_16")

def score_ref(seg, path):
    import music2 as M2
    import music as M
    t0 = seg["f0"] / FPS; d = seg["nf"] / FPS
    L = M2.Local(t0, d, tail=0.0)
    M2.m_seeing(L, t0, d, seg, {})
    x = M.reverb(L.x[: M.N(d)], 2.2, 0.28)
    x = x / (np.abs(x).max() + 1e-9) * 0.8
    sf.write(path, x.astype(np.float32), SR, format="FLAC", subtype="PCM_16")

def main(out):
    tl = json.load(open(os.path.join(FX_ROOT, "timeline.json")))
    render.load()
    os.makedirs(os.path.join(out, "interludes"), exist_ok=True); os.makedirs(os.path.join(out, "score"), exist_ok=True)
    cues = {}
    for act, new_dur in TARGET.items():
        old = next(s for s in tl["segs"] if s["act"] == act)
        seg, k = retime(old, new_dur)
        base = os.path.join(out, "interludes", act)
        encode(seg, base + "_picture.mp4")
        narration_ref(seg, old, k, base + "_narration_ref.wav")
        score_ref(seg, base + "_score_ref.flac")
        t0 = seg["beats"][0]["start"]
        cues[act] = dict(duration=new_dur, scene=seg["scene"], stretch=round(k, 4),
                         labels=[dict(title=l[0], sub=l[1]) for b in old["beats"] for l in b["labels"]],
                         sentences=[dict(text=x["text"], start=round(b["start"] - t0 + b["pre"] + x["start"], 2),
                                         end=round(b["start"] - t0 + b["pre"] + x["end"], 2))
                                    for b in seg["beats"] if b["vo"] for x in b["vo"]["sents"]])
        print("interlude", act, new_dur, "stretch", round(k, 3), flush=True)
    json.dump(cues, open(os.path.join(out, "interludes", "cues.json"), "w"), indent=1, ensure_ascii=False)
    # v3 score per chapter, for reference
    mus, sr = sf.read(os.path.join(FX_ROOT, "music.wav"))
    spans = {}
    for s in tl["segs"]:
        a = s["act"]; t = s["f0"] / FPS; e = t + s["nf"] / FPS
        spans[a] = (min(spans.get(a, (t, e))[0], t), max(spans.get(a, (t, e))[1], e))
    for a, (t, e) in spans.items():
        if a.startswith("see"): continue
        sf.write(os.path.join(out, "score", f"v3_{a}.flac"), mus[int(t * sr):int(e * sr)].astype(np.float32), sr, format="FLAC", subtype="PCM_16")
    json.dump({a: dict(start=round(t, 2), end=round(e, 2)) for a, (t, e) in spans.items()}, open(os.path.join(out, "score", "v3_spans.json"), "w"), indent=1)
    print("done")

if __name__ == "__main__":
    main(sys.argv[1])
