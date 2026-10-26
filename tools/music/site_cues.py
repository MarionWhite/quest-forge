#!/usr/bin/env python3
"""The site's own sounds (qf.*) and two music loops (music.lucky, music.krypt).

    python3 tools/music/site_cues.py [sfx|music|all] [name ...]

Needs numpy and scipy (a venv is fine) and ffmpeg. Pure synthesis, reusing the instruments in
synth.py. Output goes to site/lib/sfx/ as AAC .m4a and the entries are merged into manifest.json
(build_sfx.py keeps qf.* and music.* entries when it rebuilds the game sounds).

Seamless loops: every loop is rendered as an exactly periodic signal of P samples, then written
with PAD seconds of the loop's own tail in front and its head behind. WebAudio loops
[loopStart, loopEnd) = [PAD, PAD + P/SR). Because the signal is periodic, any window of length P is
a clean loop, so it does not matter whether the decoder strips AAC priming (Chrome and Safari do
not always agree): a shift of a few ms moves both ends together.
"""
import json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth as S
from synth import SR, t, lowpass, highpass, bandpass, reverb, env_adsr, seamless, norm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SFX = os.path.join(ROOT, "site", "lib", "sfx")
TMP = os.environ.get("QF_TMP", "/tmp/qf_site_cues")
os.makedirs(TMP, exist_ok=True)
rng = np.random.default_rng(2026)
S.rng = rng
PAD = 1.0

# ---------------------------------------------------------------- helpers
def noise(sec): return rng.standard_normal(int(sec * SR))
def ex(sec, k): return np.exp(-t(sec) * k)
def sine(f, sec, ph=0.0): return np.sin(2 * np.pi * f * t(sec) + ph)
def glide(f0, f1, sec, k=6.0):
    x = t(sec); f = f1 + (f0 - f1) * np.exp(-x * k)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def slow(sec, hz):
    from scipy.ndimage import gaussian_filter1d
    y = gaussian_filter1d(noise(sec), SR / (2 * np.pi * hz)); return y / (np.std(y) + 1e-9)
def smooth(x, sec):
    """Gaussian smoothing of a slow control curve (done at 100 Hz: a 1 s kernel at 44.1 kHz is far too slow)."""
    from scipy.ndimage import gaussian_filter1d
    k = SR // 100; c = x[::k]; c = gaussian_filter1d(c, sec * 100, mode="nearest")
    return np.interp(np.arange(len(x)), np.arange(len(c)) * k, c)
def fit(x, sec):
    n = int(sec * SR); return np.pad(x, (0, max(0, n - len(x))))[:n]
def at(dest, src, sec, g=1.0):
    i = int(sec * SR)
    if i >= len(dest): return
    n = min(len(src), len(dest) - i); dest[i:i + n] += src[:n] * g
def fade(x, a=0.003, r=0.01):
    x = x.copy(); A, R = int(a * SR), int(r * SR)
    if A: x[:A] *= np.linspace(0, 1, A)
    if R: x[-R:] *= np.linspace(1, 0, R)
    return x
def bell(f, sec, k=4.0, inh=(1, 2.76, 5.4, 8.9), amp=(1, .5, .25, .12)):
    x = t(sec); y = 0
    for r, a in zip(inh, amp): y = y + a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * k * (1 + .6 * r))
    return y * np.minimum(1, x / 0.002)
def saw(f, sec, n=14, detune=0.0):
    x = t(sec); f = f * (1 + detune); return sum(np.sin(2 * np.pi * f * k * x + k) / k for k in range(1, n))
def mid(x, rev, **kw):
    """Circular reverb: tile the loop three times and keep the middle copy."""
    n = len(x); y = rev(np.concatenate([x, x, x]), **kw); return y[n:2 * n]
def make_loop(gen, P, xf=4.0):
    """gen(n_seconds) -> signal; returns exactly P samples whose end runs into its start."""
    y = gen(P / SR + xf)
    return seamless(y, xf)[:P] if y.ndim == 1 else np.stack([seamless(y[:, c], xf)[:P] for c in range(y.shape[1])], 1)
def pad_loop(y):
    p = int(PAD * SR); return np.concatenate([y[-p:], y, y[:p]])

