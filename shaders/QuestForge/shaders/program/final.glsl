// final: exposure (already applied by TAA on Low and up), the neutral tone mapper, sRGB,
// dither. Potato has no TAA and gets a light edge filter instead (rule 12).
// QF_DEBUG_VIEW: 1 material IDs, 2 normals, 3 sky light, 4 the raw exposure-free scene.

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/buffers.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sun.glsl"
#include "/lib/tonemap.glsl"

#ifdef VSH
out vec2 uv;
void main() {
    gl_Position = ftransform();
    uv = gl_MultiTexCoord0.xy;
}
#endif

#ifdef FSH
in vec2 uv;

uniform sampler2D colortex0;
uniform sampler2D colortex1;
uniform sampler2D colortex2;
uniform sampler2D colortex3;
#if QF_TAA
uniform sampler2D colortex4;
#endif
uniform sampler2D depthtex0;
#if QF_DEBUG_VIEW == 6 && QF_SHADOWS
uniform sampler2D shadowtex0;
#endif

layout(location = 0) out vec4 outColor;

vec3 calGrade(vec3 c);
// Vibrance (r007; owner r006: "a little more vibrance"): saturation raised most where the colour is
// muted, hardly at all where it is already vivid, so grass, water and sky gain colour while wood,
// chests, sand and gold do not turn neon (look bible 3). On the exposed linear colour.
vec3 vibrance(vec3 c) {
    if (QF_VIBRANCE <= 0.0) return c;
    float mx = max(c.r, max(c.g, c.b)), mn = min(c.r, min(c.g, c.b));
    // Saturation judged perceptually (square roots), not in linear light, where almost every
    // natural colour already reads as vivid.
    float sat = mx > 1e-5 ? 1.0 - sqrt(max(mn, 0.0) / mx) : 0.0;
    float l = luminance(c);
    float k = 1.0 + float(QF_VIBRANCE) * (1.0 - sat) * 2.2 * smoothstep(0.0, 0.25, sat + 0.05);
    c = max(vec3(l) + (c - vec3(l)) * k, vec3(0.0));
    return c;
}
vec3 display(vec3 exposed) {
    return linearToSrgb(tonemapNeutral(vibrance(calGrade(exposed))));
}

#if QF_TAA
vec3 sceneExposed(ivec2 p) {
    vec3 c = texelFetch(colortex4, p, 0).rgb;
    return c / max(1.0 - luminance(c), 1e-3);   // undo TAA's luma weighting
}
#else
vec3 sceneExposed(ivec2 p) {
    return texelFetch(colortex3, p, 0).rgb * exposure();
}
#endif

#if QF_DEBUG_VIEW == 8
// Debug view 8: numbers as pixels. Each patch holds one value v, mapped to [0, 1) and
// written as two 8-bit channels (red the high byte, green the low), undithered and
// untonemapped, so read_meter.py recovers it to about 1/65000 of the range.
const int METER_PATCHES = 15;

int meterPatch(ivec2 px) {
    int top = int(viewHeight) - 1 - px.y;
    if (top < 16 || top >= 48 || px.x < 16) return -1;
    int i = (px.x - 16) / 40;
    if (i >= METER_PATCHES || (px.x - 16) - i * 40 >= 32) return -1;
    return i;
}

vec3 encodeMeter(float v) {
    v = clamp(v, 0.0, 0.99999) * 255.0;
    return vec3(floor(v) / 255.0, floor(fract(v) * 255.0 + 0.5) / 255.0, 0.0);
}

