# site-r5-lucky-accuracy (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns:
- `site/lucky/{blocks,reel,scenes,structscenes,structures,beats,fx,wells}.js`
- `site/lucky/data/*`
- `tools/site/{build_lucky,vet_lucky}.py`
- new `tools/site/audit_lucky.py`
Previous state: `ops/checkpoints/site-lucky-outcomes.md`.

## Owner's words (2026-10-26)
- "The result 'Cake Falls' shows an iron block in the reel and the cake texture is messed up. I
  am positive that there are a shit ton of errors like this, and we need to do a deep audit to
  polish all of these."
- "The death pole animation is really good, but instead of TNT it drops stone blocks. These all
  have to be accurate."
- "The anvil trap animation is pretty good, but the iron bars don't connect like they do in game."
- "When you get choice of 2 lucky blocks, the sign doesn't render properly."
- "King bob doesn't have armor." The data says he should: OreSpawn Queen armor and the Queen
  Battle Axe. The other Bobs wear enchanted diamond armor.
- Praised: bat swarm ("VERY well done"), death pole, anvil trap, most mob spawns.

## Done means
- [x] **Audit hook (page `lucky/audit.html`, runner `tools/site/audit_lucky.py`; `?audit=1` on index is a request to lucky-flow):** `lucky/?audit=1&dump=1` runs the page's own resolvers over every drop and
  every structure. It puts a table in the dump JSON listing, for each id:
  - each block id, with its resolved face textures or FALLBACK;
  - each item id, with its icon or FALLBACK;
  - each entity id, with its `mobKey` or FALLBACK;
  - each equipment id;
  - whether the reel tile matches the drop's main action (kind and id);
  - text with any leftover `§`, `#` or raw NBT.
  `tools/site/audit_lucky.py` prints the table and exits 1 on any FALLBACK or mismatch.
- [x] **Zero fallbacks (audit exits 0; 3 config typos are notes: SeamonsterScale, TRexRooth, RoyalSword):**
  - Real multi-face blocks: tnt, cake (the 1.7.10 cake model and textures), furnace, crafting
    table, pumpkin, melon, bookshelf, sponge, hay, logs, quartz, sandstone, grass, mycelium,
    command block, beacon, enchanting table, anvil, chests, dispensers, OreSpawn blocks, and
    every other block id the audit lists.
  - Stained clay and wool use their damage colours.
  - Items come from the sprite sheet.
- [~] **Death pole (TNT now a real TNT block; verify in scene):** a redstone block with TNT every 10 blocks above it, falling and stacking.
  Check every other falling column against its raw line the same way.
- [ ] **Iron bars:** the 1.7.10 pane model, connecting to neighbours and to solid blocks.
- [ ] **Lucky choice sign:** the 1.7.10 sign model with the structure's text lines rendered
  legibly.
- [ ] **Equipment:** `spawnMob` in `fx.js` passes the drop's `equipment` to `makeMob`. The mobs
  task adds the armour rendering in `site/lib/mc`, so feature-detect until it lands.
- [x] **Reel tiles (`lucky/gallery.html?tiles=A-B`; sheets scratchpad r5/lucky-accuracy/tiles):** a contact sheet of all 306 reel tiles, using `lineup.html?tiles=` or a
  hook of your own. Each tile shows the right thing.
- [ ] **Re-vet:** `vet_lucky.py` passes on all 306 drops (use `--jobs 2`, and rerun timeouts
  alone). Look at the sheets for every scene key, not only the counts.

## Done
- Audit: `python3 -I tools/site/audit_lucky.py [--all] [--json OUT]` loads `site/lucky/audit.html` (own page; the page asks blockdefs/blocks/mob lib/reel which picture each id resolves to) and exits 1 on FALLBACK, a tile that differs from the main action, leftover codes, or a falling/placed block that differs from its raw config line. Now 0 problems, 3 notes (config typos: SeamonsterScale, TRexRooth, RoyalSword are not registered in OreSpawn, nothing drops).
- Cause of the owner's errors: blocks.js only knew ~25 ids; tnt, sponge, ores, coal/lapis/redstone blocks, netherrack, dirt, stone, brick, OreSpawn blocks etc. fell to a stone cube; cake squashed its full-height side texture; panes ignored neighbours; the sign ignored meta and used a fake texture; chest body floated and was inside-out (the mob library's boxes wind inward: DoubleSide needed).
- New `blockdefs.js` (rules from decompiled 1.7.10: getIcon, RenderBlocks), `blocks.js` rewritten (position-based UVs like RenderBlocks), `mcfont.js` (baked from ascii.png by `tools/site/gen_mcfont.py`), 80 textures copied from the 1.7.10 client jar.
- Reel: block/build/structure tiles drawn from the real models (`reel.js` iconFrom); `build_lucky.py tile_for` follows the main action (temples and towers are mini builds, structures draw themselves, effect/xp/fireworks use their item). `lucky/gallery.html?tiles=A-B` and `?blocks=all` make contact sheets.
- Falling cake is a full cube with the cake side texture (vanilla RenderFallingBlock) and becomes the 14x8x14 cake on landing.
- Lucky choice: sign model with the MC bitmap font, faces Steve; camera moved to his side. Iron bars connect to bars, glass and opaque blocks. TNT in the death pole is a real TNT block.
- `fx.spawnMob` passes `equipment` (own or the drop's entity action) to makeMob.
- Commits: 6bffb74, 1901dfb.
- Sheets: tiles r5/lucky-accuracy/tiles/t*.png, scenes s1/, s2/ (scratchpad .../r5/lucky-accuracy/).

## Next
- Full vet (`vet_lucky.py r5/lucky-accuracy/vet1/<a..d> --jobs 2 --timeout 240`, by key groups), look at sheets per key.
- Verify King Bob armour once mobs-gear lands (makeMob must read opts.equipment: list of item ids).

## Log (2026-10-26)
- Plan: new pure-data `site/lucky/blockdefs.js` (`blockSpec(id, meta, o)`: faces, shapes, files) used by blocks.js
  (models with 1.7.10 per-face UVs), reel.js (tiles render makeBlock) and fx.blockCube. New `site/lucky/audit.html`
  + `site/lucky/audit.js` (page-side resolvers over every drop/structure) and `tools/site/audit_lucky.py`.
- Textures copied from the 1.7.10 client jar into site/lucky/tex/blocks (wool/clay/glass colours, cake_bottom/inner, quartz,
  planks/logs, brewing base, etc.) and entity/chest_trapped.png. Jar extracts: scratchpad r5/lucky-accuracy/jar/{mc,os}.
- Source of truth for block icon/shape rules: mods/qf-content/build/rfg/minecraft-src (decompiled 1.7.10).
- Falling cake in vanilla is a full cube (default bounds) with cake_side's transparent top half; landed cake is the 14x8x14 model.

## Requests
- lucky-flow: `lucky/?audit=1` should redirect to `audit.html` with the same query (or I can be reached at `lucky/audit.html?dump=1`).
- lucky-life: pass `equipment: e.equipment` in mobscenes.js spawnMob calls (fx.spawnMob also falls back to the drop's own entity action).
- lucky-life: camp.js's "QUEST FORGE camp" sign stands in front of the lucky-choice structure (seen from behind, dark) and covers the left lucky block in the scene; move or hide it for that scene.
- lucky-flow: `?audit=1` on lucky/index.html should `location.replace('audit.html' + location.search)`.
