import json, re, sys, os
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from script import SCRIPT

# Spoken form overrides (captions keep the written form).
SAY = [
    (r"Nilsson", "[Nilsson](/nˈɪlsən/)"),
    (r"Pelger", "[Pelger](/pˈɛlɡəɹ/)"),
    (r"Dan-Eric", "Dan Eric"),
    (r"Muybridge's", "[Muybridge's](/mˈIbɹɪʤɪz/)"),
    (r"Eadweard", "[Eadweard](/ˈɛdwəɹd/)"),
    (r"René Descartes", "[René](/ɹənˈA/) [Descartes](/dAkˈɑɹt/)"),
    (r"375 BC", "three hundred seventy-five B C"),
    (r"1637", "sixteen thirty-seven"),
    (r"1790", "seventeen ninety"),
    (r"Un Chien Andalou", "[Un Chien Andalou](/ˌʌn ʃjˈɛn ˌɑndəlˈu/)"),
    (r"Buñuel's", "[Buñuel's](/bunjwˈɛlz/)"),
    (r"Buñuel", "[Buñuel](/bunjwˈɛl/)"),
    (r"Dalí", "[Dalí](/dˈɑli/)"),
    (r"Ursulines", "[Ursulines](/ɜɹsulˈinz/)"),
    (r"Łódź", "[Lodz](/wˈuʤ/)"),
    (r"Zbigniew Rybczyński", "[Zbigniew](/zbˈiɡnjɛf/) [Rybczynski](/ɹɪbʧˈɪnski/)"),
    (r"Rybczyński", "[Rybczynski](/ɹɪbʧˈɪnski/)"),
    (r"Švankmajer", "[Svankmajer](/ʃvˈɑŋkmIəɹ/)"),
    (r"Vasulkas", "[Vasulkas](/vˈɑsʊlkəz/)"),
    (r"Vasulka", "[Vasulka](/vˈɑsʊlkə/)"),
    (r"Steina", "[Steina](/stˈAnə/)"),
    (r"Paik's", "[Paik's](/pˈIks/)"),
    (r"Paik", "[Paik](/pˈIk/)"),
    (r"Shuya Abe", "[Shuya](/ʃˈujə/) [Abe](/ˈɑbA/)"),
    (r"Mordvintsev", "[Mordvintsev](/mɔɹdvˈɪntsɛf/)"),
    (r"Geiss", "[Geiss](/ɡˈIs/)"),
    (r"Draves", "[Draves](/dɹˈAvz/)"),
    (r"Creme", "[Creme](/kɹˈim/)"),
    (r"Quays", "[Quays](/kwˈAz/)"),
    (r"Quay", "[Quay](/kwˈA/)"),
    (r"Gondry", "[Gondry](/ɡɔndɹˈi/)"),
    (r"Lye", "[Lye](/lˈI/)"),
    (r"Bute", "[Bute](/bjˈut/)"),
    (r"Kanye", "[Kanye](/kˈɑnjA/)"),
    (r"Takeshi Murata", "[Takeshi](/tɑkˈɛʃi/) [Murata](/muɹˈɑtə/)"),
    (r"Murata", "[Murata](/muɹˈɑtə/)"),
    (r"cyberdelic", "[cyberdelic](/sˌIbəɹdˈɛlɪk/)"),
    (r"Cyberdelia", "[Cyberdelia](/sˌIbəɹdˈiliə/)"),
    (r"Minogue", "[Minogue](/mɪnˈOɡ/)"),
    (r"Hammid", "[Hammid](/hˈæmɪd/)"),
    (r"WGBH", "W G B H"),
    (r"M-5", "M five"),
    (r"Kubrick's 2001", "Kubrick's two thousand and one"),
    (r"In 2001", "In two thousand and one"),
    (r"2005", "two thousand and five"),
    (r"2009", "two thousand and nine"),
    (r"2015", "twenty fifteen"),
    (r"OffOn", "Off On"),
    (r"A MOVIE", "A Movie"),
    (r"MTV", "M T V"),
    (r"VHS", "V H S"),
    (r"LSD", "L S D"),
    (r"VJs", "vee jays"),
    (r"the DJ", "the dee jay"),
    (r"Commodore 64", "Commodore sixty-four"),
    (r"Jaguar CD", "Jaguar C D"),
    (r"Philip K\. Dick", "Philip K Dick"),
]

_SAY = dict((a.replace("\\", ""), b) for a, b in SAY)
_SAY_RE = re.compile("|".join(re.escape(k) for k in sorted(_SAY, key=len, reverse=True)))

def spoken(s):
    # One pass, longest match first, so no override is rewritten by a shorter one.
    return _SAY_RE.sub(lambda m: _SAY[m.group(0)], s)

def sentences(text):
    parts = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9ŁŠ\"'])", text)
    out = []
    for p in parts:
        if out and re.search(r"\b[A-Z]\.$", out[-1]):  # e.g. "Philip K."
            out[-1] += " " + p
        else:
            out.append(p)
    return [p.strip() for p in out if p.strip()]

def main(outdir):
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a")
    os.makedirs(outdir, exist_ok=True)
    meta = {}
    gap = int(0.30 * 24000)
    n = 0
    for act, beats in SCRIPT:
        for bi, b in enumerate(beats):
            key = f"{act}_{bi:02d}"
            if not b["text"]:
                continue
            chunks, sents, pos = [], [], 0
            for s in sentences(b["text"]):
                audio = []
                for gs, ps, a in pipe(spoken(s), voice="af_heart", speed=0.98, split_pattern=None):
                    audio.append(np.asarray(a, dtype=np.float32))
                    print(key, "|", ps, flush=True)
                a = np.concatenate(audio)
                sents.append(dict(text=s, start=pos / 24000, end=(pos + len(a)) / 24000))
                chunks += [a, np.zeros(gap, np.float32)]
                pos += len(a) + gap
            wav = np.concatenate(chunks[:-1])
            sf.write(f"{outdir}/{key}.wav", wav, 24000)
            meta[key] = dict(dur=len(wav) / 24000, sents=sents)
            n += 1
    json.dump(meta, open(f"{outdir}/meta.json", "w"), indent=1, ensure_ascii=False)
    print("lines", n, "total speech", sum(m["dur"] for m in meta.values()))

if __name__ == "__main__":
    main(sys.argv[1])
