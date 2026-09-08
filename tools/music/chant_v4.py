#!/usr/bin/env python3
"""Quest Forge loading chant v4: approved v3 chant bed, rebuilt anvil stem.

v3's anvil (Duasun 321889 + modal sines + body thud + dull wet hall) failed a
firmer listen: the ring was ~90% energy below 200 Hz, attack smeared to ~22 ms,
and the steel tick/ping did not survive. A real hammered anvil is a hard
broadband TICK/CLANG (a few ms) then an inharmonic 1.5–4 kHz ping with beating,
not a 100 Hz sine thud or a church-bell oscillator bank.

v4 keeps the v3 choir/drone/horn recipe and the same circular-stereo / 8 s
RMS-clipped OLA / micro-glue seam. Only the anvil layer is replaced.

Source: BigSoundBank #3589 "Anvil #1" by Pablo BERGEL, CC0 — a working
blacksmith, hammer on iron on one anvil. Hits are the same instrument at
different velocities. No modal resynthesis. No synthetic body thud.

Distance: air absorption (ping stays, air-hiss rolls off), a brighter stone
hall excited by the recorded strike, dry attack put back on top.

No metered drum. Regen: python3 chant_v4.py
"""
import os
import subprocess
import numpy as np
from numpy.random import default_rng
from scipy.io import wavfile
from scipy.signal import butter, lfilter, fftconvolve

import synth

SR = synth.SR
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SRC = os.path.join(HERE, "src")
BSB3589 = os.path.join(SRC, "anvil_bsb3589.flac")
V2_WAV = os.path.join(OUT, "questforge_loading_chant_v2.wav")
XF_SEC = 8.0
STEREO_DELAY = 0.012
os.makedirs(OUT, exist_ok=True)

# True steel onsets in BSB 3589 (HF-onset detector, not ring-tail triggers).
BSB_STEEL = (
    0.139, 1.352, 2.427, 3.633, 3.939, 4.957, 6.012, 7.080, 8.013, 8.326,
    9.197, 10.515, 11.642, 13.058, 13.531, 14.038, 14.523, 15.036, 15.815,
    16.601, 17.139, 17.591, 18.086, 18.572, 19.403, 20.091, 20.894, 21.631,
    21.937, 22.416, 23.252, 24.106, 24.986, 25.748, 26.030, 26.478, 27.024,
    27.981, 28.324, 28.984, 29.707, 30.621,
)

# Final-loop times. Irregular, off the 72 bpm grid, off the wrap.
# Cluster 22.84 / 23.17 / 25.40 reads as a smith (heavy, light, then another).
ANVIL_HITS = (11.18, 22.84, 23.17, 25.40, 37.58)
# source time, velocity, distance (0 = closer, 1 = farther across the keep)
ANVIL_VOICES = (
    (7.080, 0.92, 1.05),   # single medium-heavy
    (0.139, 1.08, 0.88),   # cluster heavy — best isolated face strike
    (26.030, 0.76, 0.96),  # cluster light, ~330 ms later (hard tap, not a soft mallet)
    (23.252, 0.94, 1.00),  # cluster follow after a breath
    (21.937, 0.64, 1.18),  # far lighter single, long rest
)
ANVIL_GAIN = 0.132  # vs chant mid-phrase RMS; steel band pokes, overall RMS barely moves

arn = default_rng(42)


def lowpass(x, c, o=2):
    b, a = butter(o, min(c, SR / 2 * 0.99) / (SR / 2))
    return lfilter(b, a, x)


def highpass(x, c, o=2):
    b, a = butter(o, c / (SR / 2), btype="high")
    return lfilter(b, a, x)


def bandpass(x, lo, hi, o=2):
    b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return lfilter(b, a, x)


def rms(a):
    return float(np.sqrt(np.mean(np.square(a)) + 1e-12))


def db(a):
    return 20.0 * np.log10(rms(a))


