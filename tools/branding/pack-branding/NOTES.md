# Quest Forge — Branding Assets, Pass 2 (v2)

Staging folder. **Nothing here has been installed into the Minecraft instance.**
Nothing was written to `%APPDATA%\.crazycraft4` while producing this pass; the
instance was read from only (for `pack.png`). No jar was opened or modified.

v1 lives at `..\cc4-branding\` and is untouched, so the two passes can be
compared side by side.

## What changed from v1, and why

v1 was essentially monochrome violet: a purple vignette with two dragon heads,
no warm counterpoint, no depth layers, and no sense of scale. It measured a mean
frame saturation dominated by a single hue family and read closer to "generic
dark purple gamer art" than to art direction.

This pass is built around three things v1 lacked:

1. **Depth layers.** Foreground (player + giant ant + smeltery) → mid-ground
   (colossal kaiju dissolving into fog) → far ground (canopy trees, End spires,
   floating islands, cooling tower, planet) receding into haze. The scene reads
   as one enormous continuous world rather than a collage of motifs.
2. **A warm/cool axis.** v1 had only cool violet. A restrained ember amber now
   anchors the bottom-left and the earthy brown of the ant sits against the cool
   violet haze. This is what makes the palette read as painterly rather than as
   a single hue ramp.
3. **Value contrast instead of saturation.** All drama comes from a luminous sky
   against near-black silhouettes. Mean saturation of the menu background across
   all pixels brighter than luminance 70 is **0.19** — genuinely desaturated.

## Palette actually used

### Anchor (carried over from the established scheme)

| Role | Hex | Notes |
| --- | --- | --- |
| Background / darkest | `#14101C` | Exact value of the emblem's flat margin |
| Accent / highlight | `#C9A2FF` | Used **sparingly**, as light accent only |
| Border / mid-tone | `#4A3A6B` | |
| Text / lightest | `#E8E4F0` | |

### Supporting tones introduced this pass

These were added deliberately, because a purely monochrome violet image reads
cheap — which is exactly what the brief argued against.

| Role | Measured value | Why it is there |
| --- | --- | --- |
| Luminous dusk sky / god rays | `#7C6F8A` avg, peak `#FCF4FF` | hue 269, sat 0.11. The bright field the kaiju is silhouetted against. This is the single source of the image's drama. |
| Upper atmospheric haze | `#1A1621` | hue 262. First depth layer behind the kaiju. |
| Deep fog / button field | `#0D0A13` | hue 260, luminance 11. The quiet centre band. |
| Molten ember / smeltery | peak `#FFCD71`, body `#351609` | hue 17–39. Warm counterpoint for the Tinkers' smeltery; thematically the *Forge* in Quest Forge. |
| Earthy ant brown | peak `#FFD07B` over brown chitin | hue 39. Warm mid-tone that keeps the ant from reading as another violet shape. |
| Near-black canopy silhouette | `#030306` | The far depth layer; almost pure black so the haze in front of it reads. |
| Forged iron (emblem) | `#191719`–`#221F22` | Neutral grey, hue-flat, so the ember and lavender accents do the colour work. |
| Lavender rim-light (emblem) | `#D7D2D9` | hue 283. The `#C9A2FF` direction, used only on top bevels. |

**Deliberate hue correction.** The first usable generation put the sky glow at
70% in the **magenta** band (hue 300–330°) — desaturated, but still the exact
hue family the brief warned against. A hue-aware grade rotated that rose/magenta
range to **hue 268°** (the hue of `#C9A2FF` is 265°) while protecting the true
ember band (hue 12–62°) from both rotation and desaturation. Post-grade the sky
is 51% blue (240–270°) and 40% violet (270–300°), with magenta and rose gone
entirely.

## Asset 1 — Loading screen emblem

- **File:** `resources/assets/minecraft/textures/gui/title/mojang.png`
- **Dimensions:** 256 × 256
- **Format:** PNG, 32-bit ARGB, **fully opaque** — verified alpha = 255 on all
  65,536 pixels
- **Size on disk:** 74,768 bytes
- **Install to:** `<instance root>/resources/assets/minecraft/textures/gui/title/mojang.png`

**Concept.** The forge and the monster are fused rather than chosen between: a
horned beast skull whose lower jaw and base morph into a blacksmith's anvil, the
whole thing forged from chamfered blocky iron plates, with molten light bleeding
through the cracks and a single amber core burning in the eye socket, ringed by a
heavy iron band. Geometry is faceted and cubic so it stays Minecraft-legible.

**Production.** Generated at 1024 × 1024. The generated margin came in at
`#0D0917`–`#0E0D1B`, not the required value, so:

1. A flood fill from every border pixel (tolerance 12 per channel) claimed the
   connected margin — 394,330 px, 37.6% of the frame — and rewrote it to exactly
   `#14101C`. Flood fill rather than a global colour match, so the emblem's own
   dark interior crevices were left alone.
2. A 3-pixel feather band around the flood was blended toward the target so no
   hard halo formed at the mark's edge.
