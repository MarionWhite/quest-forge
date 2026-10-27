# r010 textures checkpoint (orchestrator, 2026-10-27)

Input: docs/design/shaders/feedback/r009.json (owner, 2026-10-27) and its two Stay True screenshots in
docs/design/shaders/feedback/attachments/r009/ (look at both before starting). Leaf frills are a separate track
(ops/checkpoints/r010-leaf-frills.md); this track only supplies the leaf *texture* they sit on.

## What the owner said, and the change of method it forces
- Overall: "we are kind of stalling on improvements ... you aren't asking the right questions ... I would like to be
  moving a lot faster, and getting results that surprise me." Small tweaks to a code-drawn generator are over.
- Leaves: v1 and v2 "look like shit, and honestly v2 is worse"; "completely pivot instead of making small micro
  changes"; "restart from fresh and actually work towards the reference you were given" (Stay True, direction.md l.291).
  He picked Faithful 64x (C) in all three leaf scenes.
- Farm: "doesn't have the same luscious look as the reference mod. Look at these fields." Close up, r008's crop looked
  fuller than r009's; from far, r009 looked better.
- Wall: "I don't know why the diamond blocks are only getting light on the bottom half, and why the iron and gold look
  so much darker ... you are asking the wrong questions and leaving a bunch of shit general and vague."
- Emerald: much better; aim for the diamond's direction rather than the geometric look.
- Items: decent; the green potion is boring; book logos are not all centred.

## Rules for this round
- **No more procedural leaf or wheat art.** Start from licensed art (Faithful 64x, Faithful licence v4) and, where
  Stay True is the target, reproduce its *technique* (density, variants, saturation, value structure), never its
  pixels (all-rights-reserved: study only).
- **Every weak scene shows 2-3 genuinely different directions** (not v1 vs v2 of one idea), plus the reference.
- **Explain before asking.** Every Lab question names the cause and the trade-off, with numbers.

## Order of work
1. **Wall lighting diagnosis (first; no art until the cause is known).** Build a diagnostic scene: one diamond, iron,
   gold and emerald block each, on a plain floor, sun from one known side, faces labelled. Render a ladder, one variable
   off per frame: shaders off / shader on with no PBR / normals only / specular only / both. Hypotheses to test, in
   order: (a) the normal maps use the other Y convention (DirectX vs OpenGL), so light seems to come from below: check
   by flipping the green channel; (b) the specular maps are read in the wrong format (labPBR vs oldPBR): in labPBR a
   green value of 230-237 means a hard-coded metal, which darkens the albedo; (c) emission or AO channels misread.
   Write the cause into docs/design/textures/ with crops and numbers, fix it, and re-render the wall scenes. The Lab
   question must state the cause in one sentence.
2. **Wheat and crops, Stay True's technique.** From the screenshots: tall, bushy, saturated gold sprites filling the
   block, and five random variants per block (method=random) so a field never tiles. Verify first that random CTM
   works under Angelica (one test block); if not, find the 1.7.10 route that does. Render a field near and far, against
   r008's crop (fuller up close) and r009's (better far away).
3. **Leaf texture for the frills.** Faithful 64x leaves as the base, with denser and darker clusters (faithless-study
   item 13). Coordinate with r010-leaf-frills.md: the frill quads need a matching leaf-edge texture.
4. **Emerald toward diamond's direction; a green potion with personality; centre the book logos** (check every logo
   by its bounding box, not by eye).
5. Render through renderq; write texture_scenes.json in C:\qfb\shaderdev\r010 and TEXTURES-READY; `trial.py guard`.

