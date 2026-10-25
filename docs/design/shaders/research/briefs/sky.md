# Brief: sky

Day and night, sun and moon, stars, fog and aerial perspective. Read with
[`README.md`](README.md). Clouds have their own brief.

## 1. What the owner asked for

- r000 sunset (C naturalistic, 4/5): "I intend to design some sky effects within the shaders
  pack." night (B, 3/5): "I want the night sky to stick out and be incredibly beautiful."
- r001 golden (B, 4/5): "I like how the light hits the blocks in the background."
- r002 gold-sky (B, 5/5): "Maybe more gold, and definitely try some amber effects on the
  leaves." night-sky (A, 5/5): "The Milky Way effect that you have come up with is not good ...
  I am definitely open to effects with the sky, but the execution on these is shit."
  biome-hills: "crisp enough, but this scene still looks very bland."
- r003 golden (B, 5/5): "The horizon band is pretty flat." night-new (B, 5/5): "The sky looks
  fuller in this one and has a deep rich darkness."
- r004 night-new: "give the sky a little more texture and beauty ... a rotation of skies."
  hills (B, 3/5): "I kind of like the haze off to the left where the elevation drops, but I
  don't like that it washes out the color of everything at the same elevation as the camera."
- r005 hills (A, 5/5): "way better." night-sky (A, 4/5): "Deep clear is already a success ...
  Air glow is underwhelming and the milky way looks kinda hand drawn and low quality."
  sunset-sky (A, 3/5): "The clouds, the water, and the sun all still need improvements."
- r006 sunset-sky (A, 5/5): "the sun has not improved at all." night-sky (B, photographic
  Milky Way): "These are fucking beautiful ... a meteor shower if we can come up with
  something of this quality that would last the whole night."

Settled: Hillaire sky, gold near the sun at 1.5x, haze 0.35 with height weighting, deep-clear
nights with the ESO panorama in rotation. Open: the sun itself, a livelier horizon band at
golden hour, consistency between haze, aerial perspective and fog.

## 2. What we do now

**Atmosphere** (`lib/atmosphere.glsl`): Hillaire 2020 with the paper's Earth constants
(Rayleigh (5.802, 13.558, 33.1)e-3 per km, scale height 8 km; Mie 3.996e-3 scatter and
4.44e-3 extinction **times 1.5** for a visible low-sun glow, scale height 1.2 km, g 0.8; ozone
(0.65, 1.881, 0.085)e-3 in a 25 km tent; ground albedo 0.3). Tables in `colortex5` (256x320,
RGBA16F, never cleared; `lib/lut.glsl`): transmittance 256x64, multi-scatter 32x32, sky-view
192x112 twice (sun and moon), plus a row of constants (`C_SUN`, `C_MOON`, `C_AMB_UP`,
`C_AMB_SIDE`, `C_EXPOSURE`, `C_STATE`). `program/prepare.glsl` builds the two static tables in
the first six frames (`C_STATE` age), the sky-view tables every frame with `QF_SKY_STEPS` 12 /
20 / 24 quadratic steps, the ambient constants from a 6x12 hemisphere sum, and the exposure
meter; `prepare1` copies everything so the buffer is written twice (trap 4). The sky-view
parameterisation puts the horizon at pi - beta with a squared compression toward it (the
round-9 fix). `cameraRadius()` clamps altitude to 0.2 m to 60 km.

**Sky pixels** (`lib/sky.glsl` `skyRadiance` in `deferred`): `skyScatter` = `SUN_I 3.0` x sun
sky-view + moon sky-view (`MOON_I = 0.024` x phase, `QF_NEW_MOON 0.25` floor, tint (0.78, 0.88,
1.0)); `QF_CAL_GOLD 2` warms within about 25 degrees of a low sun by (1.30, 1.0, 0.58) x
`QF_GOLD_SKY 1.5`; airglow `QF_AIRGLOW 0.004`; `QF_HORIZON_FLOOR` darkens below the horizon
(0.58, 0.64, 0.74); rain desaturates. Then `sunDiskReal` (`lib/sun.glsl`, r007, unjudged):
radius 0.0047 rad x `QF_SUN_SIZE`, per-channel limb darkening, colour = transmittance hue to
the 0.6 power, drawn at a fixed on-screen peak `sunPeak()` 6 to 9 divided by `exposure()`;
`moonDisk` 0.035 rad with phase, maria noise and `MOON_DISK_GAIN 7`; `stars` from hashed
cells (420 per unit, `STAR_CUT 0.9975`, twinkle); `nightSkyTexture` variants (deep clear,
airglow bands, the ESO/S. Brunier panorama CC BY 4.0, meteors `QF_NIGHT_SKY 4`). Glare:
`final.glsl` `sunGlare`, a three-term point-spread function scaled by nine visibility taps on
the disk, `QF_LENS` ghosts off.

