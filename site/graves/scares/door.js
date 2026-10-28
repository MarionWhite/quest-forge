// A 1.7.10 wooden door in the Krypt's wall (round 8, the Zombie): set into a side wall where the visitor cannot see it
// when the scare starts (behind and beside), with a short passage carved behind it. A zombie on the other side can
// batter it (it judders, the block-crack overlay grows stage by stage, grit sifts from the lintel) and break it (it
// vanishes into the block-break particles of its own texture, as EntityAIBreakDoor and RenderGlobal do).
//   const D = await wallDoor(R, { side, zMin, zMax, depth })   null if no wall spot fits
//     D.side      +1 right, -1 left (the wall it is in); D.face: local x of the wall face; D.z: local z of its middle
//     D.in(d)     local { x, z } d metres into the passage from the wall face (d < 0: out in the corridor)
//     D.carve()   carve the doorway and the passage (do it in build, before the first frame: nothing on screen)
//     D.update(t, { crack, bulge, gone })   crack 0..1 (ten stages), bulge 0..1 (a blow from behind), gone (broken)
//     D.breakAt(t0)   the break particles from t0 (call once at build); D.solid(worldVec): the panel, for sight lines
import { THREE, clamp, tex, loadImg } from "./rig.js";
import { mulberry } from "./common.js";

async function rawTex(name) {
  const im = await loadImg(name); if (!im) return null;
  const t = new THREE.Texture(im); t.colorSpace = THREE.NoColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.needsUpdate = true;
  return t;
}

