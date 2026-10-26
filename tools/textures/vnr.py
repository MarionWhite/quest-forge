#!/usr/bin/env python3
"""Vanilla Normals Renewed (VNR) maps, converted to LabPBR 1.3 for QF Textures v1.

Source: "Vanilla Normals Renewed" 1.12 v0.04 by Poudingue,
https://github.com/Poudingue/Vanilla-Normals-Renewed-1.12 (master c848329, 2020-05-24; the zip is
C:\\qfb\\vnr\\dl\\, sha256 43d98ed0..., see C:\\qfb\\vnr\\meta.txt). Its README: "You can do whatever you
want with my texture pack, screenshots, videos, modifications for personal use or redistribution,
as long as you don't sell it and provide a link to this page or my Patreon. Oh, and also, don't mix
it with Realistico." So: only its _n/_s maps are used (never its albedo PNGs, which are Mojang's),
the pack is never sold, CREDITS.txt links the page, and Realistico is never part of the pack.

VNR's layout (old SEUS-Renewed style, checked on the files 2026-10-25):
    _n  RGB tangent normal, OpenGL (+Y up the image: G correlates -0.83..-0.98 with the height's
        downward slope on stonebrick, cobblestone, planks_oak, brick), A height (255 = flat).
    _s  R smoothness, G metal flag (0 / 255), B emission on a few blocks (inconsistent), A 255.
LabPBR wants:
    _n  RG DirectX normal (G flipped), B AO, A height.
    _s  R smoothness, G F0 (0-229) or a metal code (230 iron, 231 gold), B porosity/SSS, A emission.

VNR was drawn for vanilla's 16x art, so its maps fit textures that stay vanilla in our pack as
they are. On a Faithful 64x texture that keeps vanilla's layout, `hybrid_normal` upscales VNR's
height (the shapes: bevelled bricks, rounded cobbles) and adds our own fine relief from the 64x art.
"""
import io
import re
import zipfile

import numpy as np
from PIL import Image

import labpbr

VNR_ZIP = r"C:\qfb\vnr\dl\Vanilla-Normals-Renewed-1.12-master.zip"
PREFIX_RX = re.compile(r"^[^/]+/assets/minecraft/textures/blocks/")
METALS = {"iron_block": 230, "gold_block": 231, "iron_bars": 230, "rail": 230, "anvil": 230,
          "cauldron": 230, "hopper": 230, "door_iron": 230, "gold_ore": None, "iron_ore": None}


class VNR:
    def __init__(self, path=VNR_ZIP):
        self.z = zipfile.ZipFile(path)
        self.maps = {}
        for n in self.z.namelist():
            m = PREFIX_RX.match(n)
            if m and n.endswith(".png"):
                self.maps[n[m.end():-4]] = n

    def has(self, name):
        return name + "_n" in self.maps

    def read(self, name, kind):
        p = self.maps.get(name + "_" + kind)
        return np.array(Image.open(io.BytesIO(self.z.read(p))).convert("RGBA")) if p else None


def resize(a, size, smooth=True):
    """Square-resize one map (float channels) to size x size."""
    if a.shape[0] == size:
        return a.astype(np.float32)
    im = [Image.fromarray(a[..., c].astype(np.float32), "F").resize((size, size), Image.BILINEAR if smooth else Image.NEAREST)
          for c in range(a.shape[2])]
    return np.dstack([np.array(i) for i in im])


