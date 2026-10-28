#!/usr/bin/env python3
"""Round 7 screams: one real man per event, minimal processing. Replaces scream_pack.py's layered stacks.

    QF_DL=<dir> QF_TMP=<dir> /opt/anaconda3/bin/python3 -I tools/music/scream_pack2.py fetch|build|preview [event ...]

The owner (r7): "It sounds digitized and not like a real person's scream." Round 6 stacked 8 game grunts, saturated and
bit-crushed them, and encoded at 32 kHz / 86 kbps. Here:
  * ONE recorded voice per file (a real performance of 1 to 5 s from Freesound, CC0 only; licence checked on each
    sound page by `fetch`), plus at most one quiet gore-foley layer (a recorded OpenGameArt CC0 wet hit, or bubbles);
  * processing = trim, fade, 70 Hz high-pass, +2 dB presence, a pitch shift within 1 semitone (rubberband, formant
    preserved), short room reverb, peak at -1 dBFS. No time-stretch, no saturation, no bit-crush;
  * encode 48 kHz, 160 kbps AAC.
Events: qf.scare.death_scream (8), scream (3), scream_far (2), underwater (3), jumpscreech (2).
`fetch` downloads each Freesound preview (hq mp3) into its own $QF_DL/fs<ID>/ directory; the downloads are untrusted data.
The foley comes from scream_pack.py's OpenGameArt downloads ($QF_DL/<key>/, run its `fetch` first).
"""
import os, sys, json, re, subprocess, html
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SFX = os.path.join(ROOT, "site", "lib", "sfx")
TMP = os.environ.get("QF_TMP", "/tmp/qf_scream2")
DL = os.environ.get("QF_DL", os.path.join(TMP, "dl"))
os.makedirs(TMP, exist_ok=True)
SR = 48000
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"

# Freesound id -> (author, title); every one is CC0 1.0 (checked on the page by fetch)
FS = {
    "575674": ("ericnorcross81", "Startled, Tortured, and Terrified (Man)"),
    "752055": ("BlockFrog", "Man Screams His Death Into The Void"),
    "542128": ("gtrempe", "Male increasing scream - horror yelling in pain"),
    "724173": ("Piement_infernal", "Pain man scream"),
    "530471": ("martian", "male scream pain torture"),
    "325548": ("Archeos", "Man screaming"),
    "381784": ("fattirewhitey", "Guttural Screams"),
    "556976": ("marc3122", "Male Screams [1]"),
    "690702": ("Capt_Bligh1", "Man Screams"),
    "760720": ("ronse", "screamimg pain"),
    "221544": ("joseppujol", "Wounded man scream"),
    "661477": ("B... (see page)", "manscreamingintowarmwaterfilledpot"),
    "767590": ("Wick... (see page)", "young man screaming, pillow on face"),
}

# name -> (freesound id, start s, end s); times are in the 128 kbps HQ preview
SEG = {
    "terrified": ("575674", 13.2, 16.7), "void": ("752055", 0.8, 4.7), "inc1": ("542128", 2.5, 5.9),
    "inc2": ("542128", 14.5, 17.6), "pain1": ("724173", 6.5, 8.3), "torture": ("530471", 21.3, 24.4),
    "man325": ("325548", 19.1, 21.9), "guttural": ("381784", 0.0, 3.4),
    "s556": ("556976", 0.5, 3.0), "s690": ("690702", 24.3, 27.1), "s760": ("760720", 3.8, 6.7),
    "s690b": ("690702", 2.8, 4.8), "s760b": ("760720", 6.8, 10.2),
    "j724": ("724173", 3.5, 5.0), "j221": ("221544", 0.3, 1.8),
    "pot1": ("661477", 12.5, 15.2), "pot2": ("661477", 23.0, 25.9), "pillow": ("767590", 6.3, 9.6),
}

