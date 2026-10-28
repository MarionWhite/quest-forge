# site-r8-skins-pilot (checkpoint, started 2026-10-27, Mac)

Agent: texture-dev (opus). Owns: `site/graves/tex/mobs/*` (new), the skin-override hook it needs in
`site/lib/mc/mobs.js` (additive), its own tools under `tools/textures/mobs/`. Research: `site-r8-skins.md`.

## Owner's words (2026-10-27, round 8)
- "use the mob skins from the Patrix 32x texture packs for the animations to make the mobs scarier unless there is
  an even more terrifying texture pack for them. Leave the actual environmental blocks the same vanilla texture,
  but lets make these mobs scary as fuck."

## Why a pilot of our own
Patrix is All Rights Reserved, and its scary mobs rely on FreshLX's Fresh Animations models (a second rights holder,
and not 1.7.10 models). The openly licensed packs found are amateur and cover 3 mobs. So: paint our own 32x horror
skins on the 1.7.10 vanilla UV layouts. Study Patrix and other horror packs for ideas (palette, rot, eyes, how
detail reads at 32x); never copy, trace or recolour them. Faithful 32x as a base is fine if its licence allows a
modified version to ship with credit: check and quote it first.

## Done means (pilot: Zombie and Spider only)
- [ ] Both skins at 32x (2x the vanilla sheet), true to the mob's silhouette and colours so it still reads as that
  Minecraft mob, and frightening: rot, wounds, sunken or glowing eyes, wet dark tones. The spider's eyes layer too.
- [ ] A Krypt-only override: scares and mood mobs on the Krypt page use `site/graves/tex/mobs/<key>.png` when it
  exists; the Lucky Block page keeps vanilla. No change to how the scares play.
- [ ] Review renders: vanilla beside new, under the Krypt's torch light, at the scare's real distance (face-close)
  and at 6 blocks, front and three-quarter; one sheet. Use the ?dump=1 hook; one Chrome at a time.
- [ ] If code cannot reach the quality, say so plainly and propose the path (as your agent file says).
- [ ] Commit your own paths, journal line in `ops/journal/site.md`, report in five lines with the sheet path.

## Progress
(write after every step)
- 2026-10-27 step 1 (read): mobs.js builds UVs from the model's texW/texH, so a 2x sheet (zombie 128x128, spider
  and eyes 128x64) drops in with no geometry change. Krypt makeMob callers: scares/rig.js, mood/events-visual.js,
  dress.js, dressx.js (all one ES module graph from graves/app.js). Plan: mobs.js gets an additive
  `setSkinOverrides({Key: url})` read by buildVanilla; a Krypt-only module `site/graves/tex/mobs/skins.js` calls it
  (skipped under `?vanillaskins` for A/B). Review: `graves/?scare=Zombie&scareat=lunge&dump=1` (+`&scarecam=x,y,z,yaw,pitch`
  local) via tools/site/dump_frames.py. Pillow: /usr/local/bin/python3.11. Scratch: scratchpad/r8/skins-pilot/.
- step 2 (design): studied Patrix's Modrinth gallery (scratch `study_dl/mobs_crop.png`, study only): banded tarantula
  legs, value-rich hair, red eye cluster; zombie dark sunken features. Our design: zombie keeps green skin / teal shirt /
  indigo pants but rotted (sunken sockets with one milky eye, nose cavity, lipless teeth, forehead gash to bone, torn
  shirt over ribs, ragged sleeves, clawed hands on the arm-end face, which faces the camera when the arms are raised).
  No zombie eye glow (r7 zombie scare says "no lit eyes"; FNAF was judged overdone). Spider: dark hairy tarantula,
  carapace grooves, abdomen chevrons, leg joint rings symmetric (legs share one unmirrored strip), 8 eyes with side
  wraps, big fangs; glow on the existing additive eyes layer. Painted from scratch, no pack pixels as a base.
  Painter: tools/textures/mobs/paint_mobs.py (python3.11 -I).

## CHANGE OF PLAN (2026-10-27, from the owner via the coordinator)
Owner's words: "This isn't going to be publicly distributed or used to make money. Just use it for the skins."
So: use Patrix's mob skins, but only as a LOCAL layer. The repo is PUBLIC and pushing main deploys GitHub Pages, so
no Patrix pixel may ever be committed, pushed or deployed.
1. Pause the painting. Commit the painter script and painted PNGs (ours); mark painting paused here.
2. Add `site/graves/tex/mobs-local/` to .gitignore; prove with `git check-ignore -v`; read .github/workflows/pages.yml
   and confirm ignored files cannot reach the deploy.
3. Get Patrix 32x from Modrinth (api.modrinth.com/v2/project/patrix-32x/version) into its own new empty scratch dir;
   untrusted, read with python3.11 -I. Pick the version(s) whose entity textures fit 1.7.10 layouts (zombie_pigman.png
   is pre-1.16; the zombified piglin model differs). Different mobs from different versions if needed.
