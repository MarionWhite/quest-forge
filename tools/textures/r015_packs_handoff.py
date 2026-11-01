#!/usr/bin/env python3
"""Write the r015 packs scenes for the Shader Lab (C:\\qfb\\shaderdev\\r015\\packs_scenes.json + crops), then PACKS-READY.

    py -3.10 -I tools/textures/r015_packs_handoff.py [--ready]

Reads the frames of render 1101-101607-textures-r015-packs (spec tools/renderq/specs/textures-r015-packs.json) from
C:\\qfb\\shaderdev\\rounds\\screenshots, and makes the offline mock and icon sheets with qf_hud_r015.py. Five complete
HUD designs, our own art, answering the owner's r014 note (ops/checkpoints/r015-plan.md, "Packs"). The frames also
show the round 12 pack set (third-party art): internal Lab review only.
"""
import json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r011_packs_handoff as h11  # noqa: E402
import qf_hud_r015 as hud  # noqa: E402

OUT = r"C:\qfb\shaderdev\r015"
h11.CROPS = os.path.join(OUT, "packs")
# GUI scale 6 on 2560 x 1440 (GUI 426 x 240, centre x 1278)
ICON_BOX = (712, 1130, 1844, 1300)     # armour row, hearts, the whole medallion, food
XP_BOX = (1110, 1200, 1450, 1314)      # the medallion, the number and the middle of the XP bar
BOSS_BOX = (600, 0, 1960, 146)         # boss name, bar and frame
HOTBAR_BOX = (712, 1290, 1844, 1440)

D = [("A", "pk15a", "gilded", "Gilded",
      "Smoky glass in bevelled gold: a gold-railed ribbon behind the hearts and food, gold studs on the seams; a gold "
      "coin medallion with clasps that grip the XP bar; Grace's hotbar grown up (gold pillars with diamonds, "
      "diamond end finials, a thicker gold selection); Tarnished's crimson boss bar with gold blades at both ends."),
     ("B", "pk15b", "cloisonne", "Cloisonne",
      "Lapis enamel cells in gold wire: every heart, shank and chestplate sits in its own cell; enamel-red hearts; "
      "octagonal slots with turquoise jewels between them; a lapis medallion in a double gold ring; a turquoise XP "
      "bar marked in tenths; a boss bar in gold-wired segments with jewelled lozenge caps."),
     ("C", "pk15c", "ironbound", "Ironbound",
      "Blackened, riveted iron plate: rubies cut with facets and set in steel; sunken slots; an ember-hot selection; "
      "molten XP that runs from dark red to white-hot; a hex-nut medallion with an ember-lined recess; iron clamp "
      "plates with spikes on the boss bar."),
     ("D", "pk15d", "moonsilver", "Moonsilver",
      "Silver filigree on midnight blue: an arcade, each heart under its own silver arch; gothic arched slots with "
      "finials; a moonlit medallion with stars on the bar; a moonlight XP bar; crescent moons at both ends of the "
      "boss bar."),
     ("E", "pk15e", "obsidian", "Obsidian",
      "Black volcanic glass with an amethyst glow: crystal hearts cut with facets, angled seams, slanted slots with "
      "cut corners, a rune-stone medallion, a violet XP bar, glowing thorns at both ends of the boss bar.")]

HOOK = ("Needs your yes: four parts of every design are drawn by a small client-only hook in qf-content "
        "(XpBarStyle.java), not by the texture pack: the medallion, the boss bar's frame, the dark outline round the "
        "boss name and the XP number's colour. It is code, so it ships only with your yes. Without it the number is "
        "plain lime, with no medallion behind it, no boss frame, and a plain white boss name; the rest of each design "
        "(bands, icons, hotbar, XP and boss bars) is texture and stays.")


def zoom_crop(tag, scene, box, name, k=2):
    p = h11.crop(tag, scene, box, name)
    if p:
        im = Image.open(p)
        im.resize((im.width * k, im.height * k), Image.NEAREST).save(p, quality=92)
    return p


