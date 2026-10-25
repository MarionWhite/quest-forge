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
#if QF_PBR == 1 && defined GB_TERRAIN
// LabPBR 1.3 maps from the resource pack (Iris stitches <name>_n / <name>_s into these atlases;
// blocks without maps read Iris's defaults: a flat normal and no specular).
uniform sampler2D normals;
uniform sampler2D specular;
#endif

#if defined GB_FORWARD || defined GB_WATER
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sun.glsl"
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
    vec3 tint = vColor.rgb;
#if defined GB_TERRAIN && !defined GB_WATER
    // Biome tints (grass, leaves, vines) are made for vanilla's flat light. Under a bright,
    // slightly warm sun they read lime (r14 critic: neutral colour at noon), so pull coloured
    // tints a little towards a deeper, less yellow green. Untinted blocks (tint ~white) and
    // water are unchanged.
    float spread = max(tint.r, max(tint.g, tint.b)) - min(tint.r, min(tint.g, tint.b));
    if (spread > 0.04) {
        float tl = dot(tint, vec3(0.2126, 0.7152, 0.0722));
        // Only yellow-greens get the red pull: the blue-green Extreme Hills grass turned mint
        // under it (r002 biome-hills).
        float yellow = smoothstep(0.02, 0.2, tint.r - tint.b);
        tint = mix(vec3(tl), tint, QF_TINT_SAT) * vec3(mix(1.0, QF_TINT_RED, yellow), 1.0, 1.0);
    }
#endif
    c.rgb *= tint;
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
#ifdef GB_PARTICLE
    // Under water, vanilla's suspended-particle texture is near black; against the pack's lit
    // water it read as dark squares (r14 critic; look bible failure class 4). Make it pale silt.
    if (isEyeInWater == 1) c.rgb = mix(c.rgb, vec3(0.62, 0.70, 0.66), 0.7);
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
#if defined GB_UNTEXTURED || defined GB_PARTICLE
    // Particles are camera-facing quads without a usable vertex normal; lit through it they
    // came out near black (dark specks under water, r14 critic). Light them as if facing up.
    n = vec3(0.0, 1.0, 0.0);
#endif
    float ao = 1.0;
#ifdef GB_TERRAIN
    ao = vColor.a;
#endif
    float pbrSmooth = 0.0, pbrF0 = 0.0;
#if QF_PBR == 1 && defined GB_TERRAIN
    {
        // Normal map in a cotangent frame from the screen derivatives (no tangent attribute
        // needed); the maps are DirectX-style, +y down the texture, which is +v in the atlas.
        vec4 nm = texture(normals, vUV);
        vec4 sp = texture(specular, vUV);
        vec2 nxy = nm.rg * 2.0 - 1.0;
        vec3 nt = vec3(nxy, sqrt(clamp(1.0 - dot(nxy, nxy), 0.0, 1.0)));
        vec3 dp1 = dFdx(vScenePos), dp2 = dFdy(vScenePos);
        vec2 du1 = dFdx(vUV), du2 = dFdy(vUV);
        vec3 dp2p = cross(dp2, n), dp1p = cross(n, dp1);
        vec3 T = dp2p * du1.x + dp1p * du2.x;
        vec3 B = dp2p * du1.y + dp1p * du2.y;
        float im = inversesqrt(max(max(dot(T, T), dot(B, B)), 1e-24));
        vec3 nn = T * im * nt.x + B * im * nt.y + n * nt.z;
        if (dot(nn, nn) > 0.25) n = normalize(nn);
        ao *= mix(1.0, nm.b, 0.8);
        pbrSmooth = sp.r;
        pbrF0 = sp.g;
    }
#endif
    outAlbedo = vec4(c.rgb, 1.0 - pbrSmooth);
    outNormal = packGbuffer1(n, mat, flag);
    outLight = vec4(vLM, ao, 1.0 - pbrF0);
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
#if QF_WAVES == 1
        // colortex2.a carries the filtered slope variance (roughness) to composite.fsh.
        vec4 nr = waterNormalRough(vScenePos + cameraPosition, face);
        vec3 n = nr.xyz;
        float roughA = clamp(sqrt(nr.w) * 8.0, 0.0, 1.0);
#else
        vec3 n = waterNormal(vScenePos + cameraPosition, face);
        float roughA = 0.0;
#endif
        outColor = vec4(0.0);
        outNormal = packGbuffer1(n, MAT_WATER, FLAG_STATIC);
        // colortex2.b: the swamp share from the game's own water tint (lib/water.glsl), which
        // composite.glsl blends over a few blocks (r007, QF_WATER_BLEND).
        float swampT = 0.0;
#if QF_BIOME_WATER == 1 && QF_CAL_WATER == 0
        swampT = swampFromTint(vColor.rgb);
#endif
        outLight = vec4(vLM, swampT, roughA);
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
    s.smoothness = 0.0;
    s.f0 = 0.0;
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
    s.smoothness = 0.0;
    s.f0 = 0.0;
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
