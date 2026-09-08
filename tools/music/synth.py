#!/usr/bin/env python3
"""Prototype cues for Quest Forge, round 2 (2026-09-04).

  loading  "Hall of the Knight"   chant + drone + horns, NO metered drum, seamless loop
  menu     "The Hall Goes Quiet"  crickets -> distant deep groan silences them -> night filler -> crickets return

Pure numpy synthesis (no soundfonts on this Mac). Writes WAV + OGG to out/.
Both outputs are seamless loops: the tail is crossfaded under the head, so the last sample
runs straight into the first. Splash playback (javax Clip.loop) is gapless; vanilla MusicTicker
inserts a 1-30 s gap between repeats unless the coremod delay tweak is applied (README).
"""
import os, subprocess, numpy as np
from numpy.random import default_rng
from scipy.signal import butter, lfilter, fftconvolve
from scipy.io import wavfile

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
rng = default_rng(11)

# ---------------- utils ----------------
def t(sec): return np.arange(int(sec * SR)) / SR
def env_adsr(n, a, d, s, r):
    e = np.ones(n); A = int(a*SR); D = int(d*SR); R = int(r*SR)
    if A: e[:A] = np.linspace(0, 1, A)
    if D: e[A:A+D] = np.linspace(1, s, D)
    e[A+D:n-R] = s
    if R: e[n-R:] = np.linspace(s, 0, R)
    return e
def lowpass(x, c, o=2):  b, a = butter(o, c/(SR/2)); return lfilter(b, a, x)
def highpass(x, c, o=2): b, a = butter(o, c/(SR/2), btype="high"); return lfilter(b, a, x)
def bandpass(x, lo, hi, o=2): b, a = butter(o, [lo/(SR/2), hi/(SR/2)], btype="band"); return lfilter(b, a, x)
def reverb(x, decay=2.5, wet=0.35, pre=0.02, tone=4000):
    n = int(decay*SR); ir = rng.standard_normal(n) * np.exp(-np.arange(n)/(decay*SR/6))
    ir = lowpass(ir, tone); ir[:int(pre*SR)] = 0; ir /= np.abs(ir).sum()**0.5
    y = fftconvolve(x, ir)[:len(x)]
    return (1-wet)*x + wet*y/(np.max(np.abs(y))+1e-9)*np.max(np.abs(x))
def mix(dest, src, at):
    i = int(at*SR); n = min(len(src), len(dest)-i)
    if n > 0: dest[i:i+n] += src[:n]
def norm(x, peak=0.89): return x / (np.max(np.abs(x))+1e-9) * peak
def seamless(y, xf=4.0):
    """Crossfade the last xf seconds under the first xf seconds and trim, so y[-1] -> y[0] is continuous."""
    n = int(xf*SR); w = np.linspace(0, 1, n)
    head = y[:n] * np.sin(w*np.pi/2) + y[-n:] * np.cos(w*np.pi/2)
    out = y[:-n].copy(); out[:n] = head
    return out
def write(name, mono_or_stereo):
    y = mono_or_stereo
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (np.clip(y, -1, 1)*32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(OUT, name + ".wav"),
                    "-c:a", "libvorbis", "-q:a", "5", os.path.join(OUT, name + ".ogg")], check=True)
    print("wrote", name, f"{len(y)/SR:.1f}s")

# ---------------- instruments ----------------
def formant_voice(f0, dur, vowel="o", vib=5.0, vibd=0.006, breath=0.05, att=0.6, rel=0.6):
    F = {"o": (450, 800, 2830), "a": (800, 1150, 2900), "u": (325, 700, 2530), "e": (400, 1700, 2600)}[vowel]
    x = t(dur); n = len(x)
    ph = 2*np.pi*np.cumsum(f0*(1 + vibd*np.sin(2*np.pi*vib*x + rng.uniform(0, 6))))/SR
    y = np.zeros(n)
    for k in range(1, 40):
        if k*f0 > SR/2: break
        y += np.sin(k*ph) / k
    y = sum(bandpass(y, f*0.85, f*1.15, 2) * g for f, g in zip(F, (1.0, 0.6, 0.25)))
    y += breath * bandpass(rng.standard_normal(n), 800, 3500)
    return y * env_adsr(n, att, 0.2, 0.85, rel)

def choir(freqs, dur, vowel="o", detune=0.012, voices=4):
    y = np.zeros(int(dur*SR))
    for f in freqs:
        for _ in range(voices):
            y += formant_voice(f*(1 + rng.uniform(-detune, detune)), dur, vowel)
    return y / (len(freqs)*voices)

def big_hit(dur=3.0, f=44):
    """Distant, soft, no slap: a single deep boom, more felt than heard."""
    x = t(dur)
    body = np.sin(2*np.pi*(f*x + 25*np.exp(-x*6))) * np.exp(-x*1.8)
    return lowpass(body, 300) * env_adsr(len(x), 0.01, 0.1, 1.0, 0.8)

