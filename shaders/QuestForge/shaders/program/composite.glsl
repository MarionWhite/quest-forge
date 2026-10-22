// composite: the water model (look bible 12), the underwater volume, and distance haze
// (look bible 6), on the HDR scene. One full-screen pass.

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/buffers.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sky.glsl"
#include "/lib/shadows.glsl"
#include "/lib/lighting.glsl"
#include "/lib/water.glsl"

#ifdef VSH
out vec2 uv;
void main() {
    gl_Position = ftransform();
    uv = gl_MultiTexCoord0.xy;
}
#endif

#ifdef FSH
in vec2 uv;

uniform sampler2D colortex1;
uniform sampler2D colortex2;
uniform sampler2D colortex3;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
#if QF_BIOME_FOG == 1
uniform float qfFogCrisp;   // shaders.properties: smoothed biome and weather weights
uniform float qfFogMoody;
uniform float qfFogStorm;
#endif

/* RENDERTARGETS: 3 */
layout(location = 0) out vec4 outColor;

vec3 scenePosAt(vec2 p, float d) {
    return sceneFromView(viewFromScreen(p, d));
}

// Light that water scatters towards the eye: sky and sun/moon reaching into the water.
vec3 waterAmbient(float skyLight) {
    float sky = skyLight * skyLight;
    return (skyIrradiance(vec3(0.0, 1.0, 0.0)) + lightIrradiance() * max(lightDirWorld().y, 0.0)) * sky / PI
         + nightFloor() * NIGHT_FLOOR_TINT / PI;
}

#if QF_SSR_STEPS > 0 && QF_WATER_STYLE > 0
// Screen-space reflection for water (Medium and up): march the reflected ray in view space
// against the opaque depth, refine the hit by bisection, and fade out towards the screen
// edges, for rays that turn back towards the camera and for long rays. The sky table is the
// fallback, so a miss is never black. Returns rgb and the hit weight.
vec4 waterSSR(vec3 viewPos, vec3 viewRefl, float jitter) {
    float stepLen = 0.6 + 0.02 * length(viewPos);
    vec3 p = viewPos + viewRefl * stepLen * jitter;
    vec3 prev = viewPos;
    for (int i = 0; i < QF_SSR_STEPS; i++) {
        vec4 clip = gbufferProjection * vec4(p, 1.0);
        if (clip.w <= 0.0) break;
        vec2 suv = clip.xy / clip.w * 0.5 + 0.5;
        if (any(lessThan(suv, vec2(0.0))) || any(greaterThan(suv, vec2(1.0)))) break;
        float sd = texture(depthtex1, suv).r;
        float sceneZ = -viewFromScreen(suv, sd).z;   // exact for any projection far plane
        float rayZ = -p.z;
        if (sd < 1.0 && rayZ > sceneZ && rayZ - sceneZ < stepLen * 2.0 + 0.5) {
            // Bisection between the last miss and this hit.
            vec3 a = prev, b = p;
            for (int k = 0; k < 4; k++) {
                vec3 m = 0.5 * (a + b);
                vec4 mc = gbufferProjection * vec4(m, 1.0);
                vec2 mu = mc.xy / mc.w * 0.5 + 0.5;
                if (-m.z > -viewFromScreen(mu, texture(depthtex1, mu).r).z) b = m; else a = m;
            }
            vec4 bc = gbufferProjection * vec4(b, 1.0);
            vec2 huv = bc.xy / bc.w * 0.5 + 0.5;
            vec2 edge = smoothstep(vec2(0.0), vec2(0.08), huv) * smoothstep(vec2(1.0), vec2(0.92), huv);
            float w = edge.x * edge.y * (1.0 - float(i) / float(QF_SSR_STEPS)) * smoothstep(0.0, 0.25, -viewRefl.z + 0.3);
            return vec4(texture(colortex3, huv).rgb, clamp(w, 0.0, 1.0));
        }
        prev = p;
        p += viewRefl * stepLen;
        stepLen *= 1.25;
    }
    return vec4(0.0);
}
#endif

