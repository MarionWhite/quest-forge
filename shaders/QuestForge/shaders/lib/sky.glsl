// Light levels and the sky as seen from the camera: the two sky-view tables, the sun disk,
// the moon with its phase, and stars. Needs lib/atmosphere.glsl and lib/lut.glsl.
//
// Units are arbitrary but consistent: the sun delivers SUN_I at the top of the atmosphere.
// Auto-exposure (prepare.fsh) maps whatever arrives to the screen, inside fixed bounds, so
// these ratios -- sun : sky : moon : torch : night floor -- are what the look depends on.

const float SUN_I = 3.0;
const float MOON_I = SUN_I * 0.008;              // full moon, before the phase factor
const vec3  MOON_TINT = vec3(0.78, 0.88, 1.0);     // a slight blue shift for scotopic night
// Block light (torches). r001's (1.0, 0.70, 0.45) is about 4000 K once taken to sRGB: the owner
// read it as "a fluorescent light bulb". Real tungsten (2700-3000 K) is about (1, 0.42, 0.13)
// linear and a candle (1900 K) (1, 0.24, 0.02). blockLightColor() in lib/lighting.glsl warms the
// colour with distance from the source, as a flame's light does, at vanilla-like luminance.
const vec3  BLOCK_LIGHT_COLOR = vec3(1.0, 0.70, 0.45);   // r001; still the emissive / lava base
const float BLOCK_I = 1.1;   // owner (r000): light sources must matter
const float NIGHT_FLOOR_I = 0.009;                // irradiance everywhere, scaled by QF_NIGHT_FLOOR
const vec3  NIGHT_FLOOR_TINT = vec3(0.8, 0.88, 1.0);

const float SUN_DISK_RADIUS = 0.016;    // radians; about three times the real sun, for readability
const float MOON_DISK_RADIUS = 0.035;   // about vanilla's moon size
const float MOON_DISK_GAIN = QF_MOON_GAIN;   // disk radiance in MOON_I units (was 60: clipped)

// The night floor (look bible 1). The moon phase now shows through partial exposure
// compensation (EXPO_DEEP_SLOPE), so the floor no longer has to fall at new moon; it is what
// keeps the near field readable then (a2: 0.7 crushed 19% of the new-moon land on High).
// Low and Potato get a little more: their shading crushes more at the same exposure (a2: Low's
// new-moon land 35% crushed against High's 19%, r14 critic: raise the floor, not exposure).
#if QF_PRESET <= 1
const float NIGHT_FLOOR_PRESET = 1.25;
#else
const float NIGHT_FLOOR_PRESET = 1.0;
#endif
// Their 12-step sky table also draws the night zenith ~30% darker (a6: luma 2 of 255 on Low).
#if QF_PRESET <= 1
const float AIRGLOW_PRESET = 1.6;
#else
const float AIRGLOW_PRESET = 1.0;
#endif
float nightFloor() {
    return NIGHT_FLOOR_I * NIGHT_FLOOR_PRESET * QF_NIGHT_FLOOR * mix(QF_NEW_MOON_FLOOR, 1.0, moonBrightness());
}

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
    // Maria: a few large dark seas plus finer mottling, so the disk reads as the moon. Round 14
    // drew it at 60x MOON_I, which clipped 98% of the disk to white after night exposure: no
    // maria and no visible phase. MOON_DISK_GAIN keeps the brightest highland under the clip.
    float seas = smoothstep(0.42, 0.62, valueNoise(p * 1.7 + vec2(3.3, 8.1)) * 0.65
                                     + valueNoise(p * 3.9 + 11.0) * 0.35);
    float mottle = 0.85 + 0.15 * valueNoise(p * 9.0 + 2.0);
    float maria = mix(1.0, 0.58, seas) * mottle;
    float limb = 0.82 + 0.18 * n.z;
    float edge = smoothstep(1.0, 0.93, rr);
    return MOON_I * MOON_DISK_GAIN * (lit * maria * limb + 0.012) * edge * MOON_TINT;
}

vec3 sunDisk(vec3 dir, vec3 sunDir) {
    float c = dot(dir, sunDir);
    float cr = cos(SUN_DISK_RADIUS);
    if (c < cr) return vec3(0.0);
    float x = clamp((1.0 - c) / (1.0 - cr), 0.0, 1.0);    // 0 centre, 1 limb
    float mu = sqrt(1.0 - x);
    float limb = 1.0 - 0.6 * (1.0 - pow(mu, 0.8));        // limb darkening
    return vec3(SUN_I * 150.0 * limb * smoothstep(1.0, 0.85, x));
}

// Night sky (look bible 8; owner r000: "strikingly beautiful"). QF_NIGHT_SKY 0 is r001's sparse
// stars; 1 and 2 add fainter stars (a magnitude spread, most of them dim) and the Milky Way: a
// soft band along a fixed great circle, mottled by dust lanes. Sky pixels only, at night only.
#if QF_NIGHT_SKY == 0
const float STAR_CUT = 0.9975;
#elif QF_NIGHT_SKY == 1
const float STAR_CUT = 0.9950;
#else
const float STAR_CUT = 0.9925;
#endif
vec3 stars(vec3 dir) {
    vec3 p = dir * 420.0;
    vec3 cell = floor(p);
    float h = hash13(cell);
    if (h < STAR_CUT) return vec3(0.0);
    vec3 centre = cell + 0.5 + (vec3(hash13(cell + 1.7), hash13(cell + 3.1), hash13(cell + 5.3)) - 0.5) * 0.6;
    float d = length(p - centre);
    float b = (h - STAR_CUT) / (1.0 - STAR_CUT);
#if QF_NIGHT_SKY > 0
    b = b * b * b;   // many faint stars, few bright ones
#endif
    float twinkle = 0.75 + 0.25 * sin(animTime() * (2.0 + 3.0 * b) + h * 100.0);
    vec3 tint = mix(vec3(0.8, 0.88, 1.0), vec3(1.0, 0.9, 0.75), hash13(cell + 9.1));
    return tint * SUN_I * 0.02 * (0.3 + b) * twinkle * smoothstep(0.6, 0.0, d);
}

