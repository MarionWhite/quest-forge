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
