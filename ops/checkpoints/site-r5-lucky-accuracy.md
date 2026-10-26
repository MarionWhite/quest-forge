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
- [ ] **Audit hook:** `lucky/?audit=1&dump=1` runs the page's own resolvers over every drop and
  every structure. It puts a table in the dump JSON listing, for each id:
  - each block id, with its resolved face textures or FALLBACK;
  - each item id, with its icon or FALLBACK;
  - each entity id, with its `mobKey` or FALLBACK;
  - each equipment id;
  - whether the reel tile matches the drop's main action (kind and id);
  - text with any leftover `§`, `#` or raw NBT.
  `tools/site/audit_lucky.py` prints the table and exits 1 on any FALLBACK or mismatch.
- [ ] **Zero fallbacks:**
  - Real multi-face blocks: tnt, cake (the 1.7.10 cake model and textures), furnace, crafting
    table, pumpkin, melon, bookshelf, sponge, hay, logs, quartz, sandstone, grass, mycelium,
    command block, beacon, enchanting table, anvil, chests, dispensers, OreSpawn blocks, and
    every other block id the audit lists.
  - Stained clay and wool use their damage colours.
  - Items come from the sprite sheet.
- [ ] **Death pole:** a redstone block with TNT every 10 blocks above it, falling and stacking.
  Check every other falling column against its raw line the same way.
- [ ] **Iron bars:** the 1.7.10 pane model, connecting to neighbours and to solid blocks.
- [ ] **Lucky choice sign:** the 1.7.10 sign model with the structure's text lines rendered
  legibly.
- [ ] **Equipment:** `spawnMob` in `fx.js` passes the drop's `equipment` to `makeMob`. The mobs
  task adds the armour rendering in `site/lib/mc`, so feature-detect until it lands.
- [ ] **Reel tiles:** a contact sheet of all 306 reel tiles, using `lineup.html?tiles=` or a
  hook of your own. Each tile shows the right thing.
- [ ] **Re-vet:** `vet_lucky.py` passes on all 306 drops (use `--jobs 2`, and rerun timeouts
  alone). Look at the sheets for every scene key, not only the counts.

## Done
(nothing yet)

## Next
Start with the audit hook and script, then fix by category in order of how many drops each
category affects.
