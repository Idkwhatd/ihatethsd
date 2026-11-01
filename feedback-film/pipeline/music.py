import json, sys, os
import numpy as np
from scipy import signal
import soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from cues import *

SR = 48000
rng = np.random.default_rng(7)

def mtof(m): return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)
def N(sec): return max(0, int(round(sec * SR)))
def T(n): return np.arange(n) / SR

def osc(kind, f, n, ph0=0.0, pw=0.5):
    if np.isscalar(f):
        ph = (f * T(n) + ph0) % 1.0
    else:
        ph = (np.cumsum(f) / SR + ph0) % 1.0
    if kind == "sine": return np.sin(2 * np.pi * ph)
    if kind == "saw": return 2 * ph - 1
    if kind == "sq": return np.where(ph < pw, 1.0, -1.0)
    if kind == "tri": return 4 * np.abs(ph - 0.5) - 1

def filt(x, kind, fc, order=2):
    if kind == "band":
        sos = signal.butter(order, [max(20, fc[0]), min(fc[1], SR * 0.45)], "band", fs=SR, output="sos")
    else:
        sos = signal.butter(order, min(max(fc, 20), SR * 0.45), kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x)

def lp(x, fc, o=2): return filt(x, "low", fc, o)
def hp(x, fc, o=2): return filt(x, "high", fc, o)
def bp(x, lo, hi, o=2): return filt(x, "band", (lo, hi), o)

def env(n, a=0.01, r=0.1):
    e = np.ones(n)
    na = min(n, N(a)); nr = min(n - na, N(r))
    if na: e[:na] = np.linspace(0, 1, na)
    if nr > 0: e[n - nr:] *= np.linspace(1, 0, nr)
    return e

def dec(n, k): return np.exp(-T(n) * k)
def noise(n): return rng.uniform(-1, 1, n)

class Buf:
    def __init__(self, sec):
        self.x = np.zeros((N(sec) + SR * 6, 2))
    def add(self, t, sig, pan=0.0, gain=1.0):
        i = N(t)
        if i < 0:
            sig = sig[-i:]; i = 0
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            s = np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * gain * 1.414
        else:
            s = sig * gain
        j = min(len(self.x), i + len(s))
        if j > i:
            self.x[i:j] += s[: j - i]

# ---------- instruments ----------
def pad(midis, dur, bright=1400, a=1.2, r=1.8, det=0.10, wave="saw"):
    n = N(dur)
    out = np.zeros((n, 2))
    for m in midis:
        for k, d in enumerate((-det, 0.0, det)):
            s = osc(wave, mtof(m + d), n, rng.random())
            out[:, 0] += s * (1.0 if k != 2 else 0.6)
            out[:, 1] += s * (1.0 if k != 0 else 0.6)
    out = np.stack([lp(out[:, 0], bright), lp(out[:, 1], bright)], 1)
    return out * env(n, a, r)[:, None] / (len(midis) * 3)

def pluck(m, dur, damp=0.996, bright=0.6):
    f = float(mtof(m)); n = N(dur); D = max(2, int(SR / f))
    x = np.zeros(n); x[:D] = lp(noise(D), 1500 + bright * 7000)
    a = np.zeros(D + 2); a[0] = 1; a[D] = -damp * 0.5; a[D + 1] = -damp * 0.5
    return signal.lfilter([1.0], a, x) * env(n, 0.001, 0.05)

def bell(m, dur, ratio=3.5, idx=4.0, k=1.6):
    n = N(dur); t = T(n); f = float(mtof(m))
    s = np.sin(2 * np.pi * f * t + idx * np.exp(-t * 3) * np.sin(2 * np.pi * f * ratio * t))
    return s * np.exp(-t * k) * env(n, 0.002, 0.05)

def sine_note(m, dur, a=0.02, r=0.2):
    n = N(dur); return osc("sine", float(mtof(m)), n) * env(n, a, r)

def theremin(path, dur, vib=5.3):
    # path: list of (t, midi); glides between them
    n = N(dur); t = T(n)
    ts = [p[0] for p in path]; ms = [p[1] for p in path]
    m = np.interp(t, ts, ms)
    m = lp(m, 3.0, 1)
    f = mtof(m) * (1 + 0.012 * np.sin(2 * np.pi * vib * t))
    s = osc("sine", f, n) + 0.15 * osc("sine", f * 2, n)
    return s * env(n, 0.6, 1.0)

def organ(midis, dur):
    n = N(dur); t = T(n); out = np.zeros(n)
    for m in midis:
        f = float(mtof(m))
        for h, w in ((0.5, 0.5), (1, 1.0), (2, 0.6), (3, 0.4), (4, 0.3), (6, 0.15)):
            out += w * np.sin(2 * np.pi * f * h * t * (1 + 0.002 * np.sin(2 * np.pi * 6.2 * t)))
    out *= (1 + 0.35 * np.sin(2 * np.pi * 6.2 * t))
    return out * env(n, 0.03, 0.15) / (len(midis) * 3)

def violin(m, dur, vib=0.006, grit=0.0):
    n = N(dur); t = T(n); f = float(mtof(m)) * (1 + vib * np.sin(2 * np.pi * 5.6 * t) * np.clip(t * 2, 0, 1))
    s = osc("saw", f, n)
    s = bp(s, 300, 3500) + 0.04 * bp(noise(n), 2000, 6000)
    if grit: s = np.tanh(s * (1 + grit * 6)) / (1 + grit)
    return s * env(n, 0.15, 0.3)

def bowl(m, dur):
    n = N(dur); t = T(n); f = float(mtof(m)); s = np.zeros(n)
    for r, a, k in ((1, 1, 0.35), (1.003, 0.7, 0.35), (2.71, 0.5, 0.7), (5.12, 0.25, 1.2), (8.0, 0.1, 2.0)):
        s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * k)
    return s * env(n, 0.005, 1.0) / 2.5

def kick(dur=0.5, f0=50, k=7):
    n = N(dur); t = T(n)
    f = f0 + 120 * np.exp(-t * 35)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * k) + 0.3 * noise(n) * np.exp(-t * 300))

