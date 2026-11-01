import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from script import SCRIPT, ACTS

FPS = 24
TARGET = 1214.0  # 20:14 (Pas de deux added)

def build(vo_dir):
    meta = json.load(open(f"{vo_dir}/meta.json"))
    beats = []
    for act, bl in SCRIPT:
        for bi, b in enumerate(bl):
            key = f"{act}_{bi:02d}"
            vo = meta.get(key) if b["text"] else None
            dur = b["dur"]
            if vo:
                dur = max(dur, b["at"] + vo["dur"] + 0.8 + b.get("hold", 0.0))
            beats.append(dict(key=key, act=act, scene=b["scene"], cont=b["cont"], labels=b["labels"], p=b["p"],
                              text=b["text"], dur=dur, grow=b["grow"], pre=b["at"], vo=vo))
    total = sum(x["dur"] for x in beats)
    target = TARGET + sum(x["dur"] for x in beats if x["act"].startswith("see"))
    gw = sum(x["grow"] for x in beats)
    for x in beats:
        x["dur"] += (target - total) * x["grow"] / gw
    t = 0
    for x in beats:
        n = round(x["dur"] * FPS)
        x["f0"], x["nf"] = t, n
        x["start"], x["dur"] = t / FPS, n / FPS
        t += n
    segs = []
    for x in beats:
        if x["cont"] and segs:
            segs[-1]["beats"].append(x)
        else:
            segs.append(dict(scene=x["scene"], act=x["act"], beats=[x]))
    for i, s in enumerate(segs):
        s["idx"] = i
        s["f0"] = s["beats"][0]["f0"]
        s["nf"] = sum(b["nf"] for b in s["beats"])
    caps = []
    for x in beats:
        if x["vo"]:
            for s in x["vo"]["sents"]:
                caps.append(dict(text=s["text"], start=x["start"] + x["pre"] + s["start"], end=x["start"] + x["pre"] + s["end"]))
    return dict(fps=FPS, total=t / FPS, beats=beats, segs=segs, caps=caps, acts=ACTS)

if __name__ == "__main__":
    tl = build(sys.argv[1])
    json.dump(tl, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print("total %.1f s, %d beats, %d segments, %d captions" % (tl["total"], len(tl["beats"]), len(tl["segs"]), len(tl["caps"])))
    for s in tl["segs"]:
        b = s["beats"][0]
        print("%3d %-7s %-12s %7.1f %5.1f %s" % (s["idx"], s["act"], s["scene"], s["f0"] / FPS, s["nf"] / FPS, b["p"].get("film", "")))
