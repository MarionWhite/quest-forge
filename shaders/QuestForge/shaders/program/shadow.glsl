// The shadow pass (rule 1: the only extra geometry pass). Distorted like lib/shadows.glsl
// reads it, with the same wind as gbuffers_terrain so leaf shadows move with the leaves.

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"
#include "/lib/shadows.glsl"

#ifdef VSH

in vec4 mc_Entity;
in vec2 mc_midTexCoord;
#include "/lib/waving.glsl"

out vec2 vUV;
out vec4 vColor;
flat out int vMat;

void main() {
    vUV = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    vColor = gl_Color;
    vMat = materialFromBlockId(int(mc_Entity.x + 0.5));
    vec4 sv = gl_ModelViewMatrix * gl_Vertex;
    vec3 scenePos = (shadowModelViewInverse * sv).xyz;
    vec2 lm = clamp(((gl_TextureMatrix[1] * gl_MultiTexCoord1).xy - 1.0 / 32.0) * (16.0 / 15.0), 0.0, 1.0);
    bool top = gl_MultiTexCoord0.t < mc_midTexCoord.t;
    scenePos += windOffset(scenePos + cameraPosition, vMat, top, lm.y);
    sv = shadowModelView * vec4(scenePos, 1.0);
    gl_Position = gl_ProjectionMatrix * sv;
    gl_Position.xyz = distortShadow(gl_Position.xyz);
}

#endif

#ifdef FSH

in vec2 vUV;
in vec4 vColor;
flat in int vMat;
uniform sampler2D gtexture;

// Depth only: writing no colour keeps Iris from allocating shadowcolor0.
void main() {
    if (vMat == MAT_WATER || vMat == MAT_WEB) discard;   // no water or cobweb shadows (yet)
    if (texture(gtexture, vUV).a < 0.1) discard;
}

#endif
