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
