// r011 (owner r010: "start just copying from the packs that are doing things right"; sunset-full: "the
// sun reads as a single hot spot rather than affecting the lighting of the whole atmosphere").
//
// PORTED from Photon Shaders 1.4, Copyright (c) 2021-2025 Benjamin Stott ("SixthSurge"), under the Photon
// Shaders License (LICENSES/photon-LICENSE.txt: modified portions may be redistributed, including in a
// modpack, not on paid platforms). Files ported: include/sky/atmosphere.glsl (the scattering-LUT lookup,
// the nu/mu/mu_s mapping, the horizon stretch, the Mie phase and the saturation boost),
// include/utility/phase_functions.glsl (nvidia_phase_area, henyey_greenstein_phase),
// include/lighting/colors/light_color.glsl (the sun's exposure and tint by time of day),
// include/fog/overworld/analytic.glsl and include/weather/fog.glsl (the analytic air fog and its
// coefficients), and the data file image/atmosphere/scattering.dat (textures/qf_scattering.dat, unmodified).
// Photon works in Rec. 2020; the LUT is converted to Rec. 709 here, where the rest of this pack works.
//
// The mapping functions in phScatterUv come from Eric Bruneton's precomputed atmospheric scattering
// (2017): Copyright (c) 2017 Eric Bruneton, all rights reserved. Redistribution and use in source and
// binary forms, with or without modification, are permitted provided that (1) redistributions of source
// code retain this copyright notice, this list of conditions and the following disclaimer; (2)
// redistributions in binary form reproduce them in the documentation; (3) neither the name of the
// copyright holder nor the names of its contributors may be used to endorse or promote products derived
// from this software without specific prior written permission. THIS SOFTWARE IS PROVIDED BY THE
// COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED (full
// text in LICENSES/photon-LICENSE.txt).
//
// Units: the LUT holds sky radiance for unit irradiance at the top of the atmosphere, the same units as
// this pack's own sky-view tables (offline check, r011 atmo_sim.py: zenith within 0.8-1.2x of ours from
// a 60 to a 0 degree sun), so it drops into the sky-view tables built in prepare.

uniform sampler3D qfScatter;   // shaders.properties: 32 x 64 x 32 RGB16F, (nu x 2, mu, mu_s)

const float PH_PLANET_R = 6371e3;
const float PH_INNER_R = PH_PLANET_R - 1e3;
const float PH_OUTER_R = PH_PLANET_R + 110e3;
const float PH_MIN_MU_S = -0.35;
const float PH_SUN_RADIUS = 2.0 * PI / 180.0;    // Photon's SUN_ANGULAR_RADIUS default (phase only)
const float PH_MOON_RADIUS = 3.0 * PI / 180.0;   // MOON_ANGULAR_RADIUS default

// Rec. 2020 -> Rec. 709, linear (columns).
const mat3 PH_2020_TO_709 = mat3(1.6605, -0.1246, -0.0182, -0.5876, 1.1329, -0.1006, -0.0728, -0.0083, 1.1187);

float phUv(float v, float res) { return v * (1.0 - 1.0 / res) + 0.5 / res; }
float phSat(float x) { return clamp(x, 0.0, 1.0); }
float phLinStep(float a, float b, float x) { return phSat((x - a) / (b - a)); }
float phPulse(float x, float c, float w) {
    x = abs(x - c) / w;
    return x > 1.0 ? 0.0 : 1.0 - x * x * (3.0 - 2.0 * x);
}
float phSphereFar(float mu, float r, float R) {
    float d = r * r * (mu * mu - 1.0) + R * R;
    return d < 0.0 ? -1.0 : -r * mu + sqrt(d);
}
float phHG(float nu, float g) {
    float gg = g * g;
    return (0.25 / PI) * (1.0 - gg) / pow(1.0 + gg - 2.0 * g * nu, 1.5);
}
float phNvidiaArea(float nu, float g, float a, float radius) {
    float cr = cos(radius), sr = sin(radius);
    float mu = nu * cr + sqrt(max(0.0, 1.0 - nu * nu)) * sr;
    if (nu > cr) mu = 1.0;
    float gg = g * g;
    return ((1.0 - gg) * (1.0 + a * mu * mu)) / (PI * pow(1.0 + gg - 2.0 * g * mu, 1.5) * 4.0 * (1.0 + a * (1.0 + 2.0 * gg) / 3.0));
}

// Photon's time-of-day weights (shaders.properties uniforms, here from the sun's height).
float phMeWeight(float sy) {
    float fade = sy < 0.18 ? 0.37 + 1.2 * max(0.0, -sy) : 1.7;
    float w = phSat(1.0 - fade * abs(sy - 0.18));
    return w * w;
}
float phBlueHourProp(float sy) { return exp(-150.0 * (sy + 0.07283) * (sy + 0.07283)); }
float phBlueHourLight(float sy) { return phLinStep(0.05, 1.0, exp(-190.0 * (sy + 0.09604) * (sy + 0.09604))); }

