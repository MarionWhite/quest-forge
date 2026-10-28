// Player-facing options and the preset table (docs/design/shaders/performance-rules.md).
// Every effect keys off QF_PRESET; the profiles in shaders.properties only set it.
// No valueless #defines in this file: Iris would list them as on/off options.

#define QF_PRESET 2 // [0 1 2 3 4]
#define QF_NIGHT_FLOOR 1.0 // [0.0 0.5 0.75 1.0 1.5 2.0 3.0]
#define QF_EXPOSURE_BIAS 0.0 // [-1.5 -1.0 -0.5 0.0 0.5 1.0 1.5]
#define QF_WAVING 1 // [0 1]
#define QF_DEBUG_VIEW 0 // [0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15]
#define QF_STILL 0 // [0 1]   development: freeze wind, waves and twinkle (temporal-noise test)
#define QF_EXPO_PIN 0 // [0 1]   development (r009 forest wash): 1 pins the exposure at QF_EXPO_PIN_LOG, so A/B frames are not re-metered
#define QF_EXPO_PIN_LOG 1.0 // [0.0 0.5 1.0 1.5 2.0]
#define QF_DUST_LEAF 1 // [0 1 2]   (r010: 2 keeps the full haze on rays longer than ~20 m, so the gap's beams reach the far leaves; owner r009 liked B's longer, broader rays)   development (r009 forest wash, canopy veil; r9xl1 canopy R 36.5 -> 28.4 at pinned exposure, dust_b beam -4 %): 1 cuts the beam dust haze to 0.4 on rays that end on leaves

