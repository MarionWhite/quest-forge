// Cast shadows from one light (round 8, the Wither Skeleton): figures between a torch and the Krypt's walls throw their
// shadows on the real stone. Each frame the casters are drawn from the light into a small mask (coverage and their
// distance from it); the Krypt's own chunk meshes near the visitor are drawn a second time with a material that darkens
// what the mask covers and is further from the light than the caster (multiplied into what is there, so a shadow
// takes the torch's light away and keeps the stone's texture). The casters live in a scene of their own: a body can cast
// a shadow and not be seen (yours, from inside your head).
//   const SH = castShadows(R, { light: [x, y, z] local, center: () => [x, y, z] local, strength, reach, fov, size, flat })
//     fov: the light's frustum (degrees), fitted to what the shadows fall on; flat: no fall-off with distance (one wall)
//   const body = SH.add(mob)       a caster drawn only into the mask (call R.mob, then SH.add moves it out of the scene)
//   SH.mirror(src, copy)          each frame: the copy (in the mask scene) takes src's pose (same model, same equipment)
//   SH.set({ strength })          the shadows' darkness 0..1 (fade them in or out)
// It cleans up after itself: once the rig's group has left the scene (R.dispose), it removes its meshes and frees its
// targets on the next frame it would have drawn, so the shared rig needs no hook.
import { THREE, clamp } from "./rig.js";

const FAR = 24;
const casterVS = "varying vec3 vW; varying vec2 vUv; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vUv = uv; gl_Position = projectionMatrix * viewMatrix * w; }";
const casterFS = "uniform vec3 uL; uniform sampler2D map; uniform float useMap; varying vec3 vW; varying vec2 vUv; void main(){ if (useMap > 0.5 && texture2D(map, vUv).a < 0.1) discard; gl_FragColor = vec4(1.0, clamp(length(vW - uL) / " + FAR.toFixed(1) + ", 0.0, 1.0), 0.0, 1.0); }";
// (gl_Position as three.js computes it for the Krypt's own draw, modelViewMatrix from the CPU: the same depth to the
// last bit, so the multiply lands on the stone it copies; world * view in the shader is off by more far from the origin)
const recvVS = "uniform mat4 uLVP; varying vec4 vL; varying vec3 vW; varying vec3 vN; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vN = normalize(mat3(modelMatrix) * normal); vL = uLVP * w; gl_Position = projectionMatrix * (modelViewMatrix * vec4(position, 1.0)); }";
const recvFS = `uniform sampler2D uMask; uniform vec3 uL; uniform vec3 uCam; uniform float uK; uniform float uReach; uniform float uFog; uniform vec2 uTexel; uniform float uFlat;
varying vec4 vL; varying vec3 vW; varying vec3 vN;
void main(){
  if (uK < 0.002 || vL.w <= 0.0) discard;
  vec3 p = vL.xyz / vL.w;
  if (abs(p.x) > 1.0 || abs(p.y) > 1.0) discard;
  vec3 toL = uL - vW; float d = length(toL);
  float facing = dot(vN, toL / d);
  if (facing <= 0.02) discard;                     // a face the torch does not light has no shadow of it
  vec2 uv = p.xy * 0.5 + 0.5;
  vec4 m = texture2D(uMask, uv);
  if (m.r < 0.5 || m.g * ${FAR.toFixed(1)} > d - 0.05) discard;   // nothing in the way, or the caster is behind it
  // (the blend is in linear light: 0.15 here reads as about 0.4 on screen, a torch's shadow in a dark crypt)
  float fall = (uFlat > 0.5 ? 1.0 : clamp(1.45 - d / uReach, 0.35, 0.88)) * clamp(facing * 2.5, 0.0, 1.0);
  float c = length(uCam - vW), fog = exp(-uFog * uFog * c * c);
  gl_FragColor = vec4(vec3(1.0 - uK * fall * fog), 1.0);
}`;

