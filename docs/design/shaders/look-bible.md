# Look bible

What the pack should look like, in order of priority. The critic scores every
frame against this document and the owner's taste profile; when they disagree,
the owner's answers win and this file is updated to match.

**Version 0**, 2026-10-16: drafted from [`research/desirability.md`](research/desirability.md).
Round 0 (calibration) answers have not been folded in yet.

## North star

Near-photoreal light and air on unmistakably Minecraft geometry. Realism comes
from the sky, sun, shadows, water and atmosphere, never from smoothing away the
blocks. The most-downloaded packs are the ones that "don't make the world feel
alien".

## Tier A: comfort. Never traded away.

1. **Readable darkness.** Nights and caves are dark, never black. An ambient
   floor scales with moon phase and a player slider. Held light works.
2. **Calm exposure.** Slow, bounded auto-exposure. No pumping when turning
   toward the sky or a lamp; no single emitter blows out the frame.
3. **Neutral colour.** Saturation near vanilla. A neutral tone mapper with no
   hue skew on bright orange and red. Wood, chests, sand and gold are the test
   surfaces: they turn neon first.
4. **Golden hour without the wash.** Warm sunlight, but the zenith stays blue.
   No pink or orange cast over the whole frame.
5. **Stable over sharp.** Temporal anti-aliasing without ghosting or trails;
   clouds and volumetrics recover quickly when something moves in front of them.
6. **Clear near field.** Haze and aerial perspective start far out and follow
   weather and biome. Gameplay distances stay crisp.
7. **Off by default:** motion blur, depth of field, lens flare, film grain,
   chromatic aberration. Available in a "Cinematic" profile.

## Tier B: what reads as photoreal

8. Physically based sky: Rayleigh and Mie scattering, ozone for a blue twilight,
   a real sun disk, stars and a moon that light the night believably.
9. Volumetric clouds with cloud shadows and day-to-day weather. Rain darkens and
   desaturates sky and clouds.
10. Soft shadows with contact hardening, reaching the shadow distance; light
    through leaves (subsurface).
11. Grounding ambient occlusion, subtle at block corners so the voxels still read.
12. Water: clear in the shallows, deeper blue-green with depth, Fresnel
    reflections with a sky fallback, gentle waves, an underwater fog volume.
13. Warm block light (about 2700–3000 K for torches); colour per source where it
    can be done.
14. Wetness after rain that dries over minutes; puddles in hollows.
15. Restrained, energy-conserving bloom on genuinely emissive pixels only.

## Tier C: Quest Forge specifics

16. **Modded blocks are first-class.** Modded leaves wave, plants sway, lamps
    glow, ores glint, metal and polished stone reflect, glass refracts. They get
    the same generated surface detail as vanilla, so nothing looks flat beside
    vanilla.
17. **Every dimension has a deliberate sky and fog.** About 30 of them; none
    falls back to the overworld at night.
18. **Custom renderers render correctly.** The pack's jukebox, record case and
    speakers, McHeli aircraft and held weapons, Legends lasers and auras,
    Transformers glows. Tested against the six modded failure classes below.

## Anti-patterns (automatic deductions)

- Pink or orange sunset wash over the whole frame
- Pitch-black caves or nights
- Exposure pumping
- Grey, washed-out haze
- TAA trails or smearing; noisy or smeary clouds
- Neon saturation
- Puddles that never dry
- Rounded-off voxel edges (heavy parallax, over-smooth normals)

## Modded failure classes (each needs a test scene)

From the Shader Fixer patch list (50 fixes across 1.7.10 mods):

1. Beams, lasers and effects not rendering
2. Emissive effects with the wrong brightness
3. Effects that cast shadows they shouldn't (forcefields, projectiles)
4. Particles with black backgrounds
5. Held items corrupting the frame (water or clouds seen through blocks)
6. GL state leaking from mod GUI or tile-entity renderers

## Owner's taste profile

From round 0 (calibration), answered 2026-10-18 (GitHub issue #1,
`feedback/r000.json`). Each later round's picks, ratings and notes are added here.
Where these contradict a rule above, these win.

- **Direction: between photoreal and cinematic.** Photoreal water and light, but blocks
  rendered as rich, high-quality surfaces, not bit-crushed textures (the generated
  normal maps are the start). Biome- and weather-driven screen atmosphere: fog,
  limited vision in a tundra storm. The aim is immersion: people should stop and look.
- **Night: between "truly dark" and "moonlit".** Light sources must matter. The night
  sky should be strikingly beautiful. The immediate area stays visible (playable), but
  visibility falls off naturally with distance, so a mob is unclear until it is fairly
  close. (Round 10's 0.085 was too bright; aim for about 0.04-0.05 mean luma at full moon.)
- **Golden hour: naturalistic** (option C, the physical sky). The owner will design
  sky effects later. Liked: foreground and background lit differently by the low
  sun, as long as the lit foreground is properly lit and saturated. Round 9's frame
  read better than round 10's (round 10's shade was murky).
- **Water: realistic depth gradient** (C). The balance of surface reflection against
  what shows through is a big part of the look.
- **Fog: per biome.** Crisp mountains and plains, natural haze elsewhere, moody thick
  fog in some biomes, and a heavy, vision-limiting tundra storm.
- **Bloom: subtle**, a natural halo that scales with light intensity. Never too much.
- **Performance: 60+ fps for everyone** comes first. Effects that need 30 fps are not
  worth having; pour the effort into optimised looks.
- **Dislikes:** motion blur, too much bloom.
- **Wants (later milestones):** unobtrusive cave dust; cheap block-break effects that
  survive mass breaking (Mobzilla); rain as misted air, not only particles; lava and
  fire light that moves naturally, not a looped flicker; realistic water and light.
