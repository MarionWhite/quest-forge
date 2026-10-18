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

vec3 display(vec3 exposed) {
    return linearToSrgb(tonemapNeutral(exposed));
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

void main() {
    ivec2 px = ivec2(gl_FragCoord.xy);
    vec3 col;
#if QF_TAA
    col = display(sceneExposed(px));
#else
    // Potato: a cheap edge-aware blend over the 4 neighbours where contrast is high.
    vec3 c = display(sceneExposed(px));
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
