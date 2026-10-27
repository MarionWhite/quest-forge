#!/usr/bin/env python3
"""Build "QF Textures" v1: vanilla's designs, Faithful 64x where the owner liked its detail, our own
drawn foliage, crops and books, and LabPBR maps from Vanilla Normals Renewed where they fit.
(v0's builder is in git history: e4dd9f6, tools/textures/build_qf_textures.py.)

    py -3.10 -I tools/textures/build_qf_textures.py --out C:\\qfb\\textures\\QFTextures-v1.zip
        [--leaf-edges none|all|sides] [--no-pbr] [--no-cit]
        [--mc-jar <minecraft.jar>] [--faithful64 <zip>] [--vnr <zip>]

What goes in, and why (docs/design/textures/direction.md, "QF Textures v1"; owner's round 7):
  * Base: vanilla 1.7.10 block textures from the player's own minecraft.jar, read at build time
    and never stored in the repo.
  * Faithful 64x (1.7.10 branch, Faithful License v4) for the list in
    resourcepacks/QFTextures/faithful64.txt: stone, stone bricks, cobble, ores, metal and gem
    blocks, glowstone, glass, and dirt with the grass side ("Faithful's dirt has the better side
    profile"; "Faithful 64 is just a better version of 32"). Its connected glass comes along, with
    its 1.13-style rules (matchBlocks=black_stained_glass) rewritten to 1.7.10 ids + metadata.
  * Our own art (tools/textures/qf_art.py; Stay True's plant art as the direction, nothing
    copied): leaves for all six woods (+ the Fast-graphics _opaque ones), bark and log ends, tall
    grass, fern, wheat 0-7, the grass top (v2: vanilla's pattern kept crisp at 32x, as r007), and bookshelves (four variants, mixed by CTM random,
    replacing Angelica's built-in horizontal bookshelf CTM).
  * --leaf-edges: the leaf "frill" options as connected textures (direction.md, "Leaf frills"):
    none (default), all (every leaf face bitten where no leaf block continues it), sides (only the
    top and bottom edges of side faces: where no leaf block is above or below).
  * Vibrance: chroma x VIBRANCE on vanilla and Faithful pixels (our drawn art is coloured by design).
  * LabPBR 1.3 (_n, _s next to each texture):
      - a texture that stays vanilla and that VNR covers: VNR's maps, converted (vnr.py);
      - a Faithful 64x texture that keeps vanilla's layout and VNR covers: VNR's shapes upscaled +
        our own fine relief from the 64x art (vnr.hybrid_*);
      - everything else (our drawn art, CTM tiles, the rest): tools/textures/labpbr.py.
  * Custom item textures (MCPatcher CIT, tools/textures/qf_items.py): potion bottles per effect and
    enchanted-book covers per enchantment. CIT is OFF in the live config; only renderq jobs with
    "cit": true turn it on. --no-cit leaves them out.
"""
import argparse, io, json, os, re, sys, zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "resourcepacks", "QFTextures")
sys.path.insert(0, os.path.join(REPO, "tools", "shaders"))
sys.path.insert(0, HERE)
import gen_surface_pack as gsp  # noqa: E402  (classify: material kind + relief strength)
import labpbr  # noqa: E402
import qf_art  # noqa: E402
import vnr as vnrmod  # noqa: E402

LIVE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".crazycraft4")
FAITHFUL64 = r"C:\qfb\faithful64\dl\Faithful-64x-Java-1.7.10.zip"
FAITHFUL_LICENSE = r"C:\qfb\faithful64\LICENSE-faithful.txt"
VERSION = "v1"
VIBRANCE = 1.10            # chroma gain; 1.0 = unchanged ("keep vibrance modest")
BLOCKS = "assets/minecraft/textures/blocks/"
CTM = "assets/minecraft/mcpatcher/ctm/"
SKIP_PBR = re.compile(r"^destroy_stage_|_overlay$|^(fire_layer|portal)")
COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray",
           "cyan", "purple", "blue", "brown", "green", "red", "black"]
