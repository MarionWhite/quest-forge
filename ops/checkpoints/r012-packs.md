# r012: packs fixes from the owner's r011 notes (texture-dev, 2026-10-28)

Work order: ops/checkpoints/r012-plan.md "Packs". Builders/world/views/jar: ops/checkpoints/r011-packs.md.
Priorities: (1) creative tabs (combat broken, brewing not rich), furnace, text contrast on all copied GUI,
TNT all lettered; (2) every mob non-vanilla (passive too); (3) 2-3 QF HUD/boss-bar directions; (4) Chisel route
for the Soartex shelf (report only). Hand-off: C:\qfb\shaderdev\r012\ (r011 vs r012) + PACKS-READY.

## Progress log
### 2026-10-28 step 0: started, reading
- r011 baseline frozen: C:\qfb\textures\r012\QF-r011-packs-final.zip, QF-r011-gui-final.zip (copies of the 10-28 09:19 builds).
### 2026-10-28 step 1: GUI + TNT fixes (code, offline preview)
- Causes found: (a) Faithless's tabs.png / tab sprites are 26 px on a 26 px pitch, 7 columns (1.19.3+); 1.7.10 reads 28 px
  cells at u=28*col, so every tab was cut across two of Faithless's (seams, stray banner edges = "broken"). (b) its
  tab_items.png is an older grey slotless panel with a dark top band over row one. (c) plaques are flat (104,61,39) wood
  sized for Faithless's font: 1.7.10's 0x404040 titles sink in and overrun them ("Enchant", "Inventory"). (d) enchanting
  spell text 0x685E4A on a red ribbon.
- r007gui.py: tabs rebuilt on 1.7.10's grid (sprites widened 26->28, scrollers at 232,0/244,0); creative style
  `--creative faithless` (its wood-framed search panel + hotbar cells over the 9x5 grid) or `book` (recipe-book parchment
  page, every tab a red banner bookmark); plaques widened to the measured 1.7.10 title + repainted light honey wood;
  enchanting ribbon parchment body + red seal for the level number, hover sprite darkened under the yellow text.
- r007packs.py: TNT lettered on every block (CTM fixed, tiles=0); `--creative` passed to the gui part.
- Offline preview: scratch prev_gui.py (draws 1.7.10's creative/container layout with the real font) looked right.
- Furnace: same plaque fix; its arches/flame/arrow already sit at 1.7.10's slots. The extra lit copy at y 172 is unused
  by vanilla (no CustomGuis on 1.7.10).
- Next: mobs (Conquest fallback + Patrix remap), world r012 with passive mobs, HUD directions, spec + render.
### 2026-10-28 step 2: mobs, world, HUD, render submitted
- tools/textures/patrix_remap.py (new): Patrix CEM per-face UVs -> 1.7.10 box UVs (stacked boxes, decals for snouts) for
  zombie_pigman, iron_golem, witch, cow, sheep, sheep_fur, chicken, blaze. r007packs.py part_mobs: `--mobs remap`
  (Patrix as is > Patrix remapped > Conquest_ 1.8 for the rest) | `conquest` (Patrix as is > Conquest) | `patrix` (r011).
  Both modes: every 1.7.10 mob texture non-vanilla (63 files; villagers, horses, squid, bat, slimes, ghast, wither, dragon
  from Conquest).
- World C:\qfb\textures\world-r012 (`build_r011_world.py --round 12`): hall x 223-271, 26 mobs 1.75 apart (+ mooshroom,
  horse, villager, squid, hanging bat). Views tools/textures/views-r012.txt (r12_mob_1..7 + r011 GUI/TNT views).
- tools/textures/qf_hud.py (new, our own art): HUD directions iron / arcane / banner (hotbar, selection, XP, boss bar at
  1.7.10 UVs; Faithless hearts/food kept). Note: r011's Faithless XP progress sprite was garbled (green glyph strip).
  Boss bar is one 182x5 strip on 1.7.10: a framed/per-boss bar needs a GuiIngame hook.
- SUBMITTED 1028-150936-textures-r012-packs (45 renders; queue ahead: shader + other texture agent ~17 min at 15:09).
  Tags pk12a (r011 frozen), pk12b (remap mobs, faithless creative, fixes), pk12c (conquest mobs, book creative),
  pk12h1-3 (HUD iron/arcane/banner). Zips in C:\qfb\textures\r012\ (prebuild owns them).
- Next: wait; review mob frames (drop remaps that break -> conquest), GUI crops; hand-off script r012 -> C:\qfb\shaderdev\r012\;
  Chisel route note; journal; track; commit; push.
### 2026-10-28 step 3: Chisel route for the Soartex shelf (report only, nothing shipped)
- Pack ships Chisel 2 2.3.10.37 (mods/Chisel.jar) and CraftTweaker 3.1.0 legacy. Chisel 2.3.10 has NO MineTweaker
  handler, but it has IMC (com/cricketcraft/chisel/api/IMC): `variation:add` with data "group|modid:block|meta",
  resolved through the block registry. Its bookshelf group already has 9 variants (default, abandoned, brim, hoarder,
  historian, necromancer, necromancer-novice, rainbow, redtomes): textures assets/chisel/textures/blocks/bookshelf/
  <v>-ctmh.png (64x64 = 2x2 tiles of 32, horizontal CTM) + <v>-top.png 32x32. BlockCarvableBookshelf keeps
  getEnchantPowerBonus. (Soartex's own biome variants are named brim/react/tome/color: Soartex drew for Chisel once.)
- Route A, texture only (ships with the pack build, no jar): override one existing variant, e.g. `default`, with a
  ctmh sheet built from Soartex's 3 sides (left/middle/right/single tiles cut from its frame) + its top. Costs a variant.
- Route B, a new variant (keeps all 9): qf-content registers `questforge:bookshelf_soartex` (BlockBookshelf subclass:
  enchant power 1, drops 3 books, own icon or ctmh), and in init sends
  `FMLInterModComms.sendMessage("chisel", "variation:add", "bookshelf|questforge:bookshelf_soartex|0")`. Client and
  server jar (block id), `trial.py install` both; new content, so the owner's yes first.
### 2026-10-28 step 4: CHECKPOINT, exiting while the render queues (ETA ~15:45; over the 10-min wait rule)
- Committed: builders, patrix_remap.py, qf_hud.py, world flag, views-r012.txt, spec, tools/textures/r012_packs_handoff.py
  (dry-run OK; it reads tags pk12a/b/c/h1-3 and writes C:\qfb\shaderdev\r012\packs_scenes.json + packs\ crops).
- RESUME (fresh agent):
  1. `py -3.10 tools/renderq/renderq.py wait 1028-150936-textures-r012-packs` (if under 10 min left), else status.
  2. Review contact sheets of C:\qfb\shaderdev\rounds\screenshots\bench-pk12{a,b,c}-r12_mob_*.png and the gui_* /
     gui_hud frames (h1-3). Check: every mob non-vanilla; remapped mobs (pigman, golem, witch, cow, sheep, chicken,
     blaze) not broken - any broken one -> drop it from patrix_remap.SPECS (Conquest takes over) and reshoot B only;
     creative tabs aligned (B, C), plaques/ribbons readable, TNT all lettered, bat/squid/horse/villager in frame.
  3. `py -3.10 -I tools/textures/r012_packs_handoff.py --ready` (writes PACKS-READY).
  4. Rewrite ops/tracks/textures.md packs bullet; one journal entry ops/journal/textures.md; BOARD textures row;
     commit own hunks; `git log origin/main..main`; push.
- Owner questions carried in the scenes: creative B vs C; HUD direction + framed boss-bar hook (qf-tweaks GuiIngame);
  per-mob Patrix-remap vs Conquest; Chisel route A (texture) vs B (new block via IMC) - see step 3.
