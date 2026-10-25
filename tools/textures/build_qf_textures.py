#!/usr/bin/env python3
"""Build "QF Textures" (v0): vanilla's design, Faithful 32x where the owner liked it, a calmer
grass, a little more colour, and generated LabPBR normal + specular maps for every block.

    py -3.10 -I tools/textures/build_qf_textures.py --out C:\\qfb\\textures\\QFTextures-v0.zip
        [--mc-jar <minecraft.jar>] [--faithful <Faithful.32x.-.1.7.10.zip>] [--no-pbr]

Why each piece (docs/design/textures/direction.md, Shader Lab round 6 answers):
  * Base = vanilla 1.7.10 block textures from the player's own minecraft.jar ("I enjoy a lot of
    Minecraft's block designs"). They are read at build time and never stored in the repo.
  * Faithful 32x (resourcepacks/QFTextures/faithful.txt) only for the blocks the owner named:
    stone, the ores, gold/iron/diamond blocks, glowstone and glass (with Faithful's connected-glass
    CTM, which Angelica's built-in MCPatcher reads). Faithful License v4: credit + link in
    pack.mcmeta and CREDITS.txt, the licence text alongside, only what we need.
  * Grass: NOT Faithful's ("noisy green carpet"). Vanilla's own grass, doubled to 32x with its
    pattern kept, with the pixel-to-pixel contrast lowered so it reads calmer at a distance.
  * Vibrance: chroma x VIBRANCE around each pixel's own luminance (grey biome-tinted textures are
    unaffected; their colour comes from the shader's tint).
  * PBR (LabPBR 1.3, https://shaderlabs.org/wiki/LabPBR_Material_Standard), written as
    <name>_n.png / <name>_s.png next to each texture, also for the CTM tiles:
      _n: R,G normal X,Y (DirectX, +Y down the image), B ambient occlusion, A height (255 = flat).
      _s: R perceptual smoothness, G F0 (0-229 linear F0; 230 iron, 231 gold), B porosity (0-64)
          or subsurface (65-255), A emission (0-254; 255 = none).
    Normals reuse tools/shaders/gen_surface_pack.py's luminance-relief normal_map and its
    per-material strengths. The QuestForge shader does not sample these yet (direction.md says
    what it would take); they are here so a PBR-capable pass can be judged on our own art.
"""
import argparse, colorsys, io, json, os, re, sys, zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "resourcepacks", "QFTextures")
sys.path.insert(0, os.path.join(REPO, "tools", "shaders"))
sys.path.insert(0, HERE)
import gen_surface_pack as gsp  # noqa: E402  (classify: material kind + relief strength)
import labpbr  # noqa: E402  (the LabPBR conversion, shared with gen_surface_pack's modded maps)

LIVE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".crazycraft4")
FAITHFUL = r"C:\qfb\faithful\dl\Faithful.32x.-.1.7.10.zip"
FAITHFUL_LICENSE = r"C:\qfb\faithful\LICENSE-faithful.txt"
VERSION = "v0"
VIBRANCE = 1.12            # chroma gain; 1.0 = unchanged
GRASS_CALM = 0.68          # grass contrast kept (1.0 = vanilla's)
BLOCKS = "assets/minecraft/textures/blocks/"
CTM = "assets/minecraft/mcpatcher/ctm/"
GRASS = {"grass_top", "grass_side_overlay"}
SKIP_PBR = re.compile(r"^destroy_stage_|_overlay$|^(fire_layer|portal)")


def load_list(name):
    out = []
    for l in open(os.path.join(SRC, name), encoding="utf-8"):
        l = l.split("#", 1)[0].strip()
        if l:
            out.append(l)
    return out


def png(arr):
    b = io.BytesIO()
    Image.fromarray(arr, "RGBA").save(b, "PNG", optimize=True)
    return b.getvalue()


def rgba(data):
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))


