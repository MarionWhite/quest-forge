# 0003 — A hand-designed continent with procedural seas beyond

**Date:** 2026-10-17
**Status:** accepted; proof of concept pending

## Decision

The overworld is a large **hand-designed continent**, painted in WorldPainter and
**pregenerated** on the server. The **sea** surrounds it on every side. Past the sea, RWG with
Biomes O' Plenty generates the **outskirts** as players explore.

- The author places the major biome regions, mountain ranges, rivers and landmark structures.
  The game fills in detail when it populates the painted chunks: trees, ores, modded dungeons
  and spawns.
- Every BoP and RWG biome is in, apart from one: the free biome IDs come up one short (108
  free, 109 needed).
- An **Ark-style spawn picker** shows a map with spawn points and an approximate difficulty
  for each. It is qf-content code, and it still has to be built.
- Danger is designed by region. The JustAnotherSpawner tables are rebuilt around the painted
  biomes and spawn points.

- The **outskirts beyond the sea are the hardest content in the game**, Valheim style. The
  author decided this on 2026-10-17; the mechanism is not chosen yet.
- The overworld continent is **sized after the author has tried WorldPainter**. The layout
  keeps a striking focal point at the centre and a natural climate: cold and mountains to
  the north, desert and tropics to the south. The pie-slice ring layout of draft v0 is
  rejected.

**Update 2026-10-25: no hand painting.** The author will not use WorldPainter. The continent
is built entirely by the pipeline from the plan spec; the size settled at 49,152 blocks
(docs/design/world/r13). The author judges renders, and agents make the changes in iterations.
WorldPainter remains only an automated build step. Anything once meant as a hand touch-up is
either automated or dropped: tree placement, river-bank softening, waterfall review.

**Difficulty (2026-10-25):** a tier layer (docs/design/world/r14) enforced by a hybrid. Biome
spawn tables decide which mobs appear, and a position hook scales them by tier
(r14/difficulty-enforcement-proposal.md, with the author's decisions recorded there).

## Why

The author wanted RLCraft's biome quality and danger gradient, along with a hand in building
the world. A painted core gives fixed landmarks and a planned difficulty layout, and the
outskirts keep the sandbox open-ended. The sea hides the seam between the painted terrain and
RWG's, and it turns the trip to the frontier into a journey.

Rejected alternative (B): a biome-map image read by a custom `GenLayer` on BoP terrain. It
gives seamless terrain but less control over terrain shape. It stays the fallback if
population of painted chunks proves unworkable.

## Open questions for the proof of concept

1. Does every mod still decorate painted chunks when the game populates them under
   `level-type=rwg`? This covers BoP trees, modded ores, Roguelike, Doomlike, Recurrent
   Complex, ChocolateQuest and Lycanites spawns.
2. Can the biome IDs be pinned with none of them colliding? RWG's defaults (200–224)
   collide with 1Legends (200–203).
3. Does WorldPainter export a 1.7.10 world that uses modded biome IDs?
4. How long does pregeneration take, and how large is the world on disk, per million chunks?
5. Do the client requirements of the GTNH RWG fork keep OptiFine E7 clients able to join?

The research behind it, from 2026-10-17: [biomes](../design/world/research/biomes.md),
[ambience](../design/world/research/ambience.md) and [quests](../design/world/research/quests.md).