## Progress log
- 2026-10-27 (texture-dev): step 1a, offline diagnosis (no code changed, no renders yet).
  - Stay True screenshots read: 5 wheat variants of differing height, each a dense gold mass, dark base to bright tips,
    filling the block width; fields never tile. Leaves: dense dark clusters, bright crowns.
  - r009 frames, front face of each block (texture_wall, px x1582-1680; diamond y636-688, iron 692-742, gold 746-792),
    luminance top half / bottom half: v2h diamond 115.6 / 155.4, gold 120.7 / 127.4, iron 149.3 / 145.3;
    Faithful 64x diamond 145.1 / 139.3, gold 126.1 / 123.8, iron 152.7 / 139.5. (scratchpad halves.py; recreate from this.)
  - **Cause found (hypothesis a, with a twist):** VNR's source maps are ALREADY DirectX (Y-): (G-128) vs dh/dv from the
    height (alpha) correlates -0.38..-0.97 (stonebrick, cobble, brick, planks); R vs dh/du is negative too, which fixes
    alpha = height. `tools/textures/vnr.py` `to_labpbr_n` (and `hybrid_normal`) flip G again (255-G), so every
    VNR-derived _n ships OpenGL-style into a DirectX shader (gbuffers.glsl l.186 assumes +G = down the texture).
    Pack: brick +0.90, planks +0.97, stonebrick +0.34, iron +0.55, gold +0.29, diamond +0.22 (wrong sign);
    our own maps (emerald -0.72, stone -0.79, log -0.89, leaves -0.82, bookshelf -0.85) are right. Mixed pack.
  - Diamond: VNR's _n is a strong dome (G by quarter rows 78/112/140/176 = ~22 deg tilt at the edges). Flipped, the top
    faces DOWN (reflects dark ground) and the bottom faces UP (reflects sky): the owner's "light only on the bottom half".
    Gold: same inverted dome at about half strength. Iron: small dome (121..134).
  - Specular (hypothesis b): diamond _s G = 230 everywhere (VNR's metal flag -> LabPBR "iron" code), R 212-229;
    iron G 190 (dielectric F0 .75), gold 60% F0 60 / 40% 231; B 0, A 255 (no emission). Shader metal cut is sp.g > .895
    (G >= 229; LabPBR says 230+, off by one, harmless here). Diamond as a metal is physically wrong (F0 ~44 for n=2.42).
  - Next: render ladder (one variable each) to confirm in-game, then fix vnr.py G flip + decide diamond F0.
- 2026-10-27 (texture-dev): step 1b, fix coded + ladder submitted (commit dcf0fd3).
  - `vnr.py`: `to_labpbr_n` keeps VNR's G; `hybrid_normal` turns VNR to OpenGL before adding our relief (it had mixed
    the two). `labpbr.y_sign(n, alpha)` + build warning on any OpenGL-style _n (opaque interiors only; thin cut-outs
    skipped). v2 zip: 34 maps OpenGL-style; fixed build: 0. `--diamond gem` = diamond_block F0 44 (dielectric, n 2.42).
  - Variants in C:\qfb\textures\diag\: QF-v3y.zip (fix; differs from QFTextures-v2.zip only in 174 _n),
    QF-v3yg.zip (+gem; differs only in diamond_block_s), QF-v2-nrm.zip / QF-v2-spc.zip (v2 minus _s / minus _n,
    made by a scratch script: copy every entry by NAME, never reuse ZipInfo objects).
  - Views added (views-world-master.txt): diag_column (259.0 69.4 181.5, yaw 180, pitch 0, 7000), diag_emerald (241.0 70.6 181.5).
  - Spec tools/renderq/specs/textures-r010-wall-ladder.json; submission **1027-164027-textures-r010-wall-ladder**
    (tags t10d0off .. t10d7f64). Snapshot includes another session's uncommitted settings.glsl/sky.glsl edits:
    compare rungs with each other (and d4v2), not with r009's t9 frames.
  - Next: review = per-block top/bottom luminance (diag_column, measure boxes from the frame) + contact sheet; then decide
    diamond metal vs gem, rebuild QFTextures-v3, re-render wall scenes.
