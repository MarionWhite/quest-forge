#!/usr/bin/env python3
"""Build a resource pack that gives every block in the pack -- vanilla and modded
alike -- generated surface relief, plus the block-ID mapping a shader needs to
know what each block is.

WHY GENERATE RATHER THAN DOWNLOAD. A PBR texture pack covers vanilla's ~400
block textures. This pack has ~5,200 more across 65 mods, which a hand-made pack
would leave flat beside vanilla's relief -- the inconsistency is worse than no
pack. No PBR pack ships the 1.7.10 file layout anyway (checked 2026-10-16). So
every texture gets the same treatment from the same algorithm, vanilla
included, and the look stays even.

TWO TARGETS (--target):

  questforge  (default; Angelica / Iris, see docs/design/shaders/README.md)
      shaders/block.properties is written INTO THE SHADER PACK (--shader-pack
      DIR). Iris reads block.properties only from the pack's shaders/ folder,
      never from mod resource domains. The file covers vanilla and modded
      blocks with our own material IDs (QF_IDS) and is wrapped in
      `#if MC_VERSION == 10710`. Without that line Angelica treats the entries
      as modern 1.13+ names and compiles the whole pack with a modern
      MC_VERSION (IdMap.detectLegacySection, ShaderPack.mcVersionOverride).

  vibrant     (OptiFine E7 only, the fallback client)
      assets/<modid>/shaders/block.properties per mod, inside the resource pack.
      E7 reads those for every Forge mod (BlockAliases.loadModBlockAliases).
      IDs are Sildur's Vibrant's own (its block.properties, pre-1.13 branch);
      vanilla is left to the shader. Angelica ignores these files.

BOTH TARGETS ALSO WRITE, into the resource pack (--out), surface maps for every
block texture (--format picks the layout; the default follows the target):

  labpbr (questforge default; LabPBR 1.3, what QF Textures v0 also writes)
      assets/<domain>/textures/blocks/<name>_n.png  R,G normal (DirectX Y),
          B ambient occlusion, A height.
      assets/<domain>/textures/blocks/<name>_s.png  R smoothness, G F0 (230-237
          the hard-coded metals: Legends' copper, lead, platinum, silver ores
          get their own codes), B porosity / subsurface, A emission.
      The conversion is tools/textures/labpbr.py, shared with
      tools/textures/build_qf_textures.py so vanilla and modded maps match.
  legacy (vibrant default)
      <name>_n.png only: RGB = tangent-space normal (OpenGL), A = height, the
      layout Sildur's Vibrant's nMap reads.

Height comes from luminance, which on 16x16 pixel art is the artist's own
shading; the strength is set per material from the texture's name, so
cobblestone gets deep relief and polished metal almost none. A mod that ships
its own <name>_n.png is never overridden.

--only FILE limits the maps to the textures listed in FILE (one per line:
assets/<domain>/textures/blocks/<name>.png, or <domain>/<name>, or
<domain>:<name>), so the texture loop can rebuild maps for a ranked list
(tools/textures/rank_modded_blocks.py --only) in seconds. --mods DIR adds jar
folders beyond <instance>/mods (Biomes O' Plenty lives on the world-design
server, not in the live client).

Classified by registry name: leaves wave, plants sway, lamps glow, metal and
polished stone reflect, glass and ice refract; with the questforge target ores
glint and water and lava get their own IDs.

Usage (py -3.10 -I):
    gen_surface_pack.py --target questforge --instance C:\qfb\client-ang --world C:\qfb\world-master \
        --shader-pack C:\qfb\client-ang\shaderpacks\QuestForge-dev --out QuestForge-Surface.zip
    gen_surface_pack.py --target vibrant --instance %APPDATA%\.crazycraft4 --world <save> --out QuestForge-Surface.zip
    gen_surface_pack.py --target questforge --instance %APPDATA%\.crazycraft4 --mods C:\qfs\v0\mods \
        --world C:\qfb\world-master --shader-pack C:\qfb\textures\shaderpack-scratch \
        --only C:\qfb\textures\top-modded.txt --out C:\qfb\textures\QFTextures-modded-v0.zip

--world is any world saved by the pack: its level.dat carries FML's registry of
every block name, which is the only complete list of what is installed.
--instance supplies mods/, and bin/minecraft.jar for the vanilla textures. An
Angelica game dir has no bin/, so the live instance's minecraft.jar is used
unless --mc-jar says otherwise.
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

# --- Quest Forge material IDs (questforge target) -------------------------------
# Our own numbering, read in GLSL as mc_Entity.x / blockEntityId. The shader's
# /lib/materials.glsl must use the same table: change both together. Unmapped
# blocks are plain opaque. Never copy another pack's numbering.
QF_IDS = {
    "water":    1001,   # Beer-Lambert volume, Fresnel, waves
    "lava":     1002,   # emissive fluid
    "leaves":   1010,   # wave + subsurface
    "plant":    1011,   # sway from the base, subsurface
    "web":      1012,   # cut-out, casts no shadow
    "emissive": 1020,   # lamps, torches, glowstone, fire
    "glass":    1030,   # refraction, tinted shadow
    "metal":    1040,   # high F0, low roughness
    "polished": 1041,   # dielectric, low roughness
    "ore":      1050,   # glint on the ore pixels
}
# Checked before RULES, for the questforge block mapping only (never the normal
# strength), so the Vibrant output is unchanged. Vanilla names here are 1.7.10
# registry names, e.g. minecraft:flowing_water.
QF_EXTRA = [
    # Off states that the RULES' lamp pattern would light up.
    (None,       re.compile(r"^redstone_lamp$|^unlit_|_off$", re.I)),
    ("water",    re.compile(r"^(flowing_)?water$|(^|[^a-z])water(_?(still|flowing|fluid|block))?$", re.I)),
    ("lava",     re.compile(r"^(flowing_)?lava$|(^|[^a-z])lava(_?(still|flowing|fluid|block))?$", re.I)),
    ("plant",    re.compile(r"waterlily|lily_?pad|double_plant|red_flower|yellow_flower|reeds|deadbush|cactus", re.I)),
    ("emissive", re.compile(r"^fire$|^lit_pumpkin$|^lit_redstone_lamp$|^beacon$|^portal$|^end_portal$", re.I)),
    # Case-sensitive on purpose: "oreCopper", "veGemOre", "copper_ore", not "core" or "store".
    ("ore",      re.compile(r"(^|[^a-zA-Z])[Oo]re|Ore|_ore|ore_")),
]


def classify_qf(name):
    """QF material kind for a registry path, or None for a plain block (QF_EXTRA may say None outright)."""
    name = re.sub(r"^(tile\.)+([a-z]+mod\.)?", "", name, flags=re.I)
    for kind, rx in QF_EXTRA:
        if rx.search(name):
            return kind
    kind, ident, _ = classify(name)
    return kind if kind in QF_IDS and ident is not None else None


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


def qf_mappings(names):
    """{qf_id: [names]} over vanilla and modded blocks, each block exactly once."""
    out, tally, skipped = collections.defaultdict(list), collections.Counter(), []
    for full in names:
        modid, path = full.split(":", 1)
        if SPAWN.search(path):
            continue
        if re.search(r"\s", full):   # the ID list is whitespace-separated
            skipped.append(full)
            continue
        kind = classify_qf(path)
        if kind is None:
            continue
        out[QF_IDS[kind]].append(full)   # one ID per block: Iris keeps the first it sees
        tally[kind] += 1
    return out, tally, skipped


def write_qf_block_properties(pack_dir, names):
    by_id, tally, skipped = qf_mappings(names)
    shaders = os.path.join(pack_dir, "shaders")
    os.makedirs(shaders, exist_ok=True)
    body = ["# Generated by tools/shaders/gen_surface_pack.py --target questforge. Do not edit:",
            "# change QF_IDS or the rules there and re-run. Iris reads this only from the pack.",
            "# The guard makes Angelica treat the file as 1.7.10 names and keeps MC_VERSION",
            "# at 10710 for the whole pack; without it the names are read as 1.13+.",
            "#if MC_VERSION == 10710"]
    for ident, members in sorted(by_id.items()):
        body.append("block.%d=%s" % (ident, " ".join(members)))
    body.append("#endif")
    path = os.path.join(shaders, "block.properties")
    with open(path, "w", encoding="latin-1", errors="replace", newline="\n") as f:   # .properties are ISO-8859-1
        f.write("\n".join(body) + "\n")
    print("block.properties: %d blocks  %s -> %s" % (sum(tally.values()), dict(tally), path))
    if skipped:
        print("  skipped %d names containing whitespace: %s" % (len(skipped), ", ".join(skipped[:8])))


# --- surface maps ------------------------------------------------------------------
# The relief and the LabPBR conversion live in tools/textures/labpbr.py, shared with
# build_qf_textures.py (QF Textures) so vanilla and modded blocks carry matching maps.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures"))
import labpbr  # noqa: E402

normal_map = labpbr.normal_map   # the old name, for callers that import it from here


def png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def texture_maps(png_bytes, name, strength, fmt, kind=None, stone=None, emissive=False):
    """{suffix: png bytes} for one texture (animated strips included): {'_n'} in the legacy
    layout, {'_n', '_s'} for LabPBR. `stone` is the vanilla stone at the texture's size, so an
    ore's flecks can be told from its host rock; `emissive` marks the bright pixels as emitting."""
    img = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGBA"))
    if fmt == "legacy":
        return {"_n": png(labpbr.legacy_normals(img, strength))}
    st = stone if (stone is not None and stone.shape[1] == img.shape[1]) else None
    n, s = labpbr.pbr_maps(name, img, strength, kind, st, emissive)
    return {"_n": png(n), "_s": png(s)}


