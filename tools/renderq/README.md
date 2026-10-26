# `renderq/`: the one render queue

Shader and texture agents never launch a client to render. They write a spec, submit it, and
read the frames from a known folder. One runner owns the single client slot and renders every
queued job, many per boot.

```
py -3.10 -I tools/renderq/renderq.py submit spec.json     # prints the submission id
py -3.10 -I tools/renderq/renderq.py status               # state, why it waits, done/total, ETA
py -3.10 -I tools/renderq/renderq.py wait ID              # run as a background task; returns when ID is done
py -3.10 -I tools/renderq/renderq.py results ID           # frames, bench txt, cache hits, failures
py -3.10 -I tools/renderq/renderq.py pause "owner gaming" # stops the running client within 10 s
py -3.10 -I tools/renderq/renderq.py resume
py -3.10 -I tools/renderq/renderq.py cancel ID
py -3.10 -I tools/renderq/renderq.py start                # start the runner hidden, if it is not running
```

Everything lives in `C:\qfb\renderq\` (`QF_RENDERQ` overrides it):

| Path | What |
|---|---|
| `queue\ID.json` | a pending submission and the state of each of its jobs |
| `results\ID\result.json` | a finished submission: per job its bench txt, frames, p50/p99 and cache hits |
| `done\ID.json` | the finished submission's record |
| `status.json` | the runner's state, heartbeat, current boot and step, ETA |
| `PAUSE`, `STALLED`, `STOP` | pause flag; stall alert written by the watchdog; ask the runner to exit |
| `runner.log`, `history.jsonl` | what the runner did; one line per boot with measured timings |
| `cache\` | every rendered scene, keyed by everything that defines its frames |
| `snap\` | the shader pack as it was at each submit |
| `jars\QuestForgeContent-1.0.0.jar` | qf-content's debug build with FrameBench batch mode |

Frames and bench files land where `bench_round.py` put them, so `check_frames.py`,
`finish_round.py` and old `make_spec.py` scripts read them unchanged:
`C:\qfb\shaderdev\rounds\screenshots\bench-TAG-SCENE.png` (and `-b.png`),
`rounds\bench\TAG.txt`, plus `rounds\bench\TAG.meta.json`, which says what the frames are.

## A spec

```json
{"name": "r008-a", "owner": "shader-agent", "priority": 0,
 "defaults": {"size": "2560x1440", "preset": "3"},
 "jobs": [
   {"tag": "rh",    "scenes": "ocean_sunset,golden_lit,forest_golden"},
   {"tag": "rm0",   "opts": {"QF_MOTES": 0}, "scenes": ["forest_golden"]},
   {"tag": "off9h", "preset": "off", "scenes": "ocean_sunset,golden_lit,forest_golden"},
   {"tag": "rl",    "preset": "1", "size": "1920x1080", "scenes": "golden_lit"}]}
