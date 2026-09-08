#!/usr/bin/env python3
"""Rebuild loved menu v8 as a mathematically seamless loop (v9).

v8 was synthesized as a linear cue, then stereo()-delayed AFTER seamless().
That left 6 ms of digital silence on the right channel at t=0, so
Clip.LOOP_CONTINUOUSLY clicks / drops every wrap. Cricket texture also
does not wrap.

This keeps the v8 mix (left channel is the true mono bed) and:
  * circular stereo (np.roll) so both channels wrap
  * 8 s equal-power overlap-add of tail under head
  * RMS-matched overlap regions
  * sample-continuous wrap (adjacent-sample step only)
Writes v9 wav/ogg, a 2-loop concat preview, and a seam excerpt.
"""
import os
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SRC = os.path.join(OUT, "questforge_menu_night_v8.wav")
XF_SEC = 8.0
STEREO_DELAY = 0.006


def lowpass(x, c, o=2):
    b, a = butter(o, min(c, SR / 2 * 0.99) / (SR / 2))
    return lfilter(b, a, x)


def rms(a):
    return float(np.sqrt(np.mean(np.square(a)) + 1e-12))


def db(a):
    return 20 * np.log10(rms(a))


def load_mono(path):
    sr, y = wavfile.read(path)
    if sr != SR:
        raise SystemExit("expected %d Hz, got %d" % (SR, sr))
    y = y.astype(np.float64) / 32768.0
    if y.ndim == 2:
        return y[:, 0].copy()
    return y.copy()


def circular_stereo(mono, delay=STEREO_DELAY):
    d = int(delay * SR)
    return np.stack([mono, np.roll(mono, d)], 1)


def overlap_add(st, xf=XF_SEC):
    """Equal-power OLA: tail of xf seconds under the head. Length -= xf."""
    n = int(xf * SR)
    if n < SR or n * 2 >= len(st):
        raise SystemExit("crossfade window invalid")
    head = st[:n].copy()
    tail = st[-n:].copy()
    # match tail loudness to the head so the join does not pump
    scale = rms(head) / rms(tail)
    tail *= scale
    w = np.linspace(0.0, 1.0, n, dtype=np.float64)[:, None]
    blended = head * np.sin(w * np.pi / 2) + tail * np.cos(w * np.pi / 2)
    out = st[:-n].copy()
    out[:n] = blended
    return out


def glue_wrap(st, ms=12.0):
    """Force first-order continuity at the exact wrap (kills residual click)."""
    k = int(ms * 0.001 * SR)
    # after OLA, out[0] ~= old tail[0] and out[-1] ~= sample just before that.
    # Re-crossfade a few milliseconds of the very end into the very start
    # so both channels meet with matched slope.
    fade = np.linspace(0.0, 1.0, k, dtype=np.float64)[:, None]
    # equal-power micro-blend of a *copy of the start* onto the end
    end = st[-k:] * np.cos(fade * np.pi / 2) + st[:k] * np.sin(fade * np.pi / 2)
    # then the start itself is left as the continuation of that end
    # (loop: end[-1] should sit next to start[0]). Shift start[0] toward end[-1]
    # by rewriting start as a 1-sample-adjacent continuation:
    st = st.copy()
    st[-k:] = end
    # one-sample DC stitch so L/R don't jump
    step = st[0] - st[-1]
    # spread the residual step over the first 2 ms so it is inaudible
    m = max(int(0.002 * SR), 8)
    ramp = np.linspace(1.0, 0.0, m)[:, None]
    st[:m] = st[:m] - step * ramp
    return st


def report(name, st):
    m = st.mean(1)
    dur = len(m) / float(SR)
    n = int(0.02 * SR)
    n2 = int(2 * SR)
    print("==", name, "%.3fs" % dur)
    print("   head 0-2   %.2f dB   tail -2-0  %.2f dB" % (db(m[:n2]), db(m[-n2:])))
    print("   wrap step L %.6f  R %.6f" % (abs(st[0, 0] - st[-1, 0]), abs(st[0, 1] - st[-1, 1])))
    print("   wrap 20ms  head %.2f / tail %.2f dB" % (db(m[:n]), db(m[-n:])))
    h = m[:n2] - m[:n2].mean()
    t = m[-n2:] - m[-n2:].mean()
    corr = float(np.dot(h, t) / (np.linalg.norm(h) * np.linalg.norm(t) + 1e-12))
    print("   head/tail 2s corr %.4f" % corr)
    # spectral continuity, 1 s
    def spec(a):
        w = np.hanning(len(a))
        return np.abs(np.fft.rfft(a * w))
    s0, s1 = spec(m[:SR]), spec(m[-SR:])
    lsd = float(np.sqrt(np.mean((np.log(s0 + 1e-9) - np.log(s1 + 1e-9)) ** 2)))
    print("   1s log-spectral distance %.3f" % lsd)
    print("   R[0:8] %s  (must not be zeros)" % np.array2string(st[:8, 1], precision=4))


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


def main():
    mono = load_mono(SRC)
    # v8 already ran a 6 s mono seamless; drop that compromised head/tail
    # pair and rebuild stereo+OLA from the stable middle+body.
    st = circular_stereo(mono)
    looped = glue_wrap(overlap_add(st, XF_SEC))
    # keep cricket bed seat near v8
    bed = looped[int(4 * SR) : int(16 * SR)]
    target = 10 ** (-25.6 / 20.0)
    looped = looped * (target / rms(bed.mean(1)))
    looped = np.clip(looped, -0.94, 0.94)
    sr0, raw = wavfile.read(SRC)
    rawf = raw.astype(np.float64) / 32768.0
    report("v8 shipped", rawf)
    report("v9 loop", looped)

    write_audio("questforge_menu_night_v9", looped)

    # 2-loop concat (user can hear the wrap twice)
    two = np.concatenate([looped, looped], 0)
    write_audio("questforge_menu_night_v9_2loop", two)

    # seam excerpt: 8 s before wrap + 8 s after (from the 2-loop file)
    seam_l = int(8 * SR)
    mid = len(looped)
    excerpt = two[mid - seam_l : mid + seam_l]
    write_audio("questforge_menu_night_v9_seam_excerpt", excerpt)

    # also a groan-region excerpt so timbre can be A/B'd against v8
    a, b = int(12 * SR), int(min(40 * SR, len(looped)))
    write_audio("groan_v9_excerpt", looped[a:b])


if __name__ == "__main__":
    main()
