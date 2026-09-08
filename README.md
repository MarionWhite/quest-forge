# Quest Forge

Source for **Quest Forge**, a quest-driven Minecraft 1.7.10 modpack: 111 mod files
(141 registered mods) on Forge 10.13.4.1558, with three mods authored or patched
in-house.

This repository holds everything hand-authored — the mods we wrote, the config that
defines the pack, the tools that generate its assets, and the notes explaining why
things are the way they are. It deliberately does **not** contain third-party mod
jars, world saves, or generated renders; see [What is not here](#what-is-not-here).

---

## Repository map

| Path | What lives there |
|---|---|
| [`mods/`](mods/) | The three mods we build ourselves. Each is a standalone Gradle project. |
| [`pack/`](pack/) | The pack definition: config, CraftTweaker scripts, branding resourcepack, and the manifest of every third-party mod the pack loads. |
| [`tools/`](tools/) | Generators and analysis scripts — branding art, menu music, ore surveys, balance simulation. |
| [`server/`](server/) | The headless survey server used to measure worldgen, stored as a delta against `pack/config`. |
| [`site/`](site/) | Static pages: the public mod list and the ore-vein atlas. |
| [`docs/`](docs/) | Setup, design, reference and decision records. Start at [`docs/README.md`](docs/README.md). |

### `mods/` — what we build

| Project | What it is |
|---|---|
| [`qf-content`](mods/qf-content/) | The pack's own content mod: 81 custom enchantments with their own application rules, in-band proximity voice chat, an in-game jukebox, and the `/qfcensus` survey commands used to balance the pack. |
| [`qf-tweaks`](mods/qf-tweaks/) | A two-transformer coremod: one ASM patch for the Better Questing panel UI, one for menu music control. |
| [`transformers`](mods/transformers/) | A local build of the FiskFille Transformers mod, patched to fit this pack. |

---

## Quick start

Building the content mod requires **three different JVMs** doing three different
jobs. This is the single most confusing part of the setup and it is not optional —
read [`docs/development/mod-workspace.md`](docs/development/mod-workspace.md)
before your first build.

```bash
cd mods/qf-content
./gradlew build            # compile + reobfuscate -> build/libs/
./gradlew runClient        # dev client, this mod only (~40s)
./install-to-prism.command # build, then install into the live Prism instance
```

A successful `runClient` is **not** proof the pack will load the mod. Only
`install-to-prism.command` followed by a real Prism launch proves that.

---

## What is not here

Four categories are excluded on purpose. Each is either someone else's to
distribute, or reproducible from what is here.

| Excluded | Why | Where it lives instead |
|---|---|---|
| Third-party mod jars (~1.3 GB) | Not ours to redistribute. | Recorded in [`pack/mods.tsv`](pack/mods.tsv) — every file, name, version and size. |
| Minecraft / Forge jars and libraries | Same. | Fetched by Gradle and by Prism. |
| World saves (~250 MB) | Large, binary, personal. | The live Prism instance. |
| Generated renders — audio, splash art, icons | Reproducible. The `_music` scratch folder alone held ten 20–44 MB renders of the same track. | Regenerate with the scripts in [`tools/`](tools/). |

Shipped assets that the game actually loads *are* here, in
[`pack/resourcepack/`](pack/resourcepack/).

---

## Conventions

Adopted when this repository was assembled, replacing the ad-hoc layout that
preceded it:

- **Directories are kebab-case** and describe their contents, not when they were
  made. `tools/branding/splash-buffer`, not `_splash-4k-buffer`.
- **No dates in filenames.** Eleven timestamped `DefaultQuests.pre-*.json`
  snapshots were deleted during the move; git history replaces them. `.gitignore`
  blocks the pattern from coming back.
- **Generated output is never committed.** If a file can be rebuilt by a script in
  `tools/`, the script is the artifact.
- **Derived config is stored as a delta.** `server/config` holds only the 28 files
  that differ from `pack/config`; the other 852 were identical and are not
  duplicated.
- **Prose is `.md`, tabular data is `.txt`.** Column-aligned survey output stays
  fixed-width in [`pack/reports/`](pack/reports/).

---

## Status

The pack runs. As of the last verified launch it loaded all 141 mods and reached a
world; the fix that got it there is recorded in
[`docs/decisions/0001-chocolatequest-enchantment-id.md`](docs/decisions/0001-chocolatequest-enchantment-id.md).
