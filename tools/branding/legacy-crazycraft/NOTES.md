# CC4 Derivative — Branding Assets

Staging folder. **Nothing here has been installed into the Minecraft instance.**
Installation into `%APPDATA%\.crazycraft4` is a separate, later step.

## Palette (locked)

Every asset must read as part of one continuous visual system.

| Role | Hex | RGB |
| --- | --- | --- |
| Background / darkest | `#14101C` | 20, 16, 28 |
| Accent / highlight | `#C9A2FF` | 201, 162, 255 |
| Border / mid-tone | `#4A3A6B` | 74, 58, 107 |
| Text / lightest | `#E8E4F0` | 232, 228, 240 |

Theme: dark violet kaiju/monster chaos — ominous but fun, not grim dark-fantasy.
No text or lettering appears in any branding image; the pack has no finalised name yet.

## Completed assets

### 1. Loading screen emblem

- **File:** `resources/assets/minecraft/textures/gui/title/mojang.png`
- **Dimensions:** 256 × 256
- **Format:** PNG, 32-bit RGBA, **fully opaque** (alpha = 255 on all 65,536 pixels)
- **Install to:** `<instance root>/resources/assets/minecraft/textures/gui/title/mojang.png`
- Generated at 1024 × 1024, downscaled to 256 × 256 with
  `System.Drawing` + `InterpolationMode.HighQualityBicubic`.
- The flat margin was remapped to exactly `#14101C` so the texture blends
  seamlessly into the colour Forge clears its splash screen to. Without this the
  square edge of the texture was faintly visible against the splash background.
- Content: centred, mirror-symmetric horned kaiju head with a single glowing
  central eye, ringed by evenly distributed radiating claws/spikes.

### 2. Main menu background

- **File:** `resourcepack/assets/custommenu/background.jpg`
- **Dimensions:** 1920 × 1080 (16:9)
- **Format:** JPEG, quality 92
- **Install to:** `<instance root>/resourcepacks/<packname>/assets/custommenu/background.jpg`
  (or wherever the active CustomMenu resource pack lives)
- The `.jpg` extension is compiled into CustomMenu.jar and **cannot** be changed.
- Generated at 1536 × 1024 (the generator returned 3:2 despite a 16:9 request),
  centre-cropped to 1536 × 864 with the crop biased toward the bottom
  (35 px off the top, 125 px off the bottom) to avoid clipping the kaiju heads in
  the upper corners, then resized to 1920 × 1080. Cropping rather than stretching
  keeps the voxel cubes square.
- Composition is a vignette: detail is held at the left/right edges, bottom
  horizon and top corners. Measured mean luminance in the central button zone is
  ~12/255 with a standard deviation of ~1.2, i.e. essentially flat haze, so the
  six menu buttons and their light text stay readable.

### 3. Resource pack skeleton

- `resourcepack/pack.mcmeta` — `pack_format: 1` (correct for MC 1.7.10),
  written as UTF-8 **without BOM** via
  `[System.IO.File]::WriteAllText` + `New-Object System.Text.UTF8Encoding($false)`.
  Verified: first bytes are `7B 0A 20`, not `EF BB BF`.
  Do **not** rewrite this file with PowerShell `Set-Content` — the default
  encoding adds a BOM and has corrupted files in this project before.
- `resourcepack/pack.png` — 256 × 256, copied read-only out of the existing
  instance (`%APPDATA%\.crazycraft4\pack.png`). Already on-palette and kaiju-themed;
  the new assets were designed as siblings to it.

## Forge splash: `rotate` setting

`splash.properties` currently has `rotate=true`.

**Recommendation: `rotate=true` is safe, but `rotate=false` is the better choice.**

The emblem was deliberately built to survive rotation — it is mirror-symmetric and
its radiating spikes are distributed all the way around, so it has no strong "up"
direction and will not look upside-down at any angle. However, it is a *face*: a
head with an eye and a fanged jaw. Even with balanced geometry, a slowly spinning
monster face reads as a novelty spinner rather than as a logo, and the jaw/horn
asymmetry (horns up, fangs down) becomes noticeable at 90° and 180°.

Setting `rotate=false` presents it as a static sigil, which suits a branding mark
better. Either value is visually acceptable; this is a taste call, not a bug.

## Still missing

### CustomMenu button textures

All PNG **with alpha** (transparency required), same palette, no lettering.
Each button needs a base and a hover (`...over`) variant.

**600 × 90:**

| Base | Hover |
| --- | --- |
| `single.png` | `singleover.png` |
| `multiplayer.png` | `multiplayerover.png` |
| `mods.png` | `modsover.png` |
| `publicserver.png` | `publicserverover.png` |

**450 × 77:**

| Base | Hover |
| --- | --- |
| `options.png` | `optionsover.png` |
| `quit.png` | `quitover.png` |

Twelve files total. These belong alongside `background.jpg` in
`assets/custommenu/`.

### Window/taskbar icons

- `icon16.png` — 16 × 16
- `icon32.png` — 32 × 32
- `icon64.png` — 64 × 64

These are **not** resource pack files — they must be placed **inside
`CustomMenu.jar`**, which means repacking the jar. No jar was modified as part of
this staging step.

## Scratch

`_work/` holds the palette-corrected 1024 × 1024 emblem master, kept in case the
emblem needs to be re-exported at another size. It is not part of either
deliverable folder and should not be installed.
