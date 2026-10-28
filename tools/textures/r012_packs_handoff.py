#!/usr/bin/env python3
"""Write the r012 packs scenes for the Shader Lab (C:\\qfb\\shaderdev\\r012\\packs_scenes.json + crops), then PACKS-READY.

    py -3.10 -I tools/textures/r012_packs_handoff.py [--ready]

Reads the frames of render 1028-154329-textures-r012-packs (the re-render after review of 1028-150936) (spec tools/renderq/specs/textures-r012-packs.json) from
C:\\qfb\\shaderdev\\rounds\\screenshots. A = round 11 as published (frozen zips), B = r012 fixes, C (where rendered) =
the alternative. The frames show third-party pack art: internal Lab review only, never the public site.
Answers the owner's r011 notes (ops/checkpoints/r012-plan.md, "Packs"); settled picks are not asked again.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r011_packs_handoff import GUI_BOX, HUD_BOXES  # noqa: E402
import r011_packs_handoff as h11  # noqa: E402

OUT = r"C:\qfb\shaderdev\r012"
h11.CROPS = os.path.join(OUT, "packs")
A, B, C = "pk12a", "pk12b", "pk12c"
HUD = {"B": ("pk12h1", "Forged iron"), "C": ("pk12h2", "Arcane"), "D": ("pk12h3", "Banner")}
MOBS = ["chicken", "creeper", "zombie", "skeleton", "wither skeleton", "spider", "cave spider", "enderman",
        "zombie pigman", "witch", "blaze", "slime", "magma cube", "silverfish", "sheep", "cow", "pig", "ocelot",
        "wolf", "mooshroom", "horse", "villager", "squid", "bat (hanging)", "iron golem", "snow golem"]
# Pigman and blaze remaps dropped after 1028-150936 (patrix_remap.DROPPED); Conquest's witch is vanilla's, so C
# takes the Patrix-remapped witch too.
SOURCE = {"B": {"iron golem": "Patrix remapped", "witch": "Patrix remapped",
                "cow": "Patrix remapped", "sheep": "Patrix remapped", "chicken": "Patrix remapped"},
          "C": {"witch": "Patrix remapped"}}
PATRIX = {"creeper", "zombie", "skeleton", "wither skeleton", "spider", "cave spider", "enderman", "silverfish",
          "pig", "ocelot", "wolf", "snow golem"}


def src(opt, mob):
    if mob in PATRIX:
        return "Patrix"
    return SOURCE.get(opt, {}).get(mob, "Conquest")


def in_view(k):
    c = 225 + 43.75 * (k + 0.5) / 7
    return [m for i, m in enumerate(MOBS) if abs(225 + 1.75 * i - c) <= 3.6]


def main():
    scenes = []
    opt = h11.opt

    def scene(sid, name, question, prompt, sc, box, options):
        imgs = []
        for key, label, tag, desc in options:
            p = h11.crop(tag, sc, box, sid)
            if p is None:
                print("missing frame", tag, sc)
                return
            imgs.append(opt(key, label, p, desc))
        scenes.append({"id": sid, "name": name, "question": question, "notePrompt": prompt, "options": imgs})

    r11 = ("A", "Round 11 (as you saw it)", A, "")
    scene("pk-creative-combat", "Creative: combat tab",
          "Fixed. Cause of the broken look: Faithless draws its tabs 26 px wide on a 26 px grid (Minecraft 1.19.3+), "
          "1.7.10 cuts 28 px cells, so every tab was sliced across two of Faithless's. Rebuilt on 1.7.10's grid. "
          "B is Faithless's own look made whole (its wood-framed panel, item cells). C answers 'richer': the parchment "
          "page and red banner bookmarks of Faithless's recipe book, from the screenshots you sent in round 7.",
          "B or C?", "gui_creative_combat", GUI_BOX,
          [r11, ("B", "Faithless, fixed", B, "Grey tabs on the right grid, wood frame, item cells."),
           ("C", "Recipe-book style", C, "Parchment page, every tab a red banner.")])
    scene("pk-creative-brewing", "Creative: brewing tab", "Same fix and the same two styles.", "",
          "gui_creative_brewing", GUI_BOX,
          [r11, ("B", "Faithless, fixed", B, ""), ("C", "Recipe-book style", C, "")])
    text = ("Text: 1.7.10 writes every screen title in fixed dark grey with no shadow. Faithless's plaques were dark "
            "wood and sized for its own font, so titles sank in and ran off them. Each plaque is now widened to the "
            "title and painted the light honey wood of Faithless's newer screens.")
    for sc, nm, extra in (("gui_furnace", "Furnace", " The furnace's other 'not right' part was its plaques: the "
                           "slots, flame and arrow already sit where 1.7.10 draws them."),
                          ("gui_enchanting", "Enchanting table", " The option ribbons are parchment now (1.7.10's "
                           "spell text is a dark brown), with Faithless's red seal kept under the green level number, narrowed to the number so less spell text "
                           "runs onto the red (1.7.10 wraps that text at the ribbon's full width)."),
                          ("gui_crafting", "Crafting table", ""), ("gui_brewing", "Brewing stand", ""),
                          ("gui_anvil", "Anvil", " 1.7.10's anvil draws no 'Inventory' title, so its lower plaque stays "
                           "Faithless's dark wood rather than a blank light one.")):
        scene("pk-" + sc[4:], nm, text + extra, "Text readable now?", sc, GUI_BOX,
              [r11, ("B", "Plaques fixed", B, "")])
    hud = [("A", "Round 11", A, "Faithless's pink bar; its XP strip did not map (garbled).")] + [
        (k, "QF: " + n, t, "") for k, (t, n) in HUD.items()]
    scene("pk-hud", "HUD: three Quest Forge directions",
          "Our own art, Faithless's hearts and food kept. Iron: the main menu's forged plates, lavender rim, ember "
          "selection, molten XP. Arcane: indigo and gold, gem corners, emerald XP, runes in the boss channel. Banner: "
          "walnut and brass, red banner selection, gold XP, red ribbon boss bar. 1.7.10 draws every boss bar from "
          "one 182 x 5 strip; a taller framed bar (one per boss) needs a small qf-tweaks hook.",
          "Which direction? And build the framed boss bar hook?", "gui_hud", "hud", hud)
    scene("pk-tnt", "TNT: lettering on every block", "Fixed: Faithless letters one block in five; now all.", "",
          "r11_tnt", None, [r11, ("B", "All lettered", B, "")])
    for k in range(7):
        mobs = in_view(k)
        names = ", ".join("%s (B: %s%s)" % (m, src("B", m), "" if src("B", m) == src("C", m) else
                                           ", C: " + src("C", m)) for m in mobs)
        q = ("Listed right to left as they stand in the frame: " + names + ". ") if mobs else ""
        if k == 0:
            q = ("Every mob is non-vanilla now. Patrix where its skin fits 1.7.10's model; where Patrix drew for its "
                 "own 3D shapes, B remaps its skin face by face onto 1.7.10's boxes (its shapes cannot come: they "
                 "need a Java renderer per mob), C uses Conquest's 1.7-era mobs instead. Passive mobs added: "
                 "mooshroom, horse, villager, squid, bat. Remaps that landed wrong in the first render (pigman: no face; "
                 "blaze: see-through head) use Conquest. Still vanilla: the wither's shield shimmer and one horse "
                 "marking overlay (no source has them). ") + q
        scene("pk-mob-%d" % (k + 1), "Mobs (%d of 7)" % (k + 1), q, "Patrix remap (B) or Conquest (C), per mob?" if k == 0
              else "", "r12_mob_%d" % (k + 1), None,
              [("A", "Round 11", A, ""), ("B", "Patrix + remapped", B, ""), ("C", "Patrix + Conquest", C, "")])
    os.makedirs(OUT, exist_ok=True)
    doc = {"from": "texture agent (r012 packs)", "round": "r012", "scenes": scenes,
           "notes": "A = round 11 as published (QF-r011-*-final.zip). B/C = r012 (C:\\qfb\\textures\\r012\\). Private "
                    "pack art; Lab only. Soartex shelf as a Chisel variant: route in ops/checkpoints/r012-packs.md."}
    p = os.path.join(OUT, "packs_scenes.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d scenes -> %s" % (len(scenes), p))
    if "--ready" in sys.argv:
        open(os.path.join(OUT, "PACKS-READY"), "w").write("r012 packs: %d scenes\n" % len(scenes))


if __name__ == "__main__":
    main()
