// Surface lighting, shared by deferred.fsh (opaque G-buffer) and the forward programs
// (glass, particles, weather, the hand). Needs common, materials, atmosphere, lut, sky, shadows.
//
// Radiance = albedo/pi * (sun or moon * N.L * shadow  +  sky irradiance * skylight^3 * AO
//                         + block light + night floor)  + emission + specular.

struct Surface {
    vec3 albedo;      // linear
    vec3 normal;      // world space
    vec3 geoNormal;   // world space, the face (for the shadow offset)
    int mat;
    float blockLight; // 0..1 lightmap
    float skyLight;   // 0..1 lightmap
    float ao;
    vec3 scenePos;    // player-relative world position
};

// Vanilla light levels are linear in blocks. Vanilla's lightmap curve, taken to linear
// light, falls to about 15% of the level-14 value at level 10 and 4% at level 7; round 5's
// pow(b, 2.6) kept 31% and 12%, so a tunnel read evenly lit (0.28 mean luma against
// vanilla's 0.17). This follows vanilla's falloff, with a hotter pool next to the source.
// Level 7 still reads as lit once exposure has adapted (gameplay).
//
// Colour (owner r001: "not warm at all ... a fluorescent light bulb"): a flame's light is
// whitest at the source and redder where it is dim, so the colour runs from a hot core (b near
// 1) to a warmer edge. Each colour is scaled to r001's luminance, so brightness stays
// vanilla-like and only the hue changes (QF_TORCH_WARM, Shader Lab r002).
#if QF_TORCH_WARM == 0
const vec3 TORCH_CORE = vec3(1.0, 0.70, 0.45), TORCH_EDGE = vec3(1.0, 0.70, 0.45);
#elif QF_TORCH_WARM == 1
const vec3 TORCH_CORE = vec3(1.0, 0.58, 0.28), TORCH_EDGE = vec3(1.0, 0.47, 0.17);   // ~3300 K to 2900 K
#elif QF_TORCH_WARM == 2
const vec3 TORCH_CORE = vec3(1.0, 0.52, 0.20), TORCH_EDGE = vec3(1.0, 0.37, 0.09);   // ~3000 K to 2400 K
#else
const vec3 TORCH_CORE = vec3(1.0, 0.44, 0.13), TORCH_EDGE = vec3(1.0, 0.29, 0.04);   // ~2700 K to 2000 K
#endif
vec3 blockLightColor(float b) {
    vec3 c = mix(TORCH_EDGE, TORCH_CORE, smoothstep(0.45, 0.95, b));
    return c * (luminance(BLOCK_LIGHT_COLOR) / luminance(c));
}

vec3 blockIrradiance(float b) {
    float e = pow(b, 4.2) * 0.75 + pow(b, 9.0) * 0.45;
    return blockLightColor(b) * BLOCK_I * e;
}

float ggx(float NdotH, float a2) {
    float d = NdotH * NdotH * (a2 - 1.0) + 1.0;
    return a2 / (PI * d * d);
}

vec3 fresnelSchlick(float c, vec3 f0) {
    return f0 + (1.0 - f0) * pow(1.0 - c, 5.0);
}

// The active light: the sun by day, the moon by night (whichever casts shadowLightPosition).
vec3 lightDirWorld() {
    return normalize(mat3(gbufferModelViewInverse) * shadowLightPosition);
}

vec3 lightIrradiance() {
    return sunDirWorld().y > -0.02 ? sunIrradiance() : moonIrradiance();
}