def lufs(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = r[r.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", tail); P = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(I.group(1)) if I else -70.0, float(P.group(1)) if P else 0.0)

def gain_to(y, wav_path, target, ceil_db=-4.0):
    """Scale y so integrated loudness hits `target` LUFS, unless that would pass the peak ceiling."""
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.5
    wavfile.write(wav_path, SR, (y * 32767).astype(np.int16))
    I, _ = lufs(wav_path)
    cap = 10 ** (ceil_db / 20) / np.max(np.abs(y))        # gain that puts the peak on the ceiling
    if I < -60: return y * min(cap, 10 ** (-4 / 20) / np.max(np.abs(y)))   # too short to measure: peak at -4 dBFS
    return y * min(10 ** ((target - I) / 20), cap)

def encode(y, rel, bitrate, ar=44100):
    os.makedirs(os.path.dirname(os.path.join(SFX, rel)), exist_ok=True)
    ch = 1 if y.ndim == 1 else 2
    wav = os.path.join(TMP, "enc.wav")
    wavfile.write(wav, SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", str(ch), "-ar", str(ar), "-c:a", "aac",
                    "-b:a", bitrate, "-movflags", "+faststart", os.path.join(SFX, rel)], check=True)

def register(name, files, **kw):
    mp = os.path.join(SFX, "manifest.json")
    m = json.load(open(mp)) if os.path.exists(mp) else {"events": {}}
    m["events"][name] = {"files": files, **kw}
    json.dump({"events": dict(sorted(m["events"].items()))}, open(mp, "w"), indent=1)

REPORT = []
def save_sfx(name, ys, target=-16.0, bus="sfx", volume=1.0, pitch=1, loop=None, ceil=-4.0):
    """ys: one signal or a list of variants (mono)."""
    ys = ys if isinstance(ys, list) else [ys]
    files = []
    for i, y in enumerate(ys):
        rel = "qf/" + name[3:].replace(".", "_") + (f"{i + 1}" if len(ys) > 1 else "") + ".m4a"
        y = gain_to(y, os.path.join(TMP, "m.wav"), target, ceil)
        if loop:
            P = len(y); y = pad_loop(y)
        encode(y, rel, "72k", 32000 if not loop else 44100)
        files.append(rel)
    kw = {"volume": volume, "pitch": pitch, "bus": bus}
    if loop: kw.update(loop=True, loopStart=PAD, loopEnd=round(PAD + P / SR, 6))
    register(name, files, **kw)
    d = (P / SR) if loop else len(ys[0]) / SR
    REPORT.append((name, round(d, 2), len(files), lufs(os.path.join(SFX, files[0]))))

# ---------------------------------------------------------------- the sounds
def whoosh():
    n = int(0.9 * SR); x = t(0.9); y = np.zeros(n); src = noise(0.9)
    for fc in (250, 500, 1000, 2000, 4000, 7000):
        g = np.exp(-((np.log2(fc) - (8.0 + 3.6 * (x / 0.9) ** 1.5)) ** 2) / 1.2)
        y += bandpass(src, fc * .7, fc * 1.4, 2) * g
    amp = (x / 0.8) ** 2.2 * (x < 0.8) + np.exp(-(x - 0.8) * 40) * (x >= 0.8)
    low = lowpass(noise(0.9), 120) * 4 * amp * 0.5
    return fade((y * 1.0 + low) * amp, 0.01, 0.03)

def case_slam():
    y = np.zeros(int(0.8 * SR)); x = t(0.8)
    y += glide(95, 44, 0.8, 9) * np.exp(-x * 5.5) * 1.0                        # the thud
    y += sine(38, 0.8) * np.exp(-x * 4.0) * 0.8                                  # low boom
    for f, g, k in ((190, .5, 22), (330, .4, 28), (545, .3, 35), (870, .2, 45), (1450, .12, 60)):   # wood and metal shell
        y += sine(f * (1 + rng.uniform(-.02, .02)), .8) * np.exp(-x * k) * g
    y += lowpass(noise(.8), 1800) * np.exp(-x * 70) * 0.9                       # impact click
    dust = np.zeros(len(x))
    for tt in np.cumsum(rng.uniform(0.012, 0.05, 14)) + 0.05:                  # short dusty rattle
        at(dust, highpass(noise(.03), 1500) * ex(.03, 120) * rng.uniform(.3, 1) * np.exp(-tt * 3.2), tt)
    y += dust * 0.35
    return fade(y, 0.0005, 0.04)

def reel_tick():
    x = t(0.025)
    return fade(sine(2100, .025) * np.exp(-x * 220) * .8 + highpass(noise(.025), 3000) * np.exp(-x * 400) * .6, .0003, .004)

def reel_land():
    y = np.zeros(int(0.45 * SR))
    for tt, g, f in ((0, 1, 1500), (.075, .75, 1350), (.17, .5, 1200), (.3, .3, 1100)):
        x = t(.05); at(y, (sine(f, .05) * np.exp(-x * 120) + lowpass(noise(.05), 2500) * np.exp(-x * 200)) * g, tt)
    at(y, glide(180, 90, .3, 14) * ex(.3, 14), 0, 0.7)
    return fade(y, .0005, .05)

def chord_bells(freqs, sec, k=3.0, spread=0.05, rev=1.6):
    y = np.zeros(int(sec * SR))
    for i, f in enumerate(freqs): at(y, bell(f, sec - i * spread, k), i * spread, 1 / (1 + .15 * i))
    return reverb(y, rev, .3, .01, 7000)

def jackpot():
    sec = 2.0; y = np.zeros(int(sec * SR)); x = t(sec)
    sw = noise(sec)
    sh = bandpass(sw, 2000, 9000, 2) * (x / 1.0).clip(0, 1) ** 2 * np.exp(-np.maximum(x - 1.0, 0) * 5)
    y += sh * 0.5
    ph = np.cumsum(500 * 2 ** (x * 2.0)) / SR * 2 * np.pi                       # rising glissando, two octaves
    y += np.sin(ph) * (x < 1.0) * (x / 1.0) ** 1.5 * 0.25
    for tt in np.sort(rng.uniform(0.05, 1.0, 26) ** 0.7):                      # sparkle that gets denser
        at(y, bell(rng.choice([2093, 2637, 3136, 3951, 4186]), .35, 9) * 0.22, tt)
    for i, f in enumerate((523.25, 659.25, 783.99, 987.77, 1174.66, 1567.98)):  # Cmaj9 bloom at 0.9 s
        at(y, bell(f, 1.1, 2.4) * 0.8 / (1 + .2 * i), 0.9 + i * .025)
    at(y, sine(130.8, 1.1) * ex(1.1, 2.5) * .5, .9)
    return fade(reverb(y, 1.8, .28, .01, 8000), .002, .1)

def good():
    y = np.zeros(int(1.1 * SR))
    at(y, bell(784, 1.0, 3.4), 0); at(y, bell(1174.7, .9, 3.0), .11); at(y, bell(1568, .8, 3.4) * .4, .11)
    return fade(reverb(y, 1.2, .25, .01, 7000), .001, .1)

def neutral():
    y = np.zeros(int(.6 * SR)); x = t(.6)
    y += (sine(440, .6) + .3 * sine(880, .6) + .12 * sine(1320, .6)) * np.exp(-x * 7)
    return fade(y * np.minimum(1, x / .004), .001, .08)

def bad():
    sec = 1.4; x = t(sec); y = np.zeros(len(x))
    y += glide(78, 49, sec, 3) * np.exp(-x * 2.4) * 1.0
    y += (sine(110, sec) + sine(116.5, sec) * .9) * np.exp(-x * 3.0) * .6        # a rubbing minor second
    y += lowpass(noise(sec), 400) * np.exp(-x * 14) * .7
    y += bell(220, sec, 1.2, (1, 1.41, 2.3), (.4, .25, .12)) * .3
    return fade(reverb(lowpass(y, 1600), 2.2, .4, .02, 1800), .001, .2)

def deadly():
    sec = 2.0; x = t(sec); y = np.zeros(len(x))
    a = np.minimum(1, x / .04) * np.exp(-np.maximum(x - .35, 0) * 1.6)
    stack = sum(saw(f, sec, 12, d) for f in (58.3, 82.4, 116.5, 164.8) for d in (-.006, .006))
    open_ = lowpass(stack, 500) * .5 + lowpass(stack, 1700) * np.exp(-x * 3) * .9
    y += open_ * a * .35
    y += glide(70, 22, sec, 1.4) * a * 1.0
    y += lowpass(noise(sec), 250) * np.exp(-x * 9) * .6
    return fade(reverb(y, 2.6, .4, .02, 1500), .001, .25)

def boss_sting():
    sec = 3.6; x = t(sec); y = np.zeros(len(x))
    y += glide(75, 25, sec, 1.1) * np.exp(-x * 1.0) * 1.2
    y += sine(30, sec) * np.exp(-x * 1.3) * .8
    stack = sum(saw(f, sec, 14, d) for f in (36.7, 55.0, 73.4, 87.3, 110.0) for d in (-.01, .01))
    y += lowpass(stack, 900) * np.minimum(1, x / .06) * np.exp(-x * 1.1) * .25
    y += lowpass(noise(sec), 1500) * np.exp(-x * 7) * .8                         # the crash
    y += bell(440, sec, .8, (1, 2.4, 3.7, 5.1), (.3, .25, .15, .1)) * .2
    return fade(reverb(y, 3.4, .45, .03, 3000), .001, .4)

def exclaim():
    x = t(.14); f = 1500 * (1 + .12 * np.exp(-x * 60))
    return fade((np.sin(2 * np.pi * np.cumsum(f) / SR) + .3 * np.sin(4 * np.pi * np.cumsum(f) / SR)) * np.exp(-x * 30), .0008, .02)

def ui_open():
    y = np.zeros(int(.2 * SR)); at(y, bell(660, .15, 14, (1, 2), (1, .2)), 0); at(y, bell(990, .15, 14, (1, 2), (1, .2)), .05); return fade(y, .001, .03)
def ui_close():
    y = np.zeros(int(.2 * SR)); at(y, bell(880, .15, 14, (1, 2), (1, .2)), 0); at(y, bell(587, .15, 14, (1, 2), (1, .2)), .05); return fade(y, .001, .03)

def krypt_gate():
    sec = 4.8; x = t(sec); n = len(x)
    amp = np.minimum(1, x / .5) * np.where(x < 4.3, 1, np.exp(-(x - 4.3) * 12)) * (.75 + .25 * np.sin(x * 2.6))
    drive = np.cumsum(np.maximum(7 + 8 * np.sin(x * 1.3) + 3 * slow(sec, 4), 2)) / SR
    imp = np.zeros(n); imp[np.where(np.diff(np.floor(drive)) > 0)[0]] = 1
    imp = np.convolve(imp, np.hanning(60), "same") * rng.uniform(.5, 1, n)
    grind = sum(bandpass(imp + .5 * noise(sec), f * .9, f * 1.1, 2) * g for f, g in ((90, 1), (170, .8), (310, .5), (620, .25)))
    grit = lowpass(noise(sec), 1800) * lowpass(np.abs(noise(sec)), 30) * .5
    rumble = lowpass(noise(sec), 70) * 5 + sine(34, sec) * .6
    y = (norm(grind, 1) * .9 + grit * .35 + rumble * .6) * amp
    at(y, glide(75, 38, .9, 7) * ex(.9, 4) * 1.6, 4.35); at(y, lowpass(noise(.3), 600) * ex(.3, 30), 4.35)   # the stop
    return fade(reverb(y, 2.6, .3, .02, 2500), .01, .3)

def krypt_wind():
    P = int(24 * SR)
    def gen(sec):
        x = t(sec); y = np.zeros(len(x))
        for fc, k, ph in ((220, 1, 0), (420, 2, 1.7), (780, 3, 3.1), (1400, 5, 4.4)):
            lfo = .55 + .45 * np.sin(2 * np.pi * k * x / 24 + ph)
            y += bandpass(noise(sec), fc * .75, fc * 1.3, 2) * lfo ** 2 * (1.2 / (1 + fc / 500))
        y += lowpass(noise(sec), 90) * 2 * (.6 + .4 * np.sin(2 * np.pi * x / 24 * 2))
        return y
    return make_loop(gen, P, 5.0)

def krypt_drip(i):
    f = [2300, 1850, 2900, 1600, 2500][i]; sec = 1.4
    y = np.zeros(int(sec * SR)); x = t(.3)
    d = np.sin(2 * np.pi * np.cumsum(f * (1 + .35 * (1 - np.exp(-x * 40)) * .3 + .0)) / SR) * np.exp(-x * 24)
    at(y, d + .3 * lowpass(noise(.3), 3500) * np.exp(-x * 400), 0)
    if i % 2: at(y, d * .3, .28 + .04 * i)                                       # a stone-tunnel echo
    return fade(reverb(y, 2.2, .5, .02, 3500), .0005, .2)

def krypt_groan(i):
    sec = [3.6, 4.2, 5.0, 3.0][i]
    g = S.groan(8.0, 30 + 8 * i, (50 - 4 * i, 30))   # groan() wants >= 7.6 s; take the middle
    a = int((8.0 - sec) / 2 * SR); g = g[a:a + int(sec * SR)]
    v = S.formant_voice(48 + 7 * i, sec, "o", 3.5, .02, .04, sec * .45, sec * .45) * .7
    y = lowpass(g * .8 + v * .5, 1100)
    return fade(reverb(y, 3.0, .45, .04, 1400), .02, .3)

def heartbeat():
    P = int(4.0 * SR); y = np.zeros(P)
    for k in range(4):
        b = k * SR
        for dt, f, g in ((0, 52, 1), (.27, 45, .7)):
            x = t(.28); at(y, glide(f * 1.6, f, .28, 25) * np.exp(-x * 17) * g, k + dt)
    return mid(lowpass(y, 160), reverb, decay=1.2, wet=.3, tone=300)

def scare_riser():
    sec = 1.5; x = t(sec)
    n = bandpass(noise(sec), 400, 6000, 2) * (x / sec) ** 2.2
    rate = 6 + 38 * (x / sec) ** 2; trem = .55 + .45 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    ph = 2 * np.pi * np.cumsum(220 * 2 ** (x * 1.2)) / SR
    tone = (np.sin(ph) + np.sin(ph * 1.414) * .7 + np.sin(ph * 1.003) * .8) * (x / sec) ** 1.8
    return fade((n * .7 * trem + tone * .35), .01, .004)

def scare_hit():
    sec = 1.5; x = t(sec); y = np.zeros(len(x))
    for f, g in ((310, 1), (587, .8), (941, .7), (1330, .55), (2210, .4), (3470, .3)):   # clanging metal
        y += sine(f * rng.uniform(.99, 1.01), sec) * np.exp(-x * (3 + f / 500)) * g * .4
    y += glide(95, 20, sec, 5) * np.exp(-x * 2.4) * 1.4
    y += noise(sec) * np.exp(-x * 45) * .9
    st = sum(saw(f, sec, 12, d) for f in (233.1, 329.6, 466.2) for d in (-.01, .01))
    y += lowpass(st, 2500) * np.exp(-x * 8) * .25
    return fade(reverb(np.tanh(y * 1.2), 1.4, .25, .005, 5000), .0003, .15)

def gore(i):
    sec = .55; x = t(sec); y = np.zeros(len(x))
    f = [260, 330, 210, 400][i]
    sq = bandpass(noise(sec), f * .6, f * 2.2, 2) * (.5 + .5 * np.sin(2 * np.pi * (14 + 5 * i) * x * (1 - x / 1.5))) * np.exp(-x * 7)
    y += sq * 1.2
    for tt in np.cumsum(rng.uniform(.01, .045, 8)):                            # crunch
        at(y, bandpass(noise(.03), 900, 3500, 2) * ex(.03, 110) * rng.uniform(.5, 1.3), tt)
    at(y, glide(160 - 20 * i, 55, .25, 18) * ex(.25, 12) * 1.2, 0)                # meaty thud
    at(y, highpass(noise(.01), 2000) * 1.5, 0)                                  # bone snap
    return fade(reverb(y, .5, .15, .004, 4000), .0003, .08)

def ringing():
    sec = 3.0; x = t(sec)
    env = np.minimum(1, x / .02) * (np.exp(-x * .9) * .6 + .4 * (1 - x / sec) ** 2)
    f = 6100 + 25 * np.sin(2 * np.pi * 0.8 * x)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) + .5 * sine(4310, sec) + .25 * sine(8200, sec)
    y *= env * (.9 + .1 * np.sin(2 * np.pi * 5 * x))
    at(y, lowpass(noise(.4), 300) * ex(.4, 10) * 4, 0)
    return fade(y, .001, .25)

