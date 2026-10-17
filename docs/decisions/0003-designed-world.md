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

The research behind this decision is summarised in the session reports: biomes, ambience
and quests, all from 2026-10-17.
