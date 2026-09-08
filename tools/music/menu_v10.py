#!/usr/bin/env python3
"""Quest Forge menu v10: night-arriving swell in front of loved v9.

v9 is the seamless 132 s cricket / groan / drone loop. This does not remix
the groan. It prepends a 4-6 s swell built from v9's own cricket + air + a
whisper of the later drone, then trims the same duration out of the
pre-groan cricket bed (after the wrap-sensitive head) so title-start →
groan stays on the v9 clock.

File layout:
    [swell 5.0 s] + [loopable body]
Body keeps v9[0] and v9[-1] so the wrap is the original sample-continuous
join. Clip.setLoopPoints(swellEnd, end) skips the swell on later loops.

Writes:
    out/questforge_menu_night_v10.wav / .ogg
    out/questforge_menu_night_v10_swell_excerpt.ogg
    out/questforge_menu_night_v10_groan_timing_excerpt.ogg
    out/questforge_handoff_mock.ogg
    out/questforge_menu_night_v10_seam_excerpt.ogg
"""
import os
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
V9 = os.path.join(OUT, "questforge_menu_night_v9.wav")
CHANT = os.path.join(OUT, "questforge_loading_chant_v3.wav")

SWELL_SEC = 5.0
TRIM_SEC = 5.0
KEEP_HEAD = 2.5
JOIN_XF = 1.0
SWELL_ARRIVE = 0.90
GLUE_MS = 12.0

# v9 measured 2026-09-04: 20-80 Hz peak at 24.25 s, broadband ~24.5 s
V9_GROAN_PEAK = 24.25


def lowpass(x, c, o=2):
    b, a = butter(o, min(c, SR / 2 * 0.99) / (SR / 2))
    if x.ndim == 2:
        return np.stack([lfilter(b, a, x[:, ch]) for ch in range(x.shape[1])], 1)
    return lfilter(b, a, x)


def highpass(x, c, o=2):
    b, a = butter(o, c / (SR / 2), btype="high")
    if x.ndim == 2:
        return np.stack([lfilter(b, a, x[:, ch]) for ch in range(x.shape[1])], 1)
    return lfilter(b, a, x)


def bandpass(x, lo, hi, o=2):
    b, a = butter(o, [lo / (SR / 2), min(hi, SR / 2 * 0.99) / (SR / 2)], btype="band")
    if x.ndim == 2:
        return np.stack([lfilter(b, a, x[:, ch]) for ch in range(x.shape[1])], 1)
    return lfilter(b, a, x)


def rms(a):
    return float(np.sqrt(np.mean(np.square(a)) + 1e-12))


def db(a):
    return 20.0 * np.log10(rms(a) + 1e-12)


def load_st(path):
    sr, y = wavfile.read(path)
    if sr != SR:
        raise SystemExit("%s: expected %d Hz, got %d" % (path, SR, sr))
    y = y.astype(np.float64) / 32768.0
    if y.ndim == 1:
        y = np.stack([y, y], 1)
    return y


def cosine(n):
    return 0.5 - 0.5 * np.cos(np.pi * np.linspace(0.0, 1.0, n))


def write_audio(name, y):
    wav = os.path.join(OUT, name + ".wav")
    ogg = os.path.join(OUT, name + ".ogg")
    pcm = np.clip(y, -1.0, 1.0)
    wavfile.write(wav, SR, (pcm * 32767.0).astype(np.int16))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5", ogg],
        check=True,
    )
    print("wrote", name, "%.2fs" % (len(y) / float(SR)))
    return wav


def report(name, st):
    m = st.mean(1)
    print("==", name, "%.3fs" % (len(m) / float(SR)))
    print("   head 0-2   %.2f dB   tail -2-0  %.2f dB" % (db(m[: 2 * SR]), db(m[-2 * SR :])))
    print("   wrap step L %.6f  R %.6f" % (abs(st[0, 0] - st[-1, 0]), abs(st[0, 1] - st[-1, 1])))


def groan_peak_time(st):
    """20-80 Hz RMS peak, 0.5 s window, 0.25 s hop, first 45 s."""
    m = st.mean(1)
    low = bandpass(m, 20, 80)
    win = int(0.5 * SR)
    best_t, best_v = 0.0, -999.0
    t = 0.0
    while t < min(45.0, len(m) / float(SR) - 0.5):
        i = int(t * SR)
        v = db(low[i : i + win])
        if v > best_v:
            best_v, best_t = v, t
        t += 0.25
    return best_t, best_v


