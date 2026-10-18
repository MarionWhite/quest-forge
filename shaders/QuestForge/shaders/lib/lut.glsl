// colortex5 layout (256 x 320, RGBA16F, never cleared) and lookups into it.
//
//   y   0- 63, x 0-255   transmittance
//   y  64- 95, x 0- 31   multi-scatter
//   y  64,     x 32-39   per-frame constants (see C_* below)
//   y  65,     x 32-63   exposure meter, one column sum per texel (prepare.glsl)
//   y  96-207, x 0-191   sky-view, lit by the sun   (radiance for unit sun irradiance)
//   y 208-319, x 0-191   sky-view, lit by the moon  (radiance for unit moon irradiance)
// Every lookup clamps inside its region so bilinear filtering never bleeds between tables.

uniform sampler2D colortex5;

const ivec2 LUT_T_ORIGIN  = ivec2(0, 0);
const ivec2 LUT_T_SIZE    = ivec2(256, 64);
const ivec2 LUT_MS_ORIGIN = ivec2(0, 64);
const ivec2 LUT_MS_SIZE   = ivec2(32, 32);
const ivec2 LUT_SV_SUN    = ivec2(0, 96);
const ivec2 LUT_SV_MOON   = ivec2(0, 208);
const ivec2 LUT_SV_SIZE   = ivec2(192, 112);
const vec2  LUT_TEX_SIZE  = vec2(256.0, 320.0);

const ivec2 C_EXPOSURE = ivec2(32, 64);   // r: exposure multiplier, g: metered log2 luminance,
                                          // b + a: log2 exposure, split high/low (prepare.glsl)
const ivec2 C_SUN      = ivec2(33, 64);   // rgb: sun irradiance at the camera (after the atmosphere)
const ivec2 C_MOON     = ivec2(34, 64);   // rgb: moon irradiance at the camera
const ivec2 C_AMB_UP   = ivec2(35, 64);   // rgb: sky irradiance on an up-facing surface
const ivec2 C_AMB_SIDE = ivec2(36, 64);   // rgb: on a vertical surface (azimuth average)
const ivec2 C_STATE    = ivec2(37, 64);   // r: frames the static tables have been built for,
                                          // g, b: ping-pong probes for debug view 8
const ivec2 C_METER    = ivec2(38, 64);   // r: log2 log-average, g: log2 mean, b: log2 target,
                                          // a: frameCounter % 2048 (debug view 8 only)

vec4 lutFetch(ivec2 p) {
    return texelFetch(colortex5, p, 0);
}

vec2 lutUv(vec2 x, ivec2 origin, ivec2 size) {
    vec2 t = clamp(x, 0.0, 1.0) * (vec2(size) - 1.0) + 0.5;
    return (vec2(origin) + t) / LUT_TEX_SIZE;
}

vec3 lookupTransmittance(float r, float mu) {
    return texture(colortex5, lutUv(transmittanceParams(r, mu), LUT_T_ORIGIN, LUT_T_SIZE)).rgb;
}

// Transmittance to the light, with the planet's shadow as a soft band at the horizon.
vec3 lightTransmittance(float r, float mu) {
    float muHorizon = -sqrt(max(1.0 - (ATM_RG * ATM_RG) / (r * r), 0.0));
    float earth = smoothstep(muHorizon - 0.01, muHorizon + 0.01, mu);
    return lookupTransmittance(r, max(mu, muHorizon)) * earth;
}

vec3 lookupMultiScatter(float r, float muSun) {
    vec2 x = vec2(muSun * 0.5 + 0.5, (r - ATM_RG) / (ATM_RT - ATM_RG));
    return texture(colortex5, lutUv(x, LUT_MS_ORIGIN, LUT_MS_SIZE)).rgb;
}

vec3 lookupSkyView(vec3 dir, vec3 lightDir, ivec2 origin) {
    vec2 x = skyViewParams(dir, lightDir, cameraRadius());
    return texture(colortex5, lutUv(x, origin, LUT_SV_SIZE)).rgb;
}

float exposure() {
    return lutFetch(C_EXPOSURE).r;
}

// Exposure bounds (linear multipliers on scene radiance). The upper bound keeps nights
// dark instead of letting the camera turn them into a grey day (look bible 1 and 2).
const float EXPOSURE_MIN = 0.12;
const float EXPOSURE_MAX = 48.0;
const float EXPOSURE_MEAN_WEIGHT = 0.75;  // prepare.glsl, meteredLog