// get_sun_exposure() * get_sun_tint() relative to noon (Photon's base scale 7 is our SUN_I).
vec3 phSunTint(float sy) {
    float bh = phBlueHourLight(sy);
    float mul = 1.0 + 0.5 * phMeWeight(sy) + 40.0 * bh;
    float p = phPulse(sy, 0.17, 0.40);
    vec3 me = mix(vec3(1.0), vec3(1.05, 0.84, 0.93) * 1.2, p * p);
    vec3 blue = mix(vec3(1.0), vec3(0.95, 0.80, 1.0), bh);
    return mul * me * blue;
}

// atmosphere_post_processing: saturation boost (0.10 + 0.20 blue hour), desaturation in rain.
vec3 phPost(vec3 c, float sy) {
    float amt = 0.10 + 0.20 * phBlueHourProp(sy);
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    return max(mix(vec3(l), c, (1.0 + amt) * (1.0 - rainStrength)), vec3(0.0));
}

vec3 phScatterUv(float nu, float mu, float muS) {
    // Improved mapping for nu (Zombye's, via Photon).
    float half_ = sqrt(max((1.0 - mu * mu) * (1.0 - muS * muS), 0.0));
    float nMin = mu * muS - half_, nMax = mu * muS + half_;
    float uNu = nMin == nMax ? nMin : (nu - nMin) / (nMax - nMin);
    uNu = phUv(uNu, 16.0);
    // Stretch the sky near the horizon upwards: the low sun's colours climb higher into the sky.
    if (mu > 0.0) mu *= sqrt(sqrt(mu));
    const float r = PH_PLANET_R;
    const float H = sqrt(PH_OUTER_R * PH_OUTER_R - PH_INNER_R * PH_INNER_R);
    const float rho = sqrt(PH_PLANET_R * PH_PLANET_R - PH_INNER_R * PH_INNER_R);
    float rmu = r * mu;
    float disc = rmu * rmu - r * r + PH_INNER_R * PH_INNER_R;
    float uMu;
    if (mu < 0.0 && disc >= 0.0) {
        float d = -rmu - sqrt(max(disc, 0.0));
        float dMin = r - PH_INNER_R, dMax = rho;
        uMu = dMax == dMin ? 0.0 : (d - dMin) / (dMax - dMin);
        uMu = 0.5 - 0.5 * phUv(uMu, 32.0);
    } else {
        float d = -rmu + sqrt(disc + H * H);
        float dMin = PH_OUTER_R - r, dMax = rho + H;
        uMu = 0.5 + 0.5 * phUv((d - dMin) / (dMax - dMin), 32.0);
    }
    const float dMin = PH_OUTER_R - PH_INNER_R;
    const float dMax = H;
    float D = phSphereFar(PH_MIN_MU_S, PH_INNER_R, PH_OUTER_R);
    float A = (D - dMin) / (dMax - dMin);
    float a = (phSphereFar(muS, PH_INNER_R, PH_OUTER_R) - dMin) / (dMax - dMin);
    float uMuS = phUv(max(0.0, 1.0 - a / A) / (1.0 + a), 32.0);
    return vec3(uNu, uMu, uMuS);
}

// Sky radiance (Rec. 709) for unit irradiance from a light at `light`; `moon` picks the moon's phase.
vec3 phScattering(vec3 dir, vec3 light, bool moon) {
    float nu = dot(dir, light);
    float mu = dir.y, muS = light.y;
    float hmu = mix(-0.01, 0.03, smoothstep(-0.05, 0.1, muS));
    mu = max(mu, hmu);
    vec3 uv = phScatterUv(nu, mu, muS);
    vec3 ray = texture(qfScatter, vec3(uv.x * 0.5, uv.yz)).rgb;
    vec3 mie = texture(qfScatter, vec3(uv.x * 0.5 + 0.5, uv.yz)).rgb;
    vec3 ph;
    if (moon) {
        float t = float(moonPhase) / 4.0;
        t = t > 1.0 ? 2.0 - t : t;
        t = (1.0 - t) * (1.0 - t) * 0.04 + 0.96;
        ph = vec3(phNvidiaArea(nu, 0.895 * t, 1.0, 2.0 * PH_MOON_RADIUS), phNvidiaArea(nu, 0.90 * t, 1.0, 2.0 * PH_MOON_RADIUS),
                  phNvidiaArea(nu, 0.905 * t, 1.0, 2.0 * PH_MOON_RADIUS)) * 1.02;
    } else {
        ph = vec3(phNvidiaArea(nu, 0.85, 1.0, PH_SUN_RADIUS), phNvidiaArea(nu, 0.86, 1.0, PH_SUN_RADIUS),
                  phNvidiaArea(nu, 0.87, 1.0, PH_SUN_RADIUS)) * 0.2;
    }
    return max(PH_2020_TO_709 * (ray + mie * ph), vec3(0.0));
}