export async function wallDoor(R, { side = 0, zMin = -1.6, zMax = -0.4, depth = 3, avoidTorch = 1.1 } = {}) {
  const sides = side ? [side] : (R.wallL <= R.wallR ? [-1, 1] : [1, -1]);
  let spot = null;
  for (const s of sides) {
    const wall = s < 0 ? R.wallL : R.wallR;
    if (wall > 9) continue;
    const zs = [];
    for (let z = (zMin + zMax) / 2, k = 0; k < 12; k++) { const zz = z + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 0.25; if (zz >= zMin - 1e-6 && zz <= zMax + 1e-6) zs.push(zz); }
    for (const z of zs) {
      // the door block (two high) and the lintel solid; the corridor in front of it open; floor under both
      const w = R.L(s * (wall + 0.5), 0.5, z), bx = Math.floor(w.x), by = Math.floor(w.y), bz = Math.floor(w.z);
      const c = R.toLocal(new THREE.Vector3(bx + 0.5, by + 0.5, bz + 0.5));
      const face = c.x - s * 0.5;
      if (Math.abs(Math.abs(face) - wall) > 0.25) continue;
      const S = (dx, y) => R.solid(c.x + s * dx, y, c.z);
      if (!S(0, 0.5) || !S(0, 1.5) || !S(0, 2.5) || S(-1, 0.5) || S(-1, 1.5) || !S(0, -0.5) || !S(-1, -0.5)) continue;
      // the wall face either side of it is wall (not an alcove or a pillar's edge)
      if (!R.solid(c.x, 1.0, c.z - 1) || !R.solid(c.x, 1.0, c.z + 1)) continue;
      if (R.torches.some((t) => Math.abs(t.l.x - face) < 0.8 && Math.abs(t.l.z - c.z) < avoidTorch)) continue;
      spot = { s, bx, by, bz, c, face }; break;
    }
    if (spot) break;
  }
  if (!spot) return null;
  const { s, bx, by, bz, c, face } = spot;
  const dW = R.dirW(s, 0, 0), dx = Math.round(dW[0]), dz = Math.round(dW[2]);
  // The light the wall has there, before it is cut (the door is lit like the stone round it).
  const pW = R.L(face - s * 0.02, 1.0, c.z), nW = new THREE.Vector3(...R.dirW(-s, 0, 0));
  const amb = R.bakeAt(pW, nW) || new THREE.Vector3(0.25, 0.22, 0.2);
  const [tl, tu] = await Promise.all([tex("k:door_wood_lower"), tex("k:door_wood_upper")]);
  const cracks = await Promise.all([...Array(10)].map((_, i) => rawTex("destroy_stage_" + i)));
  const T = 3 / 16;
  // The panel stands at the passage side of the door block (set back 13/16 in its frame, as a placed door is).
  const xPanel = face + s * (1 - T / 2);
  const g = new THREE.Group(); R.add(g);
  const hingeZ = c.z - 0.5 + 0.02;   // hinged on the near-back edge
  const hinge = new THREE.Group(); g.add(hinge);
  const mk = (t, y) => {
    const m = new THREE.MeshLambertMaterial({ map: t });
    if (R.patchBake) R.patchBake(m, { fixed: amb.clone().multiplyScalar(0.9) });
    const b = new THREE.Mesh(new THREE.BoxGeometry(T, 1, 1), m); b.position.set(0, y, -(0.5 - 0.02)); hinge.add(b); return b;
  };
  const lower = mk(tl, 0.5), upper = mk(tu, 1.5);
  // the crack overlay on the corridor face, multiplied into the door as the game blends it (dst * src * 2)
  const cMat = new THREE.MeshBasicMaterial({ map: cracks[0], transparent: true, alphaTest: 0.1, depthWrite: false, blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor, blendDst: THREE.SrcColorFactor, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4, side: THREE.DoubleSide, fog: false });
  const crackQ = [0.5, 1.5].map((y) => { const q = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), cMat); q.rotation.y = Math.PI / 2; q.position.set(-s * (T / 2 + 0.003), y, -(0.5 - 0.02)); q.visible = false; hinge.add(q); return q; });
  const place = (bul) => {
    R.at(g, xPanel, by - R.O.y, hingeZ);
    g.rotation.y = R.yaw0;
    // a blow from behind: the panel bows out into the corridor and the latch side jumps on its hinges
    hinge.position.set(-s * 0.035 * bul, 0, 0);
    hinge.rotation.y = s * 0.06 * bul;
  };
  place(0);
  const D = {
    side: s, face, z: c.z, x: c.x, floorY: by - R.O.y, amb,
    in: (d) => ({ x: face + s * d, z: c.z }),
    carve() { R.carveW([Math.min(bx, bx + dx * depth), by, Math.min(bz, bz + dz * depth)], [Math.max(bx, bx + dx * depth), by + 1, Math.max(bz, bz + dz * depth)]); },
    update(t, { crack = 0, bulge = 0, gone = false } = {}) {
      g.visible = !gone;
      if (gone) return;
      place(bulge);
      const st = Math.min(9, Math.floor(clamp(crack) * 10));
      const on = crack > 0.001;
      for (const q of crackQ) q.visible = on;
      if (on && cracks[st] && cMat.map !== cracks[st]) cMat.map = cracks[st];
    },
    solid(w) {
      if (!g.visible) return false;
      const l = R.toLocal(w);
      return Math.abs(l.x - xPanel) < T / 2 + 0.02 && Math.abs(l.z - c.z) < 0.5 && l.y > D.floorY && l.y < D.floorY + 2;
    }
  };
  // ---- the break: 4x4x4 bits of the door's texture per block, as RenderGlobal.addBlockDestroyEffects throws them ----
  D.breakAt = (t0, { out = 2.2, n = 64 } = {}) => {
    const rnd = mulberry(bx * 31 + bz * 17 + 5);
    const N = n;
    const geo = new THREE.InstancedBufferGeometry();
    const base = new THREE.PlaneGeometry(1, 1);
    geo.index = base.index; geo.setAttribute("position", base.attributes.position); geo.setAttribute("uv", base.attributes.uv);
    const iPos = new THREE.InstancedBufferAttribute(new Float32Array(N * 3), 3), iUv = new THREE.InstancedBufferAttribute(new Float32Array(N * 3), 3), iSize = new THREE.InstancedBufferAttribute(new Float32Array(N), 1);
    iPos.setUsage(THREE.DynamicDrawUsage); iSize.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute("iPos", iPos); geo.setAttribute("iUv", iUv); geo.setAttribute("iSize", iSize);
    geo.instanceCount = 0;
    const mat = new THREE.ShaderMaterial({
      uniforms: { tLow: { value: tl }, tUp: { value: tu }, uLight: { value: new THREE.Color(amb.x, amb.y, amb.z).multiplyScalar(1.4) } },
      vertexShader: "attribute vec3 iPos; attribute vec3 iUv; attribute float iSize; varying vec2 vUv; varying float vUp; void main(){ vec4 mv = viewMatrix * vec4(iPos, 1.0); mv.xy += position.xy * iSize; gl_Position = projectionMatrix * mv; vUv = iUv.xy + uv * 0.25; vUp = iUv.z; }",
      fragmentShader: "uniform sampler2D tLow; uniform sampler2D tUp; uniform vec3 uLight; varying vec2 vUv; varying float vUp; void main(){ vec4 c = vUp > 0.5 ? texture2D(tUp, vUv) : texture2D(tLow, vUv); if (c.a < 0.1) discard; gl_FragColor = vec4(c.rgb * uLight, 1.0); }"
    });
    const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; R.add(mesh);
    const bits = [];
    for (let i = 0; i < N; i++) {
      const up = i >= N / 2 ? 1 : 0;
      const p = [xPanel + (rnd() - 0.5) * 0.3, D.floorY + up + rnd(), c.z + (rnd() - 0.5) * 0.95];
      const v = [-s * (out * (0.4 + rnd())) + (rnd() - 0.5) * 1.2, (rnd() - 0.3) * 2.4, (rnd() - 0.5) * 2.0];
      bits.push({ p, v, life: 0.7 + rnd() * 0.9, size: (0.05 + rnd() * 0.05), uv: [Math.floor(rnd() * 4) * 0.25, Math.floor(rnd() * 4) * 0.25, up], d: rnd() * 0.05 });
    }
    bits.forEach((b, i) => { iUv.setXYZ(i, b.uv[0], b.uv[1], b.uv[2]); });
    iUv.needsUpdate = true;
    const wv = new THREE.Vector3();
    return (t) => {
      let k = 0;
      for (const b of bits) {
        const a = t - t0 - b.d; if (a < 0 || a > b.life + 1.2) continue;
        const tg = Math.max(0, (Math.sqrt(b.v[1] * b.v[1] + 2 * 14 * Math.max(0, b.p[1] - D.floorY - 0.03)) + b.v[1]) / 14);   // when it lands
        const ta = Math.min(a, tg), drag = (1 - Math.exp(-ta * 2.5)) / 2.5;
        const y = a < tg ? b.p[1] + b.v[1] * a - 7 * a * a : D.floorY + 0.03;
        R.L(b.p[0] + b.v[0] * drag, y, b.p[2] + b.v[2] * drag, wv);
        iPos.setXYZ(k, wv.x, wv.y, wv.z); iSize.setX(k, b.size * (a > b.life ? clamp(1 - (a - b.life) / 1.2) : 1));
        iUv.setXYZ(k, b.uv[0], b.uv[1], b.uv[2]);
        k++;
      }
      geo.instanceCount = k; iPos.needsUpdate = true; iSize.needsUpdate = true; iUv.needsUpdate = true;
      mesh.visible = k > 0;
    };
  };
  return D;
}