// The exposure the meter asks for, as log2, from the metered log2 luminance m: a curve in
// log space with three pieces (round 9, fitted to the round-8 frames once exposure
// finally adapted; r08 nights came out at three times Complementary's brightness).
//   brighter than a sunny day (m > -3.64): full adaptation, the day key (exposure 2.4);
//   day to full-moon night (m = -10.7): partial, exposure rises only 2x over 7 stops, so a
//     dusk or a torch-lit tunnel stays dim instead of being lifted to noon (look bible 1-2);
//   below the full moon: steeper (0.55 stop per stop), so a new moon stays readable.
const float EXPO_DAY_M = -3.64, EXPO_DAY_E = 1.24;
const float EXPO_NIGHT_M = -10.7, EXPO_NIGHT_E = 2.26;
const float EXPO_DEEP_SLOPE = 1.0;   // r12: 0.8 crushed 3% of the new-moon frame
// Under open sky a dark scene is night, which must stay readable; underground it is a cave
// or a tunnel, which should stay dark (round 9: the torch tunnel matched vanilla's 0.17-0.2
// mean luma, but the full moon fell to 0.038 and the new moon crushed). So the sky light
// at the eye adds up to EXPO_SKY_LIFT stops, scaled by how far below daylight the scene is.
const float EXPO_DUSK_LIFT = 0.6;
const float EXPO_SKY_LIFT = 0.3;   // owner (r000): between truly dark and moonlit; r11 0.8 gave 0.060 / 0.045
float exposureTargetLog(float m) {
    float e;
    if (m >= EXPO_DAY_M) {
        e = EXPO_DAY_E - (m - EXPO_DAY_M);
    } else if (m >= EXPO_NIGHT_M) {
        e = mix(EXPO_DAY_E, EXPO_NIGHT_E, (EXPO_DAY_M - m) / (EXPO_DAY_M - EXPO_NIGHT_M));
    } else {
        e = EXPO_NIGHT_E + (EXPO_NIGHT_M - m) * EXPO_DEEP_SLOPE;
    }
    float darkness = clamp((EXPO_DAY_M - m) / (EXPO_DAY_M - EXPO_NIGHT_M), 0.0, 1.0);
    float eyeSky = clamp(float(eyeBrightnessSmooth.y) / 240.0, 0.0, 1.0);
    e += EXPO_SKY_LIFT * darkness * eyeSky * eyeSky;
    // Golden hour and dusk under open sky: a little more, peaking between day and night, so a
    // low-sun foreground reads lit rather than murky (r10-r12 critic and owner, round 0).
    e += EXPO_DUSK_LIFT * sin(PI * darkness) * eyeSky * eyeSky;
#if QF_CAL_NIGHT == 1
    e -= 1.2 * darkness * eyeSky * eyeSky;   // calibration A: truly dark
#elif QF_CAL_NIGHT == 3
    e += 1.5 * darkness * eyeSky * eyeSky;   // calibration C: gentle
#endif
    return clamp(e, log2(EXPOSURE_MIN), log2(EXPOSURE_MAX)) + QF_EXPOSURE_BIAS;
}

vec3 sunIrradiance()  { return lutFetch(C_SUN).rgb; }
vec3 moonIrradiance() { return lutFetch(C_MOON).rgb; }

// Sky irradiance for a surface facing n (world space), with a little ground bounce below.
// The physical sky alone leaves shaded faces near-black and strongly blue (round 1: a
// stone cliff in shade read as blue). Minecraft's look keeps shade readable and close to
// neutral, so the sky term is lifted and part-desaturated (look bible 3).
const float AMBIENT_GAIN = 1.9;
const float AMBIENT_DESAT = 0.45;
const float AMBIENT_LOW_SUN_CUT = 0.0;   // r10 critic: 0.45 left golden-hour shade murky; shade should read cool blue

vec3 skyIrradiance(vec3 n) {
    vec3 up = lutFetch(C_AMB_UP).rgb;
    vec3 side = lutFetch(C_AMB_SIDE).rgb;
    vec3 down = up * GROUND_ALBEDO * 0.6;
    vec3 e = n.y >= 0.0 ? mix(side, up, n.y) : mix(side, down, -n.y);
    float g = dot(e, vec3(0.2126, 0.7152, 0.0722));
    // With the sun low the sky's warm horizon and blue zenith are the golden-hour look, so
    // less desaturation then (round 3: sunset and golden hour came out colourless).
    float sunY = normalize(mat3(gbufferModelViewInverse) * sunPosition).y;
    float desat = AMBIENT_DESAT * smoothstep(0.05, 0.35, sunY);
    // Golden hour: the lift that keeps noon shade readable also drowned the low, warm sun in
    // blue fill (rounds 3 to 5: golden hour colourless). Less fill while the sun is low, so
    // the warm direct light carries the colour; full again by mid-morning and at night.
    float lowSun = smoothstep(-0.05, 0.02, sunY) * (1.0 - smoothstep(0.10, 0.40, sunY));
    return mix(e, vec3(g), desat) * AMBIENT_GAIN * (1.0 - AMBIENT_LOW_SUN_CUT * lowSun);
}
