// Light levels and the sky as seen from the camera: the two sky-view tables, the sun disk,
// the moon with its phase, and stars. Needs lib/atmosphere.glsl and lib/lut.glsl.
//
// Units are arbitrary but consistent: the sun delivers SUN_I at the top of the atmosphere.
// Auto-exposure (prepare.fsh) maps whatever arrives to the screen, inside fixed bounds, so
// these ratios -- sun : sky : moon : torch : night floor -- are what the look depends on.

const float SUN_I = 3.0;
const float MOON_I = SUN_I * 0.008;              // full moon, before the phase factor
const vec3  MOON_TINT = vec3(0.78, 0.88, 1.0);     // a slight blue shift for scotopic night
const vec3  BLOCK_LIGHT_COLOR = vec3(1.0, 0.64, 0.38);   // about 2800 K, linear, eased so stone stays stone
const float BLOCK_I = 1.25;
const float NIGHT_FLOOR_I = 0.009;                // irradiance everywhere, scaled by QF_NIGHT_FLOOR
const vec3  NIGHT_FLOOR_TINT = vec3(0.8, 0.88, 1.0);

const float SUN_DISK_RADIUS = 0.0095;   // radians; about twice the real sun, for readability
const float MOON_DISK_RADIUS = 0.0125;

float moonIntensity() {
    // A new moon still leaves starlight and airglow: a tenth of the full moon.
    return MOON_I * mix(0.1, 1.0, moonBrightness());
}

float valueNoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash12(i), hash12(i + vec2(1, 0)), f.x),
               mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), f.x), f.y);
}

// Radiance of the moon disk at dir (0 outside it). The lit fraction follows moonPhase:
// 0 full, 4 new, waxing and waning on opposite limbs.
vec3 moonDisk(vec3 dir, vec3 moonDir) {
    float c = dot(dir, moonDir);
    float cr = cos(MOON_DISK_RADIUS);
    if (c < cr) return vec3(0.0);
    vec3 right = normalize(cross(moonDir, vec3(0.0, 0.0, 1.0)) + vec3(1e-5));
    vec3 upv = cross(right, moonDir);
    vec2 p = vec2(dot(dir, right), dot(dir, upv)) / sin(MOON_DISK_RADIUS);
    float rr = dot(p, p);
    if (rr > 1.0) return vec3(0.0);
    vec3 n = vec3(p, sqrt(1.0 - rr));
    float a = float(moonPhase) * (PI / 4.0);
    vec3 l = vec3(sin(a), 0.0, cos(a));
    float lit = smoothstep(-0.05, 0.12, dot(n, l));
    float maria = 0.72 + 0.28 * valueNoise(p * 3.1 + 7.0) * valueNoise(p * 7.3 + 1.0);
    float edge = smoothstep(1.0, 0.93, rr);
    return MOON_I * 160.0 * (lit * maria + 0.015) * edge * MOON_TINT;
}

vec3 sunDisk(vec3 dir, vec3 sunDir) {
    float c = dot(dir, sunDir);
    float cr = cos(SUN_DISK_RADIUS);
    if (c < cr) return vec3(0.0);
    float x = clamp((1.0 - c) / (1.0 - cr), 0.0, 1.0);    // 0 centre, 1 limb
    float mu = sqrt(1.0 - x);
    float limb = 1.0 - 0.6 * (1.0 - pow(mu, 0.8));        // limb darkening
    return vec3(SUN_I * 420.0 * limb * smoothstep(1.0, 0.85, x));
}

vec3 stars(vec3 dir) {
    vec3 p = dir * 520.0;
    vec3 cell = floor(p);
    float h = hash13(cell);
    if (h < 0.9975) return vec3(0.0);
    vec3 centre = cell + 0.5 + (vec3(hash13(cell + 1.7), hash13(cell + 3.1), hash13(cell + 5.3)) - 0.5) * 0.6;
    float d = length(p - centre);
    float b = (h - 0.9975) / 0.0025;
    float twinkle = 0.75 + 0.25 * sin(animTime() * (2.0 + 3.0 * b) + h * 100.0);
    vec3 tint = mix(vec3(0.8, 0.88, 1.0), vec3(1.0, 0.9, 0.75), hash13(cell + 9.1));
    return tint * SUN_I * 0.0018 * b * b * twinkle * smoothstep(0.55, 0.0, d);
}

// Scattered light only: what the sky adds in front of anything (fog, reflections).
vec3 skyScatter(vec3 dir) {
    vec3 L = SUN_I * lookupSkyView(dir, sunDirWorld(), LUT_SV_SUN)
           + moonIntensity() * MOON_TINT * lookupSkyView(dir, moonDirWorld(), LUT_SV_MOON);
    // Rain: a duller, darker, less saturated sky (look bible 9).
    float g = luminance(L);
    return mix(L, vec3(g) * 0.55, rainStrength * 0.75);
}

// The full sky in a direction: scattering plus the sun, moon and stars seen through it.
vec3 skyRadiance(vec3 dir) {
    vec3 L = skyScatter(dir);
    float r = cameraRadius();
    if (distToGround(r, dir.y) < 0.0) {
        vec3 T = lookupTransmittance(r, dir.y) * (1.0 - 0.9 * rainStrength);
        vec3 sunDir = sunDirWorld();
        L += T * (sunDisk(dir, sunDir) + moonDisk(dir, moonDirWorld()));
        float night = 1.0 - smoothstep(-0.12, 0.04, sunDir.y);
        L += T * stars(dir) * night;
    }
    return L;
}
