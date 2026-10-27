#!/usr/bin/env python3
"""Recorded-voice horror sounds for the site (qf.scare.* screams, qf.mood.*), round 6.

    QF_DL=<dir>  QF_TMP=<dir>  /opt/anaconda3/bin/python3 -I tools/music/scream_pack.py fetch
    QF_DL=<dir>  QF_TMP=<dir>  /opt/anaconda3/bin/python3 -I tools/music/scream_pack.py [build] [event ...]

The owner's bar: "a man dying, screaming for his life. Like the MK9 audio. Grotesque and harrowing."
Synthesised screams were judged terrible, so every voice here is a real recording, all CC0 from
OpenGameArt (list in SOURCES; written to site/lib/sfx/sources.json and the README). The script:

  fetch   downloads each source into its own directory under $QF_DL/<key>/ (untrusted data: run with -I)
  build   decodes, then layers and processes:
            a recorded scream (pitch / time / formant with rubberband, tape-slow bends at the death)
          + an octave-down double (the "bigger than a man" body) + a crunch/saturation layer
          + gore foley (wet tears, meat, bone crunch) and a low boom
          + room / cave reverb, and for the cut-offs a gurgle (retch + bubbles, low-passed).

Events: qf.scare.death_scream (6), jumpscreech (4), underwater (3), static (loop), scream (3),
scream_far (2), shriek (3); qf.mood.far_groan / far_rattle / far_vwoop / far_cry / far_hiss (2 each, derived
from the game-sound bank: flagged "mojang" so build_sfx.py --own-only drops them), scamper (4), scrape (2),
breath_near (2).
"""
import os, sys, json, subprocess, shutil, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QF_TMP", "/tmp/qf_scream")
import site_cues as C
import scare_sounds as SS
from site_cues import (np, SR, t, lowpass, highpass, bandpass, noise, ex, sine, glide, slow, fit, at, fade,
                       register, ROOT, SFX, TMP)
from synth import reverb as _reverb
from scipy.io import wavfile
from scipy.signal import fftconvolve, lfilter

DL = os.environ.get("QF_DL", os.path.join(TMP, "dl"))
OGA = "https://opengameart.org/sites/default/files/"
CC0 = "CC0 1.0"

# key: (page slug, author, [(file url name, local name)], used for)
SOURCES = {
    "deathpain":  ("grunts-male-death-and-pain", "thebardofblasphemy", [("death%20pain%20grunts.wav", "grunts.wav")], "main male death/pain screams"),
    "male15":     ("15-vocal-male-strainhurtpainjump-sounds", "qubodup", [("sls.mp3", "sls.mp3")], "male strain/pain bursts"),
    "maledead":   ("male-dead-voice", "mieki256", [("enemy_dead_20150802.zip", "d.zip")], "short male death cries"),
    "manhurt":    ("man-hurt-sounds", "Aharabada", [("ManHurt.ogg", "m.ogg")], "deep male roar of pain"),
    "hurtdeath":  ("hurt-death-sound-effect-for-character", "Badre-Eddine",
                   [(f + ".mp3", f + ".mp3") for f in ("1_8", "2_3", "3_2", "4_1", "5_1", "6_1", "10", "11")], "hurt/death cries"),
    "painemo":    ("pain-sounds-by-emopreben", "EmoPreben", [("painsounds.zip", "p.zip")], "grunts of pain"),
    "screech":    ("evil-screech-1", "Nocturnal_Vanguard", [("evil_screech_1.ogg", "e.ogg")], "screeches (jumpscreech, shriek)"),
    "horror1":    ("horror-scream1", "Vinrax", [("scream_horror1_0.mp3", "s.mp3")], "high horror scream (jumpscreech)"),
    "femscream":  ("female-high-pitched-scream-sfx", "WuxiaScrub", [("screams.ogg", "s.ogg")], "high screams (scream, jumpscreech)"),
    "hipitch":    ("high-pitch-scream-sounds2", "pauliuw", [("high_pitch_scream.mp3", "a.mp3")], "high scream (jumpscreech)"),
    "creature":   ("80-cc0-creature-sfx", "rubberduck", [("80-CC0-creature-SFX_0.zip", "c.zip")], "creature screams/roars (jumpscreech, shriek)"),
    "insect":     ("insect-or-alien-scream", "qubodup", [("insectoralien.flac", "i.flac")], "alien scream (shriek)"),
    "sick":       ("sick-noises", "frosty ham", [("sickness.wav", "s.wav")], "retching / gagging (gurgle)"),
    "cough":      ("old-man-cough", "AntumDeluge", [("old-man-cough.flac", "c.flac")], "wet cough (gurgle)"),
    "meat":       ("ripping-into-meat", "Eldritch Grim", [("rippingintomeat.mp3", "m.mp3")], "gore foley: flesh tears"),
    "slimy":      ("slimy-monster-or-murder-sounds9", "pauliuw", [(f"slimy_monster_or_murderd_sound_{i}.mp3", f"s{i}.mp3") for i in range(1, 8)], "gore foley: wet impacts"),
    "squish":     ("8-wet-squish-slurp-impacts", "qubodup", [("im.mp3", "s.mp3")], "gore foley: squish"),
    "splat":      ("2-wooden-squish-splatter-sequences", "qubodup", [("crack.mp3", "s.mp3")], "gore foley: splatter, cracks"),
    "towel":      ("40-wet-towel-clubpoundhitattack-sounds", "qubodup", [("a_8.mp3", "t.mp3")], "gore foley: meaty hits"),
    "hit5":       ("5-hit-sounds-dying", "TinyWorlds", [("5Hit_Sounds.zip", "h.zip")], "short male impact grunts"),
    "bubbles":    ("bubble-sound-effects", "BMacZero", [("bubbles-single1.wav", "b1.wav"), ("bubbles-single2.wav", "b2.wav"), ("bubbles-loop1-amp.wav", "bl.wav")], "bubbles (underwater, gurgle)"),
    "horrorbreath": ("horror-breathing", "primbal", [("horrorbreathing.ogg", "h.ogg")], "breath_near"),
    "tiredbreath": ("breathing-tired", "mikeask", [("breathing%20tired.wav", "t.wav")], "breath_near"),
    "ghostbreath": ("ghost-breath", "qubodup", [("ghostbreath.flac", "g.flac")], "breath_near"),
    "scrape":     ("scrapes", "AntumDeluge", [(f"scrape-{i}.ogg", f"s{i}.ogg") for i in range(1, 9)], "mood.scrape, scamper"),
}

