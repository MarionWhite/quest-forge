# Documentation

Four kinds of document, kept separate because they age differently. Setup
instructions get followed once; reference data gets regenerated; decisions are
never edited after the fact.

## Setup — getting the pack running

Read in this order on a new machine.

| Document | What it covers |
|---|---|
| [`setup/install-on-mac.md`](setup/install-on-mac.md) | The from-scratch M1 guide. Start here. |
| [`setup/jvm-args.md`](setup/jvm-args.md) | Prism JVM arguments, with RAM presets. Java 8 only. |
| [`setup/mac-setup.md`](setup/mac-setup.md) | Mac-specific notes: Rosetta, natives, LWJGL. |
| [`setup/performance-tuning.md`](setup/performance-tuning.md) | What to turn down, and what it costs. |
| [`setup/transfer-from-windows.md`](setup/transfer-from-windows.md) | How the pack was moved off the original Windows install. |
| [`setup/migration-manifest.md`](setup/migration-manifest.md) | What the 2026-09-04 migration bundle contained. |

## Development — working on the mods

| Document | What it covers |
|---|---|
| [`development/mod-workspace.md`](development/mod-workspace.md) | **Read before your first build.** The three-JVM toolchain and why each one is required. |
| [`development/cookbook.md`](development/cookbook.md) | Recipes for common changes. |

## Design — why the custom content works the way it does

| Document | What it covers |
|---|---|
| [`design/enchantments.md`](design/enchantments.md) | The 81-enchantment system: categories, application rules, balance targets. |
| [`design/voice-chat.md`](design/voice-chat.md) | In-band proximity voice: codec choice, transport, and the server-side range cut. |

## Reference — measured facts

These describe the pack as it actually is, and go stale when the pack changes.
Regenerate rather than edit.

| Document | Source |
|---|---|
| [`reference/enchantment-list.md`](reference/enchantment-list.md) | The full custom enchantment roster. |
| [`reference/enchantment-ground-truth.md`](reference/enchantment-ground-truth.md) | Measured effect values, as opposed to intended ones. |
| [`reference/enchantment-tuning.md`](reference/enchantment-tuning.md) | Balance passes and what each changed. |

Raw generated output — ore surveys, vein parameters, the enchantment registry dump —
lives in [`../pack/reports/`](../pack/reports/), not here.

## Survey — measuring the pack

| Document | What it covers |
|---|---|
| [`survey/README.md`](survey/README.md) | **How to measure ore generation.** Build the headless server, pregenerate, count the region files. Includes which of the 30 dimensions actually carry ore, and how many chunks a given precision needs. |

## Decisions

Dated records of choices that are expensive to reverse or easy to undo by accident.
Append new ones; never rewrite an old one.

| Record | Decision |
|---|---|
| [`decisions/0001-chocolatequest-enchantment-id.md`](decisions/0001-chocolatequest-enchantment-id.md) | Patch ChocolateQuest's hardcoded enchantment ID rather than move Soul Shards', to avoid reinterpreting existing enchanted gear. |
| [`decisions/0002-discard-the-ore-survey.md`](decisions/0002-discard-the-ore-survey.md) | Discard every published ore figure and re-measure: the survey ran a mod set no player has played, and vein size was never a block count. |
