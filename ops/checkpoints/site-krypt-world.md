# site-krypt-world (checkpoint)

Owns: site/graves/* except scares.js, scares/, tex/scare/ and the marked block in app.js.

## Done
- window.__krypt stub + empty scares markers committed in app.js (fields filled in as the rewrite lands).
- Design settled (not yet built): legs with 90-degree bends in krypt.js (cell mapping by heading N/W/E), 9 segments
  (crypt, mineshaft, ossuary, flooded hall, dungeon spawner, library, chasm bridge, stair descent, nether depths),
  baked vertex light + AO, 4 live point lights, wall torches from torch_on.png on real faces, drop sun/shadows/halos/bokeh.

## Next
1. krypt.js rewrite (layout legs, grid, bake, torches, dressing); 2. app.js (anchors in 3D, passing focus, lights by depth,
audio gate + ambience, speaker toggle, __krypt fill); 3. textures to site/graves/tex (bookshelf, nether_brick, soul_sand,
mob_spawner, fire_layer_0, planks, log, skeleton) ; 4. verify with dump_frames (--list, --sheet) ; 5. journal line.
