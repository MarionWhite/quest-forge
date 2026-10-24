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

// Water by biome (owner r002: "different color gradients for different biomes"). The map is
// pregenerated, so the biome decides the water: lakes and rivers clear and glassy, oceans deep
// blue, coasts and coral reefs a Maldives turquoise over pale sand, swamps and marshes a murky
// teal. The weights are the camera's biome, faded over a few seconds (shaders.properties), so
// crossing a coast is a blend, not a cut. QF_WATER_FORCE pins one look for the Shader Lab.
#if QF_BIOME_WATER == 1 && QF_CAL_WATER == 0
uniform float qfWaterOcean;
uniform float qfWaterReef;
uniform float qfWaterSwamp;
uniform float qfWaterRiver;
// Absorption (what the water takes out per block) and scattering (what it sends back).
// Glassy: little scattering, so the bed shows through and deep water goes dark, not milky.
const vec3 WA_GLASSY = vec3(0.050, 0.024, 0.026), WS_GLASSY = vec3(0.0013, 0.0031, 0.0030);   // r003 critic: 0.0026 g read dark slate; round f read too cyan
// Ocean: red and green go within a few blocks; blue scattering is the colour.
const vec3 WA_OCEAN = vec3(0.16, 0.060, 0.030),   WS_OCEAN = vec3(0.0006, 0.0034, 0.0105);
// Reef and coast: red absorbed, green and blue scattered over the sand: turquoise shallows.
const vec3 WA_REEF = vec3(0.20, 0.022, 0.026),    WS_REEF = vec3(0.0010, 0.0125, 0.0125);
// Swamp: tannin and algae absorb blue as well as red, and the silt scatters: murky teal-olive,
// the bed gone within two or three blocks (r003 critic: the first try was the clearest water).
// r004 critic and owner: still too clear and grass-green. Silt has to scatter, not only absorb:
// with scattering a tenth of absorption the water only darkened the bed; now the in-scattered
// olive-brown hides it within a block or two of path.
const vec3 WA_SWAMP = vec3(1.10, 0.80, 1.25),     WS_SWAMP = vec3(0.045, 0.060, 0.020);   // round f mint jade; ih (0.15, 0.19, 0.065) pea soup
// River (r005; owner r004 agreed with the critic: the river was "a milky blob"): moving water
// carries fine sediment, so a slightly green-brown, half-clear stream instead of glassy lake water;
// the bed shows for two or three blocks.
const vec3 WA_RIVER = vec3(0.15, 0.080, 0.115),   WS_RIVER = vec3(0.0030, 0.0060, 0.0040);   // ih: twice this read milky mint
vec4 waterBiomeWeights() {   // ocean, reef, swamp, glassy
#if QF_WATER_FORCE == 1
    return vec4(0.0, 0.0, 0.0, 1.0);
#elif QF_WATER_FORCE == 2
    return vec4(1.0, 0.0, 0.0, 0.0);
#elif QF_WATER_FORCE == 3
    return vec4(0.0, 1.0, 0.0, 0.0);
#elif QF_WATER_FORCE == 4
    return vec4(0.0, 0.0, 1.0, 0.0);
#elif QF_WATER_FORCE == 5
    return vec4(0.0, 0.0, 0.0, 1.0);
#else
    vec3 w = clamp(vec3(qfWaterOcean, qfWaterReef, qfWaterSwamp), 0.0, 1.0);
    float sum = w.x + w.y + w.z;
    if (sum > 1.0) { w /= sum; sum = 1.0; }
    return vec4(w, 1.0 - sum);
#endif
}
// The share of the glassy weight that is river water (camera in a River biome).
float waterRiverShare() {
#if QF_WATER_FORCE == 5
    return 1.0;
#elif QF_WATER_FORCE > 0
    return 0.0;
#else
    return clamp(qfWaterRiver, 0.0, 1.0);
#endif
}
vec3 waterAbsorb() {
    vec4 w = waterBiomeWeights();
    float r = waterRiverShare();
    return WA_OCEAN * w.x + WA_REEF * w.y + WA_SWAMP * w.z + mix(WA_GLASSY, WA_RIVER, r) * w.w;
}
vec3 waterScatter() {
    vec4 w = waterBiomeWeights();
    float r = waterRiverShare();
    return WS_OCEAN * w.x + WS_REEF * w.y + WS_SWAMP * w.z + mix(WS_GLASSY, WS_RIVER, r) * w.w;
}
// Glassy water is calmer: fewer wind ripples, so it mirrors more cleanly.
float waterBiomeRipple() {
    vec4 w = waterBiomeWeights();
    return w.x * 1.15 + w.y * 1.0 + w.z * 0.55 + w.w * 0.75;
}
#else
vec3 waterAbsorb() { return WATER_ABSORB; }
vec3 waterScatter() { return WATER_SCATTER; }
float waterBiomeRipple() { return 1.0; }
#endif

