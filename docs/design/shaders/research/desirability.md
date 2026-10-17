# Shader-pack desirability research (for a new 1.7.10 near-photoreal pack)

Date: 2026-10-16. Scope: what players like and dislike in shader packs, distilled into a look bible.

## Source caveat (read first)

Reddit (reddit.com, old.reddit, and the redlib mirrors tried) was **unreachable** from this research agent: blocked or offline. YouTube comment sections and the shaderLABS Discord also can't be read this way. Community sentiment here therefore comes from:
- GitHub issue trackers (Complementary, Photon, Angelica), which are real user complaints;
- the GTNH wiki and compatibility-mod changelogs;
- the CurseForge popularity blog, a community forum review thread, the Mojang feedback site and coverage of Vibrant Visuals;
- review and aggregator sites (anvilpacks, craftdex). These read as semi-promotional and are weighted low.

Items tagged **[GK]** are from my general background knowledge of the scene and were **not verified** this session. Treat them as hypotheses to check against a few Reddit threads or YouTube comparisons by hand.

---

## 1. The acclaimed packs: signature, praise, complaints, cost

shaderLABS keeps a cost-tiered list of maintained packs ([shaderLABS Shaderpacks](https://shaderlabs.org/wiki/Shaderpacks)):
- **Low:** BSL, Complementary (+Euphoria), Lux, Super Duper Vanilla, Chocapic13
- **Medium:** Bliss, Photon, Noble, SEUS Renewed, Oceano, Nostalgia, Continuum Legacy
- **High:** Kappa, Rethinking Voxels, SEUS PTGI, KappaPT, NobleVX
- **Extreme:** Continuum RT

The CurseForge all-time download ranking (Sep 2025) is: Complementary Reimagined > Complementary Unbound > BSL > Sildur's Vibrant > MakeUp UF > Insanity > Pastel > Solas > Super Duper Vanilla > Bliss > Spooklementary > AstraLex > Nostalgia > ... > Kappa (15) > Sildur's Enhanced Default (16) > ... > Oceano (24) ([CurseForge blog](https://blog.curseforge.com/the-25-most-popular-minecraft-shaders-on-curseforge/)). **The market leader is the pack that stays closest to vanilla, not the most realistic one.**

| Pack | Signature look | Praised for | Complained about | Perf rep |
|---|---|---|---|---|
| **Complementary Reimagined** | "Reworked vanilla feel", "preserving the unique visual elements of Minecraft" ([Modrinth](https://modrinth.com/shader/complementary-reimagined)) | Clean, polished, safe default; custom per-block effects; Potato to Ultra profiles; "never obstructive during gameplay" | TAA ghosting and "edge splotting" (#83, #257), noisy light shafts on Intel (#100), shadows cutting off before render distance (#216), modded glowing-ore bugs (#66), Aether "always looks like nighttime" (#46) ([GitHub](https://github.com/ComplementaryDevelopment/ComplementaryReimagined/issues)) | Low; best in class |
| **Complementary Unbound** | Same code with realism defaults: volumetric "puffy" clouds, realistic water ([Modrinth](https://modrinth.com/shader/complementary-unbound)) | Users treat it as the "safe choice" for big packs (ATM9 thread via an r/feedthebeast mirror) | Same as above; heavier | Medium |
| **BSL** | Soft, warm, cinematic. Catalogued as "cartoon" style | Water is "exceptional"; tuning depth; a "soft/hazy" filter that is loved for screenshots | "The pink in the sky is very strong" at golden hour ([MCME forum](https://www.mcmiddleearth.com/community/threads/raffys-list-of-shaders.5622)); **[GK]** heavy bloom/haze in older versions | Low–Medium |
| **Photon** | "Gameplay-focused... semi-realistic": GTAO, variable-penumbra shadows, multi-layer clouds, a different sky every day ([Modrinth](https://modrinth.com/shader/photon-shader)) | Neutral, crisp colour balance, avoids the blurry haze of older packs; ~200–250 fps at 1440p on an RX 9070 XT ([benchmark](https://www.feed-the-mods.com/minecraft-with-photon-shaders-hits-250-fps-at/)) | Issues include clouds/fog reappearing too slowly after occlusion (TAA history), TAA-scaling Z-buffer problems with particles, sun reflected in water regardless of occlusion, rain puddles never drying, blocky clouds staying sunny-blue in rain ([GitHub](https://github.com/sixthsurge/photon/issues)) | Medium |
| **Bliss** (Chocapic13 edit) | Moody, painterly; heavy biome- and time-dependent fog; volumetric clouds that tint the light | Clouds and cloud shadows, sunrise god rays; "not too dark at night" | The dev admits the second cloud layer made clouds "blurry and noisy" ([CurseForge](https://www.curseforge.com/minecraft/shaders/bliss-shader)); FPS dips under overcast | Medium |
| **SEUS Renewed / PTGI** | Physically lit, solid; PTGI has true GI | Water clarity; "adds a solidity and realism" ([RTR blog](https://www.realtimerendering.com/blog/messing-about-with-seus-for-minecraft/)) | "Dark areas are, by default, quite dark indeed"; no held-torch light; "disco floor" flicker; cave light leaks; GI noise; ghosting vs stability trade-off ([Patreon notes](https://www.patreon.com/posts/32990443)) | High |
| **Kappa** | "Realistic but authentic". Deliberately not strictly physical, "tweaked to reproduce what you could observe in nature" ([CurseForge](https://www.curseforge.com/minecraft/shaders/kappa-shader-by-rre36)) | Avoids the "washed-out" look of some realistic packs; "realistic without making your world feel alien" (anvilpacks) | **[GK]** night and caves very dark; exposure adaptation can feel slow | High |
| **Rethinking Voxels** (Complementary edit) | Voxel colored light with **sharp block-light shadows** (no torch light bleeding through pillars) | The torch-shadow "wow" | The dev admits "occasional sudden brightness changes"; Iris-only | High |
| **Solas** | Fantasy, "smooth and saturated lighting, soft clouds" ([solasshader.com](https://solasshader.com/)) | Sunset volumetric clouds; rich cave, Nether and End volumetrics | Lighting from non-vanilla light sources broke under Angelica (#1985) | Medium |
| **Nostalgia** | Early-2010s shader look, deep blue water | Soft pink sunsets, cosy torchlight | Stylised rather than realistic | Medium |
| **Sildur's Vibrant / Enhanced Default** | High-contrast, vivid | Runs everywhere and supports 1.7.10. The dev recently reworked brightness to sit "in between 'Moody' and maxed out" ([CurseForge](https://www.curseforge.com/minecraft/shaders/sildurs-vibrant-shaders)) | "Caves can be quite dark"; higher fog density on OptiFine; no reflections through transparency on 1.7.10 | Low–Medium |
| **MakeUp UF** | Subdued and fast | Modular costs | Plain | Potato |
| **Super Duper Vanilla** | Recreates the cancelled Super Duper Graphics Pack | FPS; presets | Few complaints found | Low |
| **Insanity / Spooklementary** | Foggy, muted, horror | Fits horror packs | Niche | — |
| **AstraLex / Lux** (BSL edits) | Bioluminescent glow, foaming waterfalls, aurora | Spectacle | Heavy (Lux) | Medium |
| **Kuda** (legacy) | Dramatic | "Really shines at night"; good evenings | "Very bright and in your face" in daytime | — |

Not covered for lack of reliable sources: Mellow, Oceano, Noble, Stratum/Continuum and Chocapic13 (beyond the catalogue entries). The 2026 version of Lux on CurseForge is 1.21-only. shaderLABS lists Lux as running on 1.7.10, but I could not confirm that.

---

## 2. Recurring themes (what people praise and what they hate)

- **Darkness and readability (the most frequent complaint).**
  - SEUS: "dark areas... quite dark indeed".
  - Sildur's: "caves can be quite dark".
  - Bliss is marketed as "not too dark at night".
  - Mojang's Vibrant Visuals rollout produced the canonical version of the complaint: no brightness setting works. Raise it and days go hazy; lower it and caves and nights go black. Players also reported the Nether being "pitch black" with an "overpowering" blue fog ([Sportskeeda](https://www.sportskeeda.com/minecraft/issues-minecraft-bedrock-vibrant-visuals-mojang-needs-fix), [Mojang feedback](https://feedback.minecraft.net/hc/en-us/community/posts/35611959027725/comments/35626191166861)).
  - An ecosystem of mods (More Darkness, Velvet Night, Iris Caves) exists only to retune night and cave floors. That says one fixed default can't satisfy everyone, so ship a **minimum-light floor slider**.
- **Oversaturation and "too orange".** Vibrant Visuals: "oversaturated", "chests look neon orange", desert sand at midday "literally given me a headache" ([feedback](https://feedback.minecraft.net/hc/en-us/community/posts/36401161905677/comments/40561237331469)). BSL golden hour: "the pink in the sky is very strong". Neutral colour balance is exactly what Photon is praised for.
- **Overbright / bloom.**
  - Kuda and LexShino are "very bright", and BBEPC has leaves that are "very bright".
  - Exposure that "auto changes the brightness for no real reason" (Beyond Belief) is a named annoyance. The same goes for RV's "sudden brightness changes" and Photon's overexposed F3 screen and "player incredibly bright holding a lantern".
  - Takeaway: auto-exposure must be slow, bounded and predictable.
- **Washed-out / hazy.** Photon is praised for avoiding "the blurry, hazy style of older packs" and Kappa for avoiding the "washed-out look". The BSL haze splits opinion: loved for screenshots, not for play.
- **Temporal artifacts.** These are the dominant category in GitHub trackers:
  - TAA ghosting and edge splotting (Complementary);
  - cloud and fog history lag after disocclusion (Photon #454);
  - TAA-scaling breaking particles (Photon #276);
  - "bouncy entities" with TAA (Angelica #2013);
  - noisy and blurry clouds (Bliss);
  - GI noise and "disco floor" (SEUS).
  Sharpening (unsharp mask) also leaves trails; CAS is more stable ([TAA pack](https://modrinth.com/shader/taa)).
- **Clouds and sky.** Volumetric clouds and per-day weather variety are the most-praised "wow" features (Bliss, Solas, Photon, Kappa all lead with them). Clouds staying sunny-blue in rain is filed as a bug. People want weather to visibly change the sky's mood.
- **Water.** Water is what wins people over to BSL and SEUS ("beautifully clear water"). Unchanged vanilla water under a shader is called "very weird". Waves that look odd at distance are a complaint.
- **Shadows.** People complain about cascade cutoff before render distance and about shadow artifacts on giant objects (beacon beams, large machines). Sharp, correct torch shadows are a headline feature (RV).
- **Rain and wetness.** Puddles and ripples are praised, but puddles that never dry out are filed as a bug. Wetness has to evolve over time.
- **Motion blur / DOF.** Every major pack ships these, and the guides treat them as "cinematic" toggles. **[GK]** In community threads the common first move is to turn off motion blur and DOF, and in many packs they ship off by default. I could not verify this with Reddit data.
- **Nether, End and modded dimensions.** These are frequent failure points:
  - Nether black-screen (#325);
  - Aether stuck at night (#46);
  - Multiverse dimensions not detected (#272);
  - in the past, modded dimensions breaking entirely (Builder's QOL notes Twilight Forest needed a fix).
- **Photoreal vs "still Minecraft".** Critics of realism describe "cognitive dissonance... a sculpt wearing Minecraft's outfit" ([GeekChamp](https://geekchamp.com/?p=507794)). One Reddit commenter (seen only as a search snippet): "smooth or overly realistic forms are where they draw the line". Kappa's praised framing is "realistic without making your world feel alien".

---

## 3. Look bible (prioritised)

**Tier A: gameplay comfort.** Getting these wrong makes people uninstall.
1. **Readable darkness.** Nights and caves are dark but never black. There is a guaranteed ambient floor that scales with moon phase, plus a user slider. Held light (dynamic hand light) must work, because SEUS was criticised for lacking it.
2. **Stable, slow, bounded auto-exposure.** No visible pumping when turning toward the sky or a lamp. Clamp the adaptation range, and never let one bright emitter blow out the frame.
3. **Neutral base colour grade.**
   - Saturation stays at or near vanilla albedo.
   - Golden hour gets warm light, but the sky keeps its blue zenith. No pink or orange wash over everything.
   - Neutral tonemapping (ACES-like or AgX-like, with no hue skew on bright orange or red).
   - Test against wood, chests, sand and gold, which the Vibrant Visuals complaints show go "neon" first.
4. **Temporal stability over raw detail.**
   - TAA with motion vectors for entities, particles and animated geometry, plus disocclusion rejection.
   - CAS rather than unsharp mask.
   - Cloud and volumetric history must reset quickly on disocclusion.
5. **No haze at gameplay distances.** Aerial perspective should only begin far out. Fog density follows weather and biome, but it never smothers the near field.
6. **Effects off by default: motion blur, DOF, lens flare, film grain, chromatic aberration** **[GK, consistent with how every pack ships them]**. Offer them in a "Cinematic" profile.

**Tier B: what reads as "near-photoreal".** These sell the screenshots and still help in play.
7. **Physically based sky and atmosphere**: Rayleigh and Mie scattering, ozone for a blue twilight, correct sun disk, stars and moon. This is the foundation that makes sunsets read as real rather than painted.
8. **Volumetric multi-layer clouds** with cloud shadows on terrain and real weather variation by day. Rain must darken and desaturate the sky and clouds.
9. **Soft shadows with contact hardening** (variable penumbra, as in Photon) that reach render distance, plus SSS on leaves and foliage.
10. **Grounding AO** (GTAO-class). This is the cheapest single "realism" lever. Keep it subtle at block corners so the voxel geometry still reads.
11. **Water**:
    - absorption-based colour (clear in shallows, deep blue-green at depth);
    - Fresnel reflections with SSR plus a sky fallback, and the sun not reflected when occluded;
    - gentle normal-mapped waves that look right at distance;
    - an underwater god-ray and fog volume.
12. **Warm, physically motivated block light**: about 2700–3000 K for torches, cooler for soul fire. Colored per-source light is a strong differentiator (RV, Photon Ultra). On 1.7.10 a flood-fill voxel light is plausible only if the pipeline supports it.
13. **Wetness that comes and goes**: specular boost and darkened albedo after rain, puddles in depressions, and drying over minutes.
14. **Restrained bloom**: physically based, low intensity, energy-conserving. It applies only to genuinely emissive pixels.

**Tier C: screenshot-only.** Never at the cost of A.
- Heavy god rays, DOF, motion blur, lens dirt, long cinematic exposure.

**Anti-patterns**
- Pink or orange sunset wash
- Pitch-black caves or nights
- Exposure pumping
- Grey haze ("washed out")
- Over-sharpened TAA trails
- Smeary noisy clouds
- Neon saturation
- Puddles that never dry
- Smoothing away voxel edges, for example heavy POM that rounds blocks or ultra-smooth normals ("where they draw the line")

---

## 4. Modded-pack specifics (most relevant to Quest Forge)

- **GTNH / Angelica** ([GTNH wiki](https://wiki.gtnewhorizons.com/wiki/Shaders), [Angelica](https://github.com/GTNewHorizons/Angelica)):
  - Complementary + Euphoria is the primary compatibility target. Sildur's and SEUS are hit-or-miss.
  - SEUS renders barrel and drawer items "pure black" and a drying rack "as water".
  - Botania's mana pool casts shadows that follow the player.
  - Complementary blurs sign text through its drop shadow.
- **Angelica issue themes** ([issues](https://github.com/GTNewHorizons/Angelica/issues)) are mostly custom renderers and custom passes:
  - Better Foliage dark shadows;
  - Gorge and Godforge renders;
  - a Railcraft tank "permanently glowing";
  - OpenComputers screens flicker;
  - Dynamic Surroundings breaking rain detection;
  - non-vanilla light sources broken in Solas;
  - TAA bouncy entities.
- **Shader Fixer is the best taxonomy of modded failures.** It patches 50 specific bugs ([CurseForge](https://www.curseforge.com/minecraft/mc-mods/shader-fixer)), and it is unmaintained as of 10/08/2026. The bugs fall into six classes:
  - **Beams, lasers and effects not rendering** (NTM death ray, Cherenkov glow; *Fisk Superheroes lasers/lightning*, which matters for the Legends superhero mods).
  - **Wrong brightness on emissive effects** (black hole, UFO beam, nuclear explosion, Fisk suit fabricator, Schematica highlight).
  - **Effects that should not cast shadows but do** (forcefields, tesla projectile, sign pictures).
  - **Particles with black backgrounds** (Techguns, NTM).
  - **Held items corrupting the frame** (NTM guns make water and clouds visible through blocks). This is directly relevant to McHeli and the gun mods.
  - **GL state leaks** from GUI and TESR code.
  - Also: translucent particles going dark with Complementary, and broken shadows on Avaritia cosmic armor.
- **Modded blocks look flat** because they have no material IDs. Packs only wave, glow or apply specular to IDs they know. The community fixes are:
  - per-mod `block.properties` (Forge mods can ship `assets/<modid>/shaders/block.properties`);
  - Blopedit and Swaying Garden for waving modded plants;
  - Supplemental Patches, a resource pack covering popular mods for Euphoria ([CurseForge](https://www.curseforge.com/minecraft/mc-mods/supplemental-patches)).

  Complementary's "modded glowing ores" issue (#66) shows the demand. **What modpack players want: modded ores glow, modded plants wave, modded lamps emit, and modded dimensions get a sensible sky and fog.**
- **Implications for Quest Forge:**
  - Own the block-ID map for all ~140 mods. Twilight Forest, Witchery, Chisel CTM, OreSpawn and Lycanites plants and ores matter most.
  - Write a per-dimension profile for each of the ~30 dimensions; never fall back to "night".
  - Handle every non-standard pass (TESR beams, McHeli and Legends particles, held models) by forcing correct emissive and no-shadow flags.
  - Make hand-held light work, and test against the HBM/Fisk/Techguns-style failure list above.

---

## 5. What players change first (signals of bad defaults)

There are no hard survey numbers; this is **unverified**. Indirect signals:
- **Night and cave brightness.** Several standalone mods exist only to tune it, and Photon has an open request for a "Rainy Skylight brightness" slider (#511).
- **Saturation.** Vibrant Visuals drew complaints that it has "no saturation setting".
- **Profile and performance.** The guides' first advice is to drop the profile. MakeUp notes that bloom, DOF and shadows cost the most.
- **Clouds and water style.** These are the first toggles Complementary advertises.
- **Euphoria's "Popular Settings" tab.** It exists because users repeatedly change the same options; I could not retrieve its contents.
- **[GK]** Motion blur, DOF, film grain and vignette off; bloom down; shadow distance up; TAA sharpening adjusted.

**Default recommendation:**
- Gameplay profile with no motion blur, DOF or grain.
- Exposed sliders for:
  - Minimum Light (night and cave);
  - Saturation;
  - Sunset Warmth;
  - Fog Density;
  - Exposure Speed.
- An opt-in "Cinematic" profile for screenshots.
