#!/usr/bin/env python3
"""Stay True's leaves and crops, ported into QF Textures (owner's call 2026-10-27, CLAUDE.md "Licences").

Stay True (HaiMcFly, 1.21, 16x) is all-rights-reserved except for the owner's private pack: its files live only
in C:\\qf-world\\reference-packs\\Stay True 1\\ and are READ HERE AT BUILD TIME. Nothing from it is ever committed
or shown on the public site; the built zip is git-ignored (*.zip).

What it does, read from Stay True's own JSON (no shapes invented here):
  * leaves: blockstates/<wood>_leaves.json list 2-3 models per block, picked at random per position. Each model is
    the full leaf cube (texture "all") plus two big vertical planes ("bushy", a round 32x32 clump spanning 2 blocks),
    rotated +-22.5 degrees about Y, unshaded, usually tinted. models/block/leaves_cross{,1,2}.json etc.
  * crops: wheat ages 5-7, carrots and potatoes age 7 pick from weighted models; some are the plain crop (one block),
    the rest are two blocks tall: the same four planes from y -1 to 16 (a "bottom" sprite) and 16 to 32 ("top").

This module turns that into 1.7.10 terms:
  * textures under 1.7.10 names (leaves_oak.png, wheat_stage_7.png, ...) and extra sprites under
    textures/blocks/staytrue/<Stay True name>.png, nearest-upscaled 4x (16 px per block -> 64, like Faithful 64x);
  * assets/minecraft/qf/staytrue_models.txt, which qf-tweaks (StayTrueModels) reads at texture stitch: per 1.7.10
    block and metadata, the weighted variants and every face as four rotated vertices. The geometry is computed
    here from the model JSON (Minecraft's FaceBakery rules), so the Java side holds no Stay True shapes.

    py -3.10 -I tools/textures/staytrue.py --stay-true "C:\\qf-world\\reference-packs\\Stay True 1" --dump
prints the variant table; build_qf_textures.py --stay-true PATH writes it all into the pack.
"""
import argparse, io, json, math, os, re, sys

import numpy as np
from PIL import Image

DEFAULT_ROOT = r"C:\qf-world\reference-packs\Stay True 1"
SCALE = 4                       # Stay True 16 px/block -> 64 px/block (Faithful 64x)
SPRITE_DIR = "staytrue/"        # extra sprites: textures/blocks/staytrue/<name>.png, icon name "staytrue/<name>"
SPEC_PATH = "assets/minecraft/qf/staytrue_models.txt"

# 1.7.10 leaf blocks: (registry name, meta & 3, 1.7.10 texture kind, Stay True blockstate, fixed 1.7.10 tint or None).
# 1.7.10 BlockOldLeaf.colorMultiplier: meta&3 == 1 -> pine 0x619961, == 2 -> birch 0x80A755, else the biome foliage.
LEAVES = [
    ("leaves", 0, "oak", "oak_leaves", None),
    ("leaves", 1, "spruce", "spruce_leaves", 0x619961),
    ("leaves", 2, "birch", "birch_leaves", 0x80A755),
    ("leaves", 3, "jungle", "jungle_leaves", None),
    ("leaves2", 0, "acacia", "acacia_leaves", None),
    ("leaves2", 1, "big_oak", "dark_oak_leaves", None),
]
# 1.7.10 crops: (registry name, Stay True blockstate, 1.7.10 icon for each meta 0..7 as "<stage>").
# BlockCrops: icon = meta (wheat_stage_0..7). BlockCarrot/BlockPotato: meta 0-1 -> 0, 2-3 -> 1, 4-6 -> 2, 7 -> 3.
CROPS = [
    ("wheat", "wheat", ["wheat_stage_%d" % m for m in range(8)]),
    ("carrots", "carrots", ["carrots_stage_%d" % s for s in (0, 0, 1, 1, 2, 2, 2, 3)]),
    ("potatoes", "potatoes", ["potatoes_stage_%d" % s for s in (0, 0, 1, 1, 2, 2, 2, 3)]),
]

