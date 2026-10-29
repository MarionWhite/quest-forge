#!/usr/bin/env python3
"""Write the r013 packs scenes for the Shader Lab (C:\\qfb\\shaderdev\\r013\\packs_scenes.json + crops), then PACKS-READY.

    py -3.10 -I tools/textures/r013_packs_handoff.py [--ready]

Reads the frames of render 1029-122545-textures-r013-packs (spec tools/renderq/specs/textures-r013-packs.json) from
C:\\qfb\\shaderdev\\rounds\\screenshots. Mobs: A = round 12's picked B as it was, B = round 13, both in the new views.
HUD: B-D = the three Elden-Ring-inspired directions in game, M = the offline mock (`qf_hud_er.py --preview`).
The frames show third-party pack art: internal Lab review only, never the public site.
Answers the owner's r012 notes (ops/checkpoints/r013-plan.md, "Packs"); settled picks are not asked again.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r011_packs_handoff as h11  # noqa: E402

OUT = r"C:\qfb\shaderdev\r013"
h11.CROPS = os.path.join(OUT, "packs")
A, B = "pk13a", "pk13b"
HUD = {"B": ("pk13h1", "Tarnished"), "C": ("pk13h2", "Grace"), "D": ("pk13h3", "Ashen")}
# FrameBench's FOV is very wide (a 4-mob group 4.5 blocks off spans ~550 of 2560 px), so the owner gets the group
# cropped from the full-resolution frame, not the frame (r012: "I can't see the wither skeleton").
MOB_BOX = (700, 400, 1860, 1020)      # hall views: the group, centred
TANK_BOX = (560, 420, 1900, 960)      # view 7: magma cube, slime, squid tank (checked on 1029-122545)
# per view, left to right as they stand in the frame (build_r011_world.GROUPS_R013; view 7 = the glass tanks)
VIEWS = [
    ["creeper", "skeleton", "wither skeleton", "zombie"],
    ["silverfish", "enderman", "cave spider", "spider"],
    ["chicken", "blaze", "witch", "zombie pigman"],
    ["mooshroom", "pig", "cow", "sheep"],
    ["villager", "horse", "wolf", "ocelot"],
    ["snow golem", "iron golem", "bat (hanging)"],
    ["squid (in water)", "slime", "magma cube"],
]
SRC = {"creeper": "Patrix", "skeleton": "Patrix", "wither skeleton": "Patrix", "zombie": "Patrix",
       "silverfish": "Patrix", "enderman": "Patrix", "cave spider": "Patrix", "spider": "Patrix",
       "chicken": "Patrix remapped", "blaze": "Conquest", "witch": "Patrix remapped", "zombie pigman": "Conquest",
       "mooshroom": "Conquest", "pig": "Patrix", "cow": "Patrix remapped", "sheep": "Patrix remapped",
       "villager": "Conquest", "horse": "Conquest", "wolf": "Patrix", "ocelot": "Patrix",
       "snow golem": "Faithless (was Patrix, near-vanilla)", "iron golem": "Patrix remapped", "bat (hanging)": "Conquest",
       "squid (in water)": "Faithless (was Conquest)", "slime": "Faithless (was Conquest)",
       "magma cube": "Faithless (was Conquest)"}
BOSS_HOOK = ("A framed boss bar is client-only and needs no server change and no transformer: Forge's GuiIngameForge "
             "fires RenderGameOverlayEvent.Pre(BOSSHEALTH) before it draws the strip, so a qf-tweaks client handler can "
             "cancel it and draw our own frame (a 256 x 16 sheet, name left-aligned above the bar, at the bottom centre "
             "like the reference) from BossStatus.bossName / healthScale / statusBarTime, with a per-boss frame looked "
             "up from the nearest IBossDisplayData entity's class (the name string is localised, so not a key). The same "
             "event (HEALTH, FOOD, ARMOR, AIR) could later move the bars to the top left with real end caps.")


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

    hud = [(k, n, t, "") for k, (t, n) in HUD.items()]
    scene("pk-hud", "HUD: three directions inspired by Elden Ring",
          "Our own art (nothing taken from the game). Hearts, food, armour and air are drawn as long thin bars: "
          "1.7.10 draws ten icons 8 px apart, so each icon is now one segment of a continuous bar (red health, green "
          "stamina = food, steel armour, blue air under water; lost health flashes pale gold when you are hit). Quiet "
          "hotbar, thin boss bar under the name with end caps. In game this time: these sit above QuestForge.zip, so "
          "the hotbar is ours, and the shot waits for the chat to fade off the hearts. Tarnished: charcoal and old gold, "
          "framed cells. Grace: warmer, one long strip, a glowing selection with a small diamond. Ashen: the quietest, "
          "bone hairlines, the hotbar only as corner brackets. The green stamina bar is longer or shorter from shot to shot only because the test set the food level more than once (a test bug, fixed); the art is the same. M: all three as a mock, normal and just hit. " + BOSS_HOOK,
          "Which direction? Build the framed boss bar (client only)?", "gui_hud", "hud", hud)
    if scenes and scenes[-1]["id"] == "pk-hud":
        mock = os.path.join(h11.CROPS, "pk-hud-mock.png")
        if os.path.exists(mock):
            scenes[-1]["options"].append(opt("M", "Mock: tarnished, grace, ashen (left normal, right just hit)", mock,
                                             "Top to bottom; 1.7.10's layout drawn offline from the same sheets."))
    for k, mobs in enumerate(VIEWS):
        names = ", ".join("%s (%s)" % (m, SRC[m]) for m in mobs)
        q = "Left to right: " + names + ". "
        if k == 0:
            q = ("Closer views, 3-4 mobs each. The wither skeleton (Patrix, your pick) is centred here, the dark one "
                 "next to the plain skeleton. ") + q
        if k == 5:
            q += ("Snow golem: Patrix's is near-vanilla white snow (why it read as default), so it is Faithless's, with "
                  "its red scarf; the pumpkin head is the block's own texture. The bat hangs from a beam at eye level. ")
        if k == 6:
            q += ("New: glass tanks, because a squid out of water dies and slimes hop off (they were missing in round "
                  "12); the streaks are our glass texture. Patrix draws all three for its own 3D models, so they are "
                  "Faithless's, which keep 1.7.10's. ")
        if k == 0:
            q += ("No mob texture is vanilla now: the wither's shield shimmer is Patrix's, and the black-dots horse "
                  "marking is Conquest's white dots darkened (Conquest shipped that one unchanged). The wither's body "
                  "stays Conquest's (Patrix's needs a remap; a live wither cannot be put in the hall to check it).")
        scene("pk-mob-%d" % (k + 1), "Mobs (%d of 7)" % (k + 1), q, "Right?" if k in (0, 5, 6) else "",
              "r13_mob_%d" % (k + 1), TANK_BOX if k == 6 else MOB_BOX,
              [("A", "Round 12, your pick", A, ""), ("B", "Round 13", B, "")])
    os.makedirs(OUT, exist_ok=True)
    doc = {"from": "texture agent (r013 packs)", "round": "r013", "scenes": scenes,
           "notes": "A = round 12's B packs (frozen zips) in the new views; B = r013 (C:\\qfb\\textures\\r013\\). "
                    "Private pack art; Lab only. B's creative screen does not share the book page's short-page bug."}
    p = os.path.join(OUT, "packs_scenes.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d scenes -> %s" % (len(scenes), p))
    if "--ready" in sys.argv:
        open(os.path.join(OUT, "PACKS-READY"), "w").write("r013 packs: %d scenes\n" % len(scenes))


if __name__ == "__main__":
    main()
