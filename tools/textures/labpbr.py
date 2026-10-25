#!/usr/bin/env python3
"""LabPBR 1.3 maps from a block texture, shared by tools/textures/build_qf_textures.py (QF Textures,
vanilla + Faithful) and tools/shaders/gen_surface_pack.py (every modded texture in the pack).

The standard: https://shaderlabs.org/wiki/LabPBR_Material_Standard
    <name>_n.png   R,G  normal X,Y (DirectX: +Y points DOWN the image)
                   B    ambient occlusion (255 = none)
                   A    height (255 = the surface; never 0)
    <name>_s.png   R    perceptual smoothness (roughness = (1-R)^2)
                   G    F0: 0-229 linear F0; 230 iron, 231 gold, 232 aluminium, 233 chrome,
                        234 copper, 235 lead, 236 platinum, 237 silver; 255 = albedo is F0
                   B    0-64 porosity, 65-255 subsurface scattering
                   A    0-254 emission, 255 = none

The relief comes from the texture's own luminance (the artist's shading), so every block, vanilla or
modded, 16x or 32x, gets the same treatment from the same code; nothing is drawn by hand here.
`normal_map` is the generator's original relief (RGB OpenGL normal + A height), kept for the Vibrant
target (OptiFine E7 reads that layout) and converted to LabPBR by `labpbr_normal`.

Nothing here reads other packs' pixels: the input is the texture the game already loads.
"""
import os
import re

import numpy as np

# --- relief ---------------------------------------------------------------------------------------


