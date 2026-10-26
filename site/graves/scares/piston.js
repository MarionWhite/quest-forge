// The piston trap (shared): a redstone click under your feet; the head tilts down to look; the 2 x 2 patch of real
// floor you stand on is yanked sideways by sticky pistons (2 ticks, as in 1.7.10), and you drop 6 to 8 blocks into a
// room carved under the corridor. From the bottom you see the hole, the pistons in the floor round it and the
// corridor's torchlight. The room is real (carved out of the Krypt's grid), so it is dressed in the segment's rock.
import { THREE, clamp, lerp, sstep, tex, blockTexName, easeOut } from "./rig.js";

export const GRAV = 32;   // m/s^2: 0.08 blocks a tick squared

// Piston parts in a frame where +y points at the block it pushes (BoxGeometry face order px, nx, py, ny, pz, nz).
function remapV(geo, faces, v0, v1) {   // squeeze the side faces' v into [v0, v1] (a strip of piston_side)
  const uv = geo.attributes.uv;
  for (const f of faces) for (let i = f * 4; i < f * 4 + 4; i++) uv.setY(i, v0 + uv.getY(i) * (v1 - v0));
}
function pistonMats(T, amb, KRbake) {
  const lam = (map) => { const m = new THREE.MeshLambertMaterial({ map }); if (KRbake) KRbake(m, { fixed: amb }); return m; };
  return { side: lam(T.side), bottom: lam(T.bottom), inner: lam(T.inner), sticky: lam(T.sticky) };
}