**Fog** (`program/composite.glsl`, after water): haze `1 - exp(-(d - start) rho)` from `start`
0.35 far (0.12 in rain), rho 2.2/far x `QF_HAZE 0.35`, colour `skyScatter(viewDir)`
desaturated 30%, at night toward a darker sky from 20 blocks; `QF_HAZE_HEIGHT` weights by
blocks below the camera (0.25 at eye level to 1.25 forty blocks down); `QF_AERIAL`:
T = exp(-d hw / apD (0.55, 0.78, 1.15)), apD 400 by day, in-scatter from `skyScatter` at a
horizon direction 90 degrees from the sun; biome weights `qfFogCrisp` (x0.2 density),
`qfFogMoody` (exponential height fog H 7, Y0 63, lit medium), `qfFogStorm` (tau = d/18,
snow-white). Three blends, three colours, one after another.

## 3. What the top packs do

- **Photon** [V, published `shaders.properties`; README https://github.com/sixthsurge/photon]:
  a precomputed scattering lookup, a 192x108 sky map, Rayleigh and Mie fog densities that vary
  with time and weather, border fog, cave fog, a Purkinje shift for night, a galaxy image from
  NASA SVS, crepuscular rays under the sky settings, "different skies each day".
- **Kappa** [V, https://wiki.rre36.com/wiki/Kappa_Shader]: Rayleigh tint and density, Mie,
  ozone, a volumetric "mist" at sunrise and night with altitude and falloff, scattering and
  airmass iteration counts, a multiscattering strength, "accurate transmittance" (air colours
  the light that crosses it, "a mild performance cost"), a sun path angle.
- **Sundial Lite** [V]: "physically based atmosphere" aware of the player's height; a galaxy in
  the End. **Solas** [V]: aurora, Milky Way, rainbows. **Complementary Reimagined**: auroras
  and star patterns in its changelog [U]. **SEUS PTGI E12**: sky, lighting and cloud colour
  from the same physically based functions, a horizon added [U, search snippet].
- **Hillaire 2020** [V, PDF https://sebh.github.io/publications/egsr2020.pdf; code MIT
  https://github.com/sebh/UnrealEngineSkyAtmosphere]: table 2 on a GTX 1080: transmittance
  256x64 with 40 steps 0.01 ms, sky-view 200x100 with 30 steps 0.05 ms, aerial perspective
  32^3 with 30 steps 0.04 ms, multi-scatter 32^2 with 20 steps 0.07 ms, on-screen 0.14 ms,
  0.31 ms total at 720p; the aerial-perspective volume is 32x32 over the screen by 32 depth
  slices over 32 km, RGB in-scatter and mean transmittance in A, applied to opaques as a post
  process and per vertex on transparents; the sky-view texture compresses toward the horizon
  with v = 0.5 + 0.5 sign(l) sqrt(|l| / (pi/2)); the sun disk is composited after the LUT;
  multiple scattering assumes isotropy from the second order and sums as 1 / (1 - f_ms);
  Bruneton's full LUT update costs 250 ms; on an iPhone 6s the sky-view drops to 96x50 with 8
  steps. Frostbite 2016 [V]: an aerial volume of 32x32x16 cost 0.05 ms on Xbox One; its LUT
  update is spread over 19 frames (0.22 ms per frame instead of 3.5).

## 4. The technique

**A. One medium for haze, aerial perspective and fog: an aerial-perspective LUT.** Replace the
three successive blends with Hillaire's camera-frustum volume, scaled to Minecraft distances.
32x32 texels over the screen, 16 depth slices spaced quadratically from 0 to `far`, built in
`prepare` as a 512x32 strip (grow `colortex5` to 512x352, or add a second small buffer;
neither costs full-screen bandwidth). Each texel marches 8 to 12 steps through a **local
medium** that is not the planet's air (Earth Rayleigh gives 0.1% haze over 300 blocks) but the
thing our haze already models: a height fog rho(y) = rho0 exp(-(y - y0) / H) plus a weather
term. Per step: extinction sigma_t = rho (0.55, 0.78, 1.15)-weighted (keep our wavelength
bias so distance goes blue); in-scatter colour = `skyScatter` sampled in the view direction
for the sky-lit part (Hillaire's "sky colour as the in-scatter" shortcut) plus the sun's
irradiance times a HG lobe (g 0.6) times the cloud shadow map for the sunlit part; integrate
with Frostbite's energy-conserving step. Store in-scatter RGB and mean transmittance.
`composite` then applies one `mix`: `color = color * T + S` at the pixel's depth slice. Biome
and weather uniforms set rho0, H and the scattering albedo: crisp mountains rho0 x0.2,
swamp H 7 near y 63, the storm rho0 x30 with a white albedo. The owner's height rule (r004)
is then physical: land below the camera is seen through denser air. Night: the sky term is
the moon sky-view, so distant land fades into the night sky, not a moonlit wall (the r12
lesson), without a special case.

**B. The sun** (r006: "not improved at all"; r007's `sunDiskReal` has not been judged yet, so
first show it). Physics: the disk's radiance is about 1.6e9 cd/m^2 against a sky of 1e4, so a
correctly exposed disk is always clipped white except within a few degrees of the horizon,
where transmittance drops it 100x and reddens it; a camera shows a small white disk with a
warm glare whose colour is the transmittance. So: keep the fixed-peak disk (6 to 9 times
display white after exposure), but take its colour from the transmittance directly below 5
degrees (power 1.0, not 0.6) and let the glare's inner term carry the reddening too
(multiply the PSF by the same transmittance hue). Make the disk's peak follow the metered
exposure smoothly (today `exposure()` can step; a stepping disk flickers). Test on
`shore_dusk` (sun 2 degrees) and `ocean_sunset` (9 degrees). The earth's shadow and the Belt
of Venus already come out of the sky-view table (planet shadow in `lightTransmittance`),
check `shore_dusk` at worldTime 13000 against the Commons photos.

**C. The horizon band at golden hour** ("pretty flat", r003). The band's life comes from
aerosols, not Rayleigh. Add a second Mie species in `mediumAt`: a haze aerosol with g 0.85,
scale height 1.2 km and a density that follows weather and biome through the smoothed uniforms
(desert dust warm and dense, swamp humid, mountains thin). The sky-view table is rebuilt
every frame anyway, so weather-dependent Mie is free; it also gives the "glow around a low
sun" that the 1.5x Mie fudge approximates today, and a different sunset every evening.

**D. Night.** The moon already lights the sky through its own table. Stars: replace the hashed
cells with a **real catalogue**: the Yale Bright Star Catalogue (about 9,100 stars with
position, magnitude and colour index; public-domain data [U: confirm the distribution terms])
baked by `make_textures.py` into a 2048x1024 equirectangular RG16 texture (brightness from
magnitude, colour from B-V), rotated with `worldTime` about a celestial pole tilted by
`sunPathRotation`; the ESO panorama (galactic coordinates) is then aligned to the same frame
so the Milky Way and its real stars agree. Real constellations are the kind of "texture and
beauty" that does not read as hand-drawn. Airglow: keep faint. Meteors: keep. Add a
**Purkinje shift** in `final` (Photon has one): below a metered log2 luminance of about -6,
desaturate toward a rod response and shift the white toward blue by 10 to 20%; the owner's
accepted nights are navy, so a light touch.

**E. Rain** (look bible 9): the sky-view desaturation is right; add the cloud-cover attenuation
of the sun's in-scatter from clouds.md and raise the haze aerosol with `rainStrength`.

Programs: `prepare` (tables, aerial LUT, cloud shadow map), `deferred` (sky radiance, disks),
`composite` (apply the aerial LUT), `final` (glare, Purkinje). Render targets: `colortex5`
grows, nothing full-screen.

## 5. Low and Potato

The tables already run on every tier; Potato's 0.28 ms at 720p is mostly `prepare`, so **do
not grow the per-frame tables without measuring Potato**. Aerial LUT: 32x32x16 with 6 steps on
Low (one fetch to apply), 4 steps on Potato or keep today's analytic aerial perspective. The
star texture is one fetch; the Purkinje shift is arithmetic; the aerosol species costs
nothing extra at apply time.

## 6. Cost

- **[measured]** Hillaire's whole sky 0.31 ms at 720p on a GTX 1080, aerial volume 0.04 ms;
  Frostbite's 32x32x16 volume 0.05 ms on Xbox One. Ours: Potato 0.28 ms whole pack at 720p,
  dominated by the fixed-size `prepare` work; High whole-frame 2.3 ms.
- **[estimate]** Aerial LUT 512x32 at 10 steps: 0.02 to 0.05 ms on the dev PC; applying it
  replaces three `skyScatter` evaluations per pixel, so composite gets cheaper by about the
  same. Star texture: under 0.01 ms. Second Mie species: about 10% more in the per-frame
  sky-view build (0.005 ms High; measure Potato).
- Measure: `--scenes biome_hills,biome_hillsplus,dawn_wide,shore_dusk,shore_sunset,night_sky,
  night_new,plains_noon` with `--opt QF_AERIAL=0` for the fog path and `QF_SUN=0` for the disk.

## 7. Test scenes and reference photos

Views: `dawn_wide`, `shore_sunset`, `shore_dusk` (sun below the horizon: earth shadow),
`forest_golden`, `golden_lit`, `biome_hills` and `biome_hillsplus` (aerial perspective),
`night_sky`, `night_moon`, `night_full`, `night_new`, `sky_noon`. Photos (Commons): Category:Belt
of Venus [V, e.g. "Belt of Venus over Paranal Observatory.jpg"], Category:Blue hour [V],
Category:Atmospheric perspective [V, with the subcategory "Sky gradients"], Category:Crepuscular
rays at sunset [V], Category:Milky Way Galaxy [V, subcategory "Milky Way Galaxy and a place on
Earth", "Featured pictures of the Milky Way"], Category:Full moon [V], Category:Sunsets [V,
subcategory "Water reflections of sunsets"].

## 8. Pitfalls

Angelica: `colortex5` is single-writer without `prepare1` (trap 4), so any new table needs the
same double write; mips are not rebuilt for `prepare` reads (trap 3: the exposure meter reads
level 0 for this reason); the shader-cache double build (trap 2); there is no dimension
uniform, so per-dimension skies are `dimension.properties` folders with two-line stubs; the
sky-view v mapping must keep the horizon at pi - beta (round 9); `sunPathRotation -22` moves
where the sun sets, so view yaws in `views-world-master.txt` depend on it. Technique: the
isotropic multi-scatter approximation under-colours dense or strongly anisotropic atmospheres
(paper section 7), so keep the aerosol density moderate; the sun disk must never go through
the sky-view table (resolution); coarse aerial slices near the camera band on close terrain
(quadratic slice spacing); a Purkinje shift applied before tone mapping interacts with
vibrance (apply after exposure, before the mapper, and skip it when `nightVision` is on).

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Hillaire 2020, EGSR | paper; code MIT, none copied | method and constants (physical data) |
| Bruneton 2017 | BSD-3 reference, none copied | the transmittance parameterisation (already credited) |
| Hillaire 2016, Frostbite | talk | aerial volume sizing, LUT time-slicing |
| Wenzel 2006, "Real-time atmospheric effects in games" | talk [U] | analytic height fog |
| Kutz 2013, "The importance of ozone" | blog | idea |
| Yale Bright Star Catalogue (BSC5) | public-domain astronomical data [U: confirm] | star texture |
| ESO/S. Brunier, eso0932a | CC BY 4.0, credited in `LICENSES/README.md` | the Milky Way |
| Photon, Kappa, Sundial, Solas, SEUS, Complementary | learn-only | feature survey |