vec3 waterVolume(vec3 color, float dist, float skyLight) {
    vec3 T = exp(-WATER_ABSORB * dist);
    vec3 scatterAlbedo = WATER_SCATTER / (WATER_ABSORB + WATER_SCATTER);
    return color * T + waterAmbient(skyLight) * scatterAlbedo * (1.0 - T);
}

void main() {
    ivec2 px = ivec2(gl_FragCoord.xy);
    float depth0 = texelFetch(depthtex0, px, 0).r;
    float depth1 = texelFetch(depthtex1, px, 0).r;
    vec3 color = texelFetch(colortex3, px, 0).rgb;
    vec3 scene0 = scenePosAt(uv, depth0);
    float dist0 = depth0 >= 1.0 ? far * 2.0 : length(scene0);
    vec3 viewDir = normalize(scene0);
    vec4 g1 = texelFetch(colortex1, px, 0);
    float skyLight = texelFetch(colortex2, px, 0).g;
    float eyeSky = float(eyeBrightnessSmooth.y) / 240.0;
    bool water = unpackMaterial(g1) == MAT_WATER && depth0 < depth1 && depth0 < 1.0;

    if (water) {
        vec3 n = decodeNormal(g1.rg);
        float NdotV = clamp(dot(n, -viewDir), 0.0, 1.0);
        if (isEyeInWater == 0) {
            // Refraction: shift the lookup along the wave slope, more for deeper water, and
            // fall back to the straight lookup if the shifted pixel is in front of the surface.
            vec3 scene1 = scenePosAt(uv, depth1);
            float thick = depth1 >= 1.0 ? 8.0 : distance(scene0, scene1);
            vec2 uvR = uv + n.xz * 0.035 * clamp(thick / 3.0, 0.0, 1.0) / (1.0 + dist0 * 0.04);
            float dR = texture(depthtex1, uvR).r;
            if (dR <= depth0 || any(lessThan(uvR, vec2(0.0))) || any(greaterThan(uvR, vec2(1.0)))) {
                uvR = uv;
                dR = depth1;
            }
            vec3 behind = texture(colortex3, uvR).rgb;
            float d = dR >= 1.0 ? 32.0 : distance(scene0, scenePosAt(uvR, dR));
            vec3 refracted = waterVolume(behind, d, skyLight);
            // Fresnel reflection of the sky (the lookup-table fallback; no SSR in milestone 1).
            vec3 R = reflect(viewDir, n);
            R.y = abs(R.y);
            vec3 refl = skyScatter(R) * smoothstep(0.3, 0.9, skyLight);
#if QF_WATER_STYLE > 0
            // Reflected land and sky from the screen (a hill mirrored in a lake at sunset); the
            // sky table stays the fallback. The sun itself is the glitter path below.
#if QF_SSR_STEPS > 0
            vec3 viewPos0 = viewFromScreen(uv, depth0);
            vec3 viewN = mat3(gbufferModelView) * n;
            vec3 viewR = reflect(normalize(viewPos0), viewN);
            vec4 ssr = waterSSR(viewPos0, viewR, ign(gl_FragCoord.xy + float(frameCounter % 64) * 7.0));
            refl = mix(refl, ssr.rgb, ssr.a);
#endif
#endif
            float F = 0.02 + 0.98 * pow(1.0 - NdotV, 5.0);
#if QF_CAL_WATER == 2
            F = min(1.0, F * 1.6 + 0.08);   // calibration B: strong reflections
#endif
            color = mix(refracted, refl, F);
            // Sun and moon glints: tight GGX, shadowed.
            vec3 L = lightDirWorld();
            vec3 H = normalize(L - viewDir);
            float NdotL = max(dot(n, L), 0.0);
#if QF_SHADOWS
            float sh = sampleShadow(scene0, vec3(0.0, 1.0, 0.0), NdotL, smoothstep(0.75, 0.95, skyLight), gl_FragCoord.xy);
#else
            float sh = smoothstep(0.8, 0.97, skyLight);
#endif
            float NdotH = max(dot(n, H), 0.0);
            float spec = ggx(NdotH, 0.0016) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
#if QF_WATER_STYLE > 0
            // Glitter path (owner r001: sunset water): a low sun on rippled water is a long
            // column of sparkles, not one highlight. A broad lobe gives the column and a very
            // tight one, gated by a sparkle hash on a fine grid that drifts with the waves, the
            // sparkles. Fresnel is evaluated at the half vector (F above is for the view).
            float FH = 0.02 + 0.98 * pow(1.0 - max(dot(H, -viewDir), 0.0), 5.0);
#if QF_WATER_STYLE == 2
            const float GLITTER_A2 = 0.05, GLITTER_SPARK = 1.6;   // GGX alpha^2 of the broad lobe
#else
            const float GLITTER_A2 = 0.03, GLITTER_SPARK = 1.0;
#endif
            float broad = ggx(NdotH, GLITTER_A2) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            vec2 g = (scene0.xz + cameraPosition.xz) * 6.0 + vec2(animTime() * 1.3, -animTime() * 0.9);
            float sparkle = step(0.93, hash12(floor(g))) * (1.0 - smoothstep(16.0, 96.0, dist0));
            float tight = ggx(NdotH, 0.0004) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            // r002 c-round: 0.6 x the core lobe made the path near the sun dimmer than r001's;
            // keep the core at full strength and add the column and sparkles on top.
            spec = spec + broad * 0.35 + tight * sparkle * GLITTER_SPARK * 0.15;
            color += lightIrradiance() * spec * FH * sh * 3.0;
#else
            color += lightIrradiance() * spec * F * sh * 3.0;
#endif
        } else {
            // Under the surface, looking up: Snell's window. Inside it the whole sky is
            // squeezed into a ~97-degree cone, so the sky is looked up along the refracted
            // ray (its horizon glow rings the window instead of a flat disk, round 5), and
            // the transmitted part falls with the water-to-air Fresnel term towards the
            // critical angle. Outside it, total internal reflection mirrors the water below:
            // the deep colour, shaded by the wave slope so the surface still reads as moving.
            vec3 nUp = n.y > 0.0 ? n : -n;
            vec3 Rt = refract(viewDir, -nUp, 1.333);
            float c = abs(dot(viewDir, nUp));
            vec3 deep = waterAmbient(eyeSky) * (WATER_SCATTER / (WATER_ABSORB + WATER_SCATTER));
            // The surface's own slope shades the mirrored part, so the waves read from below.
            float ripple = clamp(0.5 + 9.0 * (n.x * 0.7 + n.z * 0.7), 0.0, 1.0);
            vec3 mirrored = deep * mix(0.6, 1.5, ripple);
            float F = 1.0;
            vec3 above = deep;
            if (dot(Rt, Rt) > 0.0) {
                float cT = abs(Rt.y);
                // Unpolarised Fresnel for the water-to-air interface.
                float rs = (1.333 * c - cT) / (1.333 * c + cT);
                float rp = (c - 1.333 * cT) / (c + 1.333 * cT);
                F = clamp(0.5 * (rs * rs + rp * rp), 0.0, 1.0);
                above = depth1 >= 1.0 ? skyRadiance(normalize(vec3(Rt.x, abs(Rt.y), Rt.z))) : color;
            }
            // Physically the rim is sharp; a real surface's ripples and the eye's blur soften
            // it over a few degrees (round 9 critic: "hard, artificial rim").
            F = max(F, 1.0 - smoothstep(0.64, 0.78, c));
            color = mix(above, mirrored, F);
        }
    }

    if (isEyeInWater == 1) {
        color = waterVolume(color, min(dist0, 96.0), eyeSky);
    } else if (isEyeInWater == 2) {
        vec3 T = exp(-vec3(0.9, 1.6, 3.0) * dist0);
        color = color * T + vec3(1.0, 0.35, 0.08) * BLOCK_I * 0.5 * (1.0 - T);
    } else {
        bool sky = depth0 >= 1.0;
        // Fog modes (owner, round 0: fog per biome). Weights 0-1 from the smoothed biome and
        // weather uniforms in shaders.properties; QF_CAL_FOG forces one for the Shader Lab.
        float wCrisp = 0.0, wMoody = 0.0, wStorm = 0.0;
#if QF_BIOME_FOG == 1
        wCrisp = qfFogCrisp; wMoody = qfFogMoody; wStorm = qfFogStorm;
#endif
#if QF_CAL_FOG == 1
        wCrisp = 1.0;
#elif QF_CAL_FOG == 3
        wMoody = 1.0;
#elif QF_CAL_FOG == 4
        wStorm = 1.0;
#endif
        float lit = sky ? 1.0 : smoothstep(0.0, 0.3, max(skyLight, eyeSky));
        if (!sky) {
            // Haze: none in the near field, rising towards the render distance so chunk edges
            // fade into the sky; thicker in rain.
            float start = far * mix(0.35, 0.12, rainStrength);
            float density = mix(2.2, 4.0, rainStrength) / max(far, 32.0);
            // Owner (r001): the everyday baseline sits between r001's haze (1.0) and crisp (0.2).
            density *= QF_HAZE;
            // Night: visibility falls off with distance into the night sky's colour, so the
            // moonlit near field stays playable while a mob 40 blocks out is only a shape
            // (owner, round 0).
            float nightFog = smoothstep(-0.02, -0.12, sunDirWorld().y);
            start = mix(start, 20.0, nightFog);
            density = mix(density, 1.0 / 64.0, nightFog);
            density *= mix(1.0, 0.2, wCrisp);   // crisp: mountains and plains
            float amount = 1.0 - exp(-max(dist0 - start, 0.0) * density);
            amount = max(amount, smoothstep(far * 0.82, far * 1.0, dist0));
            vec3 haze = skyScatter(viewDir);
            haze = mix(haze, vec3(luminance(haze)), 0.3);   // round 2: a beige band at the horizon
            // At night the fade goes towards a darker sky, so distant land becomes a silhouette
            // instead of a moonlit wall of fog (r12 critic: the full moon hid the mountain that
            // the new moon kept).
            haze *= mix(1.0, 0.45, nightFog);
            color = mix(color, haze, amount * lit);
        }
        if (wMoody + wStorm > 0.0) {
            // Heavy fog is a lit medium, not a sky-coloured wall (r001 critic: the moody and
            // blizzard previews were flat beige and grey slabs that stopped at the sky): droplets
            // or snow lit by the sky dome, the sun or moon (with a forward-scatter lobe, so it
            // glows towards the low sun) and the night floor. It covers the sky as well, so the
            // land fades into it instead of cutting a silhouette.
            vec3 L = lightDirWorld();
            float mu = dot(viewDir, L);
            float g = 0.6;
            float hg = (1.0 - g * g) / (4.0 * PI * pow(1.0 + g * g - 2.0 * g * mu, 1.5));
            vec3 medium = skyIrradiance(vec3(0.0, 1.0, 0.0)) * 0.8 / PI
                        + lightIrradiance() * max(L.y, 0.0) * (0.25 / PI + 0.75 * hg)
                        + nightFloor() * NIGHT_FLOOR_TINT / PI;
            float d = sky ? far : dist0;
            // Moody: exponential height fog, densest at the water line and thin 15 blocks up, so
            // it pools in valleys and over lakes and leaves the near field readable.
            if (wMoody > 0.0) {
                const float H = 7.0, Y0 = 63.0, D0 = 1.0 / 14.0;
                float yc = cameraPosition.y, yp = yc + viewDir.y * d;
                float dy = yp - yc;
                float avg = abs(dy) < 0.05 ? exp(-(yc - Y0) / H)
                          : H * (exp(-(yc - Y0) / H) - exp(-(yp - Y0) / H)) / dy;
                float tau = D0 * min(avg, 4.0) * max(d - 6.0, 0.0);
                vec3 fogC = medium * vec3(0.92, 0.96, 1.0) * 0.9;
                color = mix(color, fogC, wMoody * (1.0 - exp(-tau)) * lit);
            }
            // Storm (snowfall or a tundra blizzard): sight cut to a few dozen blocks, sky included.
            if (wStorm > 0.0) {
                float tau = max(d - 3.0, 0.0) / 18.0;
                vec3 snow = medium * vec3(0.97, 1.0, 1.04);
                color = mix(color, snow, wStorm * (1.0 - exp(-tau)) * lit);
            }
        }
    }
    outColor = vec4(max(color, vec3(0.0)), 1.0);
}
#endif