def horn(f, dur):
    x = t(dur); n = len(x); ph = 2*np.pi*f*x
    y = sum(np.sin(k*ph)/k**0.8 for k in range(1, 12))
    return lowpass(y, 1200) * env_adsr(n, 0.5, 0.2, 0.8, 0.8)

def sub_drone(f, dur, wobble=0.06):
    x = t(dur)
    return (np.sin(2*np.pi*f*x) + 0.3*np.sin(2*np.pi*f*2*x + 0.2*np.sin(2*np.pi*wobble*x))) * 0.6

def cricket(dur, carrier=4400, chirp_rate=2.2, pulses=3, pulse_rate=42):
    """Field cricket: chirps of `pulses` pulses at pulse_rate, chirp_rate chirps/s with timing jitter."""
    x = t(dur); n = len(x); env = np.zeros(n)
    L = int(0.55/pulse_rate*SR); win = np.hanning(L)
    time = rng.uniform(0, 1/chirp_rate)
    while time < dur:
        for p in range(pulses):
            s = int((time + p/pulse_rate)*SR)
            if s+L < n: env[s:s+L] += win
        time += (1/chirp_rate) * rng.uniform(0.8, 1.25)
        if rng.random() < 0.06: time += rng.uniform(0.5, 2.0)   # occasional pause
    car = np.sin(2*np.pi*carrier*x + 0.4*np.sin(2*np.pi*pulse_rate*x))
    return env*car

def trill(dur, carrier=3900, pulse_rate=60):
    """Tree cricket: continuous trill, breaks every few seconds."""
    x = t(dur); n = len(x)
    gate = (np.sin(2*np.pi*pulse_rate*x) > 0.2).astype(float)
    gate = lowpass(gate, 800)
    on = np.ones(n)
    p = 0.0
    while p < dur:
        p += rng.uniform(2.5, 6.0); q = p + rng.uniform(0.4, 1.5)
        on[int(p*SR):int(min(q, dur)*SR)] = 0
        p = q
    return gate * lowpass(on, 20) * np.sin(2*np.pi*carrier*x)

def groan(dur=10.0, peak_rate=48, sub_f=(38, 29)):
    """Distant deep creak/groan: slow stick-slip impulse train through wooden/metal resonances, plus a sliding sub."""
    x = t(dur); n = len(x)
    shape = np.sin(np.pi*np.clip(x/dur, 0, 1))**1.4
    rate = 9 + (peak_rate-9)*shape
    rate *= 1 + 0.18*lowpass(rng.standard_normal(n), 3)*3
    ph = np.cumsum(np.maximum(rate, 2))/SR
    idx = np.where(np.diff(np.floor(ph)) > 0)[0]
    imp = np.zeros(n); imp[idx] = rng.uniform(0.4, 1.0, len(idx))
    body = np.zeros(n)
    for f, g in ((66, 1.0), (131, 0.7), (205, 0.5), (318, 0.32), (497, 0.18), (780, 0.08)):
        body += bandpass(imp, f*0.965, f*1.035, 2) * g
    body = norm(body, 1.0)
    sub = np.sin(2*np.pi*np.cumsum(sub_f[0] + (sub_f[1]-sub_f[0])*x/dur)/SR)
    y = (body*0.9 + sub*0.5*shape) * env_adsr(n, 2.8, 1.2, 0.75, 3.6)
    return lowpass(y, 1400)

def drip(f=2400):
    x = t(0.5)
    return np.sin(2*np.pi*(f*x - 300*x**0.5)) * np.exp(-x*22) * env_adsr(len(x), 0.006, 0, 1, 0.05)

