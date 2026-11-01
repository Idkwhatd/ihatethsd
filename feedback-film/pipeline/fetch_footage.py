"""Re-download the public-domain archival films (all first published before 1931) from the Internet Archive.

Usage: FX_ROOT=/path/to/work python fetch_footage.py
Writes $FX_ROOT/arch/raw/<key>.<ext> and splits Muybridge's horse into $FX_ROOT/arch/muy/NN.png.
"""
import json, os, urllib.parse, urllib.request
from PIL import Image, ImageSequence

ROOT = os.environ.get("FX_ROOT", "/tmp/fx")
RAW = os.path.join(ROOT, "arch", "raw"); os.makedirs(RAW, exist_ok=True)
rows = json.load(open(os.path.join(os.path.dirname(__file__), "footage_list.json")))
for key, ident, name, ext in rows:
    out = os.path.join(RAW, f"{key if key != 'chien2' else 'chien2'}.{ext}")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        continue
    url = f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}"
    print("fetch", key, url, flush=True)
    urllib.request.urlretrieve(url, out)
muy = os.path.join(ROOT, "arch", "muy"); os.makedirs(muy, exist_ok=True)
im = Image.open(os.path.join(RAW, "muybridge.gif"))
for i, f in enumerate(ImageSequence.Iterator(im)):
    f.convert("RGB").save(os.path.join(muy, f"{i:02d}.png"))
print("done")
