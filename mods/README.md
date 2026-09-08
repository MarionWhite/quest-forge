# Mods

The three mods built from source in this repository. Everything else the pack loads
is third-party and recorded in [`../pack/mods.tsv`](../pack/mods.tsv).

| Project | Layout | Output |
|---|---|---|
| [`qf-content`](qf-content/) | Gradle + RetroFuturaGradle | `QuestForgeContent-1.0.0.jar` |
| [`qf-tweaks`](qf-tweaks/) | Plain `javac` + `build.bat` | `QuestForgeTweaks-1.0.jar` |
| [`transformers`](transformers/) | Gradle + RetroFuturaGradle | `TransformersMod-0.6.3-qf1.jar` |

## Before you build anything

Three JVMs are involved and they are not interchangeable — Gradle runs on JDK 25,
the mod compiles to Java 8 bytecode on Zulu 8 arm64, and the packed instance runs on
Oracle 8u162 under Rosetta. Mixing them produces confusing failures that look
unrelated to the cause.
[`../docs/development/mod-workspace.md`](../docs/development/mod-workspace.md)
explains which JVM does what and why each is pinned.

## `qf-content`

The pack's own content mod, and the largest thing here.

- **`ench/`** — 81 custom enchantments with their own categories, application rules
  and event dispatch. The design is in
  [`../docs/design/enchantments.md`](../docs/design/enchantments.md); the measured
  behaviour is in
  [`../docs/reference/enchantment-ground-truth.md`](../docs/reference/enchantment-ground-truth.md).
- **`voice/`** — proximity voice chat, ADPCM in-band over the Minecraft connection
  with a server-side range cut. See
  [`../docs/design/voice-chat.md`](../docs/design/voice-chat.md).
- **`jukebox/`** — an in-game jukebox.
- **`census/`, `survey/`** — the `/qfcensus` and ore-survey commands. These measure
  the running pack, and are the source for
  [`../pack/reports/`](../pack/reports/).

`install-to-prism.command` builds and installs into the live Prism instance, keeping
one backup of whatever it replaces. It resolves its own location, so it works from
anywhere.

## `qf-tweaks`

A coremod, deliberately tiny — two ASM transformers and a loader:

- `PanelButtonQuestTransformer` — patches the Better Questing quest panel UI.
- `MusicTickerTransformer` — takes control of menu music so the splash chant can
  hard-cut to the menu drone.

Built with `javac` directly rather than Gradle; a coremod has no Minecraft
dependencies to resolve beyond the launch wrapper.

## `transformers`

A local build of FiskFille's Transformers mod, patched for this pack. The source
under `src/main/java/fiskfille/` is **not ours** — it is retained here only so the
patched build is reproducible.

`libs/` holds the compile-time dependencies (CodeChickenLib, NEI, Waila) and is
gitignored along with every other third-party jar, so a fresh clone needs those four
jars restored before the build will resolve.
