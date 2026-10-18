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
#endif
    // Triangular dither: no banding in dark skies and water.
    float dn = hash12(gl_FragCoord.xy + float(frameCounter % 16) * 17.0) + hash12(gl_FragCoord.yx * 1.37 + 3.0) - 1.0;
    outColor = vec4(col + dn / 255.0, 1.0);
}
#endif
