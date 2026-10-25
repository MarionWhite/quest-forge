#!/usr/bin/env python3
"""Build "QF Textures, modded blocks" v1: the top-ranked modded blocks brought beside QF v0.

    py -3.10 -I tools/textures/build_modded_textures.py --out C:\\qfb\\textures\\QFTextures-modded-v1.zip
        [--only C:\\qfb\\textures\\top-modded.txt] [--mods DIR ...] [--sheets C:\\qfb\\textures]

What it writes (docs/design/textures/modded-blocks.md, section 4b):

  1. Ores on our stone.  Every 16x ore texture whose host is vanilla stone (the pixels under the
     flecks differ from vanilla's stone.png on fewer than 60 % of the tile), plus the ones listed
     in resourcepacks/QFTextures-modded/ores-extra.txt, is re-composited: Faithful 32x stone (the
     same stone QF v0 ships, with its vibrance) under the mod's flecks at 2x nearest. The fleck
     mask is the difference from vanilla stone, or labpbr.ore_mask's median fallback for the
     extra list. A transparent overlay (Railcraft's ores, which RenderBlockOre draws over the
     stone block) is kept an overlay at 2x. No pixel is drawn by hand; the flecks are the mod's.
  2. Backported vanilla blocks.  Legends' and Chisel's 1.8-1.16 blocks (granite, prismarine,
     concrete, blackstone...) draw Faithful 32x's modern Java texture for the same block, from
     resourcepacks/QFTextures-modded/backports.txt, only when the mod's 16x and Faithful's 32x agree
     in colour (mean distance and a pixel-wise check); the rest are reported and left out.
  3. Connected textures.  MCPatcher `ctm` rules (the format Angelica's MCPatcherForge reads for
     1.7.10) for Witchery's shaded glass (16 colours) and SecurityCraft's reinforced glass and
     stained glass (17), with 47 tiles each generated from the mod's own texture using the tile
     layout measured from Faithful's glass tiles (which edge each index keeps); `repeat` 2x2 rules
     for Chisel's marble and limestone from the base tile's four rotations. Railcraft's strengthened
     glass is a native 5-icon sheet (TextureAtlasSheet.unstitchIcons) and needs no rule.
  4. LabPBR maps for everything in --only plus the files above (tools/textures/labpbr.py, the same
     conversion as QF v0), with emission for tools/textures/emissive-modded.txt.

Sources and licence: Faithful 32x 1.7.10 (stone) and Faithful 32x Java 1.21.1 (backports), both
under the Faithful License v4, credited per file in CREDITS.txt with the licence text alongside;
the mods' own pixels for the flecks and the glass tiles. The zip is never committed.
"""
import argparse
import collections
import hashlib
import io
import json
import os
import re
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools", "shaders"))
import labpbr  # noqa: E402
import gen_surface_pack as gsp  # noqa: E402
import build_qf_textures as bqt  # noqa: E402  (vibrance, png, rgba: the same treatment as QF v0)

SRC = os.path.join(REPO, "resourcepacks", "QFTextures-modded")
LIVE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".crazycraft4")
FAITHFUL17 = r"C:\qfb\faithful\dl\Faithful.32x.-.1.7.10.zip"
FAITHFUL_MODERN = r"C:\qfb\faithful\dl\Faithful.32x.-.1.21.1.zip"
FAITHFUL_LICENSE = r"C:\qfb\faithful\LICENSE-faithful.txt"
VERSION = "v1"
HOST_SHARE = 0.60          # a texture is "on vanilla stone" when fewer pixels than this differ from it
BACKPORT_MEAN = 60.0       # sum of |mean RGB difference| allowed between the mod's and Faithful's texture
BACKPORT_PIXEL = 48.0      # mean per-pixel |RGB difference| at 16x allowed
CTM_ROOT = "assets/minecraft/mcpatcher/ctm/qf/"