- 2026-10-27 (texture-dev): step 2a, wheat offline (commit after dcf0fd3, "--wheat dense|bushy"), while the ladder waits on the owner gate.
  - `tools/textures/wheat_dense.py`: Faithful 64x stage 7 layered (3 mirrored/shifted back copies, shorter and darker, Faithful's
    plant in front), gradient-mapped to a 6-step gold ramp by height + own luminance (dark ochre base, pale straw tips), five
    heights 0.62-1.0. `bushy` also stamps Faithful's ear pixels (top 20% luminance) across the top band = Stay True's bushy heads.
    Preview: `py -3.10 tools/textures/wheat_dense.py <F64 zip> out.png [plain|bushy]`. Reviewed: both read as dense gold masses,
    bushy closest to the reference; plain still shows Faithful's broad blades (a little corn-like).
  - Builder `--wheat drawn|dense|bushy` (default drawn = v2): stages 0-6 = Faithful 64x, ripe = variant 2, ctm/wheat/ random 0-4.
  - Built C:\qfb\textures\diag\QF-w-bushy.zip and QF-w-dense.zip (both with --diamond gem).
  - Next for step 2: render farm, farm_close (random-CTM-on-crops check: do 5 heights show?) for bushy | dense | t9f64/t9v2h.
  - Submitted **1027-164404-textures-r010-wheat** (t10wb bushy, t10wd dense, t10wf Faithful; farm, farm_close).