def frames(a):
    """Split an animated strip (height a multiple of width) into square frames."""
    h, w = a.shape[:2]
    if h > w and h % w == 0:
        return [a[i * w:(i + 1) * w] for i in range(h // w)]
    return [a]


def normal_map(img, strength):
    """RGBA uint8 relief map for one square frame: RGB = tangent-space normal (OpenGL, +Y up),
    A = height. This is the layout OptiFine's Vibrant reads and the input to labpbr_normal."""
    a = img.astype(np.float32) / 255.0
    alpha = a[..., 3]
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    # Height is the artist's shading. Centre it per texture so a uniformly dark block is not sunk
    # and a light one raised: only the variation matters.
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
    # Height for parallax: 1.0 = surface, only gently below it; deep parallax on 16x art smears.
    h = np.clip(1.0 + np.where(solid, lum, 0.0) * 0.6, 0.0, 1.0)
    height = np.clip(h * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return np.dstack([rgb, height])


def labpbr_normal(frame, strength):
    """normal_map's relief (RGB OpenGL, A height) -> LabPBR _n (RG DirectX, B AO, A height)."""
    n = normal_map(frame, strength).astype(np.float32)
    nx, ny, hgt = n[..., 0], n[..., 1], n[..., 3]
    g = 255.0 - ny   # OpenGL +Y up -> DirectX +Y down
    # AO: pixels sunk below their 3x3 neighbourhood are shaded a little (cavity term).
    hf = hgt / 255.0
    nb = sum(np.roll(np.roll(hf, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    ao = np.clip(1.0 - np.maximum(nb - hf, 0.0) * 6.0, 0.55, 1.0)
    alpha = frame[..., 3] > 25
    ao = np.where(alpha, ao, 1.0)
    out = np.dstack([nx, g, ao * 255.0, np.maximum(hgt, 1.0)])
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def legacy_normals(rgba, strength):
    """Whole texture (animated strips included) in the old layout: RGB normal + A height."""
    return np.vstack([normal_map(f, strength) for f in frames(rgba)])


# --- specular -------------------------------------------------------------------------------------
# Per-material specular: (smoothness 0-1, F0 byte, porosity/SSS byte). Matched against the texture
# name (path inside textures/blocks/, lowercased). First match wins; vanilla names first, then the
# modded families the pack's ~5,600 textures fall into.
# "ore" as a word inside a texture name, without catching core, store, shore, more or score.
ORE_RX = re.compile(r"(^|[^a-z])ore|(?<!c)(?<!st)(?<!sh)(?<!m)(?<!sc)ore($|[^a-z])|_ore|ore_|oreblock")
SPEC = [
    # Vanilla names first, anchored, so QF Textures v0's vanilla maps stay as they were.
    (r"^(furnace|dispenser|dropper|daylight_detector|endframe|itemframe|enchanting_table|destroy_stage)", (0.25, 10, 0)),
    (r"^(emerald|lapis|redstone|coal)_block", (0.62, 14, 0)),
    (r"^sandstone|^red_sandstone|^hardened_clay|^stonebrick|^cobblestone|^stone_slab|^brick|^nether_brick|^bedrock|^netherrack|^end_stone",
     (0.24, 10, 18)),
    (r"^glass|ice$|ice_packed|(^|/|_)glass|shadedglass|reinforced.*glass|_ice($|_)|hardice|frozen", (0.96, 10, 0)),
    (r"lava|magma|molten", (0.30, 10, 0)),
    (r"^water|_still$|_flow(ing)?$|/fluids/", (1.00, 5, 0)),
    (r"^gold_block|goldblock|cube\.gold", (0.78, 231, 0)),
    (r"^iron_block|^iron_bars|^anvil|^door_iron|^hopper|^cauldron|^rail|ironblock|cube\.steel|steelblock", (0.72, 230, 0)),
    (r"copperblock|cube\.copper|copper_block", (0.74, 234, 0)),
    (r"leadblock|cube\.lead", (0.60, 235, 0)),
    (r"silverblock", (0.80, 237, 0)),
    (r"platinumblock", (0.82, 236, 0)),
    (r"tinblock|cube\.tin|bronzeblock|titanium_?block|tungstenblock|blackironblock|redironblock|limoniteblock|netherite_block", (0.70, 150, 0)),
    (r"^diamond_block|diamondblock", (0.90, 44, 0)),
    (r"rubyblock|sapphireblock|amethystblock|topazblock|peridotblock|tanzaniteblock|malachiteblock|amberblock|blockruby|blockamethyst", (0.70, 20, 0)),
    # Ores keep their host rock's base; the mineral flecks are set by ore_params / ore_mask.
    (ORE_RX.pattern, (0.24, 10, 18)),
    (r"^quartz_block|quartz|marble|limestonesmooth|siltstonesmooth|shalesmooth|polished|smooth", (0.60, 12, 0)),
    (r"^obsidian|obsidian", (0.85, 12, 0)),
    (r"^glowstone|redstone_lamp|lamp|lantern|glow", (0.40, 10, 0)),
    (r"leaves|leaf|tallgrass|fern|flower|sapling|double_plant|vine|reeds|waterlily|wheat|carrots|potatoes|deadbush|"
     r"mushroom(?!_block)|_stage_|plant|bush|moss($|_|patch)|grass\d|shrub|ivy|bamboo|kelp|coral|cattail|clover|lily", (0.18, 10, 170)),
    (r"^grass|^dirt|^farmland|^mycelium|^sand|^red_sand|^gravel|^clay|^soul_sand|^snow|dirt|sand$|sand_|mud|soil|(^|_)ash|"
     r"gravel|grass_|_grass|deadrock_surface|uberous", (0.10, 10, 55)),
    (r"^log|^planks|bookshelf|crafting|jukebox|noteblock|^trapdoor|^door_wood|ladder|plank|log_|_log|wood|"
     r"crate|barrel|drawers|shelf|table|bench|door_", (0.22, 10, 30)),
    (r"^wool|wool|carpet|cloth|curtain|(^|[^a-z])bed(_|$)", (0.05, 10, 64)),
    (r"machine|boiler|tank|engine|detector|loader|signal|oven|anchor|turbine|crusher|rolling|feeder|"
     r"frame|interface|innerwall|keypad|laser|reinforced|circuit|conduit|panel|plating|casing|monitor|computer", (0.50, 40, 0)),
    (r"stone|cobble|brick|bedrock|netherrack|end_stone|endstone|sandstone|hardened_clay|rock|basalt|"
     r"granite|diorite|andesite|concrete|mazestone|nagastone|castleblock|knightbrick|towerwood|ravaged|persegrit|"
     r"deadrock|trollsteinn|cinder", (0.24, 10, 18)),
]
SPEC = [(re.compile(r), v) for r, v in SPEC]

# Hard-coded LabPBR metal codes (G channel) by the metal's name token.
METAL_CODES = {"iron": 230, "gold": 231, "alumin": 232, "aluminium": 232, "bauxite": 232, "chrome": 233,
               "copper": 234, "lead": 235, "platinum": 236, "silver": 237}
# Ore flecks: (smoothness, F0 byte), by the mineral named in the texture. Vanilla first (exact
# texture names), then tokens for the modded ores (Legends, Railcraft, TragicMC, OreSpawn, BoP, HEE).
ORE = {"gold_ore": (0.72, 231), "iron_ore": (0.45, 230), "diamond_ore": (0.90, 44), "emerald_ore": (0.86, 40),
       "lapis_ore": (0.60, 14), "redstone_ore": (0.62, 14), "coal_ore": (0.45, 12), "quartz_ore": (0.80, 12)}
ORE_TOKENS = [
    (r"gold", (0.72, 231)), (r"iron", (0.45, 230)), (r"copper", (0.60, 234)), (r"lead", (0.50, 235)),
    (r"platinum|palladium", (0.80, 236)), (r"silver", (0.78, 237)), (r"bauxite|alumin", (0.55, 232)),
    (r"tin|cassiterite", (0.60, 150)), (r"titanium", (0.62, 140)), (r"tungsten", (0.55, 130)),
    (r"nickel|magnesite|sphalerite|zinc|limonite|silicon", (0.50, 110)),
    (r"diamond", (0.90, 44)), (r"emerald|peridot|malachite", (0.86, 40)),
    (r"ruby|sapphire|amethyst|topaz|tanzanite|amber|crystal|gem|kyber|energon|transformium|lightning|star", (0.85, 24)),
    (r"redstone|mercury|quicksilver", (0.62, 14)), (r"lapis", (0.60, 14)),
    (r"coal|coke|uranium|sulfur|sulphur|saltpeter|salt|firestone|igneous|instability|stardust|endium|powder", (0.45, 12)),
]
ORE_TOKENS = [(re.compile(r), v) for r, v in ORE_TOKENS]
EMISSIVE = re.compile(r"^(glowstone|redstone_lamp_on|torch_on|redstone_torch_on|lava_|fire_|furnace_front_on|"
                      r"pumpkin_face_on|portal|beacon)")


def lum(f):
    return f[..., :3].astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32) / 255.0


def ore_params(name):
    """(smoothness, F0 byte) for the ore flecks of a texture, or None when it is not an ore."""
    base = os.path.basename(name).lower()
    if base in ORE:
        return ORE[base]
    if not ORE_RX.search(base):
        return None
    for rx, v in ORE_TOKENS:
        if rx.search(base):
            return v
    return (0.60, 20)


def ore_mask(frame, stone=None):
    """Pixels that are the mineral, not the host rock: the difference from the host texture when a
    same-sized one is given, else the pixels that stray from the texture's own median colour."""
    rgb = frame[..., :3].astype(np.float32)
    if stone is not None and stone.shape == frame.shape:
        d = np.abs(rgb - stone[..., :3].astype(np.float32)).sum(-1)
        m = d > 40
        if 0.0 < m.mean() < 0.6:       # a plausible fleck share; else the host is not this stone
            return m
    med = np.median(rgb.reshape(-1, 3), axis=0)
    d = np.abs(rgb - med).sum(-1)
    return d > 60


def labpbr_specular(name, frame, kind=None, stone=None):
    """LabPBR _s for one frame. `kind` is gen_surface_pack.classify's material kind (emissive,
    glass, metal, polished, leaves, plant, web, ore, rough, wood, soil, cloth, default)."""
    h, w = frame.shape[:2]
    lname = name.lower()
    sm, f0, por = 0.25, 10, 0
    matched = False
    for rx, v in SPEC:
        if rx.search(lname):
            sm, f0, por = v
            matched = True
            break
    if kind == "glass":
        # Glass is glass whatever else the name says (reinforced glass, laboratory glass).
        sm, f0, por = max(sm, 0.9), 10, 0
    elif not matched:
        # The classifier's kind decides when the name says nothing.
        if kind == "metal":
            code = next((c for t, c in METAL_CODES.items() if t in lname), None)
            sm, f0, por = 0.65, (code if code else 120), 0
        elif kind in ("leaves", "plant"):
            sm, f0, por = 0.18, 10, 170
        elif kind == "polished":
            sm, f0, por = 0.60, 12, 0
        elif kind == "soil":
            sm, f0, por = 0.10, 10, 55
        elif kind == "wood":
            sm, f0, por = 0.22, 10, 30
        elif kind == "cloth":
            sm, f0, por = 0.05, 10, 64
    L = lum(frame)
    # Highlights catch light a touch better than crevices: +-0.06 around the base.
    smooth = np.clip(sm + (L - L.mean()) * 0.25, 0.0, 1.0)
    F0 = np.full((h, w), float(f0))
    op = ore_params(name)
    if op is not None:
        m = ore_mask(frame, stone)
        smooth = np.where(m, op[0], smooth)
        F0 = np.where(m, float(op[1]), F0)
    emis = np.full((h, w), 255.0)
    if EMISSIVE.search(os.path.basename(lname)) or kind == "emissive":
        e = np.clip((L - 0.45) / 0.5, 0.0, 1.0)
        emis = np.where(e > 0.02, np.minimum(e * 254.0, 254.0), 255.0)
    out = np.dstack([smooth * 255.0, F0, np.full((h, w), float(por)), emis])
    out = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    if not (re.search(r"glass|ice", lname) or kind == "glass"):   # glass stays smooth through clear pixels
        out[frame[..., 3] < 25] = (0, 0, 0, 255)
    return out


def pbr_maps(name, rgba, strength, kind=None, stone=None):
    """(_n, _s) LabPBR maps for a whole texture, animated strips included. `stone` is the host rock
    texture at the same size (vanilla 16x stone for modded ores, Faithful stone for Faithful ores)."""
    fr = frames(rgba)
    st = frames(stone)[0] if stone is not None else None
    n = np.vstack([labpbr_normal(f, strength) for f in fr])
    s = np.vstack([labpbr_specular(name, f, kind, st) for f in fr])
    return n, s


def check_layout(n, s):
    """Sanity checks on one (_n, _s) pair; returns a list of problems (empty = fine)."""
    bad = []
    if n.shape[-1] != 4 or s.shape[-1] != 4:
        bad.append("not RGBA")
    if (n[..., 3] == 0).any():
        bad.append("_n height has 0 (LabPBR: at least 1)")
    if n[..., 2].min() < 100:
        bad.append("_n AO darker than 0.4")
    if (s[..., 1] > 237).any() and not (s[..., 1] == 255).all():
        if ((s[..., 1] > 237) & (s[..., 1] < 255)).any():
            bad.append("_s F0 in the reserved 238-254 range")
    return bad
