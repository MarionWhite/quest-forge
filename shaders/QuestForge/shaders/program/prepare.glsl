// prepare: runs before the world each frame, at colortex5's 256x320 (not a full-screen
// pass). It builds the sky tables (rule 9), the light constants every later pass reads,
// and the auto-exposure (look bible 2). See lib/lut.glsl for the layout.

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/buffers.glsl"
#include "/lib/common.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sky.glsl"

#ifdef VSH
void main() {
    gl_Position = ftransform();
}
#endif

#ifdef FSH

uniform sampler2D colortex3;
const bool colortex3MipmapEnabled = true;

/* RENDERTARGETS: 5 */
layout(location = 0) out vec4 outLut;

// Exposure bounds (linear multipliers on scene radiance). The upper bound keeps nights
// dark instead of letting the camera turn them into a grey day (look bible 1 and 2).
const float EXPOSURE_MIN = 0.12;
const float EXPOSURE_MAX = 30.0;
const float EXPOSURE_KEY = 0.17;

bool inRegion(ivec2 p, ivec2 origin, ivec2 size) {
    return all(greaterThanEqual(p, origin)) && all(lessThan(p, origin + size));
}

vec2 regionCoord(ivec2 p, ivec2 origin, ivec2 size) {
    return vec2(p - origin) / vec2(size - 1);
}

vec3 buildMultiScatter(float r, float muS) {
    vec3 sun = vec3(sqrt(max(1.0 - muS * muS, 0.0)), muS, 0.0);
    vec3 o = vec3(0.0, r, 0.0);
    vec3 L2 = vec3(0.0), fms = vec3(0.0);
    const int DIRS = 64;
    const int STEPS = 20;
    for (int d = 0; d < DIRS; d++) {
        // Fibonacci sphere.
        float z = 1.0 - 2.0 * (float(d) + 0.5) / float(DIRS);
        float a = float(d) * 2.39996323;
        float s = sqrt(1.0 - z * z);
        vec3 dir = vec3(s * cos(a), z, s * sin(a));
        float mu = dir.y;
        float tG = distToGround(r, mu);
        float tMax = tG > 0.0 ? tG : distToSphere(r, mu, ATM_RT);
        float dt = tMax / float(STEPS);
        vec3 T = vec3(1.0);
        for (int i = 0; i < STEPS; i++) {
            vec3 pos = o + dir * ((float(i) + 0.5) * dt);
            float pr = length(pos);
            Medium m = mediumAt(pr - ATM_RG);
            vec3 sc = m.rayleigh + vec3(m.mie);
            vec3 stepT = exp(-m.extinction * dt);
            vec3 integ = (1.0 - stepT) / max(m.extinction, vec3(1e-7));
            vec3 Ts = lightTransmittance(pr, dot(pos / pr, sun));
            L2 += T * Ts * sc * (1.0 / (4.0 * PI)) * integ;
            fms += T * sc * integ;
            T *= stepT;
        }
        if (tG > 0.0) {
            vec3 pos = o + dir * tG;
            vec3 up = normalize(pos);
            float muG = dot(up, sun);
            L2 += T * lightTransmittance(ATM_RG, muG) * max(muG, 0.0) * GROUND_ALBEDO / PI;
        }
    }
    L2 /= float(DIRS);
    fms /= float(DIRS);
    return L2 / max(1.0 - fms, vec3(1e-3));
}

// Sky radiance along dir from radius r, lit by a unit light from `light` (both in the local
// frame where up is +y at the camera).
vec3 integrateSky(float r, vec3 dir, vec3 light) {
    vec3 o = vec3(0.0, r, 0.0);
    float tG = distToGround(r, dir.y);
    float tT = distToSphere(r, dir.y, ATM_RT);
    if (tT < 0.0) return vec3(0.0);
    float tMax = tG > 0.0 ? tG : tT;
    float c = dot(dir, light);
    float pR = phaseRayleigh(c);
    float pM = phaseMie(c);
    vec3 L = vec3(0.0), T = vec3(1.0);
    const int N = QF_SKY_STEPS;
    float tPrev = 0.0;
    for (int i = 0; i < N; i++) {
        float tNext = tMax * pow((float(i) + 1.0) / float(N), 2.0);
        float t = 0.5 * (tPrev + tNext);
        float dt = tNext - tPrev;
        tPrev = tNext;
        vec3 pos = o + dir * t;
        float pr = length(pos);
        Medium m = mediumAt(pr - ATM_RG);
        float muL = dot(pos / pr, light);
        vec3 Tl = lightTransmittance(pr, muL);
        vec3 ms = lookupMultiScatter(pr, muL);
        vec3 S = Tl * (m.rayleigh * pR + vec3(m.mie * pM)) + ms * (m.rayleigh + vec3(m.mie));
        vec3 stepT = exp(-m.extinction * dt);
        L += T * S * (1.0 - stepT) / max(m.extinction, vec3(1e-7));
        T *= stepT;
    }
    if (tG > 0.0) {
        vec3 up = normalize(o + dir * tG);
        float muG = dot(up, light);
        L += T * lightTransmittance(ATM_RG, muG) * max(muG, 0.0) * GROUND_ALBEDO / PI;
    }
    return L;
}