// The same centre-weighted log-average as prepare's meter, of what final itself reads:
// mode 0 colortex3 as bound here, mode 1 the displayed scene divided by the exposure.
float finalLogAverage(int mode) {
    float sum = 0.0, wsum = 0.0;
    const int GX = 32, GY = 18;
    vec2 size = vec2(viewWidth, viewHeight);
    float e = max(exposure(), 1e-6);
    for (int y = 0; y < GY; y++) {
        for (int x = 0; x < GX; x++) {
            vec2 u = (vec2(x, y) + 0.5) / vec2(GX, GY);
            vec2 c = u - 0.5;
            float w = exp(-dot(c, c) * 4.0);
            ivec2 q = ivec2(u * size);
            float l = mode == 0 ? luminance(texelFetch(colortex3, q, 0).rgb) : luminance(sceneExposed(q)) / e;
            sum += log2(max(l, 1e-6)) * w;
            wsum += w;
        }
    }
    return sum / wsum;
}

// Patches, left to right (logs are log2, encoded as (x + 24) / 32):
//   0 meter log-average (prepare)  1 log-average of colortex3 as final reads it
//   2 log-average of the displayed scene / exposure     3 log2 exposure (applied)
//   4 log2 exposure target         5 moon phase / 8     6 log2 moon irradiance (luma)
//   7 log2 sun irradiance (luma)   8 frameTime * 10 (s)
//   9, 10 frames since prepare wrote the meter / state texel (0 or 1 when ping-pong is right)
//   11 frameCounter minus a counter prepare carries from frame to frame (the same in two
//      screenshots when prepare reads its own last output)   12 frameCounter % 2048
//   13 meter arithmetic mean (log2)   14 the metered value that drives the target (log2)
vec3 meterReadout(int i) {
    vec4 m = lutFetch(C_METER);
    vec4 ex = lutFetch(C_EXPOSURE);
    vec4 st = lutFetch(C_STATE);
    float fc = float(frameCounter % 2048);
    float v;
    if (i == 0) v = m.r;
    else if (i == 1) v = finalLogAverage(0);
    else if (i == 2) v = finalLogAverage(1);
    else if (i == 3) v = ex.b + ex.a;
    else if (i == 4) v = m.b;
    else if (i == 5) return encodeMeter(float(moonPhase) / 8.0);
    else if (i == 6) v = log2(max(luminance(moonIrradiance()), 1e-7));
    else if (i == 7) v = log2(max(luminance(sunIrradiance()), 1e-7));
    else if (i == 8) return encodeMeter(frameTime * 10.0);
    else if (i == 9) return encodeMeter(mod(fc - m.a, 2048.0) / 64.0);
    else if (i == 10) return encodeMeter(mod(fc - st.b, 2048.0) / 64.0);
    else if (i == 11) return encodeMeter(mod(fc - st.g, 2048.0) / 2048.0);
    else if (i == 12) return encodeMeter(fc / 2048.0);
    else if (i == 13) v = m.g;
    else v = ex.g;
    return encodeMeter((v + 24.0) / 32.0);
}
#endif

