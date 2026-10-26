// Particles: the torch's small flame and smoke (as in 1.7.10), fire, the spawner's flames, lava embers, drips.
// Two Points objects (additive for light, normal for smoke and drops) share one pixel-art atlas drawn here.
import * as THREE from "three";

const TILE = { flame: 0, smoke: 1, ember: 2, drip: 3 };
function atlas() {
  const c = document.createElement("canvas"); c.width = 64; c.height = 16;
  const x = c.getContext("2d");
  const px = (t, X, Y, w, h, col) => { x.fillStyle = col; x.fillRect(t * 16 + X, Y, w, h); };
  // flame: a small diamond of yellow in orange
  px(0, 6, 4, 4, 8, "#e8601a"); px(0, 4, 6, 8, 4, "#e8601a"); px(0, 6, 6, 4, 4, "#ffd35a"); px(0, 7, 3, 2, 2, "#e8601a");
  // smoke: a ragged grey blot
  const sm = (X, Y, w, h, col) => px(1, X, Y, w, h, col);
  sm(5, 3, 6, 10, "#5d5c61"); sm(3, 5, 10, 6, "#5d5c61"); sm(6, 5, 4, 6, "#7a7980"); sm(4, 6, 3, 2, "#4a494e"); sm(9, 8, 3, 3, "#4a494e");
  // ember
  px(2, 6, 6, 3, 3, "#ffb04a"); px(2, 7, 7, 1, 1, "#fff0b0");
  // drip
  px(3, 7, 4, 2, 5, "#7fb0d8"); px(3, 6, 7, 4, 2, "#7fb0d8"); px(3, 7, 5, 1, 2, "#d6ecff");
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  return t;
}

