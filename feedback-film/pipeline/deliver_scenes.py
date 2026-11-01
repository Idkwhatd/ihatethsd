"""Picture-only scene renders for the PC builder (feedback-film/deliver/scenes/). No labels, no captions.
Usage: python deliver_scenes.py <out_dir>   (FX_ROOT points at the v3 working folder, which has the dream frames
and the mosh still)"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import render, scenes
from fx import to_u8, W, H, FPS, text_img
from PIL import Image

class TitleNoSub(scenes.Title):
    """The FEEDBACK title without the subtitle line, so the builder can set its own."""
    def setup(self):
        super().setup()
        self.sub = Image.new("RGBA", (4, 4), (0, 0, 0, 0))

scenes.SCENES["title"] = TitleNoSub  # same cues as the v3 title, minus the subtitle

def seg(name, scene, act, beats, idx):
    t, bl = 0.0, []
    for i, (dur, p) in enumerate(beats):
        bl.append(dict(key=f"{name}_{i}", act=act, scene=scene, p=p, labels=[], text="", vo=None, pre=0.0,
                       start=t, dur=dur, f0=int(round(t * FPS)), nf=int(round(dur * FPS)), cont=i > 0, grow=0))
        t += dur
    return dict(scene=scene, act=act, idx=idx, f0=0, nf=int(round(t * FPS)), beats=bl)

MONTAGE = ["clip:anemic:120", "clip:rubber:80", "clip:opus4:140", "clip:chien:88", "clip:ballet:390", "tango",
           "psychedelia", "mosh_still", "clip:tusalava:300", "flame"]

JOBS = [
    ("open_tunnel", seg("open_tunnel", "feedback", "signal", [(24, dict(mode="tunnel", spin=0.4)), (21, dict(mode="mandala", spin=2.0))], 0)),
    ("title", seg("title", "title", "open", [(9, {})], 3)),
    ("noise_mosh", seg("noise_mosh", "mosh", "noise", [(26, {})], 60)),
    ("noise_dream", seg("noise_dream", "dream", "noise", [(26, {})], 61)),
    ("noise_montage", seg("noise_montage", "montage", "noise", [(31, dict(items=MONTAGE, step=3.1))], 62)),
    ("noise_mandala", seg("noise_mandala", "feedback", "noise", [(7, dict(mode="mandala", spin=1.0)), (6, dict(mode="tunnel", spin=0.4))], 63)),
    ("epi_tunnel", seg("epi_tunnel", "feedback", "epi", [(20, dict(mode="tunnel", spin=0.3)), (20, dict(mode="mandala", spin=0.9))], 64)),
    ("crt_off", seg("crt_off", "crtoff", "epi", [(4, {})], 65)),
]

def main(out):
    render.load()
    os.makedirs(out, exist_ok=True)
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    for name, s in JOBS:
        if only and name not in only: continue
        path = os.path.join(out, name + ".mp4")
        enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                                "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
        for fi, img in render.frames(s):
            enc.stdin.write(to_u8(img).tobytes())
        enc.stdin.close(); enc.wait()
        print("scene", name, s["nf"] / FPS, flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
