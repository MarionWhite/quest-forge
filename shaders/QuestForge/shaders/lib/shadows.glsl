// Sun/moon shadows from shadowtex0: a distorted map (more texels near the player), hardware
// PCF from the separate shadowtex0HW sampler, plus QF_SHADOW_TAPS rotated taps on Medium and
// up (rule 5). Low takes the single hardware tap.

const float SHADOW_DISTORT = 0.86;   // 0 = no distortion
const float SHADOW_Z_SCALE = 0.4;    // depth range squeeze, shared with shadow.vsh

vec3 distortShadow(vec3 p) {
    float d = length(p.xy);
    p.xy /= d * SHADOW_DISTORT + (1.0 - SHADOW_DISTORT);
    p.z *= SHADOW_Z_SCALE;
    return p;
}

// How many shadow-map texels one world block spans at this clip position (for biases).
float shadowTexelWorld(vec2 clipXY) {
    float d = length(clipXY) * SHADOW_DISTORT + (1.0 - SHADOW_DISTORT);
    return (2.0 * shadowDistance / float(shadowMapResolution)) * d;
}

#if QF_SHADOWS
uniform sampler2DShadow shadowtex0HW;

// scenePos: player-relative world position; geoNormal: the face normal, for the offset.
// Returns 0..1 light visibility, fading to `fallback` towards the shadow distance.
float sampleShadow(vec3 scenePos, vec3 geoNormal, float NdotL, float fallback, vec2 noisePos) {
    vec3 sv = (shadowModelView * vec4(scenePos, 1.0)).xyz;
    vec3 clip = (shadowProjection * vec4(sv, 1.0)).xyz;
    float texel = shadowTexelWorld(clip.xy);
    // Normal offset scaled by the local texel size, more on grazing faces.
    vec3 offsetPos = scenePos + geoNormal * texel * (0.9 + 1.6 * (1.0 - NdotL));
    clip = (shadowProjection * (shadowModelView * vec4(offsetPos, 1.0))).xyz;
    vec3 sp = distortShadow(clip) * 0.5 + 0.5;
    float fade = smoothstep(0.82, 1.0, max(abs(clip.x), abs(clip.y)));
    fade = max(fade, smoothstep(shadowDistance * 0.85, shadowDistance, length(scenePos.xz)));
    if (fade >= 1.0) return fallback;
    float bias = 0.00012;
    float vis = texture(shadowtex0HW, vec3(sp.xy, sp.z - bias));
#if QF_SHADOW_TAPS > 0
    float ang = ign(noisePos + float(frameCounter % 64) * vec2(5.588, 3.124)) * 2.0 * PI;
    float radius = 1.3 / float(shadowMapResolution);
    float sum = vis;
    for (int i = 0; i < QF_SHADOW_TAPS; i++) {
        // Vogel disk: golden-angle spiral, rotated per pixel and per frame (TAA resolves it).
        float r = sqrt((float(i) + 0.5) / float(QF_SHADOW_TAPS));
        float a = float(i) * 2.39996323 + ang;
        vec2 o = vec2(cos(a), sin(a)) * r * radius * 2.5;
        sum += texture(shadowtex0HW, vec3(sp.xy + o, sp.z - bias));
    }
    vis = sum / float(QF_SHADOW_TAPS + 1);
#endif
    return mix(vis, fallback, fade);
}
#endif
