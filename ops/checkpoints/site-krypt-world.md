# site-krypt-world (checkpoint)

Owns: site/graves/* except scares.js, scares/, tex/scare/ and the marked block in app.js.

## Done
- window.__krypt stub + scares markers in app.js (committed).
- krypt.js rewritten: legs with bends (N/W/E), 9 segments, passages, PROFILE (lighting by depth), bake (lightAt, AO),
  slotFrame, pathCurve (arcs at bends), finishLayout (s for slots/corners), meshGrid with patchBake. Node-tested (/tmp/kt/t.mjs).
- dress.js (torches, decor, water, lava, fire, spawner) and fx.js (particles) written, syntax-checked, not yet run in a browser.
- textures copied into site/graves/tex (bookshelf, nether_brick, soul_sand, mob_spawner, fire_layer_0, minecart, bone, iron_block, lava_flow).

## Next
1. app.js: use new layout/anchors (3D), dress+fx, lights by profile, passing focus camera, remove sun/halos/bokeh/embers.
2. kaudio.js + gate in index.html, speaker toggle, fill window.__krypt.
3. verify with tools/site/dump_frames.py (--list, --sheet); fix once; node --check; journal line (ops/journal/site.md).
