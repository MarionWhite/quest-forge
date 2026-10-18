// Neutral tone mapping: the Khronos PBR Neutral operator (Khronos Group, 2024; the
// specification and reference code are Apache-2.0). Implemented here from the published
// formula. It keeps hue and saturation through the mid-tones and only desaturates true
// highlights towards white, so wood, chests, sand and gold do not turn neon (look bible 3),
// and bright orange keeps its hue (no AgX-style skew needed).

//
// The operator's toe (subtracting a "black flare" offset of up to 0.04 from every channel)
// is left out. It assumes brighter exposure than ours: at our levels most pixels sit below
// 0.08, the offset removed the weakest channel outright, and round 2 came out neon (mean
// saturation 0.82 against vanilla's 0.53), with blue stone in shade and rust dirt at night.
vec3 tonemapNeutral(vec3 color) {
    const float startCompression = 0.8 - 0.04;
    const float desaturation = 0.15;
    float peak = max(color.r, max(color.g, color.b));
    if (peak < startCompression) return color;
    const float d = 1.0 - startCompression;
    float newPeak = 1.0 - d * d / (peak + d - startCompression);
    color *= newPeak / peak;
    float g = 1.0 - 1.0 / (desaturation * (peak - newPeak) + 1.0);
    return mix(color, vec3(newPeak), g);
}

vec3 linearToSrgb(vec3 c) {
    c = clamp(c, 0.0, 1.0);
    return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}