// --- analytic air fog (include/fog/overworld/analytic.glsl, include/weather/fog.glsl) -------------
// Photon's defaults: Rayleigh 0.0005 per block, sRGB (0.31, 0.67, 1.0), from sea level + 30 halving every
// 30 blocks; Mie by the hour (morning 0.007, noon 0.0001, evening 0.005, midnight 0.005, blue hour 0.002,
// rain 0.03), from sea level + 7 halving every 7 blocks. A thick, low, sunlit haze at dawn and dusk is what
// lets a low sun light the whole scene.
const float PH_SEA = 63.0;
const vec2 PH_FALL_START = vec2(30.0, 7.0) + PH_SEA;
const vec2 PH_FALL_HALF = vec2(30.0, 7.0);

float phSkyLen() { return max(far, 256.0); }

vec2 phAirmass(vec3 origin, vec3 dir, float len) {
    const vec2 mul = -1.0 / PH_FALL_HALF;
    const vec2 add = -mul * PH_FALL_START;
    vec2 a = origin.y * mul + add;
    float dy = abs(dir.y) < 1e-4 ? 1e-4 : dir.y;
    vec2 p1 = exp2(len * dy * mul + a);
    vec2 p2 = exp2(a);
    return clamp((p1 - p2) / (log(2.0) * mul * dy), 0.0, len) * 0.5;
}

// (in-scattered light, transmittance) along len blocks of dir from the camera. light: the sun or moon
// irradiance at the camera (lightIrradiance()), ambient: Photon's ambient_color (tau x sky radiance),
// densityMul: the pack's biome multipliers (crisp mountains).
mat2x3 phAirFog(vec3 dir, float len, vec3 L, vec3 light, vec3 ambient, float sky, float densityMul) {
    float sy = sunDirWorld().y;
    float me = phMeWeight(sy);
    bool rising = sunDirWorld().x > 0.0;   // Photon: time_sunrise when sun_dir.x > 0
    float tNoon = sy > 0.0 ? 1.0 - me : 0.0;
    float tMid = sy < 0.0 ? 1.0 - me : 0.0;
    float mie = 0.0070 * (rising ? me : 0.0) + 0.0001 * tNoon + 0.0050 * (rising ? 0.0 : me) + 0.0050 * tMid
              + 0.0020 * phLinStep(0.05, 1.0, exp(-190.0 * (sy + 0.07283) * (sy + 0.07283)));
    mie = mix(mie, 0.030, rainStrength);
    float albedo = mix(0.9, 0.5, rainStrength);
    vec3 rayleigh = vec3(0.0761, 0.4141, 1.0) * 0.0005;   // from_srgb(0.31, 0.67, 1.0) * density
    // r011 loop 2: Photon's densities assume its usual 16-32 chunk view; at our 8 chunks (far 128) the
    // haze over the horizon came out a third as thick (ocean_sunset: the sea's far band 139,109,97 vs CR's
    // 212,160,120). Loop 3: x2 density (as if the view reached 256 blocks) veiled golden_lit's near field
    // grey, so land takes sqrt of that and the sky (and its reflection) looks through 256 blocks of air
    // (phSkyLen).
    densityMul *= sqrt(max(1.0, 256.0 / far)) * QF_PH_FOG;
    vec2 am = phAirmass(cameraPosition, dir, len) * densityMul;
    vec3 od = rayleigh * am.x + vec3(mie) * am.y;
    vec3 T = exp(-od);
    vec3 integ = (1.0 - T) / max(od, vec3(1e-6));
    vec3 rs = integ * am.x * rayleigh;
    vec3 ms = integ * am.y * mie * albedo;
    float LoV = dot(dir, L);
    const float iso = 0.25 / PI;
    vec3 S = 2.0 * (rs + ms) * iso * ambient;
    float amount = 1.0, aniso = 1.0;
    for (int i = 0; i < 4; i++) {
        float ph = 0.7 * phHG(LoV, 0.5 * aniso) + 0.3 * phHG(LoV, -0.2 * aniso);
        S += amount * (rs * iso + ms * ph) * light * (1.0 - 0.9 * rainStrength);
        amount *= 0.5;
        aniso *= 0.7;
    }
    S *= sky;
    // "Artificially brighten fog in the early morning and evening (looks nice)."
    S *= 1.0 + 0.75 * phLinStep(0.05, 1.0, exp(-300.0 * (sy + 0.02) * (sy + 0.02)));
    return mat2x3(max(S, vec3(0.0)), T);
}

// The fogged sky in direction dir (reflections: the sea mirrors the lit haze over the horizon, not the
// clear sky behind it). Night keeps the plain sky, as the composite's own fog does.
vec3 phFogSky(vec3 L, vec3 dir, vec3 lightDir, vec3 light) {
    float night = smoothstep(-0.02, -0.12, sunDirWorld().y);
    if (night >= 1.0) return L;
    mat2x3 f = phAirFog(dir, phSkyLen(), lightDir, light, 2.0 * lutFetch(C_AMB_UP).rgb, 1.0, 1.0);
    return mix(L * f[1] + f[0], L, night);
}