def take_loop(src, n, start):
    """Circular slice so a 5 s swell can be longer than a source window."""
    out = np.zeros((n, src.shape[1]), dtype=np.float64)
    L = len(src)
    for i in range(n):
        out[i] = src[(start + i) % L]
    return out


def build_swell(v9, n, body_head):
    """Night arriving: air, then distant cricket density, then the bed.

    All material is v9. No synth riser, no whoosh.
    """
    cricket = v9[int(9.0 * SR) : int(18.0 * SR)]
    drone = v9[int(48.0 * SR) : int(62.0 * SR)]

    field = take_loop(cricket, n, int(0.4 * SR))
    air = lowpass(field, 160, 2) * 0.85
    room = bandpass(field, 180, 1100, 2) * 0.28
    far = lowpass(highpass(field, 1400, 2), 2600, 2)
    # slightly later cricket layer = density coming in, not a new sound
    near = take_loop(cricket, n, int(2.8 * SR))
    rumble = lowpass(take_loop(drone, n, int(1.0 * SR)), 70, 2) * 0.32

    # cosine is too slow in the first second (still ~0.02 at 0.4 s).
    # Night should already be in the air when the choir starts fading.
    p_lin = np.linspace(0.0, 1.0, n)
    p = 0.5 - 0.5 * np.cos(np.pi * np.power(p_lin, 0.62))
    e_air = 0.70 + 0.30 * np.power(p, 0.40)
    e_far = 0.28 + 0.72 * np.power(p, 0.75)
    e_near = np.power(p, 1.45)
    e_drone = 0.28 + 0.72 * np.power(p, 1.05)
    gate = 0.16 + 0.84 * np.power(p, 0.85)
    hush = air + far * 0.35
    hush = hush * (10.0 ** (-48.0 / 20.0) / max(rms(hush), 1e-9))

    swell = (
        air * e_air[:, None]
        + room * (e_air * 0.85)[:, None]
        + far * (0.70 * e_far)[:, None]
        + near * (0.95 * e_near)[:, None]
        + rumble * e_drone[:, None]
    )
    swell *= gate[:, None]
    swell = swell + hush

    # last SWELL_ARRIVE seconds already sit at body-head loudness
    arrive = int(SWELL_ARRIVE * SR)
    head = body_head[:arrive]
    # match swell tail RMS to the head we are walking into
    tail = swell[-arrive:]
    scale = rms(head) / max(rms(tail), 1e-9)
    # only lift the last second; keep the rise shape
    w = np.sin(np.linspace(0.0, np.pi / 2, arrive))[:, None]
    swell[-arrive:] = tail * (1.0 + (scale - 1.0) * w)

    # equal-power last 40 ms into a *copy* of the body head (inaudible as a repeat)
    k = int(0.040 * SR)
    fade = np.linspace(0.0, 1.0, k, dtype=np.float64)[:, None]
    swell[-k:] = swell[-k:] * np.cos(fade * np.pi / 2) + body_head[:k] * np.sin(fade * np.pi / 2)
    return swell


def trim_body(v9):
    """Drop TRIM_SEC of pre-groan cricket after KEEP_HEAD. Preserve wrap samples."""
    keep = int(KEEP_HEAD * SR)
    trim = int(TRIM_SEC * SR)
    xf = int(JOIN_XF * SR)
    a0 = keep
    a1 = keep + xf
    b0 = keep + trim
    b1 = keep + trim + xf
    if b1 >= len(v9) or a1 >= b0:
        raise SystemExit("trim window overlaps groan or wrap")
    head = v9[:keep]
    left = v9[a0:a1].copy()
    right = v9[b0:b1].copy()
    scale = rms(left) / max(rms(right), 1e-9)
    right *= scale
    w = np.linspace(0.0, 1.0, xf, dtype=np.float64)[:, None]
    blended = left * np.cos(w * np.pi / 2) + right * np.sin(w * np.pi / 2)
    tail = v9[b1:]
    body = np.concatenate([head, blended, tail], 0)
    return body


