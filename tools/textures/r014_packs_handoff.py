#!/usr/bin/env python3
"""Write the r014 packs scenes for the Shader Lab (C:\\qfb\\shaderdev\\r014\\packs_scenes.json + crops), then PACKS-READY.

    py -3.10 -I tools/textures/r014_packs_handoff.py [--ready]

Reads the frames of render 1031-194643-textures-r014-packs (spec tools/renderq/specs/textures-r014-packs.json) from
C:\\qfb\\shaderdev\\rounds\\screenshots. HUD: one HUD (qf_hud_r014.py) with XP options A-C. Mobs: round 12's set (A)
is the default everywhere; view 6 also shows three non-default snow golems. The frames show third-party pack art:
internal Lab review only, never the public site. Answers the owner's r013 notes (ops/checkpoints/r014-plan.md, "Packs").
"""
import json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r011_packs_handoff as h11  # noqa: E402

OUT = r"C:\qfb\shaderdev\r014"
h11.CROPS = os.path.join(OUT, "packs")
XP = [("A", "pk14h1", "Thread", "A gold hairline bar whose fill brightens toward its leading edge; the level number in "
                               "pale gold with a dark brown outline."),
      ("B", "pk14h2", "Notched", "A slightly taller ember bar cut into tenths by ink notches with gold studs; the number "
                                "in bone white."),
      ("C", "pk14h3", "Medallion", "The thread bar with the number set on a small dark medallion (gold hairline, "
                                  "pointed ends) at the bar's centre.")]
XP_BOX = (1000, 1170, 1560, 1290)     # the level number and the middle of the XP bar, GUI scale 6 on 2560 x 1440
ICON_BOX = (700, 1120, 1860, 1260)    # armour, hearts, food rows
MOB_BOX = (700, 400, 1480, 1020)      # hall view 6: snow golem and iron golem (left two thirds; the critic: view 5 mobs half cut at the right)
GOLEMS = [("A", "pk14a", "Round 12 set (your pick): Patrix", "Patrix's snow golem: near-vanilla white snow with "
                                                              "coal buttons, which is why it read as default."),
          ("B", "pk14g1", "Faithless", "Red scarf and hat band (round 13's B; it faces "
                                                "sideways in this shot)."),
          ("C", "pk14g2", "Soartex Forever", "Soft, warm shaded snow with buttons down the front "
                                                       "(it faces sideways in this shot)."),
          ("D", "pk14g3", "Conquest", "Rough packed snow. Its pack also replaces the pumpkin head, but that needs "
                                      "MCPatcher random mobs, which is off in this pack, so the head is the block's.")]


def zoom_crop(tag, scene, box, name, k=2):
    p = h11.crop(tag, scene, box, name)
    if p:
        im = Image.open(p)
        im.resize((im.width * k, im.height * k), Image.NEAREST).save(p, quality=92)
    return p


def main():
    scenes = []
    opt = h11.opt

    def scene(sid, name, question, prompt, options):
        if any(o is None for o in options):
            print("missing frame(s) for", sid)
            return
        scenes.append({"id": sid, "name": name, "question": question, "notePrompt": prompt, "options": options})

    hud = [opt(k, n, h11.crop(t, "gui_hud", "hud", "pk-hud") or None, d) if h11.frame(t, "gui_hud") else None
           for k, t, n, d in XP]
    scene("pk-hud", "HUD: one HUD from your picks, three XP bars",
          "Our own art. Grace's hotbar and Tarnished's boss bar, as you picked. Hearts, food, armour and air are "
          "individual icons again, drawn in the same style: an ink outline, a fine gold rim (dull bronze when empty) "
          "and a shaded body; red hearts, roast shanks with a bone, steel chestplates, glass bubbles under water. "
          "The food row is full this time (the test had been lowering it). Air bubbles only show under water, so they "
          "are in the mock (M) but not in these shots. The three options differ only in the XP bar and its level "
          "number. Vanilla draws that number lime and no texture can change it, so the coloured number in these shots "
          "comes from a small client-only hook in qf-content (XpBarStyle.java) that redraws it in the pack's colour. "
          "That hook is code, so it needs your yes to ship; without it the number stays lime whichever bar you pick. "
          "M: the offline mock, normal and just hit.",
          "Which XP bar? Ship the XP number hook (yes/no)? Anything off in the icons?", hud)
    if scenes and scenes[-1]["id"] == "pk-hud":
        mock = os.path.join(h11.CROPS, "pk-hud-mock.png")
        if os.path.exists(mock):
            scenes[-1]["options"].append(opt("M", "Mock: thread, notched, medallion (left normal, right just hit)",
                                             mock, "Top to bottom; 1.7.10's layout drawn offline from the same sheets."))
    xp = [opt(k, n, zoom_crop(t, "gui_hud", XP_BOX, "pk-hud-xp"), d) if h11.frame(t, "gui_hud") else None
          for k, t, n, d in XP]
    scene("pk-hud-xp", "HUD: the XP bars up close", "The same three shots, cropped to the level number and the "
          "middle of the bar (2x).", "", xp)
    icons = [opt("A", "Hearts, food, armour", zoom_crop("pk14h1", "gui_hud", ICON_BOX, "pk-hud-icons"),
                 "Seven and a half hearts, a full food row, armour 13 of 20.")] if h11.frame("pk14h1", "gui_hud") \
        else [None]
    scene("pk-hud-icons", "HUD: the icons up close", "Crop of option A at 2x (the icons are the same in all three).",
          "", icons)
    golems = [opt(k, n, h11.crop(t, "r13_mob_6", MOB_BOX, "pk-mob-6"), d) if h11.frame(t, "r13_mob_6") else None
              for k, t, n, d in GOLEMS]
    scene("pk-mob-6", "Mobs, view 6: snow golem options",
          "Round 12's set stays the default for every mob. Snow golem, iron golem, bat (hanging), left to right; only "
          "the snow golem changes: B-D are copied from the reference packs named. The pumpkin head is the block's "
          "own texture in 1.7.10.", "Which snow golem?", golems)
    os.makedirs(OUT, exist_ok=True)
    doc = {"from": "texture agent (r014 packs)", "round": "r014", "scenes": scenes,
           "notes": "Base everywhere: round 12's set A (QF-r012-packs-final + QF-r012-gui-final). HUD zips and golem "
                    "zips in C:\\qfb\\textures\\r014\\ (rps_top). Private pack art; Lab only."}
    p = os.path.join(OUT, "packs_scenes.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d scenes -> %s" % (len(scenes), p))
    if "--ready" in sys.argv:
        open(os.path.join(OUT, "PACKS-READY"), "w").write("r014 packs: %d scenes\n" % len(scenes))


if __name__ == "__main__":
    main()
