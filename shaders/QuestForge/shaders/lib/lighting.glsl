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
    float smoothness; // LabPBR perceptual smoothness (QF_PBR; 0 without a map)
    float f0;         // LabPBR F0 byte / 255; from 0.9 up a metal (QF_PBR; 0 without a map)
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
#elif QF_TORCH_WARM == 4
const vec3 TORCH_CORE = vec3(1.0, 0.45, 0.14), TORCH_EDGE = vec3(1.0, 0.30, 0.050);  // ~2750 K to 2100 K (owner r002: "a little warmer"; r003 critic: 2850 K was invisible)
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
// r009 (tex-golden: golden_lit's sun-shadowed field showed warm lit patches with stair-stepped edges,
// the per-block falloff of light sources in the grass, and the motes over them glowed as orange
// "coins"; QF_DEBUG_VIEW 3 bisect): out in daylight block light reads far weaker against the sky, as
// in vanilla. Up to 70% less under open sky by day; caves and nights unchanged.
float blockDayDamp(float skyLight) {
    return 1.0 - 0.7 * smoothstep(-0.05, 0.10, sunDirWorld().y) * skyLight * skyLight;
}

// Torchlight that breathes (owner r002: inexpensive ambient effects; r000: fire light that
// moves naturally, not a looped flicker). Two incommensurate slow drifts plus a faint quick
// one, varying over a few blocks so neighbouring torches do not pulse together. +-5% at most,
// strongest next to the flame, where the light is the flame's own.
float torchFlicker(vec3 worldPos, float b) {
#if QF_FLICKER == 1 && QF_STILL == 0
    float t = animTime();
    vec2 q = worldPos.xz * 0.22 + worldPos.y * 0.13;
    float n = valueNoise(q + vec2(t * 1.7, t * 1.1)) * 0.6 + valueNoise(q * 1.9 + vec2(-t * 4.3, t * 3.1)) * 0.4;
    return 1.0 + (n - 0.5) * 0.10 * smoothstep(0.4, 0.95, b);
#else
    return 1.0;
#endif
}

float ggx(float NdotH, float a2) {
    float d = NdotH * NdotH * (a2 - 1.0) + 1.0;
    return a2 / (PI * d * d);
}

vec3 fresnelSchlick(float c, vec3 f0) {
    // r008: clamped. A dot product a hair over 1 made pow() of a negative base, a NaN that TAA
    // then smeared into the soft black blob on the dirt bank in r007's PBR frame.
    return f0 + (1.0 - f0) * pow(clamp(1.0 - c, 0.0, 1.0), 5.0);
}

