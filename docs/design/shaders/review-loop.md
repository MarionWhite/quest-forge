# Review loop

How each iteration of the shader is judged before it reaches the owner. The aim
is that the owner only ever sees frames a strong critic already thinks are
close, and only ever answers questions a machine can't: taste.

## Where it runs

| | Now | Later |
|---|---|---|
| Game dir | `C:\qfb\client-ang`: Angelica 2.2.33, Forge 1614, GTNH CodeChickenCore 1.4.22, **plus Hodgepodge 2.7.216 and ArchaicFix 0.8.0** | The final Angelica client built by `tools/angelica-client/build_angelica_client.py` (for example `C:\qfb\client-ang2`), **without Hodgepodge or ArchaicFix**. Another session is building it. |
| Launch | `C:\qfb\run_bench.ps1 -Client C:\qfb\client-ang -ForgeJar C:\qfs\forge1614-install\forge-1.7.10-10.13.4.1614-1.7.10-universal.jar` (the script defaults to the live 1558 jar, which Angelica can't use) | the same, with `-Client` pointing at the new folder |
| Boot | full pack, about 3–5 min (`trial.py` has no Angelica base set, so no slim trials yet) | slim trials, once `trial.py` learns the Angelica base set |

**When the client changes, re-run three baselines in the new client before
comparing anything:** shaders off, Complementary and our last accepted round.
Frame times from the two clients aren't comparable, because Hodgepodge and
ArchaicFix change chunk and lighting work. Screenshots are comparable.

All work here is singleplayer. The pack check now refuses mismatched mod
versions on servers, which doesn't affect this loop: no server is involved.

**One client at a time.** Before every launch, run
`py -3.10 -I tools/trial/trial.py status`. If it lists any client (the user's,
or another session's), don't launch. `run_bench.ps1` also refuses when it sees
one. A second full-pack client makes the NVIDIA driver reset the GPU and kills
both.

## One-time setup of the client

Do this with the game closed; [`README.md`](README.md) "Getting started" has the
details.

- `config\angelica-options.json`: `"vsync_mode": "OFF"`. Without it every
  frame time pins to 4.16 ms, and `check_frames.py` fails the round.
- `config\shaders.properties`: `enableDebugOptions=true` and
  `saveCompiledShaders=true`.
- The dev pack is a folder at `shaderpacks\QuestForge-dev\`, a junction to the
  repo's source.

`run_bench.ps1` copies the live instance's `options.txt` over the client's on
every run, so key bindings made by hand don't survive a bench run. That doesn't
matter for unattended rounds. For hand iteration, rebind F9 (reload) after a
bench run, or launch the final client, which binds the keys in its build.

## The cycle

1. **Change.** One feature or fix at a time, on a branch of the shader source.
2. **Render the scene set** with the harness:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -Command "& C:\qfb\run_bench.ps1 -Client C:\qfb\client-ang `
       -ForgeJar C:\qfs\forge1614-install\forge-1.7.10-10.13.4.1614-1.7.10-universal.jar `
       -Tag r12 -Shader QuestForge-dev -ExtraPacks QuestForge-Surface.zip -Scenes 'static,fly,torch,gallery' `
       -PackOpts @{QF_PRESET='4'} -TimeoutMin 25"
   ```
   Run it as a background task, never in a foreground wait loop.
   - `-Shader` is the pack folder's name. The script writes
     `config\shaders.properties` (`shaderPack=`, `enableShaders=true`), and
     `-PackOpts` goes into `shaderpacks\QuestForge-dev.txt`, the option file
     Iris reads. Our pack's preset option, `QF_PRESET` (0 Potato to 4 Ultra),
     selects the tier. `-ExtraPacks` loads the generated normal-map pack from
     `C:\qfb\surface\` above `QuestForge.zip`.
   - Each run copies a fresh world from `C:\qfb\world-master`. `FrameBench`
     (`-Dqf.bench=1`) flies the scenes, then writes
     `C:\qfb\client-ang\bench\<tag>.txt` (mean, p50, p99, 1% low, worst, frames
     over 33 ms per scene) and screenshots at 2560×1440 to
     `C:\qfb\client-ang\screenshots\bench-<tag>*.png`. GPU load goes to
     `logs\gpu-<tag>.csv`.
   - Render each round twice: once on the round's tier, and once on Low with
     `-Tag <tag>-low`, so that Low can never silently fall behind.
   - Today `FrameBench` only has the static, fly, torch and gallery scenes. The
     rest of the scene set (below) still needs scenes added to it. Until then,
     those scenes are hand-captured: F2 in the dev client, the same coordinates
     and time from a written list, saved to `screenshots\`.
3. **Automatic checks**, before any model looks:
   ```
   py -3.10 -I tools/shaders/review/check_frames.py --client C:\qfb\client-ang --tag r12 --off m-B0 --prev r11 --tier ultra
   py -3.10 -I tools/shaders/review/check_frames.py --client C:\qfb\client-ang --tag r12-low --off m-B0 --tier low-proxy
   ```
   The script checks:
   - **frame-time budget:** shader cost against the tier's dev-PC budget
     (`performance-rules.md`), where shader cost is the p50 minus the
     shaders-off run's p50;
   - **regressions:** the 1% low and frames over 33 ms must not get worse than
     `--prev`;
   - **the vsync cap,** flagged when it shows in the numbers;
   - **exposure:** clipped highlights and crushed shadows, as a percentage of
     pixels with the HUD masked out;
   - **brightness:** mean luminance per frame against `--band` (night and cave
     floors);
   - **temporal noise:** `--pair` takes two consecutive frames of a still camera.
     `FrameBench` doesn't take such pairs yet; until it does, capture them with
     two F2 presses.

   It prints a JSON report and exits 1 on any failure. A failing change goes
   back to step 1 without spending a critic call.
4. **Critic.** This Claude Code session spawns a subagent (the Agent tool, on the
   strongest model available) whose prompt contains:
   - the look bible, the owner's taste profile and the latest owner feedback, as
     text;
   - for each scene, the **absolute paths** of the new frame, the previous best,
     and the reference frames. The references are Complementary Unbound r5.9.3
     and Sildur's Vibrant High in the same client, rendered once per client:
     `bench-m-B2*` and `bench-m-B1*` today.
   - the `check_frames.py` report.

   The subagent opens the PNGs with its Read tool, which shows it the images. It
   returns JSON: per-scene scores on the rubric below, specific defects with
   where they are in the frame, and the single most valuable next change. It
   never sees our code, only pixels and numbers, so it judges the result rather
   than the intent.

   Complementary appears only as a frame to compare against. Its code is never
   given to the critic or used to write ours (see the licence section in
   [`README.md`](README.md)).
5. **Gate.** A round goes to the owner only when all of these hold:
   - every scene scores at least 7 on every Tier A item;
   - no defect is marked severe;
   - the budgets pass, Low proxy included;
   - the mean overall score is at least 8 and higher than the last round the
     owner saw.

   Otherwise the critic's top change becomes step 1.
6. **Round.** Post to the **Shader Lab**, a static page on the project's GitHub Pages
   site: https://marionwhite.github.io/quest-forge/shaders/ (source in
   [`site/shaders/`](../../../site/shaders/)). Post whenever every Tier A item is at 7 or
   more with no severe defect. Post sooner for a genuine taste axis (golden-hour
   warmth, night darkness, haze density): two or three variants of that one axis
   instead of a single frame. The owner wants to see options and steer, so don't
   wait for an overall 8 (changed 2026-10-18). Every preference question gets example
   images: our renders, and for a pure taste question a real-world reference too.
   - **Before every round**, run
     `py -3.10 -I tools/shaders/review/fetch_feedback.py` and read
     `docs/design/shaders/feedback/rNNN.json` for r000 (the calibration round) and every
     later round. Fold the answers into the taste profile at the end of
     `look-bible.md`. Where an answer contradicts the current tuning, the owner's
     answer wins.
   - **Posting:** write a round spec, a JSON file with local image paths:
     ```json
     {"title": "Golden hour warmth", "intro": "One axis, three strengths.",
      "scenes": [{"id": "golden", "name": "Forest at golden hour",
                  "question": "Which warmth?", "notePrompt": "Too orange? Too grey?",
                  "options": [{"key": "A", "label": "Cooler", "img": "C:/qfb/client-ang/screenshots/bench-r12a-gallery.png",
                               "critic": "Neutral, a little flat.", "ms": 4.1}]}]}
     ```
     then run
     `py -3.10 -I tools/shaders/review/publish_round.py spec.json` (add `--dry-run`
     first to check). It numbers the round, turns the frames into 1920 px JPEG q90 in
     `site/shaders/rounds/rNNN/`, writes `rNNN.json`, updates `rounds/index.json`
     (closing the previous open round; r000 stays open until
     `feedback/r000.json` exists), commits only those paths and pushes to `main`,
     which deploys in a minute or two. A scene id is lower-case letters, digits and
     dashes. An option may carry `ref: {img, credit, source}`; the page shows the
     credit under the image.
   - **Reference images** are openly licensed only (CC0, public domain, CC BY,
     CC BY-SA), from Wikimedia Commons, credited as "<Artist>, <licence>, via
     Wikimedia Commons" with the file page as `source`, and listed in the round
     folder's `CREDITS.md`. Never shader-pack or game screenshots, stock photos, or
     anything without a clear licence: the site is public. Our renders are the only
     other images allowed. Never copy another pack's files.
   - **Calibration renders** for r000's text questions (direction, night, sunset,
     water, fog, bloom) are added with
     `py -3.10 -I tools/shaders/review/publish_round.py --round 0 --calibration C:\qfb\shaderdev\calibration\manifest.json`.
     The manifest is `[{question, key, label, scene, path, ms}]`; each render becomes
     the option `key` of the scene whose id is `question`, next to its reference.
   - Then send a push notification if you can.
7. **Learn.** The owner sends answers from the page with "Send feedback", which
   creates a GitHub issue titled "Shader Lab feedback: round N" (through the relay
   below when it is switched on, otherwise by opening a prefilled issue) whose body
   holds a readable summary and a fenced json block:
   `{round, scenes: {id: {choice, rating, note}}, overall}`. `choice` is an option
   key or `"neither"`; `rating` is 1-5. `fetch_feedback.py` reads those issues from
   the public API (unauthenticated, read-only) and rebuilds
   `docs/design/shaders/feedback/rNNN.json`; it is safe to re-run. Summarise the
   answers into the taste profile at the end of `look-bible.md`, and rewrite any rule
   they contradict. The next critic call sees the new profile.

   The earlier claude.ai artifact Lab (`C7LvLPJEpxazScuaLjJo3Q`, source
   `tools/shaders/review/shader-review.html`) is **retired**: it failed to connect in
   the owner's viewer. Don't post to it or read from it. Its r000 was ported to the
   Pages Lab on 2026-10-18; it had no responses.

## Feedback relay

"Send feedback" is one tap when `site/shaders/config.json` has a `relay_url`: the
page POSTs `{round, scenes, overall}` with the `X-QF-Passphrase` header to a free
Cloudflare Worker ([`tools/shaders/relay/`](../../../tools/shaders/relay/)), which
creates the issue with a fine-grained token limited to Issues on this repo. The
issue body is the same summary plus json block, so `fetch_feedback.py` needs no
change. The page asks for the passphrase once, inline, and keeps it in the
browser's localStorage. With `relay_url` empty the page opens a prefilled issue as
before, and that route stays available as "Send through GitHub instead".

- **Rotate the passphrase:** Cloudflare dashboard → the Worker → Settings →
  Variables and Secrets → edit `QF_PASSPHRASE` → Deploy, then tell the owner the new
  one. Each device gets "That passphrase didn't work", forgets the stored one and
  asks again.
- **Rotate the token** (it expires yearly): new fine-grained token, Issues read and
  write on this repo only, replace `GITHUB_TOKEN` the same way, delete the old one.
- **Switch off:** set `relay_url` to `""` and push.
- **Test** without creating issues: `node tools/shaders/relay/test/test_relay.mjs`
  (mock GitHub; the README has the `wrangler dev` variant).

Setup steps are in [`tools/shaders/relay/README.md`](../../../tools/shaders/relay/README.md).
Secrets live only in the Worker's settings, never in the repo.

## Rubric (each 0–10)

| Group | Items |
|---|---|
| Comfort (Tier A) | readable darkness · calm exposure · neutral colour · golden hour without wash · temporal stability · clear near field |
| Realism (Tier B) | sky · clouds · shadows · AO · water · block light · wetness · bloom restraint |
| Quest Forge (Tier C) | modded materials · dimension sky/fog · custom renderers |
| Defects | each with severity (minor / major / severe) and location |
| Overall | one number, against the look bible and taste profile |

Anti-patterns from the look bible are automatic deductions. Low-tier frames are
scored on Tier A and on the defect list only. Missing Tier B effects are
expected there, but broken ones are not.

## Scene set

Each scene is a fixed world, position, camera and time, so frames are
comparable across iterations:

- Plains at noon, forest at golden hour, mountain range at sunrise
- Ocean shore at noon and at sunset; underwater
- Night under a full moon and a new moon; a torch-lit cave
- Rain, then the same place 3 minutes after rain
- The block gallery (vanilla next to modded look-alikes; `FrameBench`'s
  `gallery` scene, list in `C:\qfb\gallery.txt`)
- Twilight Forest canopy, the Nether, the End, and two more modded dimensions.
  These also time the first-entry compile of each dimension folder.
- The pack's own custom renderers (jukebox, record case, speakers)
- Failure-class probes: a Legends laser, a McHeli aircraft held and flown, a
  modded particle effect, and a mob crowd. The crowd tests entity shadows and
  frame time, with `shadowEntities` on and off.

Under Angelica, check each failure-class probe with shaders off as well. Mod
geometry that is wrong without shaders is Angelica's fixed-function emulation,
not our pack. MCHeli rotors and Transformers are the known suspects.

## Phone notifications

The owner gets a push notification when a round is ready. It reaches the phone
only while this Claude Code session is connected to the Claude app with Remote
Control; otherwise it appears on the PC only.