// Calibration variants for the owner's taste survey (Shader Lab round r000). 0 is the
// pack as tuned; 1-3 are the survey's options A-C. Development only: not on the option
// screen, and never a default. tools/shaders/review/calibration.py renders them.
#define QF_CAL_GRADE 0 // [0 1 2 3]   direction: A photoreal, B cinematic, C storybook
#define QF_CAL_NIGHT 0 // [0 1 2 3]   night: A truly dark, B moonlit blue, C gentle
#define QF_CAL_SUNSET 0 // [0 1 2 3]  golden hour: A intense gold, B pastel, C naturalistic
#define QF_CAL_WATER 0 // [0 1 2 3]   water: A clear tropical, B deep dark, C depth gradient
#define QF_CAL_FOG 0 // [0 1 2 3 4]   distance: A crisp, B natural haze, C thick valley fog, 4 blizzard (r001)
#define QF_CAL_BLOOM 0 // [0 1 2 3]   bloom: A none, B subtle, C strong
#define QF_BIOME_FOG 1 // [0 1]   fog by biome and weather (r001: on, only where justified; shaders.properties)
#define QF_TINT_SAT 0.85 // [0.7 0.85 1.0]   development (a4): biome-tint saturation (1.0 = vanilla)
#define QF_TINT_RED 0.92 // [0.85 0.92 1.0]   development (a4): biome-tint red (less yellow)
#define QF_DEEP_SLOPE 0.6 // [0.3 0.45 0.5 0.6 0.72 0.8 1.0]   development (a2): exposure compensation below a full moon
#define QF_NEW_MOON_FLOOR 1.0 // [0.5 0.7 1.0 1.2]   development (a2): night floor left at new moon
#define QF_AIRGLOW 0.004 // [0.0 0.002 0.004 0.006 0.012]   development (a4): night-sky airglow, in MOON_I units
#define QF_MOON_GAIN 7.0 // [3.0 4.0 5.5 7.0 10.0 14.0 60.0]   development (a2): moon disk brightness
#define QF_CAL_GOLD 2 // [0 1 2]     golden hour: 1 amber light on lit faces, 2 that plus gold sky near the sun (owner r001: B)
#define QF_GOLD_SKY 1.5 // [0.6 1.0 1.5 2.0 2.5]   development (r002): strength of the gold sky near the sun (owner r002: 1.5, "maybe more gold")
#define QF_HAZE 0.35 // [0.2 0.35 0.4 0.6 0.8 1.0]   development (r002): distance-haze density (owner r002: 0.35, "definitely the best")
#define QF_HORIZON_FLOOR 1 // [0 1]   development (r002): the sky below the horizon fades to a darker, cooler far-land tone (no beige wall)
#define QF_TORCH_WARM 4 // [0 1 2 3 4]   development (r002): block-light colour. 0 r001 (~4000 K), 1 tungsten, 2 tungsten to candle with distance (r002 pick), 3 candle, 4 a little warmer than 2 (owner r002)
#define QF_WATER_STYLE 3 // [0 1 2 3 4]   development (r002): 0 r001 (sky-only Fresnel), 1 calm (reflections, glitter, ripples), 2 lively, 3 calm by day and lively at low sun (owner r002: C at sunset, B at noon; owner r005: C, lively wins at sunset), 4 calm mirror (owner r004: A; reversed in r005)
#define QF_WAVES 1 // [0 1]   development (r006): 0 r005's swells and ripples, 1 spectral waves (layered ocean-spectrum height field, detail fading with the pixel footprint, filtered detail kept as roughness), with exact Fresnel, caustics and shore foam (owner r005: "a serious jump in quality")
#define QF_FOAM 1 // [0 1]   development (r006): foam where the water is shallow at the shore (QF_WAVES 1)
#define QF_CAUSTICS 1 // [0 1]   development (r006): sunlight caustics on shallow beds (QF_WAVES 1)
#define QF_WATER_COLOR 0 // [0 1 2]   development (r002): 0 clear depth gradient, 1 teal-green, 2 deep blue (fallback when QF_BIOME_WATER is 0)
#define QF_BIOME_WATER 1 // [0 1]   water colour by biome (owner r002): glassy lakes and rivers, deep-blue ocean, turquoise coast and reef, murky teal swamp
#define QF_WATER_FORCE 0 // [0 1 2 3 4 5]   development (r003): force one biome water (1 glassy, 2 ocean, 3 reef, 4 swamp, 5 river) for the Shader Lab
#define QF_GLITTER 0 // [0 1 2]   development (r003; owner r003: A, 0 "so much more balanced"): sunset water. 0 r002 lively (hash sparkles), 1 sparkles from the surface's own micro-ripples, 2 that plus a cinematic sun (aureole, a brighter, wider path)
#define QF_FLECKS 1 // [0 1]   development (r003): bright bubble and foam flecks on near water (owner r003: "a bit much"; r002's near-water sparkles, QF_GLITTER 0, are the "bubbles" he liked; owner r004: 1.25x round 3's full amount)
#define QF_AMBER 0 // [0 1 2]   development (r003): golden-hour amber on lit faces and through leaves. 0 r002 (owner r003: B on golden and leaves), 1 amber with sunlit leaves glowing, 2 strong
#define QF_NEW_MOON 0.25 // [0.1 0.25 0.35 0.5 0.65]   development (r003): moon and sky light left at new moon (r002 0.1 crushed the sky to brown-black; owner r002: keep the full-moon feel, a bit darker; owner r003: B 0.25, "deep rich darkness")
#define QF_SUN_SPARKLE 1 // [0 1]   development (r004/r005): bright, steady glints right under a low sun (owner r003: "spots right below the sun that have the light intensity depth")
#define QF_MOTES 1 // [0 1 2]   development (r003): ambient particles: dust and pollen in sunbeams, torch-lit dust underground, bubbles under water. 2 denser
#define QF_FLICKER 1 // [0 1]   development (r003): torchlight breathes slightly, varying from place to place
#define QF_AERIAL 1 // [0 1]   development (r003): aerial perspective, distant land turns blue and pale (owner r002: Extreme Hills bland; r003: his golden and leaves picks had it off, and he rejected the hills colour range; r004: B, on)
#define QF_HAZE_HEIGHT 1 // [0 1]   development (r005): haze and aerial perspective by height below the camera as well as distance (owner r004: haze where the land drops away, not over land at eye level)
#define QF_SHAFTS 1 // [0 1 2]   (r006: sharper, gain 1.5, owner r005 forest A + leaves B)   development (r005): volumetric sunlight through gaps (light shafts), warm at golden hour (owner r004: "more cinematic light"). 2 stronger
#define QF_NIGHT_SKY 0 // [0 1 2 3 4]   (r007: the rotation is the default, owner r006: the Milky Way "fucking beautiful", give it more nights; 4 a meteor shower all night)   development (r005): night sky. 0 a rotation night by night, 1 deep clear starfield (owner r005: A, the default), 2 airglow bands (owner r005: underwhelming), 3 Milky Way, since r006 the ESO/S. Brunier photographic panorama (owner r005: the drawn band looked hand-drawn)
#define QF_METEOR_RATE 4 // [1 2 3 4 8]   (ub: 3 left ua's night frames empty)   development (r007): meteor-shower slots (QF_NIGHT_SKY 4); 1 is a meteor every few seconds somewhere in the sky, 3 (r008; owner r007: "I would expect more than 2") one or two in flight at any moment, each leaving a glowing train, 8 a storm
#define QF_SUN 1 // [0 1]   development (r007): 1 the real sun (true size, sharp limb-darkened disk, reddening toward the horizon, glare drawn over what is in front of it, scaled by how much of the disk shows); 0 r006 (three times the size, soft edge, a halo in the sky only) (owner r006: "the sun has not improved at all")
#define QF_SUN_SIZE 15.0 // [3.0 5.0 8.0 10.0 12.0 15.0 18.0]   (r008 loop 2: 5.0 drew a 20 px disk at 2560 wide, CR about 65 px; 15 is 3x)   (ub: 3.0 drew a 30 px disk at 1440p; the refs draw 60-70 px)   (r008; owner r007: "a little larger ... even a bit bigger than the 1.8x", round 6's disk "has some form to it and it is visible": 3.0, about round 6's size, with the sharp limb)   development (r007): sun disk size, 1 the real sun (0.27 degrees in radius terms 0.0047 rad); larger as a longer lens would show it
#define QF_LENS 0 // [0 1]   development (r007): a faint lens effect round a visible sun (a few dim ghosts toward the screen centre, a faint six-point starburst); off by default (look bible 7)
#define QF_UW_VIS 2.0 // [1.0 1.4 2.0]   (r010 loop 2: 2.0, far-terrain local contrast 1.10 -> 1.55, +41 %; 1.4 +27 %)   (r010; owner r009 underwater B: "the visibility is a little bit low") clear-water (not swamp) fog thinned by this factor, hue kept; the sunbeams unchanged
#define QF_RIVER_TINT 1 // [0 1 2]   (r010; owner r009 river: "very green") 0 r009 green-brown silty stream (water 51,79,63); 1 the same murk, teal-blue instead of green (50,74,80); 2 clear stream: glassier water and the bed's veil cut from 2.2 to 0.6 blocks, so ledges and stones show
#define QF_SUN_CLOUD 1 // [0 1 2]   (r010; owner r009 sun-cloud: "make sure that the sun is interacting realistically with the clouds in front of it") 0 r009: clouds within 20 deg of a low sun melt to ~20 % into the haze while still hiding the disk; 1 no melt near the sun or moon, so the cloud in front is a dark body with lit edges; 2 as 1 with the silver lining 2.5x on the thinnest fringe
#define QF_SHALLOW_SUN 0 // [0 1 2]   development (r010 session 3: NOT the mint's cause, which was the sky seen through deep water, fixed in composite; ss0/ss1/ss2 mint 692/661/686 px, so it stays off) sunlight reaching a shallow bed: 0 r009 (the filter fades out as the sun sets, so golden-lit sand under the sea turns mint); 1 the surface's Fresnel transmission (27 % at 3 deg) and the filter held to the horizon; 2 as 1, and at low sun the bed's light counts as mostly the sun's, so sunset shallows go dark and mirror the sky
#define QF_CREP_I 0.3 // [0.15 0.3 0.6 1.0]   (r011) crepuscular rays strength (QF_CREPUSCULAR 2), in sun irradiance (loop 1: 0.05 gave ~0.003, 1 % of the sky; 0.3 puts a lit lane near a low sun at ~half the sky there)
#define QF_PH_FOG 1.0 // [0.5 1.0 1.5 2.0]   (r011) Photon air-fog density on top of its defaults (scaled to a 256-block view)
#define QF_ATMOS 1 // [0 1]   (r011; owner r010 sunset-full: "the sun reads as a single hot spot rather than affecting the lighting of the whole atmosphere") 1 Photon 1.4's atmosphere, ported (lib/photon.glsl): its precomputed sky scattering with the horizon stretch, its sun tint and exposure by the hour, and its analytic air fog lit by the sun (thick and low at dawn and dusk); 0 round 10 (our Hillaire tables with the hand-made golden sky and haze)
#define QF_CREPUSCULAR 2 // [0 1 2]   (r011: 2 Photon's, ported: a world-space march from the eye to the cloud base through a cloud shadow map built in prepare, 20 steps at the horizon (12 Medium), 4 at the zenith, Medium and up; owner r010 sun-cloud B "only if we can afford them")   (r010; open owner question, ops/DECISIONS.md; High and Ultra only) crepuscular rays: sunbeams fanning from a low sun through the gaps between clouds, a screen-space march toward the sun over the sky's cloud transmittance
#define QF_METAL_FLOOR 1 // [0 1]   (r010; texture track: gold 150,126,1 under the shader vs 178,152,34 vanilla) 1 metals keep most of their diffuse look under the reflection (PBR off 0.65 -> 0.92, PBR on 0.30 -> 0.62), so gold and iron are never darker than plain blocks; 0 r009
#define QF_METAL_F0 1 // [0 1]   (r010; texture track: gold's top third showed a lime sheen) 1 LabPBR's hard-coded metals (F0 bytes 230-237: iron, gold, aluminium, chrome, copper, lead, platinum, silver) reflect with the real metal's colour, shaded by the texture's brightness; 0 r009 (the texture colour, which the grade pushes toward lime on gold)
#define QF_CLOUD_RIM 1 // [0 1]   development (r007): sharp silver linings and rim light on cloud edges toward a low sun (owner r006, golden: "a sharper highlight effect on the edges of the clouds")
#define QF_SHAFT_STYLE 1 // [0 1]   development (r007): 1 round 5's warm, open rays with r006's finer sampling (owner r006: round 5's frame, "warmer, the rays are better formed"); 0 r006's contrast-shaped rays
#define QF_VIBRANCE 0.25 // [0.0 0.1 0.15 0.2 0.25 0.3 0.35]   (r008; owner r007: "somewhere between .15 and .35")   colour vibrance: lifts the muted colours more than the already vivid ones, so wood and gold do not turn neon (owner r006: "a little more vibrance"); 0 is r006
#define QF_BOUNCE 1 // [0 1]   development (r007): sunlight bounced off the lit ground onto walls and undersides, and a faint sheen on every block at grazing light (owner r006: "the light to interact with the blocks realistically")
#define QF_WATER_BLEND 1 // [0 1]   development (r007): water colour by position as well as by the camera's biome: swamp water from the game's own per-block swamp tint, blended over several blocks, deep water toward ocean blue, so biome borders are gradients (owner r006: "a pleasant gradient ... instead of stark cutoffs")
#define QF_PBR 1 // [0 1]   (r008: on; owner r007 picked maps on, and metal blocks now reflect like metal with or without maps)   development (r007): read LabPBR 1.3 normal and specular maps from the resource pack (Iris normals/specular atlases), for packs that have them
#define QF_METEOR_SHOW 0 // [0 1]   development (r008 loop 3; critic: the stills never catch a meteor) 1 pins two meteors with trains in front of the camera, for the vote stills
#define QF_METEOR_STYLE 4 // [0 1 2 3 4 5]   (r011; owner r010 B 3/5 with reference photos: many long thin straight streaks out of one point, and "improve performance again") 4 a shower on great circles out of a radiant 18-45 deg up, the sky cut into 96 wedges round it, one meteor slot each, a pixel tests 3; 5 the same as a storm (240 wedges, fainter);   (r010; owner r009: "it doesn't look like the meteors are coasting through the atmosphere overhead ... they're plummeting ... a bunch of them passing by at high altitude") 0 r009's high-radiant shower; 1 Earth-grazers: the radiant on the horizon, so every meteor skims the upper air at ~100 km on a long, near-level path, 1-4 s, drawn in 3D so overhead ones sweep across the sky and far ones creep along the horizon; 2 grazers plus a fireball procession (one slow fireball breaking into a chain of fragments that crosses the whole sky); 3 a grazer storm (three times the rate, mostly faint, lingering trains)
#define QF_METEOR_RAZ -1 // [-1 0 20 45 90 135 180 270]   development (r010): the grazers' radiant bearing in degrees for A/B frames (shader azimuth: 0 +x east, 90 +z south); -1 a new bearing every night
#define QF_METEOR_SLOW 1.0 // [0.25 0.5 1.0]   development (r010): meteor time scale, for Lab clips only: the burst writer takes ~0.4 s a frame at uneven intervals, so a clip is shot at 0.25 and make_clip.py --speedup 4 plays it back at game speed
#define QF_METEOR_PROC_P 18.0 // [9.0 18.0 120.0 600.0]   development (r010): seconds between fireball processions (style 2); short for the Lab clips, long for play
#define QF_DUST_DBG 0 // [0 1 2 3]   development (r008 ud): 1 lights every sunlit mote, to tell a missing mote from a failed beam test; 2 near grid only, 3 far grid only (loop 4)
#define QF_DUST 1 // [0 1 2]   (r008; owner r007: "dust should only be visible in light shafts ... we can do WAYY better") dust that lives in the sunbeams: a drifting 3D dust field in the lit air of the light shafts, and a few tumbling flakes that glint only where a beam crosses the view. 0 r007's free-floating motes, 2 thicker
#define QF_VOL_FAST 1 // [0 1]   (r009; cost run: shafts 1.84 ms and dust+motes 1.48 of High's 4.6, budget 3.0) cheaper volumetrics: fewer shaft steps (TAA resolves the jitter), dust clumps sampled on every other step, Low's beam haze without clumps, and no dust walk on rays the shaft march found free of shade. 0 r008's loops
#define QF_GOLD_HORIZON 1.0 // [0.0 0.6 1.0 1.4]   (r008; owner r007 and critic: the golden-hour horizon is "still pretty weak") a warm band low round the whole horizon at golden hour, gold toward the sun and rose opposite it, and warm haze
#define QF_LAKE_CALM 1 // [0 1]   (r008; owner r007 lake 2/5, follow the critic) sheltered lakes stay a calm mirror at low sun instead of taking the ocean's sunset chop
#define QF_UNDERWATER 1 // [0 1]   (r008; owner r007: Conquest's underwater ambience) under water: sunbeams through the water from the shadow map, caustics dancing on the bed and walls, denser drifting bubbles
#define QF_SUN_GLOW 1 // [0 1]   development (r006): a soft halo round the sun disk (the eye's and the lens's glare), no wider than a few degrees
#define QF_CLOUD_COVER 0.0 // [-0.04 0.0 0.04 0.08]   development (r006): cloud threshold offset; positive is fewer, smaller clouds
#define QF_CLOUDS 2 // [0 1 2]   (r006: true 3D shapes, light by the hour, moonlit at night)   development (r003/r005): 1 the r003 flat deck, 2 raymarched broken clouds (owner r004: D, dramatic broken clouds, "dynamic ... beautiful and natural"), with shadows on the land

