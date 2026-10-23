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
    vec3 T = exp(-waterAbsorb() * dist);
    vec3 scatterAlbedo = waterScatter() / (waterAbsorb() + waterScatter());
    return color * T + waterAmbient(skyLight) * scatterAlbedo * (1.0 - T);
}

#if QF_MOTES > 0 && QF_PRESET > 0
// Ambient particles (owner r002: "I want to see more things like that"; r000: unobtrusive
// cave dust). Dust and pollen drifting in the air, which only shows where light catches it:
// in sunbeams (a strong forward-scatter lobe, so they glow when you look towards the sun past
// a shadow), around torches underground, and as bubbles rising under water. One mote at most
// per 1.25-block cell of a world-space grid, walked along the view ray for the first ~20
// blocks (a 3D DDA), so each mote is a fixed point in the world: it drifts but never swims
// with the camera. Each draws as a soft dot about two pixels wide, whatever its distance.
#if QF_PRESET >= 3
const int MOTE_STEPS = 22;
#elif QF_PRESET == 2
const int MOTE_STEPS = 16;
#else
const int MOTE_STEPS = 10;
#endif
#if QF_MOTES == 2
const float MOTE_DENSITY = 0.30;
#else
const float MOTE_DENSITY = 0.16;
#endif
const float MOTE_CELL = 1.25;

vec3 ambientMotes(vec3 viewDir, float dist0, float pixelBlock, float eyeSky) {
    vec3 sum = vec3(0.0);
    float maxD = min(dist0 - 0.2, 22.0);
    if (maxD <= 0.5) return sum;
    bool under = isEyeInWater == 1;
    float t = animTime();
    float pxA = 2.0 / (gbufferProjection[1][1] * viewHeight);   // radians per pixel
    vec3 L = lightDirWorld();
    vec3 E = lightIrradiance();
    float mu = dot(viewDir, L);
    const float g = 0.72;
    float phase = (1.0 - g * g) / (4.0 * PI * pow(1.0 + g * g - 2.0 * g * mu, 1.5));
    float eyeBlock = float(eyeBrightnessSmooth.x) / 240.0;
    vec3 Eblock = blockIrradiance(max(pixelBlock, eyeBlock * 0.85));
    bool day = sunDirWorld().y > -0.02;
    vec3 tint = under ? vec3(0.85, 0.95, 1.0) : (day ? vec3(1.0, 0.93, 0.78) : vec3(0.9, 0.93, 1.0));

    // DDA through the grid, starting at the camera.
    vec3 o = cameraPosition / MOTE_CELL;
    vec3 d = viewDir;
    vec3 cell = floor(o);
    vec3 stepv = sign(d);
    vec3 inv = 1.0 / max(abs(d), vec3(1e-4));
    vec3 tMax = (stepv * (cell - o) + stepv * 0.5 + 0.5) * inv;
    for (int i = 0; i < MOTE_STEPS; i++) {
        float h = hash13(cell + 0.17);
        if (h < MOTE_DENSITY) {
            vec3 r3 = vec3(hash13(cell + 1.3), hash13(cell + 2.9), hash13(cell + 4.1));
            vec3 m = cell + 0.2 + 0.6 * r3;
            float fadeLife = 1.0;
            if (under) {
                // Bubbles rise through the cell and fade at its top and bottom.
                float y = fract(r3.y + t * (0.18 + 0.2 * h / MOTE_DENSITY));
                m.y = cell.y + y;
                fadeLife = sin(PI * y);
            } else {
                m += 0.12 * vec3(sin(t * 0.31 + h * 40.0), sin(t * 0.23 + h * 57.0), sin(t * 0.27 + h * 73.0));
            }
            vec3 v = m * MOTE_CELL - cameraPosition;
            float along = dot(v, d);
            if (along > 0.15 && along < maxD) {
                float perp2 = max(dot(v, v) - along * along, 0.0);
                float rw = along * pxA * (under ? 1.2 : 1.1);
                float cov = smoothstep(rw * rw * 1.6, 0.0, perp2);
                if (cov > 0.0) {
                    vec3 lit;
                    if (under) {
                        lit = waterAmbient(eyeSky) * 2.2;
                    } else {
#if QF_SHADOWS
                        float vis = sampleShadow(v, vec3(0.0, 1.0, 0.0), 1.0, eyeSky * eyeSky, gl_FragCoord.xy);
#else
                        float vis = eyeSky * eyeSky;
#endif
                        // Only the forward cone: away from the sun the dust is too faint to see,
                        // and against the bright sky it read as daytime stars (r003 smoke).
                        lit = E * vis * max(phase - 0.04, 0.0) * 2.0
                            + skyIrradiance(vec3(0.0, 1.0, 0.0)) * eyeSky * eyeSky * 0.005
                            + Eblock * 0.10;
                    }
                    float fadeD = smoothstep(maxD, maxD * 0.6, along) * smoothstep(0.15, 0.8, along);
                    sum += lit * tint * cov * fadeD * fadeLife * 0.08;
                }
            }
        }
        // Next cell.
        if (tMax.x < tMax.y && tMax.x < tMax.z) { cell.x += stepv.x; tMax.x += inv.x; if (tMax.x * MOTE_CELL > maxD + 2.0) break; }
        else if (tMax.y < tMax.z)               { cell.y += stepv.y; tMax.y += inv.y; if (tMax.y * MOTE_CELL > maxD + 2.0) break; }
        else                                    { cell.z += stepv.z; tMax.z += inv.z; if (tMax.z * MOTE_CELL > maxD + 2.0) break; }
    }
    return sum;
}
#endif

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
            float sunOcc = 0.0;
            vec3 refl = skyScatter(R);