# The 47-tile `ctm` layout: which edges of tile i keep the frame, measured from Faithful 32x's
# glass tiles (assets/minecraft/mcpatcher/ctm/glass/glass/0-46.png) on 2026-10-25; it is the
# standard MCPatcher layout every pack uses, so our tiles connect exactly as Faithful's do.
CTM47 = {0: "TBLR", 1: "TBL", 2: "TB", 3: "TBR", 4: "TL", 5: "TR", 6: "L", 7: "T", 8: "", 9: "", 10: "", 11: "",
         12: "TLR", 13: "TL", 14: "T", 15: "TR", 16: "BL", 17: "BR", 18: "B", 19: "R", 20: "", 21: "", 22: "", 23: "",
         24: "LR", 25: "L", 26: "", 27: "R", 28: "L", 29: "T", 30: "L", 31: "T", 32: "", 33: "", 34: "", 35: "",
         36: "BLR", 37: "BL", 38: "B", 39: "BR", 40: "B", 41: "R", 42: "B", 43: "R", 44: "", 45: "", 46: ""}

# Vanilla's dye order (metadata 0-15), as the item dump names Witchery's and SecurityCraft's
# glass variants; the texture suffix each mod uses for the colour.
DYES = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "silver", "cyan",
        "purple", "blue", "brown", "green", "red", "black"]
GLASS_FAMILIES = [
    # (folder, block name [verified: docs/survey/block-ids.tsv], domain, texture pattern, metas)
    ("witchery_shadedglass", "witchery:shadedglass", "witchery", "shadedglass_%s", list(range(16))),
    ("securitycraft_stained", "securitycraft:reinforcedStainedGlass", "securitycraft", "glass_reinforced_%s", list(range(16))),
    ("securitycraft_glass", "securitycraft:reinforcedGlassBlock", "securitycraft", "glass_reinforced", [0]),
]
REPEAT_FAMILIES = [
    # (folder, block name, domain, texture, metadata)
    ("chisel_marble", "chisel:marble", "chisel", "marble", 0),
    ("chisel_limestone", "chisel:limestone", "chisel", "limestone", 0),
]


def log(*a):
    print(*a, file=sys.stderr)


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def jars_in(dirs):
    seen = {}
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.endswith((".jar", ".zip")) and not re.search(r"\.(pre|broken)", f) and f not in seen:
                    seen[f] = os.path.join(root, f)
    return seen


BLOCK_TEX = re.compile(r"^assets/([^/]+)/textures/blocks/(.+)\.png$")


class Textures:
    """Every block texture across the mod jars: path -> zip member reader."""

    def __init__(self, jars):
        self.where = {}
        self.zips = {}
        for f, p in jars.items():
            try:
                z = zipfile.ZipFile(p)
            except zipfile.BadZipFile:
                continue
            self.zips[f] = z
            for m in z.namelist():
                if BLOCK_TEX.match(m) and m not in self.where and not m[:-4].endswith(("_n", "_s")):
                    self.where[m] = f
                elif m.endswith(".png.mcmeta") and m[:-7] not in self.where and m not in self.where:
                    self.where[m] = f

    def read(self, path):
        return self.zips[self.where[path]].read(path)

    def jar(self, path):
        return self.where[path]

    def __contains__(self, path):
        return path in self.where


def tex_path(dom, name):
    return "assets/%s/textures/blocks/%s.png" % (dom, name)


def first_frame(a):
    h, w = a.shape[:2]
    return a[:w] if h > w and h % w == 0 else a


def up2(a):
    return a.repeat(2, axis=0).repeat(2, axis=1)


