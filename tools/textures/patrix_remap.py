#!/usr/bin/env python3
"""r012: Patrix 32x mob skins remapped onto 1.7.10's model UVs, face by face (part of r007packs.py's mobs part).

Patrix draws most mobs for its own OptiFine CEM models (assets/minecraft/optifine/cem/<mob>.jem), whose boxes and
UVs differ from 1.7.10's ModelCow, ModelIronGolem and the rest, so their skins cannot be copied as they are (r011:
the cow's body pattern landed on its head). Every CEM box gives an explicit UV rectangle per face (uvNorth ...), so
each 1.7.10 box here takes the six faces of the Patrix box(es) that play its part, resampled (nearest) to the 1.7.10
face size and written at 1.7.10's box-UV layout:
    east (u, v+d) d x h   north (u+d, v+d) w x h   west (u+d+w, v+d) d x h   south (u+2d+w, v+d) w x h
    up (u+d, v) w x d     down (u+d+w, v) w x d
A 1.7.10 box made of several Patrix boxes (the golem's 30 px arm = shoulder + arm + hand) stacks their side faces.
A few Patrix parts that stick out (snouts, noses) are painted onto the 1.7.10 face behind them ("decals").

What this cannot do: Patrix's shapes. A 6 x 6 cow head becomes an 8 x 8 one, so its pixels grow by 4:3, unevenly
(nearest). The mobs where boxes nearly match (iron golem, zombie pigman, witch) keep Patrix's look; the passive
ones are a compromise to judge in game. Patrix's real shapes need Java model renderers (see r012-packs.md).
"""
import io, json

import numpy as np
from PIL import Image

CEM = "assets/minecraft/optifine/cem/"
E = "assets/minecraft/textures/entity/"
FLIPS_STD = {"up": (True, True), "down": (True, False)}      # Blockbench box-UV export flips these vs. 1.7.10
OPP = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}

# 1.7.10 target -> (Patrix texture, Patrix jem, vanilla size at 1x, boxes)
# box: (u, v, w, h, d, [Patrix boxes "path#i", stacked top to bottom], [decals (src, face, dx, dy)]) ; src None = clear
SPECS = {
    "zombie_pigman.png": ("piglin/zombified_piglin.png", "zombified_piglin", (64, 32), [
        (0, 0, 8, 8, 8, ["headwear/head2#0"], [("headwear/head2/nose#1", "north", 2, 4)]),
        (32, 0, 8, 8, 8, None, []),
        (16, 16, 8, 12, 4, ["body#0"], []),
        (40, 16, 4, 12, 4, ["right_arm#1"], []),
        (0, 16, 4, 12, 4, ["right_leg#1"], [])]),
    "iron_golem.png": ("iron_golem/iron_golem.png", "iron_golem", (128, 128), [
        (0, 0, 8, 10, 8, ["body/body_top/head2#0"], []),
        (24, 0, 2, 4, 2, ["body/body_top/head2/bone12#0"], []),
        (0, 40, 18, 12, 11, ["body/body_top/body_torso#0"], []),
        (0, 70, 9, 5, 6, ["body/waist#0"], []),
        (60, 21, 4, 30, 6, ["right_arm/right_shoulder#0", "right_arm/right_arm2#0",
                            "right_arm/right_arm2/right_hand#0"], []),
        (60, 58, 4, 30, 6, ["left_arm/left_shoulder#0", "left_arm/left_arm2#0", "left_arm/left_arm2/left_hand#0"], []),
        (37, 0, 6, 16, 5, ["right_leg/right_leg2/right_leg_bottom/right_leg_top#0",
                           "right_leg/right_leg2/right_leg_bottom#0", "right_leg/right_leg2/right_foot#0"], []),
        (60, 0, 6, 16, 5, ["left_leg/left_leg2/left_leg_bottom/left_leg_top#0",
                           "left_leg/left_leg2/left_leg_bottom#0", "left_leg/left_leg2/left_foot#0"], [])]),
    "witch.png": ("witch/witch.png", "witch", (64, 128), [
        (0, 0, 8, 10, 8, ["body/head2#0"], []),
        (24, 0, 2, 4, 2, ["body/head2/nose2#0"], []),
        (16, 20, 8, 12, 6, ["body/body2#0"], []),
        (0, 38, 8, 18, 6, ["body/coat1#0", "body/coat2#0"], []),
        (44, 22, 4, 8, 4, ["arms/arms2#1"], []),
        (40, 38, 8, 4, 4, ["arms/arms2#0"], []),
        (0, 22, 4, 12, 4, ["right_leg#0"], []),
        (0, 64, 10, 2, 10, ["body/hat#0"], []),
        (0, 76, 7, 4, 7, ["body/hat/hat2#0"], []),
        (0, 87, 4, 4, 4, ["body/hat/hat2/hat3#0"], []),
        (0, 95, 1, 2, 1, ["body/hat/hat2/hat3/hat4#0"], [])]),
    "cow/cow.png": ("cow/cow_temperate.png", "cow", (64, 32), [
        (0, 0, 8, 8, 6, ["body/head2#0"], [("body/head2/snout/nose2#0", "north", 2, 4)]),
        (22, 0, 1, 3, 1, ["body/head2/horns#0"], []),
        (18, 4, 12, 18, 10, ["body/rotation#0"], []),
        (52, 0, 4, 6, 1, ["body/udder#1"], []),
        (0, 16, 4, 12, 4, ["leg1#0"], [])]),
    "sheep/sheep.png": ("sheep/sheep.png", "sheep", (64, 32), [
        (0, 0, 6, 6, 8, ["body/head2#0"], [("body/head2/snout/snout2#0", "north", 1, 2)]),
        (28, 8, 8, 16, 6, ["body/rotation#0"], []),
        (0, 16, 4, 12, 4, ["leg1#0"], [])]),
    "sheep/sheep_fur.png": ("sheep/sheep_wool.png", "sheep_wool", (64, 32), [
        (0, 0, 6, 6, 6, ["body/head2#0"], []),
        (28, 8, 8, 16, 6, ["body/rotation#0"], []),
        (0, 16, 4, 6, 4, ["leg1/leg1_wool#0"], [])]),
    "chicken.png": ("chicken/chicken_temperate.png", "chicken", (64, 32), [
        (0, 0, 4, 6, 3, ["body/head2#1"], []),
        (14, 0, 4, 2, 2, ["body/head2#0"], []),
        (14, 4, 2, 2, 2, ["body/head2/wattle#0"], []),
        (0, 9, 6, 8, 6, ["body/rotation#0"], []),
        (26, 0, 3, 5, 3, ["right_leg/right_leg2#0"], []),
        (24, 13, 1, 4, 6, ["body/right_wing2#0"], [])]),
    "blaze.png": ("blaze/blaze.png", "blaze", (64, 32), [
        (0, 0, 8, 8, 8, ["stick1/body/head2/bone1/bone2#0"], []),
        (0, 16, 2, 8, 2, ["stick1/body/layer2/rod5#0"], [])]),
}