def load_mono(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def fft_gain(x, gain_fn):
    n = len(x)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    spec *= gain_fn(freqs)
    return np.fft.irfft(spec, n).astype(np.float64)


def air_absorb(x, strength=1.0):
    """Indoor-distance air: keep 1.5–4 kHz ping, roll the hiss above ~6 kHz."""
    def g(f):
        # ~−1.2 dB at 2.5 kHz, ~−6 dB at 8 kHz, ~−12 dB at 12 kHz when strength=1
        att = strength * (0.12 * (np.maximum(f, 1.0) / 1000.0) ** 1.55)
        return np.power(10.0, -att / 20.0)
    return fft_gain(x, g)


def peaking(x, freq, gain_db, q=0.8):
    def g(f):
        w = ((f - freq) / (freq / max(q, 0.1)))
        return np.power(10.0, (gain_db / 20.0) * np.exp(-0.5 * w * w))
    return fft_gain(x, g)


def stone_hall(x, decay=2.55, pre=0.024, tone=4600, rng=arn):
    """Brighter, shorter keep. IR is highpassed so it cannot mint a thud."""
    n = int(decay * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (decay * SR / 5.4))
    ir = highpass(ir, 220)
    ir = lowpass(ir, tone)
    ir[: int(pre * SR)] = 0
    ir /= np.abs(ir).sum() ** 0.5
    y = fftconvolve(x, ir)[: len(x)]
    peak = np.max(np.abs(x)) + 1e-9
    return y / (np.max(np.abs(y)) + 1e-9) * peak


def early_reflections(x, rng, far=1.0):
    er = np.zeros_like(x)
    taps = (
        (0.018 + 0.004 * far, 0.13, 900),
        (0.027 + 0.006 * far, 0.09, 1200),
        (0.041 + 0.008 * far, 0.07, 1000),
        (0.058 + 0.010 * far, 0.045, 1500),
    )
    for delay, att, hp in taps:
        d = int((delay + rng.uniform(-0.0015, 0.0015)) * SR)
        if 0 < d < len(x):
            er[d:] += highpass(x[:-d], hp) * att
    return er


def circular_stereo(mono, delay=STEREO_DELAY):
    d = int(delay * SR)
    return np.stack([mono, np.roll(mono, d)], 1)


def overlap_add(st, xf=XF_SEC):
    n = int(xf * SR)
    if n < SR or n * 2 >= len(st):
        raise SystemExit("crossfade window invalid")
    head = st[:n].copy()
    tail = st[-n:].copy()
    tail *= float(np.clip(rms(head) / rms(tail), 0.90, 1.08))
    w = np.linspace(0.0, 1.0, n, dtype=np.float64)[:, None]
    blended = head * np.sin(w * np.pi / 2) + tail * np.cos(w * np.pi / 2)
    out = st[:-n].copy()
    out[:n] = blended
    return out


def glue_wrap(st, ms=12.0):
    k = int(ms * 0.001 * SR)
    fade = np.linspace(0.0, 1.0, k, dtype=np.float64)[:, None]
    st = st.copy()
    st[-k:] = st[-k:] * np.cos(fade * np.pi / 2) + st[:k] * np.sin(fade * np.pi / 2)
    step = st[0] - st[-1]
    m = max(int(0.002 * SR), 8)
    ramp = np.linspace(1.0, 0.0, m)[:, None]
    st[:m] = st[:m] - step * ramp
    return st


def spec(a):
    w = np.hanning(len(a))
    return np.abs(np.fft.rfft(a * w))


def report(name, st):
    m = st.mean(1) if st.ndim == 2 else st
    st2 = np.stack([st, st], 1) if st.ndim == 1 else st
    dur = len(m) / float(SR)
    n = int(0.02 * SR)
    n2 = int(2 * SR)
    print("==", name, "%.3fs" % dur)
    print("   head 0-2   %.2f dB   tail -2-0  %.2f dB" % (db(m[:n2]), db(m[-n2:])))
    print("   wrap step L %.6f  R %.6f" % (abs(st2[0, 0] - st2[-1, 0]), abs(st2[0, 1] - st2[-1, 1])))
    print("   wrap 20ms  head %.2f / tail %.2f dB" % (db(m[:n]), db(m[-n:])))
    h = m[:n2] - m[:n2].mean()
    t = m[-n2:] - m[-n2:].mean()
    corr = float(np.dot(h, t) / (np.linalg.norm(h) * np.linalg.norm(t) + 1e-12))
    print("   head/tail 2s corr %.4f" % corr)
    s0, s1 = spec(m[:SR]), spec(m[-SR:])
    lsd = float(np.sqrt(np.mean((np.log(s0 + 1e-9) - np.log(s1 + 1e-9)) ** 2)))
    print("   1s log-spectral distance %.3f" % lsd)
    mid = int(min(20, dur / 2) * SR)
    if mid + 2 * SR < len(m):
        sm0, sm1 = spec(m[mid : mid + SR]), spec(m[mid + SR : mid + 2 * SR])
        lsd_mid = float(np.sqrt(np.mean((np.log(sm0 + 1e-9) - np.log(sm1 + 1e-9)) ** 2)))
        print("   mid-file adjacent 1s LSD %.3f" % lsd_mid)
    print("   R[0:8] %s" % np.array2string(st2[:8, 1], precision=4))
    z = 0
    while z < min(len(st2), 2000) and abs(st2[z, 1]) < 1e-8:
        z += 1
    print("   R leading near-zeros: %d samples (%.2f ms)" % (z, 1000.0 * z / SR))


def write_audio(name, y):
    wav = os.path.join(OUT, name + ".wav")
    pcm = np.clip(y, -1.0, 1.0)
    wavfile.write(wav, SR, (pcm * 32767.0).astype(np.int16))
    ogg = os.path.join(OUT, name + ".ogg")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5", ogg],
        check=True,
    )
    print("wrote", name, "%.1fs" % (len(y) / float(SR)))
    return wav