#if QF_CLOUDS == 1
            refl = applyClouds(refl, R);
#endif
            refl *= smoothstep(0.3, 0.9, skyLight);
#if QF_WATER_STYLE > 0
            // Reflected land and sky from the screen (a hill mirrored in a lake at sunset); the
            // sky table stays the fallback. The sun itself is the glitter path below.
#if QF_SSR_STEPS > 0
            vec3 viewPos0 = viewFromScreen(uv, depth0);
            vec3 viewN = mat3(gbufferModelView) * n;
            vec3 viewR = reflect(normalize(viewPos0), viewN);
            vec4 ssr = waterSSR(viewPos0, viewR, ign(gl_FragCoord.xy + float(frameCounter % 64) * 7.0));
            refl = mix(refl, ssr.rgb, ssr.a);
            // A reflected ray that hits land cannot see the sun either: the glitter path stops
            // where the mirrored cliff is (r003 critic: an orange column ran down the water below
            // a sun hidden behind the cliff, beyond the shadow map's reach).
            sunOcc = ssr.a;
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
            sh *= 1.0 - sunOcc;
            float NdotH = max(dot(n, H), 0.0);
            float spec = ggx(NdotH, 0.0016) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
#if QF_WATER_STYLE > 0
            // Glitter path (owner r001: sunset water): a low sun on rippled water is a long
            // column of sparkles, not one highlight. A broad lobe gives the column; the sparkles
            // are a very tight lobe. Fresnel is evaluated at the half vector (F above is for the view).
            float FH = 0.02 + 0.98 * pow(1.0 - max(dot(H, -viewDir), 0.0), 5.0);
            float lively = 0.0;
#if QF_WATER_STYLE == 2
            lively = 1.0;
#elif QF_WATER_STYLE == 3
            lively = goldenHour();
#endif
            float GLITTER_A2 = mix(0.03, 0.05, lively), GLITTER_SPARK = mix(1.0, 1.6, lively);   // GGX alpha^2 of the broad lobe
            float broad = ggx(NdotH, GLITTER_A2) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
#if QF_GLITTER == 0
            // r002: sparkles gated by a hash on a fine grid that drifts with the waves.
            vec2 g = (scene0.xz + cameraPosition.xz) * 6.0 + vec2(animTime() * 1.3, -animTime() * 0.9);
            float sparkle = step(0.93, hash12(floor(g))) * (1.0 - smoothstep(16.0, 96.0, dist0));
            float tight = ggx(NdotH, 0.0004) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            spec = spec + broad * 0.35 + tight * sparkle * GLITTER_SPARK * 0.15;
#else
            // r003: each sparkle is a facet of the surface's own micro-ripples (lib/water.glsl)
            // catching the sun. Near the camera the micro normal is resolved and the highlight is
            // tight; further out the facets are smaller than a pixel, so the same energy goes
            // into a wider, dimmer lobe: the path stays continuous and never aliases into dots.
            float mfade = 1.0 - smoothstep(10.0, 70.0, dist0);
            vec2 ms = microSlope(scene0.xz + cameraPosition.xz, animTime(), mfade) * (0.6 + 0.8 * lively);
            vec3 nm = normalize(n + vec3(-ms.x, 0.0, -ms.y));
            float NdotHm = max(dot(nm, H), 0.0);
            float a2 = mix(0.0030, 0.0004, mfade);
            float tight = ggx(NdotHm, a2) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            float spark = tight * GLITTER_SPARK;
            // Mid and far: the facets are below a pixel, so draw the glitter as world-anchored
            // glints about two pixels wide (cell size follows the pixel footprint, in powers of
            // two so it stays put), lit with a probability that follows the broad lobe and
            // twinkling a few times a second. On average they carry part of the lobe's energy,
            // so the path is a field of sparkles instead of a smooth sheen (r003 smoke).
            float pxA = 2.0 / (gbufferProjection[1][1] * viewHeight);
            float lc = ceil(log2(max(dist0 * pxA * 2.2 / max(NdotV, 0.12), 0.015)));
            float cellW = exp2(lc);
            vec2 gp = (scene0.xz + cameraPosition.xz + vec2(animTime() * 0.25, -animTime() * 0.17)) / cellW;
            vec2 gid = floor(gp);
            float gtw = floor(animTime() * 5.0 + hash12(gid + lc * 7.7) * 5.0);
            float gh2 = hash12(gid + gtw * 13.17 + lc * 3.1);
            float broadPeak = ggx(1.0, GLITTER_A2) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            float pr = clamp(broad / max(broadPeak, 1e-4), 0.0, 1.0) * mix(0.10, 0.22, lively);
            float glint = step(gh2, pr) * smoothstep(0.45, 0.2, length(fract(gp) - 0.5));
            float glintW = mix(0.6, 1.0, 1.0 - mfade);   // near the camera the micro facets lead