def main():
    os.makedirs(h11.CROPS, exist_ok=True)
    mock = os.path.join(h11.CROPS, "pk-hud-mock.png")
    icons = os.path.join(h11.CROPS, "pk-hud-icon-cells.png")
    hud.mock_sheet(mock, icons)
    scenes = []
    opt = h11.opt

    def scene(sid, name, question, prompt, options):
        if any(o is None for o in options):
            print("missing frame(s) for", sid)
            return
        scenes.append({"id": sid, "name": name, "question": question, "notePrompt": prompt, "options": options})

    have = {t: h11.frame(t, "gui_hud") for _, t, _, _, _ in D}
    full = [opt(k, n, h11.crop(t, "gui_hud", "hud", "pk-hud") or None, d) if have[t] else None
            for k, t, _, n, d in D]
    if all(full):
        full.append(opt("M", "Offline mock: all five side by side", mock,
                        "Each design at GUI scale 4 (left: normal; right: just hit, under water, slot 5, level 104) and "
                        "at GUI scale 1 (what a scale-1 screen really samples, shown 4x)."))
    scene("pk-hud", "HUD: five designs",
          "Five complete HUDs, our own art, each in one material: hotbar, selection, hearts, food, armour, an XP bar "
          "with a medallion, and the boss bar. Less minimalist than round 14: every row now sits on a framed band, "
          "the medallion sits in the gap between the heart and food rows (clear of both), and the boss bar gets a frame with end pieces. Grace's hotbar, Tarnished's "
          "boss bar and the medallion were the starting point (A is closest to them). The boss name has a dark outline "
          "in all five, so it reads over a bright sky. " + HOOK,
          "Which design (or which parts of which)? Ship the XpBarStyle hook (yes/no)?", full)
    icons_o = [opt(k, n, zoom_crop(t, "gui_hud", ICON_BOX, "pk-hud-icons"), "Seven and a half hearts, full food, "
                   "armour 13 of 20, the medallion between the rows.") if have[t] else None for k, t, _, n, _ in D]
    if all(icons_o):
        icons_o.append(opt("M", "Offline: every icon state", icons, "Heart row empty, blinking, full, half, lost (just "
                           "hit), absorption; armour empty, half, full; food empty, full, half; an air bubble; the "
                           "medallion. 6x."))
    scene("pk-hud-icons", "HUD: icons up close", "The armour, heart and food rows of each design at 2x.", "", icons_o)
    xp = [opt(k, n, zoom_crop(t, "gui_hud", XP_BOX, "pk-hud-xp"), "") if have[t] else None for k, t, _, n, _ in D]
    scene("pk-hud-xp", "HUD: the XP medallions up close", "The level number on each medallion and the middle of the XP "
          "bar, 2x. The number's colour is the hook's (lime without it). Levels of 100 "
          "and up run onto the rim but stay readable (offline mock, right column).", "", xp)
    boss = [opt(k, n, h11.crop(t, "gui_hud", BOSS_BOX, "pk-hud-boss"), "") if have[t] else None
            for k, t, _, n, _ in D]
    scene("pk-hud-boss", "HUD: boss bars and the outlined name", "The boss name now has a dark outline in every "
          "design (the critic found it unreadable over white cloud in rounds 13 and 14), and each bar has its own end "
          "pieces.", "", boss)
    doc = {"from": "texture agent (r015 packs)", "round": "r015", "scenes": scenes,
           "notes": "Base everywhere: round 12's set A (QF-r012-packs-final + QF-r012-gui-final). HUD zips in "
                    "C:\\qfb\\textures\\r015\\ (rps_top), built by tools/textures/qf_hud_r015.py. Bench qf-content "
                    "jar C:\\qfb\\renderq\\jars-r015 (XpBarStyle with the boss keys; GuiShots food full). " + HOOK}
    p = os.path.join(OUT, "packs_scenes.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d scenes -> %s" % (len(scenes), p))
    if "--ready" in sys.argv:
        open(os.path.join(OUT, "PACKS-READY"), "w").write("r015 packs: %d scenes\n" % len(scenes))


if __name__ == "__main__":
    main()