# ---------------------------------------------------------------- fetch
def curl(u):
    return subprocess.run(["curl", "-sL", "-m", "90", "-A", "Mozilla/5.0", u], capture_output=True, check=True).stdout

def fetch():
    meta = {}
    for sid in FS:
        d = os.path.join(DL, "fs" + sid)
        if os.path.exists(os.path.join(d, "p.mp3")): print("have", sid); continue
        os.makedirs(d, exist_ok=True)
        # the page URL needs the author slug: search result pages carry it; the sound page redirect does not
        page = curl(f"https://freesound.org/s/{sid}/").decode("utf8", "replace")
        if CC0_URL.split("//")[1] not in page: raise SystemExit(f"{sid}: no CC0 licence link on the page, refusing")
        m = re.search(r'https://cdn.freesound.org/previews/[^"]*-hq.mp3', page)
        open(os.path.join(d, "p.mp3"), "wb").write(curl(m.group(0)))
        print("fetched", sid)

# ---------------------------------------------------------------- dsp
def decode(path, rate=SR):
    out = os.path.join(TMP, "dec_%d.wav" % (abs(hash(path)) % 10 ** 9))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-ac", "1", "-ar", str(rate), out], check=True)
    sr, y = wavfile.read(out); os.remove(out)
    return y.astype(np.float64) / 32768.0

_C = {}
def voice(name, pad_in=0.08, pad_out=0.25):
    sid, a, b = SEG[name]
    if sid not in _C: _C[sid] = decode(os.path.join(DL, "fs" + sid, "p.mp3"))
    y = _C[sid]
    a = max(0, int((a - pad_in) * SR)); b = min(len(y), int((b + pad_out) * SR))
    return y[a:b].copy()

def hp(y, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), y)
def lp(y, f, o=2): return sosfilt(butter(o, min(f, SR / 2 * .95), "low", fs=SR, output="sos"), y)
def bp(y, f0, f1, o=2): return sosfilt(butter(o, [f0, min(f1, SR / 2 * .95)], "band", fs=SR, output="sos"), y)

def peq(y, f, q, gain_db):
    band = bp(y, f / (1 + 1 / q), f * (1 + 1 / q))
    return y + band * (10 ** (gain_db / 20) - 1)

def fade(y, a=0.004, r=0.2):
    y = y.copy(); A, R = int(a * SR), min(int(r * SR), len(y))
    if A: y[:A] *= np.linspace(0, 1, A)
    if R: y[-R:] *= np.cos(np.linspace(0, np.pi / 2, R)) ** 2
    return y

