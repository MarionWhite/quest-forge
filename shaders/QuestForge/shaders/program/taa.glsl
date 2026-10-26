// composite1: temporal anti-aliasing (rule 12, milestone 1 item 5), Low and up.
// Reprojects the history with the previous camera, clips it to the current 3x3
// neighbourhood's colour distribution (variance clipping, Salvi 2016) in YCoCg, and drops it
// where the stored depth says the surface was not visible last frame (disocclusion).
// Works on exposed colour with Karis' 1/(1+luma) weighting, so a bright sky edge cannot
// ring. The hand is never reprojected.

#include "/lib/platform.glsl"
#include "/lib/settings.glsl"
#include "/lib/buffers.glsl"
#include "/lib/common.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/lut.glsl"

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
uniform sampler2D colortex3;
uniform sampler2D colortex4;
uniform sampler2D depthtex0;

/* RENDERTARGETS: 4 */
layout(location = 0) out vec4 outHistory;

vec3 toYCoCg(vec3 c) {
    return vec3(dot(c, vec3(0.25, 0.5, 0.25)), dot(c, vec3(0.5, 0.0, -0.5)), dot(c, vec3(-0.25, 0.5, -0.25)));
}

vec3 fromYCoCg(vec3 c) {
    return vec3(c.x + c.y - c.z, c.x + c.z, c.x - c.y - c.z);
}

vec3 weighted(vec3 c) {
    return c / (1.0 + luminance(c));
}

void main() {
    ivec2 px = ivec2(gl_FragCoord.xy);
    float e = exposure();
    vec3 cur = toYCoCg(weighted(texelFetch(colortex3, px, 0).rgb * e));
    vec3 m1 = vec3(0.0), m2 = vec3(0.0);
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec3 c = toYCoCg(weighted(texelFetch(colortex3, px + ivec2(x, y), 0).rgb * e));
            m1 += c;
            m2 += c * c;
        }
    }
    m1 /= 9.0;
    vec3 sigma = sqrt(max(m2 / 9.0 - m1 * m1, vec3(0.0)));

    float depth = texelFetch(depthtex0, px, 0).r;
    int flag = unpackFlag(texelFetch(colortex1, px, 0));
    vec3 viewPos = viewFromScreen(uv, depth);
    float linDepth = depth >= 1.0 ? 60000.0 : -viewPos.z;

    vec2 prevUv = uv;
    float expectedPrevDepth = linDepth;
    if (flag != FLAG_HAND) {
        if (depth >= 1.0) {
            vec3 dir = mat3(gbufferModelViewInverse) * normalize(viewPos);
            vec4 pc = gbufferPreviousProjection * vec4(mat3(gbufferPreviousModelView) * dir, 0.0);
            prevUv = pc.xy / pc.w * 0.5 + 0.5;
        } else {
            vec3 scene = sceneFromView(viewPos) + cameraPosition - previousCameraPosition;
            vec4 pv = gbufferPreviousModelView * vec4(scene, 1.0);
            vec4 pc = gbufferPreviousProjection * pv;
            prevUv = pc.xy / pc.w * 0.5 + 0.5;
            expectedPrevDepth = -pv.z;
        }
    }

    float current = 0.1;                       // weight of this frame
    if (flag == FLAG_MOVING) current = 0.2;
    if (flag == FLAG_HAND) current = 0.3;
    vec4 hist = texture(colortex4, prevUv);
    if (any(isnan(hist)) || any(isinf(hist))) hist = vec4(0.0);   // r008: a NaN in history never heals
    bool offscreen = any(lessThan(prevUv, vec2(0.0))) || any(greaterThan(prevUv, vec2(1.0)));
    bool disoccluded = depth < 1.0 && abs(hist.a - expectedPrevDepth) > 0.06 * expectedPrevDepth + 0.15;
    if (offscreen || disoccluded || !(hist.a > 0.0)) current = 1.0;

    // Faster convergence while the camera moves, which also limits smearing.
    vec2 motionPx = (uv - prevUv) * vec2(viewWidth, viewHeight);
    current = max(current, clamp(length(motionPx) * 0.04, 0.0, 0.35));

    vec3 h = toYCoCg(hist.rgb);
    vec3 lo = m1 - 1.15 * sigma, hi = m1 + 1.15 * sigma;
    // Clip towards the mean rather than clamp per channel: keeps the hue of the history.
    vec3 d = h - m1;
    vec3 ext = max(hi - m1, vec3(1e-5));
    float t = max(max(abs(d.x) / ext.x, abs(d.y) / ext.y), abs(d.z) / ext.z);
    if (t > 1.0) h = m1 + d / t;

    vec3 res = fromYCoCg(mix(h, cur, current));
    outHistory = vec4(max(res, vec3(0.0)), linDepth);
}
#endif
