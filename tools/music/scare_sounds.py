#!/usr/bin/env python3
"""The Krypt scare sounds (qf.scare.*), round 5. Pure synthesis, nothing derived from Mojang's sounds.

    QF_TMP=/some/dir /opt/anaconda3/bin/python3 tools/music/scare_sounds.py [name ...]

Needs numpy, scipy and ffmpeg (same as site_cues.py, whose helpers it reuses). Every event is a mono
AAC .m4a with its peak at about -1 dBFS (loops carry their level in the manifest "volume" instead).
Loops are exactly periodic (events placed with wrap-around in a tripled buffer, middle copy kept; beds
built from partials at multiples of 1/P), written with the same PAD scheme as site_cues.py.

Voices are a glottal source (harmonics from an f0 curve, with jitter, tremor and sub-harmonic roughness)
through formant resonators, then soft clipping: that is what makes a scream read as a throat and not a
synth lead.
"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QF_TMP", "/tmp/qf_scare")
import site_cues as C
from site_cues import (np, SR, t, lowpass, highpass, bandpass, reverb, noise, ex, sine, glide, slow, smooth,
                       fit, at, fade, saw, hz, encode, register, lufs, pad_loop, PAD, SFX, TMP)
from scipy.io import wavfile
rng = C.rng
PEAK = 10 ** (-1.4 / 20)          # pre-encode peak; AAC lands near -1 dBFS

# ---------------------------------------------------------------- voice
VOW = {"a": (850, 1220, 2810, 3600), "e": (500, 1800, 2700, 3500), "o": (500, 900, 2600, 3400),
       "i": (300, 2300, 3000, 3700), "ae": (720, 1700, 2600, 3500), "u": (330, 750, 2500, 3400)}

def tract(src, vowel, bw=0.13, g=(1, .85, .6, .35), scale=1.0):
    y = 0
    for f, gg in zip(VOW[vowel], g):
        f *= scale
        y = y + bandpass(src, f * (1 - bw), min(f * (1 + bw), SR / 2 * .95), 2) * gg
    return y

def glottal(f0, tilt=1.0, nmax=80):
    ph = 2 * np.pi * np.cumsum(f0) / SR
    kmax = int(min(nmax, 12000 / max(np.max(f0), 1)))
    y = 0
    for k in range(1, kmax + 1):
        y = y + np.sin(k * ph + 0.3 * k) / k ** tilt
    return y, ph

def voice(f0, va, vb=None, w=None, tilt=1.0, breath=.15, bw=.13, g=(1, .85, .6, .35), rough=0.0, sub=0.0, scale=1.0):
    n = len(f0)
    src, ph = glottal(f0, tilt)
    if sub: src = src + sub * np.sin(ph / 2) * 2                     # sub-harmonic: the chaotic, torn edge of a scream
    if rough:
        fr = 55 + 25 * slow(n / SR, 3)                                # amplitude roughness, jittering around 55-80 Hz
        src = src * (1 + rough * np.sin(2 * np.pi * np.cumsum(fr) / SR))
    asp = noise(n / SR) * breath
    s = src / (np.std(src) + 1e-9) + asp
    ya = tract(s, va, bw, g, scale)
    if vb is None: return ya
    yb = tract(s, vb, bw, g, scale)
    w = np.ones(n) * w if np.isscalar(w) else w
    return ya * (1 - w) + yb * w

def curve(sec, pts, jit=0.0, trem=0.0, trem_hz=7.0):
    """f0 curve from (time, hz) points, plus smooth jitter and a tremor."""
    x = t(sec); tt, ff = zip(*pts)
    f = np.interp(x, tt, np.log(ff)); f = np.exp(f)
    if jit: f = f * (1 + jit * slow(sec, 12))
    if trem: f = f * (1 + trem * np.sin(2 * np.pi * trem_hz * x + rng.uniform(0, 6)))
    return f

def envelope(sec, a=.025, hold=None, rel=.25, k=0):
    x = t(sec); n = len(x)
    e = np.minimum(1, x / a)
    hold = sec - rel if hold is None else hold
    e = e * np.where(x < hold, 1, np.exp(-(x - hold) * 3.5 / max(rel, .05)))
    e = e * (1 - np.clip((x - (sec - .02)) / .02, 0, 1))
    return e * np.exp(-x * k)

def drive(y, d=2.5):
    y = y / (np.max(np.abs(y)) + 1e-9)
    return np.tanh(y * d) / np.tanh(d)

def breath_in(sec, lo=900, hi=4200):
    x = t(sec); n = bandpass(noise(sec), lo, hi, 2)
    return n * np.sin(np.pi * np.clip(x / sec, 0, 1)) ** .8

# ---------------------------------------------------------------- screams
def scream(i, far=False):
    P = [dict(sec=1.6, pts=[(0, 330), (.05, 520), (.13, 940), (.45, 1000), (.6, 1180), (.64, 1780), (.78, 1700), (.86, 1060), (1.1, 900), (1.45, 640), (1.6, 450)],
              va="a", vb="e", wm=(.0, .5, 1.0), rough=.5, sub=.35, trem=.025),
         dict(sec=1.6, pts=[(0, 190), (.06, 330), (.16, 560), (.5, 600), (.68, 720), (.82, 560), (1.15, 520), (1.55, 330)],
              va="a", vb="o", wm=(.0, .4, 1.0), rough=.7, sub=.5, trem=.03),
         dict(sec=1.3, pts=[(0, 420), (.04, 700), (.1, 1150), (.4, 1250), (.5, 1480), (.54, 2100), (.66, 2000), (.74, 1250), (.95, 1050), (1.3, 720)],
              va="e", vb="a", wm=(.0, .6, .2), rough=.35, sub=.2, trem=.02)][i]
    sec = P["sec"]; x = t(sec)
    f0 = curve(sec, P["pts"], jit=.035, trem=P["trem"], trem_hz=6.5 + i)
    wmix = np.interp(x, np.linspace(0, sec, 3), P["wm"])
    # terror: formant 1 and 2 pulled up with the pitch (open throat), 3rd formant strong for the piercing edge
    y = voice(f0, P["va"], P["vb"], wmix, tilt=.9, breath=.28, bw=.11, g=(1, .9, .9, .55), rough=P["rough"], sub=P["sub"], scale=1.0)
    a = envelope(sec, .02, hold=sec - .35, rel=.3) * (.82 + .18 * np.clip(slow(sec, 9), -1.5, 1.5) / 1.5)
    y = y * a
    y = drive(y, 3.2)
    y = y + highpass(noise(sec), 2500) * a * .045                                  # throat rasp
    gasp = breath_in(.25, 900, 4000) * .5 * np.linspace(.4, 1, int(.25 * SR))      # the ragged breath after
    y = np.concatenate([y, np.zeros(int(.25 * SR))]); at(y, gasp * np.max(np.abs(y)) * .18, sec - .05)
    y = reverb(y, .45, .16, .004, 6000)
    if far:
        y = lowpass(y, 2600, 2) * .8
        out = np.zeros(int(3.1 * SR)); at(out, y, 0, 1.0)
        for d, gn, cut in ((.31, .5, 2200), (.66, .3, 1700), (1.05, .18, 1300), (1.5, .1, 1000)):
            at(out, lowpass(y, cut, 2), d, gn)
        out = highpass(out, 120)
        out = reverb(out, 2.8, .5, .03, 2400)
        return fade((out * np.exp(-t(3.1) * .25))[:int(3.0 * SR)], .002, .6)
    return fade(y, .001, .08)

# ---------------------------------------------------------------- shriek / hit / stinger
def shriek(i):
    sec = [.8, .62, .95][i]; x = t(sec)
    base = [2100, 2600, 1650][i]
    f0 = curve(sec, [(0, base * .6), (.05, base), (.2, base * 1.6), (.5 * sec, base * 1.35), (sec, base * .7)], jit=.05)
    f0 = f0 * (1 + .09 * np.sin(2 * np.pi * (24 + 7 * i) * x))                    # fast warble: not a throat, not a bird
    y1, _ = glottal(f0, .7, 14); y2, _ = glottal(f0 * 1.047, .7, 14)
    y = y1 + y2 * .8
    y = y * (1 + .6 * np.sin(2 * np.pi * (140 + 30 * i) * x))                     # ring-mod grit
    y = y / np.std(y) + highpass(noise(sec), 3000) * .5
    y = bandpass(y, 900, 9500, 2)
    low = drive(voice(curve(sec, [(0, 130), (.1, 180), (sec, 95)], jit=.08), "a", "o", .5, tilt=.8, breath=.4, rough=.8, sub=.6), 4)
    y = drive(y / np.max(np.abs(y)), 3.0) * .75 + low * .5
    y = y * envelope(sec, .008, hold=.25 * sec, rel=.5)
    return fade(reverb(y, .5, .22, .004, 7000), .0005, .06)

def hit():
    sec = .4; x = t(sec)
    y = glide(95, 30, sec, 11) * np.exp(-x * 7.5) * 1.5
    y += sine(46, sec) * np.exp(-x * 9) * .9
    y += glide(260, 90, sec, 40) * np.exp(-x * 30) * .6
    y += highpass(noise(sec), 1400) * np.exp(-x * 110) * 1.1                      # the crack
    y += bandpass(noise(sec), 300, 3000) * np.exp(-x * 40) * .5
    return fade(drive(y, 1.6), .0002, .05)

def stinger(i):
    sec = 1.5; x = t(sec)
    chords = [("B1 C2 F#2".split(), "B3 C4 F4 F#4".split()),
              ("A1 A#1 E2".split(), "A3 A#3 D#4 E4".split()),
              ("C#2 D2 G2".split(), "C#4 D4 G#4 G4".split())][i]
    low = sum(saw(hz(n), sec, 24, d) for n in chords[0] for d in (-.006, .006))
    brass = sum(saw(hz(n), sec, 22, d) for n in chords[1] for d in (-.008, .008))
    a = np.minimum(1, x / .012) * (np.exp(-np.maximum(x - .28, 0) * 2.6))
    bright = lowpass(brass, 5000) * np.exp(-x * 7) + lowpass(brass, 1100) * (1 - np.exp(-x * 7))      # brass bloom then dull
    y = (lowpass(low, 700) * .6 + bright * .55) * a
    for j in range(3):                                                           # strings screeching a minor second apart
        f0 = 1900 * (1 + .06 * j) * (1 + .03 * i)
        sw = f0 * (1 + .12 * np.minimum(1, x / .6))
        s = np.sin(2 * np.pi * np.cumsum(sw) / SR) + .5 * np.sin(4 * np.pi * np.cumsum(sw) / SR)
        y += s * np.minimum(1, x / .02) * np.exp(-x * 2.2) * (1 + .2 * np.sin(2 * np.pi * (6 + j) * x)) * .22
    y += glide(80, 32, sec, 4) * np.exp(-x * 3.5) * 1.5                          # sub boom
    y += (bandpass(noise(sec), 400, 9000) * np.exp(-x * 14)) * .9                 # the noise stab
    y += highpass(noise(sec), 2000) * np.exp(-x * 90) * .8
    y = drive(y, 1.8)
    y = reverb(y, 1.5, .28, .006, 4500)
    return fade(y, .0004, .2)

# ---------------------------------------------------------------- circular helpers
def circ(P, place):
    """place(dest, off): add events for one period starting at sample offset `off` (seconds).
    Events are placed in all three copies of a 3-period buffer, so anything that crosses the seam wraps."""
    n = int(P)
    dest = np.zeros(3 * n)
    for k in range(3): place(dest, k * n / SR)
    return dest

def middle(buf, n): return buf[int(n):2 * int(n)]

def addc(dest, src, off, g=1.0):
    i = int(off * SR)
    if i >= len(dest): return
    m = min(len(src), len(dest) - i); dest[i:i + m] += src[:m] * g

def periodic_noise(P, fc_lo, fc_hi):
    """exactly periodic coloured noise: FFT-domain band shaping of a random spectrum."""
    n = int(P)
    s = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR)
    m = ((f > fc_lo) & (f < fc_hi)).astype(float)
    return np.fft.irfft(s * m, n)

# ---------------------------------------------------------------- loops
def heartbeat(i):
    P = int(4.0 * SR); beats = [4, 6, 9][i]; cyc = 4.0 / beats
    def place(d, off):
        for k in range(beats):
            b = off + k * cyc
            lub = glide(78, 44, .26, 30) * np.exp(-t(.26) * 15)
            dub = glide(92, 52, .22, 30) * np.exp(-t(.22) * 19)
            clk = lowpass(noise(.05), 500) * np.exp(-t(.05) * 90)
            addc(d, lub, b); addc(d, clk, b, .6)
            addc(d, dub, b + min(.30, cyc * .42), .7); addc(d, clk, b + min(.30, cyc * .42), .35)
    buf = circ(P, place)
    y = lowpass(buf, 220, 2)
    wet = lowpass(buf, 700, 1) * .0
    y = reverb(y, .6, .25, .01, 450)
    return middle(y, P)

def breath(i=0):
    P = int(4.0 * SR)
    seq = [(.10, "in", .55, 1.0), (.75, "out", .85, 1.0), (1.75, "in", .22, .7), (2.0, "in", .30, .9), (2.4, "out", .75, .8), (3.25, "in", .38, .8)]
    def place(d, off):
        for st, kind, dur, g in seq:
            x = t(dur); n = noise(dur)
            if kind == "in":
                y = bandpass(n, 700, 4800, 2) * (x / dur) ** .8 * np.exp(-((x / dur - 1) ** 2) * 0) * g
                y += tract(n, "i", .2) * .0
            else:
                y = tract(n, "ae", .2, (1, .8, .4, .2)) * np.sin(np.pi * x / dur) ** .7 * g
                y *= 1 + .6 * np.sin(2 * np.pi * (9 + 5 * rng.random()) * x)          # shuddering exhale
                y += sine(rng.uniform(210, 260), dur) * np.sin(np.pi * x / dur) ** 2 * .05  # a whimper under it
            y = y / (np.max(np.abs(y)) + 1e-9)
            y *= 1 - np.clip(1 - x / .02, 0, 1)
            addc(d, fade(y, .02, .06), off + st, g * .8)
    buf = circ(P, place)
    y = highpass(buf, 150)
    y = reverb(y, .4, .15, .004, 4000)
    return middle(y, P)

def drone():
    Pn = 8.0; P = int(Pn * SR); x = t(Pn)
    q = lambda f: round(f * Pn) / Pn
    y = np.zeros(P)
    for f, g, m in ((41.25, 1.0, 3), (42.0, .9, 5), (58.5, .5, 2), (82.5, .35, 4), (27.5, .8, 1)):
        for h in range(1, 14):
            am = .5 + .5 * np.cos(2 * np.pi * (m + h % 3) * x / Pn + h)
            y += np.sin(2 * np.pi * q(f * h) * x + h * 1.7) * g / h ** 1.05 * (am if h > 1 else 1)
    y = middle(lowpass(np.tile(y, 3), 900, 2), P)
    # a dissonant, slightly sick upper layer: two near partials beating, and a bowed whine
    hi = (np.sin(2 * np.pi * q(1480) * x) + np.sin(2 * np.pi * q(1480) * x * 1.0 + 2 * np.pi * 1.25 * x)) * .02
    hi *= .5 + .5 * np.cos(2 * np.pi * 2 * x / Pn)
    n1 = periodic_noise(P, 60, 300); n2 = periodic_noise(P, 400, 1400)
    y += hi + n1 / np.std(n1) * .25 * (.6 + .4 * np.cos(2 * np.pi * x / Pn)) + n2 / np.std(n2) * .05 * (.5 + .5 * np.cos(2 * np.pi * 3 * x / Pn))
    # a distant, throaty "oh" a tritone up that swells in and out
    v = np.zeros(P)
    for f0, ph in ((q(55), 0), (q(77.6), 1.3)):
        v += np.sin(2 * np.pi * f0 * x + ph) * 1
    y += middle(lowpass(np.tile(v, 3), 400), P) * .5 * (.5 + .5 * np.cos(2 * np.pi * x / Pn - 2))
    return y

def ringing():
    Pn = 4.0; P = int(Pn * SR); x = t(Pn); q = lambda f: round(f * Pn) / Pn
    y = np.sin(2 * np.pi * q(6100) * x) + .45 * np.sin(2 * np.pi * q(4310) * x + 1) + .25 * np.sin(2 * np.pi * q(8200) * x + 2) \
        + .2 * np.sin(2 * np.pi * q(3170) * x + 3)
    y *= 1 + .12 * np.sin(2 * np.pi * 4 * x / Pn * 5)
    y += 0.07 * periodic_noise(P, 3000, 9000) / 0.3 * 0
    return y

def chitter():
    P = int(4.0 * SR)
    def place(d, off):
        r = np.random.default_rng(77)
        for _ in range(26):                                                   # 26 insects, each chirring in bursts
            fc = r.uniform(3200, 8200); rate = r.uniform(38, 95); tt = r.uniform(0, 4.0)
            for _b in range(r.integers(2, 4)):
                burst = r.uniform(.12, .5); gap = r.uniform(.15, .8)
                nclk = int(burst * rate); amp = r.uniform(.3, 1)
                for c in range(nclk):
                    pt = tt + c / rate + r.normal(0, .0015)
                    ln = .006
                    cl = bandpass(r.standard_normal(int(ln * SR)), fc * .8, fc * 1.2, 2) * np.exp(-t(ln) * 700) * amp
                    addc(d, cl, off + pt)
                tt += burst + gap
    buf = circ(P, place)
    y = highpass(buf, 2000)
    # scrabbling bed: low-passed leg noise with fast random gating
    bed = periodic_noise(P, 900, 3200); gate = np.abs(periodic_noise(P, 20, 160)); gate = (gate / np.max(gate)) ** 2
    return middle(y, P) * 1.0 + bed / (np.std(bed) + 1e-9) * gate * .05

# ---------------------------------------------------------------- one-shots
def whisper(i):
    sec = [1.7, 2.0, 1.4][i]; n = int(sec * SR); y = np.zeros(n); r = np.random.default_rng(300 + i)
    for voice_i, (sc, dl, gn) in enumerate(((1.0, 0.0, 1.0), (.88, .13, .7))):
        tt = dl + .05
        while tt < sec - .15:
            dur = r.uniform(.07, .24); v = list(VOW)[r.integers(0, len(VOW))]
            x = t(dur); s = noise(dur)
            seg = tract(s, v, .09, (1, .9, .6, .3), sc) * np.sin(np.pi * x / dur) ** .6
            if r.random() < .55:
                m = .05; fr = highpass(noise(m), 4500 * sc) * np.sin(np.pi * t(m) / m) * 1.6        # s / sh at the start
                seg = np.concatenate([fr, seg])
            addc(y, seg / (np.max(np.abs(seg)) + 1e-9) * r.uniform(.4, 1), tt, gn)
            tt += dur + r.uniform(.0, .2)
            if r.random() < .15: tt += r.uniform(.15, .3)
    y = highpass(y, 200)
    y = y * (.75 + .25 * slow(sec, 4))
    y = reverb(y, 1.4, .45, .01, 4000)
    return fade(y, .05, .3)

def fall():
    sec = 1.0; x = t(sec); n = noise(sec); y = np.zeros(len(x))
    for fc in (300, 600, 1200, 2400, 4800):
        c = 6500 * np.exp(-x * 2.2) + 250
        g = np.exp(-(np.log2(fc / c) ** 2) / .9)
        y += bandpass(n, fc * .75, fc * 1.3, 2) * g
    y *= np.minimum(1, x / .06) * (1 + 0.4 * x)                                  # wind builds as you plummet
    ph = 2 * np.pi * np.cumsum(1100 * np.exp(-x * 1.7) + 90) / SR
    y += np.sin(ph) * .18 * np.minimum(1, x / .1)
    y += lowpass(noise(sec), 160) * .5 * x
    return fade(y * np.minimum(1, (1 - x) / .06 + .0), .005, .12)

def crunch(i):
    r = np.random.default_rng(500 + i); sec = .5; y = np.zeros(int(sec * SR))
    at(y, highpass(noise(.01), 2500) * ex(.01, 400) * 1.5, 0)
    tt = 0.0
    for _ in range(r.integers(3, 6)):
        f = r.uniform(900, 3600); ln = .09
        c = bandpass(r.standard_normal(int(ln * SR)), f * .6, f * 1.8, 2) * ex(ln, 70) * r.uniform(.6, 1)
        c += sine(f * .9, ln) * ex(ln, 150) * .5
        at(y, c, tt); tt += r.uniform(.025, .09)
    for _ in range(9): at(y, highpass(noise(.004), 3000) * ex(.004, 600) * r.uniform(.4, 1), r.uniform(0, .25))   # splinters
    at(y, glide(150, 55, .18, 25) * ex(.18, 18) * .8, .0)
    at(y, lowpass(noise(.3), 700) * ex(.3, 14) * .3, .02)
    y = highpass(y, 40)
    return fade(drive(y, 1.3), .0003, .08)

def gore(i):
    r = np.random.default_rng(700 + i); sec = [.75, .6, .9][i]; x = t(sec); y = np.zeros(len(x))
    n = noise(sec)
    gate = np.abs(bandpass(noise(sec), 30, 120, 1)); gate = (gate / np.max(gate)) ** 1.3        # fibres letting go
    tear = bandpass(n, 400 + 150 * i, 3600, 2) * gate * np.sin(np.pi * np.minimum(1, x / sec) ** .7)
    y += tear * 1.3
    for _ in range(14):                                                                 # wet bubbles and clicks
        f0 = r.uniform(120, 480); ln = r.uniform(.02, .06); st = r.uniform(0, sec * .9)
        xb = t(ln); b = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 2.2 * xb / ln)) / SR) * ex(ln, 60 / ln / 10)
        at(y, b * r.uniform(.3, .9), st)
    sq = lowpass(noise(sec), 700) * (.5 + .5 * np.sin(2 * np.pi * (7 + 4 * i) * x)) * np.exp(-x * 3)
    y += sq * .9
    at(y, glide(130, 50, .15, 25) * ex(.15, 20) * .9, sec - .25)                         # the plop at the end
    at(y, bandpass(noise(.03), 1000, 5000) * ex(.03, 120) * 1.0, .0)
    return fade(reverb(drive(y, 1.5), .35, .14, .003, 4500), .001, .1)

def cackle(i):
    r = np.random.default_rng(900 + i); sec = [2.0, 1.7][i]; y = np.zeros(int((sec + .5) * SR))
    base = [470, 400][i]; tt = .05; k = 0
    nb = [7, 6][i]
    for k in range(nb):
        dur = r.uniform(.1, .16); f = base * (1 - .035 * k) * r.uniform(.97, 1.03)
        pts = [(0, f * .92), (.03, f * 1.12), (dur * .6, f), (dur, f * .82)]
        f0 = curve(dur + .02, pts, jit=.03)
        b = voice(f0, "e", "ae", np.linspace(0, 1, len(f0)), tilt=.8, breath=.3, bw=.1, rough=.4, sub=.1)
        b *= np.minimum(1, t(dur + .02) / .01) * np.exp(-np.maximum(t(dur + .02) - dur * .5, 0) * 14)
        at(y, highpass(noise(.03), 1500) * ex(.03, 80) * .4, tt)                      # the "h" of each "heh"
        at(y, b, tt + .015)
        tt += dur + r.uniform(.07, .12) - .005 * k
    ln = sec - tt - .1                                                                # the long rising "heeeee"
    f0 = curve(ln, [(0, base * .9), (ln * .35, base * 1.7), (ln * .75, base * 1.45), (ln, base * .8)], jit=.02, trem=.035, trem_hz=7.5)
    b = voice(f0, "e", "a", np.linspace(0, 1, len(f0)) ** 1.5, tilt=.85, breath=.35, bw=.1, rough=.5, sub=.25)
    b *= envelope(ln, .06, hold=ln * .6, rel=ln * .4)
    at(y, b, tt)
    y = drive(y, 2.0)
    y = highpass(y, 180)
    y = reverb(y, .7, .2, .006, 5000)
    return fade(y, .002, .2)

# ---------------------------------------------------------------- saving
REP = []
def peak_norm(y, db=None):
    return y / (np.max(np.abs(y)) + 1e-9) * PEAK

def save(name, ys, volume=1.0, bus="sfx", pitch=1, loop_P=None, br="96k", ar=32000):
    ys = ys if isinstance(ys, list) else [ys]; files = []
    for i, y in enumerate(ys):
        rel = "qf/" + name[3:].replace(".", "_") + (f"{i + 1}" if len(ys) > 1 else "") + ".m4a"
        y = peak_norm(y)
        if loop_P:
            assert len(y) == loop_P, (name, len(y), loop_P)
            y = pad_loop(y)
        for _ in range(6):
            encode(y, rel, br, 44100 if loop_P else ar)
            pk = decoded_peak(os.path.join(SFX, rel))
            if -1.5 < pk < -0.6: break
            y = y * 10 ** ((-1.0 - pk) / 20) * (.97 if pk > -0.3 else 1)
        files.append(rel)
    kw = dict(volume=volume, pitch=pitch, bus=bus)
    if loop_P: kw.update(loop=True, loopStart=PAD, loopEnd=round(PAD + loop_P / SR, 6))
    register(name, files, **kw)
    REP.append((name, len(files), round((loop_P or len(ys[0])) / SR, 2)))

def decoded_peak(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-"], capture_output=True).stdout
    return 20 * np.log10(np.max(np.abs(np.frombuffer(raw, np.float32))) + 1e-9)

def seam(y):
    return float(abs(y[0] - y[-1])), float(np.sqrt(np.mean(np.diff(y) ** 2)))

DEFS = [
    ("qf.scare.scream", lambda: [scream(i) for i in range(3)], {"pitch": [.96, 1.04]}),
    ("qf.scare.scream_far", lambda: [scream(i, far=True) for i in (0, 2)], {"volume": .9, "pitch": [.95, 1.05]}),
    ("qf.scare.shriek", lambda: [shriek(i) for i in range(3)], {"pitch": [.94, 1.06]}),
    ("qf.scare.stinger", lambda: [stinger(i) for i in range(3)], {}),
    ("qf.scare.hit", hit, {}),
    ("qf.scare.heartbeat", lambda: [heartbeat(i) for i in range(3)], {"volume": .7, "loop": 4.0}),
    ("qf.scare.breath", breath, {"volume": .6, "loop": 4.0}),
    ("qf.scare.drone", drone, {"volume": .55, "loop": 8.0, "bus": "ambient"}),
    ("qf.scare.ringing", ringing, {"volume": .3, "loop": 4.0}),
    ("qf.scare.chitter", chitter, {"volume": .5, "loop": 4.0}),
    ("qf.scare.whisper", lambda: [whisper(i) for i in range(3)], {"volume": .8}),
    ("qf.scare.fall", fall, {}),
    ("qf.scare.crunch", lambda: [crunch(i) for i in range(3)], {"pitch": [.94, 1.06]}),
    ("qf.scare.gore", lambda: [gore(i) for i in range(3)], {"pitch": [.94, 1.06]}),
    ("qf.scare.cackle", lambda: [cackle(i) for i in range(2)], {"pitch": [.96, 1.04]}),
]

def main():
    only = sys.argv[1:]
    for name, fn, kw in DEFS:
        if only and name not in only and name[3:] not in only and name[9:] not in only: continue
        kw = dict(kw); P = kw.pop("loop", None)
        out = fn() if callable(fn) else fn
        save(name, out, loop_P=int(P * SR) if P else None, **kw)
    for r_ in REP: print(r_)

if __name__ == "__main__":
    main()