def pitch(y, semis):
    if abs(semis) < 1e-3: return y
    pi, po = os.path.join(TMP, "rb_in.wav"), os.path.join(TMP, "rb_out.wav")
    wavfile.write(pi, SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    flt = f"rubberband=pitch={2 ** (semis / 12):.5f}:formant=preserved:transients=smooth"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", pi, "-af", flt, po], check=True)
    sr, o = wavfile.read(po); return o.astype(np.float64) / 32768.0

def room(y, decay=0.45, wet=0.12, tone=5500, pre=0.006, seed=7):
    rg = np.random.default_rng(seed)
    n = int(decay * SR)
    ir = rg.standard_normal(n) * np.exp(-np.arange(n) / (decay * SR / 6.5))
    ir = lp(ir, tone); ir[:int(pre * SR)] = 0; ir /= np.abs(ir).sum() ** .5
    y = np.concatenate([y, np.zeros(int(decay * SR * .8))])
    w = fftconvolve(y, ir)[:len(y)]
    return (1 - wet) * y + wet * w / (np.max(np.abs(w)) + 1e-9) * np.max(np.abs(y))

def at(dest, src, sec, g=1.0):
    i = int(sec * SR)
    if i >= len(dest): return
    n = min(len(src), len(dest) - i); dest[i:i + n] += src[:n] * g

def peak(y, db=-1.0): return y / (np.max(np.abs(y)) + 1e-9) * 10 ** (db / 20)

def clean(y, semis=0.0, rv=(0.45, 0.12)):
    """The whole 'processing' of a voice: high-pass, presence, +-1 semitone, a short room."""
    y = hp(y, 70)
    y = peq(y, 3000, 1.0, 2.0)
    y = pitch(y, semis)
    y = room(y, *rv)
    return y

def foley(key, rel, a=0.0, b=None):
    y = decode(os.path.join(os.environ.get("QF_FOLEY", DL), key, rel))
    b = len(y) / SR if b is None else b
    return fade(y[int(a * SR):int(b * SR)], .003, .03)

# ---------------------------------------------------------------- events
DEATH = [  # (segment, semitones, gore foley slimy index or None)
    ("terrified", 0.0, None), ("void", -0.6, 1), ("inc1", 0.5, None), ("inc2", -0.5, 3),
    ("pain1", 0.0, None), ("torture", -0.4, 5), ("man325", 0.4, None), ("guttural", -0.7, None),
]

def death(i):
    seg, sm, g = DEATH[i]
    v = clean(voice(seg), sm)
    v = fade(v, .004, .35)
    out = np.zeros(len(v) + int(.4 * SR))
    at(out, v, 0)
    if g is not None:   # one quiet wet hit under the tail, from a recorded wet-impact file
        f = lp(hp(foley("slimy", f"s{g}.mp3"), 60), 3500)
        at(out, peak(f, -1) , max(.2, len(v) / SR - .9), 10 ** (-17 / 20) * np.max(np.abs(v)))
    return peak(out)

SC = [("s556", .3), ("s690", -.5), ("s760", .6)]
def scream(i):
    seg, sm = SC[i]
    return peak(fade(clean(voice(seg), sm, (.4, .10)), .004, .3))

def scream_far(i):
    seg, sm = [("s690b", -.5), ("s760b", .4)][i]
    v = clean(voice(seg), sm, (.3, .06))
    v = lp(v, 3200)                                   # air takes the highs
    v = hp(v, 140)
    out = np.zeros(len(v) + int(2.6 * SR))
    at(out, v, .22, .55)                              # pre-delay: distance
    for d, g in [(.55, .38), (1.1, .26), (1.75, .16)]:   # echoes of the canyon / cave
        at(out, lp(v, 2200), .22 + d, .55 * g)
    out = room(out, 1.8, .38, 3000, .02, seed=11)
    return peak(fade(out, .02, .8), -2.5)

def bubbles(n, dur, seed):
    rg = np.random.default_rng(seed)
    b = np.zeros(int(dur * SR))
    for k in range(n):
        f = foley("bubbles", rg.choice(["b1.wav", "b2.wav"]))
        f = f * rg.uniform(.5, 1.2)
        at(b, f, rg.uniform(0, dur - .3), np.exp(-k * .01))
    return b

def underwater(i):
    seg, sm, fc0, fc1 = [("pot1", -.5, 1500, 600), ("pillow", .5, 1100, 450), ("void", -.8, 1200, 500)][i]
    v = voice(seg); v = hp(v, 60); v = pitch(v, sm)
    n = len(v) + int(1.0 * SR)
    y = np.zeros(n); at(y, v, .05)
    out = np.zeros(n); blk = 2048           # one low-pass whose cutoff closes over the scream
    for k in range(0, n - blk, blk):
        fc = fc0 * (fc1 / fc0) ** (k / n)
        lo = max(0, k - blk); s = lp(y[lo:k + blk], fc, 3)
        out[k:k + blk] = s[k - lo:k - lo + blk]
    bub = bubbles(22, n / SR, 40 + i)
    res = out + 0.22 * lp(bub, 3000) * np.max(np.abs(out)) / (np.max(np.abs(bub)) + 1e-9) * 2.2
    res = room(res, .8, .22, 2200, .01, seed=20 + i)
    return peak(fade(res, .004, .5), -1)

def jump(i):
    seg, sm = [("j724", .4), ("j221", -.3)][i]
    v = voice(seg, .015, .2)
    v = clean(v, sm, (.3, .08))
    v = fade(v, .001, .25)
    n = len(v)
    out = np.zeros(n + int(.2 * SR)); at(out, v, 0)
    # a short sharp hit under the first 80 ms: a recorded wet impact, low-passed, nothing synthesised on top
    h = lp(foley("slimy", "s%d.mp3" % (4 + i)), 1800)[:int(.18 * SR)]
    h = fade(h, .001, .08)
    at(out, h, 0, .9 * np.max(np.abs(v)) / (np.max(np.abs(h)) + 1e-9))
    return peak(out, -1)

DEFS = [
    ("qf.scare.death_scream", lambda: [death(i) for i in range(8)], {"pitch": [.97, 1.03]}),
    ("qf.scare.scream", lambda: [scream(i) for i in range(3)], {"pitch": [.97, 1.03]}),
    ("qf.scare.scream_far", lambda: [scream_far(i) for i in range(2)], {"volume": .9, "pitch": [.97, 1.03]}),
    ("qf.scare.underwater", lambda: [underwater(i) for i in range(3)], {"volume": .9}),
    ("qf.scare.jumpscreech", lambda: [jump(i) for i in range(2)], {"pitch": [.98, 1.02]}),
]

def encode(y, path, br="160k"):
    wav = os.path.join(TMP, "enc.wav")
    wavfile.write(wav, SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "48000", "-c:a", "aac",
                    "-b:a", br, "-movflags", "+faststart", path], check=True)