3. The mark was scaled to 92% and re-centred on a clean `#14101C` field, giving
   the logo real breathing room (v1's ring nearly touched the texture edge).
4. Downscaled to 256 × 256 with `InterpolationMode.HighQualityBicubic`.
5. Bicubic ringing left the corners at `#15101C` — one level off in red, enough
   to seam. A final snap pass (tolerance 3) forced them to exact.

**Verified after downscaling:** all four corners and both mid-edges read exactly
`#14101C`, and the entire outer 8-pixel border is exact on 7,936/7,936 pixels.
There is no visible seam against Forge's splash field.

**Legibility.** Checked at 128, 96, 64 and 32 px. It holds cleanly to 64 px; at
32 px it reduces to a horned mass with an amber core, which still reads. Forge
draws it well above that.

## `splash.properties` — rotate recommendation

**Recommendation: `rotate=false`. For this emblem it is a requirement, not a
taste call.**

v1's mark was radially symmetric with spikes distributed all the way around, so
it survived rotation and the choice was cosmetic. This one does not. It has a
hard vertical axis: horns up, anvil down, and molten light that pours and pools
downward. Gravity is baked into the design. Rotating it would look broken rather
than novel — an upside-down anvil with its lava running upward. Set
`rotate=false`.

## Asset 2 — Main menu background

- **File:** `resourcepack/assets/custommenu/background.jpg`
- **Dimensions:** 1920 × 1080 (16:9)
- **Format:** JPEG, quality 93
- **Size on disk:** 163,806 bytes
- **Install to:** `<instance root>/resourcepacks/<packname>/assets/custommenu/background.jpg`
- The `.jpg` extension is compiled into `CustomMenu.jar` and **cannot** be changed.

**Aspect ratio.** The v1 pitfall repeated: a 16:9 request returned
**1536 × 1024, which is 3:2.** Nothing was stretched — stretching would turn
voxel cubes into rectangles and destroy the Minecraft read. Instead the frame was
**centre-cropped to 1536 × 864** (the exact 16:9 height for that width) by
trimming **40 px off the top and 120 px off the bottom**, then scaled to
1920 × 1080. The crop was biased downward on purpose: trimming evenly would have
clipped the kaiju's horns, and trimming from the bottom alone would have cut the
tiny player figure, which is the scale gag and cannot be lost. 40/120 keeps the
horns, the planet, the ant's legs and the player all inside the frame.

**Keeping the centre quiet.** Six buttons are drawn over the middle. Measured
over the button field (x 360–1560, y 340–810):

| Metric | v1 | v2 |
| --- | --- | --- |
| Mean luminance | ~12 / 255 | **11.69 / 255** |
| Standard deviation | ~1.2 | **1.15** |
| Peak luminance | not reported | **18 / 255** |

Flatter and darker than v1 on every measure, while the rest of the frame is far
more dramatic — full-frame mean is 17.08 with a peak of 239, so the image holds a
wide value range instead of being uniformly dark.

Getting there took three attempts, and the failures are worth recording:

- **Attempt 1 — rectangular mask.** Hit the numbers (mean 11.23, sd 1.43) but
  left a visibly rectangular dark box: the bottom feather was only 32 px and cut
  a hard horizontal line across the water.
- **Attempt 2 — global gamma 1.18.** No artifacts, but crushing the whole frame
  flattened it into uniform murk. The kaiju lost its silhouette and the image
  stopped being dramatic. Full-frame mean fell to 13.09. Rejected.
- **Attempt 3 — warmth-protected local flatten (shipped).** No global gamma, so
  the sky and foreground keep full punch. A smooth separable mask (150 px top
  feather, 190 px bottom, 200 px sides) blends the centre toward `#0D0913`, but
  the blend strength is modulated by hue: cool fog is crushed hard (keep 0.10)
  while true ember hues are largely preserved (keep 0.80). That is why the
  smeltery glow, the rail line and the ant survive at full warmth while the fog
  beside them goes flat. The row-luminance profile is monotonic and smooth
  (56 → 48 → 17 → 13 → 11 → 11 → 11 → 14 → 13), with no step anywhere.

**Text check: none.** The frame was inspected at full size and all four corners
were re-examined at 3× magnification. No lettering, watermark, signature or UI
element anywhere.

### Pack elements included

- **OreSpawn** — the giant brown ant, foreground left, with a tiny blocky player
  standing beside it holding a lantern. This is the comedy beat and the scale
  gag: the player is dwarfed by the ant, and the ant is dwarfed in turn by the
  kaiju. Kept small and supporting, not the hero.
- **OreSpawn / Mobzilla scale** — the colossal horned kaiju rising out of the
  fog, head and shoulders above the mist and legs swallowed by it so it appears
  to have no bottom. Two further creature silhouettes sit fainter in the haze
  behind it.
- **Twilight Forest** — the impossibly tall dark canopy trees framing both edges,
  trunks running out of frame.
- **Hardcore Ender Expansion** — pale spires and small floating voxel islands
  with waterfalls, receding on both sides.
- **Railcraft** — the iron rail line curving through the bottom-left foreground
  with a steam plume drifting up.
- **Tinkers' Construct** — the smeltery pouring molten metal down a channel,
  bottom-left. Thematically the centrepiece given the pack's name.
- **HBM / nuclear** — a slender cooling tower silhouette on the far right
  horizon, small and faint.
- **Galacticraft** — a large ringed planet high in the sky.
- **Path-traced shader read** — volumetric god rays through fog, ray-traced
  water reflection bottom-right, soft global illumination with warm bounce light
  off the smeltery onto nearby stone, ambient occlusion in the block crevices,
  restrained bloom, layered depth haze.

### Pack elements deliberately left out

Composition discipline was prioritised over coverage, per the brief.

- **Thaumcraft / Witchery arcane motes, rune-glow, standing stones.** Cut
  deliberately. Glowing motes are the single fastest route to the neon look the
  brief argued against, and scattering them through the centre band would have
  destroyed the flatness the buttons need.
- **ICBM / MCHeli missile contrail or helicopter speck.** Cut. The scale
  reference is already carried by the player-to-ant-to-kaiju chain, which is
  clearer. A contrail in the sky would also have competed with the god rays.
- **Twilight Forest Lich tower and firefly motes.** Cut for the same reasons —
  the left and right thirds were already carrying trees, spires, floating
  islands and a cooling tower, and one more vertical silhouette would have
  turned a landscape into a checklist.
- **A second colossal monster in the foreground.** Considered and rejected. One
  hero kaiju reads as enormous; two read as a poster.

## Asset 3 — Wordmark

- **File:** `wordmark/questforge-wordmark.png`
- **Dimensions:** 1024 × 256
- **Format:** PNG, 32-bit ARGB with real transparency
- **Size on disk:** 462,710 bytes
- **Install to:** not a game asset. This is for CurseForge / Discord / launcher
  art. It is not referenced by the pack.

"QUEST FORGE" set as heavy condensed slab capitals in forged blackened iron,
with chamfered faceted bevels, a thin molten amber edge-light along the bottom of
each letter and a pale lavender rim on the top bevels. Spelling was verified
correct on the first generation; no regeneration was needed.

**Transparency.** The generator produced the type on a flat `#14101C` field
rather than on alpha. Keying by luminance alone would have failed — some letter
pixels are as dark as luminance 7, darker than the background's 12–13. What
separates them cleanly is hue: the background field is uniformly violet-tinted
(B − G ≈ +10 to +12) while every letter pixel is neutral or warm (B − G ≤ +3).
So alpha was derived from **violet-tint gated by darkness**: a pixel is
background only if it is both violet *and* dark. That preserves the dark iron and
the near-white lavender rim-lights, which a luminance key would have erased.

Cropping and scaling were done **before** keying, on opaque RGB, so there is no
alpha-interpolation fringing at the letter edges.

Result: 42.5% fully transparent, 50.8% fully opaque, 6.7% partial (the
antialiased edges and the letters' soft drop shadow, which was kept — it reads as
depth over dark art). Verified that **zero** pixels on any outer edge carry alpha
above 8, so no glyph is clipped; margins are 23/19 px left/right and 26/22 px
top/bottom. Checked composited over both a checkerboard and the actual menu
background.

## Resource pack skeleton

- `resourcepack/pack.mcmeta` — `pack_format: 1` (correct for MC 1.7.10), with a
  Quest Forge description. Written as UTF-8 **without BOM** via
  `[System.IO.File]::WriteAllText` with `New-Object System.Text.UTF8Encoding($false)`.
  Verified: first four bytes are `7B 0A 20 20`, not `EF BB BF`.
  Do **not** rewrite this file with PowerShell `Set-Content` — its default
  encoding adds a BOM and has corrupted files in this project before.
- `resourcepack/pack.png` — 256 × 256, 153,849 bytes, copied read-only out of
  `%APPDATA%\.crazycraft4\pack.png`. The new assets were designed as siblings to
  it, which is why the violet anchor was kept.

## Still missing

### CustomMenu button textures

Twelve files, all PNG **with alpha**, same palette, no lettering. Each button
needs a base and a hover (`...over`) variant. These belong alongside
`background.jpg` in `assets/custommenu/`.

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

Design note for whoever builds these: the background's button field now sits at
luminance ~12 with a standard deviation of ~1.15, so the buttons can be very
subtle — a forged-iron plate with a thin `#4A3A6B` border and a faint ember
under-glow on the `over` state would fit the emblem and cost almost no contrast.

### Window / taskbar icons

- `icon16.png` — 16 × 16
- `icon32.png` — 32 × 32
- `icon64.png` — 64 × 64

These are **not** resource pack files. They must be placed **inside
`CustomMenu.jar`**, which means repacking the jar. No jar was modified as part of
this staging step. The emblem is a good source for these, but at 16 px it will
need to be redrawn by hand rather than downscaled — at that size only the horns
and the amber core survive.

## Scratch

`_work/` holds intermediates: the 1024 × 1024 palette-corrected emblem master,
the rejected background grades (`bg_c_graded`, `bg_v2`, `bg_v3`), the shipped
grade (`bg_v4`), corner crops used for the text check, the emblem size-legibility
sheet, and the wordmark composites. None of it is part of either deliverable
folder and none of it should be installed.