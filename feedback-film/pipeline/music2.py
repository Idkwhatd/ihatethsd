# Score v2: continuous act-level pieces for the archival acts, per-scene cues for the recreations,
# per-segment reverb and hard cuts where the picture cuts hard.
import json, sys, os
import numpy as np
import soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
import music as M
from music import *   # instruments, Buf, helpers
from cues import cues, beat_vo

rng = np.random.default_rng(11)

class Local(Buf):
    """A segment's own buffer; add() takes absolute times."""
    def __init__(self, t0, d, tail=4.0):
        self.t0 = t0
        self.x = np.zeros((N(d + tail) + 1, 2))
    def add(self, t, sig, pan=0.0, gain=1.0):
        Buf.add(self, t - self.t0, sig, pan, gain)

def grid(t_act, bpm, sub, t0, d):
    """Absolute times of a beat grid anchored at act start, within [t0, t0+d)."""
    step = 60.0 / bpm / sub
    k0 = int(np.ceil((t0 - t_act) / step - 1e-9))
    out = []
    k = k0
    while t_act + k * step < t0 + d - 1e-6:
        out.append((k, t_act + k * step)); k += 1
    return out

def piano(m, dur=1.6, gain=1.0):
    a = pluck(m, dur, 0.9965, 0.75); b = pluck(m + 0.06, dur, 0.9965, 0.6)
    return (a + b * 0.8) * gain