// Calibration grades (QF_CAL_*), on the exposed linear colour before the tone mapper.
vec3 calSat(vec3 c, float s) {
    float l = luminance(c);
    return max(vec3(l) + (c - vec3(l)) * s, vec3(0.0));
}
vec3 calContrast(vec3 c, float k) {
    return pow(max(c, vec3(0.0)) / 0.18, vec3(k)) * 0.18;
}
vec3 calGrade(vec3 c) {
#if QF_CAL_GRADE == 2      // B cinematic: teal shadows, orange highlights, deeper contrast
    float l = luminance(c);
    float hl = smoothstep(0.05, 0.6, l);
    c *= mix(vec3(0.90, 1.0, 1.10), vec3(1.10, 1.0, 0.86), hl);
    c = calContrast(c, 1.18);
#elif QF_CAL_GRADE == 3    // C storybook: softer contrast, richer colour, lifted blacks
    c = calSat(c, 1.3);
    c = calContrast(c, 0.85) + 0.008;
#endif
    float sunY = sunDirWorld().y;
    float low = smoothstep(0.30, 0.06, sunY) * smoothstep(-0.10, 0.0, sunY);
#if QF_CAL_SUNSET == 1     // A intense gold
    c = calSat(c, 1.0 + 0.5 * low) * mix(vec3(1.0), vec3(1.22, 1.04, 0.74), low);
#elif QF_CAL_SUNSET == 2   // B soft pastel: pink, peach and lilac
    c = calSat(c, 1.0 - 0.3 * low) * mix(vec3(1.0), vec3(1.08, 0.93, 1.06), low) + 0.01 * low;
#elif QF_CAL_SUNSET == 3   // C naturalistic: brief gold, then a cool blue hour
    float blue = smoothstep(0.0, -0.08, sunY) * smoothstep(-0.25, -0.1, sunY);
    c *= mix(vec3(1.0), vec3(1.06, 1.0, 0.92), low * 0.6) * mix(vec3(1.0), vec3(0.9, 0.97, 1.12), blue);
#endif
    float night = smoothstep(-0.02, -0.15, sunY) * clamp(float(eyeBrightnessSmooth.y) / 240.0, 0.0, 1.0);
#if QF_CAL_NIGHT == 1      // A truly dark: little colour
    c = mix(c, calSat(c, 0.5), night);
#elif QF_CAL_NIGHT == 2    // B moonlit: a cool blue cast
    c *= mix(vec3(1.0), vec3(0.82, 0.95, 1.18), night);
#elif QF_CAL_NIGHT == 3    // C gentle: near-neutral
    c = mix(c, calSat(c, 0.85) * vec3(1.03, 1.0, 0.97), night);
#endif
    return c;
}

#if QF_CAL_BLOOM > 0 || QF_CAL_GRADE > 0
// A cheap three-ring glow of the bright part of the frame (calibration only).
vec3 calBloom(ivec2 px) {
#if QF_CAL_BLOOM == 3 || QF_CAL_GRADE == 2
    const float thr = 0.45, gain = 0.30;
#elif QF_CAL_BLOOM == 1
    const float thr = 1e9, gain = 0.0;
#else
    const float thr = 0.85, gain = 0.10;
#endif
    vec3 sum = vec3(0.0);
    float wsum = 0.0;
    for (int r = 1; r <= 3; r++) {
        float rad = viewHeight * 0.012 * float(r * r);
        int n = 12 * r * r;   // taps about 7 px apart on every ring, so no ghost copies
        for (int i = 0; i < n; i++) {
            float a = (float(i) + 0.5 * float(r)) * (2.0 * PI / float(n));
            ivec2 q = clamp(px + ivec2(vec2(cos(a), sin(a)) * rad), ivec2(0), ivec2(viewWidth, viewHeight) - 1);
            vec3 s = sceneExposed(q);
            float w = 1.0 / float(r * n);
            sum += min(max(s - vec3(thr), vec3(0.0)), vec3(6.0)) * w;
            wsum += w;
        }
    }
    return sum / wsum * gain;
}
#endif