class Set_ {
  constructor(max, blending, tex, scene) {
    this.max = max; this.n = 0;
    this.p = new Float32Array(max * 3); this.v = new Float32Array(max * 3);
    this.life = new Float32Array(max); this.maxLife = new Float32Array(max);
    this.s0 = new Float32Array(max); this.s1 = new Float32Array(max);
    this.col = new Float32Array(max * 3); this.tile = new Float32Array(max); this.a0 = new Float32Array(max);
    this.floorY = new Float32Array(max).fill(-1e9);
    this.outPos = new Float32Array(max * 3); this.outSize = new Float32Array(max); this.outAlpha = new Float32Array(max); this.outTile = new Float32Array(max); this.outCol = new Float32Array(max * 3);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(this.outPos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute("size", new THREE.BufferAttribute(this.outSize, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute("alpha", new THREE.BufferAttribute(this.outAlpha, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute("tile", new THREE.BufferAttribute(this.outTile, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute("color", new THREE.BufferAttribute(this.outCol, 3).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 0);
    this.uni = { map: { value: tex }, scale: { value: 600 } };
    const m = new THREE.ShaderMaterial({
      uniforms: this.uni, transparent: true, depthWrite: false, blending,
      vertexShader: `attribute float size; attribute float alpha; attribute float tile; attribute vec3 color; uniform float scale;
        varying float vA; varying float vT; varying vec3 vC;
        void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); gl_Position = projectionMatrix * mv; gl_PointSize = max(1.0, size * scale / max(0.05, -mv.z)); vA = alpha; vT = tile; vC = color; }`,
      fragmentShader: `uniform sampler2D map; varying float vA; varying float vT; varying vec3 vC;
        void main(){ vec2 uv = vec2((vT + gl_PointCoord.x) / 4.0, 1.0 - gl_PointCoord.y); vec4 t = texture2D(map, uv);
          float a = t.a * vA; if (a < 0.02) discard; gl_FragColor = vec4(t.rgb * vC, a); }`
    });
    this.points = new THREE.Points(g, m); this.points.frustumCulled = false; this.points.renderOrder = 5;
    scene.add(this.points);
  }
  spawn(x, y, z, vx, vy, vz, life, s0, s1, a0, tile, col = [1, 1, 1], floorY = -1e9) {
    if (this.n >= this.max) return;
    const i = this.n++, j = i * 3;
    this.p[j] = x; this.p[j + 1] = y; this.p[j + 2] = z; this.v[j] = vx; this.v[j + 1] = vy; this.v[j + 2] = vz;
    this.life[i] = 0; this.maxLife[i] = life; this.s0[i] = s0; this.s1[i] = s1; this.a0[i] = a0; this.tile[i] = tile;
    this.col[j] = col[0]; this.col[j + 1] = col[1]; this.col[j + 2] = col[2]; this.floorY[i] = floorY;
  }
  update(dt) {
    let i = 0;
    while (i < this.n) {
      this.life[i] += dt;
      const j = i * 3;
      this.p[j] += this.v[j] * dt; this.p[j + 1] += this.v[j + 1] * dt; this.p[j + 2] += this.v[j + 2] * dt;
      if (this.life[i] >= this.maxLife[i] || this.p[j + 1] < this.floorY[i]) {
        const l = --this.n;
        if (i !== l) {
          for (const arr of [this.life, this.maxLife, this.s0, this.s1, this.tile, this.a0, this.floorY]) arr[i] = arr[l];
          for (let q = 0; q < 3; q++) { this.p[j + q] = this.p[l * 3 + q]; this.v[j + q] = this.v[l * 3 + q]; this.col[j + q] = this.col[l * 3 + q]; }
        }
        continue;
      }
      const f = this.life[i] / this.maxLife[i];
      this.outPos[j] = this.p[j]; this.outPos[j + 1] = this.p[j + 1]; this.outPos[j + 2] = this.p[j + 2];
      this.outSize[i] = this.s0[i] + (this.s1[i] - this.s0[i]) * f;
      this.outAlpha[i] = this.a0[i] * (f < 0.12 ? f / 0.12 : 1 - (f - 0.12) / 0.88);
      this.outTile[i] = this.tile[i];
      this.outCol[j] = this.col[j]; this.outCol[j + 1] = this.col[j + 1]; this.outCol[j + 2] = this.col[j + 2];
      i++;
    }
    const g = this.points.geometry;
    g.setDrawRange(0, this.n);
    for (const k of ["position", "size", "alpha", "tile", "color"]) g.attributes[k].needsUpdate = true;
  }
}

export function makeFx(scene, emitters, { phone = false } = {}) {
  const tex = atlas();
  const add = new Set_(phone ? 260 : 600, THREE.AdditiveBlending, tex, scene);
  const nrm = new Set_(phone ? 260 : 600, THREE.NormalBlending, tex, scene);
  const R2 = 20 * 20;
  const acc = emitters.map(() => Math.random());
  const rr = (s) => (Math.random() - 0.5) * s;
  return {
    update(dt, cam, viewHeightPx, fovRad, gate = null) {
      const sc = viewHeightPx * 0.5 / Math.tan(fovRad / 2);
      add.uni.scale.value = sc; nrm.uni.scale.value = sc;
      for (let e = 0; e < emitters.length; e++) {
        const m = emitters[e];
        const dx = m.x - cam.x, dz = m.z - cam.z, dy = m.y - cam.y;
        if (dx * dx + dz * dz + dy * dy > R2) continue;
        const gf = gate ? gate(m.x, m.y, m.z) : 1;
        if (gf <= 0.03) continue;
        acc[e] += dt * Math.min(1, gf);
        const rate = m.k === "torch" ? 5 : m.k === "fire" ? 9 : m.k === "spawner" ? 12 : m.k === "lava" ? 1.4 : m.k === "drip" ? 0.28 : 0;
        const every = 1 / rate;
        while (acc[e] > every) {
          acc[e] -= every * (0.6 + Math.random() * 0.8);
          if (m.k === "torch") {
            add.spawn(m.x + rr(0.05), m.y, m.z + rr(0.05), rr(0.05), 0.2 + Math.random() * 0.12, rr(0.05), 0.42, 0.075, 0.02, 1, TILE.flame, [1.4, 1.0, 0.6]);
            if (Math.random() < 0.45) nrm.spawn(m.x + rr(0.04), m.y + 0.04, m.z + rr(0.04), rr(0.05), 0.3 + Math.random() * 0.15, rr(0.05), 1.3, 0.07, 0.2, 0.5, TILE.smoke, [0.8, 0.8, 0.85]);
          } else if (m.k === "fire") {
            add.spawn(m.x + rr(0.5), m.y - 0.3, m.z + rr(0.5), rr(0.1), 0.5 + Math.random() * 0.3, rr(0.1), 0.7, 0.1, 0.03, 1, TILE.flame, [1.3, 0.9, 0.5]);
            if (Math.random() < 0.3) nrm.spawn(m.x + rr(0.4), m.y + 0.2, m.z + rr(0.4), rr(0.08), 0.5, rr(0.08), 1.8, 0.14, 0.34, 0.5, TILE.smoke, [0.55, 0.52, 0.52]);
            if (Math.random() < 0.18) add.spawn(m.x + rr(0.4), m.y, m.z + rr(0.4), rr(0.3), 0.9, rr(0.3), 1.4, 0.04, 0.02, 1, TILE.ember, [1.3, 1, 0.7]);
          } else if (m.k === "spawner") {
            add.spawn(m.x + rr(0.9), m.y - 0.6 + Math.random() * 0.9, m.z + rr(0.9), rr(0.05), 0.35, rr(0.05), 0.8, 0.09, 0.03, 1, TILE.flame, [1.3, 0.9, 0.5]);
            if (Math.random() < 0.3) nrm.spawn(m.x + rr(0.6), m.y + 0.3, m.z + rr(0.6), rr(0.05), 0.4, rr(0.05), 1.6, 0.1, 0.26, 0.4, TILE.smoke, [0.6, 0.6, 0.65]);
          } else if (m.k === "lava") {
            add.spawn(m.x + rr(0.8), m.y, m.z + rr(0.8), rr(0.2), 0.7 + Math.random() * 0.7, rr(0.2), 1.8, 0.05, 0.02, 1, TILE.ember, [1.3, 0.9, 0.6]);
          } else if (m.k === "drip") {
            nrm.spawn(m.x, m.y, m.z, 0, -0.2, 0, 1.2, 0.07, 0.07, 0.85, TILE.drip, [0.9, 1, 1.1], m.floorY);
            const v = nrm.v; v[(nrm.n - 1) * 3 + 1] = -0.2; // accelerates below
          }
        }
      }
      // Drops fall faster as they go.
      for (let i = 0; i < nrm.n; i++) if (nrm.tile[i] === TILE.drip) nrm.v[i * 3 + 1] -= 6 * dt;
      add.update(dt); nrm.update(dt);
    },
    dispose() { scene.remove(add.points, nrm.points); }
  };
}
