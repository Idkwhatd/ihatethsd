import math, os, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import soundfile as sf
from fx import *
from cues import *

C64 = np.array([[0, 0, 0], [255, 255, 255], [136, 57, 50], [103, 182, 189], [139, 63, 150], [85, 160, 73],
                [64, 49, 141], [191, 206, 114], [139, 84, 41], [87, 66, 0], [184, 105, 98], [80, 80, 80],
                [120, 120, 120], [148, 224, 137], [120, 105, 196], [159, 159, 159]], np.float32) / 255

class Scene:
    res = "small"
    look = None
    def __init__(self, seg, c, ctx):
        self.seg, self.c, self.ctx = seg, c, ctx
        self.p = seg["beats"][0]["p"]
        self.d = seg["nf"] / FPS
        self.bv = beat_vo(seg)
        self.rng = np.random.default_rng(seg.get("idx", 0) * 7 + 1)
        self.setup()
    def setup(self): pass
    def beat(self, t):
        i = 0
        for k, (t0, b, s) in enumerate(self.bv):
            if t >= t0: i = k
        t0, b, s = self.bv[i]
        return i, t - t0, b
    def sents(self, i=0): return self.bv[i][2]

# ---------------- feedback ----------------
class Feedback(Scene):
    def setup(self):
        self.buf = np.zeros((h, w, 3), np.float32)
        self.x, self.y = grid(w, h)
        self.cx, self.cy = w / 2, h / 2
        self.hue = 0.0
        self.music = None
        self.text_seed = None
        if self.p.get("mode") == "milkdrop":
            x, sr = sf.read(self.ctx["music"], start=int(self.seg["f0"] / FPS * 48000), frames=int(self.d * 48000) + 48000)
            self.music = x.mean(1).astype(np.float32); self.msr = sr
    def seed(self, mode, t, fi):
        s = np.zeros((h, w, 3), np.float32)
        b = 3
        edge = 0.55 if mode != "dim" else 0.35
        s[:b] += edge; s[-b:] += edge; s[:, :b] += edge; s[:, -b:] += edge
        ang = t * 0.9
        px = self.cx + 120 * math.cos(ang) + 30 * math.sin(t * 2.3); py = self.cy + 70 * math.sin(ang * 1.3)
        g = np.exp(-(((self.x - px) ** 2 + (self.y - py) ** 2) / (2 * 14 ** 2)))[..., None]
        col = hsv2rgb(np.array(t * 0.05 + 0.55), np.array(0.6), np.array(1.0))
        s += g * col * (0.9 if mode != "dim" else 0.5)
        if mode == "milkdrop" and self.music is not None:
            i0 = int(fi / FPS * self.msr)
            wv = self.music[i0:i0 + 2048]
            if len(wv) < 2048: wv = np.pad(wv, (0, 2048 - len(wv)))
            xs = np.linspace(40, w - 40, 512).astype(np.int32)
            ys = (self.cy + np.interp(np.linspace(0, 2047, 512), np.arange(2048), wv) * 260).astype(np.int32)
            ys = np.clip(ys, 2, h - 3)
            colw = hsv2rgb(np.array(t * 0.11), np.array(0.8), np.array(1.0))
            for dy in (-1, 0, 1):
                s[ys + dy, xs] = colw
        if self.text_seed is not None:
            s += self.text_seed
        return s
    def frame(self, fi, t):
        i, bt, b = self.beat(t)
        p = b["p"]; mode = p.get("mode", "tunnel"); spin = p.get("spin", 0.5)
        th = math.radians(spin * (0.6 + 0.4 * math.sin(t * 0.21)))
        k = 1.055 + 0.01 * math.sin(t * 0.37)
        if mode == "milkdrop":
            r = np.sqrt((self.x - self.cx) ** 2 + (self.y - self.cy) ** 2) / 400
            thr = th + 0.04 * (1 - r)
            ca, sa = np.cos(thr), np.sin(thr)
            k = 1.04
        else:
            ca, sa = math.cos(th), math.sin(th)
        dx, dy = (self.x - self.cx) * k, (self.y - self.cy) * k
        sx = ca * dx - sa * dy + self.cx; sy = sa * dx + ca * dy + self.cy
        prev = bilinear(self.buf, sx, sy, 0.0)
        if mode in ("mandala", "milkdrop"):
            prev = np.maximum(prev, prev[:, ::-1] * 0.92)
        if mode in ("mandala", "offon", "milkdrop", "crt"):
            a = 0.035 if mode != "crt" else 0.0
            ca2, sa2 = math.cos(a * 6.28), math.sin(a * 6.28)
            m = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], np.float32) * ca2 + (1 - ca2) / 3 + np.array(
                [[0, -1, 1], [1, 0, -1], [-1, 1, 0]], np.float32) * sa2 / math.sqrt(3)
            prev = prev @ m.T
        gain = 0.93 if mode != "dim" else 0.9
        self.buf = np.clip(prev * gain + self.seed(mode, t, fi), 0, 1.4)
        out = np.clip(self.buf, 0, 1)
        if mode == "offon":
            lum = out @ np.array([0.33, 0.33, 0.33], np.float32)
            out = hsv2rgb(lum * 1.6 + t * 0.07, np.full_like(lum, 0.85), np.clip(lum * 1.5, 0, 1))
        if mode == "crt":
            lum = out @ np.array([0.3, 0.5, 0.2], np.float32)
            out = lum[..., None] * np.array([0.75, 1.0, 0.85], np.float32)
        if self.seg["idx"] == 0 and t < 3:
            out = out * smooth(t / 3)
        if mode == "dim":
            out = out * 0.75
        return out

# ---------------- title ----------------
class Title(Feedback):
    def setup(self):
        super().setup()
        im = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(im)
        f = font("inter_x", 92)
        bb = d.textbbox((0, 0), "FEEDBACK", font=f)
        d.text(((w - bb[2]) / 2, (h - bb[3]) / 2 - 12), "FEEDBACK", font=f, fill=255)
        self.mask = to_f(im)[..., None]
        self.big = text_img("FEEDBACK", "inter_x", 184)
        self.sub = text_img("a short history of psychedelic & surreal video", "inter_l", 34, fill=(235, 235, 235, 255))
        self.p = dict(mode="mandala", spin=1.2)
    def frame(self, fi, t):
        hit = self.c["hit"]
        self.text_seed = self.mask * np.array([1.0, 0.85, 0.6], np.float32) * (0.7 if t < hit else 0.25)
        self.seg["beats"][0]["p"] = dict(mode="mandala", spin=1.2)
        out = super().frame(fi, t)
        out = upscale(out) * (0.55 if t > hit else 1.0)
        a = smooth((t - hit) / 0.8)
        comp_center(out, self.big, W / 2, H / 2 - 30, a)
        comp_center(out, self.sub, W / 2, H / 2 + 95, smooth((t - hit - 1.0) / 1.0))
        return out * (1 - smooth((t - (self.d - 0.8)) / 0.8))
    res = "full"

# ---------------- act card ----------------
class ActCard(Scene):
    res = "full"
    def setup(self):
        act = self.seg["act"]
        from script import ACTS
        num, word, years = ACTS[act]["title"]
        self.act = act
        style = dict(
            tricks=("serif", "serif_b", (240, 232, 210), (8, 6, 4)),
            vmusic=("serif", "serif_b", (255, 214, 150), (10, 8, 18)),
            dreams=("serif_i", "serif_i", (236, 230, 220), (0, 0, 0)),
            light=("inter_l", "inter_x", (255, 214, 150), (12, 6, 20)),
            signal=("mono", "mono_b", (150, 255, 170), (4, 12, 8)),
            cut=("inter_xb", "inter_x", (255, 255, 255), (220, 20, 110)),
            cyber=("pixel", "pixel", (120, 105, 196), (64, 49, 141)),
            noise=("mono", "mono_b", (240, 240, 240), (8, 8, 10)),
        )[act]
        self.bg = np.array(style[3], np.float32) / 255
        col = style[2] + (255,)
        self.num = text_img(num, style[0], 40, fill=col)
        self.word = text_img(word, style[1], 150 if act not in ("cyber", "vmusic") else 128, fill=col)
        self.years = text_img(years, style[0], 30, fill=col[:3] + (200,))
    def frame(self, fi, t):
        out = np.ones((H, W, 3), np.float32) * self.bg
        if self.act == "cyber":
            out[:] = C64[14]
            out[60:H - 60, 80:W - 80] = C64[6]
        jit = 0
        if self.act == "noise" and int(t * 6) % 5 == 0:
            jit = int(self.rng.integers(-14, 14))
        comp_center(out, self.num, W / 2, H / 2 - 120, 1)
        comp_center(out, self.word, W / 2 + jit, H / 2, 1)
        comp_center(out, self.years, W / 2, H / 2 + 115, 1)
        if self.act == "cyber" and int(t * 2) % 2 == 0:
            out[H - 160:H - 132, 120:140] = C64[14]
        f = smooth(t / 0.4) * (1 - smooth((t - self.d + 0.4) / 0.4))
        return out * f

# ---------------- montage ----------------
class Montage(Scene):
    def setup(self):
        self.items = self.p["items"]; self.step = self.p["step"]; self.cur = None; self.cur_k = -1
    def make(self, name):
        if name.startswith("clip:"):
            _, film, st = name.split(":")
            fake = dict(scene="clip", act=self.seg["act"], idx=self.seg["idx"] * 100 + self.cur_k, f0=self.seg["f0"],
                        nf=int(self.step * FPS) + 2,
                        beats=[dict(p=dict(film=film, start=float(st), nofade=True), start=0.0, dur=self.step + 0.1, vo=None, pre=0.0, key="m")])
            sc = Clip(fake, {}, self.ctx); sc.toff = 0.0; sc.look = "clean"
            return sc
        cfg = dict(
            eye_slice=("eye", dict(phase="slice_static")), eye_moon=("eye", dict(phase="moon")),
            harmonograph=("harmonograph", {}), slitscan=("slitscan", {}), buddha=("buddha", {}),
            tango=("tango", dict(start=20, end=30)), psychedelia=("psychedelia", {}), flame=("flame", {}),
            liquid=("liquid", {}), door=("door", dict(open_at=0.0)), steps=("steps", dict(static=True)),
            direct=("direct", dict(mode="projected")), osc=("osc", {}), faces=("faces", {}), train=("train", {}),
            loopwalk=("loopwalk", {}), magnet=("magnet", {}), ruttetra=("ruttetra", {}),
            mosh_still=("still", dict(path="mosh")), dream_still=("still", dict(path="dream")),
        )[name]
        fake = dict(scene=cfg[0], act=self.seg["act"], idx=self.seg["idx"] * 100 + self.cur_k, f0=self.seg["f0"],
                    nf=int(self.step * FPS) + 2,
                    beats=[dict(p=cfg[1], start=0.0, dur=self.step + 0.1, vo=None, pre=0.0, key="m")])
        c = cues(fake)
        if cfg[0] == "tango":
            c["tango"] = [(0, 999, 18, 30)]
        sc = SCENES[cfg[0]](fake, c, self.ctx)
        sc.toff = dict(harmonograph=6.0, slitscan=3.0, flame=2.0, liquid=4.0, osc=5.0, train=2.0, loopwalk=12.0,
                       psychedelia=4.0, tango=0.0, ruttetra=8.0, faces=0.5).get(name, 0.0)
        return sc
    def frame(self, fi, t):
        k = min(int(t / self.step), 10 ** 6)
        if k != self.cur_k:
            self.cur_k = k
            self.cur = self.make(self.items[k % len(self.items)])
            self.cur_f0 = fi
            pre = int(getattr(self.cur, "toff", 0) * FPS)
            for j in range(pre):  # warm up stateful scenes
                if getattr(self.cur, "stateful", False):
                    self.cur.frame(j, j / FPS)
            self.pre = pre
        lf = fi - self.cur_f0 + self.pre
        img = self.cur.frame(lf, lf / FPS)
        img = upscale(img)
        lk = self.cur.look or self.ctx["acts"][self.seg["act"]]["look"]
        if lk in ("film_bw", "film_color") and self.seg["act"] not in ("razor", "light"):
            img = img * np.array([1.0, 0.97, 0.92], np.float32)
        # 4-frame dip between shots keeps cuts soft
        lt = t - k * self.step
        f = min(1.0, lt / 0.12, max(0.0, (self.step - lt) / 0.12))
        return img * (0.3 + 0.7 * f)
    res = "full"

class Still(Scene):
    res = "full"
    def setup(self):
        p = os.path.join(self.ctx["stills"], self.p["path"] + ".png")
        self.img = to_f(Image.open(p).convert("RGB").resize((W, H))) if os.path.exists(p) else np.zeros((H, W, 3), np.float32)
    def frame(self, fi, t):
        s = 1 + 0.04 * t
        x, y = grid(W, H)
        return bilinear(self.img, (x - W / 2) / s + W / 2, (y - H / 2) / s + H / 2, None)

