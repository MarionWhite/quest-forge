// composite: the water model (look bible 12), the underwater volume, and distance haze
// (look bible 6), on the HDR scene. One full-screen pass.

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/buffers.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"
#include "/lib/sun.glsl"
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
            float w = edge.x * edge.y * (1.0 - smoothstep(0.6, 1.0, float(i) / float(QF_SSR_STEPS))) * smoothstep(0.0, 0.25, -viewRefl.z + 0.3);
            // Loop 2 (critic: the lake mirrored no cliff or tower): the weight fell linearly with the
            // step count, so a hit 60 blocks out (step 14 of 20) kept under a third; now only the
            // last steps fade.
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

float gBeam = 0.0;   // r008: set by lightShafts (QF_DUST), read by ambientMotes
const float UW_SURF = 62.9;   // r008: about where the water surface is (sea level), for under-water light

#if QF_SHADOWS
float shadowRaw(vec3 scenePos) {
    vec3 clip = (shadowProjection * (shadowModelView * vec4(scenePos, 1.0))).xyz;
    if (max(abs(clip.x), abs(clip.y)) > 0.98) return 1.0;
    vec3 sp = distortShadow(clip) * 0.5 + 0.5;
    ivec2 t = clamp(ivec2(sp.xy * float(shadowMapResolution)), ivec2(0), ivec2(shadowMapResolution - 1));
    return step(sp.z - 0.0004, texelFetch(shadowtex0, t, 0).r);
}
#endif

#if QF_MOTES > 0 && QF_PRESET > 0
// Ambient particles (owner r002: "I want to see more things like that"; r000: unobtrusive
// cave dust). Dust and pollen drifting in the air, which only shows where light catches it:
// in sunbeams (a strong forward-scatter lobe, so they glow when you look towards the sun past
// a shadow), around torches underground, and as bubbles rising under water. One mote at most
// per 1.25-block cell of a world-space grid, walked along the view ray for the first ~20
// blocks (a 3D DDA), so each mote is a fixed point in the world: it drifts but never swims
// with the camera. Each draws as a soft dot about two pixels wide, whatever its distance.
// ue (QF_DUST_DBG 1 still lit nothing in forest_golden's beam): 22 cell steps reach only ~16 m
// along a diagonal ray, short of the canopy gap's beam. With beam dust the walk goes further.
#if QF_PRESET >= 3
const int MOTE_STEPS = QF_DUST > 0 ? 38 : 22;
#elif QF_PRESET == 2
const int MOTE_STEPS = QF_DUST > 0 ? 26 : 16;
#else
const int MOTE_STEPS = 10;
#endif
#if QF_MOTES == 2
const float MOTE_DENSITY = 0.40, MOTE_GAIN = 4.5;
#else
// r007 (owner r006: "I don't know if I can detect the little dust particle things anymore"): a
// little denser, bigger dots, a broad side-scatter so dust shows away from the sun too, and a slow
// glint as a flake turns to the light. r006: 0.20 and 1.8.
const float MOTE_DENSITY = 0.26, MOTE_GAIN = 3.0;
#endif
const float MOTE_CELL = 1.25;

