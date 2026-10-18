// Every gbuffers_* program is this file with a kind defined by its stub:
//   GB_DEFERRED  writes the G-buffer (colortex0/1/2); lit later in deferred.fsh.
//                GB_TERRAIN adds block IDs and wind; GB_ENTITY the hurt flash;
//                GB_UNTEXTURED for lines; GB_EMISSIVE marks the result self-lit.
//   GB_WATER     translucent terrain: water writes only its surface (normal, material);
//                composite.fsh shades it. Glass, ice and the rest are lit here, forward.
//   GB_FORWARD   lit here and blended into colortex3 (the hand, weather).
//   GB_SKY       vanilla sky geometry: discarded, deferred.fsh draws the sky.
//   GB_DAMAGE    block-breaking cracks: multiplied into the albedo.
// About 8 real variants through Iris's fallback chain (rule 13).

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"

#ifdef VSH

#ifdef GB_TERRAIN
in vec4 mc_Entity;
in vec2 mc_midTexCoord;
#include "/lib/waving.glsl"
#endif

out vec2 vUV;
out vec2 vLM;
out vec4 vColor;
out vec3 vNormal;
out vec3 vScenePos;
flat out int vMat;

void main() {
    vUV = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    vLM = clamp(((gl_TextureMatrix[1] * gl_MultiTexCoord1).xy - 1.0 / 32.0) * (16.0 / 15.0), 0.0, 1.0);
    vColor = gl_Color;
    vMat = MAT_NONE;
    vec4 viewPos = gl_ModelViewMatrix * gl_Vertex;
#ifdef GB_SKY
    gl_Position = gl_ProjectionMatrix * viewPos;
    vScenePos = vec3(0.0);
    vNormal = vec3(0.0, 1.0, 0.0);
    return;
#else
    vScenePos = sceneFromView(viewPos.xyz);
#ifdef GB_TERRAIN
    vMat = materialFromBlockId(int(mc_Entity.x + 0.5));
    bool top = gl_MultiTexCoord0.t < mc_midTexCoord.t;
    vScenePos += windOffset(vScenePos + cameraPosition, vMat, top, vLM.y);
    viewPos = gbufferModelView * vec4(vScenePos, 1.0);
#endif
    gl_Position = gl_ProjectionMatrix * viewPos;
#if QF_TAA
    gl_Position.xy += taaJitter() * gl_Position.w;
#endif
    vNormal = normalize(mat3(gbufferModelViewInverse) * (gl_NormalMatrix * gl_Normal));
#endif
}

#endif // VSH

#ifdef FSH

in vec2 vUV;
in vec2 vLM;
in vec4 vColor;
in vec3 vNormal;
in vec3 vScenePos;
flat in int vMat;

uniform sampler2D gtexture;
#ifdef GB_ENTITY
uniform vec4 entityColor;
#endif

#if defined GB_FORWARD || defined GB_WATER
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sky.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"
#include "/lib/water.glsl"
#endif

vec4 baseColor() {
#ifdef GB_UNTEXTURED
    return vColor;
#else
    vec4 c = texture(gtexture, vUV);
    // separateAo: rgb is the biome tint, alpha the vertex AO (handled below).
    c.rgb *= vColor.rgb;
    return c;
#endif
}

#if defined GB_SKY

void main() {
    discard;
}

#elif defined GB_GLINT

// Enchantment glint: vanilla draws it additively over the item, so it is written straight
// into colortex3 with vanilla's blend. Over the hand that is after deferred and works; on
// worn armour (drawn before deferred) the lit G-buffer overwrites it (milestone 1 known issue).
/* RENDERTARGETS: 3 */
layout(location = 0) out vec4 outColor;
void main() {
    vec4 c = texture(gtexture, vUV) * vColor;
    outColor = vec4(toLinear(c.rgb) * 0.35, c.a);
}

#elif defined GB_DAMAGE

/* RENDERTARGETS: 0 */
layout(location = 0) out vec4 outAlbedo;
void main() {
    vec4 c = texture(gtexture, vUV) * vColor;
    if (c.a < 0.01) discard;
    outAlbedo = c;   // vanilla's multiply blend darkens the albedo underneath
}

#elif defined GB_DEFERRED

/* RENDERTARGETS: 0,1,2 */
layout(location = 0) out vec4 outAlbedo;
layout(location = 1) out vec4 outNormal;
layout(location = 2) out vec4 outLight;