# ---------------- CUE 2: menu, "The Hall Goes Quiet" ----------------
def menu_cue():
    dur = 124.0; n = int(dur*SR); x = t(dur)
    T_GROAN = 22.0; T_CUT = 23.6; T_RETURN = 92.0
    y = np.zeros(n)

    # night bed: very low wind + faint rumble, present the whole loop so the "silence" is never digital zero
    wind = lowpass(rng.standard_normal(n), 500) * (0.6 + 0.4*np.sin(2*np.pi*0.045*x + 1.0)) * (1 + 0.5*lowpass(rng.standard_normal(n), 0.3)*20)
    y += norm(wind, 1.0) * 0.045
    rumble = np.sin(2*np.pi*31*x) * (0.5 + 0.5*np.sin(2*np.pi*0.07*x))
    after = env_adsr(n, 0.01, 0, 1, 0.01); after[:int(T_GROAN*SR)] = 0.35
    after = lowpass(after, 0.2)
    y += rumble * 0.05 * after

    # crickets: 6 field crickets + 1 trill, each with its own cut time and return time
    crick = np.zeros(n)
    specs = [(4400, 2.2), (4650, 1.9), (4250, 2.6), (4800, 2.0), (4500, 2.4), (4350, 1.7)]
    for i, (car, rate) in enumerate(specs):
        c = cricket(dur, car, rate, pulses=int(rng.integers(3, 5)), pulse_rate=rng.uniform(38, 48))
        act = np.ones(n)
        cut = T_CUT + i*0.18 + rng.uniform(0, 0.12)
        act[int(cut*SR):] = 0
        ret = T_RETURN + i*3.4 + rng.uniform(0, 1.5)
        act[int(ret*SR):] = 1
        act = lowpass(act, 6)                  # ~50 ms edges: they stop mid-chirp, they don't fade
        pan = rng.uniform(0.25, 0.75)
        level = rng.uniform(0.35, 0.7) * (0.5 + 0.5*abs(pan-0.5)*2)  # nearer ones louder
        crick += c * act * level
    tr = trill(dur) * 0.12
    act = np.ones(n); act[int((T_CUT-0.3)*SR):] = 0; act[int((T_RETURN+18)*SR):] = 1
    crick += tr * lowpass(act, 6)
    crick = lowpass(crick, 7000)               # "outside": through walls, a little dull
    crick = reverb(crick, decay=0.8, wet=0.25, tone=6000)
    y += crick * 0.9

    # the groan, far off. rises, crickets stop 1.6 s in, it peaks, dies.
    g = groan(11.0)
    g = reverb(g, decay=5.0, wet=0.6, pre=0.06, tone=1800)
    mix(y, g * 0.75, T_GROAN)
    # a smaller answering creak much later, barely there
    g2 = reverb(groan(6.0, peak_rate=30, sub_f=(34, 30)), decay=4.0, wet=0.6, tone=1500)
    mix(y, g2 * 0.22, 64.0)

    # sparse filler events in the quiet: drips, one wood knock
    for at in (36.5, 47.0, 58.5, 75.0, 83.0):
        mix(y, reverb(drip(rng.uniform(1900, 2800)), 1.5, 0.5) * rng.uniform(0.05, 0.1), at)
    knock = lowpass(big_hit(1.2, 90), 400)
    mix(y, reverb(knock, 2.5, 0.5) * 0.18, 52.0)

    y = highpass(y, 22)
    return norm(seamless(y, 5.0), 0.85)

def stereo(x, width_s=0.012):
    """Circular Haas delay. Never zero-pad: a looped cue must wrap both channels."""
    d = int(width_s * SR)
    return np.stack([x, np.roll(x, d)], 1)

# ---------------- CUE 1 linear (no loop trim) ----------------
def loading_linear(extra=4.0):
    """Hall of the Knight dry-to-wet bed. extra seconds are drone after the last phrase
    so an overlap-add seam has material that is not a choir downbeat or anvil.
    No metered drum — one soft boom per 4-bar phrase only."""
    bpm = 72
    beat = 60 / bpm
    bars = 16
    ph_len = 4 * 4 * beat
    dur = bars * 4 * beat + extra
    y = np.zeros(int(dur * SR))
    mix(y, sub_drone(73.42, dur) * 0.45, 0)          # D2
    mix(y, sub_drone(110.0, dur) * 0.18, 0)          # A2
    mix(y, formant_voice(73.42, dur, "u", att=3.0, rel=3.0, vibd=0.003) * 0.22, 0)
    phrases = [([146.8, 220.0], "o"), ([130.8, 196.0], "u"),
               ([146.8, 174.6], "o"), ([146.8, 220.0, 293.7], "a")]
    for i, (fs, vow) in enumerate(phrases):
        mix(y, choir(fs, ph_len - 0.3, vow) * (0.55 + 0.08 * i), i * ph_len + 0.15)
        mix(y, big_hit() * (0.55 if i else 0.35), i * ph_len)
    mix(y, horn(220.0, 3.2) * 0.26, 1 * ph_len)
    mix(y, horn(293.7, 3.6) * 0.30, 3 * ph_len)
    mix(y, horn(220.0, 2.2) * 0.24, 3 * ph_len + 3 * beat)
    y = reverb(y, decay=3.2, wet=0.4)
    y = highpass(y, 28)
    return y

# ---------------- CUE 1: loading, "Hall of the Knight" v2 ----------------
def loading_cue():
    return norm(seamless(loading_linear(4.0), 4.0))

if __name__ == "__main__":
    print("v2 loading / menu cues are locked reference files.")
    print("Loading loop regen: python3 chant_v3.py")
    print("Menu loop regen:    python3 make_seamless_loop.py (from v8) or menu_v3.py")
