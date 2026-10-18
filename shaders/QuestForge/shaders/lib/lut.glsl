// colortex5 layout (256 x 320, RGBA16F, never cleared) and lookups into it.
//
//   y   0- 63, x 0-255   transmittance
//   y  64- 95, x 0- 31   multi-scatter
//   y  64,     x 32-39   per-frame constants (see C_* below)
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

const ivec2 C_EXPOSURE = ivec2(32, 64);   // r: exposure multiplier, g: log2 scene luminance, b: target
const ivec2 C_SUN      = ivec2(33, 64);   // rgb: sun irradiance at the camera (after the atmosphere)
const ivec2 C_MOON     = ivec2(34, 64);   // rgb: moon irradiance at the camera
const ivec2 C_AMB_UP   = ivec2(35, 64);   // rgb: sky irradiance on an up-facing surface
const ivec2 C_AMB_SIDE = ivec2(36, 64);   // rgb: on a vertical surface (azimuth average)
const ivec2 C_STATE    = ivec2(37, 64);   // r: frames the static tables have been built for

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

vec3 sunIrradiance()  { return lutFetch(C_SUN).rgb; }
vec3 moonIrradiance() { return lutFetch(C_MOON).rgb; }

// Sky irradiance for a surface facing n (world space), with a little ground bounce below.
// The physical sky alone leaves shaded faces near-black and strongly blue (round 1: a
// stone cliff in shade read as blue). Minecraft's look keeps shade readable and close to
// neutral, so the sky term is lifted and part-desaturated (look bible 3).
const float AMBIENT_GAIN = 1.9;
const float AMBIENT_DESAT = 0.45;

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
    return mix(e, vec3(g), desat) * AMBIENT_GAIN;
}
