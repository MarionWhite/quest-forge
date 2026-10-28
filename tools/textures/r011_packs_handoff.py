#!/usr/bin/env python3
"""Write the r011 pack-copy scenes for the Shader Lab (C:\\qfb\\shaderdev\\r011\\packs_scenes.json + crops).

    py -3.10 -I tools/textures/r011_packs_handoff.py

Reads the frames renderq left in C:\\qfb\\shaderdev\\rounds\\screenshots (renders 1027-222844-textures-r011-packs,
1027-223357-textures-r011-gui, 1027-223454-textures-r011-cost; tags below) and writes JPEG crops next to the JSON,
in the r010 texture_scenes.json schema. A = round 10 as it stands (QF-v3c), B = the r007 packs copied in.
The frames show third-party pack art: internal Lab review only, never the public site.
"""
import json, os, re

from PIL import Image

SHOTS = r"C:\qfb\shaderdev\rounds\screenshots"
BENCH = r"C:\qfb\shaderdev\rounds\bench"
OUT = r"C:\qfb\shaderdev\r011"
CROPS = os.path.join(OUT, "packs")
A, B, C = "r11p0", "r11p1", "r11p2"          # r010 / + items, mobs, shelves, TNT, env / + GUI
B2 = "r11p3"                                 # B after review (compass, TNT lettering, 19 mobs): used where rendered
GUI_BOX = (600, 150, 1960, 1290)            # the screen at GUI scale 6 on 2560x1440, centred
HUD_BOXES = [(0, 0, 2560, 260), (640, 1100, 1920, 1440)]   # boss bar strip; hotbar, hearts, food, XP
PLAQUE = ("We will lighten the title plaques unless you object. Cause: 1.7.10 writes screen titles in fixed dark "
          "grey, which barely reads on Faithless's dark wooden plaques.")
GUI_FLAWS = {"gui_chest": "Keep?",      # grey plaques: its titles read
             "gui_enchanting": "We will paint out its drawn book (and lighten the plaques) unless you object. Cause: "
                               "1.7.10 floats its own 3D book over the spot where Faithless painted a book on the "
                               "table, so the two overlap."}


def frame(tag, scene):
    p = os.path.join(SHOTS, "bench-%s-%s.png" % (tag, scene))
    return p if os.path.exists(p) else None