EMISSIVE_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures", "emissive-modded.txt")


def texture_normals(png_bytes, strength):
    """Legacy entry point: RGB normal + A height for the whole texture."""
    return texture_maps(png_bytes, "", strength, "legacy")["_n"]


BLOCK_TEX = re.compile(r"^assets/([^/]+)/textures/blocks/(.+)\.png$")


LIVE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".crazycraft4")


def vanilla_jar(instance, mc_jar=None):
    if mc_jar:
        return mc_jar
    p = os.path.join(instance, "bin", "minecraft.jar")
    if not os.path.exists(p):   # an Angelica game dir launches from the live bin/
        p = os.path.join(LIVE, "bin", "minecraft.jar")
    return p


def texture_sources(instance, mc_jar=None, extra_mods=()):
    """(archive path, member) for every block texture: minecraft.jar, then mods, then --mods."""
    yield vanilla_jar(instance, mc_jar)
    seen = set()
    for folder in [os.path.join(instance, "mods")] + list(extra_mods):
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                if f.endswith((".jar", ".zip")) and not re.search(r"\.(pre|broken)", f) and f not in seen:
                    seen.add(f)   # the same jar in two folders is read once
                    yield os.path.join(root, f)


def read_only_list(path):
    """Texture paths from an --only file: full asset paths, <domain>/<name> or <domain>:<name>."""
    return labpbr.read_texture_list(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=["questforge", "vibrant"], default="questforge")
    ap.add_argument("--instance", required=True)
    ap.add_argument("--shader-pack", help="questforge target: shader pack folder that gets shaders/block.properties")
    ap.add_argument("--mc-jar", help="vanilla minecraft.jar (default: <instance>/bin, else the live instance's)")
    ap.add_argument("--world", required=True, help="a world saved by this pack (for the block registry)")
    ap.add_argument("--out", required=True, help="resource pack zip to write")
    ap.add_argument("--strength", type=float, default=1.0, help="scale every material's relief")
    ap.add_argument("--no-normals", action="store_true", help="block mappings only (still writes --out)")
    ap.add_argument("--format", choices=["labpbr", "legacy"], help="map layout (default: labpbr for questforge, legacy for vibrant)")
    ap.add_argument("--only", help="file listing the textures to build maps for (one per line); default: every block texture")
    ap.add_argument("--mods", action="append", default=[], help="extra mod jar folder (repeatable), read after <instance>/mods")
    ap.add_argument("--emissive", default=EMISSIVE_DEFAULT,
                    help="file listing textures whose bright pixels emit (LabPBR _s alpha); 'none' to disable "
                         "(default: tools/textures/emissive-modded.txt)")
    args = ap.parse_args()
    if args.target == "questforge" and not args.shader_pack:
        ap.error("--target questforge needs --shader-pack DIR (Iris reads block.properties only from the pack)")
    fmt = args.format or ("labpbr" if args.target == "questforge" else "legacy")
    only = read_only_list(args.only) if args.only else None
    emissive = set()
    if args.emissive and args.emissive.lower() != "none" and os.path.exists(args.emissive):
        emissive = labpbr.read_texture_list(args.emissive)

    out = zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED)
    out.writestr("pack.mcmeta", json.dumps({"pack": {"pack_format": 1, "description":
                 "Quest Forge surfaces: generated %s relief and shader materials for every block" %
                 ("LabPBR" if fmt == "labpbr" else "")}}, indent=1))

    names = registry_names(args.world)
    if args.target == "questforge":
        write_qf_block_properties(args.shader_pack, names)
    else:
        maps, tally = block_mappings(names)
        lines = 0
        for modid, by_id in sorted(maps.items()):
            body = ["# Generated by tools/shaders/gen_surface_pack.py for Sildur's Vibrant (OptiFine E7). Do not edit."]
            for ident, members in sorted(by_id.items()):
                body.append("block.%d=%s" % (ident, " ".join(members)))
                lines += len(members)
            # Resource domains are lowercase in 1.7.10; block names keep their case.
            out.writestr("assets/%s/shaders/block.properties" % modid.lower(), "\n".join(body) + "\n")
        print("block mappings: %d blocks in %d mods  %s" % (lines, len(maps), dict(tally)))

    if not args.no_normals:
        done, seen, own = collections.Counter(), set(), 0
        stone = None   # vanilla 16x stone: the host rock most modded ores are drawn on
        try:
            with zipfile.ZipFile(vanilla_jar(args.instance, args.mc_jar)) as mc:
                stone = np.array(Image.open(io.BytesIO(mc.read("assets/minecraft/textures/blocks/stone.png"))).convert("RGBA"))
        except (OSError, KeyError) as e:
            print("  no vanilla stone for ore detection: %s" % e)
        for archive in texture_sources(args.instance, args.mc_jar, args.mods):
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
                if only is not None and m not in only:
                    continue
                if m[:-4] + "_n.png" in members:
                    own += 1
                    continue   # the mod ships its own; never override an artist's map
                kind, _, strength = classify(g.group(2))
                try:
                    maps = texture_maps(z.read(m), g.group(2), strength * args.strength, fmt, kind, stone, m in emissive)
                except Exception as e:
                    print("  skip %s: %s" % (m, e))
                    continue
                for suffix, data in maps.items():
                    out.writestr(m[:-4] + suffix + ".png", data)
                    if m + ".mcmeta" in members:
                        out.writestr(m[:-4] + suffix + ".png.mcmeta", z.read(m + ".mcmeta"))
                done[g.group(1)] += 1
        print("surface maps (%s): %d textures across %d domains%s%s" % (
            fmt, sum(done.values()), len(done), "; %d left to the mod's own _n" % own if own else "",
            "; %d of %d listed emissive textures seen" % (len(emissive & seen), len(emissive)) if emissive else ""))
        if only is not None:
            missing = sorted(only - seen)
            print("--only: %d of %d listed textures built%s" % (
                len(only) - len(missing), len(only), "; not found: " + ", ".join(missing[:10]) if missing else ""))
    out.close()
    print("wrote %s (%.1f MB)" % (args.out, os.path.getsize(args.out) / 1e6))


if __name__ == "__main__":
    main()
