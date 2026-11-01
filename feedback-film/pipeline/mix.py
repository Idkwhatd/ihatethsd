import json, sys, os, subprocess
import numpy as np, soundfile as sf
from scipy import signal

SR = 48000

def main(tl_path, music_path, vo_dir, out_wav, ass_path, srt_path, with_vo=True):
    tl = json.load(open(tl_path))
    mus, sr = sf.read(music_path)
    n = len(mus)
    vo = np.zeros(n)
    if with_vo:
        for b in tl["beats"]:
            if not b["vo"]: continue
            x, s = sf.read(os.path.join(vo_dir, b["key"] + ".wav"))
            x = signal.resample_poly(x, 2, 1)
            x = signal.sosfilt(signal.butter(2, 90, "high", fs=SR, output="sos"), x)
            x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.085
            i = int((b["start"] + b["pre"]) * SR)
            vo[i:i + len(x)] += x[: n - i]
    # Duck the score under the voice: fast attack, slow release.
    env = np.abs(vo)
    a = signal.sosfilt(signal.butter(1, 6, "low", fs=SR, output="sos"), env)
    a = a / (a.max() + 1e-9)
    hold = np.convolve(a > 0.03, np.ones(int(0.35 * SR)), "same") > 0
    duck = signal.sosfilt(signal.butter(1, 2.5, "low", fs=SR, output="sos"), hold.astype(float))
    g = 1 - 0.55 * np.clip(duck, 0, 1)
    out = mus * g[:, None] + vo[:, None] * np.array([1.0, 1.0])
    out = out / (np.abs(out).max() + 1e-9) * 0.95
    tmp = out_wav + ".pre.wav"
    sf.write(tmp, out.astype(np.float32), SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", out_wav], check=True)
    os.remove(tmp)
    # Captions for the spoken lines.
    def ts(t, comma=False):
        h, r = divmod(t, 3600); m, s = divmod(r, 60)
        return f"{int(h):d}:{int(m):02d}:{s:05.2f}" if not comma else f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")
    def wrap(t, w=46):
        words, lines, cur = t.split(), [], ""
        for x in words:
            if len(cur) + len(x) + 1 > w and cur: lines.append(cur); cur = x
            else: cur = (cur + " " + x).strip()
        lines.append(cur); return lines
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter Medium,34,&H00FFFFFF,&H00FFFFFF,&H64000000,&H8C000000,0,0,0,0,100,100,0,0,4,10,0,2,80,80,46,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev, srt = [], []
    chunks = []
    for c in tl["caps"]:
        lines = wrap(c["text"])
        groups = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        total = sum(len(" ".join(g)) for g in groups)
        t = c["start"]
        for g in groups:
            dur = (c["end"] - c["start"]) * len(" ".join(g)) / total
            chunks.append((t, t + dur, g)); t += dur
    for i, (a0, a1, lines) in enumerate(chunks):
        end = a1 + (0.25 if i + 1 == len(chunks) or chunks[i + 1][0] - a1 > 0.3 else 0.0)
        ev.append(f"Dialogue: 0,{ts(a0)},{ts(end)},Default,,0,0,0,," + "\\N".join(lines))
        srt.append(f"{i + 1}\n{ts(a0, True)} --> {ts(end, True)}\n" + "\n".join(lines) + "\n")
    open(ass_path, "w").write(head + "\n".join(ev) + "\n")
    open(srt_path, "w").write("\n".join(srt))
    print("mixed", out_wav, len(out) / SR, "captions", len(ev))

if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], a[4], a[5], a[6], with_vo=(len(a) < 8 or a[7] != "novo"))
