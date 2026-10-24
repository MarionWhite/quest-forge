"""Generate the shader pack's data textures (shaders/QuestForge/shaders/textures/).

    py -3.10 -I tools/shaders/make_textures.py [--milkyway C:/qfb/milkyway/dl/eso0932a.jpg]

qf_waves.png  256x256 RGB, tileable. A static ocean height field built from a wave spectrum
              (inverse FFT of random phases under a Phillips-like power law, J. Tessendorf,
              "Simulating Ocean Water", 2001): R, G the slope dh/dx, dh/dy (0.5 = flat), B the
              height. lib/water.glsl layers it at several scales and angles.
qf_noise.png  256x256 RGBA, tileable. R white noise, G = R shifted by 37 texels along x (one fetch
              per 3D value-noise lookup: I. Quilez's "noise with a 2D texture" trick), B a smooth
              4-octave fbm, A cellular edges (Worley F2 - F1) for caustics and foam.
qf_milkyway.png  (with --milkyway) the ESO/S. Brunier Milky Way panorama (CC BY 4.0), galactic
              latitude -45..+45 deg, with the point stars taken out (the pack draws its own), the
              sky background subtracted and the result resized. Credit in LICENSES/README.md.
Each texture gets a .mcmeta asking for linear filtering and wrapping.
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "shaders", "QuestForge", "shaders", "textures")
N = 256


def mcmeta(name, clamp=False):
    with open(os.path.join(OUT, name + ".mcmeta"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"texture": {"blur": True, "clamp": clamp}}, f)
        f.write("\n")


def to8(x):
    return np.clip(np.round(x * 255.0), 0, 255).astype(np.uint8)


def waves(rng):
    k = np.fft.fftfreq(N, 1.0 / N)            # cycles per tile
    kx, ky = np.meshgrid(k, k)
    kk = np.hypot(kx, ky)
    # Band-limited power law (slope spectrum ~ k^-1.4), a mild wind direction so crests are
    # long-ish, no energy below 3 or above 56 cycles per tile (the shader layers octaves for range).
    wind = np.array([0.8, 0.6])
    cosw = np.where(kk > 0, (kx * wind[0] + ky * wind[1]) / np.maximum(kk, 1e-9), 0.0)
    P = np.where((kk >= 3) & (kk <= 56), np.maximum(kk, 1.0) ** -3.4, 0.0) * (0.35 + 0.65 * cosw ** 2)
    P *= np.exp(-(kk / 48.0) ** 2)
    H = (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) * np.sqrt(P)
    h = np.real(np.fft.ifft2(H))
    dx = np.real(np.fft.ifft2(H * 2j * np.pi * kx / N))
    dy = np.real(np.fft.ifft2(H * 2j * np.pi * ky / N))
    s = max(np.percentile(np.abs(dx), 99.9), np.percentile(np.abs(dy), 99.9))
    hs = np.percentile(np.abs(h), 99.9)
    img = np.stack([to8(0.5 + 0.5 * dx / s), to8(0.5 + 0.5 * dy / s), to8(0.5 + 0.5 * h / hs)], -1)
    Image.fromarray(img, "RGB").save(os.path.join(OUT, "qf_waves.png"), optimize=True)
    mcmeta("qf_waves.png")
    # The shader needs the slope scale: a texel value of 1 is s height units per texel.
    return {"slope_scale_per_texel": float(s), "height_scale": float(hs)}


def smooth_noise(rng, cells):
    g = rng.random((cells, cells))
    x = np.arange(N) * cells / N
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    a = g[np.ix_(i, i)]
    b = g[np.ix_(i, (i + 1) % cells)]
    c = g[np.ix_((i + 1) % cells, i)]
    d = g[np.ix_((i + 1) % cells, (i + 1) % cells)]
    fy, fx = np.meshgrid(f, f, indexing="ij")
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def worley(rng, cells):
    pts = (np.arange(cells)[:, None, None] * 0 + 0.0)
    jitter = rng.random((cells, cells, 2))
    y, x = np.mgrid[0:N, 0:N] * (cells / N)
    best1 = np.full((N, N), 9.0)
    best2 = np.full((N, N), 9.0)
    ci, cj = np.floor(y).astype(int), np.floor(x).astype(int)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ny, nx = ci + oy, cj + ox
            p = jitter[ny % cells, nx % cells]
            d = np.hypot(ny + p[..., 0] - y, nx + p[..., 1] - x)
            best2 = np.where(d < best1, best1, np.minimum(best2, d))
            best1 = np.minimum(best1, d)
    e = best2 - best1
    return np.clip(e / np.percentile(e, 99.5), 0, 1)


def noise(rng):
    r = rng.random((N, N))
    g = np.roll(r, -37, axis=1)   # G(x, y) = R(x + 37, y): a row shift, so a vertical flip on load cannot break it
    fbm = sum(smooth_noise(rng, c) * a for c, a in ((4, 0.5), (8, 0.25), (16, 0.125), (32, 0.0625))) / 0.9375
    fbm = (fbm - fbm.min()) / (fbm.max() - fbm.min())
    cell = worley(rng, 12)
    img = np.stack([to8(r), to8(g), to8(fbm), to8(cell)], -1)
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, "qf_noise.png"), optimize=True)
    mcmeta("qf_noise.png")


def milkyway(src, width):
    im = Image.open(src).convert("RGB")
    W, H = im.size                      # equirectangular, galactic plane horizontal, l = 0 centred
    band = im.crop((0, H // 4, W, 3 * H // 4))    # b = +45 .. -45 deg
    # Point stars out: a grey opening (min then max) removes anything a few pixels across, then a
    # median and a light blur keep the star clouds and dust lanes.
    small = band.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    small = small.filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    small = small.resize((width, width // 4), Image.LANCZOS)
    a = np.asarray(small).astype(np.float64) / 255.0
    lin = a ** 2.2
    # Background (airglow and light pollution in the source frames): the darkest 20% of the
    # high-latitude rows, per channel, taken out so only the galaxy remains.
    hi = np.concatenate([lin[: lin.shape[0] // 8], lin[-lin.shape[0] // 8:]])
    floor = np.percentile(hi.reshape(-1, 3), 20, axis=0)
    lin = np.clip(lin - floor, 0, None)
    lin /= np.percentile(lin, 99.95)
    out = np.clip(lin, 0, 1) ** (1 / 2.2)   # stored gamma-encoded for 8-bit precision in the dark
    Image.fromarray(to8(out), "RGB").save(os.path.join(OUT, "qf_milkyway.png"), optimize=True)
    mcmeta("qf_milkyway.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--milkyway")
    ap.add_argument("--mw-width", type=int, default=4096)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(20261024)
    info = waves(rng)
    noise(rng)
    print(info)
    if a.milkyway:
        milkyway(a.milkyway, a.mw_width)
    for f in sorted(os.listdir(OUT)):
        print(f, os.path.getsize(os.path.join(OUT, f)))


if __name__ == "__main__":
    main()