// 0 Potato, 1 Low, 2 Medium, 3 High, 4 Ultra.
#if QF_PRESET == 0
    #define QF_SHADOWS 0
    #define QF_TAA 0
    #define QF_SHADOW_TAPS 0
    #define QF_SKY_STEPS 12
    #define QF_AO_STRENGTH 0.6
    #define QF_SSR_STEPS 0
    #define QF_CREP_STEPS 6
#elif QF_PRESET == 1
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 0
    #define QF_SKY_STEPS 12
    #define QF_AO_STRENGTH 0.6
    #define QF_SSR_STEPS 0
    #define QF_CREP_STEPS 8
#elif QF_PRESET == 2
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 4
    #define QF_SKY_STEPS 20
    #define QF_AO_STRENGTH 0.8
    #define QF_SSR_STEPS 12
    #define QF_CREP_STEPS 12
#else
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 8
    #define QF_SKY_STEPS 24
    #define QF_AO_STRENGTH 0.8
    #define QF_SSR_STEPS 20
    #define QF_CREP_STEPS 20
#endif

// Shadow map per tier (rules 2 and 5). Iris reads these consts after preprocessing.
#if QF_PRESET <= 1
    const int shadowMapResolution = 1024;
    const float shadowDistance = 48.0;
#elif QF_PRESET == 2
    const int shadowMapResolution = 1536;
    const float shadowDistance = 80.0;
#elif QF_PRESET == 3
    const int shadowMapResolution = 2048;
    const float shadowDistance = 112.0;
#else
    const int shadowMapResolution = 2048;
    const float shadowDistance = 144.0;
#endif
#if QF_PRESET == 2
    const float entityShadowDistanceMul = 0.25;
#elif QF_PRESET == 3
    const float entityShadowDistanceMul = 0.5;
#else
    const float entityShadowDistanceMul = 1.0;
#endif
const float shadowDistanceRenderMul = 1.0;
const float sunPathRotation = -22.0;
// shadowtex0 stays a plain depth texture: lib/shadows.glsl compares it itself (see there why).
