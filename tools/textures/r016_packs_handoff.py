#!/usr/bin/env python3
"""Write the r016 packs scenes for the Shader Lab (C:\\qfb\\shaderdev\\r016\\packs_scenes.json + crops), then PACKS-READY.

    py -3.10 -I tools/textures/r016_packs_handoff.py [--ready]

Reads the frames of render 1101-155720-textures-r016-packs (spec tools/renderq/specs/textures-r016-packs.json) from
C:\\qfb\\shaderdev\\rounds\\screenshots: day pk16a-d, night pk16an-dn. Makes the offline mock, icon and boss sheets
with qf_hud_r016.py. Four minimal HUDs and four Infernum-studied boss bars, our own art, answering the owner's r015
notes (ops/checkpoints/r016-plan.md, "HUD"). The frames also show the round 12 pack set (third-party art): internal
Lab review only.
"""
import json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r011_packs_handoff as h11  # noqa: E402
import qf_hud_r016 as hud  # noqa: E402

OUT = r"C:\qfb\shaderdev\r016"
h11.CROPS = os.path.join(OUT, "packs")
h11.HUD_BOXES = [(0, 0, 2560, 280), (640, 1100, 1920, 1440)]   # the r016 bars run to GUI row 42 (252 px)
# GUI scale 6 on 2560 x 1440 (GUI 426 x 240, centre x 1280)
ICON_BOX = (712, 1130, 1844, 1300)     # armour row, hearts, the medallion, food
XP_BOX = (1110, 1200, 1450, 1314)      # the medallion, the number and the middle of the XP bar
BOSS_BOX = (540, 0, 2020, 270)         # name, bar, medallion, percent (widest bar 236 GUI px = 1416 px)
HOTBAR_BOX = (712, 1290, 1844, 1440)

D = [("A", "pk16a", "refined", "Refined",
      "Round 14 grown up, with its Elden Ring parts gone: the same individual icons, now glossy (one light, a domed "
      "body, one specular) in crisp ink keylines; a slim smoked hotbar with soft rounded ends and faint dividers; a "
      "warm white-gold selection with a soft glow; a gold glass XP thread; a gold-rimmed capsule medallion."),
     ("B", "pk16b", "glass", "Glass",
      "Frosted glass: every slot its own rounded glass tile; candy-gloss icons with tinted keylines (no black), a "
      "white rim light and a bright highlight; a white selection ring; a mint capsule XP bar; a frosted pill "
      "medallion with a white number."),
     ("C", "pk16c", "gunmetal", "Gunmetal",
      "Machined steel: a bevelled gunmetal strip with recessed wells; icons cut in flat facets inside a chrome rim; "
      "a steel selection with a crimson inner line; an amber XP bar in a steel track; a chamfered steel tag."),
     ("D", "pk16d", "wine", "Wine & gold",
      "Dark wine glass between two bevelled gold rails; a chamfered gold selection; gold-rimmed icons; a gold XP bar "
      "on wine; a gold-edged wine medallion. The same family as the gilded boss bar.")]

BOSS = [("A", "pk16a", "ember", "Ember",
         "Blackened bronze rails, a molten fill (white-yellow core to deep red) with slanted heat streaks, a glowing "
         "white cap riding the fill's edge, a bronze medallion with a flame, a pointed end, the percent after it."),
        ("B", "pk16b", "obsidian", "Obsidian",
         "Round 15's obsidian (your 'kinda close') grown into a thick bar: black glass rails with a violet edge light, "
         "a magenta fill with a slanted sheen, a crystal shard riding its edge, an octagonal amethyst socket with a "
         "slit eye, three crystal spikes at the end, the percent inside the bar."),
        ("C", "pk16c", "ironclad", "Ironclad",
         "Riveted gunmetal rails, a blood-red fill cut into tenths, a steel collar riding its edge, a steel heater "
         "shield with a chevron, a square end clamp holding the percent."),
        ("D", "pk16d", "gilded", "Gilded",
         "Closest to what makes Infernum's bar work: bevelled gold rails, a crimson fill with a slanted stepped sheen "
         "over a dark wine channel, a gold cap riding its edge, a round gold-ringed medallion with a horned skull "
         "that the fill drains toward, a pointed end, the percent in a gold-rimmed tab under the end.")]

INFERNUM = ("Studied from Infernum Mode's own source and sprites (github.com/InfernumTeam/InfernumMode, Content/"
            "BossBars; study only, nothing copied): what makes its bar work is one THICK bar (not a line), heavy "
            "bevelled rails, a dark but coloured empty channel so the bar reads whole at any health, a slanted "
            "stepped sheen on the fill, a bright cap riding the fill's edge, a medallion the fill drains toward, and "
            "the health in percent instead of a number. It shows no name; ours keep the name, outlined. Infernum's "
            "per-boss head icon, phase pips and enrage fire need data 1.7.10 does not have (it knows only a name and "
            "a health fraction), so every boss shows the design's emblem and the rails carry quarter ticks. The bar "
            "fades in over a second when a boss appears (not visible in a still).")

