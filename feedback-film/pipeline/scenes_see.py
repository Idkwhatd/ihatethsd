# "On seeing" interludes: science of the eye, then philosophy of seeing. All drawings are original.
import math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from fx import *
from scenes import Scene, Feedback, Liquid, C64

FX_ROOT = __import__("os").environ.get("FX_ROOT", "/tmp/fx")  # working folder for media, renders and caches
AMBER = (255, 184, 92)
CYAN = (110, 220, 255)
INK = (235, 232, 224)
DIM = (150, 150, 160)
MUY = f"{FX_ROOT}/arch/muy"

def bg_grad(top=(10, 14, 26), bot=(4, 6, 12)):
    im, d = draw_canvas(W, H)
    for y in range(H):
        u = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(top, bot)))
    return im

def ftext(d, xy, s, size=30, fill=INK, name="inter", anchor="la"):
    d.text(xy, s, font=font(name, size), fill=fill, anchor=anchor)

def stage_times(sents, idx):
    return [sents[i]["start"] if i < len(sents) else 1e9 for i in idx]

def muy_frames():
    fs = sorted(f for f in os.listdir(MUY) if f.endswith(".png"))
    return [Image.open(os.path.join(MUY, f)).convert("RGB") for f in fs]

# ---------------- 1. The first eye ----------------
class EyeEvo(Scene):
    res = "full"
    def setup(self):
        self.bg = bg_grad()
        s = self.sents(0)
        self.st = stage_times(s, [1, 2, 3, 4])
        self.gen_t = stage_times(s, [5])[0]
    def curve(self, s):
        cx, cy, R = 800, 330, 160
        n = 90
        flat = [(cx + 120, cy + y) for y in np.linspace(-170, 170, n)]
        def arc(ap):
            a0 = math.pi - ap / 2
            return [(cx + R * math.cos(a), cy + R * math.sin(a)) for a in np.linspace(-a0, a0, n)]
        if s <= 1:
            A, B, u = flat, arc(math.pi * 1.0), smooth(s)
        elif s <= 2:
            A, B, u = arc(math.pi * 1.0), arc(0.28), smooth(s - 1)
        else:
            A, B, u = arc(0.28), arc(0.36), smooth(s - 2)
        return [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for a, b in zip(A, B)], (cx, cy, R)
    def frame(self, fi, t):
        s = float(sum(smooth((t - x) / 1.6) for x in self.st[1:]))
        if t < self.st[0]: s = 0.0
        im = self.bg.copy(); d = ImageDraw.Draw(im, "RGBA")
        pts, (cx, cy, R) = self.curve(s)
        ox, oy = 210, 330
        d.line([(ox, oy + 60), (ox, oy - 60)], fill=AMBER, width=6)
        d.polygon([(ox - 22, oy - 50), (ox + 22, oy - 50), (ox, oy - 86)], fill=AMBER)
        ftext(d, (ox, oy + 90), "the world", 24, DIM, anchor="ma")
        lit = max(0.0, 1 - abs(s - 0.0)) if s < 1 else 0.0
        ap_x, ap_y = cx - R, cy
        if s > 1.3:
            for (px, py) in ((ox, oy - 86), (ox, oy + 60)):
                tx, ty = ap_x, ap_y
                dx, dy = tx - px, ty - py
                ex = cx + R * 0.98; ey = ty + dy / dx * (ex - tx)
                a = int(150 * min(1, s - 1.3))
                d.line([(px, py), (tx, ty), (ex, ey)], fill=(255, 220, 160, a), width=2)
        if s < 1.3:
            for k in range(9):
                yy = oy - 80 + k * 20
                for (qx, qy) in pts[10::16]:
                    d.line([(ox + 10, yy), (qx, qy)], fill=(255, 220, 160, int(18 * (1.3 - s))), width=1)
        d.line(pts, fill=AMBER, width=10, joint="curve")
        for i in range(2, len(pts) - 2, 3):
            (x0, y0), (x1, y1) = pts[i - 1], pts[i + 1]
            nx, ny = -(y1 - y0), (x1 - x0); L = math.hypot(nx, ny) + 1e-6
            d.line([(pts[i][0], pts[i][1]), (pts[i][0] - nx / L * 14, pts[i][1] - ny / L * 14)], fill=(255, 210, 140, 200), width=3)
        if s > 2.3:
            a = int(255 * min(1, (s - 2.3) / 0.6))
            d.ellipse([ap_x - 26, ap_y - 48, ap_x + 26, ap_y + 48], fill=(140, 200, 255, int(a * 0.35)), outline=(160, 220, 255, a), width=3)
            d.ellipse([cx - R + 6, cy - R + 6, cx + R - 6, cy + R - 6], fill=(80, 120, 200, int(a * 0.08)))
        img = pil_f(im)
        if s > 1.5:
            sharp = min(1.0, max(0.0, s - 2.0))
            spr = Image.new("L", (90, 160), 0); sd = ImageDraw.Draw(spr)
            sd.line([(45, 20), (45, 120)], fill=255, width=6); sd.polygon([(30, 112), (60, 112), (45, 140)], fill=255)
            spr = spr.filter(ImageFilter.GaussianBlur(float(7 * (1 - sharp) + 0.8)))
            m = to_f(spr)[..., None] * min(1.0, (s - 1.5) * 2)
            x0, y0 = int(cx + R * 0.82 - 45), int(cy - 80)
            img[y0:y0 + 160, x0:x0 + 90] = img[y0:y0 + 160, x0:x0 + 90] * (1 - m) + m * np.array([1.0, 0.85, 0.6], np.float32)
        if s < 1.0 and t > self.st[0]:
            img += lit * 0.12 * np.exp(-((grid(W, H)[0] - (cx + 120)) / 30) ** 2)[..., None] * np.array([1, 0.8, 0.5], np.float32)
        lab = Image.new("RGBA", (W, 80), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
        names = ["light-sensitive patch", "cup", "pinhole", "lens"]
        xs = [200, 560, 800, 1040]
        for i, nm in enumerate(names):
            on = 1 - min(1, abs(s - i))
            col = tuple(int(DIM[j] + (AMBER[j] - DIM[j]) * on) for j in range(3))
            ftext(ld, (xs[i], 20), nm, 28 if on > 0.5 else 24, col, "inter_b" if on > 0.5 else "inter", anchor="ma")
        comp(img, lab, 0, H - 205, 1)
        if t > self.gen_t:
            u = smooth((t - self.gen_t) / 4.0)
            card = text_img(f"≈ {int(364000 * u):,} generations", "inter_b", 40, fill=(255, 255, 255, 255))
            cite = text_img("Nilsson & Pelger, 1994", "inter", 24, fill=(200, 200, 210, 255))
            comp(img, card, 760, 70, smooth((t - self.gen_t) / 0.5)); comp(img, cite, 762, 125, smooth((t - self.gen_t) / 0.5))
        return img

# ---------------- 2. A fish's eye ----------------
class FishEye(Scene):
    res = "full"
    def setup(self):
        s = self.sents(0)
        self.tB, self.tBS, self.tC, self.tC2, self.tC3 = stage_times(s, [2, 3, 4, 5, 6])
        self.bgA = bg_grad((6, 30, 52), (2, 8, 18))
        self.bgB = bg_grad((12, 12, 20), (4, 4, 8))
        r = np.random.default_rng(3)
        self.snow = r.uniform(0, 1, (260, 3))
    def fish(self, t):
        im = self.bgA.copy(); d = ImageDraw.Draw(im, "RGBA")
        for x, y, z in self.snow:
            px = (x * W - t * 12 * (0.3 + z)) % W; py = (y * H + t * 6 * z) % H
            v = int(60 + 120 * z); d.ellipse([px - 1.5 * z, py - 1.5 * z, px + 1.5 * z, py + 1.5 * z], fill=(v, v + 20, v + 30, 160))
        hx = min(640, 120 + t * 90); hy = 360
        L = 560; n = 60
        top, bot = [], []
        for i in range(n):
            u = i / (n - 1)
            x = hx - u * L
            y = hy + 26 * math.sin(u * 7 - t * 4) * u
            th = 44 * (1 - u) ** 0.6 * (0.6 + 0.4 * math.sin(math.pi * min(1, u * 3 + 0.2)))
            top.append((x, y - th)); bot.append((x, y + th))
        d.polygon(top + bot[::-1], fill=(30, 90, 110, 230), outline=(120, 230, 255, 255))
        d.line([(p[0], p[1] - 8) for p in top[10:50]], fill=(120, 230, 255, 160), width=3)
        for k in range(7):
            gx = hx - 70 - k * 15; d.ellipse([gx - 4, hy - 4, gx + 4, hy + 4], fill=(10, 30, 40))
        ex, ey = hx - 26, hy - 12
        d.ellipse([ex - 15, ey - 15, ex + 15, ey + 15], fill=(240, 245, 250)); d.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=(10, 10, 14))
        img = pil_f(im)
        z = 1 + 9 * smooth((t - (self.tB - 2.5)) / 2.5)
        if z > 1.01:
            x, y = grid(W, H)
            img = bilinear(img, (x - W / 2) / z + ex, (y - H / 2) / z + ey, 0.0)
        return img
    def eye(self, t):
        im = self.bgB.copy(); d = ImageDraw.Draw(im, "RGBA")
        cx, cy, R = 600, 320, 235
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(40, 34, 40), outline=(220, 210, 200), width=6)
        d.chord([cx - R - 40, cy - 120, cx - R + 60, cy + 120], 90, 270, fill=(60, 80, 110), outline=(200, 220, 240), width=4)
        d.ellipse([cx - R + 30, cy - 70, cx - R + 90, cy + 70], fill=(150, 200, 255, 140), outline=(200, 230, 255), width=3)
        for k in (-1, 1): d.line([(cx - R + 20, cy + k * 80), (cx - R + 20, cy + k * 150)], fill=(120, 90, 60), width=10)
        disc = math.radians(18)
        for a in np.linspace(-1.25, 1.25, 70):
            x0, y0 = cx + (R - 8) * math.cos(a), cy + (R - 8) * math.sin(a)
            x1, y1 = cx + (R - 30) * math.cos(a), cy + (R - 30) * math.sin(a)
            d.line([(x0, y0), (x1, y1)], fill=AMBER, width=3)
        for a0 in np.linspace(-1.2, 1.2, 9):
            pts = []
            for a in np.linspace(a0, disc, 20):
                pts.append((cx + (R - 42) * math.cos(a), cy + (R - 42) * math.sin(a)))
            d.line(pts, fill=(120, 230, 255, 200), width=2)
        dx, dy = cx + R * math.cos(disc), cy + R * math.sin(disc)
        d.polygon([(dx - 10, dy - 20), (dx + 6, dy - 22), (dx + 240, dy + 40), (dx + 240, dy + 90), (dx - 6, dy + 20)], fill=(110, 200, 235, 200))
        for k in range(5):
            y = cy - 120 + k * 60
            d.line([(60, y), (cx - R - 50, y)], fill=(255, 240, 200, 160), width=2)
            d.polygon([(cx - R - 50, y - 7), (cx - R - 50, y + 7), (cx - R - 36, y)], fill=(255, 240, 200, 160))
        ftext(d, (70, cy - 160), "light", 26, (255, 240, 200))
        ftext(d, (cx - R + 60, cy + 110), "lens", 26, CYAN, anchor="ma")
        ftext(d, (cx + R + 20, cy - 200), "retina", 26, AMBER)
        ftext(d, (cx + R - 120, cy - 120), "nerves in front", 22, CYAN)
        if t > self.tBS:
            a = smooth((t - self.tBS) / 0.6)
            r = 26 + 4 * math.sin(t * 3)
            d.ellipse([dx - r, dy - r, dx + r, dy + r], outline=(255, 90, 90, int(255 * a)), width=4)
            ftext(d, (dx + 30, dy - 70), "blind spot", 30, (255, 120, 120), "inter_b")
        return pil_f(im)
    def cones(self, t):
        im = self.bgB.copy(); d = ImageDraw.Draw(im, "RGBA")
        x0, x1, yb, yt = 160, 1120, 470, 150
        X = lambda nm: x0 + (nm - 340) / (720 - 340) * (x1 - x0)
        for nm in range(400, 701, 2):
            c = hsv2rgb(np.array((700 - nm) / 300 * 0.78), np.array(0.9), np.array(0.9))
            d.rectangle([X(nm), yb + 14, X(nm + 2), yb + 34], fill=tuple(int(v * 255) for v in c))
        d.line([(x0, yb), (x1, yb)], fill=DIM, width=2)
        for nm in (400, 500, 600, 700):
            ftext(d, (X(nm), yb + 44), f"{nm} nm", 20, DIM, anchor="ma")
        sets = {"four": [(370, (200, 120, 255)), (445, (90, 140, 255)), (508, (90, 230, 140)), (565, (255, 110, 90))],
                "two": [(430, (90, 140, 255)), (555, (255, 170, 90))],
                "three": [(420, (90, 140, 255)), (534, (90, 230, 140)), (564, (255, 110, 90))]}
        a4 = 1 - smooth((t - self.tC2) / 1.5); a2 = smooth((t - self.tC2) / 1.5) * (1 - smooth((t - self.tC3) / 1.5)); a3 = smooth((t - self.tC3) / 1.5)
        for key, alpha in (("four", a4), ("two", a2), ("three", a3)):
            if alpha <= 0.01: continue
            for pk, col in sets[key]:
                pts = [(X(nm), yb - (yb - yt) * math.exp(-((math.log(nm / pk)) / 0.075) ** 2)) for nm in range(340, 721, 4)]
                d.polygon(pts + [(X(720), yb), (X(340), yb)], fill=col + (int(60 * alpha),))
                d.line(pts, fill=col + (int(255 * alpha),), width=4)
        title = "fish, reptiles, birds: 4 kinds of cones" if a4 > 0.5 else ("early mammals: 2" if a2 > 0.5 else "primates, including you: 3")
        ftext(d, (x0, 80), title, 36, INK, "inter_b")
        return pil_f(im)
    def frame(self, fi, t):
        if t < self.tB: return self.fish(t)
        if t < self.tC:
            img = self.eye(t)
            return img * smooth((t - self.tB) / 0.6)
        return self.cones(t) * smooth((t - self.tC) / 0.6)