// web: the bottom two blocks under the hole are cobweb (the fall stops in it, no fall damage, then a slow sink).
// ri, rk: the room's reach beyond the patch, across and along (it shrinks to fit the rock; if nothing fits, it is
// carved at this size anyway).
export async function pistonTrap(R, { click = 1.2, open = 1.95, D = 7, web = false, ri: RI = 3, rk: RK = 2 } = {}) {
  const [side, bottom, inner, sticky] = await Promise.all(["piston_side", "piston_bottom", "piston_inner", "piston_top_sticky"].map((n) => tex(n)));
  const T = { side, bottom, inner, sticky };
  const r = R.r, f = R.f;
  // Block offsets: i across the corridor (along r), k along it (along f), j up from the floor (j = -1 is the floor).
  const B = { x: Math.floor(R.O.x), y: R.O.y, z: Math.floor(R.O.z) };
  const blk = (i, j, k) => [B.x + r.x * i + f.x * k, B.y + j, B.z + r.z * i + f.z * k];
  const cen = (i, j, k) => { const b = blk(i, j, k); return new THREE.Vector3(b[0] + 0.5, b[1] + 0.5, b[2] + 0.5); };
  const loc = (i, j, k) => R.toLocal(cen(i, j, k));
  const d0 = R.toLocal({ x: B.x + 0.5, y: 0, z: B.z + 0.5 });   // where block (0, ., 0)'s centre is, locally
  const a = d0.x > 0 ? -1 : 0, b = d0.z > 0 ? -1 : 0;   // the 2 x 2 patch: columns a, a+1 and rows b, b+1, round you
  const solidB = (i, j, k) => { const c = cen(i, j, k); return R.solidW(c.x, c.y, c.z) && R.blockW(c.x, c.y, c.z) !== "bedrock"; };
  // The room: as big and as deep as the rock under you allows (never into another space).
  let room = null;
  for (const [dd, ri, rk] of [[D, RI, RK], [D - 1, RI, RK], [D, 2, Math.min(RK, 2)], [D, 2, 1], [D - 1, 2, 1], [D - 2, 2, 1]]) {
    let ok = true;
    for (let i = a - ri - 1; i <= a + 1 + ri + 1 && ok; i++) for (let k = b - rk - 1; k <= b + 1 + rk + 1 && ok; k++) for (let j = -dd - 1; j <= -2; j++) if (!solidB(i, j, k)) { ok = false; break; }
    for (let i = a - ri; i <= a + 1 + ri && ok; i++) for (let k = b - rk; k <= b + 1 + rk && ok; k++) if (!solidB(i, -1, k)) ok = false;
    if (ok) { room = { D: dd, ri, rk }; break; }
  }
  const fits = !!room;
  if (!room) room = { D: D - 1, ri: RI, rk: RK };
  const Dp = room.D;
  // The real floor's look where our pieces go, read before anything is carved.
  const KRbake = R.patchBake;
  const up = new THREE.Vector3(0, 1, 0);
  const bakeTop = (i, k) => R.bakeAt(cen(i, -1, k).add(new THREE.Vector3(0, 0.5, 0)), up) || new THREE.Vector3(0.2, 0.19, 0.18);
  const floorTex = {};
  const texFor = async (i, k) => { const c = cen(i, -1, k), n = R.blockW(c.x, c.y, c.z); const key = blockTexName(n); return floorTex[key] || (floorTex[key] = await tex(key)); };

  const group = new THREE.Group(); group.visible = false; R.add(group);
  const dirOf = (s) => new THREE.Vector3(r.x * s, 0, r.z * s);   // s = +1: pushing toward +r
  const q = (s) => new THREE.Quaternion().setFromUnitVectors(up, dirOf(s));
  const units = [];
  for (const k of [b, b + 1]) for (const [s, ib, ih, ip] of [[1, a - 2, a - 1, a], [-1, a + 3, a + 2, a + 1]]) {
    const amb = bakeTop(ip, k), mats = pistonMats(T, amb, KRbake);
    // Base: sides piston_side, back piston_bottom, front piston_inner (the head is out).
    const base = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), [mats.side, mats.side, mats.inner, mats.bottom, mats.side, mats.side]);
    base.position.copy(cen(ib, -1, k)); base.quaternion.copy(q(s)); group.add(base);
    // Head: the plate (sticky face forward) and the arm back into the base.
    const head = new THREE.Group(); head.quaternion.copy(q(s));
    const plateG = new THREE.BoxGeometry(1, 0.25, 1); remapV(plateG, [0, 1, 4, 5], 0.75, 1);
    const plate = new THREE.Mesh(plateG, [mats.side, mats.side, mats.sticky, mats.sticky, mats.side, mats.side]); plate.position.y = 0.375;
    const armG = new THREE.BoxGeometry(0.25, 1, 0.25); remapV(armG, [0, 1, 4, 5], 0, 0.75);
    const arm = new THREE.Mesh(armG, mats.side); arm.position.y = -0.25;
    head.add(plate, arm); head.position.copy(cen(ih, -1, k)); group.add(head);
    // The floor block it holds.
    const ft = await texFor(ip, k);
    const blkM = new THREE.MeshLambertMaterial({ map: ft }); if (KRbake) KRbake(blkM, { fixed: amb });
    const fb = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), blkM); fb.position.copy(cen(ip, -1, k)); group.add(fb);
    units.push({ s, head, fb, h0: head.position.clone(), b0: fb.position.clone() });
  }
  const holeW = cen(a, -1, b).add(cen(a + 1, -1, b + 1)).multiplyScalar(0.5);
  const hole = R.toLocal(holeW);
  // Light down the hole from the corridor, and a little in the room so it is not black.
  const holeLight = R.ownLight(R.light(0xffc890, 0, 9, 1.2));
  const roomLight = R.ownLight(R.light(0x9aa0b0, 0, 8, 1.4));

  const carve = () => {
    const box = (p, q2) => R.carveW([Math.min(p[0], q2[0]), Math.min(p[1], q2[1]), Math.min(p[2], q2[2])], [Math.max(p[0], q2[0]), Math.max(p[1], q2[1]), Math.max(p[2], q2[2])]);
    box(blk(a - room.ri, -Dp, b - room.rk), blk(a + 1 + room.ri, -2, b + 1 + room.rk));   // the room
    box(blk(a - 2, -1, b), blk(a + 3, -1, b + 1));   // the patch and the pistons' slots
  };
  const tFall = open + 0.06, stopEye = web ? -Dp + 2 + R.eye - 0.3 : -Dp + R.eye;
  const land = tFall + Math.sqrt(2 * (R.eye - stopEye) / GRAV);
  const sounds = [
    [click, "random.click", { at: [hole.x, -0.5, hole.z], volume: 0.6, pitch: 0.6 }],
    [open, "tile.piston.in", { at: [hole.x, -0.5, hole.z], volume: 1, pitch: 0.9 }],
    [open + 0.02, "tile.piston.in", { at: [hole.x + 1, -0.5, hole.z], volume: 0.8, pitch: 0.85 }],
    [tFall + 0.02, "qf.scare.fall", { volume: 1 }],
    web ? [land, "step.cloth", { volume: 1, pitch: 0.7 }] : [land, "game.player.hurt.fall.big", { volume: 1 }]
  ];
  // The camera through it: tilt down to the feet, fall through the hole (drifting to its middle), land in a crouch.
  function cam(t, c) {
    const tilt = sstep(click + 0.1, click + 0.7, t);
    c.pitch = lerp(c.pitch, -1.15, tilt); c.yaw = lerp(c.yaw, c.yaw * 0.6, tilt);
    if (t < tFall) return c;
    const dt = t - tFall, k = clamp(dt / (land - tFall));
    c.x = lerp(c.x, hole.x, easeOut(k)); c.z = lerp(c.z, hole.z, easeOut(k));
    c.y = Math.max(R.eye - 0.5 * GRAV * dt * dt, stopEye);
    c.fov += 9 * sstep(tFall, land, t) * (1 - sstep(land, land + 0.5, t));
    c.roll += 0.12 * Math.sin(k * Math.PI);
    if (t >= land && web) {   // caught: a jolt, then sinking slowly through the strands
      const l = t - land;
      c.y = stopEye - Math.min(0.5, 0.1 * l) - 0.12 * Math.sin(clamp(l / 0.25) * Math.PI) * Math.exp(-l * 4);
    } else if (t >= land) {   // the landing: knees give, the head drops and comes back
      const l = t - land;
      c.y = -Dp + R.eye - 0.42 * Math.sin(clamp(l / 0.45) * Math.PI) * Math.exp(-l * 1.5);
      c.pitch = lerp(c.pitch, -0.55, Math.exp(-l * 3) * (1 - Math.exp(-l * 30)));
    }
    return c;
  }
  function update(t, f) {
    if (t >= open) R.once("piston-carve", carve);
    group.visible = t >= open;
    const s = clamp((t - open) / 0.1);   // 2 ticks
    for (const u of units) {
      const d = dirOf(u.s).multiplyScalar(-s);
      u.head.position.copy(u.h0).add(d); u.fb.position.copy(u.b0).add(d);
      u.head.visible = s < 1;
    }
    R.L(hole.x, -0.6, hole.z, holeLight.position); holeLight.intensity = t >= open ? 2.2 : 0;
    R.L(hole.x, -Dp + 2.2, hole.z, roomLight.position); roomLight.intensity = t >= open ? 0.6 : 0;
  }
  return { fits, D: Dp, room, hole, click, open, tFall, land, stopEye, sounds, cam, update, blk, cen, loc, a, b,
    roomBox: { i0: a - room.ri, i1: a + 1 + room.ri, k0: b - room.rk, k1: b + 1 + room.rk, y: -Dp } };
}
