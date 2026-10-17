# Quest Forge Lite

A lighter way to run the same Quest Forge pack on an ordinary PC. You join the
same server and see the same world, mobs, items and quests. What changes is how
much work your PC does per frame: fewer visual extras, no shader pack, a smaller
Java heap, and four or six cosmetic client mods turned off.

Install the normal Quest Forge client first (the client-instance release, in
Prism Launcher). Lite goes on top of it. Do not assemble mods yourself: one
differing jar and the server refuses you at login.

## Which profile?

| Your PC | Profile | Java memory (max) |
|---|---|---|
| Gaming PC from the last ~5 years, 16 GB+ | none: play the normal pack, shaders optional | 5–6 GB |
| GTX 1060 / RX 580 class, 4–6 cores, 8–16 GB | **lite** | 3 GB on 8 GB RAM, 4 GB on 12–16 GB |
| Laptop / integrated graphics, 8 GB | **potato** | 3 GB |

## Install (Windows)

1. Quit Minecraft.
2. Find your game folder: in Prism, right-click the Quest Forge instance →
   **Folder**, then open `.minecraft` (the folder that holds `mods` and
   `options.txt`).
3. Open PowerShell in this `lite-client` folder and run, with your own path:

   ```
   powershell -ExecutionPolicy Bypass -File apply-lite.ps1 -Instance "C:\Users\YOU\AppData\Roaming\PrismLauncher\instances\Quest Forge\.minecraft"
   ```

   For integrated graphics add `-Tier potato`. Add `-WhatIf` first if you want
   to see the changes without making them.
4. In Prism: **Edit instance → Settings → Java**. Set the memory from the table
   above and paste the Java arguments from [`jvm-args.txt`](jvm-args.txt).
5. Start the game.

**To undo** everything: run the same command with `-Undo`. Your original
settings were saved to `_lite-backup\` the first time, and removed mods sit in
`mods-lite-removed\`. Nothing is deleted.

## What it changes

**Mods moved out of `mods\`** ([`client-only-drop.txt`](client-only-drop.txt)).
Only mods the server does not have, so nothing in the game world changes:

| Profile | Mod | What you lose |
|---|---|---|
| lite | SoundFilters | Cave reverb and muffled sounds through walls |
| lite | MobDismemberment, MobAmputation | Gore: limbs flying off killed mobs |
| lite | CustomMenu | The branded title-screen buttons (the splash and menu music stay) |
| potato | JourneyMap | The minimap and the M map |
| potato | DamageIndicators | The mob health bar at the top of the screen |

**Video settings** (only these keys; your controls, sound and chat are untouched):

| Setting | Normal pack | Lite | Potato |
|---|---|---|---|
| Shader pack | Sildur's Vibrant High | Off | Off |
| Render distance | 8 | 6 (= the server's) | 5 |
| Graphics | Fancy | Fast (opaque leaves) | Fast |
| Smooth lighting | Maximum | Minimum | Off |
| Particles | All | Decreased | Minimal |
| Mipmap levels | 4 | 2 | 0 |
| Max FPS | Unlimited | 90 | 60 |
| Fast Render (OptiFine) | Off | On | On |
| Smooth FPS (OptiFine) | On | Off | Off |
| Dynamic lights | Fast | Off | Off |
| Clouds | Fancy | Fast | Off |
| Dropped items, rain, water, trees | Fancy | Fast | Fast |
| Smooth biomes | On | Off | Off |

Render distance 6 is not a loss on the server: the server only sends 6 chunks
around you, so 8 draws nothing extra and just shows the world's hard edge
past the fog.

## If you want a shader on a GTX 1060-class card

Pick **Sildur's Enhanced Default** (already in `shaderpacks\`) under Options →
Video Settings → Shaders, and set Shadow Resolution to 0.5x. Then go to
Video Settings → Other and turn **Fast Render OFF**. Fast Render breaks every
shader pack in this OptiFine version: the screen goes black or flickers. Never
use Vibrant on a lite PC.

## What to expect

- **Memory.** The whole pack holds about 1.3 GB of live Java heap in a
  world (measured), so 3 GB is plenty. The game process uses about 4–4.5 GB of
  RAM in total.
- **Loading** is not faster: the same 140 mods load either way.
- **Frame rate.** Most of the gain comes from having no shader: 2–3× on the
  benchmark PC. The rest of the lite settings add an estimated 20–40% on a
  4–6 core CPU. Nobody has measured it on friend-class hardware yet. If you
  can, tell the host your F3 frame rate in the same spot before and after.

## Planes and helicopters missing?

MCHeli loads its vehicles from `.minecraft\assets\mcheli` (about 357 MB), not
from its mod file. If that folder is missing, the game still starts, but you
have no aircraft items or models. It ships with the client-instance release. Don't delete it to save space.

## Angelica (only if the host switches the pack to it)

The pack might move to a newer renderer, Angelica, later. Nothing here uses it
yet. If it does, this lite profile gets replaced:

- `optionsof.txt` stops mattering. OptiFine, FastCraft and BetterFps are
  disabled.
- Render distance 6, Fast graphics, fewer particles, the dropped mods and the
  3 GB heap stay the same.
- Intel HD 2000/3000 graphics (2011) cannot run Angelica. Those PCs keep this
  OptiFine lite profile.

## Troubleshooting

- **"Mod rejections" or "missing mods" at login.** A mod the server has is
  missing. Run `-Undo`, then re-apply; the script only ever moves the mods
  listed above. If you moved something by hand, put it back.
- **The game freezes for a second every so often, and the disk light is on.**
  Windows is swapping: lower the Java maximum, or close Chrome and Discord's
  overlay. On 8 GB never go above 3 GB.
- **"Out of memory" crash.** Raise the maximum by 512 MB, but on 8 GB stay at
  or under 3.5 GB.
- **Black screen or flicker with a shader.** Fast Render is on. Turn it off.
- **It still loads slowly.** Loading takes 1.5–4 minutes on any PC: the pack
  loads 140 mods every time and nothing here changes that. Loading is a
  one-off; it is not a sign the game will run badly.

## Mac

`apply-lite.ps1` is Windows-only. On a Mac use `perf-preset.command low`
(see `docs/setup/performance-tuning.md`) and set the memory from the table
above. The settings in `profiles/lite/` can also be copied by hand into
`options.txt`, `optionsof.txt` and `optionsshaders.txt`: each line replaces the
line with the same name.

## Files

| File | What it is |
|---|---|
| `apply-lite.ps1` | Applies or undoes a profile on one game folder |
| `profiles/lite/`, `profiles/potato/` | The setting overrides (potato goes on top of lite) |
| `client-only-drop.txt` | The mods each profile moves out, and why |
| `jvm-args.txt` | Prism memory table and Java arguments |
| `LAUNCH-LITE.bat` | Offline launcher for the pack's own folder layout (singleplayer/LAN only; picks the heap from your RAM) |

Why each of these was chosen, and what was measured: [`docs/design/performance-plan.md`](../../docs/design/performance-plan.md).
