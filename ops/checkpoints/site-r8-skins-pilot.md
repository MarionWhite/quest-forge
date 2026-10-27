# site-r8-skins-pilot (checkpoint, started 2026-10-27, Mac)

Agent: texture-dev (opus). Owns: `site/graves/tex/mobs/*` (new), the skin-override hook it needs in
`site/lib/mc/mobs.js` (additive), its own tools under `tools/textures/mobs/`. Research: `site-r8-skins.md`.

## Owner's words (2026-10-27, round 8)
- "use the mob skins from the Patrix 32x texture packs for the animations to make the mobs scarier unless there is
  an even more terrifying texture pack for them. Leave the actual environmental blocks the same vanilla texture,
  but lets make these mobs scary as fuck."

## Why a pilot of our own
Patrix is All Rights Reserved, and its scary mobs rely on FreshLX's Fresh Animations models (a second rights holder,
and not 1.7.10 models). The openly licensed packs found are amateur and cover 3 mobs. So: paint our own 32x horror
skins on the 1.7.10 vanilla UV layouts. Study Patrix and other horror packs for ideas (palette, rot, eyes, how
detail reads at 32x); never copy, trace or recolour them. Faithful 32x as a base is fine if its licence allows a
modified version to ship with credit: check and quote it first.

## Done means (pilot: Zombie and Spider only)
- [ ] Both skins at 32x (2x the vanilla sheet), true to the mob's silhouette and colours so it still reads as that
  Minecraft mob, and frightening: rot, wounds, sunken or glowing eyes, wet dark tones. The spider's eyes layer too.
- [ ] A Krypt-only override: scares and mood mobs on the Krypt page use `site/graves/tex/mobs/<key>.png` when it
  exists; the Lucky Block page keeps vanilla. No change to how the scares play.
- [ ] Review renders: vanilla beside new, under the Krypt's torch light, at the scare's real distance (face-close)
  and at 6 blocks, front and three-quarter; one sheet. Use the ?dump=1 hook; one Chrome at a time.
- [ ] If code cannot reach the quality, say so plainly and propose the path (as your agent file says).
- [ ] Commit your own paths, journal line in `ops/journal/site.md`, report in five lines with the sheet path.

## Progress
(write after every step)
