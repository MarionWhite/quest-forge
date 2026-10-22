// The water model (look bible 12, milestone 1 item 4): normal-only waves here; refraction,
// Beer-Lambert absorption, Fresnel and the underwater volume in composite.fsh.

// Absorption and in-scattering per metre (block). Pure water absorbs red first; a little
// green-blue scattering gives deep water its colour without hiding clear shallows.
// Round 5's red absorption (0.13) turned pale sand mint under a metre or two of water
// (the view path through it is longer than the depth); 0.075 keeps shallows clear.
#if QF_CAL_WATER == 1      // calibration A: clear tropical
const vec3 WATER_ABSORB = vec3(0.03, 0.012, 0.014);
const vec3 WATER_SCATTER = vec3(0.0008, 0.006, 0.006);
#elif QF_CAL_WATER == 2    // calibration B: deep and dark
const vec3 WATER_ABSORB = vec3(0.30, 0.16, 0.12);
const vec3 WATER_SCATTER = vec3(0.0006, 0.0018, 0.0028);
#elif QF_WATER_COLOR == 1  // r002 B: teal-green, a lake with a little plankton
const vec3 WATER_ABSORB = vec3(0.10, 0.040, 0.060);
const vec3 WATER_SCATTER = vec3(0.0015, 0.0075, 0.0055);
#elif QF_WATER_COLOR == 2  // r002 C: deep blue, open water
const vec3 WATER_ABSORB = vec3(0.12, 0.055, 0.030);
const vec3 WATER_SCATTER = vec3(0.0010, 0.0040, 0.0085);
#else
const vec3 WATER_ABSORB = vec3(0.075, 0.042, 0.038);
const vec3 WATER_SCATTER = vec3(0.0015, 0.005, 0.006);
#endif

// Surface style (Shader Lab r002; owner r001: the sunset water "doesn't look amazing").
// 0 is r001: five long swells only. 1 (calm) adds short wind ripples that fade out with
// distance (they would alias there), and composite.glsl adds screen-space reflections and a
// sun glitter path. 2 (lively) has taller swells and stronger ripples.
#if QF_WATER_STYLE == 2
const float WAVE_AMP = 1.7, RIPPLE_AMP = 1.6;
#elif QF_WATER_STYLE == 1
const float WAVE_AMP = 1.0, RIPPLE_AMP = 1.0;
#else
const float WAVE_AMP = 1.0, RIPPLE_AMP = 0.0;
#endif

// Height field: four long crossing swells plus short ripples. Returns the slope (dh/dx, dh/dz).
vec2 waterSlope(vec2 p, float t) {
    vec2 s = vec2(0.0);
    const int N = 5;
    vec2 dirs[N] = vec2[N](vec2(0.92, 0.39), vec2(-0.48, 0.88), vec2(0.21, -0.98), vec2(-0.81, -0.59), vec2(0.6, 0.8));
    float freq[N] = float[N](0.55, 0.83, 1.31, 2.17, 3.7);
    float amp[N]  = float[N](0.050, 0.034, 0.022, 0.012, 0.006);
    float spd[N]  = float[N](0.9, 1.1, 1.4, 1.9, 2.6);
    for (int i = 0; i < N; i++) {
        float x = dot(p, dirs[i]) * freq[i] + t * spd[i];
        s += dirs[i] * (cos(x) * amp[i] * freq[i]);
    }
    return s * WAVE_AMP;
}

// Wind ripples: short crossing wavelets (0.3-1.2 blocks), irregular directions so they do not
// read as a grid. fade 0 at a distance, where they would only alias.
vec2 rippleSlope(vec2 p, float t, float fade) {
    vec2 s = vec2(0.0);
    if (fade <= 0.0 || RIPPLE_AMP <= 0.0) return s;
    const int N = 6;
    vec2 dirs[N] = vec2[N](vec2(0.31, 0.95), vec2(-0.94, 0.33), vec2(0.70, -0.71), vec2(-0.20, -0.98), vec2(0.99, 0.12), vec2(-0.62, 0.78));
    float freq[N] = float[N](5.3, 6.9, 8.7, 11.3, 14.1, 17.9);
    float spd[N]  = float[N](2.9, 3.4, 3.9, 4.6, 5.2, 6.0);
    for (int i = 0; i < N; i++) {
        // Each wavelet's amplitude wanders over the surface, so the ripples come in patches.
        float patchy = 0.55 + 0.45 * sin(dot(p, dirs[(i + 2) % N]) * 0.37 + float(i) * 1.7 + t * 0.21);
        float x = dot(p, dirs[i]) * freq[i] + t * spd[i] + float(i) * 2.1;
        s += dirs[i] * (cos(x) * 0.0022 * freq[i] * patchy);
    }
    return s * RIPPLE_AMP * fade;
}

vec3 waterNormal(vec3 worldPos, vec3 faceNormal) {
    // Only the tops of water get waves; falls and sides keep the face normal.
    if (faceNormal.y < 0.5) return faceNormal;
    float t = animTime();
    float dist = length(worldPos - cameraPosition);
    vec2 s = waterSlope(worldPos.xz, t) * (1.0 + rainStrength * 0.6)
           + rippleSlope(worldPos.xz, t, 1.0 - smoothstep(12.0, 56.0, dist));
    return normalize(vec3(-s.x, 1.0, -s.y));
}
