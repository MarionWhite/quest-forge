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
| [`setup/hosting-a-server.md`](setup/hosting-a-server.md) | Building and running the multiplayer server for friends. |
| [`setup/why-was-i-refused.md`](setup/why-was-i-refused.md) | For players: what each pack-check refusal means and what to do. |
| [`setup/transfer-from-windows.md`](setup/transfer-from-windows.md) | How the pack was moved off the original Windows install. |
| [`setup/migration-manifest.md`](setup/migration-manifest.md) | What the 2026-09-04 migration bundle contained. |

## Development — working on the mods

| Document | What it covers |
|---|---|
| [`development/mod-workspace.md`](development/mod-workspace.md) | **Read before your first build.** The three-JVM toolchain and why each one is required. |
| [`development/cookbook.md`](development/cookbook.md) | Recipes for common changes. |
| [`development/building-on-windows.md`](development/building-on-windows.md) | Building the mods on a Windows PC: two JDKs and one properties file. |

## Design — why the custom content works the way it does

| Document | What it covers |
|---|---|
| [`design/enchantments.md`](design/enchantments.md) | The 81-enchantment system: categories, application rules, balance targets. |
| [`design/voice-chat.md`](design/voice-chat.md) | In-band proximity voice: codec choice, transport, and the server-side range cut. |
| [`design/shaders/`](design/shaders/README.md) | The pack's own shader pack: why, the look bible, performance rules, the phone review loop, and the research behind them. |
| [`design/questline-audit.md`](design/questline-audit.md) | **The quest book today and the plan to make it AAA.** Every chapter mapped, broken and tier-skipping quests, untouched content, and an ordered work plan (WP-0 toolkit first). |
| [`design/progression-audit.md`](design/progression-audit.md) | **Where the power curve flattens.** Gear ladder across mods, shortcuts that skip to the top, the plateau, zero-cost fixes and an enchant loot design. |
| [`design/server-readiness.md`](design/server-readiness.md) | **What the friends' server still lacks.** Backups and restarts, stale-client joins, identity, chunk loaders, profiling, admin tools, social rules. |
| [`design/performance-plan.md`](design/performance-plan.md) | **Where time and memory go, and the lite client for weaker PCs.** Measured heap/atlas/VRAM, ranked general wins, and what changes if Angelica is adopted. |

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
| [`survey/combat-server.md`](survey/combat-server.md) | **How to build the server the combat census runs on.** Assembling it from the live instance, the one mod that has to go, and the three ways this pack differs from vanilla once you measure it. |
| [`survey/combat.md`](survey/combat.md) | **How to measure enchantments in a fight.** `/qfcensus combat`, what it controls for, the two calibrations, and the chunk trap that makes targets stop ticking. Read before trusting any balance number. |

## Decisions

Dated records of choices that are expensive to reverse or easy to undo by accident.
Append new ones; never rewrite an old one.

| Record | Decision |
|---|---|
| [`decisions/0001-chocolatequest-enchantment-id.md`](decisions/0001-chocolatequest-enchantment-id.md) | Patch ChocolateQuest's hardcoded enchantment ID rather than move Soul Shards', to avoid reinterpreting existing enchanted gear. |
| [`decisions/0002-discard-the-ore-survey.md`](decisions/0002-discard-the-ore-survey.md) | Discard every published ore figure and re-measure: the survey ran a mod set no player has played, and vein size was never a block count. |