void main() {
    vec4 c = baseColor();
    if (c.a < 0.1) discard;
#ifdef GB_ENTITY
    c.rgb = mix(c.rgb, entityColor.rgb, entityColor.a);
#endif
    int mat = vMat;
    int flag = FLAG_STATIC;
#ifdef GB_ENTITY
    mat = MAT_ENTITY;
    flag = FLAG_MOVING;
#endif
#ifdef GB_EMISSIVE
    mat = MAT_EMISSIVE;
#endif
    vec3 n = normalize(vNormal);
    if (!gl_FrontFacing) n = -n;
#ifdef GB_UNTEXTURED
    n = vec3(0.0, 1.0, 0.0);
#endif
    float ao = 1.0;
#ifdef GB_TERRAIN
    ao = vColor.a;
#endif
    outAlbedo = vec4(c.rgb, 1.0);
    outNormal = packGbuffer1(n, mat, flag);
    outLight = vec4(vLM, ao, 1.0);
}

#elif defined GB_WATER

/* RENDERTARGETS: 3,1,2 */
layout(location = 0) out vec4 outColor;
layout(location = 1) out vec4 outNormal;
layout(location = 2) out vec4 outLight;

void main() {
    vec3 face = normalize(vNormal);
    if (vMat == MAT_WATER) {
        // The surface only. Alpha 0 leaves the lit scene below untouched for composite.fsh.
        vec3 n = waterNormal(vScenePos + cameraPosition, face);
        outColor = vec4(0.0);
        outNormal = packGbuffer1(n, MAT_WATER, FLAG_STATIC);
        outLight = vec4(vLM, 1.0, 1.0);
        return;
    }
    vec4 c = baseColor();
    if (c.a < 0.02) discard;
    Surface s;
    s.albedo = toLinear(c.rgb);
    s.normal = gl_FrontFacing ? face : -face;
    s.geoNormal = s.normal;
    s.mat = vMat == MAT_NONE ? MAT_GLASS : vMat;
    s.blockLight = vLM.x;
    s.skyLight = vLM.y;
    s.ao = 1.0;
    s.scenePos = vScenePos;
    vec3 viewDir = normalize(vScenePos);
    vec3 lit = shadeSurface(s, viewDir, gl_FragCoord.xy);
    // A touch of sky reflection on glass and ice.
    vec3 R = reflect(viewDir, s.normal);
    float F = fresnelSchlick(max(dot(-viewDir, s.normal), 0.0), vec3(0.04)).x;
    lit += skyScatter(R) * F * s.skyLight * s.skyLight;
    outColor = vec4(lit, c.a);
    outNormal = packGbuffer1(s.normal, s.mat, FLAG_STATIC);
    outLight = vec4(vLM, 1.0, 1.0);
}

#elif defined GB_FORWARD

#ifdef GB_WEATHER
/* RENDERTARGETS: 3 */
layout(location = 0) out vec4 outColor;
#else
/* RENDERTARGETS: 3,1 */
layout(location = 0) out vec4 outColor;
layout(location = 1) out vec4 outNormal;
#endif

void main() {
    vec4 c = baseColor();
    if (c.a < 0.02) discard;
    vec3 face = normalize(vNormal);
    if (!gl_FrontFacing) face = -face;
#ifdef GB_WEATHER
    // Rain and snow: lit by the sky and the light, no shadow lookup (they are in front of it).
    vec3 E = skyIrradiance(vec3(0.0, 1.0, 0.0)) * vLM.y + lightIrradiance() * 0.25 * vLM.y
           + blockIrradiance(vLM.x) + nightFloor();
    outColor = vec4(toLinear(c.rgb) / PI * E * 1.4, c.a * 0.55);
#else
    Surface s;
    s.albedo = toLinear(c.rgb);
    s.normal = face;
    s.geoNormal = face;
    s.mat = MAT_FORWARD;
    s.blockLight = vLM.x;
    s.skyLight = vLM.y;
    s.ao = 1.0;
    s.scenePos = vScenePos;
    vec3 viewDir = normalize(vScenePos);
    outColor = vec4(shadeSurface(s, viewDir, gl_FragCoord.xy), c.a);
    int flag = FLAG_STATIC;
#ifdef GB_HAND
    flag = FLAG_HAND;
#endif
    outNormal = packGbuffer1(face, MAT_FORWARD, flag);
#endif
}

#endif
#endif // FSH