# ---------------- I. TRICKS: music-hall stride ----------------
RAG = [([36, 43], [52, 55, 60]), ([45, 40], [55, 61, 64]), ([38, 45], [53, 57, 60]), ([43, 38], [53, 59, 62])]  # C A7 Dm7 G7
def a_tricks(b, t_act, t0, d, seg, c):
    bpm = 100
    b.add(t0, projector(d), gain=0.06)
    for k, t in grid(t_act, bpm, 1, t0, d):
        bar = (k // 4) % 4; beat = k % 4
        bass, ch = RAG[bar]
        if beat in (0, 2):
            b.add(t, piano(bass[beat // 2] - 0, 1.0), gain=0.32, pan=-0.2)
        else:
            for j, m in enumerate(ch):
                b.add(t + 0.005 * j, piano(m, 0.5), gain=0.12, pan=0.1)
    for k, t in grid(t_act, bpm, 2, t0, d):
        bar = (k // 8) % 4; pos = k % 8
        r = np.random.default_rng(k // 8 * 31 + 7)
        pattern = [1, 0, 1, 1, 0, 1, 1, 0] if (k // 8) % 2 == 0 else [1, 1, 0, 1, 0, 1, 0, 1]
        if pattern[pos]:
            tones = [m + 12 for m in RAG[bar][1]] + [72, 74, 76, 79]
            m = tones[int(r.integers(len(tones)) + pos) % len(tones)]
            b.add(t, piano(m, 0.9), gain=0.16, pan=0.25)
    film = seg["beats"][0]["p"].get("film")
    if film == "moon":
        hit = t0 + (439.2 - seg["beats"][0]["p"]["start"])
        b.add(hit, kick(1.2, 40, 3), gain=0.6); b.add(hit, hp(noise(N(2.5)), 4000) * dec(N(2.5), 2), gain=0.25)
    if film == "rubber":
        for st in (4.5, 9.5):
            n = N(2.2); f = 500 + 900 * T(n) / 2.2
            b.add(t0 + st, osc("sine", f, n) * env(n, 0.05, 0.3), gain=0.08)

# ---------------- II. VISUAL MUSIC: minimalist pulse ----------------
VM_CH = [[38, 50, 57, 60, 64, 69], [34, 46, 53, 57, 62, 65], [41, 53, 57, 60, 64, 67], [36, 48, 55, 62, 64, 69]]
def a_vmusic(b, t_act, t0, d, seg, c):
    bpm = 112
    film = seg["beats"][0]["p"].get("film", "")
    slow = film in ("anemic",)
    bright = film in ("study6", "opus4")
    for k, t in grid(t_act, bpm, 2, t0, d):
        bar = (k // 8) % 16; ch = VM_CH[(bar // 4) % 4]
        pos = k % 8
        seq = [3, 4, 5, 4, 2, 5, 3, 4] if (bar % 4) < 2 else [2, 4, 3, 5, 2, 4, 5, 3]
        if slow and pos % 2: continue
        m = ch[seq[pos]] + (12 if bright else 0)
        b.add(t, bell(m, 0.6 if not slow else 1.6, 4.0, 1.2 if not bright else 2.0, 6 if not slow else 2.5), gain=0.11, pan=0.35 * np.sin(k * 0.7))
        if pos in (0, 3, 6):
            b.add(t, bell(ch[1] + 12, 0.5, 2.0, 0.8, 7), gain=0.05, pan=-0.4)
    for k, t in grid(t_act, bpm, 1 / 4, t0, d):
        ch = VM_CH[(k // 4) % 4]
        b.add(t, pad(ch[:4], 60 / bpm * 4 + 0.6, 900, a=0.6, r=0.6), gain=0.16)
        b.add(t, pluck(ch[0], 2.0, 0.995, 0.3), gain=0.25)
    if film == "rhythmus":
        for k, t in grid(t_act, bpm, 1, t0, d):
            b.add(t, click(), gain=0.25, pan=0.5 if k % 2 else -0.5)

# ---------------- III. DREAMS: slow waltz, machines, and the razor ----------------
WZ = [([43], [59, 62, 66]), ([43], [59, 62, 66]), ([38], [57, 61, 66]), ([38], [57, 61, 66])]  # Gmaj7 / Dmaj7
def waltz(b, t_act, t0, d, theremin_on=False):
    bpm = 66
    for k, t in grid(t_act, bpm, 1, t0, d):
        bar = (k // 3) % 4; beat = k % 3
        bass, ch = WZ[bar]
        if beat == 0: b.add(t, piano(bass[0] - 12 + 12, 2.5), gain=0.30, pan=-0.2)
        else:
            for j, m in enumerate(ch): b.add(t + 0.01 * j, piano(m, 1.4), gain=0.07)
    for k, t in grid(t_act, bpm, 1 / 3, t0, d):
        r = np.random.default_rng(k * 17 + 3)
        scale = [66, 67, 69, 71, 73, 74, 76, 78]
        m = scale[int(r.integers(len(scale)))]
        b.add(t + 60 / bpm, piano(m, 3.0), gain=0.12, pan=0.25)
        if theremin_on:
            L = 60 / bpm * 3
            b.add(t, theremin([(0, m), (L, m)], L + 0.3), gain=0.05)

def machines(b, t_act, t0, d, bpm=132, dark=False):
    for k, t in grid(t_act, bpm, 2, t0, d):
        if k % 2 == 0: b.add(t, kick(0.3, 55, 12), gain=0.35)
        b.add(t, bell(84 if k % 4 else 79, 0.15, 1.41, 2.0, 25), gain=0.06, pan=0.5 * np.sin(k))
        if k % 8 == 4: b.add(t, snare(0.2), gain=0.15)
    for k, t in grid(t_act, bpm, 1 / 2, t0, d):
        b.add(t, lp(osc("saw", float(mtof(33 if not dark else 31)), N(60 / bpm * 2)) * env(N(60 / bpm * 2), 0.01, 0.2), 700), gain=0.18)

def a_dreams(b, t_act, t0, d, seg, c):
    p = seg["beats"][0]["p"]; film = p.get("film")
    if seg["scene"] == "black":
        return
    if film == "ballet":
        machines(b, t_act, t0, d, 120)
    elif film == "vertov":
        machines(b, t_act, t0, d, 132, dark=True)
    elif film == "chien" and p["start"] < 100:
        # The prologue: waltz, then a string cluster that cuts to silence with the picture.
        waltz(b, t_act, t0, min(d, 14))
        L = d - 12
        st = sum(violin(m, L, vib=0.012) for m in (57, 58, 63, 64, 70))
        st = st * (np.linspace(0, 1, len(st)) ** 2)
        b.add(t0 + 12, st, gain=0.16)
        b.add(t0 + 12, pad([33, 34], L, 300, a=3, r=0.01), gain=0.25)
    elif film == "chien":
        n = N(d); t = T(n)
        eerie = sum(osc("sine", float(mtof(m)) * (1 + 0.003 * np.sin(2 * np.pi * 0.2 * t + j)), n) for j, m in enumerate((88, 91, 95)))
        b.add(t0, eerie * env(n, 2.0, 2.0) / 3, gain=0.08)
        for k in np.arange(0.3, d, 0.5): b.add(t0 + k, click(), gain=0.18)
        b.add(t0, pad([38, 45, 50], d, 400, a=2, r=2), gain=0.18)
    else:
        waltz(b, t_act, t0, d, theremin_on=film in ("seashell", "usher", "emak"))

def m_pasdedeux(b, t0, d, seg, c):
    bpm = 72; bt = 60 / bpm
    mel = [(0, 69, 2), (2, 72, 1), (3, 71, 1), (4, 69, 2), (6, 67, 1), (7, 64, 1), (8, 65, 3), (11, 64, 1),
           (12, 69, 2), (14, 72, 1), (15, 74, 1), (16, 76, 3), (19, 74, 1), (20, 72, 2), (22, 71, 2), (24, 69, 4)]
    for st, m, L in mel:
        t = 1.0 + st * bt
        if t >= d: break
        n = N(L * bt + 0.2); tt = T(n); f0 = float(mtof(m)); f = f0 * (1 + 0.006 * np.sin(2 * np.pi * 5 * tt) * np.clip(tt * 3 - 0.3, 0, 1))
        flute = osc("sine", f, n) + 0.22 * osc("sine", 2 * f, n) + 0.05 * bp(noise(n), f0 * 0.8, f0 * 1.6)
        b.add(t0 + t, flute * env(n, 0.08, 0.25), gain=0.12, pan=0.15)
    ch = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [52, 56, 59, 64]]
    for i, t in enumerate(np.arange(0.2, d, bt / 2)):
        chord = ch[(i // 8) % 4]
        b.add(t0 + t, pluck(chord[i % 4] - (12 if i % 8 == 0 else 0), 2.5, 0.997, 0.35), gain=0.13, pan=-0.3 + 0.15 * (i % 4))
    b.add(t0, pad([45, 52, 57], d + 1, 600, a=2, r=2), gain=0.12)

SEE_SCI = ("eyeevo", "fisheye", "perceive")
SEE_PHI = ("cave", "doors", "homunculus")
def m_seeing(b, t0, d, seg, c):
    sc = seg["scene"]
    sents = [x for _, _, ss in beat_vo(seg) for x in ss]
    if sc in SEE_SCI:
        bpm = 60; bt = 60 / bpm
        chords = [[40, 52, 59, 62, 66], [36, 48, 55, 59, 64], [43, 50, 55, 59, 62], [38, 50, 57, 62, 66]]
        prog(b, t0, d, chords, 4 * bt, gain=0.22, bright=1100)
        motif = [76, 71, 67, 69, 71, 74]
        for i, t in enumerate(np.arange(0.5, d - 1, bt / 2)):
            if i % 8 in (0, 1, 2, 4, 5, 6):
                m = motif[i % 6] + (0 if (i // 16) % 2 == 0 else -5)
                b.add(t0 + t, bell(m, 1.6, 3.0, 1.2, 3), gain=0.07, pan=0.4 * np.sin(i * 0.8))
        if sc == "perceive" and len(sents) > 3:
            q0, q1 = sents[2]["start"], sents[3]["end"] + 4.5
            n = N(q1 - q0); b.add(t0 + q0, -0.0 * np.zeros(n))
            for k in np.arange(q0, q1, 1.0): b.add(t0 + k, click(), gain=0.12)
    else:
        n = N(d); t = T(n)
        cello = [(0.5, 45, 6), (6.5, 48, 6), (12.5, 43, 6), (18.5, 45, 8), (26.5, 41, 6), (32.5, 43, 6), (38.5, 45, 8)]
        for st, m, L in cello:
            if st < d - 1: b.add(t0 + st, violin(m, min(L, d - st), vib=0.007), gain=0.12)
        prog(b, t0, d, [[38, 50, 53, 57, 62], [34, 46, 53, 58, 62], [36, 48, 55, 60, 64], [33, 45, 52, 57, 61]], d / 4, gain=0.2, bright=700)
        if sc == "cave":
            b.add(t0, lp(noise(n), 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t)) * env(n, 2, 2), gain=0.06)
        if sc == "doors" and len(sents) > 3:
            hit = sents[3]["start"]
            b.add(t0 + hit - 1.5, swell(1.5, 300, 9000), gain=0.14)
            b.add(t0 + hit, pad([45, 57, 61, 64, 69, 73, 76], d - hit + 1, 2600, a=0.05, r=2.5), gain=0.5)
            for k in np.arange(hit, d, 0.15):
                b.add(t0 + k, bell(int(rng.choice([81, 85, 88, 93])), 1.0, 2.0, 1.2, 3), gain=0.03, pan=rng.uniform(-1, 1))
        if sc == "homunculus" and len(sents) > 5:
            fb = sents[5]["start"]
            b.add(t0 + fb, (osc("sine", 55.0, N(d - fb)) + 0.5 * osc("sine", 82.4, N(d - fb))) * env(N(d - fb), 2.0, 2.0), gain=0.12)

ACT_FN = dict(tricks=a_tricks, vmusic=a_vmusic, dreams=a_dreams)

def m_actcard2(b, t0, d, seg, c):
    act = seg["act"]
    if act == "tricks":
        for j, m in enumerate([60, 64, 67, 72, 76]): b.add(t0 + 0.3 + j * 0.07, piano(m, 2.0), gain=0.18)
        b.add(t0 + 0.4, projector(d), gain=0.10)
    elif act == "vmusic":
        for j, m in enumerate([62, 69, 74, 76, 81]): b.add(t0 + 0.3 + j * 0.15, bell(m, 3.0, 4.0, 1.2, 2), gain=0.12, pan=(j - 2) * 0.3)
    elif act == "dreams":
        b.add(t0 + 0.2, theremin([(0, 62), (1.5, 69), (3.5, 66)], 3.8), gain=0.12)
    else:
        M.m_actcard(b, t0, d, seg, c)

def m_feedback2(b, t0, d, seg, c):
    act = seg["act"]; mode = seg["beats"][0]["p"].get("mode")
    n = N(d); t = T(n)
    if act == "open":
        w = osc("sine", 15734.0, N(6)) * env(N(6), 0.4, 2.5) * 0.004
        b.add(t0, w)
        rise = 57 + 7 * np.clip((t - 4) / (d - 4), 0, 1)
        b.add(t0, osc("sine", mtof(rise), n) * np.clip((t - 3) / 5, 0, 1) * env(n, 0.5, 2.0), gain=0.10)
        drone = osc("sine", 55.0, n) + 0.5 * osc("sine", 82.4, n) + 0.3 * osc("sine", 110.3, n)
        b.add(t0, drone * env(n, 3.0, 2.0), gain=0.10)
        prog(b, t0 + 12, d - 12, [AM9, [41, 57, 60, 64, 69], [43, 55, 59, 62, 67], AM9], (d - 12) / 4, gain=0.24, bright=1000)
    elif mode == "milkdrop":
        M.m_milkdrop(b, t0, d, seg, c)
    else:
        M.m_open_feedback(b, t0, d, seg, c)

def m_scope(b, t0, d, seg, c):
    M.m_ruttetra(b, t0, d, seg, c)

def main(tl_path, out_path):
    tl = json.load(open(tl_path))
    total = tl["total"]
    G = np.zeros((N(total) + SR * 6, 2))
    act_start = {}
    for seg in tl["segs"]:
        act_start.setdefault(seg["act"], seg["f0"] / tl["fps"])
    rave_src = None
    for seg in tl["segs"]:
        t0 = seg["f0"] / tl["fps"]; d = seg["nf"] / tl["fps"]
        c = cues(seg); sc = seg["scene"]; act = seg["act"]
        hard = (sc == "clip" and seg["beats"][0]["p"].get("film") == "chien" and seg["beats"][0]["p"]["start"] < 100) or sc in ("black", "crtoff")
        L = Local(t0, d, tail=0.0 if hard else 4.0)
        if act in ACT_FN and sc in ("clip", "black"):
            ACT_FN[act](L, act_start[act], t0, d, seg, c)
            mix = 0.18
        elif sc == "actcard":
            m_actcard2(L, t0, d, seg, c); mix = 0.3
        elif sc == "feedback":
            m_feedback2(L, t0, d, seg, c); mix = 0.25
        elif sc in SEE_SCI + SEE_PHI:
            m_seeing(L, t0, d, seg, c); mix = 0.28
        elif sc == "pasdedeux":
            m_pasdedeux(L, t0, d, seg, c); mix = 0.3
        elif sc == "scope":
            m_scope(L, t0, d, seg, c); mix = 0.25
        elif sc == "mosh":
            M.m_mosh(L, t0, d, seg, c, src=rave_src); mix = 0.15
        else:
            fn = M.MAP.get(sc)
            if fn: fn(L, t0, d, seg, c)
            mix = 0.22
        x = L.x
        if np.abs(x).max() > 0:
            x = reverb(x, 2.2, mix)
        if hard:
            x = x[: N(d)]
            x[-N(0.01):] *= np.linspace(1, 0, N(0.01))[:, None]
        else:
            fi = min(len(x), N(0.12)); x[:fi] *= np.linspace(0, 1, fi)[:, None]
        # Even out section loudness (partial), so quiet and loud cues sit closer together.
        body = x[: N(d)]
        r = np.sqrt(np.mean(body ** 2)) + 1e-9
        g = 10 ** ((-24 - 20 * np.log10(r)) * 0.6 / 20) if r > 1e-5 else 1.0
        x = x * min(g, 4.0)
        i = N(t0); G[i:i + len(x)] += x[: len(G) - i]
        if sc == "tunnel":
            rave_src = G[N(t0):N(t0 + d)].copy()
        print("music", seg["idx"], sc, round(t0, 1), flush=True)
    x = G[: N(total)]
    x = hp(x.T, 30).T
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    sf.write(out_path, x.astype(np.float32), SR, subtype="FLOAT")
    print("wrote", out_path, len(x) / SR)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
