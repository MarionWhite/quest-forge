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
