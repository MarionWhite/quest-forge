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

uniform int worldDay;

// Night sky texture (r005; owner r004: "the lighting profile is right, but I would like to give the
// sky a little more texture and beauty ... a rotation of skies so that it doesn't get too samey").
// Drawn on sky pixels only (skyRadiance), never in skyScatter, so the light on the land, which
// prepare.fsh integrates from skyScatter, is unchanged. Three nights, chosen per world day:
//   1 deep clear: a dense field of faint stars under the bright ones, and a navy zenith;
//   2 airglow: the faint green (and higher, red) bands long exposures show near the horizon;
//   3 Milky Way: a soft band with dust lanes (the r002 one was rejected for beaded lanes: these
//     are stretched along the band), washed out by a bright moon as in life.
int nightVariant() {
#if QF_NIGHT_SKY > 0
    return QF_NIGHT_SKY;
#else
    return 1 + int(floor(hash12(vec2(float(worldDay) * 1.37 + 0.5, 7.1)) * 2.999));
#endif
}

// Faint background stars: many, dim, slightly coloured; denser where `boost` is high.
vec3 faintStars(vec3 dir, float boost) {
    vec3 p = dir * 900.0;
    vec3 cell = floor(p);
    float h = hash13(cell + 0.37);
    float cut = mix(0.982, 0.94, boost);
    if (h < cut) return vec3(0.0);
    vec3 centre = cell + 0.5 + (vec3(hash13(cell + 2.3), hash13(cell + 4.7), hash13(cell + 6.1)) - 0.5) * 0.5;
    float d = length(p - centre);
    float b = (h - cut) / (1.0 - cut);
    b = b * b;
    vec3 tint = mix(vec3(0.75, 0.85, 1.0), vec3(1.0, 0.88, 0.72), hash13(cell + 8.3));
    return tint * SUN_I * 0.0045 * (0.25 + b) * smoothstep(0.7, 0.0, d);
}

float fbm2(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 4; i++) {
        v += a * valueNoise(p);
        p = mat2(1.6, 1.2, -1.2, 1.6) * p + 4.7;
        a *= 0.5;
    }
    return v;
}