def decoded_peak(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-"], capture_output=True).stdout
    return 20 * np.log10(np.max(np.abs(np.frombuffer(raw, np.float32))) + 1e-9)

def trim_tail(y, db=-48, keep=.12):
    idx = np.nonzero(np.abs(y) > 10 ** (db / 20) * np.max(np.abs(y)))[0]
    n = min(len(y), int(idx[-1] + keep * SR)) if len(idx) else len(y)
    return fade(y[:n], 0, .1)

def save(name, ys, volume=1.0, pitch=1, bus="sfx"):
    files = []
    old = json.load(open(os.path.join(SFX, "manifest.json")))["events"].get(name, {"files": []})["files"]
    for i, y in enumerate(ys):
        y = trim_tail(y)
        rel = "qf/" + name[3:].replace(".", "_") + f"{i + 1}.m4a"
        path = os.path.join(SFX, rel)
        for _ in range(5):
            encode(y, path)
            pk = decoded_peak(path)
            if -1.5 < pk < -0.5: break
            y = y * 10 ** ((-1.0 - pk) / 20)
        files.append(rel)
    for f in old:   # variants of an earlier build that this one no longer has
        if f not in files and os.path.exists(os.path.join(SFX, f)): os.remove(os.path.join(SFX, f))
    mp = os.path.join(SFX, "manifest.json"); m = json.load(open(mp))
    m["events"][name] = {"files": files, "volume": volume, "pitch": pitch, "bus": bus}
    json.dump({"events": dict(sorted(m["events"].items()))}, open(mp, "w"), indent=1)

# ---------------------------------------------------------------- sources.json / README
USES = {
    "qf.scare.death_scream": ["575674", "752055", "542128", "724173", "530471", "325548", "381784"],
    "qf.scare.scream": ["556976", "690702", "760720"],
    "qf.scare.scream_far": ["690702", "760720"],
    "qf.scare.underwater": ["661477", "767590", "752055"],
    "qf.scare.jumpscreech": ["724173", "221544"],
}

def merge_sources():
    """Add the Freesound sources to sources.json and README.md (scream_pack.py rewrites the OGA part first)."""
    sp = os.path.join(SFX, "sources.json"); s = json.load(open(sp))
    s["sources"] = [x for x in s["sources"] if not x["id"].startswith("fs")]
    meta = json.load(open(os.path.join(HERE, "scream_pack2_meta.json")))
    for sid in FS:
        m = meta[sid]
        s["sources"].append({"id": "fs" + sid, "title": m["title"], "url": m["url"], "author": m["author"],
                             "licence": "CC0 1.0", "files": [f"{sid} (HQ preview mp3)"], "used_for": "the recorded voice (one per file)"})
    for ev, ids in USES.items(): s["events"][ev] = ["fs" + i for i in ids] + (["slimy"] if ev in ("qf.scare.death_scream", "qf.scare.jumpscreech") else []) + (["bubbles"] if ev == "qf.scare.underwater" else [])
    s["note"] = ("Round 7: the screams (qf.scare.death_scream, scream, scream_far, underwater, jumpscreech) are single real "
                 "recordings of a man screaming, CC0 1.0 from Freesound.org (licence link checked on each sound page), with at "
                 "most one quiet CC0 foley layer from OpenGameArt. The other pack sources are CC0 1.0 from OpenGameArt.org. "
                 "Nothing is NC, nothing is from a game. Synthesised layers are our own. qf.mood.far_* are the bank's Mojang "
                 "mob sounds reprocessed: flagged \"mojang\": true in manifest.json and dropped by build_sfx.py --own-only.")
    json.dump(s, open(sp, "w"), indent=1)
    rp = os.path.join(SFX, "README.md"); t = open(rp).read()
    t = t.split("\n## Freesound")[0].rstrip("\n") + "\n"
    t += "\n## Freesound recordings (round 7 screams; all CC0 1.0, one real voice per file)\n\n| Sound | Author | Licence | Events |\n|---|---|---|---|\n"
    for sid in FS:
        m = meta[sid]; ev = ", ".join(e.split(".")[-1] for e, ids in USES.items() if sid in ids)
        t += f"| [{m['title']}]({m['url']}) | {m['author']} | CC0 1.0 | {ev} |\n"
    t += "\nBuilt by `tools/music/scream_pack2.py` (trim, high-pass, presence, a pitch shift within one semitone, a short room, 48 kHz 160 kbps AAC).\n"
    open(rp, "w").write(t)

def write_meta():
    """url/author/title for each used id, from the sound page (licence link re-checked; the page title carries the author)."""
    meta = {}
    for sid in FS:
        page = curl(f"https://freesound.org/s/{sid}/").decode("utf8", "replace")
        if "creativecommons.org/publicdomain/zero/1.0" not in page: raise SystemExit(sid + ": not CC0")
        t = re.search(r"<title>(.*?)</title>", page, re.S)
        title = html.unescape(t.group(1).strip()) if t else FS[sid][1]
        m = re.match(r"Freesound - (.*) by ([^ ]+)$", title)
        name, author = (m.group(1), m.group(2)) if m else (FS[sid][1], FS[sid][0])
        link = re.search(r'href="(/people/[^"/]+/sounds/%s/)"' % sid, page)
        url = "https://freesound.org" + link.group(1) if link else f"https://freesound.org/s/{sid}/"
        meta[sid] = {"url": url, "author": author, "title": name}
    json.dump(meta, open(os.path.join(HERE, "scream_pack2_meta.json"), "w"), indent=1)

def main():
    a = sys.argv[1:]
    if os.environ.get("QF_R7") != "1":   # round 8: the five events, sources.json and README come from scream_pack3.py
        raise SystemExit("superseded by tools/music/scream_pack3.py (round 8); set QF_R7=1 to run the round-7 build anyway")
    if a and a[0] == "fetch": fetch(); write_meta(); return
    if a and a[0] == "build": a = a[1:]
    for name, fn, kw in DEFS:
        if a and not any(x in (name, name.split(".", 2)[-1]) for x in a): continue
        save(name, fn(), **kw); print("built", name, flush=True)
    merge_sources()

if __name__ == "__main__":
    main()
