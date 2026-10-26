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
    // Limb darkening (Neckel and Labs' fit, roughly): the edge about half the centre's radiance,
    // slightly redder; r005's edge was a hard step.
    float limb = 0.36 + 0.64 * pow(mu, 0.55);
    vec3 tint = mix(vec3(1.0, 0.78, 0.58), vec3(1.0), pow(mu, 0.4));
    return SUN_I * 150.0 * limb * tint * smoothstep(1.0, 0.80, x);
}

#if QF_SUN_GLOW == 1
// Glare round the sun (r006; owner r005: the sun "still needs improvement"): the eye and a lens
// scatter a little of the disk's light into a tight halo, so the disk sits in a glow instead of
// cutting a white dot out of the sky. Two narrow lobes, both inside ~3 degrees, so the sky itself
// is not washed out (owner r005, forest-light). Multiplied by the transmittance: orange when low.
vec3 sunGlow(vec3 dir, vec3 sunDir) {
    float a = acos(clamp(dot(dir, sunDir), -1.0, 1.0));
    float g = 2.2 * exp(-pow(a / 0.020, 2.0)) + 0.10 * exp(-a / 0.045);
    return vec3(SUN_I) * g;
}
#endif

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
uniform sampler2D qfMilkyWay;

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
    // r007 rotation (owner r006: the Milky Way "fucking beautiful ... keep it in the rotation and
    // give it more nights"; airglow was underwhelming in r005 and leaves the rotation): the Milky
    // Way on 45% of nights, deep clear on 30%, a meteor shower on 25%.
    float h = hash12(vec2(float(worldDay) * 1.37 + 0.5, 7.1));
    return h < 0.45 ? 3 : (h < 0.75 ? 1 : 4);
#endif
}