def snare(dur=0.3, gated=False):
    n = N(dur); t = T(n)
    s = 0.7 * bp(noise(n), 1200, 7000) * np.exp(-t * (8 if gated else 18)) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 20)
    if gated:
        s *= (t < 0.22)
    return s

def hat(open_=False):
    n = N(0.35 if open_ else 0.08); t = T(n)
    return hp(noise(n), 7000) * np.exp(-t * (10 if open_ else 60))

def clap():
    n = N(0.25); t = T(n); s = bp(noise(n), 900, 3000)
    e = np.exp(-t * 25) + 0.6 * np.exp(-np.clip(t - 0.012, 0, None) * 30) * (t > 0.012)
    return s * e

def tom(f=110, dur=0.6):
    n = N(dur); t = T(n)
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t * 12))) / SR) * np.exp(-t * 6)

def acid(notes, bpm, dur, cut=(300, 2600), res=0.9):
    # notes: list per 16th step (midi or None); resonant LP with per-note envelope, block processed
    n = N(dur); step = 60 / bpm / 4; out = np.zeros(n)
    f = np.zeros(n); g = np.zeros(n); envc = np.zeros(n)
    for i in range(int(dur / step)):
        m = notes[i % len(notes)]
        if m is None: continue
        a, b = N(i * step), min(n, N((i + 0.9) * step))
        f[a:b] = mtof(m); g[a:b] = 1; envc[a:b] = np.exp(-T(b - a) * 9)
    s = osc("saw", np.maximum(f, 1), n) * g
    zi = np.zeros(2); blk = 64
    for a in range(0, n, blk):
        b = min(n, a + blk)
        fc = cut[0] + (cut[1] - cut[0]) * envc[a]
        w0 = 2 * np.pi * fc / SR; Q = 1 + res * 12
        al = np.sin(w0) / (2 * Q); cw = np.cos(w0)
        bb = np.array([(1 - cw) / 2, 1 - cw, (1 - cw) / 2]); aa = np.array([1 + al, -2 * cw, 1 - al])
        out[a:b], zi = signal.lfilter(bb / aa[0], aa / aa[0], s[a:b], zi=zi)
    return np.tanh(out * 1.5) * 0.6

def chip(notes, bpm, dur, arp=(0, 4, 7), pw_rate=0.3):
    n = N(dur); t = T(n); step = 60 / bpm / 4; f = np.zeros(n)
    idx = (t * 50).astype(int) % len(arp)  # 50 Hz arpeggio, like the SID tunes
    for i in range(int(dur / step)):
        m = notes[i % len(notes)]
        a, b = N(i * step), min(n, N((i + 1) * step))
        if m is not None: f[a:b] = mtof(m + np.array(arp)[idx[a:b]])
    pw = 0.5 + 0.35 * np.sin(2 * np.pi * pw_rate * t)
    ph = (np.cumsum(f) / SR) % 1
    return np.where(f > 0, np.where(ph < pw, 1.0, -1.0), 0.0) * 0.5

def projector(dur, rate=24.0):
    n = N(dur); out = np.zeros(n); click = bp(noise(N(0.012)), 1500, 5000) * dec(N(0.012), 300)
    for k in range(int(dur * rate)):
        i = N(k / rate + rng.normal(0, 0.0015))
        if 0 <= i < n - len(click): out[i:i + len(click)] += click * rng.uniform(0.5, 1.0)
    out += 0.25 * lp(noise(n), 200) + 0.15 * np.sin(2 * np.pi * 50 * T(n))
    return out * env(n, 0.3, 0.5)

def hiss(dur, lo=2000, hi=12000): n = N(dur); return bp(noise(n), lo, hi) * env(n, 0.3, 0.3)
def hum(dur, f=60): n = N(dur); t = T(n); return (np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*2*f*t) + 0.2*np.sin(2*np.pi*3*f*t)) * env(n, 0.3, 0.3) / 1.7

def swell(dur, lo=200, hi=6000):
    n = N(dur); x = noise(n); t = T(n)
    return bp(x, lo, hi) * (t / dur) ** 2

def click(): n = N(0.006); return bp(noise(n), 2000, 8000) * dec(n, 600)

def reverb(x, secs=2.2, mix=0.25):
    n = N(secs); t = T(n)
    ir = np.stack([noise(n), noise(n)], 1) * np.exp(-t * 6.9 / secs)[:, None]
    ir[:N(0.01)] = 0
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    wet *= np.sqrt(np.mean(x ** 2) / (np.mean(wet ** 2) + 1e-12))
    return x * (1 - mix) + wet * mix

def crush(x, bits=5, hold=8):
    y = np.repeat(x[::hold], hold, axis=0)[: len(x)]
    q = 2 ** bits
    return np.round(y * q) / q

def steps_at(bpm, dur, every=1.0, offset=0.0):
    bt = 60 / bpm * every
    return [offset + i * bt for i in range(int((dur - offset) / bt) + 1) if offset + i * bt < dur]

# ---------- chords ----------
AM = [57, 60, 64, 67]; FM = [53, 57, 60, 64]; CM = [48, 55, 60, 64]; GM = [55, 59, 62, 67]
DM7 = [50, 57, 61, 66]; EM9 = [52, 59, 62, 66]; AM9 = [45, 57, 60, 64, 71]

def prog(buf, t0, dur, chords, bar, gain=0.5, bright=1400, wave="saw"):
    k = 0; t = 0.0
    while t < dur - 0.05:
        L = min(bar, dur - t)
        buf.add(t0 + t, pad(chords[k % len(chords)], L + 1.0, bright, a=min(1.0, L / 3), r=1.0, wave=wave), gain=gain)
        t += bar; k += 1