vec3 shadeSurface(Surface s, vec3 viewDir, vec2 pixel) {
    vec3 L = lightDirWorld();
    vec3 E = lightIrradiance();
    float NdotL = dot(s.normal, L);
    float geoNdotL = dot(s.geoNormal, L);
    bool foliage = isFoliage(s.mat);
    // Underground the shadow map may not cover a cave mouth; sky light says "outside".
    float outside = smoothstep(0.05, 0.45, s.skyLight);
    float shadow;
#if QF_SHADOWS
    shadow = sampleShadow(s.scenePos, s.geoNormal, clamp(abs(geoNdotL), 0.0, 1.0),
                          smoothstep(0.75, 0.95, s.skyLight), pixel);
    shadow *= outside;
#if QF_DEBUG_VIEW == 5
    return vec3(shadow);   // raw sun visibility; final shows it untouched
#elif QF_DEBUG_VIEW == 7
    return qfShadowDebug;  // r: map depth, g: surface depth, b: difference (0.5 = equal)
#endif
#else
    // Potato: outdoors means lit. 0.80 left anything under a few blocks of water unlit (water
    // cuts sky light by 3 a block), so Potato's lake beds and underwater view were murky (r14).
    // With the eye under water everything in view is under water, so go lower still (a3p: the
    // lake bed 4 blocks down stayed unlit at 0.55).
    shadow = smoothstep(isEyeInWater == 1 ? 0.25 : 0.55, 0.92, s.skyLight);
#endif
    // Foliage: wrapped diffuse plus light through the leaf from behind (look bible 10).
    float diffuse;
    if (foliage) {
        diffuse = clamp(NdotL * 0.6 + 0.4, 0.0, 1.0) * 0.85;
        float back = pow(clamp(dot(viewDir, L), 0.0, 1.0), 4.0) * 0.6;
        diffuse += back;
    } else {
        diffuse = clamp(NdotL, 0.0, 1.0) * step(-0.01, geoNdotL);
    }
    float sky = s.skyLight * s.skyLight * s.skyLight;
    float ao = mix(1.0, s.ao, QF_AO_STRENGTH);
    vec3 skyE = skyIrradiance(s.normal);
#if QF_CAL_GOLD > 0
    // Amber light on whatever the low sun reaches: a stronger, warmer direct term and a
    // little less blue fill, so lit faces read gold against cool shade (Shader Lab r001).
    float gh = goldenHour();
    E *= mix(vec3(1.0), vec3(1.45, 1.12, 0.80), gh);
    skyE *= mix(1.0, 0.80, gh);
#endif
    vec3 irradiance = E * diffuse * shadow
                    + skyE * sky * ao
                    + blockIrradiance(s.blockLight) * ao
                    + nightFloor() * NIGHT_FLOOR_TINT * ao;
    // Held light (look bible 1): a soft warm pool around the player.
    if (heldBlockLightValue > 0) {
        float d = length(s.scenePos);
        float hb = clamp(float(heldBlockLightValue) / 15.0 - d / 15.0, 0.0, 1.0);
        irradiance += blockIrradiance(hb) * 0.8;
    }
    irradiance += vec3(nightVision * 0.25);
    vec3 color = s.albedo / PI * irradiance;

    // Emissive blocks: their own light, not just lit by the lightmap.
    if (s.mat == MAT_EMISSIVE || s.mat == MAT_LAVA) {
        float glow = smoothstep(0.35, 0.9, luminance(s.albedo));
        color += s.albedo * BLOCK_I * (0.15 + 0.85 * glow) * 0.6;
    }

    // Specular from the light on metal and polished stone (no reflections beyond that yet).
    if (s.mat == MAT_METAL || s.mat == MAT_POLISHED || s.mat == MAT_ORE) {
        float rough = s.mat == MAT_METAL ? 0.38 : (s.mat == MAT_ORE ? 0.3 : 0.28);
        vec3 f0 = s.mat == MAT_METAL ? s.albedo : vec3(0.04);
        vec3 V = -viewDir;
        vec3 H = normalize(L + V);
        float a2 = pow(rough, 4.0);
        float NdotV = max(dot(s.normal, V), 0.01);
        vec3 F = fresnelSchlick(max(dot(H, V), 0.0), f0);
        float spec = ggx(max(dot(s.normal, H), 0.0), a2) * clamp(NdotL, 0.0, 1.0) / (4.0 * NdotV + 0.5);
        float oreMask = s.mat == MAT_ORE ? smoothstep(0.25, 0.6, abs(s.albedo.r - s.albedo.g) + abs(s.albedo.g - s.albedo.b)) : 1.0;
        color += F * E * spec * shadow * oreMask;
        if (s.mat == MAT_METAL) color *= 0.65;   // metal: less diffuse, energy goes to F
    }
    return color;
}
