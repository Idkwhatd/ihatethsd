# FEEDBACK — 20-minute sensory cut. Real public-domain footage for 1901–1930 (all published before 1931),
# code recreations for later, still-copyrighted work. One short spoken line per act.

FX_ROOT = __import__("os").environ.get("FX_ROOT", "/tmp/fx")  # working folder for media, renders and caches
def B(scene, dur, text="", at=1.5, labels=None, p=None, cont=False, grow=0.0, hold=0.0):
    return dict(scene=scene, dur=float(dur), text=text.strip(), at=at, labels=labels or [], p=p or {},
                cont=cont, grow=grow, hold=hold)

def C(film, start, dur, title, sub, grow=0.0, text="", at=1.0, label_at=0.6):
    return B("clip", dur, text, at, [(title, sub, label_at)], dict(film=film, start=start), grow=grow)

R = " · recreated in code"

ACTS = {
    "open":   dict(title=None, look="clean", font="inter"),
    "tricks": dict(title=("I", "TRICKS", "1901 – 1908"), look="clean", font="serif"),
    "vmusic": dict(title=("II", "VISUAL MUSIC", "1921 – 1930"), look="clean", font="serif"),
    "dreams": dict(title=("III", "DREAMS", "1923 – 1929"), look="clean", font="serif"),
    "light":  dict(title=("IV", "LIGHT", "1952 – 1968"), look="film_color", font="inter"),
    "signal": dict(title=("V", "SIGNAL", "1963 – 1974"), look="crt", font="mono"),
    "cut":    dict(title=("VI", "CUT", "1968 – 2002"), look="clean", font="black"),
    "cyber":  dict(title=("VII", "CYBERDELIC", "1984 – 2001"), look="clean", font="pixel"),
    "noise":  dict(title=("VIII", "NOISE", "2005 – now"), look="glitch", font="mono"),
    "see1":   dict(title=None, look="clean", font="inter"),
    "see2":   dict(title=None, look="clean", font="inter"),
    "see3":   dict(title=None, look="clean", font="inter"),
    "see4":   dict(title=None, look="clean", font="serif"),
    "see5":   dict(title=None, look="clean", font="serif"),
    "see6":   dict(title=None, look="clean", font="serif"),
    "epi":    dict(title=None, look="clean", font="inter"),
}

FILMS = {k: f"{FX_ROOT}/arch/raw/{v}" for k, v in dict(
    rubber="rubber.mp4", melomane="melomane.mp4", moon="moon.mp4", hotel="hotel.mp4", cohl="cohl.mp4",
    opus1="opus1.mp4", opus3="opus3.mp4", opus4="opus4.mp4", rhythmus="rhythmus.mkv", eggeling="eggeling.mp4",
    anemic="anemic.mp4", study6="study6.mp4", tusalava="tusalava.mp4", retour="retour.mp4", ballet="ballet.mp4",
    entracte="entracte.mp4", emak="emak.mp4", ghosts="ghosts.mp4", seashell="seashell.mp4", usher="usher.mp4",
    vertov="vertov.mp4", chien="chien2.mp4").items()}