# Specs kept for the record but not used: in the r012 render (1028-150936) these landed wrong in game.
DROPPED = {
    "zombie_pigman.png": "the piglin's 10-wide head resampled to 8x8 is pink/green noise, no face",
    "blaze.png": "Patrix's flame-shaped head faces are mostly transparent: in game the head is a thin flame sliver",
}
USE = [t for t in SPECS if t not in DROPPED]


def boxes(jem):
    """{"part/sub#i": box} for every box in the jem, i counting boxes at that exact path."""
    out = {}

    def walk(m, path):
        for i, b in enumerate(m.get("boxes", [])):
            out["%s#%d" % (path, i)] = b
        for s in m.get("submodels", []):
            walk(s, path + "/" + str(s.get("id", "?")))
    for m in jem["models"]:
        walk(m, m.get("part", "?"))
    return out


def std_faces(u, v, w, h, d):
    """1.7.10 box-UV rectangles (x, y, w, h) per face."""
    return {"east": (u, v + d, d, h), "north": (u + d, v + d, w, h), "west": (u + d + w, v + d, d, h),
            "south": (u + 2 * d + w, v + d, w, h), "up": (u + d, v, w, d), "down": (u + d + w, v, w, d)}


def face_img(tex, k, box, face):
    """The Patrix face as an image in 1.7.10's orientation for that face, or None."""
    if "textureOffset" in box:
        u, v = box["textureOffset"]
        w, h, d = box["coordinates"][3:6]
        fx, fy, fw, fh = std_faces(u, v, int(round(w)), int(round(h)), int(round(d)))[face]
        if fw <= 0 or fh <= 0:
            return None
        return tex.crop((fx * k, fy * k, (fx + fw) * k, (fy + fh) * k))
    key = "uv" + face.capitalize()
    if key not in box:
        return None
    u1, v1, u2, v2 = box[key]
    x0, x1, y0, y1 = min(u1, u2), max(u1, u2), min(v1, v2), max(v1, v2)
    if x1 - x0 < 1e-6 or y1 - y0 < 1e-6:
        return None
    im = tex.crop((int(round(x0 * k)), int(round(y0 * k)), int(round(x1 * k)), int(round(y1 * k))))
    fh_, fv_ = FLIPS_STD.get(face, (False, False))
    if (u1 > u2) != fh_:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if (v1 > v2) != fv_:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return im


def any_face(tex, k, box, face):
    for f in (face, OPP[face], "north", "south", "east", "west", "up", "down"):
        im = face_img(tex, k, box, f)
        if im is not None:
            return im
    return None


def remap(px, target):
    """Build the 1.7.10 skin for `target` from Patrix (a Pack). Returns an RGBA image (2x the vanilla size)."""
    tpath, jem, (vw, vh), spec = SPECS[target]
    tex = px.img(E + tpath)
    j = json.loads(px.read(CEM + jem + ".jem").decode("utf-8-sig"))
    k = tex.width // j["textureSize"][0]
    bx = boxes(j)
    out = Image.new("RGBA", (vw * k, vh * k))
    for u, v, w, h, d, srcs, decals in spec:
        rects = std_faces(u, v, w, h, d)
        if srcs is None:
            continue                                            # left transparent (an overlay layer we clear)
        for face, (fx, fy, fw, fh) in rects.items():
            if fw <= 0 or fh <= 0:
                continue
            if face in ("east", "west", "north", "south") and len(srcs) > 1:
                parts = [any_face(tex, k, bx[s], face) for s in srcs]
                parts = [p for p in parts if p is not None]
                tw = fw * k
                col = Image.new("RGBA", (tw, sum(p.height for p in parts)))
                y = 0
                for p in parts:
                    col.paste(p.resize((tw, p.height), Image.NEAREST), (0, y))
                    y += p.height
                img = col
            else:
                src = srcs[0] if face != "down" else srcs[-1]
                img = any_face(tex, k, bx[src], face)
                if img is None:
                    continue
            out.paste(img.resize((fw * k, fh * k), Image.NEAREST), (fx * k, fy * k))
        for src, face, dx, dy in decals:
            img = face_img(tex, k, bx[src], face)
            if img is not None:
                fx, fy, fw, fh = rects["north"]
                out.alpha_composite(img, ((fx + dx) * k, (fy + dy) * k))
    return out


def png(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()