- 2026-10-27 (texture-dev): step 1c, ladder 1027-164027 DONE and reviewed. **Cause confirmed in-game.**
  - diag_column, mean luminance top/bottom half of each block's front face (x 1134-1426; diamond y 574-718, iron 736-866,
    gold 890-1022; scratchpad ladder_nums.py):
    | rung | diamond top/bot (ratio) | iron mean | gold mean |
    | d0 off | 151.5/147.8 (1.02) | 158.7 | 148.8 |   | d1 no PBR | 144.8/140.8 (1.03) | 133.0 | 122.4 |
    | d2 normals only | 124.0/150.9 (0.82) | 142.1 | 128.8 | | d3 spec only | 157.4/160.2 (0.98) | 150.9 | 127.3 |
    | d4 v2 (r009) | 127.1/167.2 (0.76) | 150.3 | 125.9 | | d5 Y fix | 176.2/121.8 (1.45) | 153.7 | 128.0 |
    | d6 Y fix + gem | 164.8/135.7 (1.21), mean 150.2 | 153.7 | 128.0 | | d7 Faithful | 153.5/147.2 (1.04), mean 150.3 | 143.1 | 129.8 |
  - Reading: the split needs BOTH maps: diamond is coded metal (a mirror) AND has a 22-deg dome normal that was upside down.
    Fixing Y alone reverses the split (1.45: the dome's top mirrors sky, bottom mirrors ground). Y fix + gem (dielectric F0 44)
    = whole face lit, gem gloss, Faithful's mean brightness; the remaining 1.21 is "lit from above" by the bevel.
  - Iron/gold vs plain stone in the same frame (median stone lum): iron 1.82x stone in v2/gem = vanilla's 1.82x (fixed).
    Gold 1.52x in EVERY shader rung (incl. Faithful no-maps and QF_PBR 0) vs vanilla 1.71x: under the shader gold's blue is
    clipped to 0 in 81-98% of pixels (vanilla B 34) and red peaks 154-161 (vanilla 179) -> shader colour grading crushes
    saturated yellow. **Shader-side; hand to r010-shader** (not fixable in maps).
  - New: with Y fixed, gold's metal pixels on its top bevel made a thin noisy bright line (d5/d6). Fix (committed): metal only
    where normal tilt < 14.5 deg (gold metal 40% -> 33%, top rows 14%). Build: C:\qfb\textures\diag\QF-v3yg2.zip (not rendered yet).
  - Decision taken: ship Y fix + `--diamond gem` (make gem the default when building v3).
- 2026-10-27 (texture-dev): step 3a, leaves offline + submitted.
  - `tools/textures/leaves_dense.py`: dense() = 2 mirrored/shifted darker copies (x0.58/0.50) of Faithful's leaves behind it;
    crowns() = dense + 2x2-cell tileable light field (lit crowns, dark undersides); frill() = whole leaf units (>=12 px) inside a
    wavy bottom-heavy blob. Builder `--leaves drawn|faithful|dense|crowns` (default drawn = v2) also writes
    leaves_<kind>_frill.png (new: builder now writes art sprites vanilla lacks). Note for the frills agent appended to
    ops/checkpoints/r010-leaf-frills.md (unstaged: that file holds their WIP).
  - Gold hand-off note appended to ops/checkpoints/r010-shader.md (unstaged, their WIP file).
  - Submitted **textures-r010-leaves-wall** (t10la faithful / t10lb dense / t10lc crowns on leaves_close, tree_close,
    forest_lit; t10lb also texture_wall, texture_wall2, diag_column = step 1 re-render). Wheat 1027-164404 still queued.
- 2026-10-27 (texture-dev): step 4 done offline (commits 05ee96d, e39054d).
  - Books: emblems were placed by a fixed 7x7 grid origin; flame/thread were 6 wide and anvil 6 tall (bbox 0.5 px off centre).
    Redrawn to 7x7; `qf_items.emblem_origin()` places each by its drawn bbox on cover pixel (8, 7) and raises on an even-sized
    bbox. All 8 emblems verified exactly centred.
  - Green potion = splash poison on the board; every splash shared ONE plain grenade sprite. `qf_items.SPLASH`: a motif per
    effect on the grenade (poison: skull, toxic bubbles from the fuse, drips); CIT splash rules point at bottle_/liquid_<name>_splash.
    Sheet: `py -3.10 tools/textures/qf_items.py out.png` (drinkables, then every splash, then books).
  - Emerald: `tools/textures/gems.py` maps Faithful 64x diamond_block's 9 tones by rank onto a 7-step emerald ramp (Faithful's
    6 emerald colours + one deeper). Builder `--emerald faithful|diamond` (default diamond). Own maps still (VNR_SKIP).
  - Builder defaults now: --diamond gem, --emerald diamond; --wheat and --leaves still default drawn (pick after renders).
    Candidate v3 build: `--wheat bushy --leaves dense` -> C:\qfb\textures\diag\QF-v3c.zip.
  - Queue at 17:00: wheat 1027-164404 (t10wb/wd/wf) and leaves-wall 1027-165735 (t10la/lb/lc; t10lb walls) waiting behind
    shader-r010 and leaf-frills jobs, ETA ~17:16.
  - NEXT (resume here): review wheat (farm, farm_close: do 5 heights show = random CTM works on crops?; sheet t10wb|t10wd|t10wf
    + Stay True screenshot) and leaves (leaves_close/tree_close/forest_lit t10la|lb|lc) and walls (t10lb vs t10d4v2:
    texture_wall, texture_wall2 incl. new emerald, diag_column). Items need one render (items_frames, cit true) for splash+books.
    Then step 5: C:\qfb\shaderdev\r010\texture_scenes.json (+ texture_make_scenes.py, crops\) like r009's, each scene 2-3
    directions + Stay True reference; questions state the cause with numbers (wall: "VNR normals flipped + diamond coded metal";
    gold darkness is shader-side, handed to r010-shader); TEXTURES-READY; `trial.py guard`; track file + journal entry.