def ao_from_height(h):
    """LabPBR B: cavities (pixels below their neighbourhood) darkened, 0.55..1."""
    hf = h / 255.0
    nb = sum(np.roll(np.roll(hf, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    return np.clip(1.0 - np.maximum(nb - hf, 0.0) * 6.0, 0.55, 1.0) * 255.0


def to_labpbr_n(n, albedo=None):
    """VNR _n (one square frame) -> LabPBR _n at the same size."""
    n = n.astype(np.float32)
    h = n[..., 3]
    out = np.dstack([n[..., 0], 255.0 - n[..., 1], ao_from_height(h), np.maximum(h, 1.0)])
    if albedo is not None and albedo.shape[:2] == n.shape[:2]:
        out[albedo[..., 3] < 25] = (128, 128, 255, 255)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def to_labpbr_s(s, name, albedo=None, por=0):
    """VNR _s -> LabPBR _s. Metal flag -> the hard-coded metal (iron 230, gold 231, else F0 byte 10
    for a dielectric); VNR's blue emission -> LabPBR alpha; `por` (porosity / subsurface) from our
    own material table."""
    s = s.astype(np.float32)
    base = name.split("/")[-1]
    code = METALS.get(base, 230)
    metal = s[..., 1] > 127
    if code is None:                       # an ore: the flecks are the metal, judged per pixel by VNR
        code = 231 if base.startswith("gold") else 230
    g = np.where(metal, float(code), 10.0)
    emis = np.where(s[..., 2] > 8, np.minimum(s[..., 2], 254.0), 255.0)
    if base in ("gold_block",):            # VNR's gold_block B=255 everywhere is not emission
        emis[:] = 255.0
    out = np.dstack([s[..., 0], g, np.full(s.shape[:2], float(por)), emis])
    if albedo is not None and albedo.shape[:2] == s.shape[:2]:
        out[albedo[..., 3] < 25] = (0, 0, 0, 255)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def layout_match(albedo, vanilla):
    """How well a hi-res texture keeps vanilla's layout: correlation of their luminance after the
    hi-res one is box-filtered down to vanilla's size (Faithful keeps the shapes, so ~0.6-0.9)."""
    k = albedo.shape[0] // vanilla.shape[0]
    if k < 1 or albedo.shape[0] % vanilla.shape[0]:
        return 0.0
    la = labpbr.lum(albedo)
    small = la.reshape(vanilla.shape[0], k, vanilla.shape[1], k).mean((1, 3))
    lv = labpbr.lum(vanilla)
    if small.std() < 1e-4 or lv.std() < 1e-4:
        return 0.0
    return float(np.corrcoef(small.ravel(), lv.ravel())[0, 1])


def hybrid_normal(vnr_n, albedo, strength, micro=0.7):
    """VNR's shapes (its 16x height, upscaled smoothly) + our fine relief from the hi-res art.
    Returns LabPBR _n at the albedo's size."""
    size = albedo.shape[0]
    big = resize(vnr_n.astype(np.float32), size)
    # macro normal from VNR's own normal (OpenGL), re-normalised after the resize
    nx, ny = big[..., 0] / 127.5 - 1, big[..., 1] / 127.5 - 1
    ours = labpbr.normal_map(albedo, strength).astype(np.float32)   # OpenGL RGB + A height
    mx, my = ours[..., 0] / 127.5 - 1, ours[..., 1] / 127.5 - 1
    x, y = nx + mx * micro, ny + my * micro
    z = np.sqrt(np.clip(1 - x * x - y * y, 0.05, 1))
    ln = np.sqrt(x * x + y * y + z * z)
    x, y = x / ln, y / ln
    h = np.clip(big[..., 3] * 0.8 + ours[..., 3] * 0.2, 1, 255)
    out = np.dstack([(x * 0.5 + 0.5) * 255, (1 - (y * 0.5 + 0.5)) * 255, ao_from_height(h), h])
    out[albedo[..., 3] < 25] = (128, 128, 255, 255)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def hybrid_specular(vnr_s, albedo, name, stone=None, por=0):
    """VNR's smoothness pattern upscaled, our ore-fleck rule on the hi-res art, LabPBR codes."""
    size = albedo.shape[0]
    s = to_labpbr_s(resize(vnr_s.astype(np.float32), size, smooth=False), name, por=por).astype(np.float32)
    L = labpbr.lum(albedo)
    s[..., 0] = np.clip(s[..., 0] + (L - L.mean()) * 40.0, 0, 255)
    op = labpbr.ore_params(name)
    if op is not None:
        m = labpbr.ore_mask(albedo, stone)
        s[..., 0] = np.where(m, op[0] * 255.0, s[..., 0])
        s[..., 1] = np.where(m, float(op[1]), 10.0)    # VNR's 16x metal flecks do not line up at 64x
    s[albedo[..., 3] < 25] = (0, 0, 0, 255)
    return np.clip(s + 0.5, 0, 255).astype(np.uint8)