vec3 ambientMotes(vec3 viewDir, float dist0, float pixelBlock, float eyeSky) {
    vec3 sum = vec3(0.0);
    bool under = isEyeInWater == 1;
    float maxD = min(dist0 - 0.2, (QF_DUST > 0 && !under) ? 30.0 : 22.0);   // ud: the canopy gap's beam lies 15-30 m out
    if (maxD <= 0.5) return sum;
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
#if QF_DUST > 0
                // Depth-aware: a flake a metre away is a soft 2-3 px fleck, one 15 blocks out a
                // pinpoint (r007's fixed 2 px everywhere read as screen-space speckle).
                float rw = along * pxA * (under ? mix(4.5, 1.6, smoothstep(1.0, 10.0, along)) : mix(2.6, 1.3, smoothstep(1.0, 12.0, along)));
#else
                float rw = along * pxA * (under ? 1.4 : 1.85);
#endif   // r005: ~1.3 px dots vanished under TAA; r006 1.6 too faint; 2.1 read as bokeh blobs
                float cov = smoothstep(rw * rw * 1.6, 0.0, perp2);
#if QF_UNDERWATER == 1
                if (under) {
                    // r008: a bubble is a bright rim round a clearer middle with a highlight on
                    // top, not a dot (owner r007: Conquest's bubbles).
                    float rr = sqrt(perp2) / (rw * 1.26);
                    cov = smoothstep(1.0, 0.8, rr) * (0.30 + 0.70 * smoothstep(0.45, 0.85, rr)) * 1.4;
                }
#endif
                if (cov > 0.0) {
                    vec3 lit;
                    if (under) {
                        lit = waterAmbient(eyeSky) * 2.2;
#if QF_UNDERWATER == 1
                        lit += sunIrradiance() * max(lightDirWorld().y, 0.0) * exp(-waterAbsorb() * max(UW_SURF - (m.y * MOTE_CELL), 0.0)) * 0.012 * eyeSky;
#endif
                    } else {
#if QF_SHADOWS
                        float vis = sampleShadow(v, vec3(0.0, 1.0, 0.0), 1.0, eyeSky * eyeSky, gl_FragCoord.xy);
#else
                        float vis = eyeSky * eyeSky;
#endif
                        // Only the forward cone: away from the sun the dust is too faint to see,
                        // and against the bright sky it read as daytime stars (r003 smoke).
                        // A flake turning to the light flashes now and then.
                        float glint = 0.55 + 1.6 * pow(0.5 + 0.5 * sin(t * (0.9 + h * 7.0) + h * 91.0), 6.0);
#if QF_DUST > 0
                        // r008: a flake shows only where it sits in sunlight AND the ray crosses a
                        // beam (gBeam, from lightShafts): r007's motes lit every open-air cell
                        // toward the sun, the "weird white dots all over the screen" over the
                        // ocean (owner r007). In the beam they tumble and flash.
                        float glintB = 0.35 + 2.6 * pow(0.5 + 0.5 * sin(t * (1.3 + h * 9.0) + h * 91.0), 8.0);
                        // ub (ua, lake_glitter: specks still spread over the open sky above the
                        // lake, where shadow-map noise counted as beam flips): a flake must sit in a
                        // beam itself, lit with shade within a couple of blocks across the light.
                        float inBeam = 0.0;
#if QF_SHADOWS
                        // Loop 2 (critic: the dust clip showed no mote in the forest_golden beam in any
                        // of 90 frames): gBeam is a dithered per-pixel count of lit/shaded flips, so
                        // over a 2-3 px mote it was zero on most pixels and frames and TAA kept
                        // nothing. The mote's own test (sunlit, with shade within a couple of blocks
                        // across the light) is per mote and steady, and alone keeps open air clear.
                        if (vis > 0.05) {
                            vec3 p1 = normalize(cross(L, abs(L.y) < 0.95 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
                            vec3 p2 = cross(L, p1);
                            // ud: 2.2 m on three sides missed the shade round a wide canopy gap.
                            // Raw (undithered) taps, 3.5 m on four sides.
                            float s1 = shadowRaw(v + p1 * 3.5), s2 = shadowRaw(v - p1 * 3.5);
                            float s3 = shadowRaw(v + p2 * 3.5), s4 = shadowRaw(v - p2 * 3.5);
                            inBeam = 1.0 - min(min(s1, s2), min(s3, s4));
#if QF_DUST_DBG == 1
                            inBeam = 1.0;   // diagnostic: every sunlit mote
#endif
                        }
#endif
                        lit = E * vis * (phase * 2.2 + 0.10) * glintB * inBeam * 1.6
                            + Eblock * 0.32;
#else
                        lit = E * vis * (max(phase - 0.04, 0.0) * 2.4 + 0.09) * glint
                            + skyIrradiance(vec3(0.0, 1.0, 0.0)) * eyeSky * eyeSky * 0.005
                            + Eblock * 0.32;
#endif
                    }
                    float fadeD = smoothstep(maxD, maxD * 0.6, along) * smoothstep(0.15, 0.8, along);
                    sum += lit * tint * cov * fadeD * fadeLife * 0.08 * MOTE_GAIN;
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

#if QF_SHAFTS > 0 && QF_SHADOWS
// Light shafts (r005; owner r004, leaves: "I just expect more cinematic light"; the critic missed
// round f's warm shaft through the trees). Sunlit air along the view ray, from the shadow map:
// a few samples, denser near the camera and dithered per pixel and frame (TAA resolves it), give
// the metres of lit air; a forward-scattering phase makes it show mostly towards the sun, where
// trunks and leaves cut it into beams. Thicker and amber at golden hour.
// r006 (owner r005: "sharpen the rays ... without significantly intensifying the light source and
// washing out the sky"; leaves: B, the stronger ones): more samples, so a beam's edge is resolved
// along the ray instead of smeared by the dither; contrast (the lit share of the ray is raised to a
// power, so a ray that is half in shadow reads as a gap, not a dimmer beam); and less on open-sky
// pixels, so the glow round the sun and the sky itself do not brighten.
#if QF_PRESET >= 3
const int SHAFT_STEPS = 20;
#elif QF_PRESET == 2
const int SHAFT_STEPS = 12;
#else
const int SHAFT_STEPS = 8;
#endif
#if QF_SHAFTS == 2
const float SHAFT_GAIN = 2.0;
#else
const float SHAFT_GAIN = 1.5;
#endif
float hgPhaseS(float mu, float g) {
    return (1.0 - g * g) / (4.0 * PI * pow(1.0 + g * g - 2.0 * g * mu, 1.5));
}
// r008 beam dust (QF_DUST; owner r007: "dust should be visible only inside light shafts and sunbeams
// ... volumetric, depth-aware, shimmering in the beam"). gBeam is how much of this pixel's ray
// crosses a beam: 0 in open sunlight or full shade, high where lit and shaded air alternate (a gap
// in the canopy, a window). The motes and the dust haze both scale with it, so nothing speckles
// open air over the ocean or a sunny plain. (Declared before ambientMotes, which reads it.)
#if QF_DUST > 0
// Dust density, mean about 1: two sheared value-noise layers (a cheap 3D field from 2D lookups)
// multiplied into slow drifting clumps a metre or two across, and a finer churning layer that makes
// the beam shimmer as you watch.
float dustField(vec3 wp, float t) {
    vec2 a = (wp.xz + wp.y * vec2(0.61, -0.43)) * 0.38 + vec2(t * 0.021, t * 0.013);
    vec2 b = (wp.zy + wp.x * vec2(0.37, 0.55)) * 0.47 - vec2(t * 0.017, -t * 0.024);
    float n = texture(qfNoise, a).b * texture(qfNoise, b).b;           // 0-1, mean ~0.25
    float fine = texture(qfNoise, (wp.xy + wp.z * vec2(-0.5, 0.7)) * 1.9 + vec2(-t * 0.09, t * 0.06)).b;
    return clamp(n * 4.4 * (0.55 + 0.9 * fine), 0.0, 4.0);
}
#endif
vec3 lightShafts(vec3 viewDir, float dist, float eyeSky) {
    vec3 L = lightDirWorld();
    float outside = smoothstep(0.1, 0.5, eyeSky);
    if (outside <= 0.0 || L.y < 0.0) return vec3(0.0);
    float maxD = min(dist, 96.0);
    float mu = dot(viewDir, L);
#if QF_SHAFT_STYLE == 1
    float phase = 0.85 * hgPhaseS(mu, 0.78) + 0.15 / (4.0 * PI);   // round 5's lobe
#else
    float phase = 0.75 * hgPhaseS(mu, 0.78) + 0.15 * hgPhaseS(mu, 0.35) + 0.10 / (4.0 * PI);   // j1: a flatter lobe lost the rays by the sun
#endif
    float j = ign(gl_FragCoord.xy + float(frameCounter % 64) * vec2(3.17, 7.91));
    float lit = 0.0;
    float dust = 0.0, nearLit = 0.0, flips = 0.0, prevS = -1.0;
#if QF_DUST > 0
    float tD = animTime();
#endif
    for (int i = 0; i < SHAFT_STEPS; i++) {
        float f = (float(i) + j) / float(SHAFT_STEPS);
        float dd = f * f * maxD;
        float sv = shadowRaw(viewDir * dd);
        lit += sv * 2.0 * f;
        // Lit/shaded transitions along the ray within ~40 blocks: beams.
        if (dd < 40.0) {
            if (prevS >= 0.0) flips += abs(sv - prevS);
            prevS = sv;
            nearLit += sv;
        }
#if QF_DUST > 0
        // The dust lives in the first ~24 blocks, where a beam is wide enough to show it.
        if (sv > 0.0 && dd < 24.0) dust += sv * dustField(viewDir * dd + cameraPosition, tD) * 2.0 * f * smoothstep(0.3, 1.5, dd);
#endif
    }
    lit /= float(SHAFT_STEPS);          // the lit share of the ray, 0-1
    dust /= float(SHAFT_STEPS);
    // A beam: the ray crosses lit and shaded air (flips), or it is partly lit near the camera.
    gBeam = clamp((flips - 0.5) * 0.5, 0.0, 1.0) * outside * smoothstep(0.0, 0.06, L.y);
    float gh = goldenHour();
#if QF_SHAFT_STYLE == 1
    // r007 (owner r006 picked round 5's frame: "the color is warmer, the rays are better formed"):
    // round 5's linear lit air, which keeps the warm glow round the sun over open sky and the
    // half-lit rays that give the beams their shape, now with r006's finer sampling. The amber
    // at golden hour is a little deeper than round 5's.
    // Over open sky the lit air is a veil: round 5's full veil washed out the sun over the ocean (pa),
    // r006's 0.6 lost the warm glow in the forest gap (qh). 0.8, and clear of the disk itself.
    // r008: the cut-out round the disk (1 - 0.6 mu^1500) drew the "faint dark ring" round the sun
    // (critic r007): it dimmed the veil 1.5 degrees out, where the glare should rise. Gone.
    if (dist >= far) lit *= 0.8;
    lit = clamp(lit, 0.0, 1.0) * maxD;
    float sigma = mix(0.0008, 0.0038, gh) * (SHAFT_GAIN / 1.5) * (1.0 + rainStrength);
    vec3 E = lightIrradiance() * mix(vec3(1.0), vec3(1.30, 0.93, 0.56), gh);
#if QF_DUST > 0
    // The dust haze in the beams: extra scattering where the dust clumps drift, only on rays that
    // cross a beam, strongest toward the sun (the forward lobe) but visible from the side too.
#if QF_DUST == 2
    const float DUST_S = 0.022;
#else
    const float DUST_S = 0.013;
#endif
    float dPhase = 0.6 * hgPhaseS(mu, 0.62) + 0.4 / (4.0 * PI);
    vec3 dustL = E * dPhase * DUST_S * dust * min(maxD, 24.0) * gBeam;
#else
    vec3 dustL = vec3(0.0);
#endif
#else
    lit = pow(clamp(lit, 0.0, 1.0), 1.8) * maxD * 1.25;   // metres of sunlit air, with contrast
    if (dist >= far) lit *= 0.6;        // open sky: the beams, not a veil over the sky
    float sigma = mix(0.0008, 0.0036, gh) * SHAFT_GAIN * (1.0 + rainStrength);   // i0: 0.0013 barely showed
    vec3 E = lightIrradiance() * mix(vec3(1.0), vec3(1.25, 0.95, 0.62), gh);
    vec3 dustL = vec3(0.0);
#endif
    return (E * phase * sigma * lit + dustL) * outside * smoothstep(0.0, 0.06, L.y);
}
#endif

#if QF_UNDERWATER == 1 && QF_PRESET > 0
// r008 under water (owner r007: Conquest's "environmental lighting and effects like the bubbles in
// the water, or the visual effects of being in the water"). The surface is about at sea level in
// this world (UW_SURF); the patterns only need a plane to hang from.
float uwSun(vec3 scenePos) {
#if QF_SHAFTS > 0 && QF_SHADOWS
    return shadowRaw(scenePos);
#else
    return 1.0;
#endif
}
// Caustics on everything in view from under water: the waves focus sunlight into a net of bright
// lines that drifts across the bed and walls; dark between them, so they redistribute the light.
vec3 underwaterCaustics(vec3 scenePos, vec3 n) {
    vec3 L = lightDirWorld();
    if (L.y < 0.08 || sunDirWorld().y < 0.0) return vec3(1.0);
    vec3 wp = scenePos + cameraPosition;
    float wd = max(UW_SURF - wp.y, 0.0);
    vec2 cp = wp.xz + L.xz / L.y * wd;
    float t = animTime();
    float c1 = texture(qfNoise, cp * 0.23 + vec2(t * 0.031, t * 0.017)).a;
    float c2 = texture(qfNoise, mat2(0.8, 0.6, -0.6, 0.8) * cp * 0.19 + vec2(-t * 0.022, t * 0.027) + 0.37).a;
    float caust = pow(1.0 - min(c1, c2), 6.0);
    float w = exp(-wd * 0.10) * smoothstep(0.08, 0.3, L.y) * clamp(dot(n, L) * 1.5 + 0.2, 0.0, 1.0);
    w *= uwSun(scenePos + n * 0.08) * (1.0 - smoothstep(16.0, 40.0, length(scenePos)));
    w *= exp(-dot(waterAbsorb(), vec3(2.0)));
    return vec3(mix(1.0, 0.55 + caust * 5.0, w));
}
#if QF_SHADOWS
// Sunbeams in the water: lit water along the view ray (from the shadow map: the land, boats and
// overhangs cut them), in-scattered toward the eye with a forward lobe, and broken into the long
// streaks the moving surface focuses, constant along the light so they slant down like the sun.
vec3 underwaterShafts(vec3 viewDir, float dist) {
    vec3 L = lightDirWorld();
    if (L.y < 0.05 || sunDirWorld().y < 0.0) return vec3(0.0);
    float maxD = min(dist, 40.0);
    const int N = QF_PRESET >= 3 ? 14 : 8;
    float j = ign(gl_FragCoord.xy + float(frameCounter % 64) * vec2(5.3, 2.9));
    float t = animTime();
    vec3 acc = vec3(0.0);
    vec3 A = waterAbsorb();
    for (int i = 0; i < N; i++) {
        float d = (float(i) + j) / float(N) * maxD;
        vec3 p = viewDir * d;
        vec3 wp = p + cameraPosition;
        float depthS = max(UW_SURF - wp.y, 0.0);
        vec2 q = wp.xz + L.xz / L.y * depthS;                     // where its light entered
        float r1 = texture(qfNoise, q * 0.11 + vec2(t * 0.012, t * 0.007)).b;
        float r2 = texture(qfNoise, q * 0.27 - vec2(t * 0.010, -t * 0.014)).b;
        float rays = 0.25 + 3.2 * pow(r1 * r2 * 2.2, 2.0);
        acc += uwSun(p) * rays * exp(-A * (depthS / L.y + d));
    }
    acc *= maxD / float(N);
    float mu = dot(viewDir, L);
    float g = 0.75;
    float phase = 0.8 * (1.0 - g * g) / (4.0 * PI * pow(1.0 + g * g - 2.0 * g * mu, 1.5)) + 0.2 / (4.0 * PI);
    return sunIrradiance() * acc * waterScatter() * phase * 9.0 * smoothstep(0.05, 0.25, L.y);
}
#endif
#endif

#if QF_WAVES == 1
// Exact unpolarised Fresnel reflectance, air to water (n = 1.333): 2% straight down, rising
// steeply at grazing angles (Schlick's fit is a few percent off there, where it shows most).
float fresnelWater(float c) {
    c = clamp(c, 0.0, 1.0);
    float ct = sqrt(max(1.0 - (1.0 - c * c) / (1.333 * 1.333), 0.0));
    float rs = (c - 1.333 * ct) / (c + 1.333 * ct);
    float rp = (1.333 * c - ct) / (1.333 * c + ct);
    return clamp(0.5 * (rs * rs + rp * rp), 0.0, 1.0);
}

// Water seen from above (r006): refraction by the view-space slope, Beer-Lambert absorption and
// in-scattering, caustics on a shallow sunlit bed, exact Fresnel between the refracted scene and
// the reflection (screen-space, with the sky and clouds as the fallback), the sun's reflection on
// the resolved wave facets plus the filtered roughness, a long glitter path at low sun balanced
// with distance, the tight glints under the sun, and foam where the water meets the shore.
vec3 shadeWaterAbove(vec3 color, vec3 n, float var, vec3 scene0, float dist0, vec3 viewDir,
                     float depth0, float depth1, float skyLight) {
    float NdotV = clamp(dot(n, -viewDir), 0.0, 1.0);
    float t = animTime();
    vec3 scene1 = scenePosAt(uv, depth1);
    float thick = depth1 >= 1.0 ? 8.0 : distance(scene0, scene1);
    vec3 L = lightDirWorld();
    float NdotL = max(dot(n, L), 0.0);
#if QF_SHADOWS
    float sh = sampleShadow(scene0, vec3(0.0, 1.0, 0.0), max(L.y, 0.0), smoothstep(0.75, 0.95, skyLight), gl_FragCoord.xy);
#else
    float sh = smoothstep(0.8, 0.97, skyLight);
#endif

    // Refraction: the bed shifts with the slope as the eye sees it (view space), more through deep
    // water, less far away; falls back to the straight lookup if the shift lands in front.
    vec3 nV = mat3(gbufferModelView) * n;
    vec3 upV = mat3(gbufferModelView) * vec3(0.0, 1.0, 0.0);
    vec2 uvR = uv + (nV.xy - upV.xy) * 0.10 * clamp(thick / 4.0, 0.0, 1.0) / (1.0 + dist0 * 0.03);
    float dR = texture(depthtex1, uvR).r;
    if (dR <= depth0 || any(lessThan(uvR, vec2(0.0))) || any(greaterThan(uvR, vec2(1.0)))) {
        uvR = uv;
        dR = depth1;
    }
    vec3 behind = texture(colortex3, uvR).rgb;
    vec3 bedP = scenePosAt(uvR, dR);
    float d = dR >= 1.0 ? 32.0 : distance(scene0, bedP);
#if QF_CAUSTICS == 1 && QF_PRESET > 0
    if (dR < 1.0 && L.y > 0.05 && sunDirWorld().y > 0.0) {
        // Sunlight focused by the waves: two drifting layers of cellular edges, projected along the
        // light; strongest a block or two down, fading with depth (and in murky water).
        float wd = max(scene0.y - bedP.y, 0.0);
        vec2 cp = bedP.xz + cameraPosition.xz + L.xz / L.y * wd;
        float c1 = texture(qfNoise, cp * 0.23 + vec2(t * 0.031, t * 0.017)).a;
        float c2 = texture(qfNoise, mat2(0.8, 0.6, -0.6, 0.8) * cp * 0.19 + vec2(-t * 0.022, t * 0.027) + 0.37).a;
        float caust = pow(1.0 - min(c1, c2), 6.0);
        float w = smoothstep(0.1, 0.7, wd) * exp(-wd * 0.22) * (1.0 - smoothstep(24.0, 64.0, dist0));
        w *= exp(-dot(waterAbsorb(), vec3(3.0)));   // murky water (swamp) hides them
        // r008 (owner r007, river: the ledges a block under the surface look "orangey and flat"):
        // the caustics now redistribute the light instead of only adding to it (dark between the
        // bright lines), so a shallow sunlit bed reads as moving light, not a flat bright stripe.
        behind *= mix(1.0, 0.62 + caust * 4.2, w * sh * smoothstep(0.05, 0.25, L.y));
    }
#endif
    if (dR < 1.0) {
        // r008: sunlight reaching the bed crossed the water above it first (wd / L.y blocks), which
        // the bed's lighting (deferred, before the water existed) never took out: a dirt ledge a
        // block down lit by the full noon sun glowed orange through the clear river. Filter the
        // bed's light by that path (most of a sunlit bed's light is the sun's).
        float wdS = max(scene0.y - bedP.y, 0.0);
        // ub: ua's ledges a block down still glowed yellow (orange dirt through green water). The
        // sun's light also scatters out of the top layer of water and the bed sits in its own
        // in-scattered veil: an extra ~1.2 blocks of path, and a stronger artistic coefficient.
        // Loop 2 (critic: ub turned the sand under beach_noon and shore_noon mint and lime): the
        // longer path, the stronger coefficient and the shallow tint are for river beds only; sea
        // and lake shallows keep r007's filter (tan sand under turquoise, the set's best colour).
        float riv = waterRiverShare();
        vec3 TdownR = exp(-waterAbsorb() * ((wdS + 1.2 * smoothstep(0.02, 0.4, wdS)) / max(L.y, 0.25)) * 4.0);
        vec3 TdownS = exp(-waterAbsorb() * (wdS / max(L.y, 0.25)) * 1.6);
        vec3 Tdown = mix(TdownS, TdownR, riv);
        behind *= mix(vec3(1.0), Tdown, mix(0.35, 0.9, riv) * sh * smoothstep(0.0, 0.2, L.y));
        float shallowV = smoothstep(0.05, 0.5, wdS) * (1.0 - smoothstep(2.0, 4.0, wdS));
        behind = mix(behind, vec3(luminance(behind)) * normalize(waterScatter() + 1e-4) * 1.3, 0.30 * shallowV * sh * riv);
    }
    vec3 refracted = waterVolume(behind, d, skyLight);

    // Reflection: the sky and clouds, then the screen where it has the reflected land.
    vec3 R = reflect(viewDir, n);
    R.y = abs(R.y);
    vec3 refl = skyScatter(R);
#if QF_CLOUDS == 1
    refl = applyClouds(refl, R);
#elif QF_CLOUDS == 2
    refl = applyCloudsCheap(refl, R);
#endif
    refl *= smoothstep(0.3, 0.9, skyLight);
    float sunOcc = 0.0;
#if QF_SSR_STEPS > 0 && QF_WATER_STYLE > 0
    vec3 viewPos0 = viewFromScreen(uv, depth0);
    // r007 (owner r006, lake: "the water texture gets splotchy ... when not enough light"): the near
    // waves' steep facets sent the screen-space rays either into the far cliff or past it, so the
    // dark near water broke into torn patches of mirrored land. The screen rays now follow a
    // calmer normal (the waves' slope halved near the camera), so mirrored land is a smeared band,
    // as on real water; the sky reflection keeps the full waves.
    float flatS = 0.5 * (1.0 - smoothstep(8.0, 48.0, dist0));
#if QF_LAKE_CALM == 1
    // r008: on a lake the mirrored land is a clean, slightly wavering reflection, not a smear.
    flatS = mix(flatS, 0.78, waterLakeShare());
    flatS = mix(flatS, 0.92, waterCalmShare() * smoothstep(0.0, 0.5, goldenHour()));   // loop 2: a clean shore mirror at golden hour
#endif
    vec3 nS = normalize(mix(n, vec3(0.0, 1.0, 0.0), flatS));
    vec3 viewR = reflect(normalize(viewPos0), mat3(gbufferModelView) * nS);
    vec4 ssr = vec4(0.0);
    // pa: a ray reflected downward (a steep wave facet) found the lake bed in depthtex1 and mirrored
    // it as torn brown patches; it can only see the water itself, so it falls back to the sky.
    if (reflect(viewDir, nS).y > 0.01) ssr = waterSSR(viewPos0, viewR, ign(gl_FragCoord.xy + float(frameCounter % 64) * 7.0));
    refl = mix(refl, ssr.rgb, ssr.a);
    sunOcc = ssr.a;
#endif
    float F = fresnelWater(NdotV);
    // r007: near the camera the eye averages the reflectance over many facets, so soften it toward
    // the calm surface's value (lake splotches at grazing views).
    float fAvg = 0.35 * (1.0 - smoothstep(10.0, 60.0, dist0));
#if QF_LAKE_CALM == 1
    fAvg = mix(fAvg, 0.7, waterCalmShare());   // r008: no dark/bright facet flipping on the lake
#endif
    F = mix(F, fresnelWater(clamp(-viewDir.y, 0.0, 1.0)), fAvg);
    vec3 col = mix(refracted, refl, F);

    // The sun (or moon) on the waves.
    sh *= 1.0 - sunOcc;
    vec3 H = normalize(L - viewDir);
    float NdotH = max(dot(n, H), 0.0);
    float FH = fresnelWater(max(dot(H, -viewDir), 0.0));
    float gh = goldenHour();
    float G = NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
    // Resolved facets: a tight highlight, widened by the roughness the far waves filtered away.
    float spec = ggx(NdotH, 0.0006 + 2.0 * var) * G;
    // Near the camera the facets are big and few: keep their sparkle but balance it down, so the
    // path fades toward the camera instead of ending in a blown patch at your feet.
    float balance = mix(0.40, 1.0, smoothstep(2.0, 60.0, dist0));
    spec *= mix(0.55, 1.0, smoothstep(2.0, 30.0, dist0));
    // A high sun on the near water: a field of blinding facets read as the river's white patch
    // (r004-r005 critic, owner r005: follow the critic). Tamed by day, full at golden hour.
    spec *= mix(0.20, 1.0, gh);   // kh: 0.35 still left a sparkling patch on river_noon
#if QF_BIOME_WATER == 1 && QF_CAL_WATER == 0
    // r007 (critic r006: river_noon's near sparkle patch is still the brightest thing in the
    // frame): moving water near the camera at a high sun, tamed further.
    spec *= 1.0 - 0.85 * waterRiverShare() * waterBiomeWeights().w * (1.0 - gh) * (1.0 - smoothstep(6.0, 60.0, dist0));   // qh: 0.6 still the brightest patch
#endif
    // The long column at low sun (owner r005: lively's reach): a broad lobe, balanced by distance.
    float a2b = mix(0.004, 0.050, gh) + 2.0 * var;
    float broad = ggx(NdotH, a2b) * G;
    spec += broad * mix(0.05, 0.42, gh) * balance;   // j0: 0.30 stopped short of the camera
#if QF_SUN_SPARKLE == 1
    {
        // The tight core under the sun (r005, kept): world-anchored glints that hold for a second
        // or two, sized from the pixel footprint, lit with a probability that follows the path's core.
        float a2c = mix(0.0030, 0.022, gh);
        float bc = ggx(NdotH, a2c) * G;
        float bpk = ggx(1.0, a2c) * G;
        float core = smoothstep(0.06, 0.6, clamp(bc / max(bpk, 1e-4), 0.0, 1.0));
        float pxS = 2.0 / (gbufferProjection[1][1] * viewHeight);
        float lc = ceil(log2(max(dist0 * pxS * 2.5 / max(NdotV, 0.12), 0.02)));
        float cw = exp2(lc);
        vec2 g2 = (scene0.xz + cameraPosition.xz + vec2(t * 0.03, -t * 0.02)) / cw;
        vec2 id2 = floor(g2);
        float tw = floor(t * 0.6 + hash12(id2 + lc * 3.3) * 4.0);
        float on = step(1.0 - 0.42 * core, hash12(id2 + tw * 7.31 + lc * 1.7));
        vec2 off = (vec2(hash12(id2 + 1.3), hash12(id2 + 2.7)) - 0.5) * 0.4;
        float dotS = smoothstep(0.30, 0.08, length(fract(g2) - 0.5 - off));
        spec += bpk * on * dotS * core * 3.0 * gh;
    }
#endif
    col += lightIrradiance() * min(spec, mix(80.0, 400.0, gh)) * FH * sh * 3.0;

#if QF_BIOME_WATER == 1 && QF_CAL_WATER == 0
    {
        // Swamp surface (r007; critic r006: "the far water is a little flat"): drifting mats of
        // algae and duckweed, dull olive and matte, and calm slicks between them where the film
        // smooths the ripples and the sky mirrors brighter. Large patches, so they read far out.
        float swW = waterBiomeWeights().z;
        if (swW > 0.02) {
            vec2 wp = scene0.xz + cameraPosition.xz;
            float n1 = texture(qfNoise, wp * 0.019 + vec2(t * 0.0006, t * 0.0004)).b;
            float n2 = texture(qfNoise, wp * 0.043 + vec2(0.31, 0.57)).b;
            float algae = smoothstep(0.54, 0.70, n1 + (texture(qfNoise, wp * 0.21).b - 0.5) * 0.12) * swW;
            float slick = smoothstep(0.56, 0.74, n2) * swW * (1.0 - algae);
            vec3 Eu = skyIrradiance(vec3(0.0, 1.0, 0.0)) * skyLight * skyLight
                    + lightIrradiance() * max(L.y, 0.0) * sh + nightFloor() * NIGHT_FLOOR_TINT;
            col = mix(col, vec3(0.085, 0.10, 0.040) / PI * Eu + refl * 0.02, algae * 0.62);
            col += refl * F * slick * 0.9;
        }
    }
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
        float keep = mix(0.98125, 0.925, shallow);   // owner r004: 1.25x round f (0.985, 0.94)
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
            col = mix(col, foamE * (0.75 / PI), dotA * fade * 0.85);
        }
    }
#endif
#if QF_FOAM == 1 && QF_PRESET > 0
    {
        // Foam where the water meets a shore or a wall: there the view passes through only a sliver
        // of water. A ragged, drifting edge of bubbly cells, lit like any white surface.
        vec2 wp = scene0.xz + cameraPosition.xz;
        float fn = texture(qfNoise, wp * 0.11 + vec2(t * 0.006, t * 0.004)).b;
        float edge = 1.0 - smoothstep(0.05, 0.75, thick + (fn - 0.5) * 0.5);
        if (edge > 0.0 && depth1 < 1.0) {
            float cells = texture(qfNoise, wp * 0.55 + n.xz * 0.4 + vec2(t * 0.025, -t * 0.018)).a;
            float swamp = 0.0;
#if QF_BIOME_WATER == 1 && QF_CAL_WATER == 0
            swamp = waterBiomeWeights().z;
#endif
            float foam = edge * mix(0.35, 1.0, smoothstep(0.25, 0.75, cells)) * (1.0 - smoothstep(20.0, 56.0, dist0))
                       * (1.0 - 0.75 * swamp);
            vec3 foamE = skyIrradiance(vec3(0.0, 1.0, 0.0)) * skyLight * skyLight
                       + lightIrradiance() * max(L.y, 0.0) * sh + nightFloor() * NIGHT_FLOOR_TINT;
            col = mix(col, foamE * (0.8 / PI), clamp(foam * 0.8, 0.0, 1.0));
        }
    }
#endif
    return col;
}
#endif

#if QF_WATER_BLEND == 1 && QF_BIOME_WATER == 1 && QF_CAL_WATER == 0 && QF_WATER_FORCE == 0
// The swamp share round a water pixel (r007; owner r006: "a pleasant gradient to the next instead
// of stark cutoffs"). The game's tint steps from block to block; averaging it over a ring of taps
// 3 and 7 blocks out on the water plane, projected to the screen, turns the step into a gradient
// about a dozen blocks wide. Taps that miss the water are skipped.
float swampBlend(vec3 scene0, float sw0) {
    float sum = sw0 * 1.5, wsum = 1.5;
    for (int i = 0; i < 8; i++) {
        float a = float(i) * 0.7854 + 0.39 * float(i & 1);
        float r = (i & 1) == 0 ? 7.0 : 3.0;
        vec3 P = scene0 + vec3(cos(a), 0.0, sin(a)) * r;
        vec4 c = gbufferProjection * (gbufferModelView * vec4(P, 1.0));
        if (c.w <= 0.0) continue;
        vec2 q = c.xy / c.w * 0.5 + 0.5;
        if (any(lessThan(q, vec2(0.0))) || any(greaterThan(q, vec2(1.0)))) continue;
        ivec2 qp = ivec2(q * vec2(viewWidth, viewHeight));
        if (unpackMaterial(texelFetch(colortex1, qp, 0)) != MAT_WATER) continue;
        sum += texelFetch(colortex2, qp, 0).b;
        wsum += 1.0;
    }
    return sum / wsum;
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
#if QF_WAVES == 1
            float var = pow(texelFetch(colortex2, px, 0).a / 8.0, 2.0);
#if QF_WATER_BLEND == 1 && QF_BIOME_WATER == 1 && QF_CAL_WATER == 0 && QF_WATER_FORCE == 0
            {
                float sw = swampBlend(scene0, texelFetch(colortex2, px, 0).b);
                vec3 bed = scenePosAt(uv, depth1);
                float wdepth = depth1 >= 1.0 ? 16.0 : max(scene0.y - bed.y, 0.0);
                gWaterW = waterWeightsAt(sw, wdepth);
#if QF_DEBUG_VIEW == 10
                outColor = vec4(vec3(sw, texelFetch(colortex2, px, 0).b, gWaterW.x) * 0.6 / max(exposure(), 1e-4), 1.0);
                return;
#endif
            }
#endif
            color = shadeWaterAbove(color, n, var, scene0, dist0, viewDir, depth0, depth1, skyLight);
#if QF_WATER_BLEND == 1 && QF_BIOME_WATER == 1 && QF_CAL_WATER == 0 && QF_WATER_FORCE == 0
            gWaterW = vec4(-1.0);
#endif
#else
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
#elif QF_CLOUDS == 2
            refl = applyCloudsCheap(refl, R);
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
            lively = goldenHour() * (1.0 - 0.5 * waterCalmShare());   // loop 2: calm water, a narrower path
#elif QF_WATER_STYLE == 4
            lively = goldenHour() * 0.5;
#endif
#if QF_WATER_STYLE == 4
            // Calm mirror (owner r004: A): one soft path, much narrower than the lively water's.
            float GLITTER_A2 = mix(0.0030, 0.022, goldenHour()), GLITTER_SPARK = 1.0;   // ih: 0.010 at noon was the milky blob
#else
            float GLITTER_A2 = mix(0.03, 0.05, lively), GLITTER_SPARK = mix(1.0, 1.6, lively);   // GGX alpha^2 of the broad lobe
#endif
            float broad = ggx(NdotH, GLITTER_A2) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
#if QF_GLITTER == 0
            // r002: sparkles gated by a hash on a fine grid that drifts with the waves.
            vec2 g = (scene0.xz + cameraPosition.xz) * 6.0 + vec2(animTime() * 1.3, -animTime() * 0.9);
#if QF_WATER_STYLE == 4
            const float SPARK_CUT = 0.975, BROAD_W = 0.30;
            float noonTame0 = mix(0.22, 1.0, goldenHour());   // r004: river_noon's milky blob
#else
            const float SPARK_CUT = 0.93, BROAD_W = 0.35;
            float noonTame0 = mix(0.45, 1.0, lively);   // r003 critic: river_noon's blown highlight
#endif
            float sparkle = step(SPARK_CUT, hash12(floor(g))) * (1.0 - smoothstep(16.0, 96.0, dist0));
            float tight = ggx(NdotH, 0.0004) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            spec = (spec + broad * BROAD_W) * noonTame0 + tight * sparkle * GLITTER_SPARK * 0.15;
#if QF_SUN_SPARKLE == 1
            {
                // r005: r004's glints moved and twinkled six times a second, so TAA averaged them
                // into the path and they never showed in a still frame. These are world-anchored
                // facets that hold for a second or two, sized from the pixel footprint (cells in
                // powers of two, flattened like the water seen edge-on), lit with a probability that
                // follows the path's core, and several times brighter than the path itself.
                float bpk = ggx(1.0, GLITTER_A2) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
                float core = smoothstep(0.06, 0.6, clamp(broad / max(bpk, 1e-4), 0.0, 1.0));
                float pxS = 2.0 / (gbufferProjection[1][1] * viewHeight);
                float lc = ceil(log2(max(dist0 * pxS * 2.5 / max(NdotV, 0.12), 0.02)));
                float cw = exp2(lc);
                vec2 g2 = (scene0.xz + cameraPosition.xz + vec2(animTime() * 0.03, -animTime() * 0.02)) / cw;
                vec2 id2 = floor(g2);
                float tw = floor(animTime() * 0.6 + hash12(id2 + lc * 3.3) * 4.0);
                float on = step(1.0 - 0.42 * core, hash12(id2 + tw * 7.31 + lc * 1.7));
                vec2 off = (vec2(hash12(id2 + 1.3), hash12(id2 + 2.7)) - 0.5) * 0.4;
                float dotS = smoothstep(0.30, 0.08, length(fract(g2) - 0.5 - off));
                spec += bpk * on * dotS * core * 3.0 * goldenHour();
            }
#endif
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
                float keep = mix(0.98125, 0.925, shallow);   // owner r004: 1.25x round f (0.985, 0.94)
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
#if QF_UNDERWATER == 1 && QF_PRESET > 0
        if (!water && depth0 < 1.0) color *= underwaterCaustics(scene0, decodeNormal(g1.rg));
#endif
        color = waterVolume(color, min(dist0, 96.0), eyeSky);
#if QF_UNDERWATER == 1 && QF_PRESET > 0 && QF_SHADOWS
        color += underwaterShafts(viewDir, depth0 >= 1.0 ? 40.0 : dist0);
#endif
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
            // Height (owner r004, hills: liked "the haze off to the left where the elevation drops",
            // not that "it washes out the color of everything at the same elevation as the camera").
            // Air thickens towards the valley floor and the eye looks through more of it there, so
            // land well below the camera takes the full haze and land at eye level keeps its colour.
            float hw = 1.0;
#if QF_HAZE_HEIGHT == 1
            {
                float below = -scene0.y;   // blocks below the camera
                hw = mix(0.25, 1.25, smoothstep(1.5, 40.0, below)) + 0.2 * smoothstep(10.0, 80.0, -below);
                hw = mix(hw, 1.0, nightFog);
            }
#endif
            density *= hw;
            float amount = 1.0 - exp(-max(dist0 - start, 0.0) * density);
            amount = max(amount, smoothstep(far * 0.82, far * 1.0, dist0));
            vec3 haze = skyScatter(viewDir);
            // round 2: a beige band at the horizon. r008 (owner r007: golden hour "the horizon is
            // still pretty weak"): at golden hour the haze keeps the sky's warmth instead of
            // greying it, and the far land glows amber toward the sun.
            haze = mix(haze, vec3(luminance(haze)), 0.3 * (1.0 - 0.8 * goldenHour() * min(QF_GOLD_HORIZON, 1.0)));
            // Loop 2 (critic: golden_lit's field took a brown-orange wash): the golden haze is a
            // cream veil, not the band's full saturation.
            haze = mix(haze, vec3(luminance(haze)) * vec3(1.07, 1.0, 0.98), 0.45 * goldenHour());
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
                vec3 sH = sunDirWorld(); vec2 side = normalize(vec2(-sH.z, sH.x) + vec2(1e-4, 0.0));
                vec3 hdir = normalize(vec3(side.x, max(viewDir.y, 0.03), side.y));
                vec3 air = skyScatter(hdir) * mix(1.0, 0.45, nightFog);
                air = mix(air, vec3(luminance(air)) * vec3(1.04, 1.0, 0.96), 0.6 * goldenHour());   // loop 2: the band's peach tinted the whole field orange
                float apD = mix(400.0, 900.0, nightFog);
                vec3 T = exp(-dist0 * hw / apD * vec3(0.55, 0.78, 1.15));
                color = mix(color, color * T + air * (1.0 - T), lit);
            }
#endif
            color = mix(color, haze, amount * lit);
        }
#if QF_SHAFTS > 0 && QF_SHADOWS
        color += lightShafts(viewDir, dist0, eyeSky);
#endif
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
    // r008: with beam dust, flakes in a beam show against the sky through a canopy gap too.
    // ug (lake_glitter, forest_golden): sunlit motes against open sky read as the owner's "weird white dots";
    // dust over the sky is never drawn.
    if (isEyeInWater == 1 || (isEyeInWater == 0 && depth0 < 1.0)) {
        vec3 mo = ambientMotes(viewDir, dist0, texelFetch(colortex2, px, 0).r, eyeSky);
        // ug: a flake in front of bright sky or sunlit far land read as a white speck; dust shows
        // against shade, as in a real beam, so it fades over bright backgrounds.
        if (isEyeInWater == 0) mo *= 1.0 - smoothstep(0.30, 0.85, luminance(color * exposure()));
        color += mo;
    }
#endif
    // r008: never hand TAA a NaN or Inf (r007's PBR blob spread from one through the history).
    if (any(isnan(color)) || any(isinf(color))) color = vec3(0.0);
    outColor = vec4(max(color, vec3(0.0)), 1.0);
}
#endif
