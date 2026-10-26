// A small pool of square, pixel-style particles (Minecraft block chips, dust, sparks).
// One Points object per blend mode; update(dt) steps every live particle. The page calls it every
// frame whatever the phase is, so a particle can never be left frozen in mid-air.
import * as THREE from 'three';

const VERT = `
attribute float aSize; attribute float aAlpha; attribute vec3 color;
varying vec3 vC; varying float vA; uniform float uScale;
void main(){
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = max(2.0, aSize * uScale / max(0.1, -mv.z));
  vC = color; vA = aAlpha;
}`;
const FRAG = `
varying vec3 vC; varying float vA;
void main(){
  vec2 q = gl_PointCoord - 0.5;
  float shade = 0.82 + 0.3 * step(0.0, -(q.x + q.y));
  gl_FragColor = vec4(vC * shade, vA);
}`;

// The ground a particle lands on: the dais top is one block up.
export function floorAt(x, z) { return (x >= -1 && x < 2 && z >= -1 && z < 2) ? 1.02 : 0.02; }

export class Particles {
  constructor(parent, { cap = 900, additive = false } = {}) {
    this.cap = cap; this.n = 0;
    this.pos = new Float32Array(cap * 3);
    this.col = new Float32Array(cap * 3);
    this.size = new Float32Array(cap);
    this.alpha = new Float32Array(cap);
    this.vel = new Float32Array(cap * 3);
    this.age = new Float32Array(cap);
    this.life = new Float32Array(cap);
    this.s0 = new Float32Array(cap);
    this.grav = new Float32Array(cap);
    this.bounce = new Float32Array(cap);
    this.geo = new THREE.BufferGeometry();
    this.geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    this.geo.setAttribute('color', new THREE.BufferAttribute(this.col, 3).setUsage(THREE.DynamicDrawUsage));
    this.geo.setAttribute('aSize', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    this.geo.setAttribute('aAlpha', new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    this.geo.setDrawRange(0, 0);
    this.mat = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, uniforms: { uScale: { value: 600 } },
    });
    this.points = new THREE.Points(this.geo, this.mat);
    this.points.frustumCulled = false;
    this.points.renderOrder = 5;
    parent.add(this.points);
  }
  // o: { pos:{x,y,z}, vel:{x,y,z}, color, size (blocks), life (s), grav, bounce }
  emit(o) {
    if (this.n >= this.cap) return;
    const i = this.n++;
    const c = o.color instanceof THREE.Color ? o.color : new THREE.Color(o.color ?? 0xffffff);
    this.pos[i * 3] = o.pos.x; this.pos[i * 3 + 1] = o.pos.y; this.pos[i * 3 + 2] = o.pos.z;
    this.vel[i * 3] = o.vel?.x || 0; this.vel[i * 3 + 1] = o.vel?.y || 0; this.vel[i * 3 + 2] = o.vel?.z || 0;
    this.col[i * 3] = c.r; this.col[i * 3 + 1] = c.g; this.col[i * 3 + 2] = c.b;
    this.s0[i] = o.size ?? 0.1; this.size[i] = this.s0[i];
    this.alpha[i] = 1; this.age[i] = 0; this.life[i] = o.life ?? 1;
    this.grav[i] = o.grav ?? 9; this.bounce[i] = o.bounce ?? 0.3;
  }
  // Move the last particle into slot i.
  _kill(i) {
    const l = --this.n;
    if (i !== l) {
      for (let k = 0; k < 3; k++) { this.pos[i * 3 + k] = this.pos[l * 3 + k]; this.vel[i * 3 + k] = this.vel[l * 3 + k]; this.col[i * 3 + k] = this.col[l * 3 + k]; }
      this.size[i] = this.size[l]; this.alpha[i] = this.alpha[l]; this.age[i] = this.age[l]; this.life[i] = this.life[l];
      this.s0[i] = this.s0[l]; this.grav[i] = this.grav[l]; this.bounce[i] = this.bounce[l];
    }
  }
  update(dt, scale) {
    if (scale) this.mat.uniforms.uScale.value = scale;
    for (let i = this.n - 1; i >= 0; i--) {
      this.age[i] += dt;
      const k = this.age[i] / this.life[i];
      if (k >= 1) { this._kill(i); continue; }
      const p = i * 3;
      this.vel[p + 1] -= this.grav[i] * dt;
      this.pos[p] += this.vel[p] * dt; this.pos[p + 1] += this.vel[p + 1] * dt; this.pos[p + 2] += this.vel[p + 2] * dt;
      const fl = floorAt(this.pos[p], this.pos[p + 2]);
      if (this.pos[p + 1] < fl && this.vel[p + 1] < 0) {
        this.pos[p + 1] = fl;
        this.vel[p + 1] *= -this.bounce[i];
        this.vel[p] *= 0.6; this.vel[p + 2] *= 0.6;
      }
      // shrink through the last 40 percent of life and fade through the last 30
      this.size[i] = this.s0[i] * (k > 0.6 ? 1 - (k - 0.6) / 0.4 : 1);
      this.alpha[i] = k > 0.7 ? 1 - (k - 0.7) / 0.3 : 1;
    }
    this.geo.setDrawRange(0, this.n);
    const a = this.geo.attributes;
    a.position.needsUpdate = a.color.needsUpdate = a.aSize.needsUpdate = a.aAlpha.needsUpdate = true;
  }
  clear() { this.n = 0; this.geo.setDrawRange(0, 0); }
}

