#!/usr/bin/env python3
"""Build a resource pack that gives every block in the pack -- vanilla and modded
alike -- surface relief and shader materials under Sildur's Vibrant.

WHY GENERATE RATHER THAN DOWNLOAD. A PBR texture pack covers vanilla's ~400
block textures. This pack has ~5,200 more across 65 mods, which a hand-made pack
would leave flat beside vanilla's relief -- the inconsistency is worse than no
pack. No PBR pack ships the 1.7.10 file layout anyway (checked 2026-10-16), and
Complementary, whose shader-side "generated normals" would have covered every
block, does not render on OptiFine 1.7.10 E7. So every texture gets the same
treatment from the same algorithm, vanilla included, and the look stays even.

WHAT IT WRITES, into one resource pack:

  assets/<domain>/textures/blocks/<name>_n.png
      A normal map for every block texture: RGB = tangent-space normal, A =
      height, the layout Vibrant's nMap reads (it ignores specular maps
      entirely). Height comes from luminance, which on 16x16 pixel art is the
      artist's own shading; the strength is set per material from the texture's
      name, so cobblestone gets deep relief and polished metal almost none.

  assets/<modid>/shaders/block.properties
      Tells the shader what modded blocks are. OptiFine E7 reads this file for
      every Forge mod (BlockAliases.loadModBlockAliases) through the normal
      resource system, so a resource pack can supply it. Classified by
      registry name: leaves wave, plants sway, lamps glow, metal and polished
      stone reflect, glass and ice refract. IDs are Vibrant's own (its
      block.properties, pre-1.13 branch); another shader would need its own.

Usage:
    gen_surface_pack.py --instance %APPDATA%\\.crazycraft4 --world <save dir> --out QuestForge-Surface.zip

--world is any world saved by the pack: its level.dat carries FML's registry of
every block name, which is the only complete list of what is installed.
"""
import argparse, collections, gzip, io, json, os, re, sys, zipfile

import numpy as np
from PIL import Image

# --- materials ---------------------------------------------------------------
# Each rule: (shader ID or None, normal strength, name regex). First match wins,
# so the specific come before the general. Matched against the registry name's
# path (block names) or the texture's path (normal maps), lowercased.
SPAWN = re.compile(r"spawn|egg|monster", re.I)

RULES = [
    ("web",      20000, 0.6, r"cobweb|(^|[^a-z])web"),
    ("leaves",   10018, 0.8, r"leaves|leaf(?!let)"),
    ("plant",    10059, 0.6, r"sapling|flower|tallgrass|tall_grass|bush|fern|crop|wheat|reed|bramble|"
                             r"shrub|petal|clover|sprout|plant\d|plant$|mushroom(?!_block)|berr(y|ies)$|vine"),
    ("emissive", 10089, 0.5, r"^(?!.*(unlit|off$))(.*(lamp|lantern|glowstone|glow(?!er)|torch|candle|brazier|lightsource|lighton$|_on$)|.*[a-z]lit$)"),
    ("glass",    10079, 0.2, r"glass|(^|[^a-z]|packed|perpetual|brittle|black|blue|thin|dark|frost|glacial)ice(?!d)|crystal(?!.*ore)|frozen"),
    ("metal",    10080, 0.35, r"^(?!.*(curtain|carpet|wool|cloth))(.*)(iron|steel|gold|copper|bronze|tin|silver|titanium|alumin(i)?um|uranium|"
                              r"platinum|lead|nickel|cobalt|mithril|adamant|electrum|invar|endium|metal)"
                              r"(_?block|$)|plating|machine|factory|vault|anvil"),
    ("polished", 10081, 0.5, r"marble|quartz|polished|smooth|obsidian|futura"),
    # No shader ID: these only set how deep the generated relief is.
    ("ore",      None, 1.8, r"ore"),
    ("rough",    None, 2.4, r"cobble|gravel|rock|rubble|stone|brick|deadrock|basalt|cliff|ravaged"),
    ("wood",     None, 1.4, r"log|wood|plank|bark|bookshelf|crate|barrel"),
    ("soil",     None, 1.2, r"dirt|sand|grass|mud|clay|soil|snow|mycel|podzol|farmland"),
    ("cloth",    None, 0.9, r"wool|carpet|cloth|curtain|bed"),
]
DEFAULT_STRENGTH = 1.3
COMPILED = [(n, i, s, re.compile(r, re.I)) for n, i, s, r in RULES]


def classify(name):
    # "tile.TFLeaves", "tile.TardisMod.Schema": the prefix is the old unlocalized
    # form, not part of what the block is.
    name = re.sub(r"^(tile\.)+([a-z]+mod\.)?", "", name, flags=re.I)
    for n, ident, strength, rx in COMPILED:
        if rx.search(name):
            return n, ident, strength
    return "default", None, DEFAULT_STRENGTH


# --- block.properties ----------------------------------------------------------
def registry_names(world):
    data = gzip.open(os.path.join(world, "level.dat")).read()
    # FML's ItemData entries prefix block names with \x01 (items with \x02).
    return sorted(set(m.decode() for m in re.findall(rb"\x01([A-Za-z0-9_]+:[^\x00-\x1f]{2,80})", data)))