# decoded clip ids -> (source key, path inside $DL/<key>/)
CLIPS = {
    "deathpain": ("deathpain", "grunts.wav"), "male15": ("male15", "sls.mp3"), "manhurt": ("manhurt", "m.ogg"),
    "screech": ("screech", "e.ogg"), "horror1": ("horror1", "s.mp3"), "femscream": ("femscream", "s.ogg"),
    "hipitch": ("hipitch", "a.mp3"), "sick": ("sick", "s.wav"), "cough": ("cough", "c.flac"),
    "meat": ("meat", "m.mp3"), "squish": ("squish", "s.mp3"), "splat": ("splat", "s.mp3"), "towel": ("towel", "t.mp3"),
    "insect": ("insect", "i.flac"), "horrorbreath": ("horrorbreath", "h.ogg"), "tiredbreath": ("tiredbreath", "t.wav"),
    "ghostbreath": ("ghostbreath", "g.flac"), "bub1": ("bubbles", "b1.wav"), "bub2": ("bubbles", "b2.wav"), "bubloop": ("bubbles", "bl.wav"),
}
for n in ("1_8", "2_3", "3_2", "4_1", "5_1", "6_1", "10", "11"): CLIPS["hd" + n] = ("hurtdeath", n + ".mp3")
for n in (23, 32, 33, 34, 4, 5, 47, 49): CLIPS[f"md{n}"] = ("maledead", f"x/enemy_dead/enemy_dead_{n:02d}.wav")
for n in (1, 2, 3, 4, 5, 6, 7): CLIPS[f"slimy{n}"] = ("slimy", f"s{n}.mp3")
for n in range(1, 9): CLIPS[f"scrape{n}"] = ("scrape", f"s{n}.ogg")
for n in (1, 2, 3): CLIPS[f"hit{n}"] = ("hit5", f"x/ogg/hit{n}.ogg")
CLIPS["die1"] = ("hit5", "x/ogg/die1.ogg")
for n in ("scream_01", "scream_02", "monster_01", "monster_02", "alien_03", "roar_02", "roar_03", "howl", "hurt_03", "hurt_04", "bug_01", "bug_02", "bug_03", "bug_04"):
    CLIPS["cr_" + n] = ("creature", f"x/{n}.ogg")
for n in range(1, 7): CLIPS[f"pain{n}"] = ("painemo", None)   # resolved by glob in decode()

# ---------------------------------------------------------------- fetch
def fetch():
    for key, (slug, author, files, use) in SOURCES.items():
        d = os.path.join(DL, key)
        if os.path.isdir(d) and os.listdir(d): print("have", key); continue
        os.makedirs(d, exist_ok=True)
        for url, local in files:
            subprocess.run(["curl", "-sSL", "--max-time", "120", "-o", os.path.join(d, local), OGA + url], check=True)
            if local.endswith(".zip"):
                subprocess.run(["unzip", "-q", "-o", os.path.join(d, local), "-d", os.path.join(d, "x")], check=True)
        print("fetched", key)

# ---------------------------------------------------------------- decode / io
_CACHE = {}
def decode(path, rate=SR):
    out = os.path.join(TMP, "dec_" + str(abs(hash(path))) + ".wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-ac", "1", "-ar", str(rate), out], check=True)
    sr, y = wavfile.read(out); os.remove(out)
    return y.astype(np.float64) / 32768.0

def W(cid):
    if cid in _CACHE: return _CACHE[cid]
    key, rel = CLIPS[cid]
    if cid.startswith("pain") and rel is None:
        n = int(cid[4:]); rel = sorted(glob.glob(os.path.join(DL, key, "x", f"*Track {n}*.ogg")))[0]
        p = rel
    else:
        p = os.path.join(DL, key, rel)
    y = decode(p); _CACHE[cid] = y; return y