#if QF_SUN == 1
// Glare round the real sun (lib/sun.glsl), in exposed units, drawn over everything in front of it.
// The visible share of the disk comes from nine taps on it: open sky at the disk's brightness counts
// as visible, a tree or a thick cloud does not, a thin cloud edge counts in part (it glows).
// One point-spread function, three falloffs: a bright core just outside the limb, a narrow halo
// (about 1.5 degrees) and faint wide wings, so the sky round the sun is not washed out.
vec3 sunGlare(ivec2 px) {
    vec3 sv = sunPosition;
    if (sv.z >= 0.0) return vec3(0.0);                      // behind the camera
    vec4 sc = gbufferProjection * vec4(sv, 1.0);
    vec2 suv = sc.xy / sc.w * 0.5 + 0.5;
    if (any(lessThan(suv, vec2(-0.1))) || any(greaterThan(suv, vec2(1.1)))) return vec3(0.0);
    float pxA = 2.0 / (gbufferProjection[1][1] * viewHeight);
    float rpx = SUN_REAL_R / pxA * 0.45;
    float vis = 0.0;
    float want = 0.30 * sunPeak();
    for (int i = 0; i < 9; i++) {
        float a = float(i) * 2.39996;
        vec2 o = i == 0 ? vec2(0.0) : vec2(cos(a), sin(a)) * rpx * sqrt(float(i) / 8.0);
        ivec2 q = ivec2(suv * vec2(viewWidth, viewHeight) + o);
        if (any(lessThan(q, ivec2(0))) || q.x >= int(viewWidth) || q.y >= int(viewHeight)) continue;
        vec3 e = sceneExposed(q);
        float sky = step(1.0, texelFetch(depthtex0, q, 0).r);
        vis += sky * clamp(max(e.r, max(e.g, e.b)) / want, 0.0, 1.0);
    }
    vis /= 9.0;
    if (vis <= 0.0) return vec3(0.0);
    vec3 dir = normalize(viewFromScreen(uv, 1.0));
    float th = acos(clamp(dot(dir, normalize(sv)), -1.0, 1.0));
    // r008: the falloffs start at the limb, not the centre, so a larger disk keeps a tight bright
    // corona hugging its edge (the "source" the owner missed in r007) instead of a glow that only
    // reaches past a big disk's rim at a fraction of its strength. Inside the disk: none (the disk
    // is the sky pass's, crisp).
    float thl = max(th - SUN_REAL_R, 0.0);
    float inDisk = smoothstep(SUN_REAL_R * 0.85, SUN_REAL_R * 1.05, th);
    // uf (forest_golden): with the 3x disk, leaves in front of the sun showed a bright ring at the
    // limb (no glare inside, the full core just outside). Only open sky skips the glare inside.
    inDisk = mix(1.0, inDisk, step(1.0, texelFetch(depthtex0, px, 0).r));
    // Loop 3 (critic uh: a faint pale glare disk still painted over the leaves where the sun sits
    // behind them): on land the glare close to the sun is cut and fades back in over 2.5 radii, so
    // leaves in front of a partly hidden sun stay dark, with no ring and no disk.
    if (texelFetch(depthtex0, px, 0).r < 1.0) inDisk *= mix(0.12, 1.0, smoothstep(SUN_REAL_R * 0.9, SUN_REAL_R * 2.5, th));
    float psf = (0.12 * exp(-thl / 0.0026) + 0.030 * exp(-thl / 0.016) + 0.0045 * exp(-thl / 0.09)) * inDisk;   // pa: 0.22/0.045/0.006 washed out the gold sky; loop 3: core 0.10 @ 0.0040 -> 0.12 @ 0.0026, a tighter corona
    vec3 E = sunIrradiance() * exposure() * (1.0 - rainStrength);
    vec3 g = E * psf * vis;
#if QF_LENS == 1
    // A faint lens: a six-point starburst close round the sun and three dim ghosts on the line
    // from the sun through the screen centre, tinted as coated glass reflects.
    vec2 d = (uv - suv) * vec2(viewWidth / viewHeight, 1.0);
    float phi = atan(d.y, d.x);
    float star = pow(abs(cos(3.0 * phi + 0.35)), 90.0) * exp(-th / 0.035) * 0.05;
    g += E * star * vis;
    vec2 axis = vec2(0.5) - suv;
    const vec3 GC[3] = vec3[3](vec3(0.55, 0.75, 1.0), vec3(1.0, 0.75, 0.45), vec3(0.6, 1.0, 0.7));
    const float GP[3] = float[3](0.62, 1.15, 1.6), GR[3] = float[3](0.030, 0.055, 0.018);
    for (int k = 0; k < 3; k++) {
        vec2 c = suv + axis * GP[k] * 2.0;
        float r = length((uv - c) * vec2(viewWidth / viewHeight, 1.0));
        g += E * GC[k] * smoothstep(GR[k], GR[k] * 0.6, r) * 0.0035 * vis;
    }
#endif
    return g;
}
#endif

