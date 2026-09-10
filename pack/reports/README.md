# Generated reports

## The current ore numbers

`ore-rates.json` and `ore-rates.txt`, measured 2026-09-10. **Use these.**

All **30 dimensions** generated with the live mod set across **4 seeds**, and
every block in the resulting region files counted: **4,775,020 populated
chunks**. Per ore, per dimension, per depth and per biome, with a standard
deviation across seeds beside every rate.

| | |
|---|---|
| Dimensions carrying real ore | **16** |
| Carrying traces (<2 blocks/chunk) | **9** |
| Placing nothing | **5** |
| Richest | Overworld, 1,141 ore blocks/chunk across 41 ores |
| Next | dim 58 "DIM 54" (LegendsMod), 1,017 across 27 |

Depth is the measured Y band and its middle-90%, not a generator's configured
range. Biome is reported as *enrichment* — an ore's share of its own blocks in a
biome divided by that biome's share of the dimension's volume — because a biome
covering 40% of a dimension holds ~40% of every ore in it for no interesting
reason.

Two sanity checks worth knowing about, both of which the data passes: bedrock
comes out at 767 blocks/chunk against vanilla's expected ~768, and vanilla ore
depths reproduce (lapis peaks at Y 13, redstone's middle-90% is Y 1–13).


> **Reviewed.** A separate reviewing agent re-derived all 264 published rows from the
> raw scans (zero mismatches), confirmed rates are averaged not summed, found no
> dropped chunks across 4.78M, and verified the CodeChickenLib patch cannot
> touch worldgen. It also found two real errors, both since fixed and
> regenerated: dimension 53 read 28.5 instead of 15.2 because a `data/region/`
> folder shipped inside its map was counted as dimension chunks, and dimension
> 84 read 215.7 instead of 16.8 because that dimension's grass layer carries an
> "ore" token in its name. No other dimension changed.
>
> Known limits: the trace/nothing boundary is **not resolved** — dims 31, 32 and
> 36 rest on ten to twenty blocks in the whole sample, far below this survey's
> own floor. Read those as uncertainty, not as figures.

Method, and the bugs that had to be fixed before any of it was trustworthy: [`../../docs/survey/README.md`](../../docs/survey/README.md).

---

## ⚠ The older ore files here are void — do not use them

`qfcontent-oresurvey.txt`, `qfcontent-oreveins.txt`, `ore-vein-parameters.txt`
and `ore-vein-parameters-without-hbm.txt` describe **a pack nobody has played**.
They are kept only as evidence of how the measurement went wrong.

The survey server that produced them ran **HBM's ore mod**, which the live pack
does not have, and **never loaded ChocolateQuest**, which it does. HBM's veins
compete for the same stone as every other ore (measured at +4% density, +6% on
coal when removed); ChocolateQuest carves dungeons *after* ore is placed, so its
absence leaves ore in the ground that would not survive in a real world.

Two further faults, independent of the mod set:

- **Vein size is not a block count.** It parameterises the ellipsoid
  `WorldGenMinable` traces. A size-3 vein places 0.47 blocks; a size-16 vein
  places 20.04. Anything converting size to blocks by a single factor is wrong
  by up to 6×.
- **Rows blend distinct call sites.** `minecraft:diamond_ore = 1.954 veins,
  size 6.51` is two or more generators averaged into one that does not exist.
  Non-integer rates and fractional sizes are the tell.

They also silently omit whole mods: 1Legends ore is among the most abundant in
the pack and appears nowhere in them.

Full reasoning: [`../../docs/decisions/0002-discard-the-ore-survey.md`](../../docs/decisions/0002-discard-the-ore-survey.md).
Replacement procedure: [`../../docs/survey/README.md`](../../docs/survey/README.md).

Do not filter, rescale or patch these numbers. Re-measure.

## The enchantment file is fine

`qfcontent-enchantments.txt` is a registry dump from a running game and is
unaffected by any of the above.
