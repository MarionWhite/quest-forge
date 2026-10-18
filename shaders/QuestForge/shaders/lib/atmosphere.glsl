// Physically based sky after Hillaire, "A Scalable and Production Ready Sky and Atmosphere
// Rendering Technique" (EGSR 2020). Written from the paper; the medium constants are the
// paper's Earth values. Distances in km, the planet centred at the origin.
//
// Three lookup tables live in colortex5 (layout in lib/lut.glsl):
//   transmittance   256x64   (height, cos zenith) -> transmittance to the top of the atmosphere
//   multi-scatter    32x32   (height, cos sun zenith) -> isotropic multiple-scattering term
//   sky-view       192x112   (azimuth, elevation) -> sky radiance, once for the sun, once for the moon
// Transmittance and multi-scatter are built in the first frames and then kept; the sky-view
// tables are rebuilt every frame in prepare.fsh. Nothing ray-marches the atmosphere per pixel.

const float ATM_RG = 6360.0;            // ground radius
const float ATM_RT = 6460.0;            // top of the atmosphere
const vec3  RAYLEIGH_SCATTER = vec3(5.802, 13.558, 33.100) * 1e-3;   // per km
const float RAYLEIGH_H = 8.0;
const float MIE_SCATTER = 3.996e-3;
const float MIE_EXTINCT = 4.440e-3;
const float MIE_H = 1.2;
const float MIE_G = 0.8;
const vec3  OZONE_ABSORB = vec3(0.650, 1.881, 0.085) * 1e-3;
const vec3  GROUND_ALBEDO = vec3(0.3);

struct Medium {
    vec3 rayleigh;   // scattering
    float mie;       // scattering
    vec3 extinction;
};

Medium mediumAt(float h) {
    h = max(h, 0.0);
    Medium m;
    float dR = exp(-h / RAYLEIGH_H);
    float dM = exp(-h / MIE_H);
    float dO = max(0.0, 1.0 - abs(h - 25.0) / 15.0);
    m.rayleigh = RAYLEIGH_SCATTER * dR;
    m.mie = MIE_SCATTER * dM;
    m.extinction = m.rayleigh + vec3(MIE_EXTINCT * dM) + OZONE_ABSORB * dO;
    return m;
}

float phaseRayleigh(float c) {
    return 3.0 / (16.0 * PI) * (1.0 + c * c);
}

// Cornette-Shanks, the Henyey-Greenstein variant the paper uses for Mie.
float phaseMie(float c) {
    const float g = MIE_G;
    float k = 3.0 / (8.0 * PI) * (1.0 - g * g) / (2.0 + g * g);
    return k * (1.0 + c * c) / pow(1.0 + g * g - 2.0 * g * c, 1.5);
}

// Distance along a ray from radius r (direction cosine mu with the local up) to a sphere of
// radius R; negative if missed. Origin inside the sphere -> the far hit.
float distToSphere(float r, float mu, float R) {
    float d = r * r * (mu * mu - 1.0) + R * R;
    if (d < 0.0) return -1.0;
    return -r * mu + sqrt(d);
}

// Distance to the ground, or -1 if the ray clears it.
float distToGround(float r, float mu) {
    if (mu > 0.0) return -1.0;
    float d = r * r * (mu * mu - 1.0) + ATM_RG * ATM_RG;
    if (d < 0.0) return -1.0;
    return -r * mu - sqrt(d);
}

// --- transmittance table parameterisation (Bruneton 2017's mapping, Hillaire section 5.1) ---
vec2 transmittanceParams(float r, float mu) {
    float H = sqrt(ATM_RT * ATM_RT - ATM_RG * ATM_RG);
    float rho = sqrt(max(r * r - ATM_RG * ATM_RG, 0.0));
    float d = max(distToSphere(r, mu, ATM_RT), 0.0);
    float dMin = ATM_RT - r;
    float dMax = rho + H;
    return vec2((d - dMin) / max(dMax - dMin, 1e-4), rho / H);
}