def block_mappings(names):
    """{modid: {shader_id: [names]}}, minecraft excluded: the shader maps vanilla itself."""
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    tally = collections.Counter()
    for full in names:
        modid, path = full.split(":", 1)
        if modid == "minecraft" or SPAWN.search(path):
            continue
        kind, ident, _ = classify(path)
        if ident is None:
            continue
        out[modid][ident].append(full)
        tally[kind] += 1
    return out, tally


# --- normal maps -----------------------------------------------------------------
def normal_map(img, strength):
    """RGBA uint8 normal map (RGB normal, A height) for one square frame."""
    a = img.astype(np.float32) / 255.0
    alpha = a[..., 3]
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    # Height is the artist's shading. Centre it per texture so a uniformly dark
    # block is not sunk and a light one raised -- only the variation matters.
    solid = alpha > 0.1
    if solid.any():
        lum = lum - lum[solid].mean()
    lum = np.where(solid, lum, 0.0)
    # Neighbours wrap, because block textures tile.
    dx = (np.roll(lum, -1, axis=1) - np.roll(lum, 1, axis=1)) * 0.5
    dy = (np.roll(lum, 1, axis=0) - np.roll(lum, -1, axis=0)) * 0.5   # image rows run down; +y is up
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(lum)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[~solid] = (0.0, 0.0, 1.0)   # cut-out pixels stay flat
    rgb = np.clip((n * 0.5 + 0.5) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    # Height for parallax: 1.0 = surface. Only gently below it; deep parallax on
    # 16x16 art reads as smeared, not as depth.
    h = np.clip(1.0 + np.where(solid, lum, 0.0) * 0.6, 0.0, 1.0)
    height = np.clip(h * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return np.dstack([rgb, height])


def texture_normals(png_bytes, strength):
    img = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGBA"))
    h, w = img.shape[:2]
    if h > w and h % w == 0:   # animated strip: each frame is its own tile
        frames = [normal_map(img[i * w:(i + 1) * w], strength) for i in range(h // w)]
        out = np.vstack(frames)
    else:
        out = normal_map(img, strength)
    buf = io.BytesIO()
    Image.fromarray(out, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


BLOCK_TEX = re.compile(r"^assets/([^/]+)/textures/blocks/(.+)\.png$")


def texture_sources(instance):
    """(archive path, member) for every block texture: minecraft.jar, then mods."""
    yield os.path.join(instance, "bin", "minecraft.jar")
    for root, _, files in os.walk(os.path.join(instance, "mods")):
        for f in sorted(files):
            if f.endswith((".jar", ".zip")) and not re.search(r"\.(pre|broken)", f):
                yield os.path.join(root, f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--world", required=True, help="a world saved by this pack (for the block registry)")
    ap.add_argument("--out", required=True, help="resource pack zip to write")
    ap.add_argument("--strength", type=float, default=1.0, help="scale every material's relief")
    ap.add_argument("--no-normals", action="store_true", help="block mappings only")
    args = ap.parse_args()

    out = zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED)
    out.writestr("pack.mcmeta", json.dumps({"pack": {"pack_format": 1, "description":
                 "Quest Forge surfaces: generated relief and shader materials for every block"}}, indent=1))

    maps, tally = block_mappings(registry_names(args.world))
    lines = 0
    for modid, by_id in sorted(maps.items()):
        body = ["# Generated by tools/shaders/gen_surface_pack.py for Sildur's Vibrant. Do not edit."]
        for ident, names in sorted(by_id.items()):
            body.append("block.%d=%s" % (ident, " ".join(names)))
            lines += len(names)
        # Resource domains are lowercase in 1.7.10; block names keep their case.
        out.writestr("assets/%s/shaders/block.properties" % modid.lower(), "\n".join(body) + "\n")
    print("block mappings: %d blocks in %d mods  %s" % (lines, len(maps), dict(tally)))

    if not args.no_normals:
        done, seen = collections.Counter(), set()
        for archive in texture_sources(args.instance):
            try:
                z = zipfile.ZipFile(archive)
            except zipfile.BadZipFile:
                continue
            members = set(z.namelist())
            for m in sorted(members):
                g = BLOCK_TEX.match(m)
                if not g or g.group(2).endswith(("_n", "_s")) or m in seen:
                    continue
                seen.add(m)
                if m[:-4] + "_n.png" in members:
                    continue   # the mod ships its own; never override an artist's map
                _, _, strength = classify(g.group(2))
                try:
                    data = texture_normals(z.read(m), strength * args.strength)
                except Exception as e:
                    print("  skip %s: %s" % (m, e))
                    continue
                out.writestr(m[:-4] + "_n.png", data)
                if m + ".mcmeta" in members:
                    out.writestr(m[:-4] + "_n.png.mcmeta", z.read(m + ".mcmeta"))
                done[g.group(1)] += 1
        print("normal maps: %d textures across %d domains" % (sum(done.values()), len(done)))
    out.close()
    print("wrote %s (%.1f MB)" % (args.out, os.path.getsize(args.out) / 1e6))


if __name__ == "__main__":
    main()