def crop(tag, scene, box=None, name=None):
    p = frame(tag, scene)
    if p is None:
        return None
    im = Image.open(p).convert("RGB")
    if box == "hud":
        parts = [im.crop(b) for b in HUD_BOXES]
        w = max(x.width for x in parts)
        out = Image.new("RGB", (w, sum(x.height for x in parts)), (20, 20, 24))
        y = 0
        for x in parts:
            out.paste(x, ((w - x.width) // 2, y))
            y += x.height
        im = out
    elif box:
        im = im.crop(box)
    os.makedirs(CROPS, exist_ok=True)
    dst = os.path.join(CROPS, "%s-%s.jpg" % (name or scene, tag))
    im.save(dst, quality=90)
    return dst


def cost(tag, scene):
    """Mean frame time (ms) of a cost-mode scene from its bench txt, or None."""
    p = os.path.join(BENCH, tag + ".txt")
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8", errors="replace"):
        if line.split()[:1] == [scene]:
            m = re.search(r"p50\s+([\d.]+)\s*ms", line)      # "mean" is fps; p50 is ms
            return float(m.group(1)) if m else None
    return None


def opt(key, label, img, desc, ms=None):
    return {"key": key, "label": label, "img": img, "ms": ms, "desc": desc}


def main():
    scenes = []

    def pair(sid, name, question, prompt, scene, box=None, desc_a="", desc_b="", tag_b=B, cost_scene=None):
        if tag_b == B and frame(B2, scene):
            tag_b = B2
        a, b = crop(A, scene, box, sid), crop(tag_b, scene, box, sid)
        if not (a and b):
            print("missing frames for", sid)
            return
        ma = cost("r11c0", cost_scene) if cost_scene else None
        mb = cost("r11c1", cost_scene) if cost_scene else None
        scenes.append({"id": sid, "name": name, "question": question, "notePrompt": prompt,
                       "options": [opt("A", "Round 10 (ours)", a, desc_a, ma), opt("B", "Copied from the pack", b, desc_b, mb)]})

    pair("pk-items", "Items: Faithless's whole set, in game",
         "Your round 10 ask: one more full art style for all items before we commit. B is Faithless's sprites copied "
         "as they are, under 1.7.10 names (204 items, its animations kept: buckets, discs, redstone, glowstone dust, "
         "XP bottle), its own bottle per potion effect (and a different cap for II and extended), a book per "
         "enchantment, worn-down sprites for damaged tools and arrow/seed piles by stack size. Top to bottom: tools, "
         "food, materials, potions (drink then splash), books + a worn sword and pickaxe + arrows x1/x4/x16.",
         "Faithless for all items? Any you want kept as round 10?", "r11_items",
         desc_a="Vanilla items, our r010 potion bottles and book covers.",
         desc_b="Faithless v1.2 copied in (1.7.10 names; compass rebuilt from its 50 frames; clock kept: its clock is a 3D dial).",
         cost_scene="r11_items")
    pair("pk-items-close", "Potions and books up close", "The bottom two rows from 2.6 blocks.",
         "Potion shapes and book covers read?", "r11_items_bl")
    pair("pk-gui-inv", "Inventory", "Faithless's illustrated inventory. 1.9 moved the 2x2 grid and added an "
         "off-hand slot; the grid is moved back to where 1.7.10 puts its slots and the off-hand slot painted out. "
         "B also shows its HUD: hearts, armour, food, XP and hotbar.", "Keep its inventory?", "gui_inventory",
         box=GUI_BOX, tag_b=C, desc_b="Faithless GUI (r11p2).")
    for sc, nm in (("gui_creative_combat", "Creative: combat tab"), ("gui_creative_brewing", "Creative: brewing tab")):
        pair("pk-" + sc[4:].replace("_", "-"), nm, "Faithless's creative tabs and panel (its red banner marks the "
             "search and inventory tabs). Brewing shows every potion in its own bottle.", "Creative tabs right?", sc,
             box=GUI_BOX, tag_b=C)
    for sc, nm, q in (("gui_furnace", "Furnace", "Lit, mid-smelt: its flame and arrow."),
                      ("gui_crafting", "Crafting table", "A diamond sword recipe on its cloth."),
                      ("gui_brewing", "Brewing stand", "Mid-brew. 1.7.10 has no fuel slot and sets the bottles 5 px "
                                                        "higher than the stand it was drawn for."),
                      ("gui_enchanting", "Enchanting table", "1.7.10 has one slot where 1.8+ has item + lapis: it lands "
                                                              "on the drawn table."),
                      ("gui_chest", "Chest", ""), ("gui_anvil", "Anvil", "")):
        pair("pk-" + sc[4:], nm, q, GUI_FLAWS.get(sc, PLAQUE), sc, box=GUI_BOX, tag_b=C)
    pair("pk-hud", "HUD and boss bar", "Survival HUD with the Ender Dragon's bar. 1.7.10 draws one bar for every "
         "boss from one 182x5 strip, so B uses Faithless's plain pink bar; its framed per-boss bars (dragon, wither) "
         "need a code hook (GuiIngame) to draw. The XP bar is Faithless's rune strip; its empty part is see-through, "
         "as Faithless draws it.",
         "Build the framed per-boss bars? Cause: 1.7.10 draws every boss bar from one plain strip, so picking a framed "
         "bar per boss needs a small qf-tweaks hook (GuiIngame).", "gui_hud", box="hud", tag_b=C)
    pair("pk-shelves", "Bookshelves: Soartex", "Soartex Forever's three shelves mixed at random (and its swamp, "
         "roofed forest, nether and savanna/mesa variants, by biome). Its model sinks the books into the frame; "
         "1.7.10 shelves are plain cubes, so the depth is only painted and in the normal map.",
         "Is Soartex Forever the Soartex you meant? Cause: the only Soartex in our reference folder is Soartex Forever "
         "R.1.6 (made for 1.21); the 1.7-era Soartex is a separate, CurseForge-only download we don't have.",
         "r11_shelves",
         cost_scene="r11_library")
    pair("pk-library", "Library wall", "", "", "r11_library")
    pair("pk-tnt", "TNT with enchanting-table lettering", "Faithless's TNT (the only block taken from it).", "Keep?",
         "r11_tnt")
    mob_q = ("Patrix's 3D shapes are OptiFine CEM models; 1.7.10 has none, so only the skins come, and only where "
             "they map onto the vanilla model. Kept (seen working in game): creeper, zombie, skeleton, wither "
             "skeleton, spider, cave spider, enderman, wolf, ocelot and cats, pig, snow golem, silverfish. "
             "Dropped (their layout is for the CEM shape, they render broken): chicken, cow, sheep, blaze, witch, "
             "zombie pigman, iron golem (still in these frames, 5 and 6: its face lands on the chest). Held back, "
             "unjudged: slime and magma cube (they vanish from the hall before the shot, in A too), ghast, squid, bat, "
             "wither (not in the hall). The new shapes themselves (horns, manes, thin skeleton bones) would need a "
             "Java renderer per mob.")
    smoke = ("Keep Conquest's black smoke? Cause: its particle sheet replaces vanilla's grey smoke specks with big "
             "black swirls, so every fire, torch and blaze smokes like this; we can keep its other particles and "
             "put vanilla smoke back.")
    mob_notes = {1: "Which mobs keep Patrix?", 4: smoke,
                 5: "The iron golem here is the Patrix skin we dropped: its CEM layout puts the face on the chest."}
    for i in range(1, 7):
        pair("pk-mob-%d" % i, "Mobs up close (%d of 6)" % i, mob_q if i == 1 else "",
             mob_notes.get(i, ""), "r11_mob_%d" % i, cost_scene="r11_mobs_b" if i == 1 else None)
    os.makedirs(OUT, exist_ok=True)
    doc = {"from": "texture agent #2 (r011 packs)", "round": "r011", "scenes": scenes,
           "notes": "A = round 10 (QF-v3c). B = the r007 packs copied in (QF-r011-packs.zip, + QF-r011-gui.zip for GUI "
                    "scenes), private pack only. Conquest's sky, fog colours and lightmaps are shader-side (note in "
                    "ops/checkpoints/r011-shader.md); its particles, rain, snow and ambient sounds are in B but do not "
                    "show in still frames."}
    p = os.path.join(OUT, "packs_scenes.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d scenes -> %s" % (len(scenes), p))


if __name__ == "__main__":
    main()