# --- 1. ores on our stone -------------------------------------------------------------------
def composite_ores(tex, host32, stone16, extra, credits):
    """{path: rgba32} for every ore texture on vanilla stone (or in `extra`), on Faithful stone."""
    out, rows = {}, []
    for p in sorted(tex.where):
        if not p.endswith(".png"):
            continue
        name = BLOCK_TEX.match(p).group(2)
        dom = BLOCK_TEX.match(p).group(1)
        if labpbr.ore_params(name) is None:
            continue
        if dom == "orespawn" and re.match(r"^ore[a-z]+$", name) and p not in extra:
            continue   # OreSpawn's mob-spawn "ore" blocks: a mob icon on stone, not an ore
        if re.search(r"_overlay$|_background$", name):
            continue
        a = first_frame(bqt.rgba(tex.read(p)))
        if a.shape != stone16.shape:
            continue   # not 16x, or not square: left as the mod drew it
        if float((a[..., 3] == 0).mean()) > 0.5:
            # A transparent overlay: the mod's renderer draws it over the stone block (Railcraft's
            # RenderBlockOre, two passes), so the host is whatever stone the pack ships. Keep it an
            # overlay at 2x so its flecks match the 32x stone under them.
            out[p] = bqt.vibrance(up2(a))
            rows.append((p, "transparent overlay kept, 2x nearest (the mod draws it over the stone block)"))
            credits.append("%s: the overlay from %s at 2x nearest, transparency kept; no host" % (p, tex.jar(p)))
            continue
        d = np.abs(a[..., :3].astype(np.float32) - stone16[..., :3].astype(np.float32)).sum(-1)
        share = float((d > 40).mean())
        if share < HOST_SHARE:
            mask, how = d > 40, "diff vs vanilla stone (%.0f%% flecks)" % (share * 100)
        elif p in extra:
            mask, how = labpbr.ore_mask(a), "ores-extra.txt, median fallback mask"
        else:
            continue
        m2 = up2(mask)
        comp = host32.copy()
        fl = bqt.vibrance(up2(a))
        comp[m2] = fl[m2]
        comp[..., 3] = 255
        out[p] = comp
        rows.append((p, how))
        credits.append("%s: Faithful 32x (1.7.10) stone under the flecks of %s from %s, 2x nearest; mask: %s"
                       % (p, p, tex.jar(p), how))
    return out, rows


# --- 2. backported vanilla blocks --------------------------------------------------------
def backports(tex, modern, credits):
    """{path: (rgba, mcmeta or None)} for the verified pairs; also the table rows."""
    out, rows = {}, []
    mnames = set(modern.namelist())
    for l in open(os.path.join(SRC, "backports.txt"), encoding="utf-8"):
        l = l.split("#", 1)[0].strip()
        if not l or "=" not in l:
            continue
        left, right = [x.strip() for x in l.split("=", 1)]
        dom, name = left.split("/", 1)
        p = tex_path(dom, name)
        mp = "assets/minecraft/textures/block/%s.png" % right
        if p not in tex:
            rows.append((left, right, None, None, "no such mod texture"))
            continue
        if mp not in mnames:
            rows.append((left, right, None, None, "not in Faithful 32x 1.21.1"))
            continue
        a = first_frame(bqt.rgba(tex.read(p)))
        b_full = bqt.rgba(modern.read(mp))
        b = first_frame(b_full)
        if b.shape[0] % a.shape[0] != 0:
            rows.append((left, right, None, None, "size mismatch %s vs %s" % (a.shape[:2], b.shape[:2])))
            continue
        k = b.shape[0] // a.shape[0]
        b16 = b.reshape(a.shape[0], k, a.shape[1], k, 4).mean((1, 3))
        mean_d = float(np.abs(a[..., :3].mean((0, 1)) - b[..., :3].mean((0, 1))).sum())
        pix_d = float(np.abs(a[..., :3].astype(np.float32) - b16[..., :3]).mean())
        ok = mean_d <= BACKPORT_MEAN and pix_d <= BACKPORT_PIXEL
        rows.append((left, right, round(mean_d, 1), round(pix_d, 1), "verified" if ok else "guess: colours differ, left out"))
        if not ok:
            continue
        mcmeta = modern.read(mp + ".mcmeta") if mp + ".mcmeta" in mnames else None
        out[p] = (bqt.vibrance(b_full), mcmeta)
        credits.append("%s: Faithful 32x Java 1.21.1 block/%s.png (the same block, backported by the mod)%s"
                       % (p, right, "; animation from its .mcmeta" if mcmeta else ""))
    return out, rows


