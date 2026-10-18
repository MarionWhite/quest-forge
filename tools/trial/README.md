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
py -3.10 tools/trial/trial.py stop grave                        # kills only this trial's own JVM
py -3.10 tools/trial/trial.py remove grave
```

Run `launch --wait` as a **background task**. It follows the log, bounded by `--timeout`, and
returns as soon as the client reaches the title screen or crashes. Do not sit in a foreground
`until grep …; sleep` loop. In the 10-16 audit those loops cost about 85 minutes.

## Servers

`--server` builds a dedicated server with the same mod resolution. Client-only jars are
dropped from the base set, and asking for one by name is an error. The Forge and vanilla
server jars and `libraries/` are hard-linked from an existing server dir (`C:\qfs\combat`,
`friends` or `trial-base`). Each trial gets the next free port from 25600 up.

```
py -3.10 tools/trial/trial.py build naga --server qfcontent twilightforest --world C:\qfs\combat\combat
py -3.10 tools/trial/trial.py launch naga --xmx 3G -D qf.census.combat=TwilightForest.Naga --commands cmds.txt --wait
```

`--forge 1614` builds the server on Forge 10.13.4.1614 (jars from `C:\qfsorge1614-install`)
instead of the pack's 1558. Biomes O' Plenty 2.1.0.2308 refuses anything below 1566.

A client trial joins a server trial with `launch NAME --join 127.0.0.1:PORT`: it connects
as soon as its menu is up (vanilla's `--server`/`--port`).

`--commands` feeds a file of console commands on stdin. They are queued until the server
starts ticking.

Every launch, client or server, refuses when the heaps of all running Minecraft JVMs plus the
new one would pass **22 GB** (`QF_RAM_BUDGET_GB`). The PC has 31 GB, and the user's own game
takes 7.

## Candidate jars that are not in the pack

A mod being evaluated never goes into the live `mods/`. Stage it instead:

```
py -3.10 tools/trial/trial.py stage C:\path	o\BiomesOPlenty-1.7.10-2.1.0.2308-universal.jar
```

This copies it to `%APPDATA%\.qf-trials\_staged\mods`. A catalog entry marked `"staged": true`
takes its jar from there when the live instance has none.

## Installing into the live pack

```
py -3.10 tools/trial/trial.py install mods/qf-content/build/libs/QuestForgeContent-1.0.0.jar --why "jukebox lod"
```

This is the only way a jar should go into `%APPDATA%\.crazycraft4\mods`.
- It refuses while the user's game, or a server running from the live instance, is up.
- It refuses the `-dev` jar.
- It refuses a jar that would sit next to another version of itself.
- It replaces atomically and keeps the old jar in `_backup-install-<time>/`.
- It logs who installed what to `%APPDATA%\.qf-trials\install.log`.

Never drop probe jars into the live `mods/`. Put the probe in a trial.

## Guard: nothing writes the live pack behind `install`

`trial.py guard` checks two things:

- **Hard links into the live `mods/`.** A hard link is a second name for the same file, so a `cp` onto it overwrites the live jar.
  On 2026-10-17 an agent copied test builds into a test client whose jars were linked to the live ones, and two live jars changed.
  `--fix-links` turns every link outside the live pack into a real copy, skipping folders a JVM is running from.
- **Live jars that changed without `install`.** `install` keeps `%APPDATA%\.qf-trials\live-manifest.json`, a hash of every live jar.
  Any other change is reported with its file and time.

It runs on its own: `launch` warns, and `install` **refuses** while there is an unexplained change, so an accident gets looked at instead of buried under the next install.
If the change was intended, record it with `guard --accept`. If not, restore the previous jar from the `_backup-install-*` copy that `install` keeps.

## Bisecting

```
py -3.10 tools/trial/trial.py bisect start --keep qfcontent          # suspects: every non-base mod
py -3.10 tools/trial/trial.py launch bisect --wait                   # reproduce...
py -3.10 tools/trial/trial.py bisect bad                             # ...still broken -> next half
py -3.10 tools/trial/trial.py bisect good                            # ...fixed -> the other half
```

Each answer rebuilds the `bisect` trial with half the remaining suspects. Libraries come along
with whatever needs them. Expect about 7 slim boots for the whole pack.

## Disk

`trial.py disk` lists every game or server dir on the PC with its size, whether a JVM is using
it, and any junctions it contains. It never deletes anything.

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

- **The live instance is never written to.** Jars, `config/`, `scripts/`, resources and options are real copies (until 2026-10-17 jars were hard links, and a `cp` onto a trial jar overwrote two live jars), while `config/`,
  `scripts/` and options are real copies. To test a config change before it is installed,
  layer it on top with `--overlay pack`.
- **There are no junctions.** `remove` or any recursive delete cannot follow a link into
  `%APPDATA%\.crazycraft4`. An old scratch dir built with junctions has to be unlinked with
  `cmd /c rmdir`.
- **Only one client runs at a time.** Servers are bounded by the RAM budget instead. `launch` checks every running JVM for
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