void transmittanceInverse(vec2 x, out float r, out float mu) {
    float H = sqrt(ATM_RT * ATM_RT - ATM_RG * ATM_RG);
    float rho = H * x.y;
    r = sqrt(rho * rho + ATM_RG * ATM_RG);
    float dMin = ATM_RT - r;
    float dMax = rho + H;
    float d = dMin + x.x * (dMax - dMin);
    mu = d < 1e-4 ? 1.0 : (H * H - rho * rho - d * d) / (2.0 * r * d);
    mu = clamp(mu, -1.0, 1.0);
}

// Ground truth, used only to build the table.
vec3 integrateTransmittance(float r, float mu) {
    float tMax = distToSphere(r, mu, ATM_RT);
    const int N = 40;
    float dt = tMax / float(N);
    vec3 od = vec3(0.0);
    for (int i = 0; i < N; i++) {
        float t = (float(i) + 0.5) * dt;
        float h = sqrt(r * r + t * t + 2.0 * r * mu * t) - ATM_RG;
        od += mediumAt(h).extinction * dt;
    }
    return exp(-od);
}

// --- sky-view table parameterisation ---
// `horizon` is Hillaire's beta, acos(sqrt(r^2 - Rg^2) / r): just under 90 degrees near the
// ground, so the horizon sits at zenith angle pi - beta, just past 90 degrees. Rounds 1-8
// used pi/2 + beta (about 180 degrees), which packed the whole visible sky into the first
// 13% of the table's rows: the horizon band near a low sun got about one row, and golden
// hour and sunset lost their warm horizon (debug view 9 showed it).
// u: azimuth from the light, sqrt-compressed towards it; v: elevation, squared towards the
// horizon so the horizon band gets most rows.
vec2 skyViewParams(vec3 dir, vec3 lightDir, float r) {
    float horizon = acos(clamp(sqrt(max(r * r - ATM_RG * ATM_RG, 0.0)) / r, -1.0, 1.0));
    float zen = acos(clamp(dir.y, -1.0, 1.0));
    float horizonZen = PI - horizon;   // Hillaire: pi - beta (round 9: was pi/2 + beta, ~180 deg)
    float v;
    if (zen < horizonZen) {
        v = 0.5 - 0.5 * sqrt((horizonZen - zen) / horizonZen);
    } else {
        v = 0.5 + 0.5 * sqrt((zen - horizonZen) / (PI - horizonZen));
    }
    vec2 a = normalize(dir.xz + vec2(1e-6, 0.0));
    vec2 b = normalize(lightDir.xz + vec2(1e-6, 0.0));
    float phi = acos(clamp(dot(a, b), -1.0, 1.0));
    return vec2(sqrt(phi / PI), v);
}

// The view direction (in a frame where the light's azimuth is +x) for table coordinates x.
vec3 skyViewDir(vec2 x, float r) {
    float horizon = acos(clamp(sqrt(max(r * r - ATM_RG * ATM_RG, 0.0)) / r, -1.0, 1.0));
    float horizonZen = PI - horizon;   // Hillaire: pi - beta (round 9: was pi/2 + beta, ~180 deg)
    float zen;
    if (x.y < 0.5) {
        float t = 1.0 - 2.0 * x.y;
        zen = horizonZen - t * t * horizonZen;
    } else {
        float t = 2.0 * x.y - 1.0;
        zen = horizonZen + t * t * (PI - horizonZen);
    }
    float phi = x.x * x.x * PI;
    float s = sin(zen);
    return vec3(s * cos(phi), cos(zen), s * sin(phi));
}

// Camera radius: one block is a metre, sea level (y 62) sits on the ground sphere.
float cameraRadius() {
    return ATM_RG + clamp((cameraPosition.y - 62.0) * 0.001, 0.0002, 60.0);
}