4. `tools/textures/mobs/import_patrix.py <zip>...`: extract the 14 Krypt mobs (zombie, skeleton, wither skeleton,
   spider, cave spider, creeper, enderman, witch, slime, magma cube, blaze, ghast, silverfish, zombie pigman) plus eye
   and emissive layers, convert layouts to 1.7.10 where they differ, write ONLY into the ignored folder with
   index.json; refuse any output path git does not ignore.
5. Krypt-only loading: skins.js uses `tex/mobs-local/` if its index.json exists (404 = skip silently), then our own
   `tex/mobs/`, then vanilla. `?vanillaskins` = A/B. Lucky stays vanilla.
6. Review sheet: vanilla beside Patrix for all 14, Krypt torchlight, scare distance and 6 blocks. Flag mobs whose
   Patrix texture expects Fresh Animations geometry and looks wrong on the 1.7.10 model.
7. Commit only code (.gitignore, skins.js, mobs.js hook, importer). Before each commit `git diff --cached --stat`, no
   Patrix file staged. Report in five lines: sheet path, the owner's re-import command, mobs that look wrong.

### Painting: PAUSED (2026-10-27)
State at pause: tools/textures/mobs/paint_mobs.py writes site/graves/tex/mobs/{zombie,spider,spider_eyes}.png.
Zombie face reviewed in situ (scare seed 2, `fake+400`): reads as a rotting zombie; last edits (angled brows, bone
teeth, darker gums) not yet re-rendered. Spider not yet reviewed in the Krypt. Previews: scratch r8/skins-pilot/p1-p4,
renders r1, r2. Review hook: site/graves/tex/mobs/review.js (`?dump=1&skinreview=<Mob>&dist=&ang=&aimy=`).
Note for the scare agent: Zombie scare seeds 1/3/4 (walk-up variant) show one socket from centimetres away at every
mark (fake, lunge, kill-600, kill); fnaf.js jaw pegs are unlit MeshBasic and glow in the dark.
- step P1 done: painter + painted PNGs committed eefc82c (painting paused).
- step P2 done: .gitignore line 135 `site/graves/tex/mobs-local/`; `git check-ignore -v` matches the folder, index.json
  and zombie.png; own tex/mobs/ is not ignored. pages.yml deploys from actions/checkout (committed files only) and
  copies site/graves, so an ignored, never-committed folder cannot reach Pages; no other route publishes site/
  (the only wrangler config is the shader relay). .gitignore not yet committed.
- step P3 done: Modrinth has Patrix only for 1.20+ (33 versions); took #92 (26.3), sha512-verified, in scratch
  dl_patrix_32x_basic/ (+ addon, models: no entity textures there). Entities are 2x (ghast 4x) on vanilla UV sizes;
  OptiFine CEM .jem for most mobs (textureSize = vanilla). No _e files; LabPBR _s alpha = emission (blaze, magma cube,
  creeper, wither skeleton used as glow; enderman's is skipped, it has an eyes layer). Pigman only as zombified_piglin.
- step P4 done: tools/textures/mobs/import_patrix.py (refuses non-ignored outputs: tested on tex/mobs and on a path
  outside the repo); 14/14 written to site/graves/tex/mobs-local/ with index.json.
- step P5 code done (uncommitted): mobs.js hook accepts {layers, glow}; skins.js = local layer (only when served
  locally: localhost/LAN/.local/dotless host; fetch, 404 skips) > own painted (gated OWN_LIVE=false, ?ownskins) >
  vanilla; ?vanillaskins = all off. index.html has the skins.js tag (another agent added a footer link in the same
  file: stage only my hunk).
- next: review sheet for 14 mobs (vanilla vs Patrix, face-close and 6 blocks), flag FA misfits, commit code.
- step P6 done: review sheet /Users/suaz/Desktop/QuestForge/site/graves/tex/mobs-local/review/sheet.png (ignored,
  local only; tools/textures/mobs/review_sheet.py). Fit: Zombie, Skeleton, Wither Skeleton, Spider, Cave Spider,
  Creeper, Enderman, Ghast (pale sleeping face, a seam down the middle), Silverfish, Pigman (converted; ears lost).
  Wrong: Magma Cube (CEM slices, falls apart), Slime (no face). Partly: Blaze (crown for a face), Witch (hair strands
  on the arms). Importer leaves Slime and Magma Cube out unless --all (they stay vanilla). Real scares checked: the
  zombie (seed 2) and spider scares wear the local layer (the async index load lands in time).
- step P7 done: code committed cf0d960 (.gitignore, mobs.js hook, skins.js, review.js, importer, review_sheet);
  `git diff --cached --stat` showed 7 code files, no PNG, nothing from mobs-local; history has no mobs-local path.
  Not pushed.
- Re-import (owner): from the repo root, `/usr/local/bin/python3.11 -I tools/textures/mobs/import_patrix.py <path to
  Patrix_<ver>_32x_basic.zip>` (PC: `py -3.10 -I ...`, needs Pillow), then reload http://127.0.0.1:8000/graves/.
  This session's zip: scratch r8/skins-pilot/dl_patrix_32x_basic/Patrix_26.3_32x_basic.zip (sha512 checked).
## Status: DONE (Patrix local layer). Painting paused; own skins gated off the public site (OWN_LIVE=false).
