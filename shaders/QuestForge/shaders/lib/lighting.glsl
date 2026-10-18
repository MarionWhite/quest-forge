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

// Vanilla light levels are linear in blocks; this gives a torch a short warm pool with a
// long tail, so light level 7 still reads as lit (gameplay) without a flat orange wash.
vec3 blockIrradiance(float b) {
    float e = pow(b, 2.6) * 0.9 + pow(b, 8.0) * 0.6;
    return BLOCK_LIGHT_COLOR * BLOCK_I * e;
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
    shadow = smoothstep(0.80, 0.97, s.skyLight);   // Potato: outdoors means lit
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
    vec3 irradiance = E * diffuse * shadow
                    + skyIrradiance(s.normal) * sky * ao
                    + blockIrradiance(s.blockLight) * ao
                    + NIGHT_FLOOR_I * QF_NIGHT_FLOOR * NIGHT_FLOOR_TINT * ao;
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