# ---------------- v3-identical chant bed ----------------
def continue_drones(t0, extra):
    x = t0 + np.arange(int(extra * SR)) / float(SR)

    def one(f, wobble=0.06):
        return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2 * x + 0.2 * np.sin(2 * np.pi * wobble * x))) * 0.6

    return one(73.42) * 0.45 + one(110.0) * 0.18


def loading_linear_extended(extra_tail=4.0):
    synth.rng = default_rng(11)
    linear = synth.loading_linear(4.0)
    t0 = len(linear) / float(SR)
    ext = continue_drones(t0, extra_tail + 0.8)
    # same reverb call shape as v3 (uses module rng)
    n = int(3.2 * SR)
    ir = arn.standard_normal(n) * np.exp(-np.arange(n) / (3.2 * SR / 6.2))
    ir = lowpass(ir, 4000)
    ir[: int(0.02 * SR)] = 0
    ir /= np.abs(ir).sum() ** 0.5
    wet = fftconvolve(ext, ir)[: len(ext)]
    peak = np.max(np.abs(ext)) + 1e-9
    ext = 0.60 * ext + 0.40 * wet / (np.max(np.abs(wet)) + 1e-9) * peak
    ext = highpass(ext, 28)
    join = int(0.8 * SR)
    scale = rms(linear[-join:]) / rms(ext[:join])
    ext *= scale
    fade = np.linspace(1.0, 0.0, join)
    linear = np.concatenate([linear[:-join], linear[-join:] * fade + ext[:join] * (1.0 - fade), ext[join:]])
    return linear