vec3 nightSkyTexture(vec3 dir) {
    int v = nightVariant();
    float moonWash = 1.0 - 0.85 * moonBrightness();   // a bright moon hides the faint sky
    float up = clamp(dir.y, 0.0, 1.0);
    // A touch of navy towards the zenith on every night (r004 critic: near-black).
    vec3 L = vec3(0.10, 0.16, 0.42) * MOON_I * 0.0035 * smoothstep(0.0, 0.6, up);
    if (v == 1) {
        L += faintStars(dir, 0.35) * mix(0.5, 1.0, moonWash);
        L *= 1.15;
    } else if (v == 2) {
        L += faintStars(dir, 0.15) * mix(0.5, 1.0, moonWash);
        // Airglow: a green layer about 90 km up seen edge-on, so brightest 5-20 degrees above the
        // horizon, combed by gravity waves into slow ripples; a fainter red layer above it.
        float az = atan(dir.z, dir.x);
        float el = asin(clamp(dir.y, -1.0, 1.0));
        float wave = fbm2(vec2(az * 5.0 + animTime() * 0.004, el * 9.0));
        float ripple = 0.55 + 0.45 * sin(az * 23.0 + el * 40.0 + wave * 6.0);
        float green = exp(-pow((el - 0.20) / 0.11, 2.0)) * smoothstep(0.0, 0.05, el) * (0.45 + 0.55 * wave) * mix(0.75, 1.0, ripple);
        float red = exp(-pow((el - 0.42) / 0.16, 2.0)) * (0.5 + 0.5 * fbm2(vec2(az * 3.0, el * 4.0) + 9.0));
        L += (vec3(0.30, 1.0, 0.42) * green * 0.010 + vec3(1.0, 0.30, 0.22) * red * 0.0035) * MOON_I * moonWash;
    } else {
        // Milky Way: a great circle tilted across the sky; coordinates along and across the band.
        const vec3 POLE = vec3(0.946, -0.324, 0.0);   // the band crosses the night_sky view (yaw 200, 45 deg up)
        vec3 a1 = normalize(cross(POLE, vec3(0.0, 1.0, 0.0)));
        vec3 a2 = cross(POLE, a1);
        float across = dot(dir, POLE);
        float along = atan(dot(dir, a2), dot(dir, a1));
        // The bulge (galactic centre) towards one end: wider, brighter, warmer.
        float bulge = exp(-pow((along - 0.9) / 0.55, 2.0));
        float width = mix(0.11, 0.20, bulge);
        float band = exp(-pow(across / width, 2.0));
        // Clumpy star clouds, stretched along the band (anisotropic coordinates).
        float clouds = smoothstep(0.30, 0.80, fbm2(vec2(along * 12.0, across * 48.0)));
        // Dust lanes: dark, long and thin, wandering a little off the centre line.
        float laneC = across - 0.025 * sin(along * 2.3) - 0.02 * (fbm2(vec2(along * 3.0, 1.3)) - 0.5);
        float lane = exp(-pow(laneC / mix(0.018, 0.04, bulge), 2.0)) * smoothstep(0.35, 0.65, fbm2(vec2(along * 4.0, across * 12.0) + 3.3));
        float lanes2 = smoothstep(0.55, 0.75, fbm2(vec2(along * 5.0, across * 40.0) + 11.0)) * 0.5;
        float glow = band * (0.12 + 0.88 * clouds) * (1.0 - 0.8 * lane) * (1.0 - lanes2 * band);
        vec3 col = mix(vec3(0.78, 0.84, 1.0), vec3(1.0, 0.90, 0.74), bulge * 0.7 + 0.15);
        L += col * glow * (1.0 + 1.2 * bulge) * MOON_I * 0.012 * moonWash * smoothstep(-0.02, 0.12, dir.y);
        L += faintStars(dir, 0.15 + 0.85 * band * (1.0 - lane)) * mix(0.5, 1.0, moonWash);
    }
    return L;
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

#if QF_CLOUDS == 2
// Broken clouds, raymarched (r005; owner r004: D, dramatic broken clouds, "I don't want it to
// look like a png of this pasted onto the sky ... something more dynamic that looks beautiful and
// natural"). A slab of cloud 300-620 blocks up, marched along the view ray: big clumps from a
// low-frequency field whose threshold rises with height (flat bases, domed tops), edges eaten by
// finer noise that shifts with height and time, so the clouds billow as they drift. Each sample is
// lit by two looks towards the sun (Beer-Lambert, plus a soft multiple-scattering term), a
// two-lobe phase function (silver linings towards the sun) and the sky dome, darker underneath.
// Coverage changes from day to day.
// i0 smoke: at 1/1100 the clumps were sky-sized smooth blobs and the long slab near the horizon
// smeared into streaks; smaller, more broken clumps, and a shorter path at low angles.
// i1: a 2D field through a 260-block slab drew vertical walls that streaked towards the horizon;
// thinner, pinched tops, sheared by the wind, and 3D noise eats the edges.
// i2: still smeared radially: soft, thin clumps let each ray integrate density over hundreds of
// blocks of horizontal path. Dense clumps with a sharp edge go opaque at the first wall.
const float CL_BASE = 300.0, CL_TOP = 470.0, CL_SCALE = 1.0 / 520.0, CL_SIGMA = 0.16;
#if QF_PRESET >= 3
const int CL_STEPS = 14;
#elif QF_PRESET == 2
const int CL_STEPS = 10;
#elif QF_PRESET == 1
const int CL_STEPS = 7;
#else
const int CL_STEPS = 5;
#endif
vec2 cloudWind() { return vec2(animTime() * 3.2, animTime() * 1.1); }
float cloudThreshold() {
    float day = hash12(vec2(float(worldDay) * 0.731 + 0.2, 2.9));
    // Thinner at night, so most nights show the night sky (r005: the night views were all cloud).
    float night = 1.0 - smoothstep(-0.12, 0.04, sunDirWorld().y);
    return mix(mix(0.53, 0.47, day) + 0.07 * night, 0.32, rainStrength);   // i3: blue gaps too few
}
float valueNoise3(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = mix(mix(hash13(i), hash13(i + vec3(1, 0, 0)), f.x), mix(hash13(i + vec3(0, 1, 0)), hash13(i + vec3(1, 1, 0)), f.x), f.y);
    float b = mix(mix(hash13(i + vec3(0, 0, 1)), hash13(i + vec3(1, 0, 1)), f.x), mix(hash13(i + vec3(0, 1, 1)), hash13(i + vec3(1, 1, 1)), f.x), f.y);
    return mix(a, b, f.z);
}
float cloudDens(vec3 p, bool detail) {
    float h = (p.y - CL_BASE) / (CL_TOP - CL_BASE);
    if (h <= 0.0 || h >= 1.0) return 0.0;
    vec2 q = (p.xz + cloudWind()) * CL_SCALE + vec2(0.30, 0.18) * h;   // tops sheared downwind
    float base = valueNoise(q) * 0.50 + valueNoise(q * 2.03 + 5.1) * 0.26 + valueNoise(q * 4.13 + 1.7) * 0.15
               + valueNoise(q * 8.37 + 3.9) * 0.09;
    float th = cloudThreshold() + 0.50 * h + 0.10 * h * h + 0.05 * (1.0 - smoothstep(0.0, 0.08, h));   // ih: vertical walls streaked
    float d = base - th;
    if (d <= -0.10) return 0.0;
    if (detail) {
        vec3 q3 = vec3(q.x * 10.0 + animTime() * 0.010, h * 3.2 - animTime() * 0.004, q.y * 10.0);
        float e = valueNoise3(q3) * 0.62 + valueNoise3(q3 * 2.6 + 9.2) * 0.38;
        d -= (e - 0.40) * 0.30 * (0.6 + 1.0 * h);
    }
    return clamp(d * 11.0, 0.0, 1.0);
}
float cloudShadow(vec3 worldPos, vec3 L) {
    if (L.y < 0.05 || worldPos.y > CL_BASE) return 1.0;
    float ym = mix(CL_BASE, CL_TOP, 0.25);
    vec3 q = worldPos + L * ((ym - worldPos.y) / L.y);
    q.y = ym;
    return 1.0 - 0.6 * cloudDens(q, false) * smoothstep(0.05, 0.2, L.y);
}
float hgPhase(float mu, float g) {
    return (1.0 - g * g) / (4.0 * PI * pow(1.0 + g * g - 2.0 * g * mu, 1.5));
}
// Scattered light (rgb) and transmittance (a) of the cloud slab along dir.
vec4 cloudMarch(vec3 dir, int steps, float jitter) {
    float camY = cameraPosition.y;
    if (dir.y < 0.012 || camY > CL_BASE) return vec4(0.0, 0.0, 0.0, 1.0);
    float t0 = (CL_BASE - camY) / dir.y;
    if (t0 > 20000.0) return vec4(0.0, 0.0, 0.0, 1.0);
    float t1 = min((CL_TOP - camY) / dir.y, t0 + 600.0);
    float dt = (t1 - t0) / float(steps);
    vec3 Ld = normalize(mat3(gbufferModelViewInverse) * shadowLightPosition);
    bool day = sunDirWorld().y > -0.02;
    vec3 E = (day ? sunIrradiance() : moonIrradiance()) * smoothstep(-0.06, 0.03, Ld.y) * mix(1.0, 0.35, rainStrength);
    float mu = dot(dir, Ld);
    float ph = mix(hgPhase(mu, -0.15), hgPhase(mu, 0.80), 0.55) * 4.0;
    vec3 amb = lutFetch(C_AMB_UP).rgb / PI * mix(1.0, 0.6, rainStrength);
    float T = 1.0;
    vec3 S = vec3(0.0);
    float t = t0 + dt * jitter;
    for (int i = 0; i < steps; i++) {
        vec3 p = cameraPosition + dir * t;
        float dens = cloudDens(p, true);
        if (dens > 0.002) {
            float h = (p.y - CL_BASE) / (CL_TOP - CL_BASE);
            float od = (cloudDens(p + Ld * 18.0, false) * 18.0 + cloudDens(p + Ld * 70.0, false) * 50.0
                      + cloudDens(p + Ld * 220.0, false) * 140.0) * CL_SIGMA;
            float beer = exp(-od);
            float ms = exp(-od * 0.10);
            // Powder: the sunward rim of a thick cloud is darker than its thin edges.
            float powder = 1.0 - 0.75 * exp(-od * 0.8);
            // i3: the bodies were one flat grey. Multiple scattering carries light deep into a cloud,
            // more of it near the sunlit top; the base stays darker.
            vec3 lum = E * (beer * (ph + 0.15) * powder + ms * mix(0.05, 0.22, h))
                     + amb * mix(0.30, 1.10, h * h);
            float Ts = exp(-dens * CL_SIGMA * dt);
            S += T * lum * (1.0 - Ts);
            T *= Ts;
            if (T < 0.02) break;
            t += dt;
        } else {
            t += dt * 1.6;   // empty air: stride on
        }
        if (t > t1) break;
    }
    // Far clouds melt into the sky towards the horizon.
    float fade = exp(-t0 / 6000.0) * smoothstep(0.015, 0.10, dir.y);
    return vec4(S * fade, mix(1.0, T, fade));
}
vec3 applyClouds2(vec3 L, vec3 dir, int steps) {
    float j = 0.5;
#ifdef FSH
    j = ign(gl_FragCoord.xy + float(frameCounter % 64) * vec2(5.588, 3.124));
#endif
    vec4 c = cloudMarch(dir, steps, j);
    return L * c.a + c.rgb;
}
// One look at the slab's lower third, for reflections (water): no march.
vec3 applyCloudsCheap(vec3 L, vec3 dir) {
    float camY = cameraPosition.y;
    if (dir.y < 0.015 || camY > CL_BASE) return L;
    float t = (mix(CL_BASE, CL_TOP, 0.3) - camY) / dir.y;
    vec3 p = cameraPosition + dir * t;
    float d = cloudDens(p, false);
    if (d <= 0.0) return L;
    vec3 Ld = normalize(mat3(gbufferModelViewInverse) * shadowLightPosition);
    bool day = sunDirWorld().y > -0.02;
    vec3 E = (day ? sunIrradiance() : moonIrradiance()) * smoothstep(-0.06, 0.03, Ld.y);
    float beer = exp(-cloudDens(p + Ld * 40.0, false) * 40.0 * CL_SIGMA);
    float ph = mix(hgPhase(dot(dir, Ld), -0.15), hgPhase(dot(dir, Ld), 0.80), 0.55) * 4.0;
    vec3 col = E * (beer * (ph + 0.15) * 0.7 + 0.06) + lutFetch(C_AMB_UP).rgb / PI * 0.6;
    float a = clamp(d * 1.4, 0.0, 1.0) * exp(-t / 6000.0) * smoothstep(0.015, 0.10, dir.y);
    return mix(L, col, a);
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
        if (night > 0.0) L += T * nightSkyTexture(dir) * night;
#if QF_GLITTER == 2
        L += T * sunAureole(dir, sunDir);
#endif
    }
#if QF_CLOUDS == 1
    L = applyClouds(L, dir);
#elif QF_CLOUDS == 2
    L = applyClouds2(L, dir, CL_STEPS);
#endif
    return L;
}
