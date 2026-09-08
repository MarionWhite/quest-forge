#!/usr/bin/env python3
"""Quest Forge main-menu cue: "The Hall Goes Quiet" (v4 renderer).

v3 (loved): real CC0 cricket field, distant 6-mode stick-slip groan that silences
them, then the v1 dread drone fills the night. Seamless loop, crickets return.

v4: same scene and the same groan TIMBRE, made more intense. The late-quiet-build
and the 12-mode "filled" groan were both rejected; this restores the 14 s mid-peak
narrow-mode creak and puts intensity on top of it (more body, mild sat, octave
layer). Writes out/questforge_menu_night_v4.* — does not overwrite v3.

Timeline of the ~140 s loop:
    0-18   real crickets, full
   18      the groan begins, far off and very low (already speaking, all six modes)
   20.5    the field goes silent, staggered across three frequency bands over ~0.6 s
   18-32   groan climbs, peaks ~25 s, decays into a long reverb tail
   30-95   dread drone: sub swell, tritone pad, breathing, impacts at 46/68/88 s, unresolved F5 at 60 s
   95-120  drone recedes
  112-140  crickets return, quiet and dull first, then full -> seam
"""
import os, subprocess, numpy as np
from numpy.random import default_rng
from scipy.signal import butter, lfilter, fftconvolve
from scipy.io import wavfile

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SRC = os.path.join(HERE, "src", "crickets_freesound_746366_CC0.mp3")
os.makedirs(OUT, exist_ok=True)
rng = default_rng(23)

def t(sec): return np.arange(int(sec*SR))/SR
def env_adsr(n, a, d, s, r):
    e = np.ones(n); A=int(a*SR); D=int(d*SR); R=int(r*SR)
    if A: e[:A] = np.linspace(0,1,A)
    if D: e[A:A+D] = np.linspace(1,s,D)
    e[A+D:n-R] = s
    if R: e[n-R:] = np.linspace(s,0,R)
    return e
def lowpass(x,c,o=2):  b,a=butter(o,min(c,SR/2*0.99)/(SR/2)); return lfilter(b,a,x)
def highpass(x,c,o=2): b,a=butter(o,c/(SR/2),btype="high"); return lfilter(b,a,x)
def bandpass(x,lo,hi,o=2): b,a=butter(o,[lo/(SR/2),min(hi,SR/2*0.99)/(SR/2)],btype="band"); return lfilter(b,a,x)
def reverb(x, decay=3.0, wet=0.4, pre=0.02, tone=3000):
    n=int(decay*SR); ir=rng.standard_normal(n)*np.exp(-np.arange(n)/(decay*SR/6))
    ir=lowpass(ir,tone); ir[:int(pre*SR)]=0; ir/=np.abs(ir).sum()**0.5
    y=fftconvolve(x,ir)[:len(x)]
    return (1-wet)*x + wet*y/(np.max(np.abs(y))+1e-9)*np.max(np.abs(x))
def mix(dst,src,at):
    i=int(at*SR); n=min(len(src),len(dst)-i)
    if n>0: dst[i:i+n]+=src[:n]
def norm(x,p=0.89): return x/(np.max(np.abs(x))+1e-9)*p
def seamless(y,xf=6.0):
    n=int(xf*SR); w=np.linspace(0,1,n)
    head=y[:n]*np.sin(w*np.pi/2)+y[-n:]*np.cos(w*np.pi/2)
    out=y[:-n].copy(); out[:n]=head; return out

# ---------------- real crickets ----------------
def load_crickets(dur):
    """Decode the CC0 recording to mono and tile it to `dur` with crossfades so there is no obvious repeat."""
    raw = subprocess.run(["ffmpeg","-v","quiet","-i",SRC,"-ac","1","-ar",str(SR),"-f","f32le","-"],
                         capture_output=True).stdout
    c = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    c = c[int(0.5*SR):-int(0.5*SR)]                       # trim head/tail
    c = highpass(c, 180)                                  # lose the recording's low rumble; we supply our own bed
    xf = int(1.5*SR); need = int(dur*SR); L = len(c)
    if L <= xf*2:
        raise SystemExit("cricket source too short to tile")
    out = np.zeros(need)
    fade_in = np.linspace(0, 1, xf); fade_out = np.linspace(1, 0, xf)
    hop = L - xf                                          # each copy starts one crossfade before the last ends
    pos = 0
    while pos < need:
        seg = c.copy()
        if pos > 0:                                       # crossfade this copy's head under the previous tail
            k = min(xf, need-pos)
            seg[:xf] *= fade_in
            out[pos:pos+k] *= fade_out[:k]
        n = min(L, need-pos)
        out[pos:pos+n] += seg[:n]
        pos += hop                                        # strictly positive, so this always terminates
    return norm(out, 1.0)