// r008 metals (owner r007, PBR: with maps on "the metallic blocks just look like they are in the
// shade"): a metal has no diffuse light at all; everything it shows is reflection, tinted by its
// own colour. What it reflects here: the sky dome along the reflected ray (blurred toward the sky's
// irradiance as it gets rough), the lit ground below the horizon, and the sun as a sharp GGX
// highlight. So gold and iron read as polished metal, bright where they face the sky or the sun.
// Loop 4: with screen-space reflections (Medium and up) the metal's environment comes from the
// composite pass (metalReflection), which sees the real scene; this pass draws only the sun.
#if QF_SSR_STEPS > 0 && QF_WATER_STYLE > 0 && QF_PBR == 1
#define QF_METAL_SSR 1
#else
#define QF_METAL_SSR 0
#endif
vec3 metalShade(vec3 albedo, vec3 n, vec3 viewDir, vec3 L, vec3 E, float smooth_, float shadow, float sky, float ao, vec3 diffuse, vec3 scenePos) {
    float r = (1.0 - smooth_) * (1.0 - smooth_);
    float a2 = max(r * r, 0.0012);
    vec3 V = -viewDir;
    vec3 f0 = clamp(albedo * 1.15, 0.0, 1.0);
    float NdotV = clamp(dot(n, V), 0.02, 1.0);
    vec3 Rf = reflect(viewDir, n);
    // Loop 3 (critic ud_pbr: the metals are bright but read as paint, no sky or landscape in them).
    // A flat face mirrors one direction, so the reflection was one flat colour per face. Polished
    // blocks are never optically flat: each face is bent a little like a shallow lens, so across a
    // block the reflection sweeps from sky (top) through a crisp horizon line to the ground (bottom)
    // and leans sideways, which is what reads as chrome at a glance.
#if QF_METAL_SSR == 0
    {
        vec3 wp = scenePos + cameraPosition;
        vec3 an = abs(n);
        vec2 fc = an.y > 0.5 ? fract(wp.xz) : (an.x > 0.5 ? vec2(fract(wp.z), fract(wp.y)) : vec2(fract(wp.x), fract(wp.y)));
        fc -= 0.5;
        vec3 tU = an.y > 0.5 ? vec3(0.0, 0.0, 1.0) : vec3(0.0, 1.0, 0.0);
        vec3 tS = normalize(cross(tU, n));
        Rf = normalize(Rf + (tU * fc.y * 1.1 + tS * fc.x * 0.6) * smooth_);
    }
#endif
    vec3 Fe = fresnelSchlick(NdotV, f0);
    // Environment: sky above the horizon, ground (lit grass-and-earth tone) below, blended over a
    // few degrees, and toward the sky's irradiance on rough metal.
    vec3 skyR = skyScatter(normalize(vec3(Rf.x, max(Rf.y, 0.02), Rf.z)));
    vec3 skyD = skyIrradiance(n) / PI;
    vec3 env = mix(skyR, skyD, r);
    vec3 ground = (E * max(L.y, 0.0) * shadow * 0.6 + skyIrradiance(vec3(0.0, 1.0, 0.0))) * vec3(0.16, 0.15, 0.11) / PI;
    env = mix(ground * 0.7, env * 1.15, smoothstep(-0.02, 0.02, Rf.y));   // loop 3: a crisp horizon line (was -0.08..0.06)
#if QF_METAL_SSR == 1
    vec3 col = vec3(0.0);   // the reflection is added in composite
#else
    vec3 col = env * Fe * mix(0.25, 1.0, sky) * ao;
#endif
    // The sun: GGX with Smith-ish visibility, energy capped so a mirror does not blow out to a
    // pixel of infinity.
    vec3 H = normalize(L + V);
    float NdotL = clamp(dot(n, L), 0.0, 1.0);
    float sp = ggx(clamp(dot(n, H), 0.0, 1.0), a2) * NdotL / (4.0 * NdotV + 0.4);
    vec3 FH = fresnelSchlick(clamp(dot(H, V), 0.0, 1.0), f0);
    col += FH * E * min(sp, 80.0) * shadow;
    // Loop 2 (critic: ub's iron and gold read dimmer than PBR off, "in the shade", with no sky
    // reflection or sun sheen). A block face mirrors mostly the horizon sky, which is far dimmer
    // than the sun on a diffuse face, so a pure mirror reads as a darkened block. Polished metal
    // in a game reads by its highlights: a brighter, contrastier sky reflection (a horizon band
    // in the reflection, bright above and dark ground below), a broad sun sheen across the face,
    // and the block's diffuse look kept underneath so it is never darker than with PBR off.
    float hb = exp(-abs(Rf.y) / 0.12);                                  // the bright horizon band in the reflection
    col *= 1.4 + 0.9 * hb * smoothstep(-0.05, 0.02, Rf.y);   // ud: 1.6 + 1.2 pushed diamond and gold edges toward neon
    float sh2 = ggx(clamp(dot(n, H), 0.0, 1.0), 0.08) * NdotL / (4.0 * NdotV + 0.4);
    col += FH * E * min(sh2, 6.0) * shadow * 0.55;
#if QF_METAL_SSR == 1
    // r010 (texture track, diag_column: gold 158,134,1 under the shader vs 178,152,34 vanilla, iron
    // 143 vs 154, plain stone level): a block face mirrors mostly the dim horizon and ground, so 0.30
    // of the diffuse under the reflection left gold and iron ~17 % darker than plain blocks.
#if QF_METAL_FLOOR == 1
    col += diffuse * 0.62;
#else
    col += diffuse * 0.30;
#endif
#else
    col = max(col + diffuse * 0.32, diffuse * 0.95);
#endif   // loop 3: 0.55 of the diffuse on top buried the reflection (read as paint)
    return col;
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
#if QF_CLOUDS > 0
    shadow *= cloudShadow(s.scenePos + cameraPosition, L);
#endif
    // Foliage: wrapped diffuse plus light through the leaf from behind (look bible 10).
    float diffuse;
    float through = 0.0;
    if (foliage) {
        diffuse = clamp(NdotL * 0.6 + 0.4, 0.0, 1.0) * 0.85;
        float back = pow(clamp(dot(viewDir, L), 0.0, 1.0), 4.0) * 0.6;
#if QF_AMBER > 0
        // Light through the canopy (owner r002: amber on the leaves). A shadow-map texel says
        // "another leaf is in the way", but leaves pass a good part of the light on, so the
        // backlit glow survives part of the shadow: the canopy glows when you face the low sun.
        through = back * (1.0 - shadow) * 0.45 * outside;
#endif
        diffuse += back;
    } else {
        diffuse = clamp(NdotL, 0.0, 1.0) * step(-0.01, geoNdotL);
#if QF_CAL_GOLD > 0
        // r009 (critic p8 golden_lit: the near field is flat green with no warm low-sun light on
        // the grass tops): a flat top gets NdotL ~0.15 from a low sun, but blades and ground relief
        // stand up into it. Up-facing faces take at least 0.7 at golden hour (loop 1, 0.32: +2 on the
        // lit tops, unseen); the shadow map still decides which patches are lit, so only those turn gold.
        diffuse = max(diffuse, 0.7 * goldenHour() * smoothstep(0.7, 0.95, s.geoNormal.y) * step(0.0, L.y));
#endif
    }
    float sky = s.skyLight * s.skyLight * s.skyLight;
    float ao = mix(1.0, s.ao, QF_AO_STRENGTH);
    vec3 skyE = skyIrradiance(s.normal);
#if QF_CAL_GOLD > 0
    // Amber light on whatever the low sun reaches: a stronger, warmer direct term and a
    // little less blue fill, so lit faces read gold against cool shade (Shader Lab r001).
    // QF_AMBER 1-2 (owner r002: "definitely try some amber effects on the leaves and other
    // things"): deeper amber, and the light through leaves warmer still (a leaf filters it).
    float gh = goldenHour();
#if QF_AMBER == 2
    const vec3 AMBER = vec3(1.75, 1.18, 0.62), LEAF_AMBER = vec3(1.45, 1.05, 0.38);
#elif QF_AMBER == 1
    const vec3 AMBER = vec3(1.60, 1.15, 0.70), LEAF_AMBER = vec3(1.30, 1.0, 0.45);
#else
    const vec3 AMBER = vec3(1.45, 1.12, 0.80), LEAF_AMBER = vec3(1.0);
#endif
    E *= mix(vec3(1.0), AMBER, gh);
    skyE *= mix(1.0, 0.80, gh);
    vec3 Eleaf = E * mix(vec3(1.0), LEAF_AMBER, gh);
#else
    vec3 Eleaf = E;
#endif
    vec3 irradiance = (foliage ? Eleaf : E) * diffuse * shadow
                    + Eleaf * through
                    + skyE * sky * ao
                    + blockIrradiance(s.blockLight) * torchFlicker(s.scenePos + cameraPosition, s.blockLight) * ao * blockDayDamp(s.skyLight)
                    + nightFloor() * NIGHT_FLOOR_TINT * ao;
    // Held light (look bible 1): a soft warm pool around the player.
    if (heldBlockLightValue > 0) {
        float d = length(s.scenePos);
        float hb = clamp(float(heldBlockLightValue) / 15.0 - d / 15.0, 0.0, 1.0);
        irradiance += blockIrradiance(hb) * 0.8;
    }
    irradiance += vec3(nightVision * 0.25);
#if QF_BOUNCE == 1
    // Bounce light (r007; owner r006: "I like the light to interact with the blocks realistically"):
    // sunlit ground throws warm light back up onto walls, the undersides of overhangs and canopy, so
    // shade near lit ground is warmer and lifted, not only sky blue. The ground's irradiance is the
    // light times its elevation, its colour a warm earth albedo; outdoors only.
    {
        float up = clamp(0.5 - 0.5 * s.normal.y, 0.0, 1.0);
        vec3 Eg = E * max(L.y, 0.0) * vec3(0.30, 0.25, 0.18);
        irradiance += Eg * up * outside * s.skyLight * s.skyLight * ao * 0.55;
    }
#endif
    vec3 color = s.albedo / PI * irradiance;
    bool hasPbr = s.smoothness > 0.02 || s.f0 > 0.02;
#if QF_PBR == 1
    if (hasPbr) {
        // LabPBR maps (r007, QF_PBR): the pack's own smoothness and F0 drive a GGX highlight from
        // the sun or moon and a sky reflection on smooth blocks; metals take their colour into the
        // reflection and lose most of their diffuse light.
        bool metal = s.f0 > 0.895;
        if (metal) {
            color = metalShade(s.albedo, s.normal, viewDir, L, E, max(s.smoothness, 0.35), shadow, sky, ao, color, s.scenePos);
            return color;
        }
        float r = (1.0 - s.smoothness) * (1.0 - s.smoothness);
        float a2 = max(r * r, 0.0015);
        // Loop 4: a smooth leaf map can give a leaf's flat top face a mirror-tight sun highlight (first
        // suspect for forest_golden's yellow oval, which turned out to be a near dust mote). Leaves
        // are waxy, never mirrors.
        if (foliage) a2 = max(a2, 0.08);
        vec3 f0v = metal ? s.albedo : vec3(s.f0);
        vec3 V = -viewDir;
        vec3 H = normalize(L + V);
        float NdotV = max(dot(s.normal, V), 0.02);
        vec3 F = fresnelSchlick(max(dot(H, V), 0.0), f0v);
        float sp = ggx(max(dot(s.normal, H), 0.0), a2) * clamp(NdotL, 0.0, 1.0) / (4.0 * NdotV + 0.5);
        if (metal) color *= 0.15;
        color += F * E * min(sp, foliage ? 3.0 : 60.0) * shadow;
        vec3 R = reflect(viewDir, s.normal);
        vec3 Fe = fresnelSchlick(NdotV, f0v);
        color += skyScatter(R) * Fe * sky * s.smoothness * s.smoothness * ao;
    }
#endif
#if QF_BOUNCE == 1
    // A faint sheen on every block at grazing light (dielectric, F0 4%, rough), and a waxy one on
    // leaves: stone, wood and leaves catch the low sun instead of reading as flat paint.
    if ((s.mat == MAT_NONE || foliage) && !hasPbr) {
        vec3 V = -viewDir;
        vec3 H = normalize(L + V);
        float NdotV = max(dot(s.normal, V), 0.02);
        float a2 = foliage ? 0.05 : 0.09;
        float Fs = fresnelSchlick(max(dot(H, V), 0.0), vec3(foliage ? 0.03 : 0.04)).x;
        float sp = ggx(max(dot(s.normal, H), 0.0), a2) * clamp(NdotL, 0.0, 1.0) / (4.0 * NdotV + 0.5);
        color += (foliage ? Eleaf * 0.6 : E) * sp * Fs * shadow;
    }
#endif

    // Emissive blocks: their own light, not just lit by the lightmap.
    if (s.mat == MAT_EMISSIVE || s.mat == MAT_LAVA) {
        float glow = smoothstep(0.35, 0.9, luminance(s.albedo));
        color += s.albedo * BLOCK_I * (0.15 + 0.85 * glow) * 0.6;
    }

    // Specular from the light on metal and polished stone (no reflections beyond that yet).
#if QF_PBR == 1
    // Metal blocks without a map in the pack: the same model, polished.
    if (s.mat == MAT_METAL && !hasPbr) return metalShade(s.albedo, s.normal, viewDir, L, E, 0.72, shadow, sky, ao, color, s.scenePos);
#endif
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
#if QF_METAL_FLOOR == 1
        if (s.mat == MAT_METAL) color *= 0.92;   // r010: 0.65 put gold at 150 (vanilla 178) next to level stone
#else
        if (s.mat == MAT_METAL) color *= 0.65;   // metal: less diffuse, energy goes to F
#endif
    }
    return color;
}
