# `trial/` — boot only the mods a test needs

A full-pack client takes 3–5 minutes and about 6 GB of heap to reach the title screen. Most
trials look at one block, one renderer or one mob. The jukebox preview showed what a slim set
costs: OptiFine plus qf-content loads in under a minute. `trial.py` makes that the default
for any test.

```
py -3.10 tools/trial/trial.py resolve qfcontent gravestones      # show the jar set, build nothing
py -3.10 tools/trial/trial.py build grave gravestones qfcontent --bundle inspect --world "Here We Go"
py -3.10 tools/trial/trial.py launch grave --wait                 # refuses if any client is up
py -3.10 tools/trial/trial.py status                              # who is running what
py -3.10 tools/trial/trial.py remove grave
```

## What every trial gets

Every trial gets the **base set** from [`catalog.json`](catalog.json): OptiFine, BetterFps,
FastCraft, FastLeafDecay, AI Improvements, SoundFilters and QuestForgeTweaks. Together they
are about 2 MB. They are always in because a visual or performance result taken without them
does not describe the pack, and the pack's own coremod fixes have to be present too.

A trial also gets the live shader setting, the QuestForge resource pack and the live options.
Pass `--shader off|enhanced|vibrant` to change the shader. Sildur's Vibrant crashes at world
entry about half the time (a pre-existing problem), so use `enhanced` unless the shader is
the thing under test.

Everything else is opt-in. Name the mods with catalog keys or jar prefixes, and their
`requires` come along automatically. `--bundle` adds a named group:

| Bundle | What it adds |
|---|---|
| `inspect` | NEI and Waila |
| `quests` | Better Questing |
| `tweaker` | CraftTweaker for `scripts/` |
| `qf` | qf-content and qf-commands |
| `spawning` | JAS |
| `hud` | DamageIndicators and JourneyMap |
| `menu` | CustomMenu |

## Safety

- **The live instance is never written to.** Jars are hard links, while `config/`,
  `scripts/` and options are real copies. To test a config change before it is installed,
  layer it on top with `--overlay pack`.
- **There are no junctions.** `remove` or any recursive delete cannot follow a link into
  `%APPDATA%\.crazycraft4`. An old scratch dir built with junctions has to be unlinked with
  `cmd /c rmdir`.
- **Only one client runs at a time.** `launch` checks every running JVM for
  `launchwrapper.Launch`, whoever started it, and holds `%APPDATA%\.qf-trials\client.lock`.
  On 2026-10-13 a second client reset the GPU and killed the user's game.
- **The heap defaults to 3G.** The slim set rarely needs more, and the user's own game and
  other agents' servers share the same 31 GB of RAM.

## When a boot fails on a missing class

`--wait` follows the FML log. When a boot dies on `NoClassDefFoundError` or a missing mod, it
names the live jar that owns the class. Add that jar to the trial, and to `requires` in
`catalog.json`, so the next agent does not pay for the same boot. Most dependencies are kept
by hand because the jars' `mcmod.info` files declare almost none of them.

`list` prints the catalog. It ends with any jar in the live `mods/` that has no entry yet; a
trial can never load an uncatalogued jar.

## When the full pack is the right call

Use the full pack for anything that measures the pack as a whole:

- worldgen and ore surveys (see `../survey/build_server.py`)
- whole-pack frame-rate baselines
- reproducing a bug whose cause is unknown

Even then, once the full pack has reproduced the bug, bisect with trials. That takes
`log2(122)` ≈ 7 slim boots instead of 7 full ones.