def glue_splice(left, right):
    """12 ms equal-power + 2 ms step spread at left|right. Returns (left, right)."""
    k = int(GLUE_MS * 0.001 * SR)
    fade = np.linspace(0.0, 1.0, k, dtype=np.float64)[:, None]
    left = left.copy()
    right = right.copy()
    left[-k:] = left[-k:] * np.cos(fade * np.pi / 2) + right[:k] * np.sin(fade * np.pi / 2)
    step = right[0] - left[-1]
    m = max(int(0.002 * SR), 8)
    ramp = np.linspace(1.0, 0.0, m)[:, None]
    right[:m] = right[:m] - step * ramp
    return left, right


def handoff_mock(v10, chant):
    """Last ~4 s of chant from mid-file, faded under first ~6 s of menu swell."""
    # mid-file, not the seam. Includes a distant anvil (22.84 / 25.31) under the fade.
    c0 = int(22.6 * SR)
    c1 = c0 + int(4.0 * SR)
    chant_ex = chant[c0:c1].copy()
    menu_ex = v10[: int(6.0 * SR)].copy()
    n = len(chant_ex)
    hold = int(0.55 * SR)
    fade_n = n - hold
    g = np.ones(n)
    g[hold:] = np.cos(np.linspace(0.0, np.pi / 2, fade_n))
    # in-game: splash MASTER_GAIN -6 dB, menu -3 dB
    chant_ex *= (10.0 ** (-6.0 / 20.0)) * g[:, None]
    menu_ex *= 10.0 ** (-3.0 / 20.0)
    out = menu_ex.copy()
    out[:n] += chant_ex
    peak = np.max(np.abs(out))
    if peak > 0.94:
        out *= 0.94 / peak
    return out


def main():
    v9 = load_st(V9)
    chant = load_st(CHANT)
    v9_peak, v9_peak_db = groan_peak_time(v9)
    print("v9 duration %.3fs  groan-peak %.2fs (%.2f dB 20-80Hz)" % (len(v9) / float(SR), v9_peak, v9_peak_db))
    print("v9 wrap step L %.6f R %.6f" % (abs(v9[0, 0] - v9[-1, 0]), abs(v9[0, 1] - v9[-1, 1])))

    body = trim_body(v9)
    swell_n = int(SWELL_SEC * SR)
    swell = build_swell(v9, swell_n, body[: int(1.2 * SR)])
    swell, body = glue_splice(swell, body)
    v10 = np.concatenate([swell, body], 0)
    v10 = np.clip(v10, -0.94, 0.94)

    v10_peak, v10_peak_db = groan_peak_time(v10)
    print("SWELL_SEC %.2f  TRIM_SEC %.2f  KEEP_HEAD %.2f  body %.3fs" % (
        SWELL_SEC, TRIM_SEC, KEEP_HEAD, len(body) / float(SR)))
    print("v10 duration %.3fs  groan-peak %.2fs (%.2f dB)  delta vs v9 %+.2fs" % (
        len(v10) / float(SR), v10_peak, v10_peak_db, v10_peak - v9_peak))
    report("v10 full (wrap is BODY, not file[0])", body)
    report("v10 file (starts on swell; do not loop this)", v10)

    # swell head levels
    m = v10.mean(1)
    print("swell 0-0.4s %.2f dB   2-3s %.2f dB   4-5s %.2f dB   body 5-7s %.2f dB" % (
        db(m[: int(0.4 * SR)]),
        db(m[int(2 * SR) : int(3 * SR)]),
        db(m[int(4 * SR) : int(5 * SR)]),
        db(m[int(5 * SR) : int(7 * SR)]),
    ))

    write_audio("questforge_menu_night_v10", v10)

    swell_ex = v10[: int((SWELL_SEC + 15.0) * SR)]
    write_audio("questforge_menu_night_v10_swell_excerpt", swell_ex)

    groan_ex = v10[: int(min(len(v10), (v10_peak + 8.0) * SR))]
    write_audio("questforge_menu_night_v10_groan_timing_excerpt", groan_ex)

    two = np.concatenate([body, body], 0)
    mid = len(body)
    seam_l = int(8 * SR)
    write_audio("questforge_menu_night_v10_seam_excerpt", two[mid - seam_l : mid + seam_l])

    write_audio("questforge_handoff_mock", handoff_mock(v10, chant))

    # sidecar so Java comments stay honest
    with open(os.path.join(OUT, "questforge_menu_night_v10.swellsec"), "w") as f:
        f.write("%.3f\n" % SWELL_SEC)
    print("SWELL_END_FRAME", swell_n, "at", SR, "Hz")
    print("DONE")


if __name__ == "__main__":
    main()
