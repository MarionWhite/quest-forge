// The water model (look bible 12, milestone 1 item 4): normal-only waves here; refraction,
// Beer-Lambert absorption, Fresnel and the underwater volume in composite.fsh.

// Absorption and in-scattering per metre (block). Pure water absorbs red first; a little
// green-blue scattering gives deep water its colour without hiding clear shallows.
// Round 5's red absorption (0.13) turned pale sand mint under a metre or two of water
// (the view path through it is longer than the depth); 0.075 keeps shallows clear.
const vec3 WATER_ABSORB = vec3(0.075, 0.042, 0.038);
const vec3 WATER_SCATTER = vec3(0.0015, 0.005, 0.006);

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
    return s;
}

vec3 waterNormal(vec3 worldPos, vec3 faceNormal) {
    // Only the tops of water get waves; falls and sides keep the face normal.
    if (faceNormal.y < 0.5) return faceNormal;
    vec2 s = waterSlope(worldPos.xz, animTime()) * (1.0 + rainStrength * 0.6);
    return normalize(vec3(-s.x, 1.0, -s.y));
}
