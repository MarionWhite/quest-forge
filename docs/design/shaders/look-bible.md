# Look bible

What the pack should look like, in order of priority. The critic scores every
frame against this document and the owner's taste profile; when they disagree,
the owner's answers win and this file is updated to match.

**Version 5**, 2026-10-24: drafted 2026-10-16 from [`research/desirability.md`](research/desirability.md);
the Shader Lab answers to round 0 (2026-10-18), round 1 (2026-10-21), round 2 (2026-10-23),
round 3 (2026-10-23 evening) and round 4 (2026-10-24) are folded in below.

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
12. Water: clear in the shallows, deeper with depth, Fresnel reflections with a sky
    fallback, gentle waves, an underwater fog volume. **Its colour follows the biome**
    (owner r002): lakes and rivers clear and glassy, oceans deep blue, coasts and coral
    reefs a Maldives turquoise, swamps and marshes a murky teal.
13. Warm block light: torches read as a flame, not a lamp. Tungsten at the source
    (about 3000 K, r003: 2850 K) warming towards candle (about 2400 K, r003: 2200 K) where
    the light is dim, at vanilla-like brightness. r001's (1.0, 0.70, 0.45) was about 4000 K on screen and
    read as "a fluorescent light bulb". Colour per source where it can be done.
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
- Sky effects that are not genuinely beautiful (r002: the Milky Way was rejected outright;
  a half-done sky effect is worse than none)
- Bland, flat views: a crisp scene still needs depth, light and an interesting sky (r002)

## Texture pack (decided 2026-10-24, Shader Lab round 4)

The owner's pick (r004, "a combination of A and C", 5/5): **Faithful is the base.** We start
from Faithful 32x (GTNH-Faithful first for the GTNH-era blocks), whose licence lets us change
it and ship it with credit, and extend it to the modded and custom blocks in the same style.
A **broad range of other packs** (Soartex Invictus-Modded, Conquest_, John Smith Legacy and
others) is used **only for inspiration and reference**: sampled in a private test client, never
copied, traced or shipped. **Nothing that is not licensed for derivatives ships** in the pack or
appears on the public site (of the packs surveyed, only Faithful and Soartex Grove allow
derivatives). Every shipped texture records its source and licence.

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
`feedback/r000.json`), round 1, answered 2026-10-19 (issue #2, `feedback/r001.json`;
folded in 2026-10-21), and round 2, answered 2026-10-23 from a phone (issue #3,
`feedback/r002.json`; folded in 2026-10-23), and round 3, answered 2026-10-23 (issue #4,
`feedback/r003.json`; folded in the same evening), and round 4, answered 2026-10-24 (issue #5,
`feedback/r004.json`). Each later round's picks, ratings and notes
are added here. Where these contradict a rule above, these win.

- **Round 4 overall:** "beginning to take shape", and "really eager to get this to a really polished
  product". Wants to **attach reference images** to the Lab form (screen-grab on a Mac, drag and
  drop): the Lab and relay gained image attachments (live once the relay is redeployed).
- **Round 3 overall:** "Some improvements, and some things to work on for sure." Wants a **texture
  pack worked on in parallel** with the shaders, because it changes the direction of much of this:
  look at a broad range of existing packs first (sample them, take a solid one and extend it to the
  modded blocks, or make a custom one), judged against the design taste below. Wants to **decide
  directions together** from researched references: other packs' water, and cloud inspiration.
- **Round 2 overall:** "I am definitely seeing progress! ... I have very high expectations."
  Keep asking questions wherever taste decides. Sending from the phone means signing in to
  GitHub every time, "a huge pain": the feedback relay is worth switching on.

- **Direction: between photoreal and cinematic.** Photoreal water and light, but blocks
  rendered as rich, high-quality surfaces, not bit-crushed textures (the generated
  normal maps are the start). Biome- and weather-driven screen atmosphere: fog,
  limited vision in a tundra storm. The aim is immersion: people should stop and look.