- 2026-10-27 (texture-dev): wheat render 1027-164404 reviewed; session ends (leaves-wall render ~15 min out).
  - farm (sheet t10wb | t10wd | t10wf, box 0.15,0.25,0.85,0.75): bushy and dense = full saturated gold fields, far closer to
    Stay True than Faithful's olive airy rows; bushy slightly fuller heads. farm_close: bushy far fuller than Faithful.
  - **Random CTM does NOT reach crops**: native crop (t10wb farm_close px 1100,780,2000,1060) shows every block the same
    silhouette and height. Angelica 2.2.33's mcpatcherforge ctm MixinRenderBlocks targets renderCrossedSquares, panes, vines,
    lily pad, double plant, standard faces; not renderBlockCrops. Route: a qf-tweaks hook in renderBlockCrops choosing one of
    5 registered icons by position hash -> question in ops/DECISIONS.md (Textures). Until then the field shows variant 2.
  - Queued: **1027-165735-textures-r010-leaves-wall** (t10la/lb/lc leaves; t10lb texture_wall, texture_wall2 with the new
    emerald, diag_column) and **1027-171234-textures-r010-items** (t10i items_frames, cit, build QF-v3c).
  - Track file rewritten, journal entry added, DECISIONS entry added.
  - RESUME: `renderq.py results` for both; review leaves (pick a default for --leaves; wheat default -> bushy), walls
    (t10lb vs t10d4v2: diamond even, gold line gone, emerald), items (splash poison motif, books). Then step 5 hand-off as
    listed above (C:\qfb\shaderdev\r010\texture_scenes.json + TEXTURES-READY; scenes: wall (v2 | v3 | Faithful; question
    states the cause in one sentence with the ladder numbers), farm + farm_close (bushy | dense | Faithful + Stay True shot;
    say plainly the variants need the hook), leaves (faithful | dense | crowns + Stay True), items). `trial.py guard`.
- 2026-10-27 (texture-dev, session 2): reviewed 1027-165735 (leaves, walls) and 1027-171234 (items). Sheets in scratchpad (sheet.py).
  - Walls (t10lb vs t10d4v2 vs t10d7f64): diamond now evenly lit and glossy, matches Faithful; iron fine; emerald in diamond's
    direction reads as one family with diamond. Gold: a lime patch in the top third of each block = the metal mirrors the green
    field/horizon, tinted by gold's albedo (shader uses albedo as metal F0; blue clipped -> lime). Shader-side (hard-coded LabPBR
    231 F0 would fix it) -> add to the r010-shader hand-off note.
  - Items t10i (crop 660,760,1900,1120): splash poison skull motif reads; books look centred. Done.
  - Leaves: t10la Faithful = airy, ragged silhouette, big leaves. t10lb dense / t10lc crowns = solid opaque cubes: silhouette
    became hard squares (worse than Faithful), lb/lc barely differ, both lime in sun (forest_lit). Not 3 genuine directions.
  - NEXT: leaves_dense.py: `rim` (dense core, Faithful's own alpha kept in a ragged rim band) and `fine` (half-scale leaves,
    mirrored 2x2 = Stay True's grain); render t10lr/t10lf on leaves_close,tree_close,forest_lit; then texture_scenes.json.
  - Done: leaves_dense.py `rim` (dense core, Faithful holes in a patchy wavy edge band, lo=-8 hi=8) and `fine` (Faithful 32x
    leaves tiled 2x2 = half-size leaves, crowns light field, rim; mirrored quadrants were tried and printed kaleidoscopes).
    Builder `--leaves rim|fine`, `--faithful32`; CREDITS updated (Faithful 32x leaves, r010 Faithful uses, VNR G kept).
    Zips C:\qfb\textures\diag\QF-l-rim.zip, QF-l-fine.zip. Submitted **1027-185913-textures-r010-leaves2** (t10lr, t10lf;
    leaves_close, tree_close, forest_lit), queued behind leaf-frills 1027-185527.
  - NEXT: wait/review leaves2 (sheet t10la|t10lr|t10lf + crops of hedge and crown), pick --leaves default; write
    C:\qfb\shaderdev\r010\texture_make_scenes.py + texture_scenes.json + TEXTURES-READY; gold lime note to r010-shader.