# ---------- per-scene cues ----------
def m_open_feedback(b, t0, d, seg, c):
    n = N(d); t = T(n)
    if seg["idx"] == 0:
        w = osc("sine", 15734.0, N(6)) * env(N(6), 0.4, 2.5) * 0.004
        b.add(t0, w)
        rise = 57 + 7 * np.clip((t - 4) / (d - 4), 0, 1)
        tone = osc("sine", mtof(rise), n) * np.clip((t - 3) / 5, 0, 1) * env(n, 0.5, 2.0)
        b.add(t0, tone, gain=0.12)
    drone = (osc("sine", 55.0, n) + 0.5 * osc("sine", 82.4, n) + 0.3 * osc("sine", 110.3, n)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t))
    b.add(t0, drone * env(n, 3.0, 2.0), gain=0.10)
    if seg["idx"] == 2:
        prog(b, t0, d, [AM9, [41, 57, 60, 64, 69], [43, 55, 59, 62, 67], AM9], 8.8, gain=0.22, bright=900)
    if seg["act"] == "epi":
        prog(b, t0, d, [FM, GM, AM, [48, 52, 55, 60, 64]], d / 4, gain=0.35, bright=1800)
        b.add(t0, osc("sine", 440.0, n) * env(n, 2.0, 3.0), gain=0.05)
    if seg["act"] == "noise":
        b.add(t0, pad([48, 55, 60, 64, 67], d + 2, 1600, a=1.0, r=3.0), gain=0.45)
    if seg["act"] == "signal":
        prog(b, t0, d, [[45, 52, 57, 64], [43, 50, 55, 62]], 6.3, gain=0.22, bright=800)

def m_montage(b, t0, d, seg, c):
    act = seg["act"]
    for i, ct in enumerate(c["cuts"]):
        b.add(t0 + ct - 0.25, swell(0.3, 400, 5000), gain=0.10, pan=(-1) ** i * 0.4)
    n = N(d); t = T(n)
    if act == "open":
        f = mtof(57 + 12 * t / d)
        b.add(t0, osc("sine", f, n) * env(n, 0.3, 0.3), gain=0.14)
    elif act == "razor":
        mel = [(0, 69), (2.5, 72), (5, 76), (8, 74), (11, 72), (13.5, 69), (d, 69)]
        b.add(t0, theremin(mel, d), gain=0.16)
        b.add(t0, projector(d), gain=0.10)
        prog(b, t0, d, [AM, FM, CM, AM], d / 4, gain=0.18, bright=900)
    elif act == "cut":
        groove(b, t0, d, 104, intensity=2)
        b.add(t0 + d - 1.0, pad(CM, 3, 2000, a=0.05, r=2.5), gain=0.4)
    elif act == "noise":
        chords = [AM, FM, CM, GM]
        for i, ct in enumerate(c["cuts"]):
            ch = chords[i % 4]
            for j, m in enumerate(ch):
                b.add(t0 + ct + j * 0.09, pluck(m + 12, 2.5, 0.997), gain=0.18, pan=(j - 1.5) * 0.3)
        prog(b, t0, d, chords, c["cuts"][1] if len(c["cuts"]) > 1 else 3, gain=0.10 + 0.0, bright=1200)
        for k in steps_at(96, d, 1, d * 0.55):
            b.add(t0 + k, kick(0.4, 45, 8), gain=0.25 * (k / d))
    elif act == "epi":
        b.add(t0, osc("sine", 440.0, n) * env(n, 1.0, 2.0), gain=0.06)
        prog(b, t0, d, [AM9, [41, 57, 60, 64, 69]], d / 2, gain=0.22, bright=900)

def m_title(b, t0, d, seg, c):
    b.add(t0 + c["hit"] - 1.2, swell(1.2, 200, 9000), gain=0.18)
    b.add(t0 + c["hit"], kick(3.0, 38, 1.2), gain=0.45)
    b.add(t0 + c["hit"], pad([45, 57, 61, 64, 69, 76], d, 2400, a=0.02, r=4.0), gain=0.55)

def m_actcard(b, t0, d, seg, c):
    act = seg["act"]
    if act == "razor":
        b.add(t0 + 0.4, projector(d + 0.5), gain=0.16)
        b.add(t0 + 0.3, pluck(45, 4, 0.998), gain=0.35)
    elif act == "light":
        for j, m in enumerate([62, 66, 69, 73, 76]):
            b.add(t0 + 0.3 + j * 0.12, bell(m, 3.5), gain=0.15, pan=(j - 2) * 0.3)
    elif act == "signal":
        n = N(0.5); b.add(t0 + 0.3, osc("sine", 8000 * np.exp(-T(n) * 6) + 60, n) * dec(n, 6), gain=0.12)
        b.add(t0 + 0.3, hum(d), gain=0.08)
    elif act == "cut":
        for k in range(8):
            b.add(t0 + 0.3 + k * 0.09, snare(0.25), gain=0.08 + 0.03 * k)
        b.add(t0 + 1.05, kick(), gain=0.5); b.add(t0 + 1.05, pad(CM, 2.5, 3000, a=0.01, r=2), gain=0.35)
    elif act == "cyber":
        b.add(t0 + 0.3, chip([60, 64, 67, 72] * 4, 140, 1.7), gain=0.10)
    elif act == "noise":
        x = np.stack([noise(N(0.6)), noise(N(0.6))], 1) * 0.5
        b.add(t0 + 0.3, crush(x, 3, 40), gain=0.15)

def m_eye(b, t0, d, seg, c):
    ph = seg["beats"][0]["p"]["phase"]
    b.add(t0, projector(d), gain=0.10)
    if ph == "theatre":
        b.add(t0, hiss(d, 300, 2000), gain=0.03)
        for k, m in enumerate([57, 64, 60, 69, 67, 64]):
            b.add(t0 + 1.0 + k * 2.2, pluck(m, 3, 0.995), gain=0.18, pan=0.3 * (-1) ** k)
    elif ph == "moon":
        mel = [(0, 69), (3, 72), (6, 71), (9, 76), (12, 74), (d, 74)]
        b.add(t0, theremin(mel, d), gain=0.15)
    else:
        n = N(c["slice"])
        trem = sum(violin(m, c["slice"] + 0.1, vib=0.01) for m in (57, 58, 64)) * (0.2 + 0.8 * T(N(c["slice"] + 0.1)) / c["slice"])
        b.add(t0, trem, gain=0.10)
        b.add(t0 + c["slice"], hp(noise(N(0.5)), 5000) * dec(N(0.5), 10), gain=0.25)
        b.add(t0 + c["slice"] + 1.4, pad([45, 52, 57], d - c["slice"], 500, a=2.0, r=2.0), gain=0.25)