# ---------------- 3. The brain builds the picture ----------------
class Perceive(Scene):
    res = "full"
    def setup(self):
        s0 = self.sents(0)
        self.tBlind = stage_times(s0, [2])[0]
        self.tInstr = stage_times(s0, [3])[0]
        self.t1 = self.bv[1][0] if len(self.bv) > 1 else 1e9
        s1 = self.sents(1) if len(self.bv) > 1 else []
        self.tFlip = stage_times(s1, [1])[0] if s1 else 1e9
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", "436.5", "-i", f"{FX_ROOT}/arch/raw/moon.mp4", "-frames:v", "1",
                            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.moon = np.frombuffer(p.stdout, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        self.moon_blur = blur(self.moon, 9)
        r = np.random.default_rng(5)
        self.fix = [(640 + r.normal(0, 70), 360 + r.normal(0, 60)) for _ in range(80)]
        self.muy = [to_f(f.resize((680, 460), Image.LANCZOS)) for f in muy_frames()]
        self.x, self.y = grid(W, H)
    def saccades(self, t):
        k = int(t * 3.1)
        fx, fy = self.fix[k % len(self.fix)]
        m = np.exp(-(((self.x - fx) ** 2 + (self.y - fy) ** 2) / (2 * 90 ** 2)))[..., None]
        img = self.moon_blur * 0.55 * (1 - m) + self.moon * m
        im = Image.fromarray(to_u8(img)); d = ImageDraw.Draw(im, "RGBA")
        trail = [self.fix[(k - j) % len(self.fix)] for j in range(6)]
        d.line(trail, fill=(255, 220, 90, 150), width=3)
        d.ellipse([fx - 16, fy - 16, fx + 16, fy + 16], outline=(255, 220, 90, 255), width=4)
        return pil_f(im)
    def blind(self, t):
        im, d = draw_canvas(W, H, (34, 34, 38))
        cx, cy = 360, 320
        d.line([(cx - 28, cy), (cx + 28, cy)], fill=(245, 245, 245), width=7); d.line([(cx, cy - 28), (cx, cy + 28)], fill=(245, 245, 245), width=7)
        d.ellipse([900 - 30, cy - 30, 900 + 30, cy + 30], fill=(245, 245, 245))
        if t > self.tInstr:
            ftext(d, (W / 2, 90), "close your LEFT eye  ·  stare at the +  ·  lean slowly toward the screen", 30, (235, 235, 235), anchor="ma")
            ftext(d, (W / 2, 140), "the dot vanishes into your blind spot", 26, (180, 180, 190), anchor="ma")
        return pil_f(im)
    def muybridge(self, t):
        lt = t - self.t1
        out = np.ones((H, W, 3), np.float32) * 0.08
        if t < self.tFlip:
            for i, f in enumerate(self.muy[:10]):
                small = f[::4, ::4]
                y0 = 140 + (i // 5) * (small.shape[0] + 30); x0 = 90 + (i % 5) * (small.shape[1] + 40)
                a = smooth((lt - i * 0.15) / 0.4)
                out[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = out[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] * (1 - a) + small * a
            return out
        u = t - self.tFlip
        fps = min(12.0, 1.5 + u * 1.6)
        ph = 0.0
        if u < 6.6:
            ph = 1.5 * u + 0.8 * u * u
        else:
            ph = 1.5 * 6.6 + 0.8 * 6.6 ** 2 + 12.0 * (u - 6.6)
        f = self.muy[int(ph) % len(self.muy)]
        y0, x0 = (H - f.shape[0]) // 2 - 50, (W - f.shape[1]) // 2
        out[y0:y0 + f.shape[0], x0:x0 + f.shape[1]] = f
        lab = text_img(f"{fps:4.1f} pictures per second", "mono", 26, fill=(220, 220, 220, 255))
        comp(out, lab, W - 470, 40, 1)
        return out
    def frame(self, fi, t):
        if t >= self.t1: return self.muybridge(t)
        if t >= self.tBlind: return self.blind(t)
        return self.saccades(t)

# ---------------- 4. The cave ----------------
class Cave(Scene):
    res = "full"
    def setup(self):
        s = self.sents(0)
        self.tFire, self.tShadow, self.tScreen = stage_times(s, [1, 2, 4])
        self.muy = []
        for f in muy_frames():
            g = np.asarray(f.convert("L"), np.float32) / 255
            m = (g < 0.35).astype(np.float32)
            m[:30] = 0; m[-28:] = 0
            self.muy.append(Image.fromarray((m * 255).astype(np.uint8)).resize((300, 203)).filter(ImageFilter.GaussianBlur(1)))
        self.x, self.y = grid(W, H)
    def frame(self, fi, t):
        flick = 1 + 0.04 * math.sin(t * 7.3) + 0.03 * math.sin(t * 11.1 + 1)
        fire_on = smooth((t - self.tFire) / 1.5)
        im, d = draw_canvas(W, H, (10, 8, 7))
        d.polygon([(0, 0), (560, 0), (520, 720), (0, 720)], fill=(70, 52, 38))
        d.polygon([(560, 0), (W, 0), (W, 720), (520, 720)], fill=(22, 17, 14))
        img = pil_f(im)
        light = np.exp(-(((self.x - 1050) / 380) ** 2 + ((self.y - 430) / 260) ** 2)) * fire_on * flick
        img = img * (0.35 + 0.9 * light[..., None]) + light[..., None] * np.array([0.35, 0.16, 0.04], np.float32)
        wall_light = (0.55 + 0.75 * fire_on * flick)
        img[:, :540] *= wall_light
        sh = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(sh)
        a_sh = smooth((t - self.tShadow) / 1.2)
        if a_sh > 0:
            k = int(t * 10) % len(self.muy)
            hx = int(520 - ((t - self.tShadow) * 60) % 760)
            sh.paste(255, (hx, 220), self.muy[k])
            vx = int(520 - ((t - self.tShadow) * 45 + 380) % 760)
            sd.polygon([(vx, 420), (vx + 60, 420), (vx + 80, 470), (vx + 40, 560), (vx + 20, 560), (vx - 20, 470)], fill=255)
            bx = int(-100 + ((t - self.tShadow) * 70) % 700); by = 160 + 20 * math.sin(t * 2)
            sd.polygon([(bx, by), (bx + 40, by - 25 * abs(math.sin(t * 6))), (bx + 30, by + 6), (bx + 70, by + 4), (bx + 20, by + 14)], fill=255)
            sh = sh.filter(ImageFilter.GaussianBlur(6))
            m = to_f(sh)[..., None] * 0.92 * a_sh
            img[:, :560] = img[:, :560] * (1 - m[:, :560])
        im2 = Image.fromarray(to_u8(img)); d2 = ImageDraw.Draw(im2, "RGBA")
        for i in range(4):
            px = 650 + i * 110; py = 520
            d2.ellipse([px - 26, py - 120, px + 26, py - 66], fill=(6, 5, 5)); d2.rounded_rectangle([px - 46, py - 70, px + 46, py + 60], 20, fill=(6, 5, 5))
        d2.line([(600, 590), (1080, 590)], fill=(60, 50, 40), width=5)
        d2.rectangle([560, 300, W, 330], fill=(14, 11, 9))
        if t > self.tScreen:
            a = int(255 * smooth((t - self.tScreen) / 1.2))
            d2.rectangle([40, 120, 500, 600], outline=(240, 230, 210, a), width=4)
            ftext(d2, (270, 80), "the first movie theater", 26, (240, 230, 210), anchor="ma")
        return pil_f(im2)

# ---------------- 5. The doors of perception ----------------
class Doors(Scene):
    res = "full"
    def setup(self):
        s = self.sents(0)
        self.tc = stage_times(s, [0, 1, 2, 3, 4])
        fake = dict(scene="liquid", act="see5", idx=991, f0=0, nf=10, beats=[dict(p={}, start=0, dur=9, vo=None, pre=0, key="x")])
        self.liq = Liquid(fake, {}, self.ctx)
        self.cards = [
            ("“If the doors of perception were cleansed…”", "William Blake, c. 1790"),
            ("The Doors of Perception", "Aldous Huxley, 1954 · after taking mescaline with Humphry Osmond in 1953"),
            ("A new word", "proposed by Humphry Osmond, 1956–57"),
        ]
    def frame(self, fi, t):
        open_u = smooth((t - self.tc[3] + 0.3) / 2.2)
        k = sum(1 for x in self.tc[:3] if t >= x) - 1
        liq = upscale(self.liq.frame(fi, t * 0.8 + 5))
        xs = np.abs(grid(W, H)[0] - W / 2)
        liq = liq * (0.25 + 0.75 * open_u)
        im, d = draw_canvas(W, H, (8, 7, 10))
        img = pil_f(im)
        gap = 6 + 330 * open_u
        mask = (xs < gap)[..., None].astype(np.float32)
        img = img * (1 - mask) + liq * mask
        glow_ = np.exp(-(xs / (gap + 25)) ** 2)[..., None] * 0.35 * (1 - open_u) * np.array([1, 0.9, 0.7], np.float32)
        img = img + glow_
        im = Image.fromarray(to_u8(img)); d = ImageDraw.Draw(im, "RGBA")
        for side in (-1, 1):
            x_in = W / 2 + side * gap; x_out = W / 2 + side * (gap + 300 * (1 - open_u * 0.6))
            d.polygon([(x_in, 60), (x_out, 60 - 30 * open_u), (x_out, 660 + 30 * open_u), (x_in, 660)], fill=(28, 22, 20), outline=(90, 70, 55))
        if 0 <= k < 3 and t < self.tc[3] - 0.2:
            title, sub = self.cards[k]
            a = smooth((t - self.tc[k]) / 0.6)
            ti = text_img(title, "serif_i", 46, fill=(240, 232, 215, 255)); su = text_img(sub, "inter", 24, fill=(200, 195, 185, 255))
            img = pil_f(im); comp_center(img, ti, W / 2, H - 235, a); comp_center(img, su, W / 2, H - 183, a)
            return img
        img = pil_f(im)
        if t >= self.tc[3]:
            a = smooth((t - self.tc[3]) / 0.5)
            word = text_img("PSYCHEDELIC", "inter_x", 120, fill=(255, 255, 255, 255))
            comp_center(img, word, W / 2, H / 2 - 20, a)
            if t >= self.tc[4]:
                sub = text_img("psyche (mind)  +  dēlos (made visible)", "inter_b", 34, fill=(255, 240, 220, 255))
                comp_center(img, sub, W / 2, H / 2 + 80, smooth((t - self.tc[4]) / 0.5))
        return img

# ---------------- 6. Who is watching? ----------------
class Homunculus(Feedback):
    res = "full"
    def setup(self):
        super().setup()
        s = self.sents(0)
        self.tObs, self.tZoom, self.tFb, self.tPred = stage_times(s, [2, 3, 5, 6])
        self.diag = self.diagram()
    def diagram(self):
        im = Image.new("RGB", (W, H), (12, 12, 16)); d = ImageDraw.Draw(im, "RGBA")
        tx, ty = 170, 440
        d.rectangle([tx - 8, ty - 40, tx + 8, ty + 80], fill=(140, 100, 60)); d.ellipse([tx - 70, ty - 170, tx + 70, ty - 20], fill=(60, 150, 80))
        cx, cy, R = 640, 360, 190
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(220, 210, 200), width=5)
        d.ellipse([cx - R + 10, cy - 50, cx - R + 60, cy + 50], outline=(160, 220, 255), width=3)
        for (px, py) in ((tx, ty - 170), (tx, ty + 80)):
            ax, ay = cx - R + 35, cy
            ex = cx + R - 10; ey = ay + (ay - py) / (ax - px) * (ex - ax)
            d.line([(px, py), (ax, ay), (ex, ey)], fill=(255, 230, 170, 140), width=2)
        ix, iy = cx + R - 40, cy
        d.rectangle([ix - 4, iy - 20, ix + 4, iy + 40], fill=(140, 100, 60)); d.ellipse([ix - 18, iy + 20, ix + 18, iy + 62], fill=(60, 150, 80))
        return im
    def observer(self, d, x, y, s, a=255):
        d.ellipse([x - 22 * s, y - 90 * s, x + 22 * s, y - 46 * s], fill=(230, 220, 200, a))
        d.rounded_rectangle([x - 30 * s, y - 46 * s, x + 30 * s, y + 40 * s], int(14 * s) + 1, fill=(230, 220, 200, a))
    SCR = (1010, 300, 200, 112)
    def scene_img(self, depth=2):
        base = self.diag.copy(); d = ImageDraw.Draw(base, "RGBA")
        self.observer(d, 1010, 420, 1.3)
        cx, cy, sw, sh = self.SCR
        d.rounded_rectangle([cx - sw / 2 - 6, cy - sh / 2 - 6, cx + sw / 2 + 6, cy + sh / 2 + 6], 10, fill=(230, 220, 200))
        if depth > 0:
            inner = self.scene_img(depth - 1).resize((sw, sh), Image.LANCZOS)
            base.paste(inner, (int(cx - sw / 2), int(cy - sh / 2)))
        return base
    def frame(self, fi, t):
        if t < self.tObs:
            return pil_f(self.diag)
        if t < self.tZoom:
            im = self.diag.copy(); d = ImageDraw.Draw(im, "RGBA")
            self.observer(d, 1010, 420, 1.3, int(255 * smooth((t - self.tObs) / 0.6)))
            ftext(d, (1010, 500), "who looks at the picture?", 26, INK, anchor="ma")
            return pil_f(im)
        if t < self.tFb + 1.0:
            if not hasattr(self, "rec"):
                self.rec = pil_f(self.scene_img(2))
            cx, cy, sw, sh = self.SCR
            ratio = W / sw
            u = (t - self.tZoom) / max(0.5, self.tFb + 1.0 - self.tZoom)
            levels = u * 2.4
            zl = ratio ** (levels % 1.0)
            # Each level is the same picture, so zooming a fraction of a level and wrapping is seamless.
            x, y = grid(W, H)
            fx = W / 2 + (cx - W / 2) * (1 - 1 / zl) / (1 - 1 / ratio)
            fy = H / 2 + (cy - H / 2) * (1 - 1 / zl) / (1 - 1 / ratio)
            img = bilinear(self.rec, (x - W / 2) / zl + fx, (y - H / 2) / zl + fy, 0.0)
            if t > self.tFb:
                self.seg["beats"][0]["p"] = dict(mode="mandala", spin=1.0)
                fb = upscale(Feedback.frame(self, fi, t))
                img = img * (1 - smooth(t - self.tFb)) + fb * smooth(t - self.tFb)
            return img
        self.seg["beats"][0]["p"] = dict(mode="mandala", spin=1.0)
        img = upscale(Feedback.frame(self, fi, t))
        if t > self.tPred:
            a = smooth((t - self.tPred) / 0.8)
            img = img * (1 - 0.45 * a)
            l1 = text_img("the brain predicts the picture", "inter_b", 46, fill=(255, 255, 255, 255))
            l2 = text_img("perception as “controlled hallucination”", "inter", 32, fill=(230, 230, 230, 255))
            comp_center(img, l1, W / 2, H / 2 - 30, a); comp_center(img, l2, W / 2, H / 2 + 30, smooth((t - self.tPred - 2.5) / 0.8))
        return img

SCENES = dict(eyeevo=EyeEvo, fisheye=FishEye, perceive=Perceive, cave=Cave, doors=Doors, homunculus=Homunculus)