// A meteor shower (r007; owner r006: "a meteor shower ... that would last the whole night and not
// impact performance very much"). All night long, streaks shoot out from one radiant (a point
// that moves with the stars, fixed per night): short, thin, fast, brightest just before they burn
// out, a few seconds apart, now and then a bright one. QF_METEOR_RATE slots, each with at most one
// meteor in flight, and only sky pixels at night evaluate it: a few dot products per slot.
float meteorTime() {
    return frameTimeCounter;   // not animTime(): QF_STILL renders keep the shower moving
}
// Loop 2 (critic: meteors drew over the dark cloud bodies): the meteor term is kept apart and added
// after the clouds, behind them with a steep cut (a thin night cloud still let ~30 % of the bright
// head through, which read as a streak in front of the cloud).
vec3 gMeteor = vec3(0.0);
float gCloudT = 1.0;
vec3 meteors(vec3 dir) {
    vec3 R = normalize(vec3(0.35 + 0.3 * hash12(vec2(float(worldDay), 3.3)), 0.80, -0.45 + 0.4 * hash12(vec2(float(worldDay), 5.1))));
    float pxA = 2.0 / (gbufferProjection[1][1] * viewHeight);
    vec3 a1 = normalize(cross(R, vec3(0.0, 0.0, 1.0)));
    vec3 a2 = cross(R, a1);
    vec3 sum = vec3(0.0);
    // r008 (owner r007: "I would expect more than 2"): shorter slot cycles, almost every cycle has
    // a meteor, and each leaves a glowing train that fades over a second or so, as bright meteors
    // do, so a moment of sky holds two or three streaks and a still frame catches some.
    for (int k = 0; k < QF_METEOR_RATE * 3; k++) {
        float P = 3.4 + 0.9 * float(k % 3);                  // seconds per slot cycle
        float tk = meteorTime() + float(k) * 1.917;
        float ci = floor(tk / P);
        vec2 sd = vec2(ci * 0.713 + float(k) * 3.17, float(k) * 1.31 + float(worldDay) * 0.17);
        if (hash12(sd) > 0.88) continue;                       // a few cycles have none
        float life = 0.40 + 0.55 * hash12(sd + 1.1);
        float bright = hash12(sd + 6.6) > 0.80 ? 3.5 : 1.0;   // now and then a bright one
        float trainT = bright > 1.0 ? 1.6 : 0.7;              // seconds a train glows after
        float start = hash12(sd + 2.2) * max(P - life - trainT, 0.1);
        float p = (tk - ci * P - start) / life;                // 0..1 while it burns
        if (p <= 0.0 || p >= 1.0 + trainT / life) continue;
        // Its path: a great circle away from the radiant, starting 10-55 degrees out.
        float az = hash12(sd + 3.3) * 6.2832;
        vec3 U = a1 * cos(az) + a2 * sin(az);
        float th0 = 0.18 + 0.78 * hash12(sd + 4.4);
        float len = (0.12 + 0.26 * hash12(sd + 5.5)) * (bright > 1.0 ? 1.3 : 1.0);
        float pb = min(p, 1.0);
        float head = th0 + len * pb;
        float thd = atan(dot(dir, U), dot(dir, R));
        float tail0 = head - len * mix(0.25, 0.60, pb);
        if (thd < th0 - 0.01 || thd > head + 0.01) continue;
        vec3 N = cross(R, U);
        float perp = abs(dot(dir, N));
        vec3 tint = mix(vec3(0.90, 0.94, 1.0), vec3(1.0, 0.90, 0.76), hash12(sd + 7.7) * 0.6);   // loop 2: the green end read lime (critic)
        if (p < 1.0) {
            float w = pxA * (bright > 1.0 ? 1.9 : 1.4);   // ub: 1.1 px streaks thinned out under TAA in ua
            float line = exp(-perp * perp / (w * w));
            float along = clamp((thd - tail0) / max(head - tail0, 1e-4), 0.0, 1.0);
            float trail = along * along * step(tail0, thd) * smoothstep(head + 0.004, head - 0.002, thd);
            float flare = pow(sin(PI * p), 0.6) * mix(1.0, 1.8, p);
            // The head: a brighter, slightly wider point.
            float hd = (thd - head) / 0.004;
            float headDot = exp(-hd * hd - perp * perp / (w * w * 2.2)) * 1.6;
            sum += tint * (line * trail + headDot) * flare * bright;
        }
        // The train: ionised air along the whole path, greenish, wider, fading and spreading.
        float age = max(tk - ci * P - start - life * 0.6, 0.0) / trainT;   // 0 when it forms, 1 gone
        if (age < 1.0) {
            float wt = pxA * mix(1.3, 2.6, age);
            float lineT = exp(-perp * perp / (wt * wt));
            float span = smoothstep(th0 - 0.005, th0 + len * 0.3, thd) * smoothstep(head + 0.003, head - len * 0.15, thd);
            float fadeT = (1.0 - age) * (1.0 - age) * smoothstep(0.0, 0.08, age + p * 0.1);
            sum += vec3(0.82, 0.92, 1.0) * lineT * span * fadeT * 0.16 * bright;   // ud: the green train was the lime the critic saw; a faint blue-white glow instead
        }
    }
#if QF_METEOR_SHOW == 1
    // Loop 3 (critic: ud_met's stills show no meteor, the owner's exact r007 complaint): two meteors
    // pinned in front of the camera, still, so TAA keeps them. Same look as the shower's: a thin
    // streak brightening to a head, a faint blue-white train along the path.
    {
        vec3 fw = normalize(mat3(gbufferModelViewInverse) * vec3(0.0, 0.0, -1.0));
        vec3 rt = normalize(mat3(gbufferModelViewInverse) * vec3(1.0, 0.0, 0.0));
        vec3 up = normalize(mat3(gbufferModelViewInverse) * vec3(0.0, 1.0, 0.0));
        for (int k = 0; k < 2; k++) {
            vec3 A = normalize(fw + rt * (k == 0 ? -0.30 : 0.22) + up * (k == 0 ? 0.26 : 0.30));   // tail
            vec3 B = normalize(fw + rt * (k == 0 ? -0.08 : 0.36) + up * (k == 0 ? 0.10 : 0.18));   // head
            vec3 N = normalize(cross(A, B));
            float perp = abs(dot(dir, N));
            float ang = acos(clamp(dot(A, B), -1.0, 1.0));
            float s = atan(dot(dir, normalize(cross(N, A))), dot(dir, A)) / max(ang, 1e-4);   // 0 tail .. 1 head
            if (s < -0.05 || s > 1.05) continue;
            float bright = k == 0 ? 3.5 : 1.4;
            float w = pxA * (k == 0 ? 1.9 : 1.4);
            float line = exp(-perp * perp / (w * w)) * s * s * smoothstep(1.02, 0.99, s) * step(0.0, s);
            float hd = (s - 1.0) * ang / 0.004;
            float headDot = exp(-hd * hd - perp * perp / (w * w * 2.2)) * 1.6;
            float wt = pxA * 2.2;
            float train = exp(-perp * perp / (wt * wt)) * smoothstep(-0.02, 0.3, s) * smoothstep(1.0, 0.85, s) * 0.12;
            sum += (vec3(1.0, 0.95, 0.86) * (line + headDot) * 1.5 + vec3(0.82, 0.92, 1.0) * train) * bright;
        }
    }
#endif
    return sum * SUN_I * 0.06;
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
    return tint * SUN_I * 0.010 * (0.25 + b) * smoothstep(0.7, 0.0, d);   // in1: 0.0045 vanished
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
    vec3 L = vec3(0.10, 0.16, 0.42) * MOON_I * 0.006 * smoothstep(0.0, 0.6, up);
    if (v == 1 || v == 4) {
        L += faintStars(dir, 0.35) * mix(0.5, 1.0, moonWash);
        L *= 1.15;
        if (v == 4) gMeteor = meteors(dir) * mix(0.6, 1.0, moonWash) * smoothstep(-0.02, 0.10, dir.y);
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
        L += (vec3(0.30, 1.0, 0.42) * green * 0.045 + vec3(1.0, 0.30, 0.22) * red * 0.014) * MOON_I * moonWash;   // in2: 4.5x, was invisible
    } else {
#if 1
        // Milky Way (r006; owner r005: the drawn band "looks kinda hand drawn and low quality ... either
        // make it convincingly photographic or drop it"): the ESO/S. Brunier panorama (CC BY 4.0,
        // LICENSES/README.md), galactic latitude -45..45 degrees, its point stars removed so the
        // pack's own stars sit on it (tools/shaders/make_textures.py). The galactic centre stands
        // 35 degrees up in the night_sky view's direction, the plane tilted across the sky.
        const vec3 GC = vec3(0.280, 0.574, -0.770);
        const vec3 GN0 = vec3(0.940, 0.0, 0.342);
        vec3 gn = normalize(cross(GC, GN0));            // galactic north pole
        vec3 gl = cross(gn, GC);                        // l = 90 degrees
        float b = asin(clamp(dot(dir, gn), -1.0, 1.0));
        float l = atan(dot(dir, gl), dot(dir, GC));
        vec2 uvm = vec2(0.5 - l / (2.0 * PI), 0.5 - b / (PI * 0.5));
        vec3 mw = vec3(0.0);
        if (uvm.y > 0.0 && uvm.y < 1.0) {
            mw = texture(qfMilkyWay, uvm).rgb;
            mw = mw * mw;                               // stored at gamma 1/2.2; close enough to 2
            mw *= smoothstep(0.0, 0.08, uvm.y) * smoothstep(1.0, 0.92, uvm.y);
        }
        float band = clamp(luminance(mw) * 3.0, 0.0, 1.0);
        L += mw * MOON_I * 0.45 * moonWash * smoothstep(-0.02, 0.14, dir.y);
        L += faintStars(dir, 0.15 + 0.85 * band) * mix(0.5, 1.0, moonWash);
#else
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
        // in3b: across * 48 drew thin scratches; star clouds are broad, soft clumps.
        float clouds = smoothstep(0.25, 0.80, fbm2(vec2(along * 6.0, across * 14.0)));
        // Dust lanes: dark, long and thin, wandering a little off the centre line.
        float laneC = across - 0.025 * sin(along * 2.3) - 0.02 * (fbm2(vec2(along * 3.0, 1.3)) - 0.5);
        float lane = exp(-pow(laneC / mix(0.018, 0.04, bulge), 2.0)) * smoothstep(0.35, 0.65, fbm2(vec2(along * 4.0, across * 12.0) + 3.3));
        float lanes2 = smoothstep(0.55, 0.75, fbm2(vec2(along * 4.0, across * 12.0) + 11.0)) * 0.5;
        float glow = band * (0.40 + 0.60 * clouds) * (1.0 - 0.8 * lane) * (1.0 - lanes2 * band);
        vec3 col = mix(vec3(0.78, 0.84, 1.0), vec3(1.0, 0.90, 0.74), bulge * 0.7 + 0.15);
        L += col * glow * (1.0 + 1.2 * bulge) * MOON_I * 0.045 * moonWash * smoothstep(-0.02, 0.12, dir.y);
        L += faintStars(dir, 0.15 + 0.85 * band * (1.0 - lane)) * mix(0.5, 1.0, moonWash);
#endif
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
    {
        // r008 golden horizon (owner r007 and critic: the horizon band at golden hour is "beige and
        // flat"): the low sun lights a long path of air near the horizon, so a warm band rings the
        // whole sky a few degrees deep. Gold to orange toward the sun, a rose-peach on the far
        // side (the anti-twilight arch), and a brighter glow round the sun's azimuth that climbs
        // higher. Reference packs all show it; ours read grey-teal away from the sun.
        float ghH = goldenHour() * QF_GOLD_HORIZON;
        if (ghH > 0.0) {
            vec3 sd = sunDirWorld();
            vec2 hz = normalize(dir.xz + vec2(1e-5, 0.0));
            vec2 sz = normalize(sd.xz + vec2(1e-5, 0.0));
            float az = 0.5 + 0.5 * dot(hz, sz);                         // 1 under the sun, 0 opposite
            float depthB = mix(0.10, 0.24, az * az);                    // the band climbs toward the sun
            float band = exp(-max(dir.y, 0.0) / depthB);
            // ub (ua vs refs: our band was a tint, the refs' a luminous peach-gold glow brighter than
            // the zenith): the band now lifts the light as well as warming it, and the sky aloft
            // takes the lavender-blue of a golden-hour zenith instead of noon's cyan.
            // Loop 2 (critic: ub's band read brown-khaki smog; CR's is a bright cream-peach band
            // that fades upward): blue is kept (0.58 cut it to khaki), so the band is cream to
            // peach, a touch rosier away from the sun, and the lift carries the glow.
            vec3 warm = mix(vec3(1.50, 1.21, 1.56), vec3(1.86, 1.41, 1.47), pow(az, 1.6));   // loop 3: uf 199,170,137 sat ~20 under CR in R and B   // ud: 1.12/1.00 blue still read khaki (187,163,116 vs CR 222,179,155)
            float lift = 1.32 + 0.45 * pow(az, 4.0) * band;   // ud: the band sat 15 % under CR's            // brighter round the sun's bearing
            L *= mix(vec3(1.0), warm * lift, clamp(ghH * band, 0.0, 1.0));
            L *= mix(vec3(1.0), vec3(1.10, 0.93, 1.02), clamp(ghH * (1.0 - band) * 0.85, 0.0, 1.0));
        }
    }
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
    // r008: at golden hour the far land's veil is warm, not blue-grey.
    L = mix(L, L * mix(vec3(0.58, 0.64, 0.74), vec3(1.04, 0.96, 0.95), goldenHour() * min(QF_GOLD_HORIZON, 1.0)), below);   // loop 2: 0.92/0.80/0.70 was the brown under the band
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
// Broken clouds, raymarched (r005; owner r004: D, dramatic broken clouds, "something more dynamic
// that looks beautiful and natural"). A slab of cloud 300-470 blocks up, marched along the view ray.
// r006 (owner r005: "a very good start, a lot of ground to cover"; the critic: brush streaks fanning
// from the zenith; owner: cloud light must follow the hour, night clouds look weird):
// - Shape: r005's base was a 2D field pushed up through the slab, so every cloud had vertical walls,
//   and seen from below vertical walls converge on the zenith: the brush streaks. Now a 3D field
//   bends the walls (a low-frequency 3D warp of the base, and 3D erosion that grows with height), so
//   bases are flat, sides lean and bulge, and tops are cauliflower domes.
// - Light: multiple scattering by Wrenninge's octave approximation (three Beer-Lambert terms with
//   falling extinction and phase anisotropy), a two-lobe phase (silver linings toward the sun), the
//   powder darkening on thick sunward sides, sky light from above and, at golden hour, the warm sky
//   near the sun lighting the bases from below: golden and orange undersides and rims at sunset.
// - Night: lit by the moon only through its phase, the bodies dark against the sky, only thin edges
//   toward the moon lit (moonlit rims), no self-glow.
// All noise comes from qfNoise (one fetch per lookup), cheaper than r005's hashed value noise.
const float CL_BASE = 300.0, CL_TOP = 470.0, CL_SCALE = 1.0 / 520.0, CL_SIGMA = 0.16;
#if QF_PRESET >= 3
const int CL_STEPS = 24;
#elif QF_PRESET == 2
const int CL_STEPS = 16;
#elif QF_PRESET == 1
const int CL_STEPS = 9;
#else
const int CL_STEPS = 4;   // m round: 6 put Potato's night_sky at 0.42 ms (budget 0.4)
#endif
vec2 cloudWind() { return vec2(animTime() * 3.2, animTime() * 1.1); }
float cloudNight() { return 1.0 - smoothstep(-0.12, 0.04, sunDirWorld().y); }
float cloudThreshold() {
    float day = hash12(vec2(float(worldDay) * 0.731 + 0.2, 2.9));
    // Thinner at night, so most nights show the night sky (r005: the night views were all cloud).
    return mix(mix(0.52, 0.45, day) + 0.07 * cloudNight() + QF_CLOUD_COVER, 0.33, rainStrength);
}
float cloudDensD(vec3 p, bool detail) {   // the signed field: > 0 inside, -1 out of the slab
    float h = (p.y - CL_BASE) / (CL_TOP - CL_BASE);
    if (h <= 0.0 || h >= 1.0) return -1.0;
    vec2 q = (p.xz + cloudWind()) * CL_SCALE;
    // Base: a smooth 4-octave field (cells 520 down to 65 blocks), bent by a 3D warp so walls lean.
    float warp = noise3t(vec3(q * 2.2, h * 1.6 + animTime() * 0.0015)) - 0.5;
    vec2 qw = q + vec2(0.10, 0.06) * h + warp * vec2(0.16, -0.12);
    // Two layers of the smooth field at unrelated scales and angles, so its 2 km tile never repeats.
    float base = texture(qfNoise, qw * 0.25).b * 0.75 + texture(qfNoise, mat2(0.6, 0.8, -0.8, 0.6) * qw * 0.53 + 0.37).b * 0.35 - 0.05;
    // Loop 3 (critic ud sky_noon: radial streaks smeared through the right half, and in the cloud
    // clip): the 3D terms changed ~2x slower up the slab than across it, so features stayed tall
    // columns, and columns seen from below fan out from the zenith. Finer in height now (about
    // isotropic in blocks), so the texture breaks up along every view ray.
    base += (noise3t(vec3(qw * 4.0, h * 4.6)) - 0.5) * 0.30;
    // Height profile: flat bases, domed tops. The threshold climbs steadily with height, so a
    // cloud's sides slope inward all the way up (j0: a late h^2 rise still left near-vertical
    // walls, which streak toward the zenith seen from below).
    float th = cloudThreshold() + 0.55 * pow(h, 1.3) + 0.06 * (1.0 - smoothstep(0.0, 0.07, h));
    float d = base - th;
    if (d <= -0.12) return d;
    if (detail) {
        // Erosion: billows near the top, wisps at the base; drifting slowly so they boil.
        // j1: soft, lightly eroded sheets read as smooth streaks fanning from overhead; sharper
        // edges and a third, finer octave give the bases and sides texture.
        vec3 q3 = vec3(qw * 18.0 + animTime() * 0.004, h * 7.5 - animTime() * 0.003);   // loop 3: 4.5
        float e = noise3t(q3) * 0.52 + noise3t(q3 * 2.7 + 9.2) * 0.31 + noise3t(q3 * 6.9 + 4.1) * 0.17;
        d -= (e - 0.42) * mix(0.16, 0.30, h);
    }
    return d;
}
float cloudDens(vec3 p, bool detail) {
    return clamp(cloudDensD(p, detail) * 15.0, 0.0, 1.0);
}
// Loop 2 (critic: a grey lens-shaped blob in the big clouds of river_noon and biome_ocean): the
// light samples read the smooth base field with its steep x15 edge, so the shadow of the dome above
// a cloud base drew as a clean-edged dark oval inside the eroded cloud. The light path now sees a
// soft version of the field, so the shade under a thick dome fades in over tens of blocks.
float cloudDensL(vec3 p) {
    return smoothstep(-0.06, 0.16, cloudDensD(p, false)) * 0.85;
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
// What lights the clouds this hour: the light (sun or moon, its colour after the atmosphere), the
// sky dome above, and the warm horizon sky toward a low sun, which lights the bases from below.
struct CloudLight { vec3 L; vec3 E; vec3 top; vec3 under; float night; vec3 ph; float rim; };
CloudLight cloudLight() {
    CloudLight c;
    c.L = normalize(mat3(gbufferModelViewInverse) * shadowLightPosition);
    c.night = cloudNight();
    bool day = sunDirWorld().y > -0.02;
    float gh = goldenHour();
    // A deck hundreds of blocks up still sees a sun just below the camera's horizon.
    vec3 E = (day ? sunIrradiance() : moonIrradiance()) * smoothstep(-0.07, 0.02, c.L.y) * mix(1.0, 0.35, rainStrength);
    // Golden hour: the light reaching the deck has crossed the most air, so it is deeper gold than at
    // the ground's shallower slant suggests (owner r005: "golden or orange undersides and rims").
    E *= mix(vec3(1.0), vec3(1.18, 0.86, 0.56), gh);
    c.E = E;
    vec3 amb = lutFetch(C_AMB_UP).rgb / PI * mix(1.0, 0.6, rainStrength);
    c.top = amb * mix(1.0, 0.65, c.night);   // j0: 0.30 drew new-moon clouds as black holes
    // The horizon sky 60 degrees round from the sun: the warm band without the sun's own glare.
    vec2 lh = normalize(c.L.xz + vec2(1e-4, 0.0));
    vec3 hz = normalize(vec3(lh.x * 0.5 - lh.y * 0.866, 0.05, lh.x * 0.866 + lh.y * 0.5));
    vec3 horizon = day ? SUN_I * lookupSkyView(hz, sunDirWorld(), LUT_SV_SUN) : vec3(0.0);
    c.under = amb * mix(0.35, 0.12, c.night) + horizon * gh * 0.45;   // loop 4: 0.8 (the flat cream underside of an overhead deck)
    c.ph = vec3(1.0);
    c.rim = 0.0;
    return c;
}
// The three octaves' phase functions depend only on the view and light directions: once per pixel.
vec3 cloudPhases(float mu) {
    vec3 ph;
    float gk = 1.0;
    for (int k = 0; k < 3; k++) {
        ph[k] = mix(hgPhase(mu, -0.20 * gk), hgPhase(mu, 0.82 * gk), 0.62) * 4.0 * PI;
        gk *= 0.55;
    }
    return ph;
}
vec3 cloudLum(CloudLight c, float od, float h, float mu, float dens) {
    // Wrenninge's multiple-scattering octaves: each bounce sees less extinction and a softer lobe
    // (the lobes, c.ph, from cloudPhases).
    vec3 s = c.E * (exp(-od) * c.ph.x + 0.52 * exp(-od * 0.42) * c.ph.y + 0.2704 * exp(-od * 0.1764) * c.ph.z
                    // ud (critic: a grey lens in river_noon's and biome_ocean's big clouds, still there with
                    // soft light samples): the thick core's flat base, lit only through the full dome, fell
                    // to the octaves' floor. A deep, isotropic diffusion term lifts thick bases evenly.
                    // Loop 4: at golden hour that term lit whole decks a flat cream (forest_golden's wash).
                    + 0.26 * mix(1.0, 0.30, goldenHour()) * exp(-od * 0.05));   // loop 3: 0.16 left a grey patch under river_noon's big cloud
    // Powder: the sunward side of a thick body is darker than its thin edges.
    float powder = 1.0 - 0.7 * exp(-od * 0.9 - dens * 2.0);
    s *= mix(1.0, powder, 0.75) / (4.0 * PI) * 2.2;
    // Golden hour: the near-level sun slips under the deck and lights the bases and lower sides.
    s += c.E * (goldenHour() * 0.16 * exp(-od * 0.6) * (1.0 - h));   // loop 4: 0.22, exp(-od*0.25) lit whole bases cream (forest_golden wash); only the thin sunward bases now
#if QF_CLOUD_RIM == 1
    // Silver linings and rim light (r007; owner r006, golden: "a sharper highlight effect on the
    // edges of the clouds for more of a cinematic effect"). Where a cloud is thin both along the
    // view and toward the light (its fringe), the light is scattered almost straight on: a narrow,
    // bright lobe that outlines the clouds standing in front of the sun, plus a warm rim on the
    // sunward edges at golden hour. Sharp because it lives only in the fringe.
    {
        float gh = goldenHour();
        float fringe = exp(-od * 2.6) * (1.0 - smoothstep(0.0, 0.55, dens));
        s += c.E * fringe * (c.rim * 0.045 * (0.6 + 1.4 * gh) + 0.30 * gh);
    }
#endif
    // At night, only thin edges carry moonlight: the bodies stay dark (no glow).
    s *= mix(1.0, exp(-od * 0.8), c.night);
    return s + c.top * mix(0.35, 1.0, h) + c.under * (1.0 - h) * (1.0 - h);
}
// Scattered light (rgb) and transmittance (a) of the cloud slab along dir.
vec4 cloudMarch(vec3 dir, int steps, float jitter) {
    float camY = cameraPosition.y;
    if (dir.y < 0.012 || camY > CL_BASE) return vec4(0.0, 0.0, 0.0, 1.0);
    float t0 = (CL_BASE - camY) / dir.y;
    if (t0 > 20000.0) return vec4(0.0, 0.0, 0.0, 1.0);
    // jh: overhead masses still fanned into brush streaks. They were undersampling along the ray:
    // a 30-40 block step blurs each cloud edge along the ray, and on screen "along the ray" points
    // away from the zenith. Shorter segments, fine steps inside cloud, long strides through air.
    float t1 = min((CL_TOP - camY) / dir.y, t0 + 520.0);
    float dt = (t1 - t0) / float(steps);
    CloudLight c = cloudLight();
    float mu = dot(dir, c.L);
    c.ph = cloudPhases(mu);
    c.rim = min(hgPhase(mu, 0.92) * 4.0 * PI, 80.0);
    float T = 1.0;
    vec3 S = vec3(0.0);
    float t = t0 + dt * jitter;
    for (int i = 0; i < steps; i++) {
        vec3 p = cameraPosition + dir * t;
        float dens = cloudDens(p, true);
        if (dens > 0.002) {
            float h = (p.y - CL_BASE) / (CL_TOP - CL_BASE);
#if QF_PRESET == 0
            float od = (cloudDens(p + c.L * 24.0, false) * 24.0 + cloudDens(p + c.L * 120.0, false) * 150.0) * CL_SIGMA;
#else
            float od = (cloudDensL(p + c.L * 16.0) * 16.0 + cloudDensL(p + c.L * 60.0) * 44.0
                      + cloudDensL(p + c.L * 190.0) * 90.0) * CL_SIGMA;
#endif
            vec3 lum = cloudLum(c, od, h, mu, dens);
            float Ts = exp(-dens * CL_SIGMA * dt);
            S += T * lum * (1.0 - Ts);
            T *= Ts;
            if (T < 0.02) break;
            t += dt * 0.6;
        } else {
            t += dt * 1.5;   // empty air: stride on
        }
        if (t > t1) break;
    }
    // Far clouds melt into the sky towards the horizon.
    float fade = exp(-t0 / 6500.0) * smoothstep(0.012, 0.09, dir.y);
    return vec4(S * fade, mix(1.0, T, fade));
}
vec3 applyClouds2(vec3 L, vec3 dir, int steps) {
    float j = 0.5;
#ifdef FSH
    j = ign(gl_FragCoord.xy + float(frameCounter % 64) * vec2(5.588, 3.124));
#endif
    vec4 c = cloudMarch(dir, steps, j);
    gCloudT = c.a;
    return L * c.a + c.rgb;
}
// Reflections (water): two looks into the slab, lit the same way as the sky's clouds.
vec3 applyCloudsCheap(vec3 L, vec3 dir) {
    float camY = cameraPosition.y;
    if (dir.y < 0.015 || camY > CL_BASE) return L;
    CloudLight c = cloudLight();
    float mu = dot(dir, c.L);
    c.ph = cloudPhases(mu);
    float T = 1.0;
    vec3 S = vec3(0.0);
    for (int i = 0; i < 2; i++) {
        float hh = i == 0 ? 0.22 : 0.55;
        float t = (mix(CL_BASE, CL_TOP, hh) - camY) / dir.y;
        vec3 p = cameraPosition + dir * t;
        float d = cloudDens(p, false);
        if (d <= 0.0) continue;
        float od = (cloudDens(p + c.L * 40.0, false) * 40.0 + cloudDens(p + c.L * 140.0, false) * 100.0) * CL_SIGMA;
        float a = clamp(d * 1.2, 0.0, 1.0) * T;
        S += cloudLum(c, od, hh, mu, d) * a;
        T *= 1.0 - clamp(d * 1.2, 0.0, 1.0);
    }
    float t0 = (CL_BASE - camY) / dir.y;
    float fade = exp(-t0 / 6500.0) * smoothstep(0.015, 0.10, dir.y);
    return L * mix(1.0, T, fade) + S * fade;
}
#endif

// The full sky in a direction: scattering plus the sun, moon and stars seen through it.
vec3 skyRadiance(vec3 dir) {
    vec3 L = skyScatter(dir);
    float r = cameraRadius();
    if (distToGround(r, dir.y) < 0.0) {
        vec3 T = lookupTransmittance(r, dir.y) * (1.0 - 0.9 * rainStrength);
        vec3 sunDir = sunDirWorld();
#if QF_SUN == 1
        // The real sun (lib/sun.glsl); its glare is drawn in final.glsl, over what is in front.
        L += sunDiskReal(dir, sunDir, T) * (1.0 - 0.9 * rainStrength) + T * moonDisk(dir, moonDirWorld());
        {
            // Loop 4 (critic uj ocean_sunset: the disk reads as a flat white sticker; BSL's sun burns
            // into the sky round it): a warm Mie aureole a few degrees wide, deeper gold at low sun.
            float a = acos(clamp(dot(dir, sunDir), -1.0, 1.0));
            vec3 mt = mix(vec3(1.0, 0.88, 0.70), vec3(1.0, 0.78, 0.42), goldenHour());
            L += T * SUN_I * mt * (0.24 * exp(-a / 0.022) + 0.040 * exp(-a / 0.11)) * (1.0 - rainStrength);   // l4 first try 0.05/0.01 did not show against the bright sunset sky
        }
#else
        L += T * (sunDisk(dir, sunDir) + moonDisk(dir, moonDirWorld()));
#if QF_SUN_GLOW == 1
        L += T * sunGlow(dir, sunDir) * (1.0 - rainStrength);
#endif
#endif
        float night = 1.0 - smoothstep(-0.12, 0.04, sunDir.y);
        L += T * stars(dir) * night;
        if (night > 0.0) { L += T * nightSkyTexture(dir) * night; gMeteor *= T * night; }
#if QF_GLITTER == 2
        L += T * sunAureole(dir, sunDir);
#endif
    }
#if QF_CLOUDS == 1
    L = applyClouds(L, dir);
#elif QF_CLOUDS == 2
    L = applyClouds2(L, dir, CL_STEPS);
#endif
    L += gMeteor * smoothstep(0.93, 0.995, gCloudT);   // ud: 0.85 still let streaks over the thin grey cloud
    gMeteor = vec3(0.0); gCloudT = 1.0;
    return L;
}