SCRIPT = [
  ("open", [
    B("feedback", 22, "Point a camera at its own screen, and the machine starts looking at itself. "
      "What comes back is the closest thing a machine has to a dream.", at=6.0, p=dict(mode="tunnel", spin=0.4)),
    B("feedback", 18, cont=True, p=dict(mode="mandala", spin=2.0), grow=1.0),
    B("montage", 10.2, p=dict(items=["clip:anemic:40", "clip:moon:436", "harmonograph", "clip:opus1:30",
                                    "liquid", "clip:ballet:210", "psychedelia", "flame"], step=1.275)),
    B("title", 8.0),
  ]),
  ("see1", [
    B("eyeevo", 10, "Before cinema, before art, there was the eye. "
      "It began as almost nothing: a patch of light-sensitive cells that could tell day from night. "
      "Fold that patch into a cup, and it can tell where the light is coming from. "
      "Narrow the cup into a pinhole, and an image appears. "
      "Fill it with a lens, and the image sharpens. "
      "In 1994, the biologists Dan-Eric Nilsson and Susanne Pelger estimated that this could happen in fewer than four hundred thousand generations. "
      "In the history of life, that's a blink.", at=1.0, hold=1.2,
      labels=[("On seeing 1 · The first eye", "science", 0.3)]),
  ]),
  ("tricks", [
    B("actcard", 4.0),
    C("rubber", 72, 18, "The Man with the Rubber Head", "Georges Méliès, 1901",
      text="Before anyone said psychedelic, cinema's first magicians were already bending reality.", at=1.0, label_at=6.5),
    C("melomane", 30, 20, "The Melomaniac", "Georges Méliès, 1903"),
    C("moon", 421.5, 20, "A Trip to the Moon", "Georges Méliès, 1902"),
    C("hotel", 204, 16, "The Electric Hotel", "Segundo de Chomón, 1908"),
    C("hotel", 322, 12, "The Electric Hotel", "Segundo de Chomón, 1908", label_at=99),
    C("cohl", 7, 30, "Fantasmagorie", "Émile Cohl, 1908"),
  ]),
  ("see2", [
    B("fisheye", 10, "Your eyes are fish eyes. "
      "Around five hundred million years ago, early jawless fish already had camera eyes, with a lens, a retina, and muscles to aim them. "
      "We inherited the design, flaws included. "
      "Our retina is wired backwards: its nerves run in front of the light-sensitive cells, and where they leave the eye there's a hole, the blind spot. "
      "Fish, reptiles and birds have four kinds of color cells. "
      "Our mammal ancestors, living at night in the age of the dinosaurs, lost two. "
      "Our primate ancestors won one back. "
      "That's why you see the colors you see.", at=1.0, hold=1.2,
      labels=[("On seeing 2 · A fish's eye", "science", 0.3)]),
  ]),
  ("vmusic", [
    B("actcard", 4.0),
    C("opus1", 30, 30, "Lichtspiel Opus I", "Walter Ruttmann, 1921",
      text="Then painters picked up the camera, and film became music for the eyes.", at=1.0, label_at=6.0),
    C("rhythmus", 22, 18, "Rhythmus 21", "Hans Richter, 1921"),
    C("eggeling", 240, 24, "Symphonie Diagonale", "Viking Eggeling, 1924"),
    C("opus3", 38, 20, "Lichtspiel Opus III", "Walter Ruttmann, 1924"),
    C("opus4", 126, 22, "Lichtspiel Opus IV", "Walter Ruttmann, 1925"),
    C("anemic", 27, 30, "Anémic Cinéma", "Marcel Duchamp, 1926"),
    C("study6", 13.5, 26, "Study No. 6", "Oskar Fischinger, 1930"),
    C("tusalava", 286, 22, "Tusalava", "Len Lye, 1929"),
  ]),
  ("see3", [
    B("perceive", 10, "And the picture you see isn't what your eyes record. "
      "Your eyes jump about three times a second, and your brain hides the jumps. "
      "It also paints over your blind spot. "
      "Try it: close your left eye, stare at the cross, and lean toward the screen until the dot disappears.", at=1.0, hold=5.0,
      labels=[("On seeing 3 · The brain builds the picture", "science", 0.3)]),
    B("perceive", 10, "And it turns separate pictures into motion. "
      "Show it a series of still photographs, like Eadweard Muybridge's galloping horse from 1878, and it invents movement. "
      "Every film in this story depends on that trick.", at=0.5, hold=2.0, cont=True,
      labels=[("The Horse in Motion", "Eadweard Muybridge, 1878", 4.0)]),
  ]),
  ("dreams", [
    B("actcard", 4.0),
    C("retour", 116, 18, "Le Retour à la raison", "Man Ray, 1923", text="And the surrealists filmed their dreams.", at=1.0, label_at=4.0),
    B("clip", 26, labels=[("Ballet Mécanique", "Fernand Léger & Dudley Murphy, 1924", 0.6)], p=dict(film="ballet", start=209.5, ranges=[[209.5, 12.0], [330.0, 14.1]])),
    C("ballet", 388, 10, "Ballet Mécanique", "Fernand Léger & Dudley Murphy, 1924", label_at=99),
    C("entracte", 168, 14, "Entr'acte", "René Clair, 1924"),
    C("emak", 929, 15, "Emak-Bakia", "Man Ray, 1926"),
    C("ghosts", 171, 14, "Ghosts Before Breakfast", "Hans Richter, 1928"),
    C("seashell", 760, 14, "The Seashell and the Clergyman", "Germaine Dulac, 1928"),
    C("usher", 674, 17, "The Fall of the House of Usher", "James Sibley Watson & Melville Webber, 1928"),
    C("vertov", 3905, 16, "Man with a Movie Camera", "Dziga Vertov, 1929"),
    B("clip", 15.3, labels=[("Man with a Movie Camera", "Dziga Vertov, 1929", 99)], p=dict(film="vertov", start=3921, ranges=[[3921, 7.8], [3990.5, 7.5]])),
    C("chien", 63, 31.3, "Un Chien Andalou", "Luis Buñuel & Salvador Dalí, 1929"),
    B("black", 1.2),
    C("chien", 246.5, 16.5, "Un Chien Andalou", "Luis Buñuel & Salvador Dalí, 1929", label_at=99),
  ]),
  ("see4", [
    B("cave", 10, "Philosophers were worried about seeing long before cinema. "
      "Around 375 BC, Plato imagined prisoners chained in a cave, facing a wall. "
      "Behind them burns a fire, and people carry objects past it, so the prisoners see only shadows. "
      "They take the shadows for the world. "
      "It's the oldest description of a movie theater, and a warning: what you see may be a projection.", at=1.0, hold=1.5,
      labels=[("On seeing 4 · The cave", "philosophy · Plato, Republic, c. 375 BC", 0.3)]),
  ]),
  ("light", [
    B("actcard", 4.0),
    B("osc", 24, labels=[("Abstronic", "Mary Ellen Bute, 1952 · drawing with an oscilloscope" + R, 0.5)], grow=1.0),
    B("dome", 24, "Then came the light show. Images, performed live.", at=1.0,
      labels=[("Vortex Concerts", "Jordan Belson & Henry Jacobs, 1957–59" + R, 4.5)], p=dict(phase="vortex"), grow=1.0),
    B("whitney", 20, labels=[("Catalog", "John Whitney, 1961" + R, 0.5)], grow=1.0),
    B("liquid", 28, labels=[("Liquid light shows", "San Francisco, 1966" + R, 0.5)], grow=1.0),
    B("slitscan", 18, labels=[("2001: A Space Odyssey", "slit-scan by Douglas Trumbull, 1968" + R, 0.5)], grow=1.0),
  ]),
  ("see5", [
    B("doors", 10, "Around 1790, the poet William Blake wrote that if the doors of perception were cleansed, everything would appear as it is: infinite. "
      "In 1953, the writer Aldous Huxley took mescaline with the psychiatrist Humphry Osmond, and borrowed Blake's phrase for a book: The Doors of Perception. "
      "A few years later, Osmond proposed a new word for drugs that seemed to reveal the mind. "
      "Psychedelic. "
      "From the Greek: mind-manifesting.", at=1.0, hold=2.5,
      labels=[("On seeing 5 · The doors of perception", "philosophy", 0.3)]),
  ]),
  ("signal", [
    B("actcard", 4.0),
    B("tvwall", 13, "Then the television became an instrument.", at=1.0,
      labels=[("Exposition of Music – Electronic Television", "Nam June Paik, 1963" + R, 4.5)]),
    B("magnet", 18, labels=[("Magnet TV", "Nam June Paik, 1965" + R, 0.5)], grow=1.0),
    B("feedback", 14, labels=[("Video feedback", "the portable video era, late 1960s", 0.5)], p=dict(mode="crt", spin=0.5)),
    B("colorizer", 18, labels=[("Paik–Abe Video Synthesizer", "WGBH Boston, 1970" + R, 0.5)], grow=1.0),
    B("beck", 16, labels=[("Direct Video Synthesizer", "Stephen Beck, c. 1970" + R, 0.5)], grow=1.0),
    B("ruttetra", 20, labels=[("Violin Power", "Steina Vasulka, 1970–78" + R, 0.5)], grow=1.0),
    B("buddha", 14, labels=[("TV Buddha", "Nam June Paik, 1974" + R, 0.5)]),
  ]),
  ("cut", [
    B("actcard", 4.0),
    B("pasdedeux", 22, "Then the edit became a magic trick.", at=1.0,
      labels=[("Pas de deux", "Norman McLaren, 1968 · multiple exposures on an optical printer" + R, 4.5)]),
    B("tango", 38, labels=[("Tango", "Zbigniew Rybczyński, 1980" + R, 0.5)], p=dict(start=1, end=36), grow=1.0),
    B("faces", 18, labels=[("Cry", "Godley & Creme, 1985" + R, 0.5)]),
    B("train", 18, labels=[("Star Guitar", "Michel Gondry, 2002" + R, 0.5)], grow=1.0),
    B("loopwalk", 20, labels=[("Come Into My World", "Michel Gondry, 2002" + R, 0.5)], grow=1.0),
  ]),
  ("cyber", [
    B("actcard", 4.0),
    B("psychedelia", 22, "Then the dream machine moved into the home computer.", at=1.0,
      labels=[("Psychedelia", "Jeff Minter, 1984" + R, 4.5)], grow=1.0),
    B("wiregrid", 16, labels=[("The Mind's Eye", "computer animation on VHS, 1990" + R, 0.5)]),
    B("mandel", 12, labels=[("Fractals", "infinite detail from one equation", 0.5)], grow=1.0),
    B("mandel", 12, cont=True, labels=[("How to Operate Your Brain", "Timothy Leary, early 1990s" + R, 0.5)], p=dict(vhs=True)),
    B("tunnel", 16, labels=[("VJ culture", "1990s clubs, visuals mixed live", 0.5)], grow=1.0),
    B("feedback", 22, labels=[("MilkDrop", "Ryan Geiss, 2001" + R, 0.5)], p=dict(mode="milkdrop", spin=1.2), grow=1.0),
    B("flame", 24, labels=[("Electric Sheep", "Scott Draves, 1999 · fractal flames", 0.5)], grow=1.5),
  ]),
  ("see6", [
    B("homunculus", 10, "In 1637, René Descartes described cutting away the back of an ox's eye, and seeing the world projected on it, small and upside down. "
      "But that raised a puzzle. "
      "If the eye makes a picture, who looks at the picture? "
      "A little person inside the head? "
      "Then who looks inside that little person's head? "
      "Philosophers call it an infinite regress, and it looks a lot like video feedback. "
      "Today, many neuroscientists say the brain doesn't watch a picture at all: it predicts one, and checks its guess against the light. "
      "Perception, in their phrase, is a controlled hallucination. "
      "Which brings us to the machines.", at=1.0, hold=1.5,
      labels=[("On seeing 6 · Who is watching?", "philosophy · René Descartes, La Dioptrique, 1637", 0.3)]),
  ]),
  ("noise", [
    B("actcard", 4.0),
    B("mosh", 26, labels=[("Datamosh", "after Takeshi Murata, 2005 · made by breaking this film's own file", 0.5)]),
    B("dream", 26, "Now the machines dream on their own.", at=1.5,
      labels=[("DeepDream", "Alexander Mordvintsev, 2015 · run on this film's own feedback", 5.0)]),
    B("montage", 31, "The artist's job is to stay in the loop.", at=23.0,
      p=dict(items=["clip:anemic:120", "clip:rubber:80", "clip:opus4:140", "magnet", "clip:ballet:390", "tango",
                    "psychedelia", "mosh_still", "clip:tusalava:300", "flame"], step=3.1)),
    B("feedback", 13, p=dict(mode="mandala", spin=1.0)),
  ]),
  ("epi", [
    B("recipe", 16, "Point your phone's camera at a screen showing its own picture. You're part of the loop.", at=2.5,
      p=dict(text="Try it: point your phone's camera\nat a screen showing its own picture.")),
    B("crtoff", 4.0),
    B("black", 4.0),
    B("credits", 22.0),
  ]),
]