def do_sfx(only=None):
    D = [
        ("qf.whoosh", whoosh, {"ceil": -6}), ("qf.case_slam", case_slam, {"ceil": -6}), ("qf.reel_tick", reel_tick, {"pitch": [.96, 1.06], "bus": "ui", "target": -20}),
        ("qf.reel_land", reel_land, {"bus": "ui"}),
        ("qf.reveal.jackpot", jackpot, {}), ("qf.reveal.good", good, {}), ("qf.reveal.neutral", neutral, {"target": -22}),
        ("qf.reveal.bad", bad, {}), ("qf.reveal.deadly", deadly, {}), ("qf.boss.sting", boss_sting, {"volume": 1}),
        ("qf.exclaim", exclaim, {"bus": "ui", "target": -20}), ("qf.ui.open", ui_open, {"bus": "ui", "target": -22}),
        ("qf.ui.close", ui_close, {"bus": "ui", "target": -22}),
        ("qf.krypt.gate", krypt_gate, {}),
        ("qf.krypt.wind", krypt_wind, {"bus": "ambient", "target": -26, "loop": True}),
        ("qf.krypt.drip", [krypt_drip(i) for i in range(5)], {"bus": "ambient", "target": -24, "pitch": [.95, 1.05]}),
        ("qf.krypt.groan", [krypt_groan(i) for i in range(4)], {"bus": "ambient", "target": -22}),
        ("qf.krypt.heartbeat", heartbeat, {"bus": "ambient", "target": -22, "loop": True}),
        ("qf.scare.riser", scare_riser, {}), ("qf.scare.hit", scare_hit, {"ceil": -9}),
        ("qf.scare.gore", [gore(i) for i in range(4)], {"pitch": [.92, 1.08]}),
        ("qf.scare.ringing", ringing, {"target": -26, "ceil": -6}),
    ]
    for name, fn, kw in D:
        if only and name not in only and name[3:] not in only: continue
        save_sfx(name, fn() if callable(fn) else fn, **kw)