def band_gate(x, cut_at, ret_at, edge=0.09):
    """Gate a signal on/off with short (not instant) edges."""
    n = len(x); g = np.ones(n)
    g[int(cut_at*SR):] = 0
    if ret_at is not None and ret_at*SR < n: g[int(ret_at*SR):] = 1
    return x * lowpass(g, 1.0/edge)

# ---------------- the groan: loved v3 timbre, then intensified ----------------
# The hollow-v3 creak they called beautiful is this instrument:
#   six narrow stick-slip modes at 41/78/122/190/300/470 Hz (skirts ±4.5 %),
#   sliding sub 34 -> 21 Hz with an octave-down growl, 900 Hz roof, 14 s sine envelope
#   that peaks in the MIDDLE (so it is already present when the crickets cut).
#
# Failed turns, do not repeat:
#   * 12-mode / wide-skirt / constant grain "fill" -- flattened the notches, sounded like a rumble
#   * late 20 s climb, mode-entry gates, shape**0.45 duck -- made it more distant and quieter
#
# Intensity is a build ON TOP of that same instrument, not a new one:
#   more energy in the existing body toward the climax, mild saturation growth,
#   a quieter octave-of-body layer (same creak, half the resonances). No new bright texture,
#   no extra reverb, no material-noise bed.
MODES = ((41,1.0),(78,0.85),(122,0.6),(190,0.4),(300,0.22),(470,0.1))

def groan(dur=14.0, peak_rate=46, sub=(34.0, 21.0), res=MODES):
    x = t(dur); n = len(x); p = np.clip(x/dur, 0, 1)
    # steeper mid-peak: distant at the start (~30% at the cut), huge at the middle
    shape = np.sin(np.pi * p)**1.85
    shape = lowpass(shape, 6)

    rate = 6 + (peak_rate-6)*shape
    rate = rate * (1 + 0.18*lowpass(rng.standard_normal(n), 3)*3)
    ph = np.cumsum(np.maximum(rate, 1.5))/SR
    idx = np.where(np.diff(np.floor(ph))>0)[0]
    imp = np.zeros(n); imp[idx] = rng.uniform(0.35, 1.0, len(idx))

    # all six modes speak from the start -- the notches ARE the creak
    body = np.zeros(n)
    for f, g in res:
        body += bandpass(imp, f*0.955, f*1.045, 2) * g
    body = norm(body, 1.0)

    # quieter octave-of-body: same impulse train, half-frequency modes. Fullness, not a new texture.
    body_oct = np.zeros(n)
    for f, g in res:
        body_oct += bandpass(imp, (f*0.5)*0.955, (f*0.5)*1.045, 2) * g
    body_oct = norm(body_oct, 1.0)

    f_inst = sub[0] + (sub[1]-sub[0])*p
    # heavier sub stack (felt <80 Hz): fundamental, half, and a slow quarter-weight growl
    low = (np.sin(2*np.pi*np.cumsum(f_inst)/SR)
           + np.sin(2*np.pi*np.cumsum(f_inst/2)/SR)*0.90
           + np.sin(2*np.pi*np.cumsum(np.maximum(f_inst/3, 18.0))/SR)*0.40) * shape

    # same creak mix, bass-weighted — sub stays in the instrument, not a close dry layer
    core = body*0.82 + body_oct*0.36 + low*1.15
    bass = lowpass(core, 72, 2)
    core = core + bass * (0.15 + 1.25*shape**1.7)
    drive = 1.0 + 0.42*shape                              # mild; v6's 1.25 fried the top
    core = np.tanh(core * drive) / np.tanh(1.0 + 0.42)
    presence = 0.62 + 1.85*shape**1.75                    # still escalates hard
    y = core * presence * env_adsr(n, 1.8, 0.5, 0.90, 3.0)
    return lowpass(y, 720)                                # darker roof than v6's 900 Hz