# Minecraft's FaceBakery corner order per face (1.8+ EnumFaceDirection): which of from/to each vertex takes, as
# (x, y, z) with 0 = from, 1 = to. Vertex i gets uv (u0,v0), (u0,v1), (u1,v1), (u1,v0). Counter-clockwise seen from
# outside, so each face is single-sided like in the game.
FACE_CORNERS = {
    "down":  [(0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)],
    "up":    [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    "north": [(1, 1, 0), (1, 0, 0), (0, 0, 0), (0, 1, 0)],
    "south": [(0, 1, 1), (0, 0, 1), (1, 0, 1), (1, 1, 1)],
    "west":  [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)],
    "east":  [(1, 1, 1), (1, 0, 1), (1, 0, 0), (1, 1, 0)],
}
UV_CORNERS = [(0, 1), (0, 3), (2, 3), (2, 1)]


class StayTrue:
    def __init__(self, root):
        self.root = root
        self.mc = os.path.join(root, "assets", "minecraft")
        if not os.path.isdir(os.path.join(self.mc, "blockstates")):
            sys.exit("Stay True not found at %s (expected assets/minecraft/blockstates)" % root)

    def blockstate(self, name):
        return json.load(open(os.path.join(self.mc, "blockstates", name + ".json"), encoding="utf-8"))

    def model(self, ref):
        """A model with its parent chain resolved inside Stay True. Returns (textures, elements, ao, parent_outside)."""
        name = ref.split("/")[-1]
        textures, elements, ao, outside = {}, None, True, None
        chain = []
        while name:
            p = os.path.join(self.mc, "models", "block", name + ".json")
            if not os.path.exists(p):
                outside = "block/" + name          # e.g. block/crop, block/block: vanilla's own
                break
            d = json.load(open(p, encoding="utf-8"))
            chain.append(d)
            par = d.get("parent")
            name = par.split("/")[-1] if par else None
        for d in reversed(chain):                  # child entries win
            textures.update(d.get("textures", {}))
            if "elements" in d:
                elements = d["elements"]
            if "ambientocclusion" in d:
                ao = d["ambientocclusion"]
        return textures, elements, ao, outside

    def png(self, ref):
        name = ref.split("/")[-1]
        p = os.path.join(self.mc, "textures", "block", name + ".png")
        a = np.asarray(Image.open(p).convert("RGBA"))
        return np.repeat(np.repeat(a, SCALE, 0), SCALE, 1)          # nearest, 16 px/block -> 64


def resolve(textures, key):
    """'#bushy' -> 'block/oak_leaves_bushy' through the model's texture variables."""
    seen = 0
    while key.startswith("#") and seen < 8:
        key = textures.get(key[1:], key)
        seen += 1
    if key.startswith("#"):
        raise ValueError("unresolved texture " + key)
    return key


def rotate(p, rot):
    """Minecraft's element rotation (FaceBakery, no rescale): right-handed about the axis through origin."""
    if not rot:
        return p
    a = math.radians(rot["angle"])
    c, s = math.cos(a), math.sin(a)
    ox, oy, oz = rot["origin"]
    x, y, z = p[0] - ox, p[1] - oy, p[2] - oz
    axis = rot["axis"]
    if axis == "y":
        x, z = x * c + z * s, -x * s + z * c
    elif axis == "x":
        y, z = y * c - z * s, y * s + z * c
    else:
        x, y = x * c - y * s, x * s + y * c
    if rot.get("rescale"):
        raise ValueError("rescale not supported")
    return (x + ox, y + oy, z + oz)


def face_quad(el, face, f):
    """Four (x, y, z, u, v): positions in blocks (model units / 16), uv in sprite units 0..16."""
    fr, to = el["from"], el["to"]
    uv = f.get("uv")
    if uv is None:
        raise ValueError("face without uv")
    out = []
    for (cx, cy, cz), (ui, vi) in zip(FACE_CORNERS[face], UV_CORNERS):
        p = (to[0] if cx else fr[0], to[1] if cy else fr[1], to[2] if cz else fr[2])
        p = rotate(p, el.get("rotation"))
        out.append((p[0] / 16, p[1] / 16, p[2] / 16, uv[ui], uv[vi]))
    return out