HOOK = ("Needs your yes: the XP number's colour, the XP medallion and the whole boss bar (frame, medallion, percent, "
        "outlined name) are drawn by a small client-only hook in qf-content (XpBarStyle.java), not by the texture "
        "pack. It is code, so it ships only with your yes. Without it the number is plain lime with no medallion, "
        "and the boss bar falls back to vanilla's thin 182 x 5 strip (in each design's colours) with a plain white "
        "name; the rest of each HUD (icons, hotbar, XP bar) is texture and stays.")


def zoom_crop(tag, scene, box, name, k=2):
    p = h11.crop(tag, scene, box, name)
    if p:
        im = Image.open(p)
        im.resize((im.width * k, im.height * k), Image.NEAREST).save(p, quality=92)
    return p


def day_night(tag, box, name):
    a = h11.crop(tag, "gui_hud", box, name + "-day")
    c = h11.crop(tag + "n", "gui_hud", box, name + "-night")
    if not a or not c:
        return None
    ia, ic = Image.open(a), Image.open(c)
    out = Image.new("RGB", (ia.width, ia.height + ic.height + 8), (12, 12, 12))
    out.paste(ia, (0, 0))
    out.paste(ic, (0, ia.height + 8))
    dst = os.path.join(h11.CROPS, "%s-%s.jpg" % (name, tag))
    out.save(dst, quality=92)
    for p in (a, c):
        os.remove(p)
    return dst


def main():
    os.makedirs(h11.CROPS, exist_ok=True)
    mock = os.path.join(h11.CROPS, "pk-hud-mock.png")
    icons = os.path.join(h11.CROPS, "pk-hud-icon-cells.png")
    bosses = os.path.join(h11.CROPS, "pk-hud-boss-mock.png")
    hud.mock_sheet(mock, icons, bosses)
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
        full.append(opt("M", "Offline mock: all four side by side", mock,
                        "Each design at GUI scale 4 (left: day; right: night, just hit, under water, slot 5, level "
                        "104) and at GUI scale 1 (what a scale-1 screen really samples, shown 4x)."))
    scene("pk-hud", "HUD: four minimal designs",
          "Back to minimal, as you asked, but finished: no bands, cells or ornaments behind the rows (round 15's "
          "mistake) and no Elden Ring parts (round 14's grace strip and diamond finials are gone). The polish goes "
          "into the icons themselves (one light, glossy or cut shading, a clean keyline) and into one quiet hotbar "
          "per design. A starts from round 14. The medallion you liked stays, smaller and cleaner. Each frame also "
          "shows one of the four new boss bars (rated separately below). " + HOOK,
          "Which HUD (or which parts of which)? Ship the XpBarStyle hook (yes/no)?", full)
    icons_o = [opt(k, n, zoom_crop(t, "gui_hud", ICON_BOX, "pk-hud-icons"), "Seven and a half hearts, full food, "
                   "armour 13 of 20, the medallion between the rows.") if have[t] else None for k, t, _, n, _ in D]
    if all(icons_o):
        icons_o.append(opt("M", "Offline: every icon state", icons, "Heart row empty, blinking, full, half, lost (just "
                           "hit), absorption; armour empty, half, full; food empty, full, half; an air bubble; the "
                           "medallion. 6x."))
    scene("pk-hud-icons", "HUD: icons up close", "The armour, heart and food rows of each design at 2x.", "", icons_o)
    xp = [opt(k, n, zoom_crop(t, "gui_hud", XP_BOX, "pk-hud-xp"), "") if have[t] else None for k, t, _, n, _ in D]
    scene("pk-hud-xp", "HUD: XP bar and medallion up close", "The level number on each medallion and the middle of "
          "the XP bar, 2x. The number's colour and the medallion are the hook's (lime, no medallion without it).",
          "", xp)
    boss = [opt(k, n, day_night(t, BOSS_BOX, "pk-hud-boss"), d) for k, t, _, n, d in BOSS]
    if all(boss):
        boss.append(opt("M", "Offline: every bar at 62 %, 8 % and 100 %", bosses,
                        "Each bar over a bright cloud and a night sky, at GUI scale 4 and at GUI scale 1 (shown 4x)."))
    scene("pk-hud-boss", "Boss bars after Infernum: bright sky (top) and night (bottom)",
          "Four thick boss bars, our own art, each shown over a bright cloud and over a night sky, the name outlined "
          "in all four. " + INFERNUM + " " + HOOK,
          "Which boss bar (or which parts of which)?", boss)
    doc = {"from": "texture agent (r016 packs)", "round": "r016", "scenes": scenes,
           "notes": "Base everywhere: round 12's set A (QF-r012-packs-final + QF-r012-gui-final). HUD zips in "
                    "C:\\qfb\\textures\\r016\\ (rps_top), built by tools/textures/qf_hud_r016.py; each carries one "
                    "boss bar (A ember, B obsidian, C ironclad, D gilded). Bench qf-content jar "
                    "C:\\qfb\\renderq\\jars-r016 (XpBarStyle bar mode). " + HOOK}
    p = os.path.join(OUT, "packs_scenes.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d scenes -> %s" % (len(scenes), p))
    if "--ready" in sys.argv:
        open(os.path.join(OUT, "PACKS-READY"), "w").write("r016 packs: %d scenes\n" % len(scenes))


if __name__ == "__main__":
    main()