# --- 3. connected textures -----------------------------------------------------------------
def ctm_tiles(base):
    """47 `ctm` tiles from one framed glass texture: open edges take the interior next to them."""
    n = base.shape[0]
    tiles = {}
    for i, keep in CTM47.items():
        t = base.copy()
        if "T" not in keep:
            t[0, 1:n - 1] = base[1, 1:n - 1]
        if "B" not in keep:
            t[n - 1, 1:n - 1] = base[n - 2, 1:n - 1]
        if "L" not in keep:
            t[1:n - 1, 0] = base[1:n - 1, 1]
        if "R" not in keep:
            t[1:n - 1, n - 1] = base[1:n - 1, n - 2]
        for (cy, cx, ey, ex) in ((0, 0, "T", "L"), (0, n - 1, "T", "R"), (n - 1, 0, "B", "L"), (n - 1, n - 1, "B", "R")):
            if ey not in keep and ex not in keep:
                t[cy, cx] = base[1 if cy == 0 else n - 2, 1 if cx == 0 else n - 2]
            elif ey in keep and ex not in keep:
                t[cy, cx] = base[cy, 1 if cx == 0 else n - 2]       # the corner is part of the kept horizontal edge
            elif ex in keep and ey not in keep:
                t[cy, cx] = base[1 if cy == 0 else n - 2, cx]
        tiles[i] = t
    return tiles


def ctm_rules(tex, credits):
    """{zip path: bytes} for the rules and tiles, {tile path: (rgba, kind)} for their maps, table rows."""
    files, maps, rows = {}, {}, []
    for folder, block, dom, pattern, metas in GLASS_FAMILIES:
        for meta in metas:
            name = pattern % DYES[meta] if "%s" in pattern else pattern
            p = tex_path(dom, name)
            if p not in tex:
                rows.append((block, meta, name, "ctm", "NOT FOUND: no such texture"))
                continue
            base = first_frame(bqt.rgba(tex.read(p)))
            sub = "%s%s/%s/" % (CTM_ROOT, folder, DYES[meta] if "%s" in pattern else "glass")
            for i, t in ctm_tiles(base).items():
                files[sub + "%d.png" % i] = bqt.png(t)
                maps[sub + "%d.png" % i] = (t, "glass")
            files[sub + "%s.properties" % (DYES[meta] if "%s" in pattern else "glass")] = (
                "# Generated by tools/textures/build_modded_textures.py from %s\n"
                "matchBlocks=%s\nmetadata=%d\nmethod=ctm\ntiles=0-46\nconnect=tile\n" % (p, block, meta)).encode()
            rows.append((block, meta, name, "ctm, 47 tiles, connect=tile", "verified: block name (registry), metadata (item dump), texture (icon pairing)"))
            credits.append("%s*: 47 connected-texture tiles generated from %s (%s), layout as Faithful 32x's glass" % (sub, p, tex.jar(p)))
    for folder, block, dom, name, meta in REPEAT_FAMILIES:
        p = tex_path(dom, name)
        if p not in tex:
            rows.append((block, meta, name, "repeat", "NOT FOUND"))
            continue
        base = first_frame(bqt.rgba(tex.read(p)))
        sub = "%s%s/" % (CTM_ROOT, folder)
        for i in range(4):
            t = np.ascontiguousarray(np.rot90(base, i))
            files[sub + "%d.png" % i] = bqt.png(t)
            maps[sub + "%d.png" % i] = (t, "rough")
        files[sub + "%s.properties" % folder] = (
            "# Generated by tools/textures/build_modded_textures.py from %s: the tile's four rotations in a 2x2 repeat\n"
            "matchBlocks=%s\nmetadata=%d\nmethod=repeat\nwidth=2\nheight=2\ntiles=0-3\n" % (p, block, meta)).encode()
        rows.append((block, meta, name, "repeat 2x2, four rotations", "verified: block name (registry), metadata 0 = the worldgen variant (scans)"))
        credits.append("%s*: 2x2 repeat tiles, the four rotations of %s (%s)" % (sub, p, tex.jar(p)))
    return files, maps, rows