# --- colour -----------------------------------------------------------------------
def vibrance(a, gain=VIBRANCE):
    """Scale each pixel's chroma around its own luminance, so greys and brightness stay put."""
    f = a[..., :3].astype(np.float32) / 255.0
    lum = (f @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    out = np.clip(lum + (f - lum) * gain, 0.0, 1.0)
    a = a.copy()
    a[..., :3] = (out * 255.0 + 0.5).astype(np.uint8)
    return a


def calm_grass(a):
    """Vanilla grass at 32x: each pixel doubled (the design kept), then the variation around a
    lightly blurred copy pulled in, so the carpet reads calmer without new detail."""
    big = a.repeat(2, axis=0).repeat(2, axis=1).astype(np.float32)
    h, w = big.shape[:2]
    if h > w:   # animated strips do not occur for grass; keep the code honest anyway
        return big.astype(np.uint8)
    rgb = big[..., :3]
    # 3x3 wrap blur (block textures tile)
    blur = sum(np.roll(np.roll(rgb, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    rgb = blur + (rgb - blur) * GRASS_CALM
    big[..., :3] = rgb
    return np.clip(big + 0.5, 0, 255).astype(np.uint8)


# --- PBR --------------------------------------------------------------------------
# The LabPBR conversion (relief -> _n with DirectX Y, AO and height; per-material _s with the
# ore-fleck, metal-code and emission rules) is tools/textures/labpbr.py, shared with
# tools/shaders/gen_surface_pack.py so the modded maps match these. gen_surface_pack's classify()
# still decides the material kind and relief strength from the texture's name.


def pbr_maps(name, a, stone=None):
    kind, _, strength = gsp.classify(os.path.basename(name))
    return labpbr.pbr_maps(name, a, strength, kind, stone)


# --- build ------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mc-jar", default=os.path.join(LIVE, "bin", "minecraft.jar"), help="read only")
    ap.add_argument("--faithful", default=FAITHFUL)
    ap.add_argument("--faithful-license", default=FAITHFUL_LICENSE)
    ap.add_argument("--no-pbr", action="store_true")
    a = ap.parse_args()

    mc = zipfile.ZipFile(a.mc_jar)
    fa = zipfile.ZipFile(a.faithful)
    fnames = set(fa.namelist())
    picks = load_list("faithful.txt")
    take = set()
    for p in picks:
        rx = re.compile("^" + p.replace(".", r"\.").replace("*", "[^/]*") + "$")
        hit = [m for m in fnames if m.startswith(BLOCKS) and m.endswith(".png") and rx.match(m[len(BLOCKS):-4])]
        if not hit:
            sys.exit(f"faithful.txt: {p} matches nothing in the Faithful zip")
        take.update(hit)

    out = zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED)
    meta = json.load(open(os.path.join(SRC, "pack.mcmeta"), encoding="utf-8"))
    out.writestr("pack.mcmeta", json.dumps(meta, indent=1, ensure_ascii=False))
    for f in ("CREDITS.txt",):
        out.write(os.path.join(SRC, f), f)
    out.write(a.faithful_license, "LICENSE-Faithful.txt")
    if os.path.exists(os.path.join(SRC, "pack.png")):
        out.write(os.path.join(SRC, "pack.png"), "pack.png")

    tally = {"vanilla": 0, "faithful": 0, "grass": 0, "ctm": 0, "pbr": 0}
    textures = {}   # path -> (rgba, mcmeta bytes or None)
    for m in sorted(x for x in mc.namelist() if x.startswith(BLOCKS) and x.endswith(".png")):
        name = m[len(BLOCKS):-4]
        mcmeta = mc.read(m + ".mcmeta") if m + ".mcmeta" in mc.namelist() else None
        if m in take:
            img = rgba(fa.read(m))
            mcmeta = fa.read(m + ".mcmeta") if m + ".mcmeta" in fnames else mcmeta
            tally["faithful"] += 1
        elif name in GRASS:
            img = calm_grass(rgba(mc.read(m)))
            tally["grass"] += 1
        else:
            img = rgba(mc.read(m))
            tally["vanilla"] += 1
        textures[m] = (vibrance(img), mcmeta)
    # grass_side (dirt with an untinted fringe) stays vanilla 16x: only the tinted top and the
    # side overlay make the "carpet".

    # Faithful's connected glass (only the glass group: we take Faithful's glass, not its
    # bookshelf or sandstone, which stay vanilla here).
    ctm = sorted(m for m in fnames if m.startswith(CTM + "glass/") and not m.endswith("/"))
    for m in ctm:
        if m.endswith(".png"):
            textures[m] = (vibrance(rgba(fa.read(m))), None)
        else:
            out.writestr(m, fa.read(m))
        tally["ctm"] += 1

    stone = {"v": textures[BLOCKS + "stone.png"][0]}
    for m, (img, mcmeta) in sorted(textures.items()):
        out.writestr(m, png(img))
        if mcmeta:
            out.writestr(m + ".mcmeta", mcmeta)
        name = m[:-4].split("/textures/blocks/")[-1] if BLOCKS in m else m[len(CTM):-4]
        base = os.path.basename(name)
        if a.no_pbr or SKIP_PBR.search(base):
            continue
        # CTM tiles are named 0..46 inside a folder named after the block.
        mat = name if BLOCKS in m else os.path.basename(os.path.dirname(m))
        n, s = pbr_maps(mat, img, stone["v"] if base.endswith("_ore") else None)
        out.writestr(m[:-4] + "_n.png", png(n))
        out.writestr(m[:-4] + "_s.png", png(s))
        if mcmeta:
            out.writestr(m[:-4] + "_n.png.mcmeta", mcmeta)
            out.writestr(m[:-4] + "_s.png.mcmeta", mcmeta)
        tally["pbr"] += 1
    out.close()
    print("QF Textures %s: %s -> %s (%.1f MB)" % (VERSION, tally, a.out, os.path.getsize(a.out) / 1e6))


if __name__ == "__main__":
    main()