def m_type(b, t0, d, seg, c, text=None):
    text = text or seg["beats"][0]["p"].get("text", "")
    k = 0
    for ch in text:
        if ch == "\n":
            b.add(t0 + c["type_start"] + k / TYPE_CPS, bell(96, 1.0, 1.4, 1.0, 3), gain=0.06)
            k += 3; continue
        b.add(t0 + c["type_start"] + k / TYPE_CPS, click(), gain=0.22, pan=rng.uniform(-0.3, 0.3))
        k += 1
    b.add(t0, projector(d), gain=0.08)

def m_door(b, t0, d, seg, c):
    n = N(d); t = T(n)
    b.add(t0, projector(d), gain=0.07)
    wind = bp(noise(n), 300, 1200) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t)) * np.clip((t - c["open"]) / 1.5, 0, 1)
    waves = lp(noise(n), 600) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t) ** 2) * np.clip((t - c["open"]) / 2, 0, 1)
    b.add(t0, wind, gain=0.12, pan=-0.3); b.add(t0, waves, gain=0.25, pan=0.3)
    b.add(t0 + c["open"] - 0.3, pad([57, 64, 69, 76], d - c["open"] + 0.3, 1600, a=1.5, r=2), gain=0.22)

def m_steps(b, t0, d, seg, c):
    b.add(t0, projector(d), gain=0.07)
    for i, st in enumerate(c["steps"]):
        b.add(t0 + st, tom(95 - i * 6, 1.0), gain=0.55)
    b.add(t0, pad([45, 52, 60], d, 600, a=2, r=2), gain=0.15)

