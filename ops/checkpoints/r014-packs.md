# r014: packs from the owner's r013 notes (texture-dev, 2026-10-31)

Work order: ops/checkpoints/r014-plan.md "Packs". Builders/world/views/traps: r013-packs.md, r012-packs.md.
Settled: round 12's mob set (r013 A = QF-r012-packs-final.zip + QF-r012-gui-final.zip) is the default everywhere.

## Progress log
### 2026-10-31 step 1: bench jar (food full, XP number hook)
- XP number: MCPatcher text.xpbar cannot reach it here (Angelica applies text colours only in its extended-HD font
  mixin, skipped when CoFHCore loads). New client hook mods/qf-content/.../client/XpBarStyle.java (Post EXPERIENCE,
  redraws the number over the lime one): reads mcpatcher/color.properties text.xpbar, qf.xpbar.outline,
  qf.xpbar.plate=u,v,w,h (sprite in gui/icons.png). No key = vanilla. Registered in ClientProxy.
- GuiShots: food set to 20 (idempotent) + gamerule naturalRegeneration false (else full food heals the hearts).
- Built in worktree C:\qfb\wt-r011-fb (-PqfDebugTools=true; qf-content there = HEAD + debug files + my 3 files)
  -> C:\qfb\renderq\jars-r014\QuestForgeContent-1.0.0.jar.
- Snow golem options (view 6 only): Faithless (red scarf, r013 B), Soartex Forever (buttons, soft shading), Conquest
  (packed snow). Patrix's reads as default (r013), so not offered. Conquest's pumpkin overlay needs random_mobs (off).
- Next: qf_hud_er.py style "r014" (grace hotbar + tarnished boss bar + individual icons, XP options x1-x3);
  golem zips; spec tools/renderq/specs/textures-r014-packs.json; submit.
### 2026-10-31 step 2: HUD + golems built, render SUBMITTED
- tools/textures/qf_hud_r014.py (own art): grace hotbar/selection + tarnished boss strip (from qf_hud_er.py) + hand-
  placed 18x18 icons (heart, roast shank with bone, chestplate, bubble): ink outline, bevelled gold hairline (dull
  when empty), shaded body. XP options thread / notched / plate (plate sprite at icons.png 0,100 22x10), each zip
  with mcpatcher/color.properties (text.xpbar, qf.xpbar.outline, qf.xpbar.plate). Mock: scratch pk14/prev.png.
- tools/textures/r014_golems.py -> C:\qfb\textures\r014\QF-r014-golem-{faithless,soartex,conquest}.zip (rps_top).
- Spec tools/renderq/specs/textures-r014-packs.json: pk14h1-3 (HUD x thread/notched/plate, measure 220), pk14a (set
  A, view 6), pk14g1-3 (golems, view 6). Base stack = set A; jars-r014.
- SUBMITTED 1031-194643-textures-r014-packs (queue was idle at 19:46).
- Next: `renderq.py wait 1031-194643-textures-r014-packs`; review HUD crops (number recoloured? plate? food full
  10 shanks, hearts 7.5, no screen, clear of chat, hotbar ours) and view-6 golem crops; hand-off script
  tools/textures/r014_packs_handoff.py -> C:\qfb\shaderdev\r014\ (packs_scenes.json, packs\ crops, PACKS-READY).