# ---------------- anvil: recorded steel, no sines ----------------
def extract_hit(src, t, steel_times=BSB_STEEL, pre=0.010, post_cap=1.15):
    nxt = min((u for u in steel_times if u > t + 0.05), default=t + post_cap)
    post = min(post_cap, max(0.38, nxt - t - 0.014))
    i = int(t * SR)
    a = max(0, i - int(pre * SR))
    b = min(len(src), i + int(post * SR))
    h = src[a:b].copy()
    fi = min(int(0.002 * SR), len(h) // 16)
    fo = min(int(0.16 * SR), len(h) // 3)
    if fi:
        h[:fi] *= np.linspace(0, 1, fi)
    if fo:
        h[-fo:] *= np.linspace(1, 0, fo)
    return h


def make_distant_strike(hit, rng, vel=1.0, far=1.0):
    """Recording stays the strike. Hall is excited by that strike, not by a sine bank.

    Level is normalized here; mix_anvils re-applies per-hit velocity so a light
    tap stays a light tap.
    """
    n = int(2.35 * SR)
    dry = np.zeros(n)
    dry[: len(hit)] += hit
    # Don't let a 1 s leftover 2.5 kHz line become a UI ding; the real ping is in
    # the first half-second. Hall finishes the rest.
    fade_at = int(0.48 * SR)
    if fade_at < n:
        fade_n = n - fade_at
        dry[fade_at:] *= np.exp(-np.arange(fade_n) / (0.22 * SR))

    # Air first — distance must not turn this into a pad or a thud.
    air = air_absorb(dry, strength=0.80 + 0.35 * far)
    air = peaking(air, 2520.0, 1.35 - 0.25 * far, q=0.55)
    air = highpass(air, 90)

    # Hall sings the steel band of the first 80 ms (tick + emerging ping).
    exciter = np.zeros(n)
    take = min(len(hit), int(0.080 * SR))
    exciter[:take] = bandpass(dry[:take], 850, 6800)
    hall = stone_hall(air_absorb(exciter, strength=0.50 + 0.22 * far),
                      decay=1.45 + 0.35 * far,
                      pre=0.020 + 0.010 * far,
                      tone=5000.0 - 500.0 * far,
                      rng=rng)
    hall = highpass(hall, 320)

    er = early_reflections(air, rng, far)

    wet_amt = 0.22 + 0.08 * far
    y = (1.0 - wet_amt) * air + wet_amt * hall + er * (0.50 + 0.12 * far)

    # Hammer-mass stock: short 180–750 Hz from the recording, not a 100 Hz sine.
    stock_n = min(int(0.038 * SR), len(hit))
    stock = bandpass(dry[:stock_n], 180, 750) * (0.22 + 0.04 * vel)
    y[:stock_n] += stock

    # Put the hammer face back on top. First ~8 ms fully dry; fade by 48 ms.
    att = int(0.048 * SR)
    fade = np.linspace(1.0, 0.0, att) ** 0.70
    y[:att] = y[:att] * (1.0 - 0.78 * fade) + dry[:att] * (0.86 * fade)

    tick = highpass(dry[: int(0.012 * SR)], 4000)
    y[: len(tick)] += tick * (0.62 * (1.12 - 0.22 * far))

    y = highpass(y, 70)
    y *= 0.52 / (np.max(np.abs(y)) + 1e-9)
    return y


def build_anvil_hits():
    src = load_mono(BSB3589)
    hits = []
    for t, vel, far in ANVIL_VOICES:
        raw = extract_hit(src, t)
        hits.append((make_distant_strike(raw, arn, vel=vel, far=far), raw, vel, far, t))
    return hits


def mix_anvils(mono, distant_hits, times, vels, gain):
    y = mono.copy()
    chant_seat = rms(mono[int(8 * SR) : int(16 * SR)])
    placed = []
    for hit, t, vel in zip(distant_hits, times, vels):
        att = hit[: int(0.10 * SR)]
        hit = hit * ((chant_seat * gain * vel) / (rms(att) + 1e-12))
        i = int(t * SR)
        n = min(len(hit), len(y) - i)
        if n > 0:
            y[i : i + n] += hit[:n]
            placed.append((t, db(hit[: int(0.10 * SR)]), db(hit)))
    return y, placed


def loop_from_mono(mono):
    return glue_wrap(overlap_add(circular_stereo(mono), XF_SEC))


def match_v2_seat(looped, v2):
    a, b = int(8 * SR), int(16 * SR)
    v2m = v2.mean(1) if v2.ndim == 2 else v2
    target = rms(v2m[a:b])
    cur = rms(looped[a:b].mean(1))
    return looped * (target / cur)


def band_rms(x, lo, hi):
    return rms(bandpass(x, lo, hi))


def anvil_vs_chant(looped, times):
    m = looped.mean(1)
    print("-- anvil vs chant (0.6 s windows) --")
    for t in times:
        i = int(t * SR)
        win = m[i : i + int(0.60 * SR)]
        pre = m[max(0, i - int(0.60 * SR)) : i]
        print("   @%5.2fs  hit %.2f dB   pre %.2f dB   delta %+.2f dB   steel1.5-4k %+0.2f dB" % (
            t, db(win), db(pre), db(win) - db(pre),
            db(bandpass(win, 1500, 4000)) - db(bandpass(pre, 1500, 4000)),
        ))


def judge_hit(name, y):
    """Concrete gates vs a real hammered anvil (see module docstring)."""
    early = y[: int(0.025 * SR)]
    ring = y[int(0.060 * SR) : int(0.40 * SR)]
    env = np.abs(y[: int(0.030 * SR)])
    k = max(1, int(0.0004 * SR))
    env = np.convolve(env, np.ones(k) / k, mode="same")
    pk = env.max()
    att = 1000.0 * (np.argmax(env >= 0.90 * pk) - np.argmax(env >= 0.10 * pk)) / SR

    def be(seg, lo, hi):
        w = np.hanning(len(seg))
        mag = np.abs(np.fft.rfft(seg * w))
        f = np.fft.rfftfreq(len(seg), 1.0 / SR)
        p = mag ** 2
        return float(np.sum(p[(f >= lo) & (f < hi)]) / (np.sum(p) + 1e-18))

    e_hf, e_ping, e_sub = be(early, 4000, 12000), be(early, 1500, 4000), be(early, 20, 200)
    r_ping, r_sub = be(ring, 1500, 4000), be(ring, 20, 200)
    freqs = np.fft.rfftfreq(len(ring), 1.0 / SR)
    mag = np.abs(np.fft.rfft(ring * np.hanning(len(ring))))
    p = float(np.sum(freqs * mag ** 2) / (np.sum(mag ** 2) + 1e-18))
    print("   %s  att=%.2fms  eHF=%.2f ePing=%.2f eSub=%.2f  rPing=%.2f rSub=%.2f  ringC=%.0fHz" % (
        name, att, e_hf, e_ping, e_sub, r_ping, r_sub, p))
    ok = att < 6.0 and e_sub < 0.12 and r_sub < 0.18 and r_ping > 0.45 and p > 1400 and e_hf > 0.12
    if not ok:
        print("   WARNING: failed hammer-on-anvil gate")
    return ok


def v2_as_float():
    sr, y = wavfile.read(V2_WAV)
    if sr != SR:
        raise SystemExit("v2 sr %d" % sr)
    return y.astype(np.float64) / 32768.0


def write_spectrograms(distant, dry_hits):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("no spectrograms:", e)
        return
    v3p = os.path.join(OUT, "anvil_v3_excerpt.wav")
    refp = os.path.join(SRC, "_ref", "benboncan_103629.mp3")
    pairs = [("v4_distant", distant[:, 0] if distant.ndim == 2 else distant)]
    if os.path.exists(v3p):
        pairs.insert(0, ("v3_distant", load_mono(v3p)))
    if os.path.exists(refp):
        pairs.append(("benboncan_large_anvil_ref", load_mono(refp)))
    if dry_hits:
        d = np.zeros(int(3.2 * SR))
        d[: min(len(dry_hits[0]), len(d))] += dry_hits[0][: min(len(dry_hits[0]), len(d))]
        if len(dry_hits) > 1:
            at = int(1.55 * SR)
            n = min(len(dry_hits[1]), len(d) - at)
            d[at : at + n] += dry_hits[1][:n]
        pairs.append(("v4_dry_close", d))
    fig, axes = plt.subplots(len(pairs), 1, figsize=(12, 2.55 * len(pairs)), sharex=False)
    if len(pairs) == 1:
        axes = [axes]
    for ax, (name, x) in zip(axes, pairs):
        n = min(len(x), int(8.0 * SR) if "v4_distant" in name or "v3" in name else int(3.2 * SR))
        ax.specgram(x[:n], NFFT=1024, Fs=SR, noverlap=768, cmap="magma", vmin=-110, vmax=-30)
        ax.set_ylim(0, 8000)
        ax.set_ylabel("Hz")
        ax.set_title(name)
    axes[-1].set_xlabel("s")
    fig.tight_layout()
    png = os.path.join(OUT, "anvil_v4_vs_refs.spec.png")
    fig.savefig(png, dpi=120)
    plt.close(fig)
    print("wrote", png)

    # first-hit zoom: v3 vs v4 vs real large anvil
    zooms = []
    if os.path.exists(v3p):
        zooms.append(("v3 first hit (0.55–2.2s)", load_mono(v3p)[int(0.50 * SR) : int(2.20 * SR)]))
    zooms.append(("v4 first hit (0.50–2.2s)", distant[int(0.50 * SR) : int(2.20 * SR)]))
    if os.path.exists(refp):
        zooms.append(("Benboncan 103629 large anvil (CC BY, ref only)", load_mono(refp)))
    fig, axes = plt.subplots(len(zooms), 1, figsize=(10, 2.4 * len(zooms)))
    if len(zooms) == 1:
        axes = [axes]
    for ax, (name, x) in zip(axes, zooms):
        ax.specgram(x, NFFT=1024, Fs=SR, noverlap=768, cmap="magma", vmin=-110, vmax=-30)
        ax.set_ylim(0, 8000)
        ax.set_ylabel("Hz")
        ax.set_title(name)
    axes[-1].set_xlabel("s")
    fig.tight_layout()
    png2 = os.path.join(OUT, "anvil_v4_firsthit_vs_refs.spec.png")
    fig.savefig(png2, dpi=120)
    plt.close(fig)
    print("wrote", png2)


def main():
    v2 = v2_as_float()
    linear = loading_linear_extended(4.0)
    print("linear extended %.3fs (want ~61.333)" % (len(linear) / float(SR)))

    built = build_anvil_hits()
    distant = [b[0] for b in built]
    raws = [b[1] for b in built]

    print("-- v4 isolated-hit gates (want att<6ms, eSub<0.12, rPing>0.45, ringC>1400) --")
    ok = True
    for i, d in enumerate(distant):
        ok = judge_hit("hit%d@%.2f" % (i, ANVIL_HITS[i]), d) and ok

    # isolated distant rings, no chant — keep heavy/light velocity
    iso = np.zeros(int(18.5 * SR))
    for i, (h, _raw, vel, _far, _t) in enumerate(built):
        at = 0.55 + i * 3.55
        n = min(len(h), len(iso) - int(at * SR))
        iso[int(at * SR) : int(at * SR) + n] += h[:n] * vel
    iso *= 0.78 / (np.max(np.abs(iso)) + 1e-9)
    write_audio("anvil_v4_excerpt", circular_stereo(iso))

    # closer/drier: two raw BSB strikes (heavy 0.139, light 8.326) so the timbre is audible
    dry = np.zeros(int(3.6 * SR))
    for raw, at, g in ((raws[1], 0.25, 0.62), (raws[2], 1.85, 0.50)):
        n = min(len(raw), len(dry) - int(at * SR))
        dry[int(at * SR) : int(at * SR) + n] += raw[:n] * g
    dry *= 0.84 / (np.max(np.abs(dry)) + 1e-9)
    write_audio("anvil_v4_dry_close", circular_stereo(dry))

    vels = [v[1] for v in ANVIL_VOICES]
    mixed, placed = mix_anvils(linear, distant, ANVIL_HITS, vels, ANVIL_GAIN)
    print("placed anvils:", ", ".join("%.2fs" % t for t, _, _ in placed))

    looped = np.clip(match_v2_seat(loop_from_mono(mixed), v2), -0.94, 0.94)
    seam_only = np.clip(match_v2_seat(loop_from_mono(linear), v2), -0.94, 0.94)

    report("v3-identical seam-only (no anvil)", seam_only)
    report("v4 loop", looped)
    anvil_vs_chant(looped, ANVIL_HITS)

    loop_dur = len(looped) / float(SR)
    for t in ANVIL_HITS:
        if t < XF_SEC + 2.0 or t > (loop_dur - XF_SEC - 2.0):
            print("WARNING anvil at %.2f is too close to the seam" % t)

    write_audio("questforge_loading_chant_v4", looped)
    two = np.concatenate([looped, looped], 0)
    write_audio("questforge_loading_chant_v4_2loop", two)
    mid = len(looped)
    write_audio("questforge_loading_chant_v4_seam_excerpt", two[mid - int(8 * SR) : mid + int(8 * SR)])
    # ~23 s of chant with the working cluster in bed
    a, b = int(8.5 * SR), int(31.5 * SR)
    write_audio("questforge_loading_chant_v4_anvil_context", looped[a:b])

    write_spectrograms(iso, [raws[1], raws[2]])
    if not ok:
        print("GATES FAILED — do not install over v3 splash")
    else:
        print("GATES PASSED — isolated stem is spectrally a hammered anvil")


if __name__ == "__main__":
    main()