vec3 skyViewTexel(ivec2 p, ivec2 origin, vec3 lightWorld) {
    vec2 x = regionCoord(p, origin, LUT_SV_SIZE);
    float r = cameraRadius();
    vec3 dir = skyViewDir(x, r);
    vec3 light = vec3(sqrt(max(1.0 - lightWorld.y * lightWorld.y, 0.0)), lightWorld.y, 0.0);
    return integrateSky(r, dir, light);
}

void ambientIrradiance(out vec3 up, out vec3 side) {
    up = vec3(0.0);
    side = vec3(0.0);
    const int NE = 6, NA = 12;
    for (int i = 0; i < NE; i++) {
        float el = (float(i) + 0.5) / float(NE) * (0.5 * PI);
        for (int j = 0; j < NA; j++) {
            float az = (float(j) + 0.5) / float(NA) * (2.0 * PI);
            vec3 dir = vec3(cos(el) * cos(az), sin(el), cos(el) * sin(az));
            float dOmega = cos(el) * (0.5 * PI / float(NE)) * (2.0 * PI / float(NA));
            vec3 L = skyScatter(dir);
            up += L * sin(el) * dOmega;
            float s = max(dir.x, 0.0) + max(-dir.x, 0.0) + max(dir.z, 0.0) + max(-dir.z, 0.0);
            side += L * 0.25 * s * dOmega;
        }
    }
    side += up * GROUND_ALBEDO * 0.5;   // the ground a wall sees below the horizon
}

vec4 computeExposure(float prevExposure) {
    float lod = max(floor(log2(max(viewWidth, viewHeight))) - 5.0, 0.0);
    float sum = 0.0, wsum = 0.0;
    const int GX = 16, GY = 9;
    for (int y = 0; y < GY; y++) {
        for (int x = 0; x < GX; x++) {
            vec2 uv = (vec2(x, y) + 0.5) / vec2(GX, GY);
            vec2 c = uv - 0.5;
            float w = exp(-dot(c, c) * 4.0);   // centre-weighted
            float l = luminance(textureLod(colortex3, uv, lod).rgb);
            sum += log2(max(l, 1e-6)) * w;
            wsum += w;
        }
    }
    float avg = exp2(sum / wsum);
    float target = clamp(EXPOSURE_KEY / avg, EXPOSURE_MIN, EXPOSURE_MAX) * exp2(QF_EXPOSURE_BIAS);
    float prev = prevExposure;
    if (!(prev > 0.0) || prev > 1e4) prev = target;   // first frame, or after a reload
    // Slow and asymmetric: adapting to a bright view takes ~1.2 s, to darkness ~3 s.
    float tau = target < prev ? 1.2 : 3.0;
    float k = 1.0 - exp(-max(frameTime, 0.0) / tau);
    float e = exp2(mix(log2(prev), log2(target), k));
    return vec4(e, log2(avg), target, 1.0);
}

void main() {
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 prev = texelFetch(colortex5, p, 0);
    float age = texelFetch(colortex5, C_STATE, 0).r;
    // The two static tables are rebuilt for the first frames after (re)creation: the
    // multi-scatter table reads the previous frame's transmittance, so it needs two passes.
    bool rebuild = !(age >= 6.0 && age < 1e5);

    if (inRegion(p, LUT_T_ORIGIN, LUT_T_SIZE)) {
        if (!rebuild) { outLut = prev; return; }
        float r, mu;
        transmittanceInverse(regionCoord(p, LUT_T_ORIGIN, LUT_T_SIZE), r, mu);
        outLut = vec4(integrateTransmittance(r, mu), 1.0);
        return;
    }
    if (inRegion(p, LUT_MS_ORIGIN, LUT_MS_SIZE)) {
        if (!rebuild) { outLut = prev; return; }
        vec2 x = regionCoord(p, LUT_MS_ORIGIN, LUT_MS_SIZE);
        float r = ATM_RG + 0.01 + x.y * (ATM_RT - ATM_RG - 0.02);
        outLut = vec4(buildMultiScatter(r, x.x * 2.0 - 1.0), 1.0);
        return;
    }
    if (inRegion(p, LUT_SV_SUN, LUT_SV_SIZE)) {
        outLut = vec4(skyViewTexel(p, LUT_SV_SUN, sunDirWorld()), 1.0);
        return;
    }
    if (inRegion(p, LUT_SV_MOON, LUT_SV_SIZE)) {
        outLut = vec4(skyViewTexel(p, LUT_SV_MOON, moonDirWorld()), 1.0);
        return;
    }
    float r = cameraRadius();
    float clearSky = 1.0 - 0.85 * rainStrength;
    if (p == C_EXPOSURE) { outLut = computeExposure(prev.r); return; }
    if (p == C_SUN)  { outLut = vec4(SUN_I * lightTransmittance(r, sunDirWorld().y) * clearSky, 1.0); return; }
    if (p == C_MOON) { outLut = vec4(moonIntensity() * MOON_TINT * lightTransmittance(r, moonDirWorld().y) * clearSky, 1.0); return; }
    if (p == C_AMB_UP || p == C_AMB_SIDE) {
        vec3 up, side;
        ambientIrradiance(up, side);
        outLut = vec4(p == C_AMB_UP ? up : side, 1.0);
        return;
    }
    if (p == C_STATE) { outLut = vec4(rebuild ? (age >= 0.0 && age < 1e5 ? age + 1.0 : 0.0) : age, 0.0, 0.0, 1.0); return; }
    outLut = vec4(0.0);
}

#endif