#if QF_GLITTER == 2
            // Cinematic: a longer, warmer, brighter column towards a low sun.
            float gh = goldenHour();
            broad *= 1.0 + 0.9 * gh;
            spark *= 1.0 + 0.6 * gh;
            glint *= 1.0 + 0.8 * gh;
#endif
            // At noon the path is short and close: fewer, softer sparkles (r003 critic: a blown-out
            // blob with sparkles swarming over it on the river).
            float noonTame = mix(0.45, 1.0, lively);
            spec = spec * mix(0.55, 1.0, lively) + broad * 0.26 + (spark * 0.035 + glint * glintW * broad * 1.4 * GLITTER_SPARK) * noonTame;
#endif
            color += lightIrradiance() * spec * FH * sh * 3.0;
#else
            color += lightIrradiance() * spec * F * sh * 3.0;
#endif
#if QF_FLECKS == 1
            // Bubbles and foam flecks (owner r002 loved the "bubble" effect on near water and
            // wants more like it). Tiny pale dots that ride the surface and drift with it,
            // thickest in the shallows and near the shore, gone with distance (they are smaller
            // than a pixel there). Lit like foam: sky, plus the sun where it reaches.
            {
                vec2 wp = scene0.xz + cameraPosition.xz;
                float t = animTime();
                vec2 gp = wp * 7.0 + vec2(t * 0.35, t * 0.22) + n.xz * 3.0;
                vec2 cell = floor(gp);
                float h = hash12(cell);
                float shallow = 1.0 - smoothstep(0.6, 2.5, thick);
                float keep = mix(0.985, 0.94, shallow);
                if (h > keep) {
                    vec2 c = cell + 0.25 + 0.5 * vec2(hash12(cell + 3.7), hash12(cell + 9.1));
                    // Smaller and softer close up (r003 critic: the nearest read as confetti).
                    float r = (0.07 + 0.07 * hash12(cell + 5.3)) * mix(0.6, 1.0, smoothstep(2.0, 10.0, dist0));
                    float dd = length(gp - c);
                    float dotA = smoothstep(r, r * 0.15, dd) * 0.8;
                    // Fade with distance, and out over a few seconds so each fleck has a life.
                    float life = sin(PI * fract(t * 0.12 + h * 7.0));
                    float fade = (1.0 - smoothstep(6.0, 28.0, dist0)) * life;
                    vec3 foamE = skyIrradiance(vec3(0.0, 1.0, 0.0)) * skyLight * skyLight
                               + lightIrradiance() * max(lightDirWorld().y, 0.0) * sh + nightFloor() * NIGHT_FLOOR_TINT;
                    color = mix(color, foamE * (0.75 / PI), dotA * fade * 0.85);
                }
            }
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
            vec3 deep = waterAmbient(eyeSky) * (waterScatter() / (waterAbsorb() + waterScatter()));
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
#if QF_AERIAL == 1
            // Aerial perspective (owner r002: the crisp Extreme Hills view was "very bland"):
            // air between you and far land scatters blue in and takes red out more slowly, so
            // ridges step back in layers, bluer and paler with distance, the way mountains do.
            // It starts at the camera and is far gentler than the haze; crisp biomes keep it, so
            // they stay sharp but gain depth.
            {
                vec3 hdir = normalize(vec3(viewDir.x, max(viewDir.y, 0.03), viewDir.z));
                vec3 air = skyScatter(hdir) * mix(1.0, 0.45, nightFog);
                float apD = mix(400.0, 900.0, nightFog);
                vec3 T = exp(-dist0 / apD * vec3(0.55, 0.78, 1.15));
                color = mix(color, color * T + air * (1.0 - T), lit);
            }
#endif
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
#if QF_MOTES > 0 && QF_PRESET > 0
    // Only in front of land (or under water): against open sky the dust read as daytime stars
    // (r003 critic). It shows in the air between you and the trees, the walls, the lake bed.
    if (isEyeInWater == 1 || (isEyeInWater == 0 && depth0 < 1.0)) color += ambientMotes(viewDir, dist0, texelFetch(colortex2, px, 0).r, eyeSky);
#endif
    outColor = vec4(max(color, vec3(0.0)), 1.0);
}
#endif
