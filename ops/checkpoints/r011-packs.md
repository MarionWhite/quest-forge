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
### 2026-10-27 step 1: survey (texture-dev #2)
- Faithless licence (its credits.txt): modpack use allowed with credit + link to modrinth.com/resourcepack/faithless.
- Faithless: 16x, 1.20 names. Potions = CIT model per effect (layer0 item/potions/<effect>[_strong] full colour + layer1
  cap_normal|cap_splash|cap_*_long) -> 1.7.10 CIT on damage bits (reuse qf_items' EFFECTS map, same file paths so ours
  override). Books = CIT enchantmentIDs=<name> -> 1.7.10 numeric ids. Worn-tool sprites (<tool>_1.._5 by damage
  predicate) -> CIT damage=%. Stackables (stackSize) -> CIT. Animated items (buckets, discs, redstone, slime, xp bottle,
  glowstone dust...) carry .mcmeta -> work on 1.7.10. Bow: bow/bow + bow1..11 by pull -> bow_standby/pulling_0-2.
  Compass/clock are 3D models with separate hands: need compositing into 1.7.10 frame strips.
- GUI: 1.20.2+ split widgets/icons into gui/sprites/*; 1.7.10 needs icons.png/widgets.png/tabs.png re-composited at
  the old UVs. Slot layouts changed since 1.7.10 in inventory (crafting grid moved, offhand), brewing stand (fuel slot,
  bottle y), enchanting table (lapis slot): remap or skip each. FrameBench has NO GUI capture: in-game GUI shots need
  a FrameBench change (qf-content jar; other sessions' WIP in AutoShot/QFNetwork -> build from a clean worktree).
- Patrix: every mob has CEM. Aspect-compatible skins: creeper, zombie, spider, enderman, sheep, ghast, wolf, slime,
  snowman, iron golem, pig(?), witch, cats, squid. Clearly CEM-only layouts: cow, skeleton, horses, bat, blaze, chicken.
  No villager/zombie_villager/dragon/player in the "basic" zip. Judge in game (mob lineup), keep only those that map.
- Plan: overlay pack built by tools/textures/r007packs.py -> C:\qfb\textures\QF-r011-packs.zip (layered over the
  QFTextures build; no edits to build_qf_textures.py). World C:\qfb\textures\world-r011 (copy of world-showcase +
  mob hall, TNT/bookshelf wall, item board) by tools/textures/build_r011_world.py; own views file.
### 2026-10-27 step 2: builder + FrameBench GUI views (texture-dev #2)
- tools/textures/r007packs.py (new, uncommitted yet): overlay zip, parts items,cit,tnt,books,mobs,env (gui next).
  Built C:\qfb\textures\QF-r011-packs.zip. Items: 204 Faithless sprites + compass strip (32 frames from its 50
  angle models) + bow pull frames with its 3D arrow rasterised in; clock kept (Faithless clock = 3D dial, no frames).
  CIT: potions per effect x normal/strong/long x drink/splash (damageMask 0x406F), 24 books, worn tools (damage %),
  arrow/seed stacks. Verified in Angelica's CIT class: damage % and stackSize are parsed.
- Conquest: live mcpatcherforge.cfg has custom_colors and better_skies OFF, and our shader discards vanilla sky and
  never reads fogColor/skyColor/lightmap -> its sky layers, fog/sky colormaps and lightmaps cannot show as files;
  shader work (note for r011-shader.md). Shipping: particles.png, footprint, rain, snow, ambient cave/rain sounds.
- FrameBench forces PEACEFUL (hostile mobs removed) and has no GUI capture. Added (opt-in, nothing else changes):
  views named gui_<kind> open a filled screen (GuiShots.java), gui_hud = survival HUD + Ender Dragon boss bar,
  -Dqf.bench.difficulty=easy. Built from a clean worktree C:\qfb\wt-r011-fb (HEAD 369939c + my two files) ->
  C:\qfb\renderq\jars-r011\QuestForgeContent-1.0.0.jar; use it per job via "jars" (replaces the runner's FrameBench
  jar for my jobs only; the shared jar is untouched). Source edits in the main tree are mine to commit.
- Next: tools/textures/build_r011_world.py (world-r011: mob hall, library+TNT, item board), views file, spec, submit.
### 2026-10-27 step 3: scenes submitted (texture-dev #2)
- World C:\qfb\textures\world-r011 (tools/textures/build_r011_world.py; copy of world-showcase): item board 12x5 at
  x 224-237 z 216, library 9x3 + TNT at x 240-256 z 216, mob hall x 223-269 z 222-232 (21 mobs, speed/followRange 0,
  light flood-filled by the builder: block 12-13 at the mobs). Views tools/textures/views-r011.txt (incl. gui_* views).
- Spec tools/renderq/specs/textures-r011-packs.json -> render 1027-222844-textures-r011-packs (58 renders):
  r11p0 = QF-v3c (r010 candidate), r11p1 = QF-v3c + QF-r011-packs.zip. Shot mode, CIT on, jars-r011, difficulty easy.
- Next: GUI part as a SEPARATE overlay (QF-r011-gui.zip, tools/textures/r007gui.py) so the items/mobs cache stays;
  then review r11p0/r11p1 sheets, drop Patrix skins that break (MOB_SKIP), hand off to C:\qfb\shaderdev\r011\.
### 2026-10-27 step 4: GUI overlay + shader note (texture-dev #2)
- tools/textures/r007gui.py (part gui of r007packs.py) -> C:\qfb\textures\QF-r011-gui.zip: Faithless containers
  (its pre-1.20.2 atlas layout; inventory grid/result moved (-10,+8), offhand painted out), legacy tabs.png +
  creative backgrounds, icons.png/widgets.png composited from its 1.20 sprites at 1.7.10 UVs (pink boss bar;
  per-boss framed bars bar_dragon/bar_wither need a GuiIngame hook), empty armour slot icons moved here.
- Render 1027-223357-textures-r011-gui (r11p2: v3c + packs + gui, 12 gui_* views). Packs render 1027-222844 running.
- Conquest note appended to ops/checkpoints/r011-shader.md (uncommitted there: that file holds the shader agent's WIP;
  they commit it).
- Next: review r11p0/r11p1/r11p2 frames (contact sheets), MOB_SKIP for broken Patrix skins, hand-off JSON
  C:\qfb\shaderdev\r011\packs_scenes.json, journal + track update, commit.
### 2026-10-27 step 5: first review (texture-dev #2)
- Render 1027-222844 done (r11p0 A / r11p1 B, frames in C:\qfb\shaderdev\rounds\screenshots\bench-r11p*-*.png).
- Found: compass = missing texture (1.7.10 needs compass.png.mcmeta {"animation":{}}: fixed); Faithless TNT's
  Galactic letters are tnt_side2, picked 1 in 5 by its blockstate (now CTM random weights 4 1, symmetry=all);
  item board reads right-to-left from the camera (cosmetic, left as is).
- Patrix in game: good = creeper, zombie, skeleton, wither skeleton, spider, cave spider, enderman, wolf, ocelot,
  pig, iron golem, snowman, silverfish. Broken (CEM layout) = chicken, cow, sheep (+wool), blaze, witch, zombie
  pigman. Unseen, held back = slime, magma cube, ghast, squid, bat, wither. -> MOB_SKIP in r007packs.py.
- Conquest particles: its smoke (blaze) is heavy black swirls vs vanilla specks: flag for the owner.
- MISTAKE: rebuilt QF-r011-packs.zip by hand while the r11p2 GUI boot was running (its prebuild had built it).
  Only mob skins differed (not in GUI frames). Rule: hand builds go to scratch; renderq prebuilds own the real zips.
- Submitted 1027-...-textures-r011-packs-b (r11p3: corrected B for items, items_tl, tnt, mob_1..6).
- Wide mob views r11_mobs_a/b/c are far (FrameBench FOV wide): hand off the close r11_mob_N views instead.
- Next: wait GUI (1027-223357) + cost (1027-223454) + packs-b; review GUI frames; run tools/textures/r011_packs_handoff.py
  (switch B to r11p3 for the re-rendered scenes); journal, track, commit.
### 2026-10-27 step 6: GUI reviewed, hand-off written (texture-dev #2)
- GUI render 1027-223357 (r11p2): every screen works in game (inventory grid aligned, creative tabs, furnace lit,
  crafting, chest, brewing, enchanting, anvil, HUD with the dragon bar). Cosmetic: titles are dark text on its wooden
  plaques; 1.7.10's floating enchanting book overlaps its drawn table; hotbar compass magenta (pre-fix build).
- Hand-off written: C:\qfb\shaderdev\r011\packs_scenes.json (21 scenes, crops in r011\packs\), by
  `py -3.10 -I tools/textures/r011_packs_handoff.py` (prefers r11p3 frames where they exist; cost from r11c0/r11c1).
- PENDING renders (queued behind other agents, ETA ~23:40): 1027-224607-textures-r011-packs-b (r11p3),
  1027-224805-textures-r011-gui (r11p2 again, fixed compass), 1027-223454-textures-r011-cost (r11c0/r11c1).
  When all three are done: review r11p3 mob/TNT/items frames and r11c0 vs r11c1 p50; rerun the hand-off script;
  touch C:\qfb\shaderdev\r011\PACKS-READY; one journal line; commit.
- Rule: never rebuild C:\qfb\textures\QF-r011-*.zip by hand while a render runs (prebuilds own them); test builds to scratch.
- Worktree C:\qfb\wt-r011-fb (detached, for rebuilding the jars-r011 FrameBench jar); remove with
  `git worktree remove C:/qfb/wt-r011-fb` once FrameBench's gui_* views reach the shared runner jar.
- Not copyable / open: Patrix CEM shapes (Java renderer per mob); Faithless per-boss framed bars (GuiIngame hook);
  Faithless clock (3D dial); Faithless villager/horse GUIs (modern layouts); custom enchantments' books (81 modded
  ids, no Faithless art); Conquest sky/fog/lightmaps (shader). Owner question: Soartex here is R.1.6 for 1.21.
### 2026-10-28 step 7: DONE, handed off (texture-dev #2)
- All three renders landed (10-27 22:56, 10-28 08:19). r11p3: compass dial, TNT lettering mix, skipped mobs vanilla.
  Patrix iron golem is a CEM layout (square, so the aspect test passed it; face lands on the chest) -> MOB_SKIP
  (zip not rebuilt by hand; the next prebuild drops it). Slime/magma cube vanish from the hall (A too): unjudged.
  GUI r11p2: compass fixed; plaque titles and the enchanting book overlap remain (fix unless the owner objects).
- Cost r11c0/r11c1 frame p50 ms: items 3.26/3.25, mobs_b 2.56/2.54, library 3.14/3.15 -> none measurable.
- Hand-off rerun with the owner's questions and causes (pk-shelves, pk-mob-4, pk-hud, GUI scenes); PACKS-READY touched.
- Next, after the owner's answers: lighten plaques + paint out the enchanting book in r007gui.py; per-boss bar hook if
  yes; vanilla smoke if no; remove worktree C:/qfb/wt-r011-fb once gui_* views reach the shared runner jar.
### 2026-10-28 step 8: pre-publish fixes (texture-dev #2)
- Critic (C:\qfb\shaderdev\r011\critic.json): pk-items-close / pk-library used stale r11p1 frames (missing texture);
  pk-enchanting "lost its option rows". Cause of the latter: Faithless's enchantment_slot_disabled is fully transparent
  (by design: its rows are red ribbons that only slide out when an item is in), and 1.7.10 draws the disabled row for
  an empty table. Fix in GuiShots.java (main + worktree): a diamond sword in the table, levels 4/17/30 set by hand.
  Jar rebuilt in C:\qfb\wt-r011-fb with -PqfDebugTools=true (without it debug/** is excluded!) -> jars-r011
  (old jar in scratch). Spec tools/renderq/specs/textures-r011-packs-c.json.
- SUBMITTED 1028-091920-textures-r011-packs-c (r11p3: r11_items_bl, r11_library; r11p2: gui_enchanting).
- Next: wait; check crops for magenta; rerun r011_packs_handoff.py; stay-true gems/roofed drop (r011-stay-true.md); commit, push.
