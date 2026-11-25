# Quest Forge client profiles: full, lite, potato

The same Quest Forge pack on an ordinary PC. You join the same server and see the
same world, mobs, items and quests. What changes is how much work your PC does
per frame: a lighter shader preset, fewer visual extras, a smaller Java heap, and
four or six cosmetic client-only mods set aside.

Install the normal Quest Forge client first (the Angelica edition of the
client-instance release, in Prism Launcher; [`docs/setup/angelica-client.md`](../../docs/setup/angelica-client.md)).
A profile goes on top of it. Do not assemble mods yourself: one differing jar
and the server refuses you at login.

## Which profile?

| Your PC | Profile | Shader preset | Play at | Java max heap |
|---|---|---|---|---|
| Gaming PC from the last ~5 years (RTX 3060 / RX 6600 or better, 16 GB+) | **full** (the normal pack) | QuestForge Medium; High or Ultra by hand on a stronger card | 1080p or 1440p | 5 GB on 16 GB, 6 GB on 32 GB |
| GTX 1060 / RX 580 class, 4–6 cores, 8–16 GB | **lite** | QuestForge Low | 1080p | 3 GB on 8 GB, 4 GB on 12–16 GB |
| Laptop or desktop on integrated graphics (Iris Xe, Vega 8), 8 GB | **potato** | QuestForge Potato | 720p | 3 GB |
| Older integrated graphics (Intel UHD 620 and older) | **potato** with `-Shaders off` | none | 720p | 3 GB |
| Graphics without OpenGL 3.3 (Intel HD 2000/3000, 2011) | the OptiFine E7 client + **lite** or **potato** (shaders are always off there) | none | 720p–1080p | 3 GB |

The profiles are defined in [`profiles/full.json`](profiles/full.json),
[`profiles/lite.json`](profiles/lite.json) and [`profiles/potato.json`](profiles/potato.json).
Every setting in them has a `why` line: what it buys and what it costs in looks.
None of them changes content.

## Install (Windows)

1. Quit Minecraft.
2. Find your game folder: in Prism, right-click the Quest Forge instance →
   **Folder**, then open `.minecraft` (the folder that holds `mods` and
   `options.txt`). For the raw-folder install it is the folder with
   `LAUNCH-ANGELICA.bat` in it.
3. Open PowerShell in this `lite-client` folder and run, with your own path:

   ```
   powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "C:\Users\YOU\AppData\Roaming\PrismLauncher\instances\Quest Forge (Angelica)\.minecraft" -Profile lite
   ```

   `-Profile potato` for integrated graphics; add `-Shaders off` on a GPU below
   the Iris Xe / Vega 8 class. Add `-WhatIf` first to see the changes without
   making them. `-Status` shows what is applied right now.
4. The script ends by printing the Java memory and arguments for this PC. In
   Prism: **Edit instance → Settings → Java**, tick Memory and Java arguments and
   paste them in.
5. Start the game.

Running the same command again changes nothing (it says so). Switching
profiles is just running it with another `-Profile`; mods set aside by the old
profile come back if the new one keeps them.