def kaiju(dur=14.0):
    """Distant giant-creature voice: pitched throat moan, not more earthquake.

    Glottal pulses through moving animal formants, sliding down like a call.
    Highpassed so it sits above the v7 rumble instead of thickening it.
    """
    x = t(dur); n = len(x); p = np.clip(x/dur, 0, 1)
    shape = np.sin(np.pi * p)**1.85
    shape = lowpass(shape, 6)
    # 68 -> 41 Hz moan (creature chest, above the 21–34 Hz quake)
    f0 = 68.0 - 27.0*p**0.85 + 3.5*np.sin(2*np.pi*p*1.25)
    f0 = f0 * (1 + 0.014*np.sin(2*np.pi*4.6*x) + 0.03*lowpass(rng.standard_normal(n), 2.5)*3)
    ph = np.cumsum(np.maximum(f0, 28.0))/SR
    idx = np.where(np.diff(np.floor(ph))>0)[0]
    glott = np.zeros(n)
    pw = int(0.005*SR); pulse = np.hanning(max(pw, 8))
    for i in idx:
        if i+len(pulse) < n:
            glott[i:i+len(pulse)] += pulse * rng.uniform(0.65, 1.0)
    # two dark animal vowels, morph aw -> oh with the swell (full-length filters, no hops)
    aw = (bandpass(glott, 220, 340, 2)*1.00
          + bandpass(glott, 500, 700, 2)*0.55
          + bandpass(glott, 900, 1150, 2)*0.16)
    oh = (bandpass(glott, 280, 420, 2)*1.00
          + bandpass(glott, 620, 840, 2)*0.50
          + bandpass(glott, 1000, 1280, 2)*0.14)
    voice = aw*(1.0 - 0.55*shape) + oh*(0.45 + 0.55*shape)
    rasp = bandpass(rng.standard_normal(n), 180, 850, 2)
    breath = lowpass(np.abs(lowpass(glott, 12)), 5); breath /= breath.max()+1e-9
    voice = voice + rasp*(0.10 + 0.08*breath)*shape
    # two-breath phrasing so it reads as a call, not a pad
    phrase = 0.50 + 0.50*np.sin(2*np.pi*p*1.12 + 0.35)**2
    y = voice * shape * phrase * env_adsr(n, 2.0, 0.5, 0.90, 3.2)
    y = np.tanh(norm(y, 1.0)*1.12)
    return lowpass(highpass(y, 85), 1350)

# ---------------- the dread drone (from v1) ----------------
def dread(dur):
    x = t(dur); n = len(x); y = np.zeros(n)
    # beating sub around E1
    y += (np.sin(2*np.pi*41.2*x) + np.sin(2*np.pi*41.7*x)) * 0.33
    # tritone pad E2 + Bb2 + low B, slow filter drift
    def pad(f, amp):
        ph = 2*np.pi*f*x; s = np.zeros(n)
        for k in range(1,30): s += np.sin(k*ph + rng.uniform(0,6))/k
        return s*amp
    p = pad(82.4,0.5) + pad(116.5,0.35) + pad(61.7,0.25)
    cut = 380 + 260*np.sin(2*np.pi*0.018*x)
    filt = np.zeros(n); ch = SR
    for i in range(0,n,ch): filt[i:i+ch] = lowpass(p[i:i+ch], float(cut[i]))
    y += filt*0.4
    y *= 1 + 0.13*np.sin(2*np.pi*x/9.0)          # breathing
    return y

def impact(dur=4.0, f=36):
    x = t(dur)
    return lowpass(np.sin(2*np.pi*(f*x + 20*np.exp(-x*5)))*np.exp(-x*1.4), 260) * env_adsr(len(x),0.02,0.1,1.0,1.2)

# ---------------- build ----------------
def build(preview=False):
    DUR = 42.0 if preview else 146.0
    T_GROAN, T_CUT, T_RETURN = 18.0, 20.5, 112.0
    n = int(DUR*SR); x = t(DUR); y = np.zeros(n)

    # --- crickets, band-staggered cut and return ---
    c = load_crickets(DUR)
    bands = [(180, 3200, 0.00), (3200, 6500, 0.28), (6500, 20000, 0.55)]
    crick = np.zeros(n)
    for lo, hi, lag in bands:
        b = bandpass(c, lo, hi, 2)
        crick += band_gate(b, T_CUT+lag, None)
    # the return: quiet and dull first, opening up over ~20 s
    ret = np.zeros(n)
    for lo, hi, lag in bands:
        b = bandpass(c, lo, hi, 2)
        g = np.zeros(n); g[int((T_RETURN+lag*14)*SR):] = 1
        ret += b * lowpass(g, 0.12)
    open_env = np.clip((x-T_RETURN)/22.0, 0, 1)**1.6
    crick = crick + ret*open_env
    crick = reverb(crick, decay=0.7, wet=0.18, tone=7000)
    y += crick*1.00

    # --- distant huge groan: wetter/darker air, bass bloom through reverb (no dry close layer) ---
    g_src = groan(14.0)
    g_amb = reverb(g_src, decay=7.4, wet=0.74, pre=0.11, tone=820)
    swell = np.sin(np.pi * np.clip(np.arange(len(g_src))/max(len(g_src)-1, 1), 0, 1))**1.8
    sub = lowpass(g_src, 68, 2)
    sub_amb = reverb(sub, decay=8.2, wet=0.84, pre=0.16, tone=380)
    g = g_amb + sub_amb * swell * 0.90                     # felt bass, still far off
    mix(y, g*0.68, T_GROAN)

    # kaiju throat on TOP of the unchanged v7 quake — distant, pitched, not more rumble
    k = reverb(kaiju(14.0), decay=6.8, wet=0.70, pre=0.13, tone=1500)
    mix(y, k*0.55, T_GROAN)

    if not preview:
        # --- the dread drone taking over AFTER the groan peak, not under it ---
        d_start, d_len = 31.5, 90.5
        d = dread(d_len)
        d *= env_adsr(len(d), 16.0, 0, 1.0, 26.0)     # slow swell in, long recede
        mix(y, reverb(d, decay=4.5, wet=0.42, tone=2200)*0.20, d_start)
        for at in (46.0, 68.0, 88.0):
            mix(y, reverb(impact(), 5.0, 0.55, tone=1400)*0.22, at)
        # one high note that never resolves (F5 over the E minor bed)
        ln = 11.0
        mix(y, np.sin(2*np.pi*698.5*t(ln))*env_adsr(int(ln*SR),5,0,1,5)*0.045, 60.0)

    y = highpass(y, 16)                  # keep the sub swell; just kill DC
    if not preview:
        y = seamless(y, 6.0)
    return y