# ---------------------------------------------------------------- music
NOTE = {n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}
def hz(name):
    m = re.match(r"([A-G]#?)(\d)", name); return 440 * 2 ** ((NOTE[m.group(1)] + 12 * (int(m.group(2)) + 1) - 69) / 12)

def kalimba(f, sec=2.2):
    x = t(sec)
    y = np.sin(2 * np.pi * f * x) * np.exp(-x * 2.6) + .25 * np.sin(2 * np.pi * f * 5.4 * x) * np.exp(-x * 14) + .08 * np.sin(2 * np.pi * f * 8.9 * x) * np.exp(-x * 30)
    return y * np.minimum(1, x / .002)
def harp(f, sec=3.0):
    x = t(sec); y = sum(np.sin(2 * np.pi * f * k * x * (1 + 4e-5 * k * k)) * np.exp(-x * (1.6 + .9 * k)) / k ** 1.3 for k in range(1, 8))
    return y * np.minimum(1, x / .003)
def piano(f, sec=3.5):
    x = t(sec); y = 0
    for k in range(1, 9):
        y = y + (np.sin(2 * np.pi * f * k * x * (1 + 1.2e-4 * k * k) + k) * np.exp(-x * (.9 + .5 * k)) / k ** 1.1)
    y += .6 * np.sin(2 * np.pi * f * x * 1.002) * np.exp(-x * .8)
    return lowpass(y, 3200) * np.minimum(1, x / .004)
