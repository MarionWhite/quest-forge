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
            float F = 0.02 + 0.98 * pow(1.0 - NdotV, 5.0);
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
            float spec = ggx(max(dot(n, H), 0.0), 0.0016) * NdotL / (4.0 * max(NdotV, 0.05) + 0.3);
            color += lightIrradiance() * spec * F * sh * 3.0;
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
            float ripple = clamp(0.5 + 6.0 * dot(n.xz, vec2(0.7, 0.7)), 0.0, 1.0);
            vec3 mirrored = deep * mix(0.75, 1.3, ripple);
            if (dot(Rt, Rt) > 0.0) {
                float cT = abs(Rt.y);
                // Unpolarised Fresnel for the water-to-air interface.
                float rs = (1.333 * c - cT) / (1.333 * c + cT);
                float rp = (c - 1.333 * cT) / (c + 1.333 * cT);
                float F = clamp(0.5 * (rs * rs + rp * rp), 0.0, 1.0);
                vec3 above = depth1 >= 1.0 ? skyRadiance(normalize(vec3(Rt.x, abs(Rt.y), Rt.z))) : color;
                color = mix(above, mirrored, F);
            } else {
                color = mirrored;
            }
        }
    }

    if (isEyeInWater == 1) {
        color = waterVolume(color, min(dist0, 96.0), eyeSky);
    } else if (isEyeInWater == 2) {
        vec3 T = exp(-vec3(0.9, 1.6, 3.0) * dist0);
        color = color * T + vec3(1.0, 0.35, 0.08) * BLOCK_I * 0.5 * (1.0 - T);
    } else if (depth0 < 1.0) {
        // Haze: none in the near field, rising towards the render distance so chunk edges
        // fade into the sky; thicker in rain.
        float start = far * mix(0.35, 0.12, rainStrength);
        float density = mix(2.2, 4.0, rainStrength) / max(far, 32.0);
        float amount = 1.0 - exp(-max(dist0 - start, 0.0) * density);
        amount = max(amount, smoothstep(far * 0.82, far * 1.0, dist0));
        vec3 haze = skyScatter(viewDir);
        haze = mix(haze, vec3(luminance(haze)), 0.3);   // round 2: a beige band at the horizon
        color = mix(color, haze, amount * smoothstep(0.0, 0.3, max(skyLight, eyeSky)));
    }
    outColor = vec4(max(color, vec3(0.0)), 1.0);
}
#endif
