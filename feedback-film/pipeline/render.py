import json, os, sys, subprocess, time, traceback
import numpy as np
from PIL import Image
from multiprocessing import Pool
FX_ROOT = __import__("os").environ.get("FX_ROOT", "/tmp/fx")  # working folder for media, renders and caches
sys.path.insert(0, os.path.dirname(__file__))
from fx import *
from cues import cues
import scenes
import scenes_see
scenes.SCENES.update(scenes_see.SCENES)

ROOT = FX_ROOT
CTX = dict(music=f"{ROOT}/music.wav", vo=f"{ROOT}/vo2", stills=f"{ROOT}/stills", work=f"{ROOT}/work")

def load():
    tl = json.load(open(f"{ROOT}/timeline.json"))
    CTX["acts"] = tl["acts"]
    return tl

def label_layers(seg, act_font):
    out = []
    t0 = seg["beats"][0]["start"]
    for b in seg["beats"]:
        for title, sub, at in b.get("labels", []):
            if at < b["dur"] - 2:
                out.append((b["start"] - t0 + at - 0.7, label_img(title, sub, act_font)))
    return out

def frames(seg, limit=None):
    c = cues(seg)
    sc = scenes.SCENES[seg["scene"]](seg, c, CTX)
    act = CTX["acts"][seg["act"]]
    lk = sc.look or act["look"]
    look = Look(lk, seg["idx"]) if lk not in ("clean", None) else None
    labels = label_layers(seg, act["font"])
    n = seg["nf"] if limit is None else min(limit, seg["nf"])
    for fi in range(n):
        t = fi / FPS
        img = sc.frame(fi, t)
        img = upscale(img)
        if look is not None:
            img = look(img, fi)
        for lt, lab in labels:
            a = smooth((t - lt - 0.7) / 0.4) * (1 - smooth((t - lt - 6.2) / 0.5))
            if a > 0:
                img = comp(np.ascontiguousarray(img), lab, 56, 44, a)
        yield fi, img

def render_seg(seg):
    out = f"{ROOT}/segs/seg_{seg['idx']:03d}.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return seg["idx"], 0.0, "cached"
    t = time.time()
    tmp = out + ".part.mp4"
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15",
                            "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    try:
        for fi, img in frames(seg):
            enc.stdin.write(to_u8(img).tobytes())
        enc.stdin.close(); enc.wait()
        os.replace(tmp, out)
        return seg["idx"], time.time() - t, "ok"
    except Exception:
        enc.kill()
        return seg["idx"], time.time() - t, traceback.format_exc()

def test(idxs, at=2.0):
    tl = load()
    os.makedirs(f"{ROOT}/test/frames", exist_ok=True)
    for seg in tl["segs"]:
        if idxs and seg["idx"] not in idxs: continue
        try:
            n = int(min(seg["nf"] - 1, at * FPS))
            last = None
            t = time.time()
            for fi, img in frames(seg, n + 1):
                last = img
            dt = (time.time() - t) / (n + 1)
            Image.fromarray(to_u8(last)).resize((640, 360)).save(f"{ROOT}/test/frames/{seg['idx']:03d}_{seg['scene']}.png")
            print(f"{seg['idx']:3d} {seg['scene']:12s} {dt * 1000:6.0f} ms/frame", flush=True)
        except Exception:
            print(seg["idx"], seg["scene"], "FAILED"); traceback.print_exc()

def run(skip=(), only=None, procs=3):
    tl = load()
    os.makedirs(f"{ROOT}/segs", exist_ok=True)
    jobs = [s for s in tl["segs"] if s["idx"] not in skip and (only is None or s["idx"] in only)]
    jobs.sort(key=lambda s: -s["nf"])
    t = time.time()
    with Pool(procs) as p:
        for idx, dt, st in p.imap_unordered(render_seg, jobs):
            print(f"seg {idx:3d} {dt:6.1f}s {st if st in ('ok', 'cached') else 'ERROR'}  [{time.time() - t:6.0f}s]", flush=True)
            if st not in ("ok", "cached"): print(st, flush=True)

if __name__ == "__main__":
    for d in ("stills", "work", "segs"): os.makedirs(f"{ROOT}/{d}", exist_ok=True)
    if sys.argv[1] == "test":
        test([int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 and sys.argv[2] else None,
             float(sys.argv[3]) if len(sys.argv) > 3 else 2.0)
    elif sys.argv[1] == "run":
        skip = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 and sys.argv[2] else []
        only = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 and sys.argv[3] else None
        run(skip, only, int(sys.argv[4]) if len(sys.argv) > 4 else 3)
