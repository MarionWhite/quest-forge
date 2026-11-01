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
- Committed bc0c907 (my files only). Hand-off script written (not yet run); mock already at
  C:\qfb\shaderdev\r014\packs\pk-hud-mock.png. Queue at 19:50: 2 shader-r014 submissions ahead, ETA ~20:10.

### 2026-10-31 step 3: render 1031-194643 reviewed, one fix, RE-RENDER SUBMITTED
- Reviewed as sheets/crops (scratch rv/). All good: HUD ours (grace hotbar, tarnished boss bar), no screen open, no
  chat, 7.5 hearts, armour 13, FULL food (10 shanks), XP number recoloured in all three (h1 pale gold, h2 bone white,
  h3 gold on the medallion), XP options clearly different. Air not in shot (not under water; the mock has it).
  Golems: A Patrix (white + coal buttons), g1 red scarf, g2 Soartex warm soft shading + buttons (faces sideways),
  g3 Conquest packed snow; iron golem/villager/horse unchanged.
- Broken: h3's medallion (22 GUI px) touched the first shank (hearts end at w/2-10, food starts at w/2+10). Fixed in
  qf_hud_r014.py: PLATE 18x10, blunter points (slope 0.55). Mock regenerated (C:\qfb\shaderdev\r014\packs\pk-hud-mock.png).
- h2's number sits on the notched bar's top rim, as vanilla's does; left as is (moving it needs the Java hook).
- Handoff text updated: hook needs the owner's yes; air only in mock; golem descriptions.
- SUBMITTED 1031-201118-textures-r014-packs-b (spec tools/renderq/specs/textures-r014-packs-b.json, pk14h3 only,
  overwrites bench-pk14h3-gui_hud.png). ETA ~20:38 at 20:11.

## RESUME (fresh agent)
0. `py -3.10 -I tools/renderq/renderq.py wait 1031-201118-textures-r014-packs-b`; check bench-pk14h3-gui_hud.png
   (C:\qfb\shaderdev\rounds\screenshots, timestamp after 20:11): medallion clear of hearts and shanks, "27" inside it.
   Then step 4 below (`r014_packs_handoff.py`, look at crops, `--ready`), commit any change, push. Track/journal
   already written in step 3 (add a line only if the re-render changes something).
1. (done) `py -3.10 -I tools/renderq/renderq.py wait 1031-194643-textures-r014-packs`.
2. HUD frames bench-pk14h{1,2,3}-gui_hud.png (C:\qfb\shaderdev\rounds\screenshots): no screen open, hearts clear of
   chat, hotbar ours (grace strip + diamond), boss bar tarnished, 7.5 hearts, FULL food (10 shanks), armour 13.
   XP number NOT lime (h1 pale gold, h2 bone white, h3 gold on a medallion)? If lime: XpBarStyle did not load
   (log in the renderq trial: %APPDATA%\.qf-trials\renderq\logs) -> fix, rebuild jar in C:\qfb\wt-r011-fb
   (-PqfDebugTools=true), copy to jars-r014, resubmit. If hearts healed above 7.5: the gamerule did not stick.
   Check the plate does not cover the hearts/food (22 GUI px gap between them).
3. View 6 (bench-pk14{a,g1,g2,g3}-r13_mob_6.png): A Patrix white, g1 red scarf, g2 buttons, g3 packed snow.
4. `py -3.10 -I tools/textures/r014_packs_handoff.py` (dry), look at C:\qfb\shaderdev\r014\packs\ crops (XP_BOX,
   ICON_BOX may need nudging), then `--ready`.
5. Track ops/tracks/textures.md (packs bullet), one journal entry ops/journal/textures.md; commit own hunks; push
   after `git log origin/main..main`. Owner question for the hand-off: ship XpBarStyle (client-only qf-content hook)?

### 2026-10-31 20:40 (orchestrator): hand-off done
- 1031-201118-textures-r014-packs-b (pk14h3) checked: medallion clear of hearts and shanks, "27" inside it.
- Crops checked as a sheet (HUD full/icons/XP x3, mob 6 x4). Note for the critic: the Faithless golem (g1) stands
  side-on, so its face is hidden and the red scarf shows; not a texture fault.
- `r014_packs_handoff.py --ready` run: packs_scenes.json (4 scenes), crops, PACKS-READY in C:\qfb\shaderdev\r014\.