```

Job fields, with their defaults:

| Field | Default | Meaning |
|---|---|---|
| `tag` | required | bench tag: letters, digits, `_`, `.` |
| `scenes` | required | view names from `views` (or `static`, `torch`, `torch_wall`, `gallery`) |
| `preset` | `"3"` | `0`-`4`, or `off` for shaders off |
| `opts` | `{}` | pack options on top of the preset (`QF_...`) |
| `size` | `2560x1440` | window size |
| `world` | `C:\qfb\world-master` | world copied into the trial |
| `resourcepacks` | `[]` | resource packs, bottom first, under the live ones |
| `reference` | none | render this shader pack zip instead of ours (internal reference frames) |
| `pack` | `shaders/QuestForge` | the pack folder to snapshot at submit |
| `mode` | `cost` | `cost`: frame times count. `shot`: pictures only (20 measured ticks, allowed at night) |
| `fresh` | `false` | render even if the cache has these frames |
| `warm` | `160` | ticks a scene settles after a pipeline rebuild, before it is measured |
| `measure` | `0` | measured ticks (0: the view's own, normally 200) |
| `views`, `rounds`, `mods`, `xmx`, `debug_view` | as `bench_round.py` | |

`prebuild` is a list of commands (argument lists, run in the repo root) that run once before
the submission's first boot: `specs\textures.json` builds the texture pack this way and renders
it next to vanilla and Faithful in the same boot. A failing step fails the submission.

The pack is copied when you submit, so you can keep editing `shaders/QuestForge` while the job
waits. Submitting a tag that is still queued is refused; `--replace` drops the old one.

## What a boot is

Jobs with the same window size, world, mods and pack snapshot render in one boot; shaders-off
jobs join any boot of their size and world, and resource packs switch in the world. FrameBench's
batch mode (`-Dqf.bench.jobs`, written by `batch.py`) places each scene once, then measures every
job that wants it there: it rewrites `shaderpacks/QuestForge.txt` and calls `Iris.reload()`, or
`Iris.toggleShaders` for shaders off, and lets the scene settle `warm` ticks before measuring.
r007's 23 runs become 4 boots (1440p vanilla, 1440p texture world, 1080p, 720p).

Every boot starts with shaders OFF and turns them on in the world. Booting with shaders on
crashed every run whose pack or options were new to the shader cache (r007: every first launch,
49 s, then a 5-minute idle wait and a second boot): Angelica 2.2.33 builds the pipeline before the
game's last resource reload and again after it (`[Load #2]`), and the rebuilt full-screen quad
draws with a stale VAO. It was never the trial rebuild: `angelica\shadercache` survives
`build --force`. Turning the pack on in the world builds the pipeline once.

## The runner

- **The owner first.** A boot starts only after `trial.py userbusy` has said idle for 5 minutes.
  While a client runs, userbusy is sampled every minute; when the owner starts a game the client
  is stopped at once, the steps measured before the last idle sample are kept and the rest
  re-render later. Nothing is ever only "marked noisy". `pause` does the same on request.
- **One client.** It waits while any other client runs or holds `client.lock`, and after another
  session's client it waits 3 more minutes, so a session's own run script gets its next turn.
- **The cache.** A scene's key covers the window size, the world (file sizes and times), the
  resource packs (zip entries), the mods and the FrameBench jar, the scene's line in the views
  file, and for shaders on the pack snapshot and the option file. A hit is copied to the new tag
  with a `cached from TAG DATE` line in the bench txt. Two jobs that ask for the same frames in
  one boot render them once.
- **Retries and the watchdog.** A boot that crashes, hangs (no log and no progress for 6 min) or
  stalls (no progress for 20 min: `STALLED` plus `status.json`) is stopped; the steps it
  finished are kept and the rest go into the next boot. A job fails after 3 attempts.
- **Hidden.** `start` writes `start.vbs` and runs it with `wscript`: pythonw, window style 0, so
  nothing shows; the client is `trial.py launch`'s usual background client.
- **Sleep and wake.** A loop gap over 150 s resets every timer, so a sleep is not a stall.
  `status` reports a dead runner when the heartbeat is over 3 minutes old.
- **Starting it.** `install-task` prints a per-user scheduled task (no admin) that runs
  `start.vbs` every 10 minutes, which starts the runner only when none is alive; `--yes`
  creates it. It is the owner's call.

## Night mode (off unless the owner turns it on)

`C:\qfb\renderq\config.json`:

```json
{"night": {"enabled": true, "start": "23:00", "end": "08:00", "max_fps": 30, "power_limit_w": null}}
```

Between `start` and `end` only `mode: shot` jobs run, with the frame rate capped at `max_fps`
(their frame times are not costs, and cost jobs wait for the day). `power_limit_w` runs
`nvidia-smi -pl` around each boot. That needs an elevated prompt ("Insufficient Permissions"
otherwise), and the RTX 5070 Ti's floor is 250 W of its 300, so the frame cap is the real lever.
Measured on 6 views at 1440p: 41 W GPU mean at 30 fps against 233 W uncapped, fan 0-30% against
30-56%, 39 C against 68 C, at the same speed (22.9 against 21.2 s a scene).

## The FrameBench jar

The runner loads `C:\qfbenderq\jars\QuestForgeContent-1.0.0.jar`, qf-content built with
`-PqfDebugTools=true` (in a worktree: `.\gradlew.bat build -PqfDebugTools=true -x test` in
`mods/qf-content`, then copy `build\libs\QuestForgeContent-1.0.0.jar` there). It never goes into
the live instance. A new jar changes every cache key, so everything re-renders once.

## Reference frames from other packs (internal only)

`specs
eferences.json` renders the r007 views once with Complementary Reimagined and Unbound
r5.9.3, Photon v1.4 and BSL 10.1.8, unmodified, at their defaults, into `C:\qfb\shaderdev
efs`
(`refcr`, `refcu`, `refph`, `refbsl`). They are for the critic's comparison and NEVER go on the
site: none of those licences allows it. The zips come from each pack's official Modrinth project,
sha512-checked, in `C:\qfb
efpacks\<name>\dl\` (Unbound in `C:\qfb\dl\complementary`).
Complementary and BSL render correctly under Angelica on 1.7.10. Photon v1.4 does not (flat
yellow terrain, plain blue sky), so `refph` is not a reference. Being cached, they re-render only
when the world, the views or the jars change.

## Finishing a round

`tools/shaders/review/finish_round.py ROUND_DIR [--publish]` posts a round from finished renders:
it waits for nothing, it checks. See its docstring.