// Surface style (Shader Lab r002; owner r001: the sunset water "doesn't look amazing").
// 0 is r001: five long swells only. 1 (calm) adds short wind ripples that fade out with
// distance (they would alias there), and composite.glsl adds screen-space reflections and a
// sun glitter path. 2 (lively) has taller swells and stronger ripples.
// 3 (owner r002: lively at sunset, calm at noon) is calm by day and eases to lively as the sun
// gets low, where the extra ripples feed the glitter path; at noon lively's ripples aliased into
// parallel streaks in the distance.
// 4 (owner r004: A, the calm mirror, toward Complementary's realistic water and Photon's strict
// realism): low swells and faint ripples, so the water mirrors the land and sky cleanly and the sun
// makes one soft path; a little more life at low sun so the path still breaks up near the sun.
#if QF_WATER_STYLE == 4
#define WAVE_AMP (0.50 + 0.25 * goldenHour())
#define RIPPLE_AMP ((0.45 + 0.25 * goldenHour()) * waterBiomeRipple())
#elif QF_WATER_STYLE == 3
#define WAVE_AMP (1.0 + 0.7 * goldenHour())
#define RIPPLE_AMP ((1.0 + 0.6 * goldenHour()) * waterBiomeRipple())
#elif QF_WATER_STYLE == 2
const float WAVE_AMP = 1.7, RIPPLE_AMP = 1.6;
#elif QF_WATER_STYLE == 1
const float WAVE_AMP = 1.0, RIPPLE_AMP = 1.0;
#else
const float WAVE_AMP = 1.0, RIPPLE_AMP = 0.0;
#endif

// Micro-ripples for the glitter (QF_GLITTER 1-2): two short capillary wavelets, 5-10 cm, that
// tilt each patch of the surface a little differently. The glint is then a tight highlight on
// this normal, so the sparkles sit on the surface's own texture and move with it (owner r002:
// "glittery interaction with the water's surface texture") instead of a hash grid. Faded out
// with distance, where the broad lobe stands in for them (they would only alias there).
vec2 microSlope(vec2 p, float t, float fade) {
    if (fade <= 0.0) return vec2(0.0);
    // Gradients of two drifting value-noise fields (5 and 11 cm cells), irregular by design:
    // r003 smoke's plane waves interfered into a regular lattice of dots.
    const float e = 0.3;
    vec2 q1 = mat2(0.8, 0.6, -0.6, 0.8) * p * 9.0 + vec2(t * 1.1, t * 0.5);
    vec2 q2 = mat2(0.6, -0.8, 0.8, 0.6) * p * 19.0 - vec2(t * 0.7, -t * 1.3);
    vec2 g1 = vec2(valueNoise(q1 + vec2(e, 0.0)) - valueNoise(q1 - vec2(e, 0.0)),
                   valueNoise(q1 + vec2(0.0, e)) - valueNoise(q1 - vec2(0.0, e))) / (2.0 * e);
    vec2 g2 = vec2(valueNoise(q2 + vec2(e, 0.0)) - valueNoise(q2 - vec2(e, 0.0)),
                   valueNoise(q2 + vec2(0.0, e)) - valueNoise(q2 - vec2(0.0, e))) / (2.0 * e);
    return (g1 * 0.030 + g2 * 0.018) * fade;
}

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
