import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from functools import lru_cache

W, H = 1280, 720
w, h = 640, 360
FPS = 24

F = "/usr/share/fonts/"
FONTS = {
    "inter": F + "opentype/inter/Inter-Medium.otf",
    "inter_r": F + "opentype/inter/Inter-Regular.otf",
    "inter_b": F + "opentype/inter/Inter-Bold.otf",
    "inter_l": F + "opentype/inter/InterDisplay-Light.otf",
    "inter_x": F + "opentype/inter/InterDisplay-Black.otf",
    "inter_xb": F + "opentype/inter/InterDisplay-ExtraBold.otf",
    "serif": F + "truetype/liberation/LiberationSerif-Regular.ttf",
    "serif_i": F + "truetype/liberation/LiberationSerif-Italic.ttf",
    "serif_b": F + "truetype/liberation/LiberationSerif-Bold.ttf",
    "mono": F + "truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
    "mono_b": F + "truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
    "mono_l": F + "truetype/jetbrains-mono/JetBrainsMono-Light.ttf",
    "pixel": F + "opentype/unifont/unifont.otf",
}

@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(FONTS[name], int(size))

def smooth(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x

def to_u8(img): return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
def to_f(arr): return np.asarray(arr, np.float32) / 255.0

def upscale(img, size=(W, H)):
    if img.shape[1] == size[0] and img.shape[0] == size[1]:
        return img
    return to_f(Image.fromarray(to_u8(img)).resize(size, Image.BICUBIC))

def blur(img, r):
    return to_f(Image.fromarray(to_u8(img)).filter(ImageFilter.GaussianBlur(r)))

def glow(img, r=6, amt=0.6, down=4):
    hh, ww = img.shape[:2]
    small = Image.fromarray(to_u8(img)).resize((ww // down, hh // down), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / down * 2))
    return img + amt * to_f(small.resize((ww, hh), Image.BILINEAR))

def hsv2rgb(hh, s, v):
    hh = (hh % 1.0) * 6.0
    i = np.floor(hh).astype(np.int32) % 6
    f = hh - np.floor(hh)
    p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1).astype(np.float32)

def grid(ww, hh):
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    return x, y

def bilinear(img, sx, sy, oob=0.0):
    hh, ww = img.shape[:2]
    inside = (sx >= 0) & (sx <= ww - 1) & (sy >= 0) & (sy <= hh - 1)
    sx = np.clip(sx, 0, ww - 1.001); sy = np.clip(sy, 0, hh - 1.001)
    x0 = sx.astype(np.int32); y0 = sy.astype(np.int32)
    fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    out = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    if oob is not None:
        out = np.where(inside[..., None], out, oob)
    return out

def vignette(ww=W, hh=H, k=0.55):
    x, y = grid(ww, hh)
    r = np.sqrt(((x - ww / 2) / (ww / 2)) ** 2 + ((y - hh / 2) / (hh / 2)) ** 2)
    return (1 - k * smooth((r - 0.55) / 0.9))[..., None].astype(np.float32)

VIG = vignette()

def text_img(lines, fname, size, fill=(255, 255, 255, 255), spacing=1.25, align="left", stroke=0, stroke_fill=(0, 0, 0, 255)):
    f = font(fname, size)
    if isinstance(lines, str): lines = lines.split("\n")
    widths = [f.getbbox(l)[2] if l else 0 for l in lines]
    lh = int(size * spacing)
    im = Image.new("RGBA", (max(widths + [1]) + 8 + 2 * stroke, lh * len(lines) + int(size * 0.4) + 2 * stroke), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = stroke + (0 if align == "left" else (max(widths) - widths[i]) // (2 if align == "center" else 1))
        d.text((x, stroke + i * lh), l, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im

def comp(img, rgba, x, y, alpha=1.0):
    """Alpha-composite a PIL RGBA image onto float img (in place), top-left at x,y."""
    if alpha <= 0: return img
    a = np.asarray(rgba, np.float32) / 255.0
    hh, ww = img.shape[:2]
    x, y = int(x), int(y)
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(ww, x + a.shape[1]), min(hh, y + a.shape[0])
    if x1 <= x0 or y1 <= y0: return img
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
    al = sub[..., 3:4] * alpha
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - al) + sub[..., :3] * al
    return img

def comp_center(img, rgba, cx, cy, alpha=1.0):
    return comp(img, rgba, cx - rgba.size[0] / 2, cy - rgba.size[1] / 2, alpha)

def draw_canvas(ww=W, hh=H, color=(0, 0, 0)):
    im = Image.new("RGB", (ww, hh), color)
    return im, ImageDraw.Draw(im, "RGBA")

def pil_f(im): return to_f(im.convert("RGB"))

# ---------- looks ----------
class Look:
    def __init__(self, kind, seed=0):
        self.kind = kind
        self.rng = np.random.default_rng(seed)
        if kind in ("film_bw", "film_color"):
            g = self.rng.normal(0, 1, (8, H // 2, W // 2)).astype(np.float32)
            self.grain = [to_f(Image.fromarray(np.clip(gi * 40 + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR))[..., None] - 0.5 for gi in g]
            self.wx = self.wy = 0.0
        if kind == "crt":
            x, y = grid(W, H)
            nx, ny = (x - W / 2) / (W / 2), (y - H / 2) / (H / 2)
            r2 = nx * nx + ny * ny
            k = 0.06
            self.sx = (nx * (1 + k * r2)) * (W / 2) / 1.04 + W / 2
            self.sy = (ny * (1 + k * r2)) * (H / 2) / 1.04 + H / 2
            self.inside = ((self.sx >= 0) & (self.sx < W - 1) & (self.sy >= 0) & (self.sy < H - 1))[..., None]
            self.sxi = np.clip(self.sx, 0, W - 1).astype(np.int32); self.syi = np.clip(self.sy, 0, H - 1).astype(np.int32)
            sl = np.ones((H, 1, 1), np.float32); sl[1::3] = 0.78; sl[2::3] = 0.9
            self.scan = sl
            edge = smooth((1.0 - np.maximum(np.abs(nx) * 1.04, np.abs(ny) * 1.04) * (1 + k * r2)) * 25)
            self.edge = edge[..., None].astype(np.float32)
        if kind == "vhs":
            self.rng2 = np.random.default_rng(seed + 1)

    def __call__(self, img, fi):
        k = self.kind
        if k == "film_bw" or k == "film_color":
            bw = k == "film_bw"
            if bw:
                g = img @ np.array([0.3, 0.59, 0.11], np.float32)
                img = g[..., None] * np.array([1.0, 0.97, 0.9], np.float32)
            else:
                img = img * np.array([1.03, 1.0, 0.94], np.float32)
            self.wx = 0.8 * self.wx + self.rng.normal(0, 0.6); self.wy = 0.8 * self.wy + self.rng.normal(0, 0.6)
            img = np.roll(img, (int(round(self.wy)), int(round(self.wx))), (0, 1))
            img = img * (1 + self.rng.normal(0, 0.012))
            img = img + self.grain[fi % 8] * (0.10 if bw else 0.06)
            if self.rng.random() < 0.12:
                x = int(self.rng.integers(0, W)); img[:, x:x + 1] = img[:, x:x + 1] * 0.6 + 0.3
            for _ in range(int(self.rng.poisson(1.2))):
                x, y = int(self.rng.integers(0, W - 4)), int(self.rng.integers(0, H - 4))
                img[y:y + 3, x:x + 2] = 0.05 if self.rng.random() < 0.5 else 0.9
            return img * VIG
        if k == "crt":
            out = img[self.syi, self.sxi]
            out = out * self.scan
            out[..., 0] = np.roll(out[..., 0], 1, 1); out[..., 2] = np.roll(out[..., 2], -1, 1)
            band = (np.arange(H) - (fi * 3) % (H + 200) + 100)
            out = out * (1 - 0.05 * np.exp(-(band / 60.0) ** 2))[:, None, None]
            out = glow(out, 6, 0.25)
            return out * self.edge * VIG
        if k == "glitch":
            if self.rng.random() < 0.07:
                y0 = int(self.rng.integers(0, H - 40)); hh = int(self.rng.integers(8, 40)); dx = int(self.rng.integers(-30, 30))
                img = img.copy(); img[y0:y0 + hh] = np.roll(img[y0:y0 + hh], dx, 1)
            return img
        if k == "vhs":
            img = img.copy()
            img[..., 0] = np.roll(img[..., 0], 3, 1); img[..., 2] = np.roll(img[..., 2], -2, 1)
            y = int((fi * 7) % (H + 60)) - 30
            if 0 <= y < H - 12:
                img[y:y + 10] = np.roll(img[y:y + 10], int(self.rng2.integers(-12, 12)), 1) * 0.8 + 0.12
            img = img + self.rng2.normal(0, 0.025, (H, 1, 1)).astype(np.float32)
            return img
        return img

def label_img(title, sub, act_font):
    tf = {"serif": "serif_i", "mono": "mono_b", "pixel": "pixel", "black": "inter_xb"}.get(act_font, "inter_b")
    sf = {"serif": "serif", "mono": "mono", "pixel": "pixel", "black": "inter"}.get(act_font, "inter")
    a = text_img(title, tf, 38 if act_font != "pixel" else 34)
    b = text_img(sub, sf, 26 if act_font != "pixel" else 26, fill=(230, 230, 230, 240)) if sub else None
    wd = max(a.size[0], b.size[0] if b else 0) + 48
    ht = a.size[1] + (b.size[1] if b else 0) + 18
    im = Image.new("RGBA", (wd, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, wd - 1, ht - 1], 10, fill=(0, 0, 0, 140))
    d.rectangle([10, 10, 14, ht - 12], fill=(255, 255, 255, 230))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste(a, (26, 4), a)
    if b: sh.paste(b, (26, a.size[1] + 2), b)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    alpha = sh.split()[3].filter(ImageFilter.GaussianBlur(6))
    shadow.putalpha(alpha.point(lambda v: int(v * 0.85)))
    im = Image.alpha_composite(im, shadow)
    im = Image.alpha_composite(im, sh)
    return im