CREDITS = [
    ("FEEDBACK", "title"),
    ("a short history of psychedelic and surreal video", "sub"),
    ("", "gap"),
    ("Archival films (all public domain in the US, published before 1931)", "head"),
    ("The Man with the Rubber Head · The Melomaniac · A Trip to the Moon · Georges Méliès", "body"),
    ("The Electric Hotel · Segundo de Chomón · Fantasmagorie · Émile Cohl", "body"),
    ("Lichtspiel Opus I, III, IV · Walter Ruttmann · Rhythmus 21, Ghosts Before Breakfast · Hans Richter", "body"),
    ("Symphonie Diagonale · Viking Eggeling · Anémic Cinéma · Marcel Duchamp", "body"),
    ("Study No. 6 · Oskar Fischinger · Tusalava · Len Lye", "body"),
    ("Le Retour à la raison, Emak-Bakia · Man Ray · Ballet Mécanique · Fernand Léger & Dudley Murphy", "body"),
    ("Entr'acte · René Clair · The Seashell and the Clergyman · Germaine Dulac", "body"),
    ("The Fall of the House of Usher · Watson & Webber · Man with a Movie Camera · Dziga Vertov", "body"),
    ("Un Chien Andalou · Luis Buñuel & Salvador Dalí", "body"),
    ("Sources: Internet Archive (archive.org)", "body"),
    ("", "gap"),
    ("Recreated in code (go watch the originals)", "head"),
    ("Mary Ellen Bute · Jordan Belson · John Whitney · Nam June Paik · Stephen Beck", "body"),
    ("Steina & Woody Vasulka · Norman McLaren · Zbigniew Rybczyński · Godley & Creme · Michel Gondry", "body"),
    ("Jeff Minter · Timothy Leary · Ryan Geiss · Scott Draves · Takeshi Murata", "body"),
    ("", "gap"),
    ("Narration: synthetic voice (Kokoro) · Score: generated in code", "body"),
    ("Visuals: Python, NumPy, FFmpeg, PyTorch", "body"),
    ("Written and produced with Claude", "body"),
]


def _apply_slots():
    """Swap a recreation for a real clip: $FX_ROOT/slots.json maps a label title to {"file", "start"}."""
    import json, os
    path = os.path.join(FX_ROOT, "slots.json")
    if not os.path.exists(path):
        return
    slots = json.load(open(path))
    for act, bl in SCRIPT:
        for b in bl:
            for i, (title, sub, at) in enumerate(b["labels"]):
                s = slots.get(title)
                if s and s.get("file"):
                    b["scene"] = "clip"
                    b["p"] = dict(film="__path__", path=s["file"], start=float(s.get("start", 0)))
                    b["cont"] = False
                    b["labels"][i] = (title, sub.replace(R, ""), at)

_apply_slots()