# --- build ----------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=r"C:\qfb\textures\top-modded.txt", help="textures that get LabPBR maps (rank_modded_blocks --only)")
    ap.add_argument("--mods", action="append", help="mod jar folders (default: live mods + C:\\qfs\\v0\\mods)")
    ap.add_argument("--mc-jar", default=os.path.join(LIVE, "bin", "minecraft.jar"))
    ap.add_argument("--faithful", default=FAITHFUL17)
    ap.add_argument("--faithful-modern", default=FAITHFUL_MODERN)
    ap.add_argument("--faithful-license", default=FAITHFUL_LICENSE)
    ap.add_argument("--emissive", default=os.path.join(HERE, "emissive-modded.txt"))
    ap.add_argument("--sheets", default=None, help="folder for the review contact sheets (ores before/after, backports, CTM)")
    ap.add_argument("--tables", default=None, help="write the doc's markdown tables here")
    a = ap.parse_args()
    mods = [m for m in (a.mods or [os.path.join(LIVE, "mods"), r"C:\qfs\v0\mods"]) if os.path.isdir(m)]
    tex = Textures(jars_in(mods))
    log("textures: %d from %d jars" % (sum(p.endswith(".png") for p in tex.where), len(tex.zips)))

    mc = zipfile.ZipFile(a.mc_jar)
    fa = zipfile.ZipFile(a.faithful)
    modern = zipfile.ZipFile(a.faithful_modern)
    stone16 = bqt.rgba(mc.read("assets/minecraft/textures/blocks/stone.png"))
    host32 = bqt.vibrance(bqt.rgba(fa.read("assets/minecraft/textures/blocks/stone.png")))
    extra = labpbr.read_texture_list(os.path.join(SRC, "ores-extra.txt"))
    emissive = labpbr.read_texture_list(a.emissive) if os.path.exists(a.emissive) else set()
    only = labpbr.read_texture_list(a.only) if a.only and os.path.exists(a.only) else set()
    credits = []

    ores, ore_rows = composite_ores(tex, host32, stone16, extra, credits)
    log("ores: %d re-composited (%d via ores-extra)" % (len(ores), sum(1 for _, h in ore_rows if "extra" in h)))
    missing_extra = sorted(p for p in extra if p not in ores)
    if missing_extra:
        log("  ores-extra not built (no such texture or not 16x): " + ", ".join(missing_extra))
    bp, bp_rows = backports(tex, modern, credits)
    log("backports: %d verified of %d listed" % (len(bp), len(bp_rows)))
    ctm_files, ctm_maps, ctm_rows = ctm_rules(tex, credits)
    log("ctm: %d files, %d rules" % (len(ctm_files), sum(1 for f in ctm_files if f.endswith(".properties"))))

    out = zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED)
    out.writestr("pack.mcmeta", open(os.path.join(SRC, "pack.mcmeta"), encoding="utf-8").read())
    out.write(a.faithful_license, "LICENSE-Faithful.txt")
    albedo = {}   # path -> (rgba, mcmeta)
    for p, img in ores.items():
        albedo[p] = (img, None)
    for p, (img, mcmeta) in bp.items():
        albedo[p] = (img, mcmeta)
    for p, (img, mcmeta) in sorted(albedo.items()):
        out.writestr(p, bqt.png(img))
        if mcmeta:
            out.writestr(p + ".mcmeta", mcmeta)
    for p, data in sorted(ctm_files.items()):
        out.writestr(p, data)

    # LabPBR maps: --only textures (from the mod's own pixels unless replaced above), replaced
    # textures (from what ships), CTM tiles.
    tally = collections.Counter()
    want = set(only) | set(albedo)
    for p in sorted(want):
        name = BLOCK_TEX.match(p).group(2)
        kind, _, strength = gsp.classify(name)
        if p in albedo:
            img, mcmeta = albedo[p]
            host = host32 if p in ores else None
        else:
            if p not in tex:
                tally["missing"] += 1
                continue
            img = bqt.rgba(tex.read(p))
            mcmeta = tex.read(p + ".mcmeta") if (p + ".mcmeta") in tex else None
            host = stone16 if img.shape[1] == 16 else None
        n, s = labpbr.pbr_maps(name, img, strength, kind, host, p in emissive)
        out.writestr(p[:-4] + "_n.png", bqt.png(n))
        out.writestr(p[:-4] + "_s.png", bqt.png(s))
        if mcmeta:
            out.writestr(p[:-4] + "_n.png.mcmeta", mcmeta)
            out.writestr(p[:-4] + "_s.png.mcmeta", mcmeta)
        tally["maps"] += 1
        if p in emissive:
            tally["emissive"] += 1
    for p, (img, kind) in sorted(ctm_maps.items()):
        _, _, strength = gsp.classify(kind)
        n, s = labpbr.pbr_maps(kind, img, strength, kind)
        out.writestr(p[:-4] + "_n.png", bqt.png(n))
        out.writestr(p[:-4] + "_s.png", bqt.png(s))
        tally["ctm maps"] += 1

    cred = ["Quest Forge Textures, modded blocks (%s)" % VERSION, "=" * 40, "",
            "Built by tools/textures/build_modded_textures.py. Sources:", "",
            "1. Faithful 32x -- https://faithfulpack.net -- Faithful License, Version 4 (LICENSE-Faithful.txt).",
            "   a. Faithful 32x, Java Edition 1.7.10 branch, release R17 (December 2025): stone.png,",
            "      the host under every re-composited ore (with the same chroma x%.2f as QF Textures v0)." % bqt.VIBRANCE,
            "      File: %s, sha256 %s." % (os.path.basename(a.faithful), sha256(a.faithful)),
            "   b. Faithful 32x, Java Edition 1.21.1, June 2026 release: the textures of the vanilla",
            "      1.8-1.16 blocks that Legends and Chisel backport, listed below.",
            "      File: %s, sha256 %s." % (os.path.basename(a.faithful_modern), sha256(a.faithful_modern)),
            "   Only the listed files are used. This pack is not made or endorsed by Faithful.",
            "2. The mods' own textures (Legends, Railcraft, VoltzEngine, TragicMC, OreSpawn, Transformers,",
            "   Biomes O' Plenty, Witchery, SecurityCraft, Chisel, ...): the ore flecks, the glass tiles and",
            "   the stone rotations below are their pixels, re-arranged; the LabPBR maps are generated from them.",
            "3. Quest Forge: the build script, the generated LabPBR 1.3 maps (_n, _s) and the CTM rules.", "",
            "Per-file records", "-" * 16]
    out.writestr("CREDITS.txt", "\n".join(cred + credits) + "\n")
    out.close()
    size = os.path.getsize(a.out)
    print("QF Textures modded %s: ores %d, backports %d, ctm files %d, %s -> %s (%d bytes, %.1f MB)"
          % (VERSION, len(ores), len(bp), len(ctm_files), dict(tally), a.out, size, size / 1e6))

    if a.sheets:
        os.makedirs(a.sheets, exist_ok=True)
        cs = 48
        items = sorted(ores)
        sheet = Image.new("RGBA", (10 * (2 * cs + 4), ((len(items) + 9) // 10) * (cs + 12)), (40, 40, 40, 255))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for i, p in enumerate(items):
            x, y = (i % 10) * (2 * cs + 4), (i // 10) * (cs + 12)
            before = Image.fromarray(first_frame(bqt.rgba(tex.read(p)))).resize((cs, cs), Image.NEAREST)
            after = Image.fromarray(ores[p]).resize((cs, cs), Image.NEAREST)
            sheet.paste(before, (x, y), before)
            sheet.paste(after, (x + cs, y), after)
            dr.text((x + 1, y + cs), BLOCK_TEX.match(p).group(2).split("/")[-1][:14], fill=(230, 230, 230, 255))
        sheet.save(os.path.join(a.sheets, "sheet-ores-v1.png"))
        items = sorted(bp)
        sheet = Image.new("RGBA", (10 * (2 * cs + 4), max(1, (len(items) + 9) // 10) * (cs + 12)), (40, 40, 40, 255))
        dr = ImageDraw.Draw(sheet)
        for i, p in enumerate(items):
            x, y = (i % 10) * (2 * cs + 4), (i // 10) * (cs + 12)
            before = Image.fromarray(first_frame(bqt.rgba(tex.read(p)))).resize((cs, cs), Image.NEAREST)
            after = Image.fromarray(first_frame(bp[p][0])).resize((cs, cs), Image.NEAREST)
            sheet.paste(before, (x, y))
            sheet.paste(after, (x + cs, y))
            dr.text((x + 1, y + cs), BLOCK_TEX.match(p).group(2).split("/")[-1][:14], fill=(230, 230, 230, 255))
        sheet.save(os.path.join(a.sheets, "sheet-backports-v1.png"))
        # CTM: one family's 47 tiles laid out 12 x 4 as MCPatcher's template, plus a 3x3 join
        fam = [p for p in ctm_files if p.startswith(CTM_ROOT + "witchery_shadedglass/blue/") and p.endswith(".png")]
        if fam:
            tiles = {int(p.split("/")[-1][:-4]): Image.open(io.BytesIO(ctm_files[p])).convert("RGBA") for p in fam}
            n = tiles[0].size[0]
            sheet = Image.new("RGBA", (12 * (n * 3 + 2) + 8 + 3 * n * 3, max(4 * (n * 3 + 2), 3 * n * 3)), (40, 40, 40, 255))
            for i in range(47):
                sheet.paste(tiles[i].resize((n * 3, n * 3), Image.NEAREST), ((i % 12) * (n * 3 + 2), (i // 12) * (n * 3 + 2)))
            # a 3x3 pane: corners, edges and centre as the ctm method would pick them
            pick = [[4, 7, 5], [6, 26, 19], [16, 18, 17]]
            ox = 12 * (n * 3 + 2) + 8
            for r in range(3):
                for c in range(3):
                    sheet.paste(tiles[pick[r][c]].resize((n * 3, n * 3), Image.NEAREST), (ox + c * n * 3, r * n * 3))
            sheet.save(os.path.join(a.sheets, "sheet-ctm-v1.png"))
        log("sheets -> " + a.sheets)

    if a.tables:
        with open(a.tables, "w", encoding="utf-8", newline="\n") as f:
            f.write("### Ores re-composited (%d)\n\n| texture | mask |\n|---|---|\n" % len(ore_rows))
            for p, how in ore_rows:
                f.write("| `%s` | %s |\n" % (p.split("assets/")[1], how))
            f.write("\n### Backports (%d listed, %d verified)\n\n| mod texture | Faithful 32x 1.21.1 `block/` | mean colour d | pixel d (16x) | result |\n|---|---|---|---|---|\n"
                    % (len(bp_rows), len(bp)))
            for left, right, md, pd, res in bp_rows:
                f.write("| `%s` | `%s` | %s | %s | %s |\n" % (left, right, "" if md is None else md, "" if pd is None else pd, res))
            f.write("\n### CTM rules (%d)\n\n| block | meta | texture | method | sources |\n|---|---|---|---|---|\n" % len(ctm_rows))
            for block, meta, name, method, src in ctm_rows:
                f.write("| `%s` | %s | `%s` | %s | %s |\n" % (block, meta, name, method, src))
        log("tables -> " + a.tables)


if __name__ == "__main__":
    main()
