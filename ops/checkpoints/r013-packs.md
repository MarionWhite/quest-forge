# r013: packs from the owner's r012 notes (texture-dev, 2026-10-29)

Work order: ops/checkpoints/r013-plan.md "Packs". Builders/world/views/traps: ops/checkpoints/r012-packs.md.
Settled: Faithless GUI (B) everywhere, every TNT lettered, Patrix-remap mobs (B) in all views.

## Progress log
### 2026-10-29 step 1: HUD directions (code, offline mock)
- tools/textures/qf_hud_er.py (new, own art, 2x sheets): tarnished / grace / ashen. Hearts, food, armour, air, mount
  icons are 8 px bar segments that tile into one 80 px bar (Forge 10.13 GuiIngameForge draws them 8 px apart; blend on
  for bars + hotbar, OFF for XP, so icon pixels are opaque or clear). Lost HP blinks pale gold. Boss strip gets caps.
  widgets.png is QuestForge.zip's (menu buttons kept, read-only from the live dir) with our hotbar/selection.
- Mock: scratch hud_prev.png (looks right). Next: renderq job field rps_top (packs above QuestForge.zip) so the
  hotbar draws in game; HUD job measure >= 210 ticks so chat (posted at scene start) has faded off the hearts.
### 2026-10-29 step 2: mobs, world, renderq rps_top, render SUBMITTED
- Creative (3): B (Faithless frame) does NOT share the book page's "few px short" bug (r012 crop pk-creative-combat-pk12b:
  hotbar row inside its cells, frame intact). Nothing to fix; C is not picked.
- r007packs.py `--faithless-mobs`: snow golem, slime, magma cube, squid from Faithless (vanilla box layout; Patrix's
  slime/magma/squid are CEM layouts, its snow golem near-vanilla white). Patrix wither_armor (scrolling overlay, layout-
  free); horse_markings_blackdots derived from Conquest's whitedots (same 1.7.10 layout, darkened). Still vanilla: none.
  Wither body stays Conquest (Patrix's wither.png is a different layout; not remapped, never in a frame: a live wither
  would blow up the hall).
- build_r011_world.py --round 13 -> C:\qfb\textures\world-r013: hall in 6 groups (GROUPS_R013), wither skeleton centred
  in view 1, bat under an oak beam at y 70 (camera 4.5 off: > 4, so it stays hanging); glass tanks x 258-268 z 218-221:
  squid in water (it died out of water in r012), slime, magma cube (they hopped out of frame). views-r013.txt.
- renderq: job field rps_top (packs above the live QuestForge.zip); README row. Cache keys unchanged when unset.
- Spec tools/renderq/specs/textures-r013-packs.json: pk13a (r012 B frozen, new views), pk13b (r013), pk13h1-3 (HUD
  tarnished/grace/ashen, rps_top, measure 220). Zips in C:\qfb\textures\r013\.
- SUBMITTED 1029-121538-textures-r013-packs (17 scenes; queue ahead: r013-gems-ctm ~4 min at 12:15).
- Next: wait; review mob contact sheets + HUD crops (hotbar ours? hearts clear?); handoff script
  tools/textures/r013_packs_handoff.py -> C:\qfb\shaderdev\r013\packs_scenes.json + PACKS-READY; track, journal, commit.
### 2026-10-29 step 3: first render reviewed, fixes, runner restarted, re-render SUBMITTED
- 1029-121538 (first render) findings: (a) the HUD zips never reached the stack: the runner process (pid 27096)
  predated the rps_top edit and ran the old batch.py (h1-h3 frames identical, the pack's own hotbar). The chat fix DID
  work (measure 220: hearts uncovered). Runner restarted (pause --after-boot, stop, start, resume; pid 11044), no other
  agent's boot interrupted. (b) View 1: the Patrix wither skeleton is clear, centred beside the skeleton. View 6:
  Faithless snow golem (red scarf) reads non-vanilla; bat hangs from its beam. (c) FrameBench's FOV is very wide (a
  4-mob group 4.5 blocks off spans ~550 of 2560 px): the hand-off crops the group (MOB_BOX) instead of moving cameras.
  (d) Tanks: slime and magma cube in frame; squid at the edge of a 2-deep tank -> tank now 1 deep (z 219), camera
  2.2 off the glass. The streaks there are our glass texture, not rain (FrameBench clears weather).
- B creative: no short-page bug (see step 2).
- Hand-off script tools/textures/r013_packs_handoff.py (dry run OK on the old frames; packs_scenes.json removed again).
- SUBMITTED 1029-122545-textures-r013-packs (17 scenes; queue ahead ~16 min at 12:25: shader-r013 loop1a/1b,
  gems-ctm-c). Over the 10-min rule: exiting.

## RESUME (fresh agent)
1. `py -3.10 -I tools/renderq/renderq.py wait 1029-122545-textures-r013-packs` if under 10 min left, else exit again.
2. Check pk13h1/h2/h3 gui_hud frames DIFFER (md5) and the hotbar is ours (thin bars, dark cells), hearts clear.
   If identical again: the runner did not load rps_top (status pid != 11044?) -> do not resubmit blindly.
3. Review crops: hall views r13_mob_1..6 at MOB_BOX; set TANK_BOX in r013_packs_handoff.py from the view-7 frame
   (squid inside the water now?). Contact sheets in a private folder (the scratchpad root is shared: sheet.py got
   overwritten by another agent).
4. `py -3.10 -I tools/textures/r013_packs_handoff.py --ready` (writes C:\qfb\shaderdev\r013\packs_scenes.json,
   packs\ crops, PACKS-READY; pk-hud-mock.png is already in packs\).
5. Track ops/tracks/textures.md packs bullet; journal entry ops/journal/textures.md (one, dated, newest first);
   commit own hunks; `git log origin/main..main`; push.
- Boss-bar hook (answer for the owner, also in the HUD scene text): client-only, no transformer, no server change.
  GuiIngameForge fires RenderGameOverlayEvent.Pre(ElementType.BOSSHEALTH) before drawing the 182x5 strip; a qf-tweaks
  client event handler cancels it and draws a framed bar (own 256x16 sheet, name left-aligned above, bottom centre)
  from BossStatus.bossName/healthScale/statusBarTime; per-boss frames keyed by the nearest IBossDisplayData entity's
  class (the name is localised). The same event (HEALTH, FOOD, ARMOR, AIR) could later move the bars to the top left
  with true end caps (texture-only bars cannot have caps: every segment is the same icon).