def seg(cid, a=0.0, b=None, fin=0.004, fout=0.02):
    y = W(cid); b = len(y) / SR if b is None else b
    return fade(y[int(a * SR):int(b * SR)].copy(), fin, fout)

def bank(rel):
    return decode(os.path.join(SFX, rel))

# ---------------------------------------------------------------- processing
def rb(y, semis=0.0, tempo=1.0, formant=True):
    """Pitch / tempo with rubberband (ffmpeg); formant=True keeps the vocal tract (a man stays a man)."""
    if abs(semis) < 1e-3 and abs(tempo - 1) < 1e-3: return y
    pi, po = os.path.join(TMP, "rb_in.wav"), os.path.join(TMP, "rb_out.wav")
    wavfile.write(pi, SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    flt = f"rubberband=pitch={2 ** (semis / 12):.5f}:tempo={tempo:.5f}:formant={'preserved' if formant else 'shifted'}:transients=crisp"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", pi, "-af", flt, po], check=True)
    sr, o = wavfile.read(po); return o.astype(np.float64) / 32768.0

def bend(y, s0, s1, power=1.0):
    """Tape-style pitch glide: playback rate goes from 2^(s0/12) to 2^(s1/12) over the clip (length changes)."""
    n = len(y); x = np.linspace(0, 1, n) ** power
    rate = 2 ** ((s0 + (s1 - s0) * x) / 12)
    pos = np.cumsum(rate); pos = pos[pos < n - 1]
    return np.interp(pos, np.arange(n), y)

def sat(y, d=2.5):
    y = y / (np.max(np.abs(y)) + 1e-9)
    return np.tanh(y * d) / np.tanh(d)

def grit(y, hold=3, bits=7):
    """Sample-and-hold decimation plus quantising: the crunch under a screaming throat."""
    z = np.repeat(y[::hold], hold)[:len(y)]
    q = 2 ** bits
    return np.round(z * q) / q

def peq(y, f, q, gain_db):
    """Peaking EQ as parallel band: boost or cut a band around f."""
    band = bandpass(y, f / (1 + 1 / q), min(f * (1 + 1 / q), SR / 2 * .95), 2)
    return y + band * (10 ** (gain_db / 20) - 1)

def room(y, decay=0.6, wet=0.18, tone=5000, pre=0.008):
    y = np.concatenate([y, np.zeros(int(decay * SR * .6))])
    return _reverb(y, decay, wet, pre, tone)

def echoes(y, taps, tone=2500):
    out = np.zeros(len(y) + int(max(d for d, g in taps) * SR) + 1)
    out[:len(y)] += y
    for d, g in taps:
        at(out, lowpass(y, tone) , d, g)
    return out

def mix(*parts, n=None):
    n = n or max(int(p[1] * SR) + len(p[0]) for p in parts)
    out = np.zeros(n)
    for y, t0, g in parts: at(out, y, t0, g)
    return out

def xfade_join(a, b, ov=0.06):
    k = int(ov * SR); k = min(k, len(a), len(b))
    if k <= 0: return np.concatenate([a, b])
    w = np.linspace(0, 1, k)
    mid = a[-k:] * np.cos(w * np.pi / 2) + b[:k] * np.sin(w * np.pi / 2)
    return np.concatenate([a[:-k], mid, b[k:]])

def rms_norm(y, target=0.2):
    return y * (target / (np.sqrt(np.mean(y ** 2)) + 1e-9))

def wetfoley(i, n=2):
    """A wet gore hit: layers from the recorded slimy / meat / splat / towel foley, pitched down for weight."""
    rg = np.random.default_rng(700 + i)
    srcs = [seg(f"slimy{1 + (i + k) % 7}") for k in range(n)]
    y = np.zeros(int(.7 * SR))
    for k, s in enumerate(srcs):
        s = rb(s, rg.uniform(-6, -2), 1.0, False)
        at(y, s, 0.02 * k, 1.0 / (1 + k))
    return y

def flesh_tear(i, dur=0.6):
    """Slow wet rip: a stretched slice of the meat recording, shaped."""
    spans = [(1.81, 2.33), (2.82, 3.17), (7.64, 7.92), (14.80, 15.04), (19.18, 19.43), (24.19, 24.38)]
    a, b = spans[i % len(spans)]
    y = seg("meat", a, b)
    y = rb(y, -3 - i % 3, max(.5, (b - a) / dur), False)
    return y

def bone_crunch(i):
    return SS.crunch(i % 3)

def boom(freq=70, dur=1.2, k=4.0):
    x = t(dur)
    y = glide(freq * 1.8, freq * .5, dur, 10) * np.exp(-x * k) + .7 * sine(freq * .45, dur) * np.exp(-x * (k * .8))
    y += lowpass(noise(dur), 300) * np.exp(-x * 25) * .8
    return fade(y, .001, .05)

def gurgle(dur=1.2, seed=0):
    """Choking in blood: the retch recording low-passed, bubbles over it, wet breath."""
    rg = np.random.default_rng(1200 + seed)
    y = np.zeros(int(dur * SR))
    retch = [(5.94, 7.24), (1.50, 1.80), (2.24, 3.08)][seed % 3]
    r = seg("sick", *retch, fin=.02, fout=.1)
    r = rb(r, -3 + seed, 1.0, True)
    at(y, lowpass(r, 2600) * 1.2, 0.0, 1.0)
    for k in range(int(dur * 9)):
        b = seg("bub1" if rg.random() < .5 else "bub2")
        b = rb(b, rg.uniform(-4, 5), 1.0, False)
        at(y, lowpass(b, 3000), rg.uniform(0, dur - .2), rg.uniform(.7, 1.5) * np.exp(-k * .03))
    wob = 1 + .5 * np.sin(2 * np.pi * rg.uniform(7, 11) * t(dur))
    y = y * wob
    return fade(y, .01, .25)

def limiter(y, ceil=0.89, d=1.0):
    y = y / (np.max(np.abs(y)) + 1e-9)
    return np.tanh(y * 1.2 * d) / np.tanh(1.2 * d) * ceil

def master_voice(y, drive=2.2, hp=70, presence=5.0, grit_amt=0.18, rv=(0.55, 0.14)):
    """Common bus for the screams: high-pass, throat/presence bump, saturation, a bit of decimation grit, short room."""
    y = highpass(y, hp)
    y = peq(y, 2500, 1.2, presence)
    y = peq(y, 700, 1.0, 2.5)
    d = sat(y, drive)
    d = d + grit_amt * lowpass(grit(d, 3, 7), 5200)
    d = room(d, *rv)
    return d

# ---------------------------------------------------------------- death screams
# every variant: ordered voice parts (clip, a, b, semis, tempo) joined with overlaps; the double an octave down; foley.
DEATH = [
    dict(parts=[("deathpain", 4.0, 6.1, -1, 1.0)], ov=.35, end="gurgle", bend=(0, -4), under=.55, cut=2.0),
    dict(parts=[("deathpain", 14.5, 16.3, 2, 1.0), ("deathpain", 20.4, 22.6, -2, 0.95)], ov=.5, end="drop", bend=(0, -7), under=.5, cut=None),
    dict(parts=[("deathpain", 36.0, 37.4, -2, 1.0), ("md33", 0, None, -1, 1.1)], ov=.3, end="gurgle", bend=(0, -3), under=.6, cut=2.0),
    dict(parts=[("deathpain", 23.9, 25.8, 0, 1.0), ("hd3_2", 0.5, 3.2, -4, 0.95)], ov=1.2, end="drop", bend=(0, -6), under=.5, cut=None),
    dict(parts=[("deathpain", 0.5, 1.9, 1, 1.0), ("deathpain", 47.5, 49.0, 2, 1.0)], ov=.15, end="gurgle", bend=(0, -4), under=.5, cut=2.5),
    dict(parts=[("deathpain", 42.2, 43.7, -3, 1.0), ("manhurt", 4.98, 6.39, 0, 1.0), ("deathpain", 31.5, 32.6, -2, 1.0)], ov=.5, end="drop", bend=(1, -8), under=.6, cut=None),
]

def death(i):
    D = DEATH[i]; rg = np.random.default_rng(300 + i)
    voice = None
    for cid, a, b, semis, tempo in D["parts"]:
        s = seg(cid, a, b)
        s = rb(s, semis, tempo, True)
        s = s / (np.max(np.abs(s)) + 1e-9)
        voice = s if voice is None else xfade_join(voice, s, D["ov"])
    voice = bend(voice, *D["bend"], power=2.0)
    cap = D["cut"] or 3.3
    if len(voice) > cap * SR: voice = fade(voice[:int(cap * SR)], .005, .04 if D["cut"] else .5)   # a hard cut when it ends in a gurgle
    body = voice
    under = rb(voice, -12, 1.0, True)
    over = rb(voice, 5, 1.0, True) * .22                                       # the thin, high tearing edge
    n = len(body)
    stack = np.zeros(n); stack += body
    under, over = fit(under, n / SR), fit(over, n / SR)
    at(stack, under, 0, D["under"]); at(stack, over, 0.01, 1.0)
    # throat-tear grit layer: the voice through the band 1-4 kHz, crushed
    gr = grit(sat(bandpass(body, 900, 4200), 4), 4, 6) * .35
    stack += np.pad(gr, (0, max(0, n - len(gr))))[:n]
    v = master_voice(stack, drive=2.4, grit_amt=.2)
    out_n = len(v) + int(1.4 * SR)
    out = np.zeros(out_n)
    at(out, v, 0.06, 0.9)
    # onset: boom + flesh tear + bone crunch, hits timed on the first loud syllable
    at(out, boom(60 + 6 * i, 1.4, 3.5), 0.0, .9)
    at(out, rms_norm(flesh_tear(i, .55), .11) , 0.02, 1.0)
    at(out, bone_crunch(i), 0.05, .7)
    at(out, wetfoley(i, 2), 0.1, .8)
    # a second wet tear and crunch during the scream, at its peak
    pk = 0.06 + np.argmax(np.convolve(np.abs(body), np.ones(2000) / 2000, 'same')) / SR
    at(out, rms_norm(flesh_tear(i + 3, .5), .09), pk + .05, .8)
    at(out, SS.crunch((i + 1) % 3), pk + .4, .55)
    # ending: gurgle after a cut-off, or the voice sags into a rattle
    end_t = 0.06 + len(v) / SR - .5
    if D["end"] == "gurgle":
        g = gurgle(1.5, i)
        at(out, g, end_t - .1, .9 + .1 * i % 2)
        at(out, rms_norm(wetfoley(i + 5, 1), .08), end_t + .6, .7)
    else:
        at(out, lowpass(gurgle(1.0, i + 1), 1800), end_t + .1, .45)
    out = highpass(out, 35)
    return fade(out[:int(3.95 * SR)], .001, .35)

# ---------------------------------------------------------------- jump screeches
JUMP = [
    dict(v=[("screech", 1.93, 2.86, 3, 1.0), ("deathpain", 4.0, 5.2, 4, 1.0)], m=("cr_scream_01", 0, None, -2, 1.0), sub=48),
    dict(v=[("horror1", 1.0, 2.6, 0, 1.0), ("hipitch", 0.1, 1.5, -3, 1.0)], m=("cr_monster_01", 0, None, -5, 1.0), sub=44),
    dict(v=[("femscream", 3.44, 4.24, -2, 1.0), ("hd11", 0, 1.8, 2, 1.0)], m=("cr_scream_02", 0, None, -4, 1.0), sub=52),
    dict(v=[("screech", 3.86, 4.71, 2, 1.0), ("deathpain", 20.4, 22.0, 3, 1.0)], m=("cr_alien_03", 0, None, -6, 1.0), sub=46),
]

def jump(i):
    J = JUMP[i]; rg = np.random.default_rng(400 + i)
    layers = []
    for cid, a, b, sm, tp in J["v"]:
        s = rb(seg(cid, a, b), sm, tp, True); layers.append(s / (np.max(np.abs(s)) + 1e-9))
    m = J["m"]; mob = rb(seg(m[0], m[1], m[2]), m[3], m[4], False); mob = mob / (np.max(np.abs(mob)) + 1e-9)
    n = int(1.7 * SR)
    y = np.zeros(n)
    at(y, layers[0], 0.02, 1.0)
    at(y, layers[1], 0.03, .9)
    at(y, mob, 0.0, .9)
    at(y, rb(mob, -12, 1.0, False), .01, .5)
    body = master_voice(y, drive=3.0, grit_amt=.2, presence=6, rv=(.35, .1))
    out = np.zeros(len(body) + int(.4 * SR))
    at(out, body, 0.0, 0.8)
    # static burst at the lunge, sub hit under it
    st = lowpass(noise(.35), 9000) * ex(.35, 16) * .8 * (1 + .6 * np.sin(2 * np.pi * 60 * t(.35)))
    at(out, st, 0.0, 1.0)
    at(out, boom(J["sub"], 1.4, 3.0), 0.0, 1.2)
    at(out, SS.hit() if callable(SS.hit) else SS.hit, 0.0, .5)
    at(out, rms_norm(flesh_tear(i, .4), .1), .02, .7)
    # a late second jolt (stutter), like the FNAF cut
    at(out, mob * .5, .35, 1.0)
    out = out[:int(1.6 * SR)]
    out = fade(out, .0005, .12)
    return limiter(out, 0.89, 2.2)

# ---------------------------------------------------------------- underwater
UNDER = [("deathpain", 4.0, 6.1, -3, 0.9), ("deathpain", 23.9, 25.8, -1, 0.85), ("manhurt", 4.98, 6.39, 3, 1.0)]

def underwater(i):
    cid, a, b, sm, tp = UNDER[i]; rg = np.random.default_rng(500 + i)
    v = rb(seg(cid, a, b), sm, tp, True); v = bend(v, 0, -4, 1.5)
    v = v / (np.max(np.abs(v)) + 1e-9)
    n = len(v) + int(1.2 * SR)
    y = np.zeros(n); at(y, v, .05)
    # muffling: a low-pass that closes as water takes the air (cutoff sweeps down), plus refractive wobble
    out = np.zeros(n); blk = 2048
    for k in range(0, n - blk, blk):
        fc = 1100 * np.exp(-k / n * 1.2)
        seg_ = lowpass(y[max(0, k - blk): k + blk], max(250, fc), 2)
        out[k:k + blk] = seg_[(k - max(0, k - blk)): (k - max(0, k - blk)) + blk]
    out = out * (1 + .35 * np.sin(2 * np.pi * (6 + 2 * i) * t(n / SR)))
    out = sat(out, 1.8)
    # bubbles: bursts that thicken as the voice dies
    bub = np.zeros(n)
    for k in range(int(26 + 6 * i)):
        b_ = seg("bub1" if rg.random() < .5 else "bub2"); b_ = rb(b_, rg.uniform(-7, 4), rg.uniform(.7, 1.2), False)
        tt = rg.uniform(.1, n / SR - .4)
        at(bub, b_ , tt, rg.uniform(.6, 1.4) * (.6 + tt / (n / SR)))
    loopb = seg("bubloop", 3.6, 4.2); at(bub, loopb, .3 + .2 * i, .8)
    # a final gurgle and a muffled thud, a rumble underneath
    at(bub, lowpass(gurgle(1.2, i), 1400), n / SR - 1.4, .9)
    res = out * 1.0 + bub * .55
    at(res, boom(50, 1.2, 4.0), 0.0, .5)
    at(res, lowpass(noise(2.5), 220) * ex(2.5, 1.6), 0.0, .35)
    res = room(res, 1.1, .35, 2200)
    return fade(lowpass(res, 5000)[:int(3.6 * SR)], .003, .4)

# ---------------------------------------------------------------- static loop
def static_loop():
    P = int(4.0 * SR)
    def gen(sec):
        n = int(sec * SR); x = t(sec)
        w = noise(sec)
        s = highpass(w, 400) * .8 + lowpass(noise(sec), 900) * .3
        # raster flutter: scan-line amplitude, a few Hz of hold-roll tearing
        s = s * (1 + .25 * np.sin(2 * np.pi * 15.75 * x) + .15 * slow(sec, 2.2))
        hum = sum(a * np.sin(2 * np.pi * f * x) for f, a in ((60, .22), (120, .16), (180, .08), (240, .05)))
        return s * .45 + hum
    return C.make_loop(gen, P, 0.5)

# ---------------------------------------------------------------- scream / scream_far / shriek (recorded)
SCREAM = [
    [("deathpain", 4.0, 5.6, 2, 1.0), ("hd11", 0, 1.6, -1, 1.0)],
    [("hd11", 0, 2.0, 0, 1.0), ("md47", 0, None, 3, 1.0)],
    [("femscream", 0.08, 1.05, -2, 1.0), ("deathpain", 20.4, 22.0, 3, 1.0)],
]

def scream(i, far=False):
    layers = [rb(seg(c, a, b), sm, tp, True) for c, a, b, sm, tp in SCREAM[i]]
    layers = [l / (np.max(np.abs(l)) + 1e-9) for l in layers]
    n = max(len(l) for l in layers) + int(.4 * SR)
    y = np.zeros(n); at(y, layers[0], 0, 1.0); at(y, layers[1], .04, .7)
    y = master_voice(y, drive=3.0, grit_amt=.25)
    if not far:
        out = np.zeros(len(y) + int(.3 * SR)); at(out, y, 0, 1.0)
        at(out, rms_norm(wetfoley(i + 2, 1), .06), .0, .5)
        return fade(out[:int(2.0 * SR)], .002, .15)
    # far: long cave echo, low-passed, thin
    y = lowpass(highpass(y, 250), 2600)
    y = np.concatenate([y, np.zeros(int(1.5 * SR))])
    y = echoes(y, [(.38, .45), (.8, .3), (1.3, .2)], 1800)
    y = _reverb(y, 2.6, .55, .03, 2200)
    return fade(y[:int(3.1 * SR)], .02, .6)

SHRIEK = [
    [("screech", 0.42, 1.10, 5, 1.0), ("cr_alien_03", 0, None, -3, 1.0)],
    [("insect", 0, 1.0, -4, 1.1), ("screech", 1.93, 2.86, 7, 1.4)],
    [("cr_scream_01", 0, None, 4, 0.9), ("hipitch", 0.2, 1.0, 5, 1.2)],
]

def shriek(i):
    layers = [rb(seg(c, a, b), sm, tp, False) for c, a, b, sm, tp in SHRIEK[i]]
    layers = [l / (np.max(np.abs(l)) + 1e-9) for l in layers]
    n = int(1.0 * SR); y = np.zeros(n); at(y, layers[0], 0, 1.0); at(y, layers[1], .02, .8)
    y = highpass(y, 450)
    y = master_voice(y, drive=4.2, grit_amt=.35, rv=(.3, .1), hp=300, presence=5)
    return fade(y[:int(.95 * SR)], .001, .12)

# ---------------------------------------------------------------- mood set
def far(rel, seed, semis=0.0, tempo=1.0, lp=1700):
    """The bank's mob sound as if 100 blocks away: thin, dark, drowned in a long cave echo."""
    y = bank(rel); y = y / (np.max(np.abs(y)) + 1e-9)
    y = rb(y, semis, tempo, True)
    y = lowpass(highpass(y, 140), lp, 3)
    y = np.concatenate([y, np.zeros(int(3.2 * SR))])
    y = echoes(y, [(.42, .5), (.93, .34), (1.55, .22), (2.3, .13)], lp * .8)
    y = _reverb(y, 3.4, .6, .05, 1800)
    return fade(y[:int(5.0 * SR)], .02, .8)

FARS = {
    "qf.mood.far_groan": [("mob/zombie/say1.m4a", -3, .85), ("mob/zombie/say3.m4a", -4, .8)],
    "qf.mood.far_rattle": [("mob/skeleton/say1.m4a", -2, .9), ("mob/skeleton/say3.m4a", -3, .85)],
    "qf.mood.far_vwoop": [("mob/endermen/idle1.m4a", -2, .9), ("mob/endermen/idle4.m4a", 0, .8)],
    "qf.mood.far_cry": [("mob/ghast/moan1.m4a", -2, .9), ("mob/ghast/moan5.m4a", -3, .85)],
    "qf.mood.far_hiss": [("mob/spider/say1.m4a", -4, .9), ("mob/cat/hiss1.m4a", -5, .85)],
}

def scamper(i):
    """Claws skittering on stone, passing left to right: tick groups, louder and brighter as it passes, fading after."""
    rg = np.random.default_rng(800 + i); sec = [2.4, 2.8, 2.2, 3.0][i]
    y = np.zeros(int(sec * SR)); tt = .05
    while tt < sec - .2:
        burst = rg.integers(3, 8); gap = rg.uniform(.012, .028)
        for b in range(burst):
            f = rg.uniform(1600, 3600)
            tick = highpass(noise(.02), 2500) * ex(.02, 380) + sine(f, .02) * ex(.02, 230) * .6
            at(y, tick, tt + b * gap * rg.uniform(.8, 1.3), rg.uniform(.5, 1.0))
        tt += burst * gap + rg.uniform(.05, .22) * (1 if rg.random() < .6 else 2)
    sc = seg(f"scrape{[3, 4, 6, 7][i]}", 0, .25); at(y, highpass(sc, 3000) * .15, .5)     # a claw dragging
    x = t(sec) / sec
    pas = np.exp(-((x - (.28 + .1 * i)) ** 2) / .05)                                       # the moment it goes by
    y = y * (.15 + pas)
    # brighter at the pass, duller far away: crossfade a low-passed copy
    dull = lowpass(y, 2200)
    w = np.clip(pas, 0, 1)
    y = y * w + dull * (1 - w)
    y = lowpass(sat(y, 3.0), 9000) * .6                                                                  # claws are all transient: squash the crest
    y = room(y, .5, .12, 4500)
    return fade(y, .003, .15)

def scrape_stone(i):
    srcs = [("scrape1", "scrape2"), ("scrape5", "scrape6")][i]
    a = rb(seg(srcs[0]), -6, .6, False); b = rb(seg(srcs[1]), -9, .5, False)
    n = int(2.3 * SR); y = np.zeros(n)
    at(y, lowpass(a, 4500), .05, 1.0); at(y, lowpass(b, 3000), .55, .8)
    at(y, lowpass(noise(2.0), 180) * ex(2.0, 1.0) * np.minimum(1, t(2.0) / .3), .1, .35)   # the weight of the slab
    y = peq(y, 900, 1.0, 4)
    y = room(y, .9, .25, 3500)
    return fade(y, .01, .3)

def breath_near(i):
    if i == 0:
        b = seg("horrorbreath", .05, 4.6, .03, .15)
    else:
        b = seg("tiredbreath", 0, 3.1, .03, .15)
        b = b / (np.max(np.abs(b)) + 1e-9)
    b = b / (np.max(np.abs(b)) + 1e-9)
    b = highpass(b, 90) if i else highpass(b, 60)
    b = peq(b, 4200, .8, 5); b = sat(b, 1.6)                                               # close: sibilant, a little warm crush
    rg = np.random.default_rng(900 + i); y = np.zeros(len(b) + int(.5 * SR)); at(y, b, 0, 1.0)
    for k in range(7):                                                                     # wet mouth: tiny slimy clicks
        s = rb(seg(f"slimy{1 + rg.integers(0, 7)}", 0, .08), rg.uniform(2, 7), 1.0, False)
        at(y, highpass(s, 600), rg.uniform(.2, len(b) / SR - .3), .22)
    y = room(y, .35, .1, 5000)
    return fade(y, .02, .25)

# ---------------------------------------------------------------- manifest, sources, readme
FAR_NAMES = list(FARS)

def flag_mojang(names):
    mp = os.path.join(SFX, "manifest.json"); m = json.load(open(mp))
    for n in names: m["events"][n]["mojang"] = True
    json.dump({"events": dict(sorted(m["events"].items()))}, open(mp, "w"), indent=1)

USED_BY = {
    "qf.scare.death_scream": ["deathpain", "manhurt", "maledead", "hurtdeath", "sick", "bubbles", "meat", "slimy"],
    "qf.scare.jumpscreech": ["screech", "deathpain", "horror1", "hipitch", "femscream", "hurtdeath", "creature", "meat"],
    "qf.scare.underwater": ["deathpain", "manhurt", "bubbles", "sick", "slimy"],
    "qf.scare.static": [],
    "qf.scare.scream": ["deathpain", "hurtdeath", "maledead", "femscream", "slimy"],
    "qf.scare.scream_far": ["deathpain", "hurtdeath", "maledead", "femscream", "slimy"],
    "qf.scare.shriek": ["screech", "creature", "insect", "hipitch"],
    "qf.mood.scamper": ["scrape"], "qf.mood.scrape": ["scrape"],
    "qf.mood.breath_near": ["horrorbreath", "tiredbreath", "slimy"],
}

def write_sources():
    out = {"note": "Every voice and foley recording in the scream pack is CC0 1.0 (public domain dedication) from "
                   "OpenGameArt.org; the licence line on each page was checked when it was downloaded. Nothing is "
                   "NC, nothing is from a game. Synthesised layers (booms, static, ticks, crunch/gore in "
                   "tools/music/scare_sounds.py) are our own. qf.mood.far_* are the bank's Mojang mob sounds "
                   "reprocessed: flagged \"mojang\": true in manifest.json and dropped by build_sfx.py --own-only.",
           "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
           "sources": [], "events": {k: sorted(set(v)) for k, v in USED_BY.items()},
           "mojang_derived": FAR_NAMES}
    for key, (slug, author, files, use) in SOURCES.items():
        out["sources"].append({"id": key, "title": slug.replace("-", " "), "url": "https://opengameart.org/content/" + slug,
                               "author": author, "licence": CC0, "files": [f[0] for f in files], "used_for": use})
    json.dump(out, open(os.path.join(SFX, "sources.json"), "w"), indent=1)
    lines = ["# Site sound bank", "",
             "`manifest.json` maps event names to files. `mob/`, `step/`, `random/` ... are the 1.7.10 game sounds and OreSpawn's, "
             "rebuilt by `tools/site/build_sfx.py` (the game's sounds are not redistributable: `--own-only` drops them).",
             "`qf/` holds our own sounds. Synthesised ones come from `tools/music/site_cues.py` and `scare_sounds.py`.",
             "The screams and the mood set are layered **recordings**: `tools/music/scream_pack.py` (fetch, then build).", "",
             "## Recordings in the scream pack (all CC0 1.0, OpenGameArt)", "",
             "Machine-readable copy: `sources.json`. Licence text: https://creativecommons.org/publicdomain/zero/1.0/", "",
             "| Source | Author | Licence | Used for |", "|---|---|---|---|"]
    for key, (slug, author, files, use) in SOURCES.items():
        lines.append(f"| [{slug}](https://opengameart.org/content/{slug}) | {author} | {CC0} | {use} |")
    lines += ["", "## Events from the pack", ""]
    for k, v in USED_BY.items():
        lines.append(f"- `{k}`: " + (", ".join(sorted(set(v))) if v else "synthesised (noise and mains hum)"))
    lines += ["", "## Mojang-derived (flagged `\"mojang\": true`; `build_sfx.py --own-only` drops them)", ""]
    lines += [f"- `{n}`: the bank's zombie / skeleton / enderman / ghast / spider / cat sounds, pitched down, low-passed, in a cave echo" for n in FAR_NAMES]
    open(os.path.join(SFX, "README.md"), "w").write("\n".join(lines) + "\n")

# ---------------------------------------------------------------- driver
DEFS = [
    ("qf.scare.death_scream", lambda: [death(i) for i in range(6)], {"pitch": [.96, 1.04]}),
    ("qf.scare.jumpscreech", lambda: [jump(i) for i in range(4)], {"pitch": [.97, 1.03]}),
    ("qf.scare.underwater", lambda: [underwater(i) for i in range(3)], {"volume": .9}),
    ("qf.scare.static", static_loop, {"volume": .35, "loop": 4.0}),
    ("qf.scare.scream", lambda: [scream(i) for i in range(3)], {"pitch": [.96, 1.04]}),
    ("qf.scare.scream_far", lambda: [scream(i, far=True) for i in (0, 2)], {"volume": .9, "pitch": [.95, 1.05]}),
    ("qf.scare.shriek", lambda: [shriek(i) for i in range(3)], {"pitch": [.94, 1.06]}),
] + [(n, (lambda n=n: [far(rel, k, sm, tp) for k, (rel, sm, tp) in enumerate(FARS[n])]), {"volume": .5, "pitch": [.97, 1.03], "bus": "ambient"}) for n in FARS] + [
    ("qf.mood.scamper", lambda: [scamper(i) for i in range(4)], {"volume": .7, "pitch": [.95, 1.05]}),
    ("qf.mood.scrape", lambda: [scrape_stone(i) for i in range(2)], {"volume": .8, "pitch": [.95, 1.05]}),
    ("qf.mood.breath_near", lambda: [breath_near(i) for i in range(2)], {"volume": .7}),
]

R7_OWNED = {"qf.scare.death_scream", "qf.scare.jumpscreech", "qf.scare.underwater", "qf.scare.scream", "qf.scare.scream_far"}

def main():
    args = sys.argv[1:]
    if args and args[0] == "fetch": return fetch()
    if args and args[0] == "build": args = args[1:]
    for name, fn, kw in DEFS:
        if name in R7_OWNED: continue   # rebuilt by scream_pack2.py (round 7: one real voice, minimal processing)
        if args and not any(a in (name, name.split(".", 2)[-1]) for a in args): continue
        kw = dict(kw); P = kw.pop("loop", None)
        SS.save(name, fn(), loop_P=int(P * SR) if P else None, **kw)
        print("built", name, flush=True)
    flag_mojang([n for n in FAR_NAMES if n in json.load(open(os.path.join(SFX, "manifest.json")))["events"]])
    write_sources()
    try:
        import scream_pack2; scream_pack2.merge_sources()
    except FileNotFoundError: pass
    for r in SS.REP: print(r)

if __name__ == "__main__":
    main()
