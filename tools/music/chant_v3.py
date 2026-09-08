#!/usr/bin/env python3
"""Quest Forge loading chant v3: v2 mix, cleaner seam, distant anvil.

v2 seam problems (installed splash.wav is 32 kHz mono of the stereo master):
  * synth.stereo() zero-padded 12 ms of silence on the right after seamless()
  * downmix then made wrap step ~0.016 (first sample L/2, last sample (L+R)/2)
  * 4 s OLA, no RMS match, modest head/tail spectral jump (LSD ~1.08 vs mid ~0.89)

v3 keeps the v2 choir/drone/horn/boom recipe (seed 11, extra=4 linear, then a
phase-continuous drone tail so an 8 s overlap-add has non-choir material).
Adds a far-off forge: real CC0 steel strikes (Duasun, freesound 321889) with
a modal ring extension so they sing in the hall, placed irregularly and kept
off the wrap. Circular stereo, 8 s equal-power RMS-matched OLA, micro-glue.

No metered drum. No zero-pad delay. Regen: python3 chant_v3.py
"""
import os
import subprocess
import numpy as np
from numpy.random import default_rng
from scipy.io import wavfile
from scipy.signal import butter, lfilter, fftconvolve, find_peaks

import synth

SR = synth.SR
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SRC = os.path.join(HERE, "src")
DUASUN = os.path.join(SRC, "fs_duasun_321889.mp3")
V2_WAV = os.path.join(OUT, "questforge_loading_chant_v2.wav")
XF_SEC = 8.0
STEREO_DELAY = 0.012
os.makedirs(OUT, exist_ok=True)

# Final-loop hit times (seconds). Irregular, off the 72 bpm grid, off the wrap.
# Cluster at 22.8 / 25.3 reads as a smith working, then a long rest.
ANVIL_HITS = (11.18, 22.84, 25.31, 37.62)
ANVIL_GAIN = 0.175          # vs chant mid-phrase RMS; sit beside, not on, the voices
ANVIL_SOURCE_TIMES = (10.90, 17.69, 14.43, 5.25)  # Duasun isolated rings

arn = default_rng(42)


def lowpass(x, c, o=2, rng_ok=True):
    b, a = butter(o, min(c, SR / 2 * 0.99) / (SR / 2))
    return lfilter(b, a, x)


def highpass(x, c, o=2):
    b, a = butter(o, c / (SR / 2), btype="high")
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


def reverb(x, decay=4.8, wet=0.70, pre=0.055, tone=2000, rng=arn):
    n = int(decay * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (decay * SR / 6.2))
    ir = lowpass(ir, tone)
    ir[: int(pre * SR)] = 0
    ir /= np.abs(ir).sum() ** 0.5
    y = fftconvolve(x, ir)[: len(x)]
    peak = np.max(np.abs(x)) + 1e-9
    return (1 - wet) * x + wet * y / (np.max(np.abs(y)) + 1e-9) * peak


def circular_stereo(mono, delay=STEREO_DELAY):
    d = int(delay * SR)
    return np.stack([mono, np.roll(mono, d)], 1)


def overlap_add(st, xf=XF_SEC):
    n = int(xf * SR)
    if n < SR or n * 2 >= len(st):
        raise SystemExit("crossfade window invalid")
    head = st[:n].copy()
    tail = st[-n:].copy()
    # clip — a quiet drone tail must not be pumped up to a choir head
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
    if st.ndim == 1:
        st2 = np.stack([st, st], 1)
    else:
        st2 = st
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


# ---------------- v2-identical linear + drone tail ----------------
def continue_drones(t0, extra):
    """Phase-continuous D2/A2 bed from synth.sub_drone, starting at time t0."""
    x = t0 + np.arange(int(extra * SR)) / float(SR)

    def one(f, wobble=0.06):
        return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2 * x + 0.2 * np.sin(2 * np.pi * wobble * x))) * 0.6

    return one(73.42) * 0.45 + one(110.0) * 0.18


