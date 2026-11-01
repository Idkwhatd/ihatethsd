# DeepDream run on this film's own feedback tunnel, zooming in as it dreams.
import os, sys, math, json
import numpy as np, torch, torchvision
from PIL import Image
FX_ROOT = __import__("os").environ.get("FX_ROOT", "/tmp/fx")  # working folder for media, renders and caches
sys.path.insert(0, os.path.dirname(__file__))
from fx import *
import scenes

torch.set_num_threads(int(os.environ.get("DREAM_THREADS", "3")))
OUT = f"{FX_ROOT}/work/dream"; os.makedirs(OUT, exist_ok=True); os.makedirs(f"{FX_ROOT}/stills", exist_ok=True)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 170

m = torchvision.models.googlenet(weights="IMAGENET1K_V1").eval()
feats = {}
m.inception4c.register_forward_hook(lambda mod, i, o: feats.__setitem__("c", o))
m.inception4d.register_forward_hook(lambda mod, i, o: feats.__setitem__("d", o))
mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1); std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

def dream(x0, iters=6, lr=0.022, octaves=3, scale=1.45):
    base = x0
    shapes = [x0.shape[-2:]]
    for _ in range(1, octaves): shapes.append((int(shapes[-1][0] / scale), int(shapes[-1][1] / scale)))
    detail = torch.zeros(1, 3, *shapes[-1])
    for sh in reversed(shapes):
        b = torch.nn.functional.interpolate(base, size=sh, mode="bilinear", align_corners=False)
        detail = torch.nn.functional.interpolate(detail, size=sh, mode="bilinear", align_corners=False)
        x = (b + detail).requires_grad_(True)
        for _ in range(iters):
            m((x - mean) / std)
            loss = feats["d"].pow(2).mean() + 0.5 * feats["c"].pow(2).mean()
            loss.backward()
            g = x.grad
            x.data += lr * g / (g.abs().mean() + 1e-8); x.grad.zero_(); x.data.clamp_(0, 1)
        detail = (x - b).detach()
    return (base + detail).clamp(0, 1)

# Seed: the film's own feedback tunnel.
seg = dict(scene="feedback", act="noise", idx=4242, f0=0, nf=200,
           beats=[dict(p=dict(mode="mandala", spin=1.2), start=0, dur=9, vo=None, pre=0, key="d")])
fb = scenes.Feedback(seg, {}, dict(music=f"{FX_ROOT}/music.wav", acts={}))
img = None
for k in range(96):
    img = fb.frame(k, k / 24)
x = torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1)[None].float()
for k in range(N):
    p = os.path.join(OUT, f"{k:04d}.png")
    if os.path.exists(p):
        x = torch.from_numpy(np.asarray(Image.open(p), np.float32) / 255).permute(2, 0, 1)[None]
        continue
    z = 1.045
    hh, ww = x.shape[-2:]
    crop = x[..., int(hh * (1 - 1 / z) / 2): int(hh * (1 + 1 / z) / 2), int(ww * (1 - 1 / z) / 2): int(ww * (1 + 1 / z) / 2)]
    x = torch.nn.functional.interpolate(crop, size=(hh, ww), mode="bilinear", align_corners=False)
    x = dream(x)
    Image.fromarray((x[0].permute(1, 2, 0).numpy() * 255).astype(np.uint8)).save(p)
    if k == 110:
        Image.fromarray((x[0].permute(1, 2, 0).numpy() * 255).astype(np.uint8)).save(f"{FX_ROOT}/stills/dream.png")
    print("dream", k, flush=True)
print("done")
