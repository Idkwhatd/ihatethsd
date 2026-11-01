# Rough photosensitivity screen: flags any 1-second window with more than 3 large luminance
# flashes (pairs of opposing swings >= 0.2 on a 0..1 scale) over a large part of the frame.
import subprocess, sys
import numpy as np

def main(path, fps=24):
    w, h = 32, 18
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                       stdout=subprocess.PIPE, check=True)
    fr = np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w).astype(np.float32) / 255
    cells = fr.reshape(len(fr), 3, h // 3, 4, w // 4).mean((2, 4)).reshape(len(fr), -1)  # 12 cells
    full = fr.mean((1, 2))
    bad = []
    for series in [full] + [cells[:, i] for i in range(cells.shape[1])]:
        d = np.diff(series)
        big = np.where(np.abs(d) >= 0.2)[0]
        sign = np.sign(d[big])
        ev = []
        for i in range(1, len(big)):
            if sign[i] != sign[i - 1] and big[i] - big[i - 1] <= fps:
                ev.append(big[i])
        ev = np.array(ev)
        for e in ev:
            if np.sum((ev > e - fps) & (ev <= e)) > 3:
                bad.append(e)
    bad = sorted(set(int(b) for b in bad))
    spans = []
    for b in bad:
        if spans and b - spans[-1][1] <= fps: spans[-1][1] = b
        else: spans.append([b, b])
    print("frames", len(fr), "flash spans:", [(round(a / fps, 1), round(b / fps, 1)) for a, b in spans])

if __name__ == "__main__":
    main(sys.argv[1])
