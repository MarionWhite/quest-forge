# r011: copy the r007 packs' best parts (texture-dev #2, 2026-10-27)

Owner, 2026-10-27: "please also copy from the other [packs] that we pointed out all the details from in round 7
other than the details that we have already gotten right like the underwater effects from conquest."
Read ops/checkpoints/r011-plan.md (copy first, then improve; small rounds) and the r007 notes below. The owner's own
words: docs/design/shaders/feedback/r007.json (scene tex-packs and the fl-* scenes) and the screenshots in
docs/design/shaders/feedback/attachments/r007/. Summary of what was taken from each: docs/design/textures/direction.md
l.285-296, l.404-511.

## The packs (all at C:\qf-world\reference-packs, see its README.txt)
Copying allowed into the private pack (CLAUDE.md "Licences"). NEVER git-add their files; the build reads them from
that folder at build time. Lab images of our own game are fine; never post their raw textures on the public site.

| Pack | File | What to take (owner, r007) |
|---|---|---|
| Faithless v1.2 (1.20.5-1.21) | Faithless/Faithless.zip | Item sprites ("fucking awesome"), every potion its own bottle shape, every enchantment its own book, GUI (not the main menu), creative tabs, TNT with enchanting-table lettering, boss health bars, its animations. NOT its blocks. |
| Patrix 32x basic 26.3 | Patrix 32x/Patrix_26.3_32x_basic.zip | Mob skins ("especially the mobs"). Its 3D shapes are OptiFine CEM: skins only where they map onto 1.7.10's vanilla model UVs; list the mobs that need CEM geometry and stop there. |
| Conquest_ 1.8 (1.6-1.7.x names) | Conquest_/Conquest_1.8.zip | "Environmental lighting and effects ... the visual effects of being in the water or specific other environments": sky (mcpatcher/sky), fog and colour (color.properties, colormaps), particles, ambient sounds. Underwater is DONE (owner), skip it. Not its block textures ("I don't think I like the textures of Conquest"). Some of this may be shader-side: hand those to ops/checkpoints/r011-shader.md as a note, don't edit shaders. |
| Soartex Forever R.1.6 | Soartex Forever/Soartex Forever.zip | Bookshelves only. Compare with the owner's r007 screenshot; if it's a different Soartex, say so. |

Already done, don't redo: Faithful 64x blocks (stone bricks, metals), Vanilla Normals Renewed (light and reflections),
underwater effects. Stay True leaves and wheat belong to the other texture agent (r011-stay-true.md).

## Work
1. For each item, find the files in the pack, map 1.13+/1.20 names to 1.7.10 names (`textures/items`,
   `textures/blocks`, `textures/gui`, `textures/entity`, mcpatcher paths), and check what the 1.7.10 pack and
   Angelica actually support (CIT, CTM, random mobs, animations, custom sky, color.properties). Where a feature
   needs a hook (e.g. potion shapes by damage value), reuse what our r010 items work already does.
2. Build step that copies them in at build time (extend tools/textures, a separate module/flag so you don't collide
   with the Stay True agent editing build_qf_textures.py in parallel; commit only your own hunks).
3. Renders through renderq: items/GUI/creative tabs, potions and books, TNT, a boss bar if a scene can show one,
   mobs lineup, a bookshelf wall, Conquest environment scenes (sky, fog, particles). Measure frame time where
   anything could cost (animations, sky layers).
4. Hand the r011 scenes to C:\qfb\shaderdev\r011\ (like texture_scenes.json in r010): our current r010 vs the copy.
   The items scene answers the owner's r010 ask, "at least one other art style set for all of them before we commit".

## Progress log
