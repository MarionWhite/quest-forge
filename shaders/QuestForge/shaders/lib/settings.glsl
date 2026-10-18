// Player-facing options and the preset table (docs/design/shaders/performance-rules.md).
// Every effect keys off QF_PRESET; the profiles in shaders.properties only set it.
// No valueless #defines in this file: Iris would list them as on/off options.

#define QF_PRESET 2 // [0 1 2 3 4]
#define QF_NIGHT_FLOOR 1.0 // [0.0 0.5 0.75 1.0 1.5 2.0 3.0]
#define QF_EXPOSURE_BIAS 0.0 // [-1.5 -1.0 -0.5 0.0 0.5 1.0 1.5]
#define QF_WAVING 1 // [0 1]
#define QF_DEBUG_VIEW 0 // [0 1 2 3 4]
#define QF_STILL 0 // [0 1]   development: freeze wind, waves and twinkle (temporal-noise test)

// 0 Potato, 1 Low, 2 Medium, 3 High, 4 Ultra.
#if QF_PRESET == 0
    #define QF_SHADOWS 0
    #define QF_TAA 0
    #define QF_SHADOW_TAPS 0
    #define QF_SKY_STEPS 12
    #define QF_AO_STRENGTH 0.6
#elif QF_PRESET == 1
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 0
    #define QF_SKY_STEPS 12
    #define QF_AO_STRENGTH 0.6
#elif QF_PRESET == 2
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 4
    #define QF_SKY_STEPS 20
    #define QF_AO_STRENGTH 0.8
#else
    #define QF_SHADOWS 1
    #define QF_TAA 1
    #define QF_SHADOW_TAPS 8
    #define QF_SKY_STEPS 24
    #define QF_AO_STRENGTH 0.8
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
// Hardware PCF comes from the separate shadowtex0HW sampler, so shadowtex0 stays a plain depth texture.
