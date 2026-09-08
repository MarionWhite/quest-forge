# Survey server

A headless Forge server used to measure worldgen. Running four copies in parallel
("nodes") and merging their output is how the ore-vein numbers in
[`../pack/reports/`](../pack/reports/) were produced — a single client cannot
generate enough chunks in reasonable time.

## What is stored here

| Path | Contents |
|---|---|
| `config/` | **Only the 28 files that differ from [`../pack/config`](../pack/config).** |
| `scripts/` | The server's CraftTweaker scripts. |
| `disabled-mods.md` | Which mods were removed from the server, and the rule for removing one. |
| `server.properties`, `ops.json`, `whitelist.json`, `eula.txt` | Server setup. |

`config/` is a **delta, not a copy**. Of the 880 config files, 852 were byte-identical
to the pack's; duplicating them would have added 15 MB of noise and two places to
make the same edit. To reconstruct the full server config, copy `pack/config` and
overlay this directory on top.

The differences are meaningful and worth reading as a set: the server runs HBM's ore
mod (`hbm.cfg`) that the live pack does not, drops ChocolateQuest, and adds
`JourneyMapServer`.

## What is not stored here

The server jars, the mod jars, the four node directories and their generated worlds —
roughly 3 GB, all of it either third-party or regenerable. Rebuild a node by taking a
Forge 1.7.10-10.13.4.1558 server, adding the pack's mods minus the ones listed in
`disabled-mods.md`, and overlaying `config/`.

## The rule for disabling a mod

From `disabled-mods.md`, and worth restating because it is what makes the survey
trustworthy:

> A mod is only removed if it cannot place a block in the world, so removing it
> cannot change what the ore survey measures. Everything that touches worldgen,
> ores, dimensions or biomes stays in, whatever it costs to make it boot.

Client-only mods — renderers, HUDs, sorting, cosmetics — are safe to drop. Anything
else is not.
