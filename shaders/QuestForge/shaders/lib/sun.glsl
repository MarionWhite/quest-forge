// The real sun (r007; owner r006, sunset-sky: "the sun has not improved at all"). Needs
// common, atmosphere and lut. Used by sky.glsl (the disk) and final.glsl (the glare).
//
// - Size: the real sun, 0.27 degrees across in radius terms 0.0047 rad (r006 drew three times that
//   with a soft edge), with a sharp limb antialiased over about a pixel.
// - Limb darkening per channel (the blue limb darkens most, so the edge is a little redder).
// - Colour: the disk is drawn at a fixed brightness on screen instead of its true radiance.
//   The true sun is ~10^5 times the sky and clipped every channel to white, so the reddening near
//   the horizon never showed. Here the transmittance's hue survives the tone mapper: white-gold
//   high up, deep orange as it sets, and dimmer at the horizon, the way a camera sees it.
// - Glare (final.glsl): the eye's and the lens's scatter, as a narrow point-spread function drawn
//   over everything in front, scaled by how much of the disk is visible this frame (taps on the
//   disk), so trees and clouds cut it and thin cloud edges glow. Its wide wings are tiny: the sky
//   is not washed out (owner r005-r006, look bible: too much bloom is a dislike).

const float SUN_REAL_R = 0.0047 * QF_SUN_SIZE;

// Exposed (on-screen) peak value of the disk centre: below ~1 the tone mapper keeps the hue.
float sunPeak() {
    float y = sunDirWorld().y;
    // pa: 1.6-5 drew a low sun the colour and brightness of the gold sky round it: invisible.
    // r008 (owner r007: the soft dots have no form, "the light doesn't seem to have much of a
    // source"): 6-9 still sat barely above the glare at sunset. The centre now burns white-hot
    // and the limb keeps the gold, so the disk is the brightest thing on screen with a crisp edge.
    return mix(16.0, 22.0, smoothstep(0.0, 0.25, y));
}

// Disk radiance (scene units) seen through transmittance T, at dir.
vec3 sunDiskReal(vec3 dir, vec3 sunDir, vec3 T) {
    float c = dot(dir, sunDir);
    if (c < cos(SUN_REAL_R * 1.3)) return vec3(0.0);
    float a = length(cross(dir, sunDir));                        // ~ the angle, for small angles
    float pxA = 2.0 / (gbufferProjection[1][1] * viewHeight);      // radians per pixel
    float cov = clamp((SUN_REAL_R - a) / pxA + 0.5, 0.0, 1.0);
    if (cov <= 0.0) return vec3(0.0);
    float x = clamp(a / SUN_REAL_R, 0.0, 1.0);
    float mu = sqrt(max(1.0 - x * x, 0.0));
    // Linear limb-darkening coefficients, about right for the visible bands (red, green, blue).
    vec3 limb = 1.0 - vec3(0.47, 0.58, 0.72) * (1.0 - pow(mu, 0.9));
    // The hue of the transmittance, softened (pa: its full hue matched the gold sky round it):
    // yellow-white a few degrees up, orange to red only right at the horizon.
    vec3 Tn = T / max(max(T.r, max(T.g, T.b)), 1e-5);
    vec3 col = pow(Tn, vec3(0.6)) * limb;
    // r008: a hot core that tone-maps to near white, so the hue lives in the limb, as photographs
    // of a low sun show it (white centre, gold to orange rim).
    col = mix(col, vec3(1.0, 0.97, 0.92) * max(col.r, max(col.g, col.b)), 0.55 * mu * mu);
    // r008 loop 2 (critic: at size 5 the disk was 20 px and pale against the glare round it):
    // a white-hot core over the inner 70 % of the radius and a gold rim that falls to a few times
    // the sky, so the disk has a visible form (white centre, gold limb, crisp edge), not a flat dot.
    float core = smoothstep(0.55, 0.95, mu);
    col = mix(col * mix(0.10, 0.5, smoothstep(0.0, 0.6, mu)), vec3(1.0, 0.98, 0.95) * 1.6, core);
    return col * cov * sunPeak() / max(exposure(), 1e-4);
}
