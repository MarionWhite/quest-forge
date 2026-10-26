// Player-facing options and the preset table (docs/design/shaders/performance-rules.md).
// Every effect keys off QF_PRESET; the profiles in shaders.properties only set it.
// No valueless #defines in this file: Iris would list them as on/off options.

#define QF_PRESET 2 // [0 1 2 3 4]
#define QF_NIGHT_FLOOR 1.0 // [0.0 0.5 0.75 1.0 1.5 2.0 3.0]
#define QF_EXPOSURE_BIAS 0.0 // [-1.5 -1.0 -0.5 0.0 0.5 1.0 1.5]
#define QF_WAVING 1 // [0 1]
#define QF_DEBUG_VIEW 0 // [0 1 2 3 4 5 6 7 8 9 10]
#define QF_STILL 0 // [0 1]   development: freeze wind, waves and twinkle (temporal-noise test)

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
#define QF_CLOUD_RIM 1 // [0 1]   development (r007): sharp silver linings and rim light on cloud edges toward a low sun (owner r006, golden: "a sharper highlight effect on the edges of the clouds")
#define QF_SHAFT_STYLE 1 // [0 1]   development (r007): 1 round 5's warm, open rays with r006's finer sampling (owner r006: round 5's frame, "warmer, the rays are better formed"); 0 r006's contrast-shaped rays
#define QF_VIBRANCE 0.25 // [0.0 0.1 0.15 0.2 0.25 0.3 0.35]   (r008; owner r007: "somewhere between .15 and .35")   colour vibrance: lifts the muted colours more than the already vivid ones, so wood and gold do not turn neon (owner r006: "a little more vibrance"); 0 is r006
#define QF_BOUNCE 1 // [0 1]   development (r007): sunlight bounced off the lit ground onto walls and undersides, and a faint sheen on every block at grazing light (owner r006: "the light to interact with the blocks realistically")
#define QF_WATER_BLEND 1 // [0 1]   development (r007): water colour by position as well as by the camera's biome: swamp water from the game's own per-block swamp tint, blended over several blocks, deep water toward ocean blue, so biome borders are gradients (owner r006: "a pleasant gradient ... instead of stark cutoffs")
#define QF_PBR 1 // [0 1]   (r008: on; owner r007 picked maps on, and metal blocks now reflect like metal with or without maps)   development (r007): read LabPBR 1.3 normal and specular maps from the resource pack (Iris normals/specular atlases), for packs that have them
#define QF_METEOR_SHOW 0 // [0 1]   development (r008 loop 3; critic: the stills never catch a meteor) 1 pins two meteors with trains in front of the camera, for the vote stills
#define QF_DUST_DBG 0 // [0 1 2 3]   development (r008 ud): 1 lights every sunlit mote, to tell a missing mote from a failed beam test; 2 near grid only, 3 far grid only (loop 4)
#define QF_DUST 1 // [0 1 2]   (r008; owner r007: "dust should only be visible in light shafts ... we can do WAYY better") dust that lives in the sunbeams: a drifting 3D dust field in the lit air of the light shafts, and a few tumbling flakes that glint only where a beam crosses the view. 0 r007's free-floating motes, 2 thicker
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
#elif QF_PRESET == 1
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 0
    #define QF_SKY_STEPS 12
    #define QF_AO_STRENGTH 0.6
    #define QF_SSR_STEPS 0
#elif QF_PRESET == 2
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 4
    #define QF_SKY_STEPS 20
    #define QF_AO_STRENGTH 0.8
    #define QF_SSR_STEPS 12
#else
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 8
    #define QF_SKY_STEPS 24
    #define QF_AO_STRENGTH 0.8
    #define QF_SSR_STEPS 20
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
