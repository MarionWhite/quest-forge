# r013 textures: connected gem blocks (texture-dev, 2026-10-29)

Brief: ops/checkpoints/r013-plan.md "Textures". Owner picked gems C (A's Faithful facet gems + glass maps + shader SSR),
"I think they should have connected textures though". Hand-off: C:\qfb\shaderdev\r013\ (scenes, crops, marker).

## Progress log
### session 1
- CTM path, evidence: Angelica 2.2.33 (C:\qfb\client-ang2\mods) bundles MCPatcherForge CTM (com/prupe/mcpatcher/ctm,
  TileOverrideImpl$CTM needs 47 tiles); verified for connected glass in r007 renders (direction.md section 1) and TNT
  fixed / bookshelf random in r012. Its neighborMap (TileOverride <clinit>, javap) is the standard MCPatcher 47 layout
  (bits 0 W,1 SW,2 S,3 SE,4 E,5 NE,6 N,7 NW; map[255]=26 interior, map[85]=46 four inner corners).
- PBR on CTM tiles: Iris AtlasPBRLoader resolves each sprite via TextureMap.completeResourceLocation, which the
  mcpatcherforge ctm_cc MixinTextureMap redirects through TileLoader.getOverridePath, so mcpatcher/ctm/x/0.png ->
  0_n.png / 0_s.png should load. To confirm in the render (gem floor keeps C's SSR look on CTM tiles).
- Reference packs: NONE has connected gem/metal blocks (Stay True only ore overlays + glass/quartz/sandstone CTM;
  Faithful 32x/64x 1.7.10 only glass + sandstone; Patrix/Faithless/Soartex/Conquest none). Layout to copy = the standard
  47-tile ctm as Stay True's and Faithful's glass use it; art = Faithful 64x's own frame + a seamless interior.
- shader-dev's r013-shader.md asks nothing of the gem maps yet. Plan for the wobble: CTM _n flat in the interior,
  bevel only on the outer frame of a connected group (no per-block dome, so no per-block checker in the SSR).

### session 1, renders
- 1029-121044-r013-gems-ctm DONE. Sheets C:\qfb\shaderdev
013\sheets\gems_ctm_full/crop/pillars.jpg, metals_ctm.jpg.
  CTM WORKS in this client: floors and pillars are one slab, frame only on the rim; gold, diamond, emerald, lapis pairs
  joined in diag_column/diag_emerald. PBR on CTM tiles WORKS: the connected floors take C's SSR (mirror the pillar,
  clouds, sun). Flat = one long sun smear like water; facet = sharp glints along the streaks (recommend facet).
  Redstone unchanged (by design). Iron joined but showed a faint vertical line at the old seam: its face shades
  229 -> 226.6 luma left to right and the quilting cut jumped 2.2 luma; fixed with x_mirror (step now 0.31).
- Packs rebuilt (gems identical, iron mirrored). 12:18 guard OK, SUBMITTED `1029-121818-r013-gems-ctm-b`
  (g13facet2 diag_column only). Hand-off script written: C:\qfb\shaderdev
013	extures_make_scenes.py (uses g13*;
  switch metals scene to g13facet2 once rendered; fix the iron sentence: iron DOES connect, the dark shapes on it are a
  reflection present in r12 too).

- Iron 2nd try: g13facet2 showed lines at the mirror axes (col 61 still frame shading): bands -> (4, 2, 4, 3), step
  0.44. Packs rebuilt (gem tiles identical, md5 of diamond+emerald ctm entries 20094d26...). 12:23 guard OK, SUBMITTED
  `1029-122300-r013-gems-ctm-c` (g13facet3 diag_column; queue ETA ~12:37, over 10 min: not waited for).
- HANDED OFF: C:\qfb\shaderdev013	extures_scenes.json (4 scenes: gems-ctm-diamond/emerald/lit A r12 C, B facet,
  C flat; metals-ctm), crops C:\qfb\shaderdev013\crops\, TEXTURES-READY. Track, journal updated; committed.
- CONFLICT for shader-dev / publisher: r013-shader.md 12:19 sets QF_GEM_FACET 2 (gemFacetNormal from block-local
  position). On connected gems that redraws a per-block pattern in the reflection. Connected gems need the normal
  from the _n (QF_GEM_FACET 0); the CTM tiles already carry rim bevel + streak facets.

## Next (only if needed)
1. After 1029-122300-r013-gems-ctm-c lands: `py -3.10 -I -X utf8 C:\qfb\shaderdev013	extures_make_scenes.py`
   (metals scene switches to g13facet3 by itself); look at diag_column iron crop 1150,700,340,320 for any line left.
2. Owner picks facet/flat -> make --gems-ctm the builder default.