#if QF_NIGHT_SKY > 0
const vec3 MILKY_POLE = vec3(0.83, -0.53, -0.19);   // normal of the band's great circle: it crosses the night_sky view on a diagonal (c-round critic: a dead-straight vertical band)
// In MOON_I units, like the airglow (QF_AIRGLOW 0.004): the band's core is 5-10x the airglow (b1: 2-4x was invisible).
#if QF_NIGHT_SKY == 1
const float MILKY_I = 0.035;   // c-round: 0.020 read as "a faint grey stripe"
#else
const float MILKY_I = 0.060;
#endif
vec3 milkyWay(vec3 dir) {
    vec3 pole = normalize(MILKY_POLE);
    float lat = dot(dir, pole);
    float band = exp(-lat * lat * 38.0);
    if (band < 0.01) return vec3(0.0);
    vec3 q = dir * 9.0;
    float n = valueNoise(q.xy + q.z * 1.7) * 0.6 + valueNoise(q.yz * 2.3 + 4.1) * 0.4;
    float dust = smoothstep(0.35, 0.75, valueNoise(q.xz * 3.1 + 7.7));
    float core = band * (0.45 + 0.9 * n) * mix(1.0, 0.35, dust * smoothstep(0.2, 0.0, abs(lat)));
    // Fine unresolved stars inside the band.
    float grain = step(0.985, hash13(floor(dir * 900.0))) * band;
    // A faint warm core and bluer edges, as in long exposures (c-round critic: grey band).
    vec3 tint = mix(vec3(0.70, 0.82, 1.0), vec3(1.0, 0.90, 0.78), smoothstep(0.35, 0.0, abs(lat)) * n);
    return MOON_I * MILKY_I * tint * core + SUN_I * 0.0015 * grain * vec3(0.9, 0.93, 1.0);
}
#endif

// How far into golden hour the sun is: 1 with the sun a few degrees up, 0 by mid-afternoon
// and once it has set. Used by the QF_CAL_GOLD variants (Shader Lab r001).
float goldenHour() {
    float y = sunDirWorld().y;
    return smoothstep(0.32, 0.08, y) * smoothstep(-0.04, 0.03, y);
}

// Scattered light only: what the sky adds in front of anything (fog, reflections).
vec3 skyScatter(vec3 dir) {
    // Below the horizon the table holds the lit ground; past the render distance and in
    // haze that read as a brown band under the sky (round 9). Use the horizon instead.
    float belowY = dir.y;
    dir.y = max(dir.y, 0.0);
    dir = dot(dir, dir) > 1e-8 ? normalize(dir) : vec3(1.0, 0.0, 0.0);
    vec3 L = SUN_I * lookupSkyView(dir, sunDirWorld(), LUT_SV_SUN)
           + moonIntensity() * MOON_TINT * lookupSkyView(dir, moonDirWorld(), LUT_SV_MOON);
    // Rain: a duller, darker, less saturated sky (look bible 9).
#if QF_CAL_GOLD == 2
    // Gold sky near the sun (owner r001: B): warm the glow within about 25 degrees of it, and
    // pull the grey-mauve above the horizon band slightly towards peach. r001's version also
    // warmed the horizon band itself, the "beige haze wall" when facing away from the sun; the
    // peach pull now starts a few degrees up, and the band away from the sun stays as it was.
    float gh = goldenHour() * QF_GOLD_SKY;
    float nearSun = pow(clamp(dot(dir, sunDirWorld()), 0.0, 1.0), 6.0);
    float aboveBand = smoothstep(0.03, 0.18, dir.y);
    L *= mix(vec3(1.0), vec3(1.30, 1.0, 0.58), clamp(gh * nearSun, 0.0, 1.5));
    L *= mix(vec3(1.0), vec3(1.06, 1.0, 0.90), clamp(gh * (1.0 - nearSun) * aboveBand, 0.0, 1.5));
#endif
    // Airglow and starlight: a moonless sky is never black, and is brightest towards the
    // horizon (van Rhijn). With exposure now letting a new moon read darker (EXPO_DEEP_SLOPE),
    // the bare sky fell to luma 1-2 of 255 (a4h: 22% of the new-moon frame crushed).
    float night = 1.0 - smoothstep(-0.12, 0.04, sunDirWorld().y);
    L += MOON_I * QF_AIRGLOW * AIRGLOW_PRESET * vec3(0.62, 0.76, 1.0) * night * (1.0 + 0.6 * (1.0 - dir.y));
#if QF_HORIZON_FLOOR == 1
    // Below the horizon nothing is sky: it is land past the render distance, seen through
    // haze. Drawn as the bright horizon band it read as a flat beige wall under the sky
    // (r001 critic and owner). Fade it to a darker, cooler veil over the first few degrees.
    // The distance haze uses this colour too, so far terrain fades into the same tone.
    float below = smoothstep(0.0, -0.10, belowY);
    L = mix(L, L * vec3(0.58, 0.64, 0.74), below);
#endif
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
#if QF_NIGHT_SKY > 0
        L += T * milkyWay(dir) * night * smoothstep(0.0, 0.25, dir.y) * (1.0 - 0.8 * moonBrightness());
#endif
    }
    return L;
}
