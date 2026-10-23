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
    // The moon's light, and the moonlit sky, across the phases. r002 left a tenth at new moon:
    // the sky fell to airglow alone and read brown-black, and the owner picked the full-moon
    // frame instead ("we regressed"). QF_NEW_MOON keeps more, so a new moon is the full-moon
    // night a little darker: the same navy sky and readable land, the phase still plain.
    return MOON_I * mix(QF_NEW_MOON, 1.0, moonBrightness());
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

// Night sky (look bible 8; owner r000: "strikingly beautiful"). r001's sparse stars, which the
// owner kept in r002 (5/5); the r002 Milky Way was rejected ("the execution is not good") and
// is gone. A new sky effect comes back only when it is genuinely beautiful.
const float STAR_CUT = 0.9975;
vec3 stars(vec3 dir) {
    vec3 p = dir * 420.0;
    vec3 cell = floor(p);
    float h = hash13(cell);
    if (h < STAR_CUT) return vec3(0.0);
    vec3 centre = cell + 0.5 + (vec3(hash13(cell + 1.7), hash13(cell + 3.1), hash13(cell + 5.3)) - 0.5) * 0.6;
    float d = length(p - centre);
    float b = (h - STAR_CUT) / (1.0 - STAR_CUT);
    float twinkle = 0.75 + 0.25 * sin(animTime() * (2.0 + 3.0 * b) + h * 100.0);
    vec3 tint = mix(vec3(0.8, 0.88, 1.0), vec3(1.0, 0.9, 0.75), hash13(cell + 9.1));
    return tint * SUN_I * 0.02 * (0.3 + b) * twinkle * smoothstep(0.6, 0.0, d);
}

// How far into golden hour the sun is: 1 with the sun a few degrees up, 0 by mid-afternoon
// and once it has set. Used by the QF_CAL_GOLD variants (Shader Lab r001).
float goldenHour() {
    float y = sunDirWorld().y;
    return smoothstep(0.32, 0.08, y) * smoothstep(-0.04, 0.03, y);
}

#if QF_GLITTER == 2
// A cinematic low sun (owner r002: "the light source doesn't look as cinematic as I would
// hope"): the eye and lens see a low sun as a large warm glow, not a small white dot. A soft
// aureole around the disk, strongest a few degrees above the horizon and gone by mid-afternoon.
// Coloured by the transmittance it is multiplied with, so it is orange near the horizon.
vec3 sunAureole(vec3 dir, vec3 sunDir) {
    float gh = goldenHour();
    if (gh <= 0.0) return vec3(0.0);
    float c = max(dot(dir, sunDir), 0.0);
    float glow = pow(c, 900.0) * 0.9 + pow(c, 120.0) * 0.18 + pow(c, 24.0) * 0.035;
    return vec3(1.0, 0.82, 0.62) * SUN_I * glow * gh;
}
#endif

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

#if QF_CLOUDS == 1
// A cheap cloud layer (owner r002: the Extreme Hills view "looks very bland"; sky interest).
// One thin deck of fair-weather cumulus at a fixed world height, so it parallaxes as you move,
// drifting with the wind; fuller and greyer in rain. Lit by the sun (a forward lobe, so the
// edges glow towards a low sun) and the sky, self-shadowed by one look towards the light.
// Its shadows drift over the land (lib/lighting.glsl). Volumetric clouds are a later milestone.
const float CLOUD_Y = 260.0, CLOUD_SCALE = 1.0 / 340.0;
vec2 cloudWind() { return vec2(animTime() * 2.2, animTime() * 0.9); }
float cloudCoverage() { return mix(0.47, 0.30, rainStrength); }
float cloudFbm(vec2 p, int octaves) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < octaves; i++) {
        v += a * valueNoise(p);
        p = mat2(1.6, 1.2, -1.2, 1.6) * p + 7.3;
        a *= 0.5;
    }
    return v;
}
float cloudDensity(vec2 worldXZ, int octaves) {
    vec2 p = (worldXZ + cloudWind()) * CLOUD_SCALE;
    // Clumps from two broad octaves, edges eaten by finer ones, so a cloud has a body and
    // ragged edges instead of a smooth smudge (r003 smoke).
    float base = cloudFbm(p * 0.55, 2);
    float n = base;
    if (octaves > 2) n = base * 0.62 + cloudFbm(p * 2.3 + 3.1, octaves - 2) * 0.38;
    float c = cloudCoverage();
    return smoothstep(c, c + 0.12, n);
}
float cloudShadow(vec3 worldPos, vec3 L) {
    if (L.y < 0.05 || worldPos.y > CLOUD_Y) return 1.0;
    vec2 q = worldPos.xz + L.xz * ((CLOUD_Y - worldPos.y) / L.y);
    return 1.0 - 0.55 * cloudDensity(q, 3) * smoothstep(0.05, 0.2, L.y);
}
// Blend the cloud deck over sky radiance L in direction dir (world space).
vec3 applyClouds(vec3 L, vec3 dir) {
    float camY = cameraPosition.y;
    if (dir.y < 0.015 || camY > CLOUD_Y) return L;
    float t = (CLOUD_Y - camY) / dir.y;
    vec2 q = cameraPosition.xz + dir.xz * t;
    float d = cloudDensity(q, 5);
    if (d <= 0.0) return L;
    vec3 Ld = normalize(mat3(gbufferModelViewInverse) * shadowLightPosition);
    // Self-shadow: denser cloud towards the light means a darker base.
    float toward = cloudDensity(q + Ld.xz / max(Ld.y, 0.08) * 60.0, 3);
    float mu = dot(dir, Ld);
    float g = 0.55;
    float hg = (1.0 - g * g) / (4.0 * PI * pow(1.0 + g * g - 2.0 * g * mu, 1.5));
    bool day = sunDirWorld().y > -0.02;
    vec3 E = day ? sunIrradiance() : moonIrradiance();
    vec3 amb = lutFetch(C_AMB_UP).rgb * 1.3;
    // A cloud deck is lit even by a sun on the horizon (it is a few hundred metres up), so at
    // golden hour the clouds take the orange light: no N.L.
    float sunUp = smoothstep(-0.05, 0.03, Ld.y);
    vec3 col = (E * sunUp * (0.30 + 2.4 * hg) * mix(1.0, 0.22, toward) + amb) * (0.85 / PI);
    col = mix(col, vec3(luminance(col)) * 0.6, rainStrength * 0.7);
    // Thin and faded with distance: far clouds melt into the horizon haze instead of aliasing.
    float a = d * smoothstep(0.015, 0.14, dir.y) * exp(-t / 9000.0);
    return mix(L, col, clamp(a, 0.0, 1.0));
}
#endif

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
#if QF_GLITTER == 2
        L += T * sunAureole(dir, sunDir);
#endif
    }
#if QF_CLOUDS == 1
    L = applyClouds(L, dir);
#endif
    return L;
}