export function castShadows(R, { light, center, strength = 0.7, reach = 9, size = 512, fov = 110, flat = false } = {}) {
  const kr = R.kr, scene = R.scene;
  const L = R.L(light[0], light[1], light[2], new THREE.Vector3());
  const maskScene = new THREE.Scene();
  maskScene.background = null;
  const lightCam = new THREE.PerspectiveCamera(fov, 1, 0.05, FAR);
  const rt = new THREE.WebGLRenderTarget(size, size, { depthBuffer: true, magFilter: THREE.NearestFilter, minFilter: THREE.NearestFilter, generateMipmaps: false });   // (half float: the distance to a few mm)
  const LVP = new THREE.Matrix4();
  const uniforms = { uMask: { value: rt.texture }, uL: { value: L }, uCam: { value: new THREE.Vector3() }, uK: { value: strength }, uReach: { value: reach }, uFog: { value: 0.04 }, uFlat: { value: flat ? 1 : 0 }, uLVP: { value: LVP }, uTexel: { value: new THREE.Vector2(1 / size, 1 / size) } };
  const recvMat = new THREE.ShaderMaterial({ uniforms, vertexShader: recvVS, fragmentShader: recvFS, transparent: true, depthWrite: false, depthTest: true,
    blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor, blendDst: THREE.ZeroFactor, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -4, fog: false });
  // The receivers: the Krypt's chunk meshes within reach of the visitor, drawn again (their geometry, shared).
  const recv = new THREE.Group(); recv.name = "scare-shadows";
  const near = new THREE.Box3(), ctr = R.L(0, 1, 4, new THREE.Vector3());
  near.setFromCenterAndSize(ctr, new THREE.Vector3(30, 14, 30));
  const _bb = new THREE.Box3();
  scene.traverse((o) => {
    if (!o.isMesh || !o.geometry || !o.geometry.attributes.bake || !o.geometry.attributes.normal || o.parent === recv) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    o.updateMatrixWorld();
    if (!_bb.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld).intersectsBox(near)) return;
    const m = new THREE.Mesh(o.geometry, recvMat);
    m.matrixAutoUpdate = false; m.matrix.copy(o.matrixWorld); m.matrixWorld.copy(o.matrixWorld); m.matrixWorldAutoUpdate = false;
    m.frustumCulled = false; m.renderOrder = 3;
    recv.add(m);
  });
  scene.add(recv);
  // The casters' mask material: one per texture (so a sword's or a skull's cut-out pixels cast nothing).
  const cmats = new Map();
  const casterMat = (src) => {
    const map = src && src.map ? src.map : null, key = map ? map.uuid : "-";
    if (!cmats.has(key)) cmats.set(key, new THREE.ShaderMaterial({ uniforms: { uL: { value: L }, map: { value: map }, useMap: { value: map ? 1 : 0 } }, vertexShader: casterVS, fragmentShader: casterFS, side: THREE.DoubleSide }));
    return cmats.get(key);
  };
  const toMask = (root) => root.traverse((o) => {
    if (!o.isMesh || !o.material) return;
    const src = Array.isArray(o.material) ? o.material[0] : o.material;
    if (src.blending === THREE.AdditiveBlending) { o.visible = false; return; }   // glow layers cast nothing
    o.material = casterMat(src);
  });
  const SH = {
    light: L, rt, uniforms, recv, maskScene, lightCam,
    add(m) { const p = m.pivot; if (p.parent) p.parent.remove(p); maskScene.add(p); toMask(p); return m; },
    mirror(src, copy) {
      const a = [], b = [];
      src.pivot.traverse((o) => a.push(o)); copy.pivot.traverse((o) => b.push(o));
      for (let i = 0; i < Math.min(a.length, b.length); i++) {
        b[i].position.copy(a[i].position); b[i].quaternion.copy(a[i].quaternion); b[i].scale.copy(a[i].scale);
        if (!b[i].isMesh || b[i].material.isShaderMaterial) b[i].visible = a[i].visible;
        if (b[i].matrixAutoUpdate === false) b[i].matrix.copy(a[i].matrix);
      }
    },
    set({ strength: s } = {}) { if (s != null) uniforms.uK.value = s; },
    dispose() {
      if (recv.parent) recv.parent.remove(recv);
      rt.dispose(); recvMat.dispose(); for (const m of cmats.values()) m.dispose();
    }
  };
  // The mask, drawn just before the receivers (Reflector-style, inside the frame's render): from the torch, aimed at the
  // middle of the figures.
  const trigger = new THREE.Mesh(new THREE.PlaneGeometry(0.001, 0.001), new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false, depthTest: false }));
  trigger.frustumCulled = false; trigger.renderOrder = -1e6; recv.add(trigger);
  const prevClear = new THREE.Color(), cv = new THREE.Vector3();
  let dead = false;
  trigger.onBeforeRender = (renderer) => {
    if (dead) return;
    if (!R.group.parent) { dead = true; uniforms.uK.value = 0; setTimeout(() => SH.dispose(), 0); return; }   // the rig is gone
    if (uniforms.uK.value < 0.002) return;
    const c = center(); R.L(c[0], c[1], c[2], cv);
    lightCam.position.copy(L); lightCam.lookAt(cv); lightCam.updateMatrixWorld(true);
    LVP.multiplyMatrices(lightCam.projectionMatrix, lightCam.matrixWorldInverse);
    uniforms.uCam.value.copy(R.camera.position);
    if (scene.fog && scene.fog.density != null) uniforms.uFog.value = scene.fog.density;
    maskScene.updateMatrixWorld(true);
    const cur = renderer.getRenderTarget(), ac = renderer.autoClear, ca = renderer.getClearAlpha(); renderer.getClearColor(prevClear);
    renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 1); renderer.clear(true, true, false);
    renderer.render(maskScene, lightCam);
    renderer.setRenderTarget(cur); renderer.setClearColor(prevClear, ca); renderer.autoClear = ac;
  };
  return SH;
}