WOODS = ["oak", "spruce", "birch", "jungle", "acacia", "big_oak"]
LEAF_SIZE = 32
# Faithful 64x redrew these and VNR's vanilla-layout maps no longer line up (layout_match still
# passes them): emerald's rhombus height and metal flag over Faithful's square bevels read as a murky
# green mirror (owner r008 tex-wall-close). They take our own maps from the 64x art instead.
VNR_SKIP = {"emerald_block"}
# r009 metals (owner r008 tex-wall: iron and gold "not receiving any direct light"). A metal-coded
# pixel keeps only ~30% of its diffuse light in the shader and shows reflection otherwise, and
# iron's F0 (albedo x 1.15) already clips at 1, so a brighter albedo cannot lift it. Per block:
# (metal code, dielectric F0 byte, percentile above which a pixel stays metal). Iron: every pixel
# a strong dielectric, full diffuse + an untinted reflection (plates read, lit like its neighbours).
# Gold: the same washed it pale (sky blue over yellow, render 1026-231924), so only its shine
# streaks stay metal for the gold-tinted glints, over a low-F0 base that keeps the yellow.
# --metals vnr: VNR's flag as is (every pixel metal, v1).
METAL_BLOCKS = {"iron_block": (230, 190, 100), "gold_block": (231, 60, 55)}
# r010 --diamond gem: VNR flags diamond as metal (LabPBR 230, iron), so the shader mirrors the world
# in it and keeps 30% of its diffuse. A real diamond is a dielectric, n = 2.42 -> F0 0.17 = byte 44.
GEM_BLOCKS = {"diamond_block": (230, 44, 100)}


def metal_spec(s, img, name, mode, gem=False):
    """Rewrite the F0 channel of a metal block's LabPBR _s for --metals (see METAL_BLOCKS)."""
    table = dict(METAL_BLOCKS, **(GEM_BLOCKS if gem else {}))
    if mode == "vnr" or name not in table:
        return s
    code, f0, pct = table[name]
    s = s.copy()
    s[..., 1] = f0
    if pct < 100:
        L = labpbr.lum(img)
        s[..., 1] = np.where(L > np.percentile(L, pct), code, f0)   # strict: a tied plateau stays lit
    s[img[..., 3] < 25] = (0, 0, 0, 255)
    return s


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