// Helpers shared by the page and Steve.
export function makeFx(scene) {
  const solid = new Particles(scene, { cap: 1100 });
  const glow = new Particles(scene, { cap: 500, additive: true });
  const rnd = (a, b) => a + Math.random() * (b - a);
  const fx = {
    solid, glow,
    update(dt, scale) { solid.update(dt, scale); glow.update(dt, scale); },
    clear() { solid.clear(); glow.clear(); },
    // block chips: colours from a palette
    chips(pos, palette, n = 8, o = {}) {
      for (let i = 0; i < n; i++) {
        solid.emit({
          pos: { x: pos.x + rnd(-0.25, 0.25), y: pos.y + rnd(-0.25, 0.25), z: pos.z + rnd(-0.25, 0.25) },
          vel: { x: rnd(-1, 1) * (o.speed ?? 1.6), y: rnd(0.6, 2.2) * (o.up ?? 1), z: rnd(-1, 1) * (o.speed ?? 1.6) },
          color: palette[Math.floor(Math.random() * palette.length)], size: o.size ?? rnd(0.06, 0.1), life: o.life ?? rnd(0.7, 1.1), grav: 11,
        });
      }
    },
    dust(pos, n = 6, o = {}) {
      for (let i = 0; i < n; i++) {
        solid.emit({
          pos: { x: pos.x + rnd(-0.12, 0.12), y: pos.y + 0.05, z: pos.z + rnd(-0.12, 0.12) },
          vel: { x: rnd(-0.5, 0.5) + (o.vx || 0), y: rnd(0.2, 0.7), z: rnd(-0.5, 0.5) + (o.vz || 0) },
          color: o.color ?? 0xcfc4b0, size: rnd(0.08, 0.16), life: rnd(0.35, 0.7), grav: -0.5, bounce: 0,
        });
      }
    },
    ring(pos, n = 36, o = {}) {
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2 + rnd(-0.08, 0.08), s = (o.speed ?? 4.2) * rnd(0.8, 1.15);
        solid.emit({
          pos: { x: pos.x + Math.cos(a) * 0.6, y: pos.y + 0.06, z: pos.z + Math.sin(a) * 0.6 },
          vel: { x: Math.cos(a) * s, y: rnd(0.3, 1.1), z: Math.sin(a) * s },
          color: o.color ?? 0xa89c8a, size: rnd(0.09, 0.17), life: rnd(0.5, 0.9), grav: 0.5, bounce: 0,
        });
      }
    },
    sparks(pos, color, n = 10, o = {}) {
      for (let i = 0; i < n; i++) {
        glow.emit({
          pos: { x: pos.x, y: pos.y, z: pos.z },
          vel: { x: rnd(-1, 1) * (o.speed ?? 1.4), y: rnd(0.8, 2.4), z: rnd(-1, 1) * (o.speed ?? 1.4) },
          color, size: rnd(0.05, 0.1), life: rnd(0.5, 1.0), grav: 4,
        });
      }
    },
    splash(pos, n = 12) {
      for (let i = 0; i < n; i++) {
        solid.emit({
          pos: { x: pos.x + rnd(-0.1, 0.1), y: pos.y, z: pos.z + rnd(-0.1, 0.1) },
          vel: { x: rnd(-0.8, 0.8), y: rnd(1.4, 3), z: rnd(-0.8, 0.8) },
          color: i % 3 ? 0x6fa0ee : 0xcfe2ff, size: rnd(0.05, 0.1), life: rnd(0.5, 0.8), grav: 10, bounce: 0,
        });
      }
    },
  };
  return fx;
}
