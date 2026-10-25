// deferred: lights the opaque G-buffer and draws the sky into colortex3 (HDR), before any
// translucent geometry. One full-screen pass on every tier (rule 6).

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/buffers.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sun.glsl"
#include "/lib/sky.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"

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
uniform sampler2D depthtex0;

/* RENDERTARGETS: 3 */
layout(location = 0) out vec4 outColor;

void main() {
    ivec2 px = ivec2(gl_FragCoord.xy);
    float depth = texelFetch(depthtex0, px, 0).r;
    vec3 viewPos = viewFromScreen(uv, depth);
    vec3 scenePos = sceneFromView(viewPos);
    vec3 viewDir = normalize(scenePos);

    if (depth >= 1.0) {
        outColor = vec4(skyRadiance(viewDir), 1.0);
        return;
    }
    vec4 g1 = texelFetch(colortex1, px, 0);
    int mat = unpackMaterial(g1);
    if (mat == MAT_FORWARD) {
        // Lit by its own program already (drawn before this pass): keep it.
        outColor = texelFetch(colortex3, px, 0);
        return;
    }
    vec4 g2 = texelFetch(colortex2, px, 0);
    Surface s;
    s.albedo = toLinear(texelFetch(colortex0, px, 0).rgb);
    s.normal = decodeNormal(g1.rg);
    s.geoNormal = s.normal;
    s.mat = mat;
    s.blockLight = g2.r;
    s.skyLight = g2.g;
    s.ao = g2.b;
    s.scenePos = scenePos;
    s.smoothness = 0.0;
    s.f0 = 0.0;
#if QF_PBR == 1
    // gbuffers.glsl stores 1 - value, so blocks without maps (and entities) read 0.
    s.smoothness = 1.0 - texelFetch(colortex0, px, 0).a;
    s.f0 = 1.0 - g2.a;
#endif
    outColor = vec4(shadeSurface(s, viewDir, gl_FragCoord.xy), 1.0);
}
#endif