def vibrance(a, gain=VIBRANCE):
    """Scale each pixel's chroma around its own luminance, so greys and brightness stay put."""
    f = a[..., :3].astype(np.float32) / 255.0
    lum = (f @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    out = np.clip(lum + (f - lum) * gain, 0.0, 1.0)
    a = a.copy()
    a[..., :3] = (out * 255.0 + 0.5).astype(np.uint8)
    return a


def drawn_art(planks, grass):
    """{texture name: rgba} for everything qf_art draws (grass: vanilla's grass_top, which v2 keeps)."""
    out = {}
    for w in WOODS:
        leaf = qf_art.needles() if w == "spruce" else qf_art.leaves(w, LEAF_SIZE)
        out["leaves_" + w] = leaf
        out["leaves_%s_opaque" % w] = qf_art.opaque(leaf)
        out["log_" + w] = qf_art.bark(w)
        out["log_%s_top" % w] = qf_art.log_top(w)
    out["tallgrass"] = qf_art.tall_grass()
    out["fern"] = qf_art.fern()
    for i in range(8):
        out["wheat_stage_%d" % i] = qf_art.wheat(i)
    out["grass_top"] = qf_art.grass_top_from(grass)
    out["bookshelf"] = qf_art.bookshelf(planks=planks)
    return out


def glass_rule(text):
    """Faithful 64x's 1.13-style glass rule -> 1.7.10 ids + metadata."""
    m = re.search(r"^matchBlocks=(\S+)", text, re.M)
    name = m.group(1)
    pane = name.endswith("_pane")
    base = name[:-5] if pane else name
    if base == "glass":
        repl = "matchBlocks=%d" % (102 if pane else 20)
    else:
        col = base[:-len("_stained_glass")]
        repl = "matchBlocks=%d\nmetadata=%d" % (160 if pane else 95, COLOURS.index(col))
    return text[:m.start()] + repl + text[m.end():]


def leaf_ctm(textures, source, mode, out):
    """--leaf-edges all|sides: CTM rules + 47 tiles per broadleaf wood (module docstring)."""
    spec = json.load(open(os.path.join(SRC, "ctm47.json"), encoding="utf-8"))
    n = 0
    for w in WOODS:
        if w == "spruce":
            continue
        base = textures[BLOCKS + "leaves_%s.png" % w][0]
        d = CTM + "leaves/" + w + "/"
        faces = "sides" if mode == "sides" else "all"
        out.writestr(d + "leaves_%s.properties" % w,
                     "matchTiles=leaves_%s\nmethod=ctm\nconnect=tile\nfaces=%s\ntiles=0-46\n" % (w, faces))
        for i in range(47):
            edges = spec[str(i)]["edges"]
            if mode == "sides":
                edges = "".join(e for e in edges if e in "TB")
            p = d + "%d.png" % i
            textures[p] = (qf_art.ragged_tile(base, edges, seed=1000 + i * 7 + WOODS.index(w)), None)
            source[p] = "ctm"
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mc-jar", default=os.path.join(LIVE, "bin", "minecraft.jar"), help="read only")
    ap.add_argument("--faithful64", default=FAITHFUL64)
    ap.add_argument("--faithful-license", default=FAITHFUL_LICENSE)
    ap.add_argument("--vnr", default=vnrmod.VNR_ZIP)
    ap.add_argument("--leaf-edges", choices=("none", "all", "sides"), default="none")
    ap.add_argument("--no-pbr", action="store_true")
    ap.add_argument("--no-cit", action="store_true")
    ap.add_argument("--metals", choices=("qf", "vnr"), default="qf")
    ap.add_argument("--diamond", choices=("metal", "gem"), default="metal",
                    help="metal: VNR's metal flag (v2); gem: a dielectric, F0 44 (GEM_BLOCKS)")
    a = ap.parse_args()

    mc = zipfile.ZipFile(a.mc_jar)
    mcn = set(mc.namelist())
    fa = zipfile.ZipFile(a.faithful64)
    froot = fa.namelist()[0].split("/")[0] + "/"
    fnames = {n[len(froot):] for n in fa.namelist() if n.startswith(froot)}

    def fread(n):
        return fa.read(froot + n)
    vn = vnrmod.VNR(a.vnr)

    take = set()
    for p in load_list("faithful64.txt"):
        rx = re.compile("^" + p.replace(".", r"\.").replace("*", "[^/]*") + "$")
        hit = [m for m in fnames if m.startswith(BLOCKS) and m.endswith(".png") and rx.match(m[len(BLOCKS):-4])]
        if not hit:
            sys.exit(f"faithful64.txt: {p} matches nothing in the Faithful 64x zip")
        take.update(m for m in hit if m in mcn)        # 1.7.10 textures only (the zip carries newer ones)

    out = zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED)
    meta = json.load(open(os.path.join(SRC, "pack.mcmeta"), encoding="utf-8"))
    if a.leaf_edges != "none":
        meta["pack"]["description"] += " Leaf edges: %s." % a.leaf_edges
    out.writestr("pack.mcmeta", json.dumps(meta, indent=1, ensure_ascii=False))
    out.write(os.path.join(SRC, "CREDITS.txt"), "CREDITS.txt")
    out.write(a.faithful_license, "LICENSE-Faithful.txt")

    planks = rgba(mc.read(BLOCKS + "planks_oak.png"))
    art = drawn_art(planks, rgba(mc.read(BLOCKS + "grass_top.png")))
    ywrong = []   # _n maps whose G runs OpenGL-style (labpbr.y_sign > 0): lit from below in the shader
    tally = dict(vanilla=0, faithful64=0, drawn=0, ctm=0, pbr_vnr=0, pbr_hybrid=0, pbr_ours=0, cit=0)
    textures = {}     # path -> (rgba, mcmeta bytes or None)
    source = {}       # path -> "vanilla" | "faithful64" | "drawn" | "ctm"
    for m in sorted(x for x in mcn if x.startswith(BLOCKS) and x.endswith(".png")):
        name = m[len(BLOCKS):-4]
        mcmeta = mc.read(m + ".mcmeta") if m + ".mcmeta" in mcn else None
        if name in art:
            textures[m], source[m] = (art[name], None), "drawn"
        elif m in take:
            img = rgba(fread(m))
            mcmeta = fread(m + ".mcmeta") if m + ".mcmeta" in fnames else mcmeta
            textures[m], source[m] = (vibrance(img), mcmeta), "faithful64"
        else:
            textures[m], source[m] = (vibrance(rgba(mc.read(m))), mcmeta), "vanilla"
        tally[source[m]] += 1

    # Faithful 64x's connected glass, rules rewritten for 1.7.10
    for m in sorted(n for n in fnames if n.startswith(CTM + "glass/") and not n.endswith("/")):
        if m.endswith(".png"):
            textures[m], source[m] = (vibrance(rgba(fread(m))), None), "ctm"
        elif m.endswith(".properties"):
            folder = m.split("/")[-2]
            if folder == "glass":
                # Clear glass and its pane ship exactly as Faithful 64x has them: matchBlocks=glass /
                # glass_pane are 1.7.10 names too, and only this form beats Angelica's built-in 16x
                # glass rule (its jar's ctm/glass/glass.properties). Renamed (clear_glass) it lost
                # outright; at the jar's own path with matchBlocks=20 the jar's 'compact' rule still
                # won and drew our tile 0 on every block (the r008 v1 and v1b renders).
                out.writestr(m, fread(m))
                tally["ctm"] += 1
                continue
            # Faithful 64x names every rule glass.properties / glass_pane.properties. MCPatcher also
            # reads a rule's file name as a tile name, so every stained rule then matched CLEAR
            # glass too and the first (black) won: the r008 first render drew the clear panel
            # black. Name each stained rule after its folder, as Angelica's own defaults do
            # (black_stained_glass, black_stained_glasspane).
            pane = os.path.basename(m) == "glass_pane.properties"
            new = m.rsplit("/", 1)[0] + "/" + folder + ("pane" if pane else "") + ".properties"
            out.writestr(new, glass_rule(fread(m).decode("utf-8")))
        tally["ctm"] += 1
    # bookshelves: four variants mixed at random (replaces Angelica's built-in horizontal rule)
    d = CTM + "bookshelf/"
    out.writestr(d + "bookshelf.properties", "matchTiles=bookshelf\nmethod=random\nfaces=sides\ntiles=0-3\n")
    for i in range(4):
        p = d + "%d.png" % i
        textures[p], source[p] = (qf_art.bookshelf(seed=71 + i, planks=planks), None), "ctm"
        tally["ctm"] += 1
    if a.leaf_edges != "none":
        tally["ctm"] += leaf_ctm(textures, source, a.leaf_edges, out)

    stone = textures[BLOCKS + "stone.png"][0]
    for m, (img, mcmeta) in sorted(textures.items()):
        out.writestr(m, png(img))
        if mcmeta:
            out.writestr(m + ".mcmeta", mcmeta)
        if a.no_pbr:
            continue
        name = m[len(BLOCKS):-4] if m.startswith(BLOCKS) else m[len(CTM):-4]
        base = os.path.basename(name)
        if SKIP_PBR.search(base):
            continue
        n = s = None
        src = source[m]
        mat = name if m.startswith(BLOCKS) else os.path.basename(os.path.dirname(m))
        kind, _, strength = gsp.classify(os.path.basename(mat))
        por = 170 if kind in ("leaves", "plant") else (55 if kind == "soil" else (30 if kind == "wood" else 0))
        square = img.shape[0] == img.shape[1]
        if m.startswith(BLOCKS) and vn.has(name) and square and src in ("vanilla", "faithful64") and name not in VNR_SKIP:
            vn_n, vn_s = vn.read(name, "n"), vn.read(name, "s")
            van = rgba(mc.read(m))
            if vn_n is not None and vn_n.shape[0] == vn_n.shape[1] == van.shape[0]:
                if src == "vanilla" and img.shape == van.shape:
                    n = vnrmod.to_labpbr_n(vn_n, img)
                    s = vnrmod.to_labpbr_s(vn_s, name, img, por) if vn_s is not None else None
                    tally["pbr_vnr"] += 1
                elif src == "faithful64" and vnrmod.layout_match(img, van) > 0.45:
                    n = vnrmod.hybrid_normal(vn_n, img, strength)
                    st = stone if base.endswith("_ore") else None
                    s = vnrmod.hybrid_specular(vn_s, img, name, st, por) if vn_s is not None else None
                    tally["pbr_hybrid"] += 1
        if n is None or s is None:
            n2, s2 = labpbr.pbr_maps(mat, img, strength, kind, stone if base.endswith("_ore") else None)
            n = n2 if n is None else n
            s = s2 if s is None else s
            tally["pbr_ours"] += 1
        s = metal_spec(s, img, name, a.metals, a.diamond == "gem")
        ys = labpbr.y_sign(n, img[..., 3])
        if ys is not None and ys > 0.1:
            ywrong.append("%s %+.2f" % (name, ys))
        out.writestr(m[:-4] + "_n.png", png(n))
        out.writestr(m[:-4] + "_s.png", png(s))
        if mcmeta:
            out.writestr(m[:-4] + "_n.png.mcmeta", mcmeta)
            out.writestr(m[:-4] + "_s.png.mcmeta", mcmeta)

    if not a.no_cit:
        import qf_items
        tally["cit"] = qf_items.write_cit(out)
    out.close()
    print("QF Textures %s: %s -> %s (%.1f MB)" % (VERSION, tally, a.out, os.path.getsize(a.out) / 1e6))
    if ywrong:
        print("WARNING: %d normal maps run OpenGL-style (+G up), the shader reads DirectX: %s"
              % (len(ywrong), ", ".join(ywrong[:12])))


if __name__ == "__main__":
    main()
