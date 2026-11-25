# r016: packs, minimal sleek HUD + Infernum-style boss bars (texture-dev, 2026-11-01)

Work order: ops/checkpoints/r016-plan.md "HUD". Owner notes: docs/design/shaders/feedback/r015.json (pk-hud*).
Base/builders/traps: r015-packs.md, r014-packs.md. Bench worktree C:\qfb\wt-r011-fb (XpBarStyle/GuiShots identical
to the repo's at start).

## Step 1 (done): Infernum Mode's boss bar, studied (never copied)
Source: github.com/InfernumTeam/InfernumMode (code MIT; art is theirs, study only), Content/BossBars/BaseBossBar.cs,
Textures/*.png, Assets/Effects/Overlays/BossBarShader.fx; wiki infernummod.wiki.gg/wiki/Boss_health_bar. Downloaded to
the session scratchpad only (infernum-study/), assembled per the draw code to see it whole. Nothing goes in the repo.
What makes it work:
- Shape: one THICK bar (fill 33 px tall in a 352x82 frame, ~1:7), not a hairline. Heavy bevelled gold rails top and
  bottom (lit top edge, a specular streak, dark under-edge and a dark drop edge), a pointed arrowhead cap at one end,
  a round medallion socket (dark wine disc in a gold ring) overlapping the other end.
- Fill: saturated crimson (153,24,51)->(208,47,63), shaded in 8 pixel-stepped vertical bands slanted ~6 deg, brighter
  in the middle. The EMPTY channel is dark wine, not black or clear, so the bar reads as one solid object at any health.
  A small gold bullet cap rides the fill's leading edge. The fill drains toward the medallion.
- Name: not shown (we keep ours, outlined: owner).
- Numbers: percentage (2 decimals) in gold text (210,158,68) in a slanted dark tab with a gold rim, on top of the bar
  near the medallion. No raw HP.
- Phases: slanted crimson pips in a gold shell beside the percent tab; a pip pops off (fade + gold sparkles) when its
  phase ends; the bar shows health within the current phase only.
- Icon: the boss's head icon in the medallion with a soft glow; orange-red + fire particles when enraged.
- States/animation: fade in 25 ticks, out 30; a riveted gold plate overlays the fill while the boss is invulnerable.
- Palette: two materials only (warm gold metal + wine/crimson), opaque, high contrast on bright and dark backgrounds.
What 1.7.10 allows: the vanilla bar is a 182x5 strip with no number, icon or phase data. So the chunky bar, the
percent, the medallion and the fade need the XpBarStyle hook extended (draws its own bar instead of vanilla's, from
a separate sprite sheet); per-boss icons and phase pips need data 1.7.10 does not have (generic emblem; quarter ticks).

## Next
- Hook: XpBarStyle qf.boss.* "bar mode" (own sheet textures/gui/qf_bossbar.png; back, fill clipped by health, tip at
  the fill edge, over sprite, percent text, name y, fade-in). Build in C:\qfb\wt-r011-fb -> C:\qfb\renderq\jars-r016.
- tools/textures/qf_hud_r016.py: 4 minimal sleek HUDs (from r014's, no Elden Ring motifs) + 4 boss bars; mock sheet.
- Spec textures-r016-packs.json: day (views-r013 gui_hud) + night (views-r016-night.txt, gui_hud at worldTime 18000).

## Step 2 (done): hook bar mode, bench jar
- XpBarStyle.java (repo + worktree C:\qfb\wt-r011-fb): qf.boss.sheet/top/back/fill/tip/over/pct/namey/fade (javadoc
  lists them). Cancels vanilla's bar in Pre and counts statusBarTime down itself. Built -PqfDebugTools=true ->
  C:\qfb\renderq\jars-r016\QuestForgeContent-1.0.0.jar (15:49). Not yet committed.
- Next: tools/textures/qf_hud_r016.py (4 HUDs + 4 boss bars + mock), then spec + submit.

## Step 3 (done): designs built, render SUBMITTED
- tools/textures/qf_hud_r016.py (own art): HUDs refined/glass/gunmetal/wine (icons: glossy dome / candy glass / cut
  facets + chrome rim / gold rim; hotbars: smoked strip / glass tiles / gunmetal wells / wine between gold rails),
  each paired with a boss bar ember/obsidian/ironclad/gilded (sheet textures/gui/qf_bossbar.png: back 0,0; fill 0,48;
  tip 0,72; over 0,96). Mock: `--mock M.png --icons I.png --boss B.png` (scratchpad r16/ looked right: GUI 4 + GUI 1).
- Zips C:\qfb\textures\r016\QF-r016-hud-<design>.zip. Night views tools/textures/views-r016-night.txt (18000).
- Spec tools/renderq/specs/textures-r016-packs.json: pk16a-d day, pk16an-dn night. SUBMITTED
  1101-155720-textures-r016-packs at 15:57 (two submissions ahead, ETA was ~16:09 for them + owner-idle gate).
- Next: `py -3.10 -I tools/renderq/renderq.py wait 1101-155720-textures-r016-packs` (one call; checkpoint + exit if
  the ETA is past 10 min); check frames (bar mode drew? vanilla strip gone? name outlined, percent, food full, 7.5
  hearts, no screen, chat clear); then tools/textures/r016_packs_handoff.py (to write) --ready.
- Hand-off script written (not yet run): tools/textures/r016_packs_handoff.py (scenes pk-hud [A-D + M mock],
  pk-hud-icons [A-D + M], pk-hud-xp [A-D], pk-hud-boss [A-D day-over-night stacks + M boss mock]; BOSS_BOX
  540,0,2020,270; HUD boss strip 0-280). Committed e225d64 (my files only).
- Exited at 15:59 to wait: the queue ETA was ~16:14 (> 10 min), owner-idle gated.

## RESUME (fresh agent)
1. `py -3.10 -I tools/renderq/renderq.py status`; if this render's ETA is under 10 min, ONE call:
   `py -3.10 -I tools/renderq/renderq.py wait 1101-155720-textures-r016-packs`; else re-checkpoint and exit.
2. Frames C:\qfb\shaderdev\rounds\screenshots\bench-pk16{a,b,c,d}{,n}-gui_hud.png (newer than 15:57 on 11-01).
   Review as a contact sheet + crops (boss strip 0-280 px; HUD 640-1920 x 1100-1440). Check: the bar-mode boss bar
   drew (thick bar + medallion + percent "62%"; NO vanilla thin strip under it: if both show, the Pre cancel failed;
   if only the thin vanilla strip shows, XpBarStyle did not read qf.boss.sheet -> log in
   %APPDATA%\.qf-trials\renderq\logs); name outlined; night frames dark behind the bar; hotbar/selection/icons ours;
   XP number recoloured on its medallion; food 10 shanks, 7.5 hearts, armour 13; no screen open; chat clear.
3. Fix what is broken (qf_hud_r016.py; hook -> rebuild in C:\qfb\wt-r011-fb -PqfDebugTools=true, rm then cp to
   C:\qfb\renderq\jars-r016), resubmit only the failing tags if needed.
4. `py -3.10 -I tools/textures/r016_packs_handoff.py` (dry); look at every crop in C:\qfb\shaderdev\r016\packs\
   (nudge ICON_BOX/XP_BOX/BOSS_BOX if cut); then `--ready` (packs_scenes.json + PACKS-READY in C:\qfb\shaderdev\r016).
5. ops/tracks/textures.md packs bullet (r016: 4 HUDs + 4 boss bars, bar-mode hook, still the owner's yes), ONE journal
   entry in ops/journal/textures.md (Infernum study, the designs, bar mode, the render), commit own hunks,
   `git log origin/main..main`, push. Report <= 5 lines; say the XP colour, medallion and boss bar need the hook's yes.

## Step 4 (2026-11-01 18:45): frames reviewed, one fix re-rendering
- 1101-155720 done (18:42). Bar mode drew in all 8 frames (thick bar + medallion + 62%, no vanilla strip). Names
  outlined, legible on day sky and night sky. GUI-scale-1 sim (nearest-sample the GUI-6 frames at 6k+1): every rim,
  number and icon survives. No chat in frame; hearts/armour keep vanilla rows. The 4 HUDs and 4 bars all differ
  (A/D closest: both round medallion + gold point, but orange vs crimson fill, flame vs skull, percent beside vs tab below).
- Fix: Ember percent dx 212 -> 215 (its outline touched the arrowhead point). Spec textures-r016-packs-a.json (pk16a,
  pk16an only) SUBMITTED 1101-184442-textures-r016-packs-a behind 2 shader jobs (ETA ~7 min).
- Next: wait that ID once; crop A's percent; then r016_packs_handoff.py dry, look at crops, --ready; track + journal; commit.
- 18:51 A re-render 1101-184442 landed: percent clear of the point, day and night. Hand-off dry run OK, every crop
  checked (boss, icons, xp, hud). Found: B and C XP medallions near-identical (slate pill, white number). Fix: Gunmetal
  xp_num FFB650 (its bar's orange), medallion chamfer 5 -> 7 (hex). Spec textures-r016-packs-c.json SUBMITTED
  1101-*-textures-r016-packs-c (pk16c, pk16cn). Honest note for the scene text: heart/food rows read nearly alike
  across the four at play size; the designs part in hotbar, selection, XP bar, medallion and boss bar.
- Next: wait it once; check C's xp crop; add that note to r016_packs_handoff.py pk-hud text; --ready; track/journal; commit.
- 18:57 C re-render 1101-185125 landed (orange number, hex tag, readable at scale 1). Hand-off text updated
  (gunmetal desc; icon-rows-alike note). `--ready` run: 4 scenes, PACKS-READY. Track + journal written. DONE except commit/push.