def norm_to_bed(y, target_db=-25.6, thresh=0.90, ceil=0.94, t0=4.0, t1=16.0):
    """Keep the cricket bed at the v4 seat. Soft knee only — no hard fry."""
    m = y.mean(1) if y.ndim > 1 else y
    s = m[int(t0*SR):int(t1*SR)]
    cur = 20*np.log10(np.sqrt(np.mean(s**2))+1e-12)
    y = y * (10**((target_db - cur)/20.0))
    a = np.abs(y)
    over = a > thresh
    if np.any(over):
        knee = max(1e-9, ceil - thresh)
        mag = np.where(over, thresh + knee * np.tanh((a-thresh)/(knee*2.2)), a)
        y = np.sign(y) * mag
    return y

def stereo(x, w=0.006):
    """Circular delay so a looped cue does not start the right channel on zeros."""
    d = int(w*SR)
    r = np.roll(x, d)
    return np.stack([x, r], 1)

def write_audio(name, y):
    wav = os.path.join(OUT, name+".wav")
    wavfile.write(wav, SR, (np.clip(y,-1,1)*32767).astype(np.int16))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav,
                    "-c:a","libvorbis","-q:a","5",os.path.join(OUT,name+".ogg")], check=True)
    print("wrote", name, f"{len(y)/SR:.1f}s")

def report_levels(y):
    """y is stereo float. Print cricket / groan / drone RMS so we can A/B against loved v3 (~+9 dB)."""
    m = y.mean(1) if y.ndim > 1 else y
    dur = len(m)/SR
    def rms(a, b):
        s = m[int(a*SR):int(min(b, dur)*SR)]
        if len(s) < SR*0.2: return float("nan")
        return 20*np.log10(np.sqrt(np.mean(s**2))+1e-12)
    cricket = rms(4, 16)
    start = rms(18, 20)
    peak_end = min(32.0, dur-2)
    best = max((rms(t, t+2), t) for t in np.arange(20.0, peak_end, 0.5))
    hole = rms(21, 23)
    print(f"crickets  4-16 s   {cricket:6.1f} dB")
    print(f"groan start 18-20  {start:6.1f} dB   ({start-cricket:+.1f} vs crickets)")
    print(f"post-cut 21-23 s   {hole:6.1f} dB   ({hole-cricket:+.1f} vs crickets)")
    print(f"groan climax       {best[0]:6.1f} dB   ({best[0]-cricket:+.1f} vs crickets) @ {best[1]:.1f}-{best[1]+2:.1f} s")
    if dur > 75:
        drone = rms(55, 75)
        print(f"drone    55-75 s   {drone:6.1f} dB   ({drone-cricket:+.1f} vs crickets)")
        n = int(0.02*SR)
        print(f"seam step          {abs(m[0]-m[-1]):.4f}   head/tail {rms(0,0.02):.1f}/{20*np.log10(np.sqrt(np.mean(m[-n:]**2))+1e-12):.1f} dB")

if __name__ == "__main__":
    import sys
    preview = "--preview" in sys.argv
    y = norm_to_bed(stereo(build(preview=preview)))
    if preview:
        write_audio("groan_v4_preview", y)
        report_levels(y)
    else:
        write_audio("questforge_menu_night_v8", y)
        # 12-40 s: crickets, the cut, the whole groan, fall into the drone
        a, b = int(12*SR), int(40*SR)
        write_audio("groan_v8_excerpt", y[a:b])
        report_levels(y)
