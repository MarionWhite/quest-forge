// Uniforms, buffer layout and small helpers shared by every program.
//
// BUFFERS (formats are declared in final.fsh)
//   colortex0  RGBA8          albedo (sRGB-encoded texture colour)
//   colortex1  RGB10_A2       rg: octahedral normal, b: material index / 1023, a: flag / 3
//   colortex2  RGBA8          r: block light, g: sky light, b: ambient occlusion, a: unused
//   colortex3  R11G11B10F     HDR scene radiance (deferred, translucents, composite)
//   colortex4  RGBA16F        TAA history: rgb exposed colour, a: linear depth (Low and up)
//   colortex5  RGBA16F 256x320  sky lookup tables and per-frame constants (lib/lut.glsl)
// Five full-screen targets from Low up, four on Potato (rule 10). colortex5 is a small
// fixed-size buffer, not a full-screen bandwidth cost.

uniform mat4 gbufferModelView;
uniform mat4 gbufferModelViewInverse;
uniform mat4 gbufferProjection;
uniform mat4 gbufferProjectionInverse;
uniform mat4 gbufferPreviousModelView;
uniform mat4 gbufferPreviousProjection;
uniform mat4 shadowModelView;
uniform mat4 shadowModelViewInverse;
uniform mat4 shadowProjection;

uniform vec3 cameraPosition;
uniform vec3 previousCameraPosition;
uniform vec3 sunPosition;
uniform vec3 moonPosition;
uniform vec3 shadowLightPosition;

uniform float viewWidth;
uniform float viewHeight;
uniform float near;
uniform float far;
uniform float frameTimeCounter;
uniform float frameTime;
uniform float rainStrength;
uniform float nightVision;
uniform int frameCounter;
uniform int worldTime;
uniform int moonPhase;
uniform int isEyeInWater;
uniform int heldBlockLightValue;
uniform ivec2 eyeBrightnessSmooth;

const float PI = 3.14159265359;

// Material indices stored in colortex1.b. Terrain gets them from block.properties through
// lib/materials.glsl; the others are set by the program that draws them.
const int MAT_NONE     = 0;
const int MAT_WATER    = 1;
const int MAT_LAVA     = 2;
const int MAT_LEAVES   = 3;
const int MAT_PLANT    = 4;
const int MAT_WEB      = 5;
const int MAT_EMISSIVE = 6;
const int MAT_GLASS    = 7;
const int MAT_METAL    = 8;
const int MAT_POLISHED = 9;
const int MAT_ORE      = 10;
const int MAT_ENTITY   = 16;
const int MAT_FORWARD  = 30;   // already lit by its own program: deferred passes it through

// colortex1.a flags, for TAA.
const int FLAG_STATIC = 0;
const int FLAG_MOVING = 1;     // entities: weaker history
const int FLAG_HAND   = 2;     // no reprojection

vec2 octWrap(vec2 v) {
    return (1.0 - abs(v.yx)) * vec2(v.x >= 0.0 ? 1.0 : -1.0, v.y >= 0.0 ? 1.0 : -1.0);
}

vec2 encodeNormal(vec3 n) {
    n /= abs(n.x) + abs(n.y) + abs(n.z);
    vec2 e = n.z >= 0.0 ? n.xy : octWrap(n.xy);
    return e * 0.5 + 0.5;
}

vec3 decodeNormal(vec2 e) {
    e = e * 2.0 - 1.0;
    vec3 n = vec3(e, 1.0 - abs(e.x) - abs(e.y));
    float t = clamp(-n.z, 0.0, 1.0);
    n.x += n.x >= 0.0 ? -t : t;
    n.y += n.y >= 0.0 ? -t : t;
    return normalize(n);
}

vec4 packGbuffer1(vec3 normalWorld, int mat, int flag) {
    return vec4(encodeNormal(normalWorld), float(mat) / 1023.0, float(flag) / 3.0);
}

int unpackMaterial(vec4 g1) {
    return int(g1.b * 1023.0 + 0.5);
}

int unpackFlag(vec4 g1) {
    return int(g1.a * 3.0 + 0.5);
}

vec3 toLinear(vec3 c) {
    return c * c * (c * 0.2848 + 0.7152);   // close fit of the sRGB curve, cheap
}

float luminance(vec3 c) {
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

// Screen uv + depth -> view space / player-relative world space ("scene" space).
vec3 viewFromScreen(vec2 uv, float depth) {
    vec4 p = gbufferProjectionInverse * vec4(vec3(uv, depth) * 2.0 - 1.0, 1.0);
    return p.xyz / p.w;
}

vec3 sceneFromView(vec3 v) {
    return mat3(gbufferModelViewInverse) * v + gbufferModelViewInverse[3].xyz;
}

float linearDepth(float depth) {
    return (2.0 * near * far) / (far + near - (depth * 2.0 - 1.0) * (far - near));
}

// Interleaved gradient noise (Jimenez 2014): cheap per-pixel jitter that TAA resolves.
float ign(vec2 p) {
    return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))));
}

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float hash13(vec3 p) {
    p = fract(p * 0.1031);
    p += dot(p, p.zyx + 31.32);
    return fract((p.x + p.y) * p.z);
}

// Animation clock; QF_STILL freezes it so two frames of a still camera differ only by noise.
float animTime() {
#if QF_STILL
    return 0.0;
#else
    return frameTimeCounter;
#endif
}

// World-space directions of the sun and moon (unit vectors, y up).
vec3 sunDirWorld() {
    return normalize(mat3(gbufferModelViewInverse) * sunPosition);
}

vec3 moonDirWorld() {
    return normalize(mat3(gbufferModelViewInverse) * moonPosition);
}

// 1 at full moon (phase 0), 0 at new moon (phase 4).
float moonBrightness() {
    return 0.5 + 0.5 * cos(float(moonPhase) * (PI / 4.0));
}

// Subpixel jitter for TAA: Halton (2, 3), 8 positions, in NDC units.
vec2 taaJitter() {
    int i = frameCounter % 8;
    const vec2 h[8] = vec2[8](
        vec2(0.5, 0.333333), vec2(0.25, 0.666667), vec2(0.75, 0.111111), vec2(0.125, 0.444444),
        vec2(0.625, 0.777778), vec2(0.375, 0.222222), vec2(0.875, 0.555556), vec2(0.0625, 0.888889));
    return (h[i] * 2.0 - 1.0) / vec2(viewWidth, viewHeight);
}