def loading_linear_extended(extra_tail=4.0):
    """v2 linear (57.333 s, seed 11) plus extra drone so 8 s OLA does not eat a phrase."""
    synth.rng = default_rng(11)
    linear = synth.loading_linear(4.0)          # 53.333 + 4 of original extra
    t0 = len(linear) / float(SR)
    ext = continue_drones(t0, extra_tail + 0.8)
    ext = reverb(ext, decay=3.2, wet=0.40, pre=0.02, tone=4000, rng=arn)
    ext = highpass(ext, 28)
    # match the last second of the v2 linear so the join does not step
    join = int(0.8 * SR)
    scale = rms(linear[-join:]) / rms(ext[:join])
    ext *= scale
    fade = np.linspace(1.0, 0.0, join)
    linear = np.concatenate([linear[:-join], linear[-join:] * fade + ext[:join] * (1.0 - fade), ext[join:]])
    return linear


# ---------------- distant anvil (real strike + modal ring) ----------------
def extract_hit(src, t, pre=0.016, post=1.70):
    i = int(t * SR)
    a = max(0, i - int(pre * SR))
    b = min(len(src), i + int(post * SR))
    h = src[a:b].copy()
    fi = min(int(0.010 * SR), len(h) // 10)
    fo = min(int(0.22 * SR), len(h) // 4)
    h[:fi] *= np.linspace(0, 1, fi)
    h[-fo:] *= np.linspace(1, 0, fo)
    return h


def fit_modes(hit, n_modes=15):
    a = int(0.048 * SR)
    b = min(len(hit), int(0.62 * SR))
    seg = hit[a:b]
    if len(seg) < int(0.15 * SR):
        return [(1962, 1.0, 2.1), (2961, 0.85, 1.6), (3670, 0.45, 1.2), (168, 0.7, 0.4)]
    s = spec(seg)
    freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
    df = freqs[1] if len(freqs) > 1 else 1.0
    pks, _ = find_peaks(s, distance=max(5, int(28.0 / df)), prominence=s.max() * 0.035)
    cands = [(freqs[k], s[k]) for k in pks if 110.0 < freqs[k] < 7000.0]
    cands.sort(key=lambda z: -z[1])
    modes = []
    for f, amp in cands:
        if any(abs(f - f0) < 28.0 for f0, _, _ in modes):
            continue
        if f < 350:
            tau = 0.50
        elif f < 2200:
            tau = 2.55 * (1700.0 / f) ** 0.42
        else:
            tau = 1.05 * (3200.0 / f) ** 0.80
        modes.append((f, amp, tau))
        if len(modes) >= n_modes:
            break
    # always a bit of anvil body under the ping (recordings are close/bright)
    for f, amp, tau in ((92.0, 0.55, 0.22), (168.0, 0.70, 0.38), (246.0, 0.40, 0.28), (412.0, 0.28, 0.55)):
        if not any(abs(f - f0) < 20.0 for f0, _, _ in modes):
            modes.append((f, amp * (cands[0][1] if cands else 1.0) * 0.35, tau))
    return modes


def modal_ring(modes, dur, rng, hardness=1.0):
    n = int(dur * SR)
    x = np.arange(n) / float(SR)
    y = np.zeros(n)
    mx = max(a for _, a, _ in modes) or 1.0
    for f, amp, tau in modes:
        f = f * (1.0 + rng.uniform(-0.0028, 0.0028))
        tau = tau * rng.uniform(0.88, 1.14)
        f_inst = f * (1.0 + 0.010 * hardness * np.exp(-x * 85.0))
        ph = 2.0 * np.pi * np.cumsum(f_inst) / SR
        beat = 1.0 + 0.07 * np.sin(2.0 * np.pi * rng.uniform(0.6, 2.6) * x + rng.uniform(0, 6))
        y += (amp / mx) * np.sin(ph + rng.uniform(0, 6)) * np.exp(-x / max(tau, 0.08)) * beat
    return y


def body_thud(rng, dur=0.48):
    x = np.arange(int(dur * SR)) / float(SR)
    f = 76.0 + 42.0 * np.exp(-x * 26.0)
    y = np.sin(2.0 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 8.5)
    y += 0.40 * np.sin(2.0 * np.pi * np.cumsum(f * 1.68) / SR) * np.exp(-x * 13.0)
    noise = lowpass(rng.standard_normal(len(x)), 580) * np.exp(-x * 20.0)
    return lowpass(y + 0.30 * noise, 360)


def make_distant_strike(hit, rng, hardness=1.0, far=1.0):
    """Real steel attack, modal tail after the recorded ring dies, hall air.

    The close-mic hit is the strike. Modal synthesis only continues the ring
    so it can sing across the keep — it must not out-shout the hammer.
    """
    n = int(4.2 * SR)
    core = np.zeros(n)
    core[: len(hit)] += hit
    thud = body_thud(rng)
    core[: len(thud)] += thud * (0.18 * hardness)

    modes = fit_modes(hit)
    ring = modal_ring(modes, 3.7, rng, hardness)
    splice = min(int(0.72 * SR), max(len(hit) - int(0.18 * SR), int(0.40 * SR)))
    ref = hit[splice : min(len(hit), splice + int(0.10 * SR))]
    if len(ref) < 64:
        ref = hit[-int(0.12 * SR) :]
    ring *= 0.90 * rms(ref) / (rms(ring[: max(len(ref), 64)]) + 1e-12)
    xf = int(0.40 * SR)
    w = np.zeros(n)
    w[splice : splice + xf] = np.linspace(0.0, 1.0, xf)
    w[splice + xf :] = 1.0
    core[: len(ring)] += ring * w[: len(ring)]

    y = highpass(core, 70)
    air = 3480.0 - 820.0 * far
    y = lowpass(y, air, 2)
    y = lowpass(y, min(air * 0.78, 2800.0), 1)
    er = np.zeros_like(y)
    d1 = int(rng.uniform(0.020, 0.030) * SR)
    d2 = int(rng.uniform(0.044, 0.062) * SR)
    if d1 < len(y):
        er[d1:] += y[:-d1] * 0.12
    if d2 < len(y):
        er[d2:] += y[:-d2] * 0.07
    y = y + er

    wet_only = reverb(y, decay=4.4 + 1.0 * far, wet=1.0,
                      pre=0.050 + 0.030 * far, tone=2050.0 - 380.0 * far, rng=rng)
    mix_w = 0.52 + 0.14 * far
    dry = y
    y = (1.0 - mix_w) * dry + mix_w * wet_only
    # put the hammer tick back on top so distance does not turn this into a pad
    att = int(0.11 * SR)
    y[:att] += dry[:att] * (0.40 * (1.15 - 0.25 * far))
    y *= 0.50 / (np.max(np.abs(y)) + 1e-9)
    return y


def build_anvil_hits():
    src = load_mono(DUASUN)
    hits = []
    for i, t in enumerate(ANVIL_SOURCE_TIMES):
        raw = extract_hit(src, t)
        hardness = (0.82, 1.05, 0.90, 0.75)[i]
        far = (1.05, 0.88, 1.12, 1.20)[i]
        hits.append(make_distant_strike(raw, arn, hardness=hardness, far=far))
    return hits


def mix_anvils(mono, hits, times, gain):
    y = mono.copy()
    chant_seat = rms(mono[int(8 * SR) : int(16 * SR)])
    placed = []
    for hit, t in zip(hits, times):
        # keep a little off-center in time already; scale each strike to chant seat
        target = chant_seat * gain
        # measure the first 80 ms of the distant strike (the audible ping)
        att = hit[: int(0.12 * SR)]
        hit = hit * (target / (rms(att) + 1e-12))
        i = int(t * SR)
        n = min(len(hit), len(y) - i)
        if n > 0:
            y[i : i + n] += hit[:n]
            placed.append((t, db(hit[: int(0.12 * SR)]), db(hit)))
    return y, placed


# ---------------- build ----------------
def loop_from_mono(mono):
    st = circular_stereo(mono)
    return glue_wrap(overlap_add(st, XF_SEC))


def match_v2_seat(looped, v2):
    """Keep the mid-phrase chant at the approved v2 loudness."""
    a, b = int(8 * SR), int(16 * SR)
    v2m = v2.mean(1) if v2.ndim == 2 else v2
    target = rms(v2m[a:b])
    cur = rms(looped[a:b].mean(1))
    return looped * (target / cur)


def anvil_vs_chant(looped, times):
    m = looped.mean(1)
    print("-- anvil vs chant (0.6 s windows) --")
    for t in times:
        i = int(t * SR)
        win = m[i : i + int(0.60 * SR)]
        pre = m[max(0, i - int(0.60 * SR)) : i]
        print("   @%5.2fs  hit %.2f dB   pre %.2f dB   delta %+.2f dB" % (t, db(win), db(pre), db(win) - db(pre)))


def v2_as_float():
    sr, y = wavfile.read(V2_WAV)
    if sr != SR:
        raise SystemExit("v2 sr %d" % sr)
    return y.astype(np.float64) / 32768.0


def main():
    v2 = v2_as_float()
    write_audio("questforge_loading_chant_v2_seam_excerpt",
                np.concatenate([v2[-int(8 * SR) :], v2[: int(8 * SR)]], 0))

    linear = loading_linear_extended(4.0)
    print("linear extended %.3fs (want ~61.333)" % (len(linear) / float(SR)))

    hits = build_anvil_hits()
    # isolated anvil excerpt: four distant rings, ~3.6 s apart, no chant
    iso = np.zeros(int(16.5 * SR))
    for i, h in enumerate(hits):
        at = 0.6 + i * 3.85
        n = min(len(h), len(iso) - int(at * SR))
        iso[int(at * SR) : int(at * SR) + n] += h[:n] * 1.35
    write_audio("anvil_v3_excerpt", circular_stereo(iso * (0.72 / (np.max(np.abs(iso)) + 1e-9))))

    mixed, placed = mix_anvils(linear, hits, ANVIL_HITS, ANVIL_GAIN)
    print("placed anvils:", ", ".join("%.2fs" % t for t, _, _ in placed))

    looped = match_v2_seat(loop_from_mono(mixed), v2)
    looped = np.clip(looped, -0.94, 0.94)

    # seam-only control (same loop math, no anvil) so we can A/B the wrap
    seam_only = match_v2_seat(loop_from_mono(linear), v2)
    seam_only = np.clip(seam_only, -0.94, 0.94)

    report("v2 shipped", v2)
    report("v3 seam-only (no anvil)", seam_only)
    report("v3 loop", looped)
    anvil_vs_chant(looped, ANVIL_HITS)

    # do not sit an anvil on the wrap
    for t in ANVIL_HITS:
        if t < XF_SEC + 2.0 or t > (len(looped) / float(SR) - XF_SEC - 2.0):
            print("WARNING anvil at %.2f is too close to the seam" % t)

    write_audio("questforge_loading_chant_v3", looped)
    two = np.concatenate([looped, looped], 0)
    write_audio("questforge_loading_chant_v3_2loop", two)
    mid = len(looped)
    write_audio("questforge_loading_chant_v3_seam_excerpt", two[mid - int(8 * SR) : mid + int(8 * SR)])
    # mixed context: first anvil in the bed (~20 s)
    a, b = int(8.5 * SR), int(31.5 * SR)
    write_audio("questforge_loading_chant_v3_anvil_context", looped[a:b])


if __name__ == "__main__":
    main()