def is_cube(el):
    return el["from"] == [0, 0, 0] and el["to"] == [16, 16, 16] and not el.get("rotation") \
        and set(el["faces"]) == set(FACE_CORNERS)


def variants_of(entry):
    """A blockstate entry -> [(model ref, weight)]."""
    if isinstance(entry, dict):
        entry = [entry]
    return [(e["model"], e.get("weight", 1)) for e in entry]


def build(root):
    """Everything the pack needs: (textures {1.7.10 or staytrue/ name: rgba}, spec text, table lines for --dump)."""
    st = StayTrue(root)
    tex, spec, table = {}, [], []
    spec.append("# Quest Forge: Stay True's leaf and crop models for qf-tweaks (StayTrueModels). GENERATED by")
    spec.append("# tools/textures/staytrue.py from Stay True's blockstates and models; do not edit.")
    spec.append("# target <block> <meta>        variants for that 1.7.10 block + metadata (leaves: meta & 3)")
    spec.append("# variant <weight> <mode> <sprite|->   mode cube: vanilla leaf cube with this sprite, then the quads;")
    spec.append("#   icon: vanilla crop planes with this sprite; quads: only the quads. - = the block's own icon")
    spec.append("# quad <sprite> <tint 0|1> then 4 x (x y z u v): blocks from the block's corner, uv 0..16, CCW = front")

    def sprite(ref, data=None):
        name = SPRITE_DIR + ref.split("/")[-1]
        if name not in tex:
            tex[name] = st.png(ref) if data is None else data
        return name

    def quad_line(textures, el, face, f, tint_ok=True):
        ref = resolve(textures, f["texture"])
        nm = sprite(ref)
        tint = 1 if ("tintindex" in f and tint_ok) else 0
        q = face_quad(el, face, f)
        return "quad %s %d %s" % (nm, tint, " ".join("%.5f %.5f %.5f %.3f %.3f" % v for v in q))

    # ---- leaves
    for block, meta, kind, bs, fixed in LEAVES:
        state = st.blockstate(bs)["variants"]
        lists = {json.dumps(v, sort_keys=True) for v in state.values()}
        if len(lists) != 1:
            raise ValueError("%s: variants differ by distance; not handled" % bs)
        vs = variants_of(next(iter(state.values())))
        spec.append("target %s %d" % (block, meta))
        base_cube = None
        for ref, w in vs:
            textures, elements, ao, outside = st.model(ref)
            if not elements or not is_cube(elements[0]):
                raise ValueError("%s: expected a leaf cube + planes, got parent %s" % (ref, outside))
            cube = elements[0]
            cube_refs = {resolve(textures, f["texture"]) for f in cube["faces"].values()}
            if len(cube_refs) != 1:
                raise ValueError("%s: the cube has several textures %s" % (ref, cube_refs))
            cube_ref = cube_refs.pop()
            cube_tinted = all("tintindex" in f for f in cube["faces"].values())
            img = st.png(cube_ref)
            if not cube_tinted:
                # 1.7.10 tints every leaf cube; undo a fixed tint so the screen shows Stay True's own colours.
                if fixed is None:
                    raise ValueError("%s: untinted cube on a biome-coloured 1.7.10 leaf" % ref)
                img = untint(img, fixed)
            if base_cube is None:
                base_cube = cube_ref
                tex["leaves_" + kind] = img                 # the block's own icon (1.7.10 name)
                cube_name = "-"
            elif cube_ref == base_cube or img.tobytes() == tex["leaves_" + kind].tobytes():
                cube_name = "-"
            else:
                cube_name = sprite(cube_ref, img)
            spec.append("variant %d cube %s" % (w, cube_name))
            planes = []
            for el in elements[1:]:
                for face, f in el["faces"].items():
                    planes.append(quad_line(textures, el, face, f))
            spec.extend(planes)
            bushy = sorted({resolve(textures, f["texture"]).split("/")[-1] for el in elements[1:] for f in el["faces"].values()})
            table.append("%-8s %d %-7s w%-2d cube %-22s planes %d %s rot %s" % (
                block, meta, kind, w, cube_ref.split("/")[-1] + ("" if cube_tinted else " (untinted)"), len(planes),
                bushy, [el.get("rotation", {}).get("angle") for el in elements[1:]]))

    # ---- crops
    for block, bs, icons in CROPS:
        state = st.blockstate(bs)["variants"]
        for meta in range(8):
            entry = state["age=%d" % meta]
            vs = variants_of(entry)
            base_icon = icons[meta]
            models = [(ref, w, crop_model(st, ref)) for ref, w in vs]
            distinct = {json.dumps([m[2][0], m[2][1]], sort_keys=True) for m in models}
            first_tex = models[0][2][0]
            if models[0][2][3] != "block/crop":
                raise ValueError("%s age %d: first model is not a plain crop" % (bs, meta))
            if base_icon not in tex:
                tex[base_icon] = st.png(resolve(first_tex, "#crop"))      # 1.7.10 icon <- the plain model's sprite
            if len(distinct) == 1:
                continue                                                # one look: the texture copy is all it needs
            spec.append("target %s %d" % (block, meta))
            for ref, w, (textures, elements, ao, outside) in models:
                if outside == "block/crop":
                    s = resolve(textures, "#crop")
                    nm = "-" if st.png(s).tobytes() == tex[base_icon].tobytes() else sprite(s)
                    spec.append("variant %d icon %s" % (w, nm))
                    table.append("%-8s %d w%-2d icon  %s" % (block, meta, w, s.split("/")[-1]))
                elif elements:
                    spec.append("variant %d quads -" % w)
                    n = 0
                    for el in elements:
                        for face, f in el["faces"].items():
                            spec.append(quad_line(textures, el, face, f))
                            n += 1
                    ys = sorted({v for el in elements for v in (el["from"][1], el["to"][1])})
                    table.append("%-8s %d w%-2d quads %d faces y %s %s" % (
                        block, meta, w, n, ys, sorted({resolve(textures, f["texture"]).split("/")[-1]
                                                       for el in elements for f in el["faces"].values()})))
                else:
                    raise ValueError("%s: unexpected model shape (parent %s)" % (ref, outside))
    return tex, "\n".join(spec) + "\n", table


