// Player-facing options and the preset table (docs/design/shaders/performance-rules.md).
// Every effect keys off QF_PRESET; the profiles in shaders.properties only set it.
// No valueless #defines in this file: Iris would list them as on/off options.

#define QF_PRESET 2 // [0 1 2 3 4]
#define QF_NIGHT_FLOOR 1.0 // [0.0 0.5 0.75 1.0 1.5 2.0 3.0]
#define QF_EXPOSURE_BIAS 0.0 // [-1.5 -1.0 -0.5 0.0 0.5 1.0 1.5]
#define QF_WAVING 1 // [0 1]
#define QF_DEBUG_VIEW 0 // [0 1 2 3 4 5 6 7 8 9]
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
#define QF_WATER_STYLE 3 // [0 1 2 3]   development (r002): 0 r001 (sky-only Fresnel), 1 calm (reflections, glitter, ripples), 2 lively, 3 calm by day and lively at low sun (owner r002: C at sunset, B at noon)
#define QF_WATER_COLOR 0 // [0 1 2]   development (r002): 0 clear depth gradient, 1 teal-green, 2 deep blue (fallback when QF_BIOME_WATER is 0)
#define QF_BIOME_WATER 1 // [0 1]   water colour by biome (owner r002): glassy lakes and rivers, deep-blue ocean, turquoise coast and reef, murky teal swamp
#define QF_WATER_FORCE 0 // [0 1 2 3 4]   development (r003): force one biome water (1 glassy, 2 ocean, 3 reef, 4 swamp) for the Shader Lab
#define QF_GLITTER 0 // [0 1 2]   development (r003; owner r003: A, 0 "so much more balanced"): sunset water. 0 r002 lively (hash sparkles), 1 sparkles from the surface's own micro-ripples, 2 that plus a cinematic sun (aureole, a brighter, wider path)
#define QF_FLECKS 0 // [0 1]   development (r003): bright bubble and foam flecks on near water (owner r003: "a bit much"; r002's near-water sparkles, QF_GLITTER 0, are the "bubbles" he liked)
#define QF_AMBER 0 // [0 1 2]   development (r003): golden-hour amber on lit faces and through leaves. 0 r002 (owner r003: B on golden and leaves), 1 amber with sunlit leaves glowing, 2 strong
#define QF_NEW_MOON 0.25 // [0.1 0.25 0.35 0.5 0.65]   development (r003): moon and sky light left at new moon (r002 0.1 crushed the sky to brown-black; owner r002: keep the full-moon feel, a bit darker; owner r003: B 0.25, "deep rich darkness")
#define QF_MOTES 1 // [0 1 2]   development (r003): ambient particles: dust and pollen in sunbeams, torch-lit dust underground, bubbles under water. 2 denser
#define QF_FLICKER 1 // [0 1]   development (r003): torchlight breathes slightly, varying from place to place
#define QF_AERIAL 0 // [0 1]   development (r003): aerial perspective, distant land turns blue and pale (owner r002: Extreme Hills bland; r003: his golden and leaves picks had it off, and he rejected the hills colour range)
#define QF_CLOUDS 0 // [0 1]   development (r003): a cheap cloud layer with its shadows on the land

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