**To undo** everything: the same command with `-Revert`. Your own settings were
saved to `_qf-profile\original\` the first time, every run also keeps the
files it changed in `_qf-profile\backup-<time>\`, and set-aside mods sit in
`mods-aside\`. Nothing is deleted.

## What each profile changes

Only client-side files the server never sees. Keybinds, sound, chat, language
and resource packs are untouched.

**Video** (`options.txt`, Angelica's `config\angelica-options.json` and
`config\angelica-modules.cfg`):

| Setting | Full | Lite | Potato | What lite/potato lose |
|---|---|---|---|---|
| Render distance | 8 | 6 | 5 | Nothing on the server (it sends 6 chunks); 2–3 chunks in singleplayer |
| Graphics | Fancy | Fast | Fast | Translucent leaves, entity blob shadows, fancy rain |
| Smooth lighting (Celeritas) | on | on | **off** | Potato: flat per-block light; visible indoors |
| Particles | All | Decreased | Minimal | Thinner particle storms in fights and rain |
| Mipmap levels | 4 | 2 | 1 | A little more shimmer on distant blocks |
| Max FPS | 120 | 90 | 60 | Nothing on a 60 Hz monitor; far less heat |
| Clouds | on | on | off | Potato with shaders off: a clear sky |
| Biome colour blend | 3 blocks, fancy | 1 block, fast | none | Narrower, then hard biome borders |
| Grass block sides | overlay texture | plain | plain | The old grass side |
| Texture filtering | RGSS + anisotropic | anisotropic | none | A little shimmer on distant floors |
| Dynamic lights (held torch) | on | off | off | A held torch lights nothing until placed |
| Dropped items drawn at once | 256 | 256 | 128 | Item piles beyond 128 are not all drawn (all still exist) |
| FPS reducer (unfocused / idle) | off | 10 / 30 fps | 10 / 20 fps | Nothing while you play |

**Shader pack** (`config\shaders.properties` and `shaderpacks\QuestForge.txt`):
the pack's own QuestForge shader, at the preset the profile names. Each preset
is one option, `QF_PRESET`; the shader screen (F8 → the pack → Profile) shows
the same five.

| Preset | Keeps | Drops |
|---|---|---|
| Medium (full) | sky, shadows to 80 blocks with entities, TAA, SSR, GTAO, soft shadows, bloom | volumetrics beyond what High adds |
| Low (lite) | the physically based sky, your own shadow to 48 blocks, water, TAA, exposure, bloom, waving leaves, emissives | volumetric clouds (a 2D layer), volumetric light, SSR (sky only), GTAO (vanilla AO), puddles, soft shadows |
| Potato | sky, water, exposure, colour | the whole shadow pass, TAA (FXAA-class instead), bloom |

Budgets and the hardware they target: [`docs/design/shaders/performance-rules.md`](../../docs/design/shaders/performance-rules.md).
If the QuestForge pack is not in `shaderpacks\`, lite and potato turn shaders
**off** rather than leave a heavier pack on (`if_missing` in the JSON); full
leaves your choice alone. `-Shaders off` turns them off whatever the profile says.

**Mods set aside** (moved from `mods\` to `mods-aside\`). Every one is on the
server's `CLIENT_ONLY` list in `tools/server/build_play_server.py`, so the
server never had it and nothing in the world changes:

| Profile | Mod | What you lose |
|---|---|---|
| lite, potato | SoundFilters | Cave reverb and muffled sounds through walls |
| lite, potato | MobDismemberment, MobAmputation | Gore: limbs flying off killed mobs |
| lite, potato | CustomMenu | The branded title-screen buttons (the mural splash and menu music stay) |
| potato | JourneyMap | The minimap and the M map |
| potato | DamageIndicators | The mob health bar and damage numbers |

InventoryTweaks and Controlling stay in every profile (no measurable cost).

**Java** (printed by the script; set it in Prism):

| Installed RAM | Full | Lite | Potato |
|---|---|---|---|
| 8 GB | 3072 MiB | 3072 MiB | 3072 MiB |
| 12 GB | 4096 | 4096 | 3584 |
| 16 GB | 5120 | 4096 | 4096 |
| 32 GB+ | 6144 | 4096 | 4096 |

The whole pack holds about 1.3 GB of live heap in a world (measured; Angelica
adds about 95 MB), so 3 GB is plenty. On 8 GB never go higher: Windows, Discord
and a browser need the rest, and swapping stutters far worse than a small heap.
The Java arguments are the same for every profile and both clients (they are in
each JSON under `jvm.args`). Java must be 8 (1.8.0_2xx), 64-bit.

## The OptiFine E7 fallback client

On a GPU without OpenGL 3.3 the pack runs on the OptiFine E7 client, and
shaders are off. The same script works there: it sees `OptiFine*.jar` instead
of `angelica-*.jar` and writes `optionsof.txt` and `optionsshaders.txt`
(the `optifine` section of the JSON: Fast Render on, Smooth FPS off, Fast Math,
fast everything, dynamic lights off, shaders OFF) instead of the Angelica files.
It never leaves Fast Render on while a shader pack is selected, because that
combination breaks every shader pack on E7. `LAUNCH-LITE.bat` is the offline
launcher for that client's raw folder layout (singleplayer and LAN only).

## Mac

`apply-profile.ps1` is Windows-only. The profile JSON files are the source of
truth for the Mac's Prism tooling (the pre-Angelica `perf-preset.command` on
the Mac knows only OptiFine's files; replace its tables with these). Each
section maps to one file in the instance's `minecraft` folder:

| JSON section | File | Format |
|---|---|---|
| `options_txt` | `options.txt` | `key:value`, replace the line with the same key |
| `angelica_options` | `config/angelica-options.json` | JSON; merge the keys in, keep the rest |
| `angelica_modules` | `config/angelica-modules.cfg` | Forge config; replace `B:key=` / `I:key=` lines inside `general { }` |
| `shaders` | `config/shaders.properties` (`shaderPack=`, `enableShaders=`) and `shaderpacks/<pack>.txt` (`QF_PRESET=`) | `key=value` |
| `optifine` | `optionsof.txt`, `optionsshaders.txt` | E7 client only |
| `mods_aside` | move `mods/<prefix>*.jar` to `mods-aside/` | jar-name prefixes, case-insensitive |
| `jvm` | Prism → Edit instance → Settings → Java | heap by installed RAM; one arguments line |

Keys starting with `_` are comments; `why` is documentation. Angelica on a Mac
is untested; the Mac notes in
[`docs/setup/performance-tuning.md`](../../docs/setup/performance-tuning.md) are
E7-era.

## What to expect

- **Loading** is not faster: the same 110-odd mods load either way. 2–3 minutes
  on a 4-core CPU is normal and not a sign the game will run badly.
- **Memory.** The game process uses about 4–4.5 GB of RAM in total at a 3 GB heap.
- **Frame rate.** Measured on the dev PC per profile in
  [`docs/setup/performance-tuning.md`](../../docs/setup/performance-tuning.md).
  Nobody has measured friend-class hardware yet. If you can, tell the host your
  F3 frame rate in the same spot before and after.

## Planes and helicopters missing?

MCHeli loads its vehicles from `.minecraft\assets\mcheli` (about 357 MB), not
from its mod file. If that folder is missing, the game still starts, but you
have no aircraft items or models. It ships with the client-instance release.
Don't delete it to save space.

## Troubleshooting

- **"Mod rejections" or "missing mods" at login.** A mod the server has is
  missing. Run `-Revert`, then re-apply; the script only ever moves the mods
  listed above. If you moved something by hand, put it back.
- **The game freezes for a second every so often, and the disk light is on.**
  Windows is swapping: lower the Java maximum, or close Chrome and Discord's
  overlay. On 8 GB never go above 3 GB.
- **"Out of memory" crash.** Raise the maximum by 512 MB, but on 8 GB stay at
  or under 3.5 GB.
- **Shaders are on but look like the full pack.** Check F8: the QuestForge pack
  should show Profile LOW or POTATO. `-Status` prints the `QF_PRESET` the
  script wrote; F8 → Profile changes it in game too.
- **Black screen or flicker with a shader on the E7 client.** Fast Render is
  on with a shader pack. Run the profile again; it turns one of them off.

## Files

| File | What it is |
|---|---|
| `apply-profile.ps1` | Applies, shows or reverts a profile on one game folder (Angelica or E7) |
| `profiles/full.json`, `lite.json`, `potato.json` | The profile definitions, with a `why` per setting |
| `apply-lite.ps1` | The old command line; forwards to `apply-profile.ps1` |
| `LAUNCH-LITE.bat` | Offline launcher for the E7 client's raw folder layout (picks the heap from your RAM) |

Why each of these was chosen, and what was measured: [`docs/design/performance-plan.md`](../../docs/design/performance-plan.md)
and [`docs/setup/performance-tuning.md`](../../docs/setup/performance-tuning.md).
