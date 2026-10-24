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

## Background, silent clients (the default)

A client trial never appears on the owner's screen, takes focus or makes a sound. The owner
can work or play a game while it renders. This became the default on 2026-10-23, after a
trial went fullscreen over the owner's game and console windows took focus.

- **Window.** The JVM is `javaw` (no console), started with `-WindowStyle Hidden`: STARTUPINFO SW_HIDE
  keeps the game window hidden through LWJGL's first ShowWindow, so it can only appear once it is
  already off-screen (verified 2026-10-23: no on-screen sample at 10 ms; no stall, same fps). A hidden,
  detached `window.ps1 -Mode hide` watches every top-level window of that pid for the JVM's
  whole life: every 100 ms for the first 40 s (the splash, then the main window), then every
  second. It restores the window if it is minimized, because a minimized LWJGL window stalls.
  It moves the window left of the virtual screen with `SWP_NOACTIVATE|SWP_NOZORDER`, adds
  `WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE`, removes `WS_EX_APPWINDOW`, and drops the taskbar tab.
  It shows the hidden window with one async `SetWindowPos(SWP_SHOWWINDOW|SWP_NOACTIVATE)` plus
  `ShowWindowAsync(SW_SHOWNOACTIVATE)`. All calls are async, because the main thread pumps no messages
  during the splash. A visible window not yet off-screen is veiled (layered, alpha 0) until the move
  lands. It never calls `SetForegroundWindow`. The requested `--size` is kept. Its log is
  `logs\window.log`. `launch --foreground` shows the window on the desktop as before.
- **No console windows.** Every process `trial.py` and the shader review scripts start uses
  `CREATE_NO_WINDOW`, or a Hidden PowerShell. Started from an agent's shell, a console program
  otherwise opens a Windows Terminal window that steals focus. Servers start Hidden.
- **Silent and windowed.** Each build and launch writes `fullscreen:false`, `key_key.fullscreen:0`
  (F11 unbound) and `soundCategory_*:0.0` into the trial's `options.txt`. It deletes the trial's
  copy of `resources\...\music\splash.wav` and `menu.wav`, which `qf/splash/SplashMusic`
  plays through Java Sound regardless of volume. It writes `enabled=false` into
  `config\qf-voice.properties` and passes `-Dqf.silent=true`, which silences SplashMusic,
  the jukebox and voice chat in qf-tweaks/qf-content jars built from 5450145 on.
- **Is the owner gaming?** `trial.py userbusy` prints JSON and exits 1 when the owner is busy.
  Busy means one of these: the foreground window covers its monitor, the foreground exe is
  under a game store's folder, Windows reports a fullscreen or D3D app, or a process that
  isn't one of our clients uses at least 40% of the GPU 3D engine (any game-store exe counts
  at a lower load). `launch` prints the same answer on its `launch-info:` JSON line and in
  `<trial>\launch.json`. Launches are not blocked on it. Screenshots stay valid, but frame
  times taken while busy share the GPU with the game, so mark them noisy or wait.

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

## Angelica trials (`--renderer angelica`)

```
py -3.10 tools/trial/trial.py stage-angelica          # once: copies the Angelica stack into _staged, by sha1
py -3.10 tools/trial/trial.py build shaders --renderer angelica qfcontent twilightforest ^
    --shaderpack shaders/QuestForge --shader QuestForge --world C:\qfb\world-master
py -3.10 tools/trial/trial.py launch shaders --size 1920x1080 --wait
```

`--renderer angelica` swaps the base set's OptiFine, BetterFps and FastCraft for Angelica 2.2.33,
UniMixins and GTNHLib, and launches on stock Forge 1614 instead of the live 1558 jar. CodeChickenCore
needs no swap: since 2026-10-18 the live pack itself runs GTNH CodeChickenCore 1.4.22 (CodeChickenLib
merged in), for both renderers. The jars and hashes are
[`../angelica-client/manifest.json`](../angelica-client/manifest.json): the stack friends install.
They are not in the live pack, so `stage-angelica` copies them (from `C:\qfb\dl` and
`C:\qfb\client-ang2` by default, `--from DIR` otherwise) into `%APPDATA%\.qf-trials\_staged`, refusing
any jar whose SHA-1 differs. It also stages `falsepattern\`, the libraries Angelica downloads on its
first boot, so trials start offline.

The trial gets the Angelica client's overlay (vsync off, the Iris keys on F4/F8/F9, no splash memory bar)
and Iris's debug output (`enableDebugOptions`, `saveCompiledShaders`: errors in game, transformed GLSL in
`patched_shaders\`). `--shader NAME` picks the pack in `config\shaders.properties`; `--shaderpack DIR`
copies a pack folder in, and **every launch re-copies it**, so a launch always runs the repo's current
source. `--jar BUILT.jar` swaps in a built jar for the live one of the same catalog entry (for example
qf-content built with `-PqfDebugTools=true` for FrameBench). `launch --size WxH` sets the window size,
because shader budgets are per resolution.

The shader review loop drives these trials through `tools/shaders/review/bench_round.py`.

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

A jar that supersedes one with a different file name (a version in the name, or GTNH
`CodeChickenCore-1.4.22.jar` for stock `CodeChickenCore.jar`) goes in with `--replace OLD`: the old jar
moves into the same backup folder in the same step, so FML never sees both and the pack is never
left with neither.

### Taking a jar out

```
py -3.10 tools/trial/trial.py uninstall "1.7.10/CodeChickenLib-*.jar" --why "merged into GTNH CodeChickenCore"
```

Removing a jar changes the pack as much as adding one, so `uninstall` gets the same checks:

- `--why` is required.
- It runs the guard first and refuses on an unexplained change, like `install`.
- It refuses while the user's game, or a server running from the live instance, is up.
- The name is a file name or a path under `mods/` (`1.7.10/x.jar`), globs allowed, and must match exactly one jar.
- It refuses when another live jar requires it (catalog `requires`) and nothing else provides it.
- The jar moves to `_backup-install-<time>/` (keeping `1.7.10/`), the line goes into `install.log`
  (`UNINSTALL ...`), and `live-manifest.json` drops it. It prints the `install --as` line that undoes it.

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
- **Never over the owner's game.** A background client launch waits until `userbusy` has said idle
  for 5 minutes in a row (`--idle-min`); `bench_round.py` waits the same way before each run. On
  2026-10-24 a shader round rendered through three hours of the owner's Deadlock because the runs
  were only marked noisy. `--busy-ok` overrides it, and only the owner can ask for that.
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
