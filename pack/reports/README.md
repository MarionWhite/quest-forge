# Generated reports

## ⚠ The ore files here are void — do not use them

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