- **Night: between "truly dark" and "moonlit".** Light sources must matter. The night
  sky should be strikingly beautiful. The immediate area stays visible (playable), but
  visibility falls off naturally with distance, so a mob is unclear until it is fairly
  close. (Round 10's 0.085 was too bright; aim for about 0.04-0.05 mean luma at full moon.)
  - **Full moon: keep it** (r001: current, rated 5, mean luma about 0.046-0.050). More
    beauty comes from extra effects (sky, stars), not from changing its brightness.
  - **Night sky (r004: neither, 4/5): the lighting profile is right**, but the sky wants "a little
    more texture and beauty", and **a rotation of skies** so nights are not samey. Land light
    stays as it is; the sky itself changes (r005: a deep clear starfield, airglow bands and a
    Milky Way, chosen per night, the faint ones washed out by a bright moon).
  - **New moon: QF_NEW_MOON 0.25** (r003: B, 5/5, "the sky looks fuller ... a deep rich darkness").
  - (r002:) **New moon: the full-moon night, a bit darker** (r002: picked the full-moon frame over
    all three new-moon options, rated 4: "we regressed with the new proposed changes"). The
    r002 new moons had a brown-black sky; the full moon's navy sky and readable land are
    the look. Darker than the full moon, never that regressed look. (r001: A, rated 3, asked
    for 0.033-0.037; superseded.)
  - **Night sky: r001's stars** (r002: A, 5/5). The Milky Way was rejected ("the execution
    is not good"). Open to sky effects, but only ones that are genuinely beautiful.
- **Golden hour (r004): keep the current default** (A, 3/5: "a good spot, but we can always do
  better"). **Leaves (r004: neither, 4/5): "more cinematic light"**: he agrees with the critic
  that forest_golden lost round f's warm shaft through the trees. Light shafts (volumetric sun
  through gaps, warm at golden hour) are the answer being tried in r005.
- **Golden hour: amber light plus a gold sky near the sun** (r001: B, rated 4, for both
  the wide view and the sunset; replaces r000's "naturalistic"). **r003: round 2's version won
  (B, 5/5) over the extra amber on lit faces (QF_AMBER 1/2, now 0); "the horizon band is pretty
  flat"**, so the band needs life, not more warmth. Leaves (r003: B, 4/5): round 2's leaves "give
  the environment depth" and the amber options did not show the effect described. r002 confirmed it (5/5,
  "keep pushing in this direction"), with the gold sky at 1.5x (5/5, "maybe more gold")
  and **amber on the leaves and other lit surfaces**. Liked: "how the light
  hits the blocks in the background", and foreground and background lit differently by
  the low sun, as long as the lit foreground is properly lit and saturated. The gold
  stays near the sun and above the horizon band: it must not warm the haze into a
  beige wall. The owner will design sky effects of his own later.
- **Water: realistic depth gradient** (C). The balance of surface reflection against
  what shows through is a big part of the look. r001 said "the water doesn't look
  amazing"; r002's new water is "much better" (sunset over the lake 5/5).
  - **Direction (r004: A, the calm mirror, 5/5):** still water that mirrors the sky with one soft
    sun path, heading for "a combination of Complementary's Unbound (realistic) style and Photon's
    strict realism" ("I really like the screenshots from those 2 the best").
  - **At sunset (r004: neither, 4/5):** "a really good starting platform", but he hopes for "more
    beauty out of a scene like this". Still wanted: bright spots right below the sun with depth to
    their light (r003).
  - **Biome water (r004: the lake at noon, B, 5/5):** the critic was "right on the money" again:
    the river at noon is a milky blob, the swamp too clear and too grass-green. The glassy lake is
    the reference. Rivers get their own slightly green, half-clear water; swamps get silt that hides
    the bed.
  - **Flecks (r004: 1.25x round 3's full amount)**, i.e. "125% of whichever of these has more";
    QF_FLECKS is on again.
  - **Colour by biome** (r002: neither fixed colour; rated 5): teal and murky in swamps and
    marshes, deep blue for most oceans, transparent and glassy for most rivers and lakes,
    Maldives turquoise for coasts and coral reefs. The pregenerated map makes this work.
  - **At sunset: r002's lively water** (r003: A, 4/5, "so much more balanced", the fullest range of
    colours; QF_GLITTER 0). The surface-glitter and cinematic-sun options had "an ugly orange cone
    artifact right down the middle of the screen" (critic: the aerial-perspective term sampled the
    sun's glow for every pixel below the sun). Wanted from the cinematic one: "spots right below the
    sun that have the light intensity depth". Direction to be chosen together from other packs' water.
  - **Biome water** (r003: coast 5/5): coast and ocean are the best; the critic's notes were "right on
    the money" (river dark slate with a blown noon highlight, swamp too clear): realise and iterate them.
  - **Near-water flecks: less** (r003: "a bit much"; the r002 amount, maybe a little more, was right).
    r002's "bubbles" were the near-water sparkles of QF_GLITTER 0, so QF_FLECKS is now 0.
  - (r002, superseded at sunset by r003:) **At sunset: lively** (r002: C, 3/5). The light source should look more cinematic, with
    a glitter that interacts with the surface texture, "but only if we can get it right".
  - **At noon: calm** (r002: B, 4/5): the distant surface texture must not dominate. Loved
    the "bubble" flecks on the near water and wants more effects like that. Room to improve.
- **Fog: per biome.** Crisp mountains and plains, natural haze elsewhere, moody thick
  fog in some biomes, and a heavy, vision-limiting tundra storm.
  - **Baseline: haze 0.35** (r002: C, 5/5, "definitely the best ... not too crisp, and not
    too murky"; r001 asked for between r001's haze and crisp).
  - **Hills (r004: B, aerial perspective on, 3/5):** likes "the haze off to the left where the
    elevation drops", not that "it washes out the color of everything at the same elevation as the
    camera". **Haze and aerial perspective depend on height below the camera as well as distance**
    (QF_HAZE_HEIGHT): full where the land drops away, light over land at eye level.
  - **Hills (r003: neither):** not loving the colour range, the environment or the clouds. Clouds:
    research inspiration and pick a direction together. Aerial perspective is off (QF_AERIAL 0) until
    then: neither of his golden or leaves picks had it.
  - **Crisp is not enough on its own** (r002 Extreme Hills, 4/5: "crisp enough, but this
    scene still looks very bland"): give such views depth (aerial perspective), light and
    a sky with something in it.
  - (r001:) The biome
    looks are dialled in from real views inside each biome, round by round; until then
    biome fog is on only where clearly justified (crisp mountains, the snow storm) and
    subtle elsewhere.
- **Clouds (r004: D, dramatic broken clouds, 5/5):** "only good with the right execution. I don't
  want it to look like a png of this pasted onto the sky. I would want something more dynamic that
  looks beautiful and natural. I want this pack to have a truly beautiful sky." Clouds must be
  volumetric-looking, lit by the sun and sky (silver linings, darker bases), moving and changing,
  never a texture. Raymarched clouds start in r005.
- **Bloom: subtle**, a natural halo that scales with light intensity. Never too much.
- **Performance: 60+ fps for everyone** comes first. Effects that need 30 fps are not
  worth having; pour the effort into optimised looks.
- **Dislikes:** motion blur, too much bloom.
- **Questions: more per round** (r001 overall: "happy to field more questions with each
  iteration"). Ask wherever taste decides: water colour and surface, torch warmth, sky
  gold, night-sky beauty, and each biome's fog.
- **Torches: tungsten to candle, a little warmer** (r002: B, 4/5; r003: B, 4/5, QF_TORCH_WARM 4;
  r004: A, 3/5, "warmer was definitely the right call": keep it).
  Wanted next (r003): heat shimmer around the flame, small embers, ambient dust "like some of the
  modern effects mods have". Inexpensive
  environmental and ambient effects are welcome (heat shimmer, dust motes, flicker), within
  the budget.
- **Ambient particles: visible, balanced** (r003: the three mote options "look the exact same":
  too faint to judge). Likes the bubbles and dust; try other creative ideas.
- (r002:) **Ambient particles: yes, more** (r002 water and torch notes): cheap environmental effects
  such as the water's bubble flecks, dust in sunbeams and around torches.
- **Wants (later milestones):** unobtrusive cave dust; cheap block-break effects that
  survive mass breaking (Mobzilla); rain as misted air, not only particles; lava and
  fire light that moves naturally, not a looped flicker; realistic water and light.
