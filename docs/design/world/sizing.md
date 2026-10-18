# How big the designed continent can be

Measured 2026-10-17 for [decision 0003](../../decisions/0003-designed-world.md).

## The speed the world has to hold up to

Cloudtrap is the fastest sustained mobility. In
`mods/transformers/.../TransformerCloudtrap.java` its jet mode calls `motionJet(player, 140, 200, 50)`.
`TFMotionManager.fromKMPH` gives these speeds:

- Cruise: 140 km/h, about **39 blocks/s**.
- Nitro: 200 km/h, about **56 blocks/s** (limited by the nitro supply).
- The other jets reach 100 / 140 km/h, about 28 / 39 blocks/s.

MCHeli's `Speed` values (F-22A 1.2, for example) were not converted to blocks/s.

At 56 blocks/s a player crosses about 3.5 chunks/s. With view distance 6, that is roughly 45
new chunks/s per player:

- On a pregenerated world this is disk reads only.
- In the RWG outskirts it is generation. The slim proof of concept generated about 133
  chunks/s, so two or three jets on nitro outrun generation. A pregenerated buffer ring
  around the sea avoids that.

## What limits the size

The limit is RAM in WorldPainter, not disk. The PC has 2.2 TB free.

Per WorldPainter tile (128 × 128 blocks), measured on 4k, 8k and 16k worlds with a full
16-bit heightmap and a biome layer:

- About **0.13 MB of heap**.
- About **23 KB of `.world` file**.

Both grow linearly. Painted layers (custom terrain, trees, undo history) add an unmeasured
amount on top; budget for 1.5–2× until measured.

| Edge (blocks) | Chunks | WP heap (bare) | `.world` (bare) | Game world (about 10 KB/chunk) | Pregen at about 80 chunks/s (full pack, estimated) | Cloudtrap edge to edge (nitro / cruise) | Sprint on foot |
|---|---|---|---|---|---|---|---|
| 16,384 | 1.0 M | 2.1 GB | 0.4 GB | about 10 GB | about 4 h | 5 / 7 min | 49 min |
| 24,576 | 2.4 M | 4.8 GB | 0.9 GB | about 24 GB | about 8 h | 7 / 11 min | 1.2 h |
| 32,768 | 4.2 M | 8.5 GB | 1.5 GB | about 42 GB | about 15 h | 10 / 14 min | 1.6 h |
| 49,152 | 9.4 M | 19 GB | 3.4 GB | about 94 GB | about 33 h | 15 / 21 min | 2.4 h |
| 65,536 | 16.8 M | 34 GB | 6 GB | about 170 GB | about 58 h | 20 / 28 min | 3.3 h |

Sources for the table:

- Heap and file size are measured up to 16k and extrapolated beyond.
- Pregen throughput for the full pack has not been measured. The slim set populated painted
  chunks at 181 chunks/s.

The edge includes the sea ring. Recommended size: the largest row whose heap with layers
(about 2× the bare figure) fits the painting machine's RAM.
