// Wind for leaves and plants, by material ID: the one place the generated block.properties
// is visible in motion (milestone 1, item 7). Used by gbuffers_terrain and shadow, so a
// leaf's shadow sways with the leaf.

// worldPos: absolute world position of the vertex. top: the vertex is on the upper edge of
// its texture (plants bend from the base). skyLight: no wind underground.
vec3 windOffset(vec3 worldPos, int mat, bool top, float skyLight) {
#if QF_WAVING
    if (mat != MAT_LEAVES && mat != MAT_PLANT) return vec3(0.0);
    float t = animTime();
    vec3 p = mod(worldPos, 1024.0);
    float phase = dot(p, vec3(0.73, 1.31, 1.07));
    float gust = 0.65 + 0.35 * sin(t * 0.37 + p.x * 0.021 + p.z * 0.017);
    float strength = (gust + rainStrength * 0.8) * smoothstep(0.2, 0.7, skyLight);
    if (mat == MAT_LEAVES) {
        vec3 o = vec3(sin(t * 1.63 + phase),
                      sin(t * 2.21 + phase * 1.37) * 0.5,
                      sin(t * 1.91 + phase * 0.83 + 1.3));
        return o * 0.045 * strength;
    }
    if (!top) return vec3(0.0);
    vec2 sway = vec2(sin(t * 1.9 + phase), sin(t * 1.5 + phase * 1.21 + 0.7));
    return vec3(sway.x, 0.0, sway.y) * 0.09 * strength;
#else
    return vec3(0.0);
#endif
}
