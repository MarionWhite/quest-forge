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

## Next
1. tools/textures/gems_ctm.py: 47 tiles + _n per gem/metal from Faithful 64x (frame from the block, interior made
   periodic by re-placing Faithful's own marks on a torus). Builder flag --gems-ctm.
2. Build C:\qfb\textures\r013\QF-gems-ctm.zip; render vs r012 C on gem_glint_d/e + gem_lit (spec C:\qfb\gems\specs).