def pad_note(f, sec):
    x = t(sec); y = (saw(f, sec, 10, -.004) + saw(f, sec, 10, .004) + .5 * np.sin(2 * np.pi * f * x))
    return lowpass(y, 700) * env_adsr(len(x), sec * .35, 0, 1, sec * .35)
def sbass(f, sec=1.6):
    x = t(sec); return (np.sin(2 * np.pi * f * x) + .2 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 2.2) * np.minimum(1, x / .01)

def lucky():
    BPM = 72; beat = int(60 / BPM * SR); bar = 4 * beat; bars = 32
    P = bars * bar; L = np.zeros(P); R = np.zeros(P)
    r = np.random.default_rng(7)
    def put(sig, pos, g=1.0, pan=0.0):
        n = len(sig); idx = (pos + np.arange(n)) % P                          # wraps: the tails carry over the seam
        np.add.at(L, idx, sig * g * (1 - max(pan, 0))); np.add.at(R, idx, sig * g * (1 + min(pan, 0)))
    chords = [("C3", ["C4", "E4", "G4", "B4"], ["C5", "D5", "E5", "G5", "B5"]),      # Cmaj7
              ("A2", ["A3", "C4", "E4", "G4"], ["C5", "E5", "G5", "A5", "D5"]),      # Am7
              ("F2", ["F3", "A3", "C4", "E4"], ["C5", "E5", "F5", "G5", "A5"]),      # Fmaj7
              ("G2", ["G3", "B3", "D4", "E4"], ["B4", "D5", "E5", "G5", "A5"])]      # G6
    mot = [["E5", "G5", "A5", "G5"], ["C5", "E5", "G5"], ["D5", "E5", "G5", "A5"], ["B4", "D5", "E5"]]
    for b in range(0, bars, 2):
        root, tones, scale = chords[(b // 2) % 4]
        for j, nm in enumerate(tones):                                         # soft pad, long overlaps
            put(pad_note(hz(nm) / 2 if j == 0 else hz(nm), 2 * bar / SR + 2.0), b * bar - int(.8 * SR), .05)
        put(sbass(hz(root)), b * bar, .5)                                      # the gentle pulse: bass on 1 and 3
        put(sbass(hz(root) * 1.5, 1.2), b * bar + 2 * beat, .22)
        put(sbass(hz(root)), (b + 1) * bar, .4); put(sbass(hz(root) * 1.5, 1.2), (b + 1) * bar + 2 * beat, .2)
        sec_ = b // 8
        if sec_ in (0, 1, 2, 3):                                               # kalimba, sparse
            for s in range(2):
                if r.random() < (.9 if sec_ != 3 else .6):
                    for k, nm in enumerate(mot[(b // 2) % 4][:3 if sec_ else 2]):
                        put(kalimba(hz(nm)), (b + s) * bar + int((1 + 1.5 * k + r.choice([0, 0, .5])) * beat), .22, r.uniform(-.4, .4))
        if sec_ in (1, 2):                                                     # harp arpeggio rolling up the chord
            for s in range(2):
                for k, nm in enumerate(tones + [tones[0].replace("4", "5")]):
                    if r.random() < .8: put(harp(hz(nm)), (b + s) * bar + k * beat // 2 + (0 if s == 0 else 3 * beat // 2), .09, r.uniform(-.5, .5))
        if sec_ == 2:                                                          # a tender piano line
            for k, nm in enumerate(mot[(b // 2) % 4]):
                put(piano(hz(nm)), (b + 1) * bar + int((k * 1.5 + 0.0) * beat), .16, .1)
    for ch in (L, R): pass
    st = np.stack([L, R], 1)
    wet = np.stack([mid(L, reverb, decay=3.4, wet=.5, pre=.015, tone=5000), mid(R, reverb, decay=3.4, wet=.5, pre=.02, tone=5000)], 1)
    return wet, P

def krypt():
    P = int(135 * SR); xf = 5.0
    r = np.random.default_rng(13); S.rng = r
    def gen(sec):
        n = int(sec * SR); x = t(sec)
        L = np.zeros(n); R = np.zeros(n)
        # drones: a beating E1 pair, with a breathing level
        br = .6 + .4 * np.sin(2 * np.pi * x / 22.5)
        d = (sine(41.2, sec) + sine(41.2 * 1.0058, sec) + .3 * sine(82.4, sec) + .2 * sine(82.4 * 1.004, sec)) * br * .5
        L += d; R += d
        # a slow tritone pad, E and Bb, filter drifting
        pad = sum(saw(f, sec, 12, dt) for f in (82.4, 116.5, 123.5) for dt in (-.005, .005)) * .06
        drift = .5 + .5 * np.sin(2 * np.pi * x / 45)
        pad = lowpass(pad, 380) * (1 - drift) + lowpass(pad, 900) * drift
        pad *= .4 + .6 * np.clip(np.sin(np.pi * ((x % 67.5) / 67.5)) ** 1.5, 0, 1)
        L += pad; R += np.roll(pad, int(.01 * SR))
        # gates of silence: everything but the sub falls away
        gate = np.ones(n)
        for a, b in ((52, 66), (96, 108)):
            gate[int(a * SR):int(b * SR)] = .06
        gate = smooth(gate, 1.0)
        L *= np.where(True, gate * .85 + .15, 1); R *= gate * .85 + .15
        # distant chant
        for tt, root, dur, v in ((8, 82.4, 11, "o"), (24, 82.4, 9, "u"), (36, 110.0, 12, "o"), (70, 82.4, 10, "u"), (82, 116.5, 8, "o"), (112, 82.4, 11, "o")):
            c = S.choir([root, root * 1.5, root * 2], dur, v, voices=3)
            c = lowpass(c, 1100) * .55
            cl = reverb(np.pad(c, (0, int(3 * SR))), 4.0, .6, .05, 1200); cr = reverb(np.pad(c, (0, int(3 * SR))), 4.0, .6, .06, 1200)
            at(L, cl, tt, .5); at(R, cr, tt, .5)
        # far booms
        for tt in (14.5, 44, 64.5, 91, 118, 126):
            h = S.big_hit(4.0, 38 + r.integers(0, 8))
            hl = reverb(np.pad(h, (0, int(2 * SR))), 3.5, .5, .05, 400)
            at(L, hl, tt, 1.1); at(R, hl, tt + .012, 1.1)
        # metal scrapes
        for tt in (19, 49, 76, 99, 121):
            dur = r.uniform(1.8, 3.0); xx = t(dur)
            sweep = r.uniform(700, 1100) * (1 + r.uniform(-.4, .5) * xx / dur)
            drive = np.maximum(26 + 12 * slow(dur, 5), 3)
            imp = (np.diff(np.floor(np.cumsum(drive) / SR), prepend=0) > 0).astype(float) * r.uniform(.4, 1, len(xx))
            m = sum(bandpass(imp + .08 * noise(dur), f * .96, f * 1.04, 2) * g for f, g in ((1130, 1), (1830, .7), (2790, .45), (4100, .25)))
            m = m * np.sin(np.pi * xx / dur) ** 2
            m = reverb(np.pad(m, (0, int(3 * SR))), 3.2, .6, .03, 3500)
            pan = r.uniform(-.6, .6); at(L, m, tt, .09 * (1 - max(pan, 0))); at(R, m, tt, .09 * (1 + min(pan, 0)))
        # an occasional drip down a long tunnel
        for tt in (29.5, 58, 86.5, 104.5, 123):
            dp = reverb(np.pad(S.drip(r.uniform(1700, 2800)), (0, int(2.5 * SR))), 2.6, .7, .03, 3000)
            at(L, dp, tt, .12); at(R, np.roll(dp, 40), tt, .12)
        return np.stack([L, R], 1)
    y = make_loop(gen, P, xf)
    return y, P

def do_music(only=None):
    for name, fn, target, br in (("music.lucky", lucky, -20.0, "112k"), ("music.krypt", krypt, -20.0, "96k")):
        if only and name not in only and name[6:] not in only: continue
        out = fn()
        y, P = out
        y = y / (np.max(np.abs(y)) + 1e-9) * .5
        wav = os.path.join(TMP, name + ".wav"); wavfile.write(wav, SR, (y * 32767).astype(np.int16))
        I, pk = lufs(wav); y = y * 10 ** ((target - I) / 20)
        peak = np.max(np.abs(y))
        if peak > 10 ** (-2 / 20): y *= 10 ** (-2 / 20) / peak
        seam = float(np.sqrt(np.mean((y[0] - y[-1]) ** 2))); typ = float(np.sqrt(np.mean(np.diff(y, axis=0) ** 2)))
        rel = "qf/" + name.replace(".", "_") + ".m4a"
        encode(pad_loop(y), rel, br)
        register(name, [rel], volume=1, bus="music", loop=True, loopStart=PAD, loopEnd=round(PAD + P / SR, 6))
        REPORT.append((name, round(P / SR, 1), 1, lufs(os.path.join(SFX, rel))))
        print(f"{name}: seam step {seam:.5f} vs typical sample step {typ:.5f}")

if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    what, names = a[0], a[1:]
    if what in ("sfx", "all"): do_sfx(names or None)
    if what in ("music", "all"): do_music(names or None)
    for r_ in REPORT: print(r_)