def m_direct(b, t0, d, seg, c):
    bpm = 104; bt = 60 / bpm
    for i, k in enumerate(steps_at(bpm, d, 0.5)):
        pat = [1, 0, 0, 1, 0, 0, 1, 0]  # 3-3-2 clave feel
        if pat[i % 8]: b.add(t0 + k, bp(noise(N(0.04)), 2500, 4500) * dec(N(0.04), 80), gain=0.25)
    bass = [45, 45, 52, 52, 50, 50, 52, 44]
    for i, k in enumerate(steps_at(bpm, d, 1)):
        b.add(t0 + k, pluck(bass[i % 8] - 12, 0.6, 0.99), gain=0.35)
    mel = [69, 72, 76, 74, 72, 71, 69, 64]
    for i, k in enumerate(steps_at(bpm, d, 1, bt * 0.5)):
        if i % 2 == 0: b.add(t0 + k, bell(mel[(i // 2) % 8], 0.8, 2.0, 1.5, 4), gain=0.10, pan=0.4)
    b.add(t0, projector(d), gain=0.06)

def m_synchromy(b, t0, d, seg, c):
    bt = 60 / SYNCH_BPM; loop = 24 * bt; t = 0.5
    while t < d:
        for beat, L, m in SYNCH_NOTES:
            st = t + beat * bt
            if st < d:
                s = osc("sq", float(mtof(m)), N(L * bt * 0.95)) * env(N(L * bt * 0.95), 0.005, 0.03)
                b.add(t0 + st, lp(s, 3000), gain=0.07)
        t += loop

def m_osc(b, t0, d, seg, c):
    n = N(d); t = T(n)
    seg_t = t + c.get("osc_offset", 0.0)
    k = np.minimum((seg_t // OSC_STEP).astype(int), len(OSC_RATIOS) - 1)
    a = np.array([r[0] for r in OSC_RATIOS])[k]; bb = np.array([r[1] for r in OSC_RATIOS])[k]
    f0 = 110.0
    L = np.sin(2 * np.pi * np.cumsum(f0 * a) / SR)
    R = np.sin(2 * np.pi * np.cumsum(f0 * bb) / SR + 0.4 * seg_t)
    x = np.stack([L, R], 1) * env(n, 1.0, 1.5)[:, None]
    b.add(t0, lp(x.T, 1200).T, gain=0.07)
    b.add(t0, pad([45, 57, 64], d, 700, a=2, r=2), gain=0.10)

def m_dome(b, t0, d, seg, c):
    n = N(d); t = T(n)
    prog(b, t0, d, [DM7, EM9, DM7, [47, 54, 57, 62, 66]], d / 4, gain=0.25, bright=1100)
    for i, k in enumerate(np.arange(0.5, d, 0.45)):
        m = [74, 78, 81, 85, 88, 81][i % 6]
        b.add(t0 + k, bell(m, 1.5, 2.0, 1.2, 3), gain=0.05, pan=float(np.sin(k * 1.3)))
    b.add(t0, lp(noise(n), 300) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)), gain=0.10)

def m_harmonograph(b, t0, d, seg, c):
    pent = [62, 64, 66, 69, 71, 74, 76, 78]
    for i, k in enumerate(np.arange(0.4, d, 0.62)):
        b.add(t0 + k, bell(pent[(i * 3) % 8], 2.2, 3.5, 3, 2), gain=0.08, pan=0.5 * np.sin(i))
    prog(b, t0, d, [DM7, [43, 50, 59, 66]], d / 2, gain=0.18, bright=900)

def m_whitney(b, t0, d, seg, c):
    lyd = [62, 66, 68, 69, 73, 74, 78, 80]
    for i, k in enumerate(np.arange(0.3, d, 0.31)):
        b.add(t0 + k, bell(lyd[(i * 5) % 8] + (12 if i % 7 == 0 else 0), 1.4, 2.0, 2, 3), gain=0.06, pan=0.6 * np.sin(i * 0.7))
    prog(b, t0, d, [[50, 57, 62, 66, 68]], d, gain=0.18, bright=1000)

def m_leader(b, t0, d, seg, c):
    b.add(t0, projector(d), gain=0.12)
    for k in c["counts"]:
        b.add(t0 + k, osc("sine", 1000.0, N(0.12)) * env(N(0.12), 0.002, 0.02), gain=0.06)
    for i, k in enumerate(c["cards"]):
        b.add(t0 + k, tom(70, 1.2), gain=0.45)
        b.add(t0 + k, pad([[48, 55, 60], [46, 53, 58], [44, 51, 56], [43, 50, 55]][i % 4], 1.4, 2200, a=0.01, r=1.0), gain=0.3)

def m_liquid(b, t0, d, seg, c):
    bpm = 92; bt = 60 / bpm
    prog_ch = [[57, 60, 64, 67], [50, 57, 60, 66]]
    k = 0; t = 0.0
    while t < d:
        b.add(t0 + t, organ(prog_ch[k % 2], min(4 * bt, d - t) + 0.2), gain=0.25)
        t += 4 * bt; k += 1
    for i, s in enumerate(steps_at(bpm, d, 0.5)):
        pat = [1, 0, 1, 1, 0, 1, 0, 1]
        if pat[i % 8]: b.add(t0 + s, tom(220 if i % 2 else 300, 0.3), gain=0.12, pan=0.4 if i % 2 else -0.4)
    for i, s in enumerate(steps_at(bpm, d, 1)):
        b.add(t0 + s, pluck([33, 33, 40, 38][i % 4], 0.8, 0.99), gain=0.35)

def m_slitscan(b, t0, d, seg, c):
    n = N(d); t = T(n); x = np.zeros(n)
    for i in range(22):
        f = rng.uniform(250, 900); g = rng.uniform(-0.15, 0.15)
        x += np.sin(2 * np.pi * np.cumsum(f * (1 + g * t / d)) / SR + rng.random() * 6)
    first = seg["beats"][0]["p"].get("speed", 1.0) == 1.0
    shape = np.clip(t / (d * 0.7), 0, 1) ** 1.5 if first else np.clip(1 - t / d, 0.1, 1)
    b.add(t0, x / 22 * shape * env(n, 1.5, 2.0), gain=0.35)
    b.add(t0, lp(noise(n), 120) * env(n, 1, 1), gain=0.25)

def m_feedback_mid(b, t0, d, seg, c):
    # OffOn / CRT: tape-wobbled electronic sequence
    n = N(d); t = T(n)
    wob = 1 + 0.01 * np.sin(2 * np.pi * 0.7 * t)
    seq = [57, 64, 60, 67, 62, 69, 64, 71]
    for i, k in enumerate(np.arange(0.2, d, 0.24)):
        m = seq[i % 8] + (12 if (i // 8) % 2 else 0)
        s = lp(osc("saw", float(mtof(m)) * wob[min(N(k), n - 1)], N(0.2)) * dec(N(0.2), 12), 1800)
        b.add(t0 + k, s, gain=0.06, pan=0.5 * np.sin(i * 0.9))
    b.add(t0, pad([45, 52, 57], d, 600), gain=0.15)

def m_tvwall(b, t0, d, seg, c):
    b.add(t0, hiss(d, 1500, 9000), gain=0.035); b.add(t0, hum(d), gain=0.06)
    for i, k in enumerate(np.arange(0.8, d, 1.9)):
        m = [45, 56, 51, 62, 46, 58][i % 6]
        b.add(t0 + k, pluck(m, 3, 0.994, 1.0) * 0.6 + bell(m + 24, 3, 1.41, 3, 3) * 0.3, gain=0.25, pan=0.4 * np.sin(i))

def m_magnet(b, t0, d, seg, c):
    n = N(d); t = T(n)
    f = 330 * (1 + 0.15 * np.sin(2 * np.pi * 0.21 * t) * np.sin(2 * np.pi * 0.05 * t))
    b.add(t0, osc("sine", f, n) * env(n, 1, 1), gain=0.07)
    b.add(t0, hum(d), gain=0.07)
    b.add(t0, pad([45, 52, 60], d, 600), gain=0.12)

def m_vhs(b, t0, d, seg, c):
    n = N(d); t = T(n)
    whirr = osc("saw", 200 + 1800 * (t % 3.0) / 3.0, n) * (t < 3.0)
    b.add(t0, lp(whirr, 2500) * env(n, 0.05, 0.3), gain=0.05)
    wow = 1 + 0.006 * np.sin(2 * np.pi * 0.6 * t)
    for m in (45, 52, 57, 60):
        b.add(t0 + 2.5, lp(osc("saw", float(mtof(m)) * wow[: N(d - 2.5)], N(d - 2.5)), 900) * env(N(d - 2.5), 1.5, 2), gain=0.04)
    b.add(t0, hiss(d, 3000, 10000), gain=0.02)

def m_colorizer(b, t0, d, seg, c):
    pent = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79]
    for i, k in enumerate(np.arange(0.3, d, 60 / 120 / 4)):
        if rng.random() < 0.55:
            m = pent[rng.integers(len(pent))]
            s = bell(m, 0.25, rng.choice([1.0, 2.0, 3.01]), 2.5, 14)
            b.add(t0 + k, s, gain=0.05, pan=rng.uniform(-0.7, 0.7))
    prog(b, t0, d, [AM, [53, 57, 62, 65]], 4.0, gain=0.18, bright=1000)

def m_beck(b, t0, d, seg, c):
    for i, k in enumerate(np.arange(0.2, d, 0.35)):
        m = 48 + rng.integers(0, 36)
        s = bell(int(m), 0.6, rng.choice([1.41, 2.0, 3.5]), 3, 6)
        b.add(t0 + k, s, gain=0.05, pan=rng.uniform(-0.8, 0.8))
    b.add(t0, pad([45, 52], d, 500), gain=0.15)

def m_schematic(b, t0, d, seg, c):
    m_type(b, t0, d, seg, c, text="THE DISTRIBUTION RELIGION")
    for k in np.arange(3.0, d, 1.0):
        b.add(t0 + k, sine_note(81, 0.08, 0.002, 0.03), gain=0.03)
    b.add(t0, pad([45, 52, 57], d, 700), gain=0.14)

def m_voicesynth(b, t0, d, seg, c):
    b.add(t0, pad([33, 45], d, 300, a=2, r=2), gain=0.18)

def m_ruttetra(b, t0, d, seg, c):
    mel = [(0.5, 64, 2.0), (2.5, 67, 1.5), (4.0, 69, 3.0), (7.0, 72, 2.0), (9.0, 71, 1.5), (10.5, 69, 2.5),
           (13.0, 76, 3.0), (16.0, 74, 2.0), (18.0, 72, 2.5), (20.5, 69, 4.0)]
    for st, m, L in mel:
        if st < d:
            gr = st / d
            b.add(t0 + st, violin(m, L + 0.3, vib=0.006 + 0.01 * gr, grit=gr), gain=0.10)
    b.add(t0, pad([45, 52, 57], d, 600), gain=0.14)

def m_channels(b, t0, d, seg, c):
    snippets = [lambda L: organ([57, 60, 64], L), lambda L: hum(L), lambda L: chip([60, 64, 67, 72], 140, L) * 0.5,
                lambda L: pad([48, 55, 64], L, 1500), lambda L: bell(76, L, 2, 2, 1.5), lambda L: hiss(L, 2000, 6000) * 0.3]
    edges = [0.0] + c["switch"] + [d]
    for i in range(len(edges) - 1):
        L = edges[i + 1] - edges[i]
        sn = snippets[i % len(snippets)](L); e = env(len(sn), 0.02, 0.05)
        b.add(t0 + edges[i], sn * (e if sn.ndim == 1 else e[:, None]), gain=0.10)
        if i > 0: b.add(t0 + edges[i], hiss(0.12, 1000, 9000), gain=0.08)

def m_buddha(b, t0, d, seg, c):
    b.add(t0 + 0.6, bowl(57, 14), gain=0.5)
    if d > 18: b.add(t0 + d * 0.55, bowl(52, 14), gain=0.4)
    b.add(t0, hum(d, 50), gain=0.02)

def groove(b, t0, d, bpm, intensity=3, gated=True):
    bt = 60 / bpm
    for i, k in enumerate(steps_at(bpm, d, 0.5)):
        beat = i // 2; off = i % 2
        if not off and beat % 2 == 0: b.add(t0 + k, kick(), gain=0.45)
        if not off and beat % 2 == 1 and intensity >= 2: b.add(t0 + k, snare(0.35, gated), gain=0.25)
        if intensity >= 1: b.add(t0 + k, hat(), gain=0.08, pan=0.3)
    if intensity >= 2:
        bass = [45, 57, 45, 57, 41, 53, 43, 55]
        for i, k in enumerate(steps_at(bpm, d, 0.5)):
            s = lp(osc("saw", float(mtof(bass[(i // 2) % 8] - 12 + (12 if i % 2 else 0))), N(bt * 0.45)) * env(N(bt * 0.45), 0.003, 0.05), 900)
            b.add(t0 + k, s, gain=0.18)
    if intensity >= 3:
        prog(b, t0, d, [AM, FM, CM, GM], 4 * bt, gain=0.2, bright=2500)

def m_tango(b, t0, d, seg, c):
    bpm = 112; bt = 60 / bpm
    for k in steps_at(bpm, d, 2):
        for st, w in ((0, 1.0), (0.75, 0.7), (1.0, 0.8), (1.5, 0.7)):  # habanera
            t = k + st * bt
            if t >= d: continue
            n_ch = tango_count(c, t)
            b.add(t0 + t, pluck(33 if st < 1 else 40, 0.5, 0.99), gain=0.4 * w)
            if n_ch >= 6:
                ch = [57, 60, 64] if int(k / (4 * bt)) % 2 == 0 else [56, 59, 64]
                s = sum(lp(osc("saw", float(mtof(m)) * (1 + 0.003 * j), N(bt * 0.4)), 1800) for j, m in enumerate(ch))
                b.add(t0 + t, s * env(N(bt * 0.4), 0.01, 0.08), gain=0.06 * w)
            if n_ch >= 20 and st == 0:
                b.add(t0 + t, snare(0.15), gain=0.08)
    mel = [76, 77, 76, 72, 69, 71, 72, 74, 76, 81, 80, 76, 77, 76, 74, 72]
    for i, k in enumerate(steps_at(bpm, d, 1)):
        if tango_count(c, k) >= 12:
            b.add(t0 + k, violin(mel[i % 16], bt * 0.9, 0.005), gain=0.07)
            if tango_count(c, k) >= 30:
                b.add(t0 + k, violin(mel[i % 16] - 12, bt * 0.9, 0.005), gain=0.05)

def m_alley(b, t0, d, seg, c):
    n = N(d); t = T(n)
    b.add(t0, lp(noise(n), 400) * env(n, 1, 1), gain=0.15)
    siren = osc("sine", 700 + 150 * np.sin(2 * np.pi * 0.4 * t), n) * np.exp(-((t - d * 0.6) / 3) ** 2)
    b.add(t0, lp(siren, 900), gain=0.015, pan=0.6)
    for k in (2.0, 7.0, 12.0):
        if k < d: b.add(t0 + k, hp(noise(N(1.2)), 4000) * env(N(1.2), 0.3, 0.8) * 0.4, gain=0.06)
    b.add(t0, pad([45, 48, 52], d, 500, a=2, r=2), gain=0.12)

def m_mtv(b, t0, d, seg, c): groove(b, t0, d, 100, 3)
def m_chain(b, t0, d, seg, c): groove(b, t0, d, 100, 2)

def m_faces(b, t0, d, seg, c):
    bt = 60 / 70
    for i, k in enumerate(steps_at(70, d, 1)):
        if i % 2 == 1: b.add(t0 + k, snare(0.6, gated=True), gain=0.2)
        if i % 4 == 0: b.add(t0 + k, kick(0.6), gain=0.3)
    prog(b, t0, d, [[45, 57, 60, 64, 71], [41, 57, 60, 64, 69], [48, 55, 60, 64, 67], [43, 55, 59, 62, 67]], 4 * bt, gain=0.25, bright=2200)

def m_train(b, t0, d, seg, c):
    bt = 60 / TRAIN_BPM
    for i, k in enumerate(c["poles"]):
        b.add(t0 + k, kick(0.4), gain=0.45)
        b.add(t0 + k + bt / 2, hat(True), gain=0.06)
        if i % 4 == 0: b.add(t0 + k, pad([57, 64, 67, 72], 4 * bt, 2600, a=0.01, r=0.5), gain=0.2)
    bass = [45, 45, 57, 45, 43, 43, 55, 43]
    for i, k in enumerate(np.arange(c["poles"][0], d, bt / 2)):
        b.add(t0 + k, lp(osc("saw", float(mtof(bass[i % 8] - 12)), N(bt * 0.4)) * env(N(bt * 0.4), 0.003, 0.05), 1000), gain=0.15)

def m_loopwalk(b, t0, d, seg, c):
    bpm = LOOP_BPM; bt = 60 / bpm
    for lap_i, L0 in enumerate(c["laps"]):
        L = min(c["lap"], d - L0)
        if L <= 0: continue
        for k in steps_at(bpm, L, 1):
            b.add(t0 + L0 + k, kick(), gain=0.4)
            b.add(t0 + L0 + k + bt / 2, hat(), gain=0.08)
        if lap_i >= 1:
            for i, k in enumerate(steps_at(bpm, L, 0.5)):
                b.add(t0 + L0 + k, lp(osc("saw", float(mtof([33, 45][i % 2])), N(bt * 0.4)) * env(N(bt * 0.4), 0.003, 0.05), 800), gain=0.15)
        if lap_i >= 2:
            b.add(t0 + L0, pad([57, 60, 64, 69], L, 2200, a=0.05, r=0.4), gain=0.2)
        if lap_i >= 3:
            for i, k in enumerate(steps_at(bpm, L, 0.5)):
                b.add(t0 + L0 + k, bell([69, 72, 76, 79, 76, 72, 74, 71][i % 8], 0.5, 2, 2, 5), gain=0.06, pan=0.4)
        if lap_i >= 1:
            for k in steps_at(bpm, L, 2, bt):
                b.add(t0 + L0 + k, clap(), gain=0.15)

def m_psychedelia(b, t0, d, seg, c):
    bpm = CHIP_BPM
    notes = [57, None, 57, 60, None, 64, 62, None, 57, None, 57, 67, None, 64, 62, 60]
    b.add(t0, chip(notes, bpm, d, (0, 3, 7)), gain=0.07)
    bassn = [33, None, None, 33, None, None, 31, None, 29, None, None, 29, None, 31, None, None]
    b.add(t0, lp(chip(bassn, bpm, d, (0,), 0.05), 1200), gain=0.08)
    for i, k in enumerate(steps_at(bpm, d, 0.5)):
        if i % 4 == 2: b.add(t0 + k, crush(np.stack([noise(N(0.1))] * 2, 1) * dec(N(0.1), 30)[:, None], 3, 6), gain=0.08)
    if len(seg["beats"]) > 1:
        st = seg["beats"][1]["start"] - seg["beats"][0]["start"]
        b.add(t0 + st, pad([45, 57, 64, 71], d - st, 1800, a=2, r=2), gain=0.2)

def m_wiregrid(b, t0, d, seg, c):
    prog(b, t0, d, [[50, 57, 62, 66, 69], [47, 54, 59, 62, 66], [43, 50, 55, 59, 62], [45, 52, 57, 61, 64]], d / 4, gain=0.3, bright=2000)
    arp = [74, 78, 81, 85, 81, 78]
    for i, k in enumerate(np.arange(0.2, d, 60 / 100 / 2)):
        b.add(t0 + k, bell(arp[i % 6], 1.0, 2.0, 1.5, 3), gain=0.05, pan=0.5 * np.sin(i * 0.5))

def m_mandel(b, t0, d, seg, c):
    n = N(d); t = T(n)
    prog(b, t0, d, [[38, 50, 57, 62, 65], [36, 48, 55, 60, 64], [41, 53, 57, 60, 65]], d / 3, gain=0.28, bright=900)
    if len(seg["beats"]) > 1:
        st = seg["beats"][1]["start"] - seg["beats"][0]["start"]
        throb = osc("sine", 55.0, n) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.5 * t)) * np.clip((t - st) / 3, 0, 1)
        b.add(t0, throb * env(n, 0.1, 2), gain=0.12)

RAVE_ACID = [45, 45, 57, None, 45, 48, None, 45, 55, None, 45, 57, 43, None, 45, 52]

def m_tunnel(b, t0, d, seg, c, intensity=2):
    bpm = RAVE_BPM; bt = 60 / bpm
    for i, k in enumerate(steps_at(bpm, d, 0.5)):
        if i % 2 == 0: b.add(t0 + k, kick(0.35, 48, 9), gain=0.5)
        else: b.add(t0 + k, hat(True), gain=0.07)
        if i % 4 == 2: b.add(t0 + k, clap(), gain=0.15)
    b.add(t0, acid([m - 12 if m else None for m in RAVE_ACID], bpm, d, (250, 1800 + 800 * intensity), 0.8 + 0.05 * intensity), gain=0.25)
    b.add(t0, pad([57, 64, 69], d, 1500, a=1, r=1), gain=0.12)

def m_milkdrop(b, t0, d, seg, c): m_tunnel(b, t0, d, seg, c, intensity=3)

def m_flame(b, t0, d, seg, c):
    prog(b, t0, d, [[45, 57, 64, 71, 76], [41, 53, 60, 67, 72], [43, 55, 62, 69, 74], [40, 52, 59, 64, 71]], d / 4, gain=0.3, bright=1600)
    for k in np.arange(0.3, d, 0.17):
        if rng.random() < 0.35:
            b.add(t0 + k, bell(int(rng.choice([81, 83, 86, 88, 91, 93])), 1.2, 2.0, 1, 3), gain=0.025, pan=rng.uniform(-1, 1))

def m_blocks(b, t0, d, seg, c):
    for k in np.arange(0.2, d, 0.125):
        if rng.random() < 0.3:
            s = np.stack([noise(N(0.03))] * 2, 1) * dec(N(0.03), 120)[:, None]
            b.add(t0 + k, crush(s, 2, 4), gain=0.10, pan=rng.uniform(-0.8, 0.8))
    p = pad([45, 52, 60, 64], d, 1600, a=1, r=1)
    b.add(t0, crush(p, 4, 6), gain=0.25)

def m_mosh(b, t0, d, seg, c, src=None):
    # smear a grain of the rave music across time: the past dragged into the present
    if src is not None:
        out = np.zeros((N(d), 2)); pos = 0
        while pos < len(out):
            g = N(rng.uniform(0.06, 0.25)); reps = int(rng.integers(1, 5))
            a = int(rng.integers(0, len(src) - g))
            grain = src[a:a + g] * env(g, 0.005, 0.01)[:, None]
            for r in range(reps):
                j = min(len(out), pos + g)
                out[pos:j] += grain[: j - pos]; pos = j
                if pos >= len(out): break
        out = crush(out, 5, 3) * np.linspace(1, 0.4, len(out))[:, None]
        b.add(t0, out, gain=0.6)
    b.add(t0, pad([45, 48, 52], d, 600), gain=0.12)

def m_dream(b, t0, d, seg, c):
    n = N(d); out = np.zeros(n)
    for m, (f1, f2) in zip((57, 60, 64, 69), ((700, 1100), (400, 1700), (300, 2300), (500, 900))):
        s = osc("saw", float(mtof(m)) * (1 + 0.004 * np.sin(2 * np.pi * 0.3 * T(n))), n)
        out += bp(s, f1 * 0.8, f1 * 1.2) + 0.6 * bp(s, f2 * 0.85, f2 * 1.15)
    b.add(t0, out * env(n, 2, 2), gain=0.25)
    b.add(t0, hiss(d, 4000, 9000), gain=0.01)

def m_prompt(b, t0, d, seg, c):
    m_type(b, t0, d, seg, c, text="a surreal psychedelic dream, endless")
    b.add(t0, pad([45, 52, 60, 64], d, 900), gain=0.18)

def m_recipe(b, t0, d, seg, c):
    for i, k in enumerate(steps_at(90, d, 1)):
        b.add(t0 + k, kick(0.3, 50, 12), gain=0.18)
        b.add(t0 + k + 1 / 3, hp(noise(N(0.06)), 6000) * dec(N(0.06), 50), gain=0.05)
    for i, st in enumerate(c["steps"]):
        b.add(t0 + st, bell([69, 72, 74, 76, 79, 81][i % 6], 2.0, 2, 2, 2), gain=0.12)
    prog(b, t0, d, [AM9, [41, 57, 60, 64, 69], [48, 55, 60, 64, 67], [43, 55, 59, 62, 67]], d / 4, gain=0.22, bright=1200)

def m_crtoff(b, t0, d, seg, c):
    n = N(0.6); f = 2000 * np.exp(-T(n) * 7) + 40
    b.add(t0 + c["off"], osc("sine", f, n) * dec(n, 5), gain=0.15)
    b.add(t0 + c["off"], click(), gain=0.3)

def m_credits(b, t0, d, seg, c):
    ch = [AM9, [41, 57, 60, 64, 69], [48, 55, 60, 64, 67], [43, 55, 59, 62, 67]]
    prog(b, t0, d, ch, d / 6, gain=0.3, bright=1500)
    arp = [69, 72, 76, 79, 76, 72]
    for i, k in enumerate(np.arange(0.5, d - 4, 0.42)):
        b.add(t0 + k, pluck(arp[i % 6], 2.0, 0.997), gain=0.08, pan=0.4 * np.sin(i * 0.6))

MAP = dict(feedback=m_open_feedback, montage=m_montage, title=m_title, actcard=m_actcard, eye=m_eye, type=m_type,
           door=m_door, steps=m_steps, direct=m_direct, synchromy=m_synchromy, osc=m_osc, dome=m_dome,
           harmonograph=m_harmonograph, whitney=m_whitney, leader=m_leader, liquid=m_liquid, slitscan=m_slitscan,
           tvwall=m_tvwall, magnet=m_magnet, vhs=m_vhs, colorizer=m_colorizer, beck=m_beck, schematic=m_schematic,
           voicesynth=m_voicesynth, ruttetra=m_ruttetra, channels=m_channels, buddha=m_buddha, tango=m_tango,
           alley=m_alley, mtv=m_mtv, chain=m_chain, faces=m_faces, train=m_train, loopwalk=m_loopwalk,
           psychedelia=m_psychedelia, wiregrid=m_wiregrid, mandel=m_mandel, tunnel=m_tunnel, flame=m_flame,
           blocks=m_blocks, mosh=m_mosh, dream=m_dream, prompt=m_prompt, recipe=m_recipe, crtoff=m_crtoff,
           credits=m_credits)

def main(tl_path, out_path):
    tl = json.load(open(tl_path))
    total = tl["total"]
    b = Buf(total)
    rave_src = None
    for seg in tl["segs"]:
        t0 = seg["f0"] / tl["fps"]; d = seg["nf"] / tl["fps"]
        c = cues(seg)
        sc = seg["scene"]
        if sc == "door":
            s = beat_vo(seg)[0][2]
            c["open"] = s[1]["start"] + 2.0
        fn = MAP.get(sc)
        if sc == "feedback" and seg["act"] in ("light", "signal") and seg["beats"][0]["p"]["mode"] in ("offon",):
            fn = m_feedback_mid
        if sc == "feedback" and seg["beats"][0]["p"]["mode"] == "milkdrop":
            fn = m_milkdrop
        if sc == "mosh":
            fn(b, t0, d, seg, c, src=rave_src); continue
        if fn: fn(b, t0, d, seg, c)
        if sc == "tunnel":
            i0, i1 = N(t0), N(t0 + d)
            rave_src = b.x[i0:i1].copy()
        print("music", seg["idx"], sc, round(t0, 1), flush=True)
    x = b.x[: N(total)]
    x = reverb(x, 2.4, 0.22)
    x = hp(x.T, 30).T
    peak = np.max(np.abs(x)) + 1e-9
    x = x / peak * 0.9
    sf.write(out_path, x.astype(np.float32), SR, subtype="FLOAT")
    print("wrote", out_path, x.shape[0] / SR)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
