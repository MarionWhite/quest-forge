// Sky pieces for the stage: 1.7.10 "fancy" clouds (environment/clouds.png, one cell per pixel,
// extruded, drifting, built so the map wraps without a seam) and square pixel stars.
import * as THREE from 'three';
import { tex } from './stage.js';

const CELL = 18;       // blocks per cloud-map pixel (vanilla is 12; the plateau is small, so a little larger)
const HALF = 22;       // cells each way from the middle of the window
const Y0 = 34, THICK = 4;

const CLOUD_VERT = `
attribute vec3 color; varying vec3 vC; varying float vD;
void main(){ vC = color; vec4 w = modelMatrix*vec4(position,1.0); vD = length(w.xz - cameraPosition.xz);
  gl_Position = projectionMatrix*viewMatrix*w; }`;
const CLOUD_FRAG = `
uniform vec3 uTint; uniform vec3 uHorizon; uniform float uAlpha; varying vec3 vC; varying float vD;
void main(){
  vec3 col = vC * uTint;
  float f = smoothstep(150.0, 330.0, vD);
  col = mix(col, uHorizon, f * 0.85);
  gl_FragColor = vec4(col, uAlpha * (1.0 - smoothstep(300.0, 400.0, vD)));
}`;

export function buildClouds(S) {
  const mask = new Uint8Array(256 * 256);
  let ready = false;
  const img = new Image();
  const group = new THREE.Group();
  group.renderOrder = -5;
  S.scene.add(group);
  const mat = new THREE.ShaderMaterial({
    vertexShader: CLOUD_VERT, fragmentShader: CLOUD_FRAG, transparent: true, depthWrite: false, side: THREE.FrontSide,
    uniforms: { uTint: { value: new THREE.Color(0xf0b9a8) }, uHorizon: { value: new THREE.Color(0xd9703a) }, uAlpha: { value: 0.9 } },
  });
  let mesh = null, ox = 1e9, drift = 0;
  const at = (i, j) => mask[(((j % 256) + 256) % 256) * 256 + (((i % 256) + 256) % 256)];

  function rebuild(cx) {
    const pos = [], col = [], idx = [];
    const quad = (p, c) => {
      const k = pos.length / 3;
      for (const v of p) pos.push(v[0], v[1], v[2]);
      for (let i = 0; i < 4; i++) col.push(c, c, c);
      idx.push(k, k + 1, k + 2, k, k + 2, k + 3);
    };
    // z stays put in map space, the window slides in x
    for (let a = -HALF; a < HALF; a++) for (let c = -HALF; c < HALF; c++) {
      const mi = cx + a, mj = c;
      if (!at(mi, mj)) continue;
      const x0 = a * CELL, x1 = x0 + CELL, z0 = c * CELL, z1 = z0 + CELL, y0 = Y0, y1 = Y0 + THICK;
      quad([[x0, y1, z0], [x0, y1, z1], [x1, y1, z1], [x1, y1, z0]], 1.0);            // top
      quad([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], 0.55);           // bottom
      if (!at(mi + 1, mj)) quad([[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]], 0.8);
      if (!at(mi - 1, mj)) quad([[x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [x0, y0, z0]], 0.8);
      if (!at(mi, mj + 1)) quad([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], 0.68);
      if (!at(mi, mj - 1)) quad([[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]], 0.68);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.setIndex(idx);
    if (mesh) { group.remove(mesh); mesh.geometry.dispose(); }
    mesh = new THREE.Mesh(g, mat);
    mesh.frustumCulled = false;
    mesh.renderOrder = -5;
    group.add(mesh);
  }

  img.onload = () => {
    const c = document.createElement('canvas');
    c.width = c.height = 256;
    const g = c.getContext('2d');
    g.drawImage(img, 0, 0, 256, 256);
    const d = g.getImageData(0, 0, 256, 256).data;
    for (let i = 0; i < 256 * 256; i++) mask[i] = d[i * 4 + 3] > 128 ? 1 : 0;
    ready = true; ox = 1e9;
    S.cloudsReady = true;
  };
  img.src = new URL('./tex/environment/clouds.png', import.meta.url).href;

  const api = {
    group, mat,
    // t: clock seconds. Drifts along +x; the window's cell offset steps, the mesh slides in between.
    update(t) {
      if (!ready) return;
      drift = t * 1.4 + 900;
      const cells = Math.floor(drift / CELL);
      if (cells !== ox) { ox = cells; rebuild(cells); }
      group.position.x = -(drift - cells * CELL);
    },
    setNight(f, horizon) {
      const day = new THREE.Color(0xf0b9a8), night = new THREE.Color(0x2a2540);
      mat.uniforms.uTint.value.copy(day).lerp(night, f);
      mat.uniforms.uHorizon.value.copy(horizon);
    },
  };
  return api;
}

const STAR_VERT = `
attribute float aSeed; uniform float uPx; uniform float uTime; varying float vA; varying vec3 vC;
void main(){
  vec4 mv = modelViewMatrix*vec4(position,1.0);
  gl_Position = projectionMatrix*mv;
  float el = normalize(position).y;
  vA = smoothstep(0.12, 0.55, el) * (0.7 + 0.3*sin(uTime*(0.8+aSeed*1.6) + aSeed*40.0));
  vC = mix(vec3(0.85,0.9,1.0), vec3(1.0,0.86,0.8), fract(aSeed*7.3));
  gl_PointSize = uPx * (aSeed > 0.93 ? 1.6 : 1.0);
}`;
const STAR_FRAG = `uniform float uOpacity; varying float vA; varying vec3 vC; void main(){ gl_FragColor = vec4(vC, vA*uOpacity); }`;

export function buildStars(S, rnd) {
  const n = 420;
  const pos = new Float32Array(n * 3), seed = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const th = rnd() * Math.PI * 2, el = Math.asin(0.05 + rnd() * 0.95);
    pos.set([Math.cos(el) * Math.cos(th) * 200, Math.sin(el) * 200, Math.cos(el) * Math.sin(th) * 200], i * 3);
    seed[i] = rnd();
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  const mat = new THREE.ShaderMaterial({
    vertexShader: STAR_VERT, fragmentShader: STAR_FRAG, transparent: true, depthWrite: false,
    uniforms: { uPx: { value: 2.5 }, uTime: { value: 0 }, uOpacity: { value: 0.5 } },
  });
  const pts = new THREE.Points(geo, mat);
  pts.frustumCulled = false;
  pts.renderOrder = -9;
  S.scene.add(pts);
  return { points: pts, mat, setPx(px) { mat.uniforms.uPx.value = px; } };
}