void main() {
    ivec2 px = ivec2(gl_FragCoord.xy);
    vec3 col;
    vec3 glare = vec3(0.0);
#if QF_SUN == 1
    glare = sunGlare(px);
#endif
#if QF_TAA
#if QF_CAL_BLOOM > 0 || QF_CAL_GRADE > 0
    col = display(sceneExposed(px) + calBloom(px) + glare);
#else
    col = display(sceneExposed(px) + glare);
#endif
#else
    // Potato: a cheap edge-aware blend over the 4 neighbours where contrast is high.
    vec3 c = display(sceneExposed(px) + glare);
    vec3 n = display(sceneExposed(px + ivec2(0, 1)));
    vec3 s = display(sceneExposed(px + ivec2(0, -1)));
    vec3 e = display(sceneExposed(px + ivec2(1, 0)));
    vec3 w = display(sceneExposed(px + ivec2(-1, 0)));
    float lc = luminance(c), ln = luminance(n), ls = luminance(s), le = luminance(e), lw = luminance(w);
    float range = max(max(max(ln, ls), max(le, lw)), lc) - min(min(min(ln, ls), min(le, lw)), lc);
    float k = smoothstep(0.08, 0.3, range) * 0.5;
    col = mix(c, (n + s + e + w) * 0.25, k);
#endif

#if QF_DEBUG_VIEW == 1
    vec4 g1 = texelFetch(colortex1, px, 0);
    if (texelFetch(depthtex0, px, 0).r < 1.0) col = materialDebugColor(unpackMaterial(g1)) * (0.55 + 0.45 * luminance(col));
#elif QF_DEBUG_VIEW == 2
    col = decodeNormal(texelFetch(colortex1, px, 0).rg) * 0.5 + 0.5;
#elif QF_DEBUG_VIEW == 3
    col = texelFetch(colortex2, px, 0).rgg * vec3(1.0, 1.0, 0.0) + vec3(0.0, 0.0, texelFetch(colortex2, px, 0).b);
#elif QF_DEBUG_VIEW == 4 || QF_DEBUG_VIEW == 5 || QF_DEBUG_VIEW == 7
    col = linearToSrgb(texelFetch(colortex3, px, 0).rgb);
#elif QF_DEBUG_VIEW == 6 && QF_SHADOWS
    col = vec3(pow(texture(shadowtex0, uv).r, 8.0));   // the shadow map itself, contrast-stretched
#elif QF_DEBUG_VIEW == 9
    // colortex5 stretched over the screen, raw (no exposure, no tone map): the transmittance
    // table (texel rows 0-63, at the bottom) at gain 1, the constants (rows 64-65 from x 32)
    // at 0.1, the rest at gain 10.
    ivec2 q = ivec2(uv * LUT_TEX_SIZE);   // texel row 0 at the bottom of the screen
    vec3 v = texelFetch(colortex5, q, 0).rgb * (q.y < 64 ? 1.0 : (q.y < 66 && q.x >= 32 ? 0.1 : 10.0));
    outColor = vec4(linearToSrgb(v), 1.0);
    return;
#elif QF_DEBUG_VIEW == 8
    // The normal frame, with a row of numeric patches at the top left that
    // tools/shaders/review/read_meter.py decodes from a screenshot.
    int patchId = meterPatch(px);
    if (patchId >= 0) {
        outColor = vec4(meterReadout(patchId), 1.0);
        return;
    }
#endif
    // Triangular dither: no banding in dark skies and water.
    float dn = hash12(gl_FragCoord.xy + float(frameCounter % 16) * 17.0) + hash12(gl_FragCoord.yx * 1.37 + 3.0) - 1.0;
    outColor = vec4(col + dn / 255.0, 1.0);
}
#endif
