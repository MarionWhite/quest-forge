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
- HANDED OFF: C:\qfb\shaderdev
013	extures_scenes.json (4 scenes: gems-ctm-diamond/emerald/lit A r12 C, B facet,
  C flat; metals-ctm), crops C:\qfb\shaderdev
013\crops\, TEXTURES-READY. Track, journal updated; committed.
- CONFLICT for shader-dev / publisher: r013-shader.md 12:19 sets QF_GEM_FACET 2 (gemFacetNormal from block-local
  position). On connected gems that redraws a per-block pattern in the reflection. Connected gems need the normal
  from the _n (QF_GEM_FACET 0); the CTM tiles already carry rim bevel + streak facets.

### session 2 (iron seam, 4th try)
- Cause from the pixels: NOT the albedo or _n (both continuous). The _s: the ctm maps index the block's _s too, whose
  frame is 4 px (VNR 16x upscaled) vs the albedo's 2/3; the squeezed mirror put _s col 3 (smoothness 131 vs ~215) at
  tile x=63 and x=0 -> a 2-texel rough column at every seam (render luma 164 vs 170 at x 1279-1284). Ticks = the
  squeeze halving the _s's 4-px steps; the grey shapes = iron _s pixels >= 225 tripping the shader's gem path
  (lighting.glsl: smoothness > 0.88 && f0 > 0.1). NOT a reflection of the ore wall (the old scene note was wrong).
- Fix (gems_ctm.py): x_mirror = 1:1 mirror of the central half (cols 16..47, asserted inside SPEC_FRAME 4);
  spec_tiles() caps NOT_GEM (iron) ctm _s at 224. Builder uses spec_tiles. Rebuilt facet + flat packs: only iron
  entries changed (93), seam |L63-R0| = 0 in albedo and _s, no _s >= 225.
- 13:03 guard OK, SUBMITTED `1029-130343-r013-gems-ctm-d` (tag g13facet4, diag_column only; spec
  C:\qfb\gems\specs013-gems-ctm-d.json). Queue: shader-dev's 1029-130228-r013-loop2 (46 scenes) ahead, ETA
  ~13:16+ owner-idle gated: over 10 min, not waited for.
- textures_make_scenes.py now prefers g13facet4 when its frame exists and fixes the iron sentence (IRON_NOTE). NOT rerun
  yet (would hand off g13facet3 with the line).

## Next (only if needed)
0. After 1029-130343-r013-gems-ctm-d lands: crop bench-g13facet4-diag_column.png at 1150,700,340,320; expect no seam
   line (x ~1280), no ticks, no grey shapes on iron. If clean: `py -3.10 -I -X utf8 C:\qfb\shaderdev013	extures_make_scenes.py`.
1. After 1029-122300-r013-gems-ctm-c lands: `py -3.10 -I -X utf8 C:\qfb\shaderdev
013	extures_make_scenes.py`
   (metals scene switches to g13facet3 by itself); look at diag_column iron crop 1150,700,340,320 for any line left.
2. Owner picks facet/flat -> make --gems-ctm the builder default.

### 2026-10-29 16:10 (orchestrator): iron 4th try clean
- 1029-130343-r013-gems-ctm-d (g13facet4) reviewed at crop 1150,700,340,320: no seam, no ticks, no dark patches.
  textures_make_scenes.py re-run: textures_scenes.json (4 scenes) now uses g13facet4. Gems hand-off complete.
- Still for the owner (in the Lab): connected facet vs flat; then make --gems-ctm the builder default.