def crop_model(st, ref):
    """st.model, except a model Stay True does not ship (carrots_stage0, ...) is vanilla 1.21's: the plain crop with
    the sprite of the same name ({"parent": "block/crop", "textures": {"crop": "block/<name>"}})."""
    textures, elements, ao, outside = st.model(ref)
    if outside == "block/" + ref.split("/")[-1] and not textures:
        return {"crop": "block/" + ref.split("/")[-1]}, None, True, "block/crop"
    return textures, elements, ao, outside


def untint(img, colour):
    """Divide the RGB by a fixed vertex tint so tint x result = the original (no clipping in Stay True's birch)."""
    t = np.array([(colour >> 16) & 255, (colour >> 8) & 255, colour & 255], np.float32)
    out = img.copy()
    rgb = img[..., :3].astype(np.float32) * 255.0 / t
    if (rgb[img[..., 3] > 0] > 255.5).any():
        raise ValueError("untint would clip")
    out[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stay-true", default=DEFAULT_ROOT)
    ap.add_argument("--dump", action="store_true", help="print the variant table")
    ap.add_argument("--spec", help="write the model spec here too (a local file for checking; never commit it)")
    a = ap.parse_args()
    tex, spec, table = build(a.stay_true)
    if a.dump:
        print("\n".join(table))
        print("%d textures/sprites, spec %d lines" % (len(tex), spec.count("\n")))
    if a.spec:
        open(a.spec, "w", encoding="utf-8").write(spec)


if __name__ == "__main__":
    main()