# ---------------- Act I ----------------
class Eye(Scene):
    res = "full"
    def setup(self):
        self.stars = self.rng.uniform(0, 1, (220, 3))
    def moon(self, t):
        im, d = draw_canvas(W, H, (6, 6, 8))
        for sx, sy, sb in self.stars:
            v = int(80 + 150 * sb); d.point((sx * W, sy * H * 0.9), fill=(v, v, v))
        cx, cy, r = W * 0.5, H * 0.42, 140
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(228, 226, 218))
        for ox, oy, rr in ((-40, -30, 30), (35, 20, 22), (-10, 55, 18), (60, -50, 14)):
            d.ellipse([cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr], fill=(200, 198, 190))
        u = t / max(self.d, 1)
        cxl = -500 + u * (W + 900)
        for k in range(5):
            yy = cy - 6 + k * 4
            d.rounded_rectangle([cxl - 420 + k * 30, yy - 7, cxl + 420 - k * 20, yy + 7], 7, fill=(30, 30, 34, 235))
        img = pil_f(im)
        return blur(img, 1.2)
    def theatre(self, t):
        im, d = draw_canvas(W, H, (8, 8, 10))
        sx0, sy0, sx1, sy1 = 360, 90, 920, 400
        flick = 0.92 + 0.08 * math.sin(t * 2.1)
        v = int(215 * flick)
        d.rectangle([sx0, sy0, sx1, sy1], fill=(v, v, v - 6))
        hx = 640 + 40 * math.sin(t * 0.3)
        d.ellipse([hx - 38, 210, hx + 38, 290], fill=(v - 70, v - 70, v - 72))
        d.rounded_rectangle([hx - 95, 280, hx + 95, 420], 60, fill=(v - 70, v - 70, v - 72))
        d.rectangle([sx0 - 20, sy1, sx1 + 20, sy1 + 20], fill=(20, 18, 18))
        for row in range(4):
            y = 470 + row * 70
            for k in range(-9, 10):
                x = 640 + k * (70 + row * 6)
                d.ellipse([x - 32 - row * 3, y, x + 32 + row * 3, y + 90 + row * 10], fill=(18 + row * 2, 16, 16))
        beam = Image.new("L", (W, H), 0); bd = ImageDraw.Draw(beam)
        bd.polygon([(640, 720), (sx0 + 40, sy0 + 20), (sx1 - 40, sy0 + 20)], fill=40)
        beam = beam.filter(ImageFilter.GaussianBlur(30))
        img = pil_f(im)
        img += to_f(beam)[..., None] * 0.35
        return img
    def eye(self, t, open_=1.0, cut=None, razor_x=None):
        im, d = draw_canvas(W, H, (14, 13, 12))
        cx, cy = 640, 360
        d.ellipse([cx - 420, cy - 300, cx + 420, cy + 300], fill=(60, 56, 52))
        oh = 190 * open_
        lid = [(cx - 380, cy)] + [(cx + x, cy - oh * math.cos(x / 380 * math.pi / 2)) for x in range(-380, 381, 20)] + \
              [(cx + 380, cy)] + [(cx + x, cy + oh * 0.8 * math.cos(x / 380 * math.pi / 2)) for x in range(380, -381, -20)]
        mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).polygon(lid, fill=255)
        eye = Image.new("RGB", (W, H), (228, 224, 216)); ed = ImageDraw.Draw(eye)
        for r, v in ((150, 110), (140, 95), (120, 80), (100, 70)):
            ed.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(v, v, v))
        rng = np.random.default_rng(3)
        for a in np.linspace(0, 2 * np.pi, 140, endpoint=False):
            r0 = 60 + rng.uniform(0, 10); r1 = 145
            v = int(rng.uniform(50, 140))
            ed.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=(v, v, v), width=2)
        ed.ellipse([cx - 58, cy - 58, cx + 58, cy + 58], fill=(8, 8, 8))
        ed.ellipse([cx + 25, cy - 70, cx + 70, cy - 25], fill=(250, 250, 250))
        im.paste(eye, (0, 0), mask)
        for x in range(-360, 361, 28):
            y = cy - oh * math.cos(x / 380 * math.pi / 2)
            d.line([(cx + x, y), (cx + x * 1.08, y - 30 - 10 * math.cos(x / 380 * 1.5))], fill=(20, 18, 16), width=4)
        d.line(lid[: len(lid) // 2], fill=(30, 26, 24), width=6)
        if razor_x is not None:
            d.polygon([(razor_x - 900, cy - 8), (razor_x, cy - 8), (razor_x + 30, cy), (razor_x - 900, cy + 10)], fill=(200, 205, 210))
            d.line([(razor_x - 900, cy - 8), (razor_x, cy - 8)], fill=(255, 255, 255), width=2)
        img = pil_f(im)
        if cut is not None:
            u, sep = cut
            xx = int(u * W)
            img[cy - 2:cy + 2, :xx] = 0.98
            if sep > 0:
                s = int(sep * 380)
                top = np.zeros_like(img); top[: max(0, cy - s)] = img[s: cy] if s < cy else 0
                bot = np.zeros_like(img); bot[cy + s:] = img[cy: H - s] if s < H - cy else 0
                light = np.clip(1 - np.abs(np.arange(H) - cy)[:, None, None] / (s + 1), 0, 1) * 0.85
                img = top + bot + light * (1 - smooth(sep * 1.5 - 0.5))
        return img
    def frame(self, fi, t):
        ph = self.p.get("phase")
        if ph == "theatre": return self.theatre(t)
        if ph == "moon": return self.moon(t)
        if ph == "slice_static":
            return self.eye(0, 1.0, (1.0, 0.25))
        c = self.c
        open_ = smooth(t / 2.5)
        rx = None
        if t >= c["razor"] - 1.0:
            rx = lerp(-100, 400, smooth((t - c["razor"] + 1.0) / max(0.5, c["slice"] - c["razor"] + 0.5)))
        cut = None
        if t >= c["slice"]:
            u = smooth((t - c["slice"]) / 0.3); sep = smooth((t - c["slice"] - 0.35) / 1.2)
            cut = (u, sep)
            rx = lerp(400, 1600, u)
        img = self.eye(t, open_, cut, rx)
        if t > c["slice"] + 1.6:
            img = img * (1 - smooth((t - c["slice"] - 1.6) / 1.0)) + 0.04
        return img

class TypeCard(Scene):
    res = "full"
    def setup(self):
        self.text = self.p["text"]
    def frame(self, fi, t):
        im, d = draw_canvas(W, H, (6, 6, 6))
        d.rectangle([110, 90, W - 110, H - 90], outline=(220, 214, 200), width=3)
        d.rectangle([124, 104, W - 124, H - 104], outline=(220, 214, 200), width=1)
        for (x, y) in ((124, 104), (W - 124, 104), (124, H - 104), (W - 124, H - 104)):
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(220, 214, 200))
        n = int(max(0, t - self.c["type_start"]) * TYPE_CPS)
        shown, k = [], 0
        for line in self.text.split("\n"):
            take = max(0, min(len(line), n - k)); shown.append(line[:take]); k += len(line) + 3
        f0 = font("serif_b", 46); f1 = font("serif_i", 60)
        y = 210
        for i, l in enumerate(shown):
            f = f0 if i == 0 else f1
            full = self.text.split("\n")[i]
            wfull = d.textbbox((0, 0), full, font=f)[2]
            d.text(((W - wfull) / 2, y), l, font=f, fill=(236, 230, 214))
            y += 70 if i == 0 else 84
        return pil_f(im)

class Door(Scene):
    res = "full"
    def frame(self, fi, t):
        op = self.p.get("open_at")
        if op is None:
            s = self.sents(0); op = s[1]["start"] + 2.0 if len(s) > 1 else 3.0
        u = smooth((t - op) / 1.6)
        im, d = draw_canvas(W, H, (40, 38, 36))
        for x in range(0, W, 22):
            d.line([(x, 0), (x, H)], fill=(48, 46, 43), width=8)
        dx0, dy0, dx1, dy1 = 470, 110, 810, 660
        sky = Image.new("RGB", (dx1 - dx0, dy1 - dy0)); sd = ImageDraw.Draw(sky)
        for y in range(dy1 - dy0):
            v = int(235 - y * 0.12) if y < 300 else int(150 + 30 * math.sin(y * 0.3 + t * 3))
            sd.line([(0, y), (dx1 - dx0, y)], fill=(v, v, v - 4))
        for k in range(8):
            yy = 300 + k * 26 + 4 * math.sin(t * 1.5 + k)
            sd.line([(0, yy), (dx1 - dx0, yy + 3 * math.sin(t + k))], fill=(240, 240, 240), width=2)
        sd.rectangle([0, 470, dx1 - dx0, dy1 - dy0], fill=(200, 196, 186))
        im.paste(sky, (dx0, dy0))
        if u > 0.45:
            wk = smooth((t - op - 1.0) / 6.0)
            fx = lerp(620, 700, wk); fy = lerp(560, 520, wk); sc = lerp(1.0, 0.45, wk)
            d.ellipse([fx - 18 * sc, fy - 160 * sc, fx + 18 * sc, fy - 124 * sc], fill=(20, 20, 20))
            d.polygon([(fx - 30 * sc, fy - 120 * sc), (fx + 30 * sc, fy - 120 * sc), (fx + 50 * sc, fy + 30 * sc), (fx - 50 * sc, fy + 30 * sc)], fill=(25, 25, 25))
        ww = (dx1 - dx0) * (1 - u)
        skew = 60 * u
        d.polygon([(dx0, dy0), (dx0 + ww, dy0 + skew), (dx0 + ww, dy1 - skew), (dx0, dy1)], fill=(70, 62, 55))
        if ww > 30:
            d.ellipse([dx0 + ww - 30, 380, dx0 + ww - 16, 394], fill=(180, 170, 140))
        d.rectangle([dx0 - 16, dy0 - 16, dx1 + 16, dy1], outline=(25, 22, 20), width=16)
        img = pil_f(im)
        return img

class Steps(Scene):
    res = "full"
    def setup(self):
        rng = self.rng
        def tex(kind):
            x, y = grid(W // 2, H // 2)
            if kind == "sand":
                n = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
                b = to_f(Image.fromarray(np.clip(n * 30 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)))
                v = 0.72 + 0.25 * (b - 0.5) + 0.05 * np.sin(x * 0.05 + y * 0.02)
            elif kind == "grass":
                im = Image.new("L", (W // 2, H // 2), 40); d = ImageDraw.Draw(im)
                for _ in range(5000):
                    x0, y0 = rng.uniform(0, W // 2), rng.uniform(0, H // 2)
                    d.line([(x0, y0), (x0 + rng.normal(0, 4), y0 - rng.uniform(8, 22))], fill=int(rng.uniform(60, 200)), width=1)
                v = to_f(im)
            elif kind == "pave":
                im = Image.new("L", (W // 2, H // 2), 120); d = ImageDraw.Draw(im)
                for yy in range(0, H // 2, 60):
                    off = 45 if (yy // 60) % 2 else 0
                    for xx in range(-60, W // 2, 90):
                        g = int(rng.uniform(100, 150)); d.rectangle([xx + off + 2, yy + 2, xx + off + 88, yy + 58], fill=g)
                v = to_f(im) + rng.normal(0, 0.03, (H // 2, W // 2)).astype(np.float32)
            else:
                v = 0.35 + 0.25 * (np.sin(x * 0.12) * np.sin(y * 0.12) > 0) + 0.15 * np.sin((x + y) * 0.05)
                v = v + 0.1 * ((np.abs((x % 40) - 20) < 2) | (np.abs((y % 40) - 20) < 2))
            return upscale(np.repeat(np.asarray(v, np.float32)[..., None], 3, -1))
        self.tex = [tex(k) for k in ("sand", "grass", "pave", "rug")]
        steps = self.c.get("steps") or [0.5, 1.5, 2.5, 3.5]
        self.times = steps
        self.static = self.p.get("static", False)
    def foot(self, img, t_land, t):
        u = smooth((t - t_land + 0.35) / 0.35)
        y = lerp(-200, 330, u); sc = lerp(1.3, 1.0, u)
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
        cx = 640
        d.ellipse([cx - 70 * sc, y - 20 * sc, cx + 70 * sc, y + 230 * sc], fill=255)
        for k, (ox, rr) in enumerate(((-55, 26), (-18, 22), (14, 19), (40, 16), (60, 13))):
            d.ellipse([cx + ox * sc - rr * sc, y - 70 * sc - rr * sc + k * 6 * sc, cx + ox * sc + rr * sc, y - 70 * sc + rr * sc + k * 6 * sc], fill=255)
        m = to_f(im.filter(ImageFilter.GaussianBlur(3)))[..., None]
        sh = to_f(im.filter(ImageFilter.GaussianBlur(30)))[..., None]
        sh = np.roll(sh, (30, 30), (0, 1))
        img = img * (1 - 0.45 * sh * u)
        return img * (1 - m) + m * 0.08
    def frame(self, fi, t):
        if self.static:
            k = int(t / 0.5) % 4
            return self.foot(self.tex[k].copy(), -1, t)
        tt = self.times
        k = sum(1 for x in tt if t >= x - 0.35) - 1
        if k < 0:
            x, y = grid(W, H)
            sx = 1.15 - 0.1 * t / max(tt[0], 1)
            return bilinear(self.tex[0], (x - W / 2) / sx + W / 2, (y - H / 2) / sx + H / 2, None) * 0.7
        if k >= 3 and t > tt[3] + 2.2:
            out = np.zeros((H, W, 3), np.float32)
            for i in range(4):
                small = self.foot(self.tex[i].copy(), -1, t)[::2, ::2]
                y0 = (i // 2) * (H // 2); x0 = (i % 2) * (W // 2)
                out[y0:y0 + H // 2, x0:x0 + W // 2] = small
            out[H // 2 - 2:H // 2 + 2] = 0; out[:, W // 2 - 2:W // 2 + 2] = 0
            return out
        return self.foot(self.tex[min(k, 3)].copy(), tt[min(k, 3)], t)

class Direct(Scene):
    res = "full"
    look = "film_color"
    def setup(self):
        rng = self.rng
        Hs = 7000
        im = Image.new("RGB", (W, Hs)); d = ImageDraw.Draw(im, "RGBA")
        y = 0
        pal = [(214, 40, 40), (247, 200, 30), (30, 90, 200), (30, 160, 90), (240, 120, 30), (150, 40, 160), (250, 240, 220)]
        while y < Hs:
            L = int(rng.uniform(150, 500)); c = pal[rng.integers(len(pal))]
            d.rectangle([0, y, W, y + L], fill=c); y += L
        for _ in range(260):
            x = rng.uniform(0, W); y = rng.uniform(0, Hs); c = pal[rng.integers(len(pal))] + (int(rng.uniform(150, 240)),)
            kind = rng.integers(4)
            if kind == 0:
                n = int(rng.integers(5, 14)); sp = rng.uniform(6, 16); amp = rng.uniform(20, 120); L = rng.uniform(200, 900)
                for j in range(n):
                    pts = [(x + j * sp + amp * math.sin(yy * 0.01 + j * 0.2), y + yy) for yy in range(0, int(L), 12)]
                    d.line(pts, fill=c, width=3)
            elif kind == 1:
                r = rng.uniform(20, 120); d.ellipse([x - r, y - r, x + r, y + r], fill=c)
            elif kind == 2:
                for j in range(int(rng.integers(10, 40))):
                    xx, yy = x + rng.normal(0, 60), y + rng.normal(0, 60); r = rng.uniform(3, 10)
                    d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=c)
            else:
                d.polygon([(x, y), (x + rng.uniform(-300, 300), y + rng.uniform(100, 500)), (x + rng.uniform(-300, 300), y + rng.uniform(50, 400))], fill=c)
        self.strip = to_f(im.filter(ImageFilter.GaussianBlur(1.5)))
        self.Hs = Hs
    def frame(self, fi, t):
        i, bt, b = self.beat(t)
        mode = b["p"].get("mode", "strip")
        if mode == "projected":
            off = int(t * 900) % (self.Hs - H)
            return self.strip[off:off + H].copy()
        out = np.ones((H, W, 3), np.float32) * np.array([0.93, 0.92, 0.88], np.float32)
        sw = 420; x0 = (W - sw) // 2
        off = int(t * 60) % (self.Hs - H)
        film = self.strip[off:off + H, :sw * 2:2].copy()
        out[:, x0:x0 + sw] = film
        for yy in range(-40, H + 40, 44):
            y = int(yy + (t * 60) % 44)
            for xs in (x0 - 40, x0 + sw + 12):
                if 0 <= y < H - 24: out[y:y + 22, xs:xs + 28] = np.array([0.93, 0.92, 0.88])
            out[max(0, y):max(0, min(H, y + 22)), x0 - 52:x0 - 44] = 0.1
        out[:, x0 - 56:x0 - 2] = np.where(out[:, x0 - 56:x0 - 2] > 0.9, out[:, x0 - 56:x0 - 2], 0.12)
        out[:, x0 + sw + 2:x0 + sw + 56] = np.where(out[:, x0 + sw + 2:x0 + sw + 56] > 0.9, out[:, x0 + sw + 2:x0 + sw + 56], 0.12)
        bx = x0 + sw / 2 + 120 * math.sin(t * 1.3); by = H / 2 + 120 * math.sin(t * 0.9)
        im = Image.fromarray(to_u8(out)); d = ImageDraw.Draw(im)
        d.line([(bx, by), (bx + 260, by - 300)], fill=(90, 60, 30), width=14)
        d.ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=(214, 40, 40))
        return pil_f(im)

class Synchromy(Scene):
    res = "full"
    look = "film_color"
    def frame(self, fi, t):
        bt = 60 / SYNCH_BPM; loop = 24 * bt
        tt = (t - 0.5) % loop
        cur = SYNCH_NOTES[0]
        for n in SYNCH_NOTES:
            if tt >= n[0] * bt: cur = n
        k = SYNCH_NOTES.index(cur)
        hue = (k * 0.085) % 1
        bg = hsv2rgb(np.array(hue), np.array(0.55), np.array(0.55))
        fg = hsv2rgb(np.array(hue + 0.5), np.array(0.35), np.array(0.95))
        out = np.ones((H, W, 3), np.float32) * bg
        f = float(mtof_(cur[2]))
        bars = int(f / 40)
        cols = 1 + (k % 4)
        cw = 120
        x_all = [W / 2 + (j - (cols - 1) / 2) * (cw + 40) for j in range(cols)]
        y = np.arange(H)
        stripes = ((y * bars / H) % 1.0 < 0.5)[:, None, None]
        for x in x_all:
            x0 = int(x - cw / 2); out[:, x0:x0 + cw] = np.where(stripes, fg, bg * 0.6)
        return out

def mtof_(m): return 440 * 2 ** ((m - 69) / 12)

class Osc(Scene):
    look = "film_color"
    stateful = True
    def setup(self):
        self.buf = np.zeros((h, w), np.float32)
        x, y = grid(W, H)
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
        cx, cy, R = W / 2, H / 2, 300
        for k in range(-5, 6):
            d.line([(cx + k * 60, cy - R + 10), (cx + k * 60, cy + R - 10)], fill=(80, 140, 110, 60))
        for k in range(-4, 5):
            d.line([(cx - 5 * 60, cy + k * 60), (cx + 5 * 60, cy + k * 60)], fill=(80, 140, 110, 60))
        self.grat = g
        self.mask = (np.sqrt((x - cx) ** 2 + ((y - cy) * 1.0) ** 2) < 330)[..., None].astype(np.float32)
        self.mask = blur(np.repeat(self.mask, 3, -1), 6)
    def frame(self, fi, t):
        st = t + getattr(self, "toff", 0.0)
        k = min(int(st // OSC_STEP), len(OSC_RATIOS) - 1)
        a, b = OSC_RATIOS[k]
        s = np.linspace(0, 2 * np.pi, 6000)
        ph = 0.4 * st
        x = np.sin(a * s); y = np.sin(b * s + ph)
        u = (st % OSC_STEP) / OSC_STEP
        if u > 0.85 and k + 1 < len(OSC_RATIOS):
            a2, b2 = OSC_RATIOS[k + 1]; m = smooth((u - 0.85) / 0.15)
            x = x * (1 - m) + np.sin(a2 * s) * m; y = y * (1 - m) + np.sin(b2 * s + ph) * m
        px = (w / 2 + x * 140).astype(np.int32); py = (h / 2 - y * 140).astype(np.int32)
        self.buf *= 0.78
        np.add.at(self.buf, (np.clip(py, 0, h - 1), np.clip(px, 0, w - 1)), 0.35)
        v = np.clip(self.buf, 0, 1)
        img = np.stack([v * 0.35, v, v * 0.55], -1)
        img = upscale(img)
        img = glow(img, 8, 1.2)
        img = img * self.mask + 0.02
        comp(img, self.grat, 0, 0, 1)
        return img
    res = "full"

# ---------------- Act II ----------------
class Dome(Scene):
    def setup(self):
        self.x, self.y = grid(w, h)
        self.cx, self.cy = w / 2, h / 2 + 10
        dx, dy = self.x - self.cx, self.y - self.cy
        self.r = np.sqrt(dx * dx + dy * dy) / 170; self.th = np.arctan2(dy, dx)
        self.disc = smooth((1 - self.r) * 30)[..., None]
        n = 500
        self.sr = np.sqrt(self.rng.uniform(0, 1, n)); self.sa = self.rng.uniform(0, 2 * np.pi, n); self.sb = self.rng.uniform(0.3, 1, n)
    def frame(self, fi, t):
        i, bt, b = self.beat(t)
        ph = b["p"].get("phase", "stars")
        out = np.zeros((h, w, 3), np.float32)
        a = self.sa + t * 0.03
        px = (self.cx + self.sr * 168 * np.cos(a)).astype(np.int32); py = (self.cy + self.sr * 168 * np.sin(a)).astype(np.int32)
        out[np.clip(py, 0, h - 1), np.clip(px, 0, w - 1)] = self.sb[:, None]
        mix = 0.0
        if ph == "vortex":
            mix = smooth(bt / 4.0)
        if mix > 0:
            r, th = self.r, self.th
            v = np.sin(6 * th + 4 * np.log(r + 0.05) * 3 - t * 0.9) + np.sin(3 * th - 9 * r + t * 1.3) + 0.6 * np.sin(14 * r - t * 2)
            hue = 0.6 + 0.12 * v + t * 0.02
            col = hsv2rgb(hue, np.full_like(v, 0.75), np.clip(0.25 + 0.3 * v, 0, 1) * np.clip(1.2 - r, 0, 1))
            out = out * (1 - mix) + col * mix
        out = out * self.disc
        out += (1 - self.disc) * 0.03 * np.array([0.6, 0.5, 0.8], np.float32)
        return out

class Harmonograph(Scene):
    res = "full"
    stateful = True
    def setup(self):
        self.canvas = Image.new("RGB", (W, H), (8, 4, 6)); self.dr = ImageDraw.Draw(self.canvas)
        self.s = 0.0
        self.fig = 0
        self.par = [(2.01, 3.0, 0.0, 1.6, 0.004), (3.0, 2.0, 1.0, 0.5, 0.003)]
    def pt(self, s, par):
        f1, f2, p1, p2, dd = par
        e = math.exp(-dd * s)
        x = (math.sin(f1 * s + p1) + 0.6 * math.sin(f2 * 1.01 * s + p2)) * e
        y = (math.sin(f2 * s) + 0.6 * math.sin(f1 * 0.99 * s + p1 + 0.5)) * e
        return W / 2 + x * 210, H / 2 + y * 190
    def frame(self, fi, t):
        par = self.par[0 if t < self.d * 0.55 else 1]
        if t >= self.d * 0.55 and self.fig == 0:
            self.fig = 1; self.s = 0.0
        col = (230, 70, 50) if self.fig == 0 else (250, 170, 60)
        pts = [self.pt(self.s + k * 0.02, par) for k in range(40)]
        self.dr.line(pts, fill=col, width=2)
        self.s += 0.8
        img = pil_f(self.canvas)
        sc = 1 + 0.06 * t / self.d
        x, y = grid(W, H)
        img = bilinear(img, (x - W / 2) / sc + W / 2, (y - H / 2) / sc + H / 2, None)
        return glow(img, 5, 0.6)

class Whitney(Scene):
    stateful = True
    def setup(self):
        self.buf = np.zeros((h, w, 3), np.float32)
        n = 300
        self.k = np.arange(1, n + 1)
        self.col = hsv2rgb(self.k / n * 0.6 + 0.0, np.full(n, 0.8), np.full(n, 1.0))
    def frame(self, fi, t):
        tt = t * 0.05 + 3.0
        a = self.k * tt
        r = self.k * 0.55
        px = (w / 2 + r * np.cos(a)).astype(np.int32); py = (h / 2 + r * np.sin(a) * 0.95).astype(np.int32)
        ok = (px > 1) & (px < w - 2) & (py > 1) & (py < h - 2)
        self.buf *= 0.8
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            self.buf[py[ok] + dy, px[ok] + dx] = np.maximum(self.buf[py[ok] + dy, px[ok] + dx], self.col[ok])
        return glow(np.clip(self.buf, 0, 1), 6, 0.9, 2)

class Leader(Scene):
    res = "full"
    def frame(self, fi, t):
        c = self.c
        counts = c["counts"]
        if t < counts[-1] + 1.0:
            k = max(0, min(len(counts) - 1, int(t - counts[0]) if t >= counts[0] else 0))
            num = 8 - k
            u = (t - counts[0]) % 1.0 if t >= counts[0] else 0
            im, d = draw_canvas(W, H, (150, 150, 150))
            cx, cy = W / 2, H / 2
            d.pieslice([cx - 600, cy - 600, cx + 600, cy + 600], -90, -90 + 360 * u, fill=(95, 95, 95))
            d.ellipse([cx - 260, cy - 260, cx + 260, cy + 260], outline=(240, 240, 240), width=6)
            d.ellipse([cx - 220, cy - 220, cx + 220, cy + 220], outline=(240, 240, 240), width=4)
            d.line([(0, cy), (W, cy)], fill=(30, 30, 30), width=3); d.line([(cx, 0), (cx, H)], fill=(30, 30, 30), width=3)
            f = font("serif_b", 300)
            bb = d.textbbox((0, 0), str(num), font=f)
            d.text((cx - bb[2] / 2, cy - bb[3] / 2 - 30), str(num), font=f, fill=(20, 20, 20))
            return pil_f(im)
        cards = c["cards"]; k = 0
        for i, ct in enumerate(cards):
            if t >= ct: k = i
        im, d = draw_canvas(W, H, (5, 5, 5))
        txt = LEADER_CARDS[k]
        f = font("serif_b", 120 if len(txt) < 10 else 80)
        bb = d.textbbox((0, 0), txt, font=f)
        jx = int(self.rng.integers(-3, 4)); jy = int(self.rng.integers(-3, 4))
        d.text(((W - bb[2]) / 2 + jx, (H - bb[3]) / 2 + jy), txt, font=f, fill=(235, 235, 230))
        img = pil_f(im)
        if t > cards[-1] + 1.4:
            img *= 1 - smooth((t - cards[-1] - 1.4) / 1.0)
        return img

class Liquid(Scene):
    look = "film_color"
    def setup(self):
        self.ww, self.hh = 320, 180
        self.x, self.y = grid(self.ww, self.hh)
        self.n = 9
        self.ph = self.rng.uniform(0, 6.28, (self.n, 4)); self.fr = self.rng.uniform(0.05, 0.16, (self.n, 2)); self.rad = self.rng.uniform(14, 34, self.n)
        cx, cy = self.ww / 2, self.hh / 2
        self.mask = smooth((1 - np.sqrt(((self.x - cx) / 150) ** 2 + ((self.y - cy) / 95) ** 2)) * 6)[..., None]
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        cx, cy = self.ww / 2, self.hh / 2
        a = t * 0.05
        xr = (self.x - cx) * math.cos(a) - (self.y - cy) * math.sin(a)
        yr = (self.x - cx) * math.sin(a) + (self.y - cy) * math.cos(a)
        u = xr + 14 * np.sin(yr * 0.05 + t * 0.4); v = yr + 14 * np.sin(xr * 0.045 - t * 0.33)
        f = np.sin(u * 0.03 + t * 0.2) + np.sin(v * 0.035 - t * 0.25) + np.sin((u + v) * 0.02 + t * 0.15)
        m = np.zeros_like(self.x)
        for i in range(self.n):
            bx = cx + 110 * math.sin(t * self.fr[i, 0] + self.ph[i, 0]) + 20 * math.sin(t * 0.3 + self.ph[i, 2])
            by = cy + 60 * math.sin(t * self.fr[i, 1] + self.ph[i, 1])
            r = self.rad[i] * (1 + 0.2 * math.sin(t * 0.4 + self.ph[i, 3]))
            m += r * r / ((self.x - bx) ** 2 + (self.y - by) ** 2 + 1)
        inside = smooth((m - 0.9) * 5)
        rim = np.exp(-((m - 1.0) / 0.12) ** 2)
        hue = 0.85 + 0.12 * f + t * 0.01
        base = hsv2rgb(hue, np.full_like(f, 0.9), np.clip(0.55 + 0.2 * f, 0, 1))
        oil = hsv2rgb(hue + 0.3 + 0.1 * m, np.full_like(f, 0.8), np.clip(0.8 + 0.1 * f, 0, 1))
        img = base * (1 - inside[..., None]) + oil * inside[..., None]
        img = img * (1 - 0.6 * rim[..., None]) + rim[..., None] * 0.25
        img = img * self.mask
        return upscale(img, (w, h))

class SlitScan(Scene):
    def setup(self):
        rng = self.rng
        tw, th = 512, 2048
        cols = hsv2rgb(rng.uniform(0, 1, 64), rng.uniform(0.5, 1.0, 64), rng.uniform(0.5, 1.0, 64))
        edges = np.sort(rng.integers(0, tw, 63)); band = np.searchsorted(edges, np.arange(tw))
        tex = np.repeat(cols[band][None], th, 0)
        mod = 0.6 + 0.4 * np.sin(np.arange(th)[:, None] * rng.uniform(0.01, 0.05, (1, tw)) + rng.uniform(0, 6, (1, tw)))
        self.tex = (tex * mod[..., None]).astype(np.float32)
        self.x, self.y = grid(w, h)
        self.cy = h / 2
        dy = np.abs(self.y - self.cy) + 0.5
        self.z = 30.0 / dy
        self.u = (self.x - w / 2) * self.z * 0.006
        self.top = self.y < self.cy
        self.fog = np.clip(1 - self.z / 14, 0, 1)[..., None] ** 1.5
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        sp = self.p.get("speed", 1.0)
        v = self.z * 0.8 + t * 9 * sp
        ui = ((self.u + np.where(self.top, 0.37, 0.0)) * 512).astype(np.int64) % 512
        vi = (v * 60).astype(np.int64) % 2048
        img = self.tex[vi, ui]
        hue_shift = np.where(self.top, 0.0, 0.5)[..., None]
        img = img * (0.75 + 0.25 * np.cos(hue_shift * 6.28 + t * 0.2))
        img = img * self.fog + (1 - self.fog) * np.array([1.0, 0.95, 0.85], np.float32) * 0.9 * np.exp(-np.abs(self.y - self.cy)[..., None] / 6)
        return img

# ---------------- Act III ----------------
def test_pattern(ww=w, hh=h):
    im, d = draw_canvas(ww, hh, (40, 40, 40))
    bars = [(192, 192, 192), (192, 192, 0), (0, 192, 192), (0, 192, 0), (192, 0, 192), (192, 0, 0), (0, 0, 192)]
    bw = ww / 7
    for i, c in enumerate(bars):
        d.rectangle([i * bw, 0, (i + 1) * bw, hh * 0.35], fill=c)
    for k in range(0, ww, 40): d.line([(k, hh * 0.35), (k, hh)], fill=(90, 90, 90))
    for k in range(int(hh * 0.35), hh, 40): d.line([(0, k), (ww, k)], fill=(90, 90, 90))
    cx, cy = ww / 2, hh * 0.66
    for r in (110, 80, 50): d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(230, 230, 230), width=3)
    d.line([(cx - 120, cy), (cx + 120, cy)], fill=(230, 230, 230), width=3); d.line([(cx, cy - 120), (cx, cy + 120)], fill=(230, 230, 230), width=3)
    return pil_f(im)

class TVWall(Scene):
    res = "full"
    look = "film_bw"
    def setup(self):
        self.tp = test_pattern(300, 200)
    def screen(self, k, t, sw, sh):
        x, y = grid(sw, sh)
        if k == 0:
            v = np.exp(-((y - sh / 2) / 2.0) ** 2)
        elif k == 1:
            v = 0.35 + 0.25 * self.rng.random((sh, sw))
        elif k == 2:
            v = 0.5 + 0.5 * np.sin((y + t * 60) * 0.08)
        elif k == 3:
            v = 0.5 + 0.5 * np.sin(x * 0.05 + 3 * np.sin(y * 0.04 + t))
        elif k == 4:
            r = np.sqrt((x - sw / 2) ** 2 + (y - sh / 2) ** 2); v = 0.5 + 0.5 * np.sin(r * 0.2 - t * 3)
        elif k == 5:
            tp = self.tp @ np.array([0.3, 0.6, 0.1], np.float32)
            v = np.roll(tp[:sh, :sw], int(t * 40) % sh, 0)
        elif k == 6:
            a = np.arctan2(y - sh / 2, x - sw / 2); r = np.sqrt((x - sw / 2) ** 2 + (y - sh / 2) ** 2)
            v = 0.5 + 0.5 * np.sin(a * 5 + r * 0.1 - t * 2)
        elif k == 7:
            v = np.exp(-((x - sw / 2) / 2.0) ** 2) + 0 * y
        else:
            v = 0.5 + 0.5 * np.sin((y + 20 * np.sin(x * 0.03 + t * 2)) * 0.15)
        return np.repeat(np.asarray(v, np.float32)[..., None], 3, -1)
    def frame(self, fi, t):
        out = np.ones((H, W, 3), np.float32) * 0.05
        sc = 1 + 0.05 * t / self.d
        sw, sh = 260, 170
        for k in range(9):
            r, c = divmod(k, 3)
            x0 = int(W / 2 + (c - 1) * 330 * sc - sw / 2); y0 = int(H / 2 + (r - 1) * 215 * sc - sh / 2)
            out[y0 - 16:y0 + sh + 16, x0 - 18:x0 + sw + 18] = 0.16
            out[y0:y0 + sh, x0:x0 + sw] = self.screen(k, t, sw, sh) * 0.9 + 0.04
        return out

class Magnet(Scene):
    look = "crt"
    def setup(self):
        self.tp = test_pattern()
        self.x, self.y = grid(w, h)
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        mx = w / 2 + 160 * math.sin(t * 0.31); my = h / 2 + 90 * math.sin(t * 0.47 + 1)
        dx, dy = self.x - mx, self.y - my
        r2 = dx * dx + dy * dy + 400
        st = 5000 * (0.6 + 0.4 * math.sin(t * 0.8))
        rot = 0.9 + 0.5 * math.sin(t * 0.23)
        ux = (dx * math.cos(rot) - dy * math.sin(rot)) / r2 * st
        uy = (dx * math.sin(rot) + dy * math.cos(rot)) / r2 * st
        return bilinear(self.tp, self.x + ux, self.y + uy, 0.05)

class VHS(Scene):
    res = "full"
    look = "vhs"
    def frame(self, fi, t):
        s = self.sents(0)
        im, d = draw_canvas(W, H, (16, 22, 70))
        fo = font("mono_b", 40)
        if t < 3.0:
            d.text((80, 60), "<< REW", font=fo, fill=(240, 240, 240))
        else:
            d.text((80, 60), "PLAY >", font=fo, fill=(240, 240, 240))
        if len(s) > 2 and t >= s[2]["start"]:
            n = int((t - s[2]["start"]) * 24)
            d.text((W - 380, 60), "REC ●", font=fo, fill=(250, 60, 60) if int(t * 1.5) % 2 == 0 else (250, 250, 250))
            d.text((W - 380, H - 110), "00:%02d:%02d" % (n // 24 // 60, (n // 24) % 60), font=font("mono", 36), fill=(240, 240, 240))
            y = np.arange(0, H, 1)
            for k in range(12):
                yy = 260 + k * 30 + 6 * math.sin(t + k)
                d.line([(0, yy), (W, yy + 20 * math.sin(t * 0.5 + k))], fill=(70, 80, 120), width=3)
        f = font("mono_b", 150)
        txt = self.p.get("text", "1965 ?")
        bb = d.textbbox((0, 0), txt, font=f)
        d.text(((W - bb[2]) / 2, (H - bb[3]) / 2 - 20), txt, font=f, fill=(240, 240, 240))
        img = pil_f(im)
        if len(s) > 1 and t >= s[1]["start"]:
            st = text_img("UNVERIFIED", "mono_b", 70, fill=(230, 40, 40, 255))
            st = st.rotate(12, expand=True, resample=Image.BICUBIC)
            comp_center(img, st, W / 2 + 230, H / 2 + 120, smooth((t - s[1]["start"]) / 0.3))
        if t < 3.0:
            yy = int((t * 400) % H)
            img[yy:yy + 60] = np.roll(img[yy:yy + 60], 40, 1)
        return img

class Colorizer(Scene):
    look = "crt"
    def setup(self):
        self.x, self.y = grid(w, h)
    def frame(self, fi, t):
        x = self.x + 18 * np.sin(self.y * 0.04 + t * 2.0)
        lum = np.zeros_like(self.x)
        for i in range(5):
            bx = w / 2 + 180 * math.sin(t * (0.2 + 0.07 * i) + i); by = h / 2 + 100 * math.sin(t * (0.3 + 0.05 * i) + 2 * i)
            lum += np.exp(-((x - bx) ** 2 + (self.y - by) ** 2) / (2 * (40 + 10 * i) ** 2))
        hx, hy = w / 2, h / 2
        face = np.exp(-(((x - hx) / 90) ** 2 + ((self.y - hy) / 120) ** 2) * 2)
        lum = np.clip(lum * 0.7 + face * 0.8, 0, 1.5)
        return hsv2rgb(lum * 2.2 + t * 0.15, np.full_like(lum, 0.95), np.clip(lum * 1.3, 0, 1))

class Beck(Scene):
    look = "crt"
    def setup(self):
        self.x, self.y = grid(w, h)
    def frame(self, fi, t):
        x, y = self.x / w, self.y / h
        a = np.sin(x * 9 + t * 0.7) * np.sin(y * 6 - t * 0.5)
        b = np.sin((x + y) * 7 - t * 0.9) * np.cos(x * 4 + t * 0.3)
        c = np.sin(np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2) * 30 - t * 1.6)
        r = smooth((a - 0.3) * 4); g = smooth((b - 0.2) * 4); bl = smooth((c - 0.5) * 3)
        img = np.stack([r * 0.9 + bl * 0.3, g * 0.8 + bl * 0.2, bl * 0.9 + r * 0.3], -1)
        return img.astype(np.float32)

class Schematic(Scene):
    res = "full"
    look = "film_color"
    def setup(self):
        rng = self.rng
        self.segs = []
        nodes = [(rng.integers(3, 30) * 40, rng.integers(5, 16) * 40) for _ in range(60)]
        for i in range(90):
            a = nodes[rng.integers(len(nodes))]; b = nodes[rng.integers(len(nodes))]
            mid = (b[0], a[1])
            kind = rng.integers(5)
            self.segs.append((a, mid, b, kind))
        self.title = "THE DISTRIBUTION RELIGION"
    def frame(self, fi, t):
        im, d = draw_canvas(W, H, (14, 38, 88))
        for x in range(0, W, 40): d.line([(x, 0), (x, H)], fill=(26, 54, 110))
        for y in range(0, H, 40): d.line([(0, y), (W, y)], fill=(26, 54, 110))
        n = int(len(self.segs) * min(1, t / (self.d * 0.7)))
        col = (225, 235, 255)
        for a, mid, b, kind in self.segs[:n]:
            d.line([a, mid, b], fill=col, width=2)
            mx, my = (a[0] + mid[0]) / 2, a[1]
            if kind == 0:
                pts = [(mx - 30 + k * 7.5, my + (8 if k % 2 else -8)) for k in range(9)]
                d.rectangle([mx - 32, my - 10, mx + 32, my + 10], fill=(14, 38, 88)); d.line(pts, fill=col, width=2)
            elif kind == 1:
                d.rectangle([mx - 6, my - 18, mx + 6, my + 18], fill=(14, 38, 88)); d.line([(mx - 5, my - 16), (mx - 5, my + 16)], fill=col, width=3); d.line([(mx + 5, my - 16), (mx + 5, my + 16)], fill=col, width=3)
            elif kind == 2:
                d.polygon([(mx - 20, my - 22), (mx - 20, my + 22), (mx + 22, my)], outline=col, fill=(14, 38, 88))
            d.ellipse([a[0] - 4, a[1] - 4, a[0] + 4, a[1] + 4], fill=col)
        k = int(max(0, t - self.c["type_start"]) * TYPE_CPS)
        d.rectangle([60, H - 210, 980, H - 40], fill=(14, 38, 88))
        d.text((80, H - 200), self.title[:k], font=font("mono_b", 52), fill=(255, 255, 255))
        if t > 6:
            d.text((80, H - 110), "free to copy for individuals & nonprofits", font=font("mono", 30), fill=(200, 215, 255))
        return pil_f(im)

class VoiceSynth(Scene):
    res = "full"
    look = "crt"
    stateful = True
    def setup(self):
        b = self.seg["beats"][0]
        x, sr = sf.read(os.path.join(self.ctx["vo"], b["key"] + ".wav"))
        self.vo = np.concatenate([np.zeros(int(b["pre"] * sr)), x]).astype(np.float32); self.sr = sr
        self.hist = []
    def frame(self, fi, t):
        i0 = int(t * self.sr); n = 1600
        wv = self.vo[i0:i0 + n]
        if len(wv) < n: wv = np.pad(wv, (0, n - len(wv)))
        wv = np.interp(np.linspace(0, n - 1, 320), np.arange(n), wv)
        self.hist.insert(0, wv)
        self.hist = self.hist[:44]
        im, d = draw_canvas(W, H, (0, 0, 0))
        for k, line in enumerate(self.hist):
            y0 = 140 + k * 11
            amp = 380 * (1 - k / 60)
            xs = np.linspace(120 + k * 6, W - 120 - k * 6, 320)
            ys = y0 - np.abs(line) * amp * 0.9 - line * amp * 0.3
            col = hsv2rgb(np.array(0.35 + k * 0.012 + t * 0.03), np.array(0.7), np.array(1 - k / 50))
            pts = list(zip(xs, ys))
            d.polygon(pts + [(xs[-1], y0 + 30), (xs[0], y0 + 30)], fill=(0, 0, 0))
            d.line(pts, fill=tuple(int(v * 255) for v in col), width=2)
        return glow(pil_f(im), 6, 0.7)

class RuttEtra(Scene):
    res = "full"
    look = "crt"
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        u = min(1.0, t / max(self.d, 1))
        im, d = draw_canvas(W, H, (0, 0, 0))
        xs = np.linspace(80, W - 80, 300)
        xn = (xs - W / 2) / 300
        for k in range(58):
            yb = 70 + k * 10.5
            yn = (yb - H / 2) / 260
            r = np.sqrt(xn ** 2 + yn ** 2)
            ang = math.atan2(yn, 1) + t * 0.2
            body = np.exp(-((xn / 0.55) ** 2 + (yn / 0.85) ** 2) * 2) * (1 + 0.3 * np.sin(xn * 6 + t))
            viol = np.sin(xs * 0.05 * (1 + 0.5 * math.sin(t * 0.7)) + t * 9 + k * 0.4) * np.sin(xs * 0.011 + t * 3)
            ys = yb - body * 120 * (1 - 0.7 * u) - viol * 40 * u * (0.4 + 0.6 * np.exp(-r))
            pts = list(zip(xs, ys))
            v = int(140 + 110 * (k / 58))
            d.line(pts, fill=(v // 2, v, int(v * 0.8)), width=2)
        return glow(pil_f(im), 5, 0.6)

class Channels(Scene):
    res = "full"
    look = "crt"
    def setup(self):
        self.subs = []
    def frame(self, fi, t):
        edges = [0.0] + self.c["switch"]
        k = sum(1 for e in edges if t >= e) - 1
        lt = t - edges[k]
        kinds = ["bars", "liquid", "osc", "slit", "beck", "psych", "magnet", "whitney"]
        kind = kinds[k % len(kinds)]
        key = (k, kind)
        if not self.subs or self.subs[-1][0] != key:
            fake = dict(scene=kind, act="signal", idx=900 + k, f0=0, nf=60, beats=[dict(p={}, start=0, dur=5, vo=None, pre=0, key="c")])
            cls = dict(bars=None, liquid=Liquid, osc=Osc, slit=SlitScan, beck=Beck, psych=Psychedelia, magnet=Magnet, whitney=Whitney)[kind]
            self.subs.append((key, cls(fake, {}, self.ctx) if cls else None))
        sub = self.subs[-1][1]
        img = test_pattern() if sub is None else sub.frame(int(lt * FPS) + 30, lt + 1.25)
        img = upscale(img)
        if lt < 0.15:
            nz = self.rng.random((H // 4, W // 4)).astype(np.float32)
            img = upscale(np.repeat(nz[..., None], 3, -1) * 0.5 + 0.2)
        ch = text_img("CH %02d" % (2 + (k * 7) % 60), "mono_b", 48, fill=(120, 255, 140, 255))
        comp(img, ch, W - 260, 50, 1 if lt < 1.4 else 0.0)
        return img

class Buddha(Scene):
    res = "full"
    look = "film_color"
    def figure(self, d, cx, by, s, col):
        d.ellipse([cx - 120 * s, by - 60 * s, cx + 120 * s, by + 20 * s], fill=col)
        d.polygon([(cx - 95 * s, by - 20 * s), (cx + 95 * s, by - 20 * s), (cx + 55 * s, by - 190 * s), (cx - 55 * s, by - 190 * s)], fill=col)
        d.ellipse([cx - 48 * s, by - 290 * s, cx + 48 * s, by - 180 * s], fill=col)
        d.ellipse([cx - 22 * s, by - 312 * s, cx + 22 * s, by - 270 * s], fill=col)
        d.ellipse([cx - 58 * s, by - 255 * s, cx - 40 * s, by - 205 * s], fill=col); d.ellipse([cx + 40 * s, by - 255 * s, cx + 58 * s, by - 205 * s], fill=col)
    def frame(self, fi, t):
        im, d = draw_canvas(W, H, (20, 16, 12))
        d.rectangle([0, 520, W, H], fill=(30, 24, 18))
        self.figure(d, 360, 560, 1.0, (120, 92, 52))
        tvx, tvy, R = 900, 380, 150
        d.rectangle([tvx - 30, tvy + 120, tvx + 30, 560], fill=(40, 34, 28))
        d.ellipse([tvx - R - 22, tvy - R - 22, tvx + R + 22, tvy + R + 22], fill=(210, 205, 195))
        scr = Image.new("RGB", (2 * R, 2 * R), (70, 72, 74)); sd = ImageDraw.Draw(scr)
        self.figure(sd, R, 2 * R - 20, 0.55, (24, 24, 26))
        for y in range(0, 2 * R, 3): sd.line([(0, y), (2 * R, y)], fill=(60, 62, 64))
        m = Image.new("L", (2 * R, 2 * R), 0); ImageDraw.Draw(m).ellipse([0, 0, 2 * R, 2 * R], fill=255)
        im.paste(scr, (tvx - R, tvy - R), m)
        d.rectangle([600, 430, 650, 470], fill=(30, 30, 30)); d.line([(625, 470), (600, 560)], fill=(30, 30, 30), width=4); d.line([(625, 470), (650, 560)], fill=(30, 30, 30), width=4)
        d.ellipse([588, 438, 604, 454], fill=(70, 70, 80))
        img = pil_f(im)
        x, y = grid(W, H)
        img = img + 0.25 * np.exp(-(((x - 360) / 260) ** 2 + ((y - 380) / 220) ** 2))[..., None] * np.array([1, 0.8, 0.5], np.float32)
        sc = 1 + 0.12 * t / self.d
        cx, cy = 640, 380
        return bilinear(img, (x - cx) / sc + cx, (y - cy) / sc + cy, None)

# ---------------- Act IV ----------------
class Tango(Scene):
    look = "film_color"
    def setup(self):
        rng = self.rng
        self.chars = []
        for i in range(36):
            pts = [(rng.uniform(0.1, 0.9), rng.uniform(0.05, 0.95)) for _ in range(int(rng.integers(3, 6)))]
            self.chars.append(dict(pts=pts, per=float(rng.uniform(7, 14)), ph=float(rng.uniform(0, 1)),
                                   col=tuple(int(v) for v in rng.uniform(60, 220, 3)), h=float(rng.uniform(0.6, 1.1))))
        self.chars[0]["h"] = 0.55
    def floor_to_screen(self, fx, fz):
        y = lerp(205, 345, fz)
        half = lerp(190, 300, fz)
        return w / 2 + (fx - 0.5) * 2 * half, y, lerp(0.7, 1.15, fz)
    def frame(self, fi, t):
        im, d = draw_canvas(w, h, (150, 140, 120))
        d.polygon([(130, 205), (510, 205), (620, 360), (20, 360)], fill=(110, 82, 60))
        d.rectangle([130, 20, 510, 205], fill=(196, 186, 160))
        d.polygon([(0, 0), (130, 20), (130, 205), (20, 360), (0, 360)], fill=(170, 160, 138))
        d.polygon([(640, 0), (510, 20), (510, 205), (620, 360), (640, 360)], fill=(170, 160, 138))
        d.rectangle([180, 50, 270, 130], fill=(170, 210, 235)); d.line([(225, 50), (225, 130)], fill=(90, 70, 50), width=3)
        d.polygon([(545, 70), (590, 60), (590, 300), (545, 240)], fill=(90, 66, 44))
        d.rectangle([360, 120, 470, 205], fill=(120, 90, 60))
        n = tango_count(self.c, t) if "tango" in self.c else 30
        people = []
        for i, ch in enumerate(self.chars[:n]):
            u = ((t / ch["per"]) + ch["ph"]) % 1.0
            pts = ch["pts"] + [ch["pts"][0]]
            seg = u * (len(pts) - 1); j = int(seg); f = seg - j
            fx = lerp(pts[j][0], pts[j + 1][0], f); fz = lerp(pts[j][1], pts[j + 1][1], f)
            people.append((fz, fx, ch))
        bu = (t % 4.0) / 4.0
        bx = lerp(225, 330, bu); by = 90 + 200 * bu * bu - 60 * math.sin(bu * math.pi) if bu < 1 else 300
        for fz, fx, ch in sorted(people, key=lambda p: p[0]):
            sx, sy, s = self.floor_to_screen(fx, fz)
            hh = 70 * s * ch["h"]
            d.rounded_rectangle([sx - 9 * s, sy - hh, sx + 9 * s, sy], 6, fill=ch["col"])
            d.ellipse([sx - 7 * s, sy - hh - 15 * s, sx + 7 * s, sy - hh - 1], fill=(225, 190, 160))
        d.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=(220, 40, 40))
        d.text((w - 150, 12), "LAYER %02d/36" % n, font=font("mono_b", 16), fill=(30, 26, 20))
        return pil_f(im)

class Alley(Scene):
    res = "full"
    look = "film_color"
    def frame(self, fi, t):
        im, d = draw_canvas(W, H, (14, 12, 14))
        for r in range(0, H, 36):
            off = 40 if (r // 36) % 2 else 0
            for c in range(-80, W, 80):
                v = 26 + int(6 * math.sin(c * 0.37 + r))
                d.rectangle([c + off + 2, r + 2, c + off + 78, r + 34], fill=(v + 6, v, v - 2))
        dx0, dx1 = 760, 960
        d.rectangle([dx0, 180, dx1, 620], fill=(250, 214, 150))
        s = self.sents(0)
        guard = len(s) > 1 and t >= s[1]["start"] + 0.5
        if guard:
            gx = 860
            d.ellipse([gx - 32, 260, gx + 32, 330], fill=(10, 8, 8)); d.rounded_rectangle([gx - 70, 320, gx + 70, 620], 30, fill=(10, 8, 8))
        img = pil_f(im)
        x, y = grid(W, H)
        img += np.exp(-(((x - 860) / 300) ** 2 + ((y - 640) / 80) ** 2))[..., None] * np.array([0.5, 0.4, 0.25], np.float32)
        mx = 520
        im2 = Image.fromarray(to_u8(img)); d2 = ImageDraw.Draw(im2)
        d2.ellipse([mx - 30, 300, mx + 30, 370], fill=(6, 6, 6)); d2.rounded_rectangle([mx - 65, 360, mx + 65, 640], 30, fill=(6, 6, 6))
        img = pil_f(im2)
        glowv = 0.6 + 0.4 * math.sin(t * 1.6) ** 2
        img += glowv * np.exp(-(((x - 570) / 7) ** 2 + ((y - 352) / 7) ** 2))[..., None] * np.array([1.0, 0.45, 0.1], np.float32) * 1.5
        sm = 0.06 * np.exp(-((x - 580 - 30 * np.sin(y * 0.02 + t)) / 25) ** 2) * np.clip((352 - y) / 200, 0, 1)
        img += sm[..., None]
        return img

class MTV(Scene):
    res = "full"
    def frame(self, fi, t):
        bt = 60 / 100 * 2
        k = int(t / bt)
        pal = [(255, 40, 120), (40, 220, 255), (255, 230, 40), (130, 60, 255), (40, 255, 140)]
        bg = pal[k % 5]; fg = pal[(k + 2) % 5]; fg2 = pal[(k + 3) % 5]
        im, d = draw_canvas(W, H, bg)
        cx, cy = W / 2 + 200 * math.sin(t), H / 2
        a = t * 1.5
        pts = [(cx + 220 * math.cos(a + i * 2.094), cy + 220 * math.sin(a + i * 2.094)) for i in range(3)]
        d.polygon(pts, fill=fg)
        for i in range(6):
            x0 = (i * 260 + t * 200) % (W + 260) - 130
            d.line([(x0 + j * 30, 600 + (20 if j % 2 else -20)) for j in range(8)], fill=fg2, width=12)
        d.ellipse([200 - 80, 180 - 80, 200 + 80, 180 + 80], outline=(20, 20, 20), width=14)
        f = font("inter_x", 150)
        txt = "VIDEO"
        bb = d.textbbox((0, 0), txt, font=f)
        d.text(((W - bb[2]) / 2 + 6, H / 2 - bb[3] / 2 + 6), txt, font=f, fill=(20, 20, 20))
        d.text(((W - bb[2]) / 2, H / 2 - bb[3] / 2), txt, font=f, fill=(255, 255, 255))
        return pil_f(im)

class Chain(Scene):
    res = "full"
    def frame(self, fi, t):
        tt = int(t * 12) / 12
        rng = np.random.default_rng(int(t * 12))
        im, d = draw_canvas(W, H, (205, 170, 130))
        for i in range(12):
            x = (i * 137) % W; y = (i * 251) % H
            d.ellipse([x - 90, y - 60, x + 90, y + 60], fill=(190 + i * 2, 150, 110))
        s = self.sents(0)
        nodes = [("PRAGUE", "Jan Švankmajer", "banned, 1970s"), ("LONDON", "the Brothers Quay", "his biggest fans"), ("MTV", "Sledgehammer, 1986", "9 MTV awards")]
        starts = [s[0]["start"], s[1]["start"], s[2]["start"]] if len(s) > 2 else [0, 3, 6]
        xs = [230, 640, 1050]
        for i, (city, who, note) in enumerate(nodes):
            if t < starts[i]: continue
            jx, jy = rng.integers(-3, 4), rng.integers(-3, 4)
            x = xs[i] + jx; y = 330 + jy
            d.rounded_rectangle([x - 175, y - 120, x + 175, y + 120], 24, fill=(30, 22, 18))
            for (txt, fn, sz, col, dy) in ((city, "inter_x", 54, (255, 214, 120), -70), (who, "inter_b", 30, (255, 255, 255), 5), (note, "inter", 24, (220, 200, 180), 55)):
                f = font(fn, sz); bb = d.textbbox((0, 0), txt, font=f)
                d.text((x - bb[2] / 2, y + dy - bb[3] / 2), txt, font=f, fill=col)
            if i > 0:
                d.line([(xs[i - 1] + 180, 330), (xs[i] - 185, 330)], fill=(30, 22, 18), width=8)
                d.polygon([(xs[i] - 185, 330), (xs[i] - 205, 318), (xs[i] - 205, 342)], fill=(30, 22, 18))
        return pil_f(im)

class Faces(Scene):
    res = "full"
    look = "film_bw"
    def setup(self):
        self.rng2 = np.random.default_rng(11)
        self.cache = {}
    def face(self, k):
        if k in self.cache: return self.cache[k]
        r = np.random.default_rng(k * 13 + 5)
        im, d = draw_canvas(W, H, (30, 30, 30))
        cx, cy = 640, 380
        fw, fh = r.uniform(170, 220), r.uniform(230, 270)
        tone = int(r.uniform(120, 200))
        hair = int(r.uniform(10, 90))
        d.ellipse([cx - fw - 20, cy - fh - 40, cx + fw + 20, cy + fh * 0.2], fill=(hair, hair, hair))
        d.ellipse([cx - fw, cy - fh, cx + fw, cy + fh], fill=(tone, tone, tone))
        ey = cy - 40
        for sx in (-1, 1):
            ex = cx + sx * 80
            d.ellipse([ex - 38, ey - 16, ex + 38, ey + 16], fill=(235, 235, 235))
            d.ellipse([ex - 15, ey - 15, ex + 15, ey + 15], fill=(25, 25, 25))
            bw = r.uniform(-12, 12)
            d.line([(ex - 45, ey - 38 + bw * sx), (ex + 45, ey - 42 - bw * sx)], fill=(hair // 2, hair // 2, hair // 2), width=8)
        d.line([(cx, ey + 10), (cx - 14, cy + 60), (cx + 8, cy + 66)], fill=(tone - 50,) * 3, width=4)
        mw = r.uniform(40, 70); mo = r.uniform(4, 22)
        d.ellipse([cx - mw, cy + 110 - mo, cx + mw, cy + 110 + mo], fill=(60, 30, 30))
        img = blur(pil_f(im), 2.5)
        x, y = grid(W, H)
        img = img * (0.7 + 0.5 * np.exp(-(((x - 560) / 400) ** 2 + ((y - 300) / 300) ** 2)))[..., None]
        self.cache[k] = img
        return img
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        st = 2.2
        k = int(t / st); u = (t % st) / st
        a, b = self.face(k), self.face(k + 1)
        m = smooth((u - 0.45) / 0.55)
        if k % 2 == 0:
            return a * (1 - m) + b * m
        x, _ = grid(W, H)
        edge = smooth((x / W - (1.2 * m - 0.1)) / -0.2)[..., None]
        return a * (1 - edge) + b * edge

class Train(Scene):
    res = "full"
    def setup(self):
        rng = self.rng
        self.build = [(rng.uniform(60, 160), rng.uniform(80, 260), tuple(int(v) for v in rng.uniform(60, 140, 3))) for _ in range(200)]
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        sp = 520
        im, d = draw_canvas(W, H)
        for y in range(H):
            v = y / H
            d.line([(0, y), (W, y)], fill=(int(250 - 90 * v), int(170 - 40 * v), int(120 + 60 * v)))
        for k in range(-1, 4):
            x = (k * 500 - t * 40) % 1800 - 300
            d.ellipse([x - 400, 420, x + 400, 700], fill=(120, 90, 110))
        bt = 60 / TRAIN_BPM
        for i in range(-2, 60):
            tb = 0.6 + i * 4 * bt
            x = W / 2 + (tb - t) * sp * 1.6
            if -300 < x < W + 300:
                bw, bh, col = self.build[i % 200]
                d.rectangle([x - bw, 560 - bh, x + bw, 560], fill=col)
                for wy in range(int(560 - bh + 15), 545, 26):
                    for wx in range(int(x - bw + 12), int(x + bw - 12), 24):
                        d.rectangle([wx, wy, wx + 10, wy + 12], fill=(255, 220, 140))
        d.rectangle([0, 560, W, H], fill=(60, 50, 50))
        for tp in self.c.get("poles", []):
            x = W / 2 + (tp - t) * sp * 2.4
            if -60 < x < W + 60:
                d.rectangle([x - 10, 120, x + 10, 640], fill=(25, 22, 26))
                d.line([(x - 60, 150), (x + 60, 150)], fill=(25, 22, 26), width=8)
        d.line([(0, 160), (W, 160)], fill=(20, 20, 20), width=2)
        d.rounded_rectangle([60, 60, W - 60, H - 60], 60, outline=(30, 30, 34), width=60)
        d.rectangle([0, 0, W, 40], fill=(30, 30, 34)); d.rectangle([0, H - 40, W, H], fill=(30, 30, 34))
        return pil_f(im)

class LoopWalk(Scene):
    res = "full"
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        im, d = draw_canvas(W, H, (60, 64, 70))
        L, T_, R, B = 300, 140, 980, 580
        d.rounded_rectangle([L - 40, T_ - 40, R + 40, B + 40], 50, fill=(150, 150, 145))
        d.rounded_rectangle([L, T_, R, B], 30, fill=(110, 90, 80))
        for i in range(6):
            for j in range(4):
                d.rectangle([L + 30 + i * 108, T_ + 30 + j * 104, L + 120 + i * 108, T_ + 110 + j * 104], fill=(130 + (i * 7 + j * 13) % 40, 100, 90))
        lap = self.c.get("lap", LOOP_LAP_BEATS * 60 / LOOP_BPM)
        per = 2 * ((R - L) + (B - T_)) + 4 * 20 * 3.14
        def pos(u):
            u = u % 1.0
            L2, T2, R2, B2 = L - 20, T_ - 20, R + 20, B + 20
            pw = 2 * ((R2 - L2) + (B2 - T2))
            s = u * pw
            if s < R2 - L2: return L2 + s, T2
            s -= R2 - L2
            if s < B2 - T2: return R2, T2 + s
            s -= B2 - T2
            if s < R2 - L2: return R2 - s, B2
            s -= R2 - L2
            return L2, B2 - s
        n = 1 + int(t / lap)
        for k in range(min(n, 12)):
            u0 = (t - k * lap * 0.0) / lap - k * 0.083
            col = tuple(int(v) for v in hsv2rgb(np.array(k * 0.13), np.array(0.6), np.array(1.0)) * 255)
            for tr in range(12):
                x, y = pos(u0 - tr * 0.004)
                r = 9 - tr * 0.6
                d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(255 * (1 - tr / 12)),))
        d.text((W - 220, 40), "LAP %d" % n, font=font("mono_b", 40), fill=(255, 255, 255))
        return pil_f(im)

# ---------------- Act V ----------------
class Psychedelia(Scene):
    res = "full"
    stateful = True
    def setup(self):
        self.gw, self.gh = 160, 90
        self.age = np.full((self.gh, self.gw), 999, np.int32)
        self.col0 = np.zeros((self.gh, self.gw), np.int32)
        self.seq = [6, 4, 2, 10, 8, 7, 1, 13, 3, 14, 6]
        self.bursts = []
    def frame(self, fi, t):
        i, bt, b = self.beat(t)
        smoothm = b["p"].get("smooth", False)
        cx = 80 + 55 * math.sin(t * 0.7) * math.cos(t * 0.23); cy = 45 + 30 * math.sin(t * 0.53)
        if fi % 3 == 0:
            self.bursts.append([cx, cy, 0, int(self.rng.integers(len(self.seq)))])
        self.age += 1
        nb = []
        for bx, by, r, c0 in self.bursts:
            if r > 16: continue
            for a in np.linspace(0, 2 * np.pi, 8 + r * 4, endpoint=False):
                x = int(bx - 80 + r * math.cos(a)); y = int(by - 45 + r * math.sin(a))
                for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                    gx, gy = 80 + sx * x, 45 + sy * y
                    if 0 <= gx < self.gw and 0 <= gy < self.gh:
                        self.age[gy, gx] = 0; self.col0[gy, gx] = c0 + r
            nb.append([bx, by, r + 1, c0])
        self.bursts = nb
        idx = (self.col0 + self.age // 2) % len(self.seq)
        pal = C64[np.array(self.seq)[idx]]
        pal = pal * (self.age < 40)[..., None]
        img = np.repeat(np.repeat(pal, 8, 0), 8, 1).astype(np.float32)
        if smoothm:
            img = glow(blur(img, 6), 10, 0.6)
        return img

class WireGrid(Scene):
    res = "full"
    def frame(self, fi, t):
        im, d = draw_canvas(W, H, (6, 2, 20))
        for y in range(0, 360):
            v = y / 360
            d.line([(0, y), (W, y)], fill=(int(20 + 60 * v), int(5 + 10 * v), int(40 + 60 * v)))
        d.ellipse([W / 2 - 110, 200, W / 2 + 110, 420], fill=(255, 120, 60))
        for k in range(8):
            d.rectangle([0, 330 + k * 9, W, 333 + k * 9], fill=(6, 2, 20))
        nz, nx = 36, 41
        cam = t * 3.0
        rows = []
        for iz in range(nz):
            z = iz + 1 - (cam % 1.0)
            wz = iz + math.floor(cam)
            row = []
            for ix in range(nx):
                xw = (ix - nx // 2) * 1.2
                yw = 1.6 * math.sin(xw * 0.5 + wz * 0.35) * math.cos(wz * 0.21 - xw * 0.2) + (abs(xw) * 0.15) ** 2
                sy = 360 + (2.2 - yw) * 260 / z
                sx = W / 2 + xw * 420 / z
                row.append((sx, sy))
            rows.append(row)
        for iz in range(nz - 1, -1, -1):
            a = 1 - iz / nz
            col = (int(255 * a), int(60 * a), int(220 * a))
            d.line(rows[iz], fill=col, width=2)
            if iz < nz - 1:
                for ix in range(0, nx, 2):
                    d.line([rows[iz][ix], rows[iz + 1][ix]], fill=(int(40 * a), int(220 * a), int(255 * a)), width=2)
        return glow(pil_f(im), 6, 0.5)

class Mandel(Scene):
    res = "full"
    def setup(self):
        d = self.d + 1
        cmd = ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
               f"mandelbrot=s={w}x{h}:rate={FPS}:start_x=-0.743643887037158704752191506114774:start_y=-0.131825904205311970493132056385139:start_scale=3:end_scale=0.00002:end_pts={d * FPS}:maxiter=2000:outer=normalized_iteration_count:inner=black",
               "-t", str(d), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.vhs = None
    def frame(self, fi, t):
        raw = self.proc.stdout.read(w * h * 3)
        if len(raw) < w * h * 3:
            img = getattr(self, "last", np.zeros((h, w, 3), np.float32))
        else:
            img = np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
            self.last = img
        lum = img @ np.array([0.3, 0.5, 0.2], np.float32)
        img = hsv2rgb(lum * 1.5 + t * 0.03, np.full_like(lum, 0.9), np.clip(lum * 1.15, 0, 0.92) ** 1.1)
        img = upscale(img)
        i, bt, b = self.beat(t)
        if b["p"].get("vhs"):
            if self.vhs is None: self.vhs = Look("vhs", 3)
            img = self.vhs(img, fi)
            comp(img, text_img("PLAY >", "mono_b", 40), W - 260, 50, 1)
        return img

class Tunnel(Scene):
    def setup(self):
        x, y = grid(w, h)
        dx, dy = (x - w / 2) / h, (y - h / 2) / h
        self.r = np.sqrt(dx * dx + dy * dy) + 1e-3; self.a = np.arctan2(dy, dx)
    def frame(self, fi, t):
        bt = 60 / RAVE_BPM
        pulse = 1 + 0.06 * math.exp(-((t % bt) / bt) * 6)
        v = 0.35 / self.r * pulse + t * 1.6
        u = self.a / math.pi * 3 + t * 0.2
        u = np.abs(((u * 2) % 2) - 1)
        ring = (np.floor(v * 4) % 2)
        hue = 0.75 + 0.15 * np.sin(v * 0.7) + t * 0.03
        img = hsv2rgb(hue + ring * 0.25 + u * 0.1, np.full_like(v, 0.85), np.clip(0.35 + 0.65 * ring * u, 0, 1))
        return img * np.clip(self.r * 4, 0, 1)[..., None]

class Flame(Scene):
    stateful = True
    def setup(self):
        self.n = 160000
        self.p_ = self.rng.uniform(-1, 1, (self.n, 2)).astype(np.float32)
        self.cc = self.rng.uniform(0, 1, self.n).astype(np.float32)
        self.hist = np.zeros((h, w, 4), np.float32)
        self.base = [np.array(v, np.float32) for v in ([0.56, -0.47, 0.31, 0.53, 0.1, -0.2], [0.6, 0.35, -0.42, 0.55, -0.3, 0.25], [-0.42, 0.25, 0.3, 0.4, 0.4, 0.1])]
        self.colv = np.array([0.0, 0.5, 0.9], np.float32)
        for _ in range(20): self.iterate(0.0, acc=False)
    def iterate(self, t, acc=True):
        k = self.rng.integers(0, 3, self.n)
        x, y = self.p_[:, 0], self.p_[:, 1]
        nx = np.empty_like(x); ny = np.empty_like(y)
        for j in range(3):
            m = k == j
            a, b, c, d, e, f = self.base[j] * (1 + 0.15 * np.sin(t * (0.11 + 0.05 * j) + np.arange(6)))
            X = a * x[m] + b * y[m] + e; Y = c * x[m] + d * y[m] + f
            r2 = X * X + Y * Y + 1e-6
            if j == 0: X, Y = np.sin(X) * 1.1, np.sin(Y) * 1.1
            elif j == 1: X, Y = X / r2, Y / r2
            else:
                s, cs = np.sin(r2), np.cos(r2); X, Y = X * s - Y * cs, X * cs + Y * s
            nx[m], ny[m] = X, Y
            self.cc[m] = (self.cc[m] + self.colv[j]) * 0.5
        bad = ~np.isfinite(nx) | ~np.isfinite(ny) | (np.abs(nx) > 50) | (np.abs(ny) > 50)
        nx[bad] = self.rng.uniform(-1, 1, bad.sum()); ny[bad] = self.rng.uniform(-1, 1, bad.sum())
        self.p_[:, 0], self.p_[:, 1] = nx, ny
        if not acc: return
        a = t * 0.05
        rx = nx * math.cos(a) - ny * math.sin(a); ry = nx * math.sin(a) + ny * math.cos(a)
        px = (w / 2 + rx * 120).astype(np.int32); py = (h / 2 + ry * 120).astype(np.int32)
        ok = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        idx = py[ok] * w + px[ok]
        col = hsv2rgb(self.cc[ok] * 0.8 + 0.55 + t * 0.01, np.full(ok.sum(), 0.8, np.float32), np.ones(ok.sum(), np.float32))
        for ch in range(3):
            self.hist[..., ch].flat[:] += np.bincount(idx, col[:, ch], w * h)
        self.hist[..., 3].flat[:] += np.bincount(idx, None, w * h)
    def frame(self, fi, t):
        t = t + getattr(self, "toff", 0.0)
        self.hist *= 0.55
        for _ in range(3): self.iterate(t)
        cnt = self.hist[..., 3:4]
        alpha = np.log1p(cnt) / np.log1p(cnt.max() + 1e-6)
        col = self.hist[..., :3] / (cnt + 1e-6)
        img = col * alpha ** (1 / 2.2)
        return np.clip(img * 1.2, 0, 1)

# ---------------- Act VI ----------------
class Blocks(Scene):
    res = "full"
    look = "glitch"
    def setup(self):
        fake = dict(scene="liquid", act="noise", idx=777, f0=0, nf=10, beats=[dict(p={}, start=0, dur=5, vo=None, pre=0, key="b")])
        self.base = upscale(Liquid(fake, {}, self.ctx).frame(0, 8.0))
        self.vec = self.rng.normal(0, 1, (9, 16, 2))
    def frame(self, fi, t):
        img = self.base.copy() * 0.8
        im = Image.fromarray(to_u8(img)); d = ImageDraw.Draw(im, "RGBA")
        bs = 80
        s = self.sents(0)
        phase2 = len(s) > 2 and t >= s[2]["start"]
        for r in range(9):
            for c in range(16):
                x0, y0 = c * bs, r * bs
                d.rectangle([x0, y0, x0 + bs, y0 + bs], outline=(255, 255, 255, 70))
                if phase2 and (r * 16 + c) % 3 == 0:
                    vx, vy = self.vec[r, c] * 22
                    cx, cy = x0 + bs / 2, y0 + bs / 2
                    wob = math.sin(t * 2 + r + c)
                    d.line([(cx, cy), (cx + vx * wob, cy + vy * wob)], fill=(255, 255, 80, 230), width=4)
                    d.ellipse([cx + vx * wob - 5, cy + vy * wob - 5, cx + vx * wob + 5, cy + vy * wob + 5], fill=(255, 255, 80, 230))
        d.rectangle([0, H - 120, W, H], fill=(0, 0, 0, 200))
        for k in range(14):
            x = 40 + k * 86
            iframe = k == 0
            d.rectangle([x, H - 100, x + 72, H - 40], fill=(255, 80, 80, 255) if iframe else (60, 160, 255, 255))
            d.text((x + 24, H - 92), "I" if iframe else "P", font=font("mono_b", 36), fill=(255, 255, 255))
        d.text((40, H - 160), "1 complete picture   →   then only instructions", font=font("mono_b", 30), fill=(255, 255, 255))
        return pil_f(im)

class Mosh(Scene):
    res = "full"
    look = "glitch"
    def setup(self):
        tmp = os.path.join(self.ctx["work"], "mosh"); os.makedirs(tmp, exist_ok=True)
        srcs = [("liquid", 3.5), ("train", 11.0), ("whitney", self.d - 14.5 + 1)]
        raw = os.path.join(tmp, "src.avi")
        enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS),
                                "-i", "-", "-c:v", "mpeg4", "-q:v", "3", "-g", "100000", "-bf", "0",
                                "-force_key_frames", ",".join(str(x) for x in (0, 3.5, 14.5)), "-f", "avi", raw], stdin=subprocess.PIPE)
        for name, dur in srcs:
            fake = dict(scene=name, act="noise", idx=555, f0=0, nf=int(dur * FPS), beats=[dict(p={}, start=0, dur=dur, vo=None, pre=0, key="m")])
            c = cues(fake) if name == "train" else {}
            if name == "train": c["poles"] = list(np.arange(0.2, dur, 60 / TRAIN_BPM))
            sc = SCENES[name](fake, c, self.ctx)
            for k in range(int(dur * FPS)):
                img = sc.frame(k, k / FPS)
                if img.shape[0] != h: img = upscale(img, (w, h))
                enc.stdin.write(to_u8(img).tobytes())
        enc.stdin.close(); enc.wait()
        moshed = os.path.join(tmp, "moshed.avi")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-c", "copy", "-bsf:v", "noise=drop=key*gt(n\\,0)", "-f", "avi", moshed], check=True)
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "quiet", "-i", moshed, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.saved = False
    def frame(self, fi, t):
        raw = self.proc.stdout.read(w * h * 3)
        if len(raw) == w * h * 3:
            self.last = np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        img = upscale(self.last)
        if not self.saved and t > 6.0:
            Image.fromarray(to_u8(img)).save(os.path.join(self.ctx["stills"], "mosh.png")); self.saved = True
        return img

class Dream(Scene):
    res = "full"
    def setup(self):
        dd = os.path.join(self.ctx["work"], "dream")
        self.frames = sorted(os.path.join(dd, f) for f in os.listdir(dd) if f.endswith(".png"))
        self.fps = 6.0
        self.cache = {}
    def get(self, k):
        k = max(0, min(len(self.frames) - 1, k))
        if k not in self.cache:
            self.cache = {kk: v for kk, v in self.cache.items() if kk >= k - 1}
            self.cache[k] = to_f(Image.open(self.frames[k]).convert("RGB").resize((W, H), Image.BICUBIC))
        return self.cache[k]
    def frame(self, fi, t):
        x = t * self.fps; k = int(x); u = x - k
        a, b = self.get(k), self.get(k + 1)
        xg, yg = grid(W, H)
        z = 1 + 0.04 * u
        a2 = bilinear(a, (xg - W / 2) / z + W / 2, (yg - H / 2) / z + H / 2, None)
        return a2 * (1 - u) + b * u

class Prompt(Scene):
    res = "full"
    def setup(self):
        dd = os.path.join(self.ctx["work"], "dream")
        fr = sorted(f for f in os.listdir(dd) if f.endswith(".png"))
        self.bgs = [to_f(Image.open(os.path.join(dd, f)).convert("RGB").resize((W, H))) for f in fr[-40::4]]
    def frame(self, fi, t):
        s = self.sents(0)
        gen = s[1]["start"] - 1.0 if len(s) > 1 else 5.0
        k = int(max(0, t - gen) * 2) % len(self.bgs)
        bg = self.bgs[k] * smooth((t - gen) / 1.5)
        bg = bg if t > gen + 1.5 else blur(bg, 12)
        img = bg + 0.03
        im = Image.fromarray(to_u8(img)); d = ImageDraw.Draw(im, "RGBA")
        bx0, by0, bx1, by1 = 190, 300, 1090, 420
        d.rounded_rectangle([bx0, by0, bx1, by1], 28, fill=(20, 20, 26, 230), outline=(120, 120, 140, 255), width=2)
        txt = "a surreal psychedelic dream, endless"
        n = int(max(0, t - self.c["type_start"]) * TYPE_CPS)
        cur = "|" if int(t * 2) % 2 == 0 else ""
        d.text((bx0 + 36, by0 + 36), txt[:n] + cur, font=font("inter", 40), fill=(240, 240, 245))
        d.rounded_rectangle([bx1 - 190, by1 + 24, bx1, by1 + 84], 20, fill=(240, 240, 245, 255) if t < gen else (120, 120, 130, 255))
        d.text((bx1 - 160, by1 + 34), "Generate", font=font("inter_b", 30), fill=(20, 20, 26))
        return pil_f(im)

class Recipe(Feedback):
    res = "full"
    def setup(self):
        super().setup()
        self.txt = text_img(self.p.get("text", ""), "inter_b", 52, align="center")
    def frame(self, fi, t):
        self.seg["beats"][0]["p"] = dict(mode="mandala", spin=1.2)
        img = upscale(Feedback.frame(self, fi, t)) * 0.55
        comp_center(img, self.txt, W / 2, H / 2, smooth((t - 1.0) / 0.8))
        return img

class CRTOff(Feedback):
    res = "full"
    def setup(self):
        super().setup()
        for k in range(48):
            self.seg["beats"][0]["p"] = dict(mode="mandala", spin=1.6)
            self.last = Feedback.frame(self, k, k / FPS)
    def frame(self, fi, t):
        img = upscale(np.clip(self.last, 0, 1))
        off = self.c["off"]
        u = (t - off)
        if u < 0: return img
        x, y = grid(W, H)
        sy = max(0.004, 1 - smooth(u / 0.35))
        sx = 1.0 if u < 0.35 else max(0.003, 1 - smooth((u - 0.35) / 0.35))
        out = bilinear(img, (x - W / 2) / sx + W / 2, (y - H / 2) / sy + H / 2, 0.0)
        bright = 1 + 2 * smooth(u / 0.5)
        fade = 1 - smooth((u - 0.7) / 1.2)
        dot = np.exp(-(((x - W / 2) / 8) ** 2 + ((y - H / 2) / 8) ** 2))[..., None] * smooth((u - 0.6) / 0.1)
        return np.clip(out * bright, 0, 1) * fade + dot * fade

class Black(Scene):
    res = "full"
    def frame(self, fi, t): return np.zeros((H, W, 3), np.float32)

class Credits(Scene):
    res = "full"
    def setup(self):
        from script import CREDITS
        imgs = []
        for txt, kind in CREDITS:
            if kind == "gap": imgs.append(None); continue
            f, s, c = dict(title=("inter_x", 96, (255, 255, 255, 255)), sub=("inter_l", 34, (220, 220, 220, 255)),
                           head=("inter_b", 34, (255, 200, 120, 255)), body=("inter", 28, (215, 215, 215, 255)))[kind]
            imgs.append(text_img(txt, f, s, fill=c))
        hh = sum(60 if i is None else i.size[1] + 10 for i in imgs)
        self.sheet = Image.new("RGBA", (W, hh + H * 2), (0, 0, 0, 0))
        y = H
        for i in imgs:
            if i is None: y += 60; continue
            self.sheet.paste(i, ((W - i.size[0]) // 2, y), i); y += i.size[1] + 10
        self.total = y
    def frame(self, fi, t):
        img = np.zeros((H, W, 3), np.float32)
        y = (self.total) * min(1, t / (self.d - 3))
        comp(img, self.sheet, 0, -y, 1)
        return img * (1 - smooth((t - self.d + 2) / 2))


class Clip(Scene):
    res = "full"
    def setup(self):
        from script import FILMS
        p = self.p
        src = p.get("path") or FILMS[p["film"]]
        dur = self.d + 0.6
        vf = ("fps=24,split[a][b];[b]scale=48:27,boxblur=2:1,scale=1280:720:flags=bilinear,eq=brightness=-0.22:saturation=0.7[bg];"
              "[a]scale=1280:720:force_original_aspect_ratio=decrease:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=rgb24")
        self.src, self.vf = src, vf
        self.ranges = [tuple(r) for r in p.get("ranges", [(p["start"], dur)])]
        if "ranges" in p:
            self.ranges[-1] = (self.ranges[-1][0], self.ranges[-1][1] + 0.6)
        self.proc = self.open(self.ranges.pop(0))
        self.last = np.zeros((H, W, 3), np.float32)
    def open(self, r):
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(r[0]), "-i", self.src, "-t", str(r[1]), "-an",
                                 "-vf", self.vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    def frame(self, fi, t):
        raw = self.proc.stdout.read(W * H * 3)
        if len(raw) < W * H * 3 and self.ranges:
            self.proc = self.open(self.ranges.pop(0))
            raw = self.proc.stdout.read(W * H * 3)
        if len(raw) == W * H * 3:
            self.last = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        f = min(1.0, t / 0.25, max(0.0, (self.d - t) / 0.2)) if not self.p.get("nofade") else 1.0
        return self.last * f

class Scope(VoiceSynth):
    def setup(self):
        x, sr = sf.read(self.ctx["music"], start=int(self.seg["f0"] / FPS * 48000), frames=int(self.d * 48000) + 48000)
        self.vo = x.mean(1).astype(np.float32) * 1.6; self.sr = sr
        self.hist = []

class PasDeDeux(Scene):
    """McLaren's optical-printer technique: each dancer re-exposed again and again, a few frames late."""
    look = "film_bw"
    S = 1.55
    def pose(self, t, who):
        S = self.S
        ph = 0.0 if who == 0 else 2.1
        sgn = -1 if who == 0 else 1
        sep = 78 + 48 * math.cos(2 * math.pi * t / 22.0)
        hx = w / 2 + sgn * sep + 14 * math.sin(t * 0.7 + ph)
        hy = 206 - 8 * max(0.0, math.sin(t * 1.3 + ph)) ** 2
        turn = math.cos(t * 0.9 + ph) if (int((t + ph) / 5.5) % 2 == 0) else 1.0
        tilt = 0.2 * math.sin(t * 1.1 + ph) * sgn
        def pt(x, y, a, L):
            return x + L * S * math.sin(a) * turn, y - L * S * math.cos(a)
        neck = pt(hx, hy, tilt, 64)
        head = pt(neck[0], neck[1], tilt, 13)
        A = []
        sh = pt(hx, hy, tilt, 58)
        for side in (-1, 1):
            a1 = side * (1.15 + 1.35 * (0.5 + 0.5 * math.sin(t * 1.4 + ph + side * 0.9)))
            a2 = a1 + side * 0.45 * math.sin(t * 1.8 + ph)
            el = pt(sh[0], sh[1], a1, 34); hd = pt(el[0], el[1], a2, 32)
            A.append((sh, el, hd))
        L = []
        lift = 1.5 * max(0.0, math.sin(t * 0.8 + ph))
        for side, ang in ((-1, math.pi + 0.06 * sgn), (1, math.pi - sgn * lift)):
            kn = pt(hx, hy, ang, 44); ft = pt(kn[0], kn[1], ang + 0.12 * side, 42)
            L.append(((hx, hy), kn, ft))
        return (hx, hy), sh, neck, head, A, L, tilt, turn
    def body(self, d, P, v, who, t):
        S = self.S
        hip, sh, neck, head, A, L, tilt, turn = P
        nx, ny = math.cos(tilt), math.sin(tilt)
        hw, sw = 8 * S * max(0.35, abs(turn)), 15 * S * max(0.35, abs(turn))
        d.polygon([(hip[0] - hw * nx, hip[1] - hw * ny), (hip[0] + hw * nx, hip[1] + hw * ny),
                   (sh[0] + sw * nx, sh[1] + sw * ny), (sh[0] - sw * nx, sh[1] - sw * ny)], fill=v)
        if who == 1:
            sway = 10 * S * math.sin(t * 1.6)
            d.polygon([(hip[0] - hw, hip[1] - 4), (hip[0] + hw, hip[1] - 4),
                       (hip[0] + 34 * S + sway, hip[1] + 30 * S), (hip[0] - 34 * S + sway, hip[1] + 30 * S)], fill=v)
        for a in L:
            d.line(list(a), fill=v, width=int(9 * S), joint="curve")
            for j in a[1:]: d.ellipse([j[0] - 4.5 * S, j[1] - 4.5 * S, j[0] + 4.5 * S, j[1] + 4.5 * S], fill=v)
        for a in A:
            d.line(list(a), fill=v, width=int(6 * S), joint="curve")
            for j in a: d.ellipse([j[0] - 3 * S, j[1] - 3 * S, j[0] + 3 * S, j[1] + 3 * S], fill=v)
        d.line([sh, neck], fill=v, width=int(5 * S))
        r = 8.5 * S
        d.ellipse([head[0] - r * 0.85, head[1] - r, head[0] + r * 0.85, head[1] + r], fill=v)
    def frame(self, fi, t):
        im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
        n_echo = int(round(11 * smooth((t - 2.0) / 9.0)))
        dt = 0.13
        for k in range(n_echo, -1, -1):
            v = int(255 * (0.84 ** k) * (0.95 if k == 0 else 0.62))
            for who in (0, 1):
                self.body(d, self.pose(t - k * dt, who), v, who, t - k * dt)
        a = to_f(im.filter(ImageFilter.GaussianBlur(1.4)))
        img = np.stack([a * 0.92, a * 0.96, a], -1)
        img = glow(img, 8, 0.65, 2)
        x, y = grid(w, h)
        floor = np.clip((y - 320) / 50, 0, 1) * 0.05
        return img + floor[..., None]

SCENES = dict(feedback=Feedback, title=Title, actcard=ActCard, montage=Montage, still=Still, eye=Eye, type=TypeCard,
              door=Door, steps=Steps, direct=Direct, synchromy=Synchromy, osc=Osc, dome=Dome, harmonograph=Harmonograph,
              whitney=Whitney, leader=Leader, liquid=Liquid, slitscan=SlitScan, tvwall=TVWall, magnet=Magnet, vhs=VHS,
              colorizer=Colorizer, beck=Beck, schematic=Schematic, voicesynth=VoiceSynth, ruttetra=RuttEtra,
              channels=Channels, buddha=Buddha, tango=Tango, alley=Alley, mtv=MTV, chain=Chain, faces=Faces, train=Train,
              loopwalk=LoopWalk, psychedelia=Psychedelia, wiregrid=WireGrid, mandel=Mandel, tunnel=Tunnel, flame=Flame,
              blocks=Blocks, mosh=Mosh, dream=Dream, prompt=Prompt, recipe=Recipe, crtoff=CRTOff, black=Black,
              credits=Credits, clip=Clip, scope=Scope, pasdedeux=PasDeDeux)
