// The terror kit (v3, after FNAF): what every scare's climax is built from.
//   lunge(R, m, o)        the mob's face driven into the lens from where it stood: ~0.22 s, an overshoot on impact,
//                         then a hold, jittering hard, jaw open, eyes lit, until the static cut
//   splitJaw(m, specs)    the head box cut at the mouth row (the same 1.7.10 UVs), a dark mouth and pixel teeth
//   faceAnchor(m, ...)    where a mob's face is, in its pivot's frame
//   jit(t, seed)          hard random wobble (a value per 1/26 s, interpolated): the animatronic shake
//   screech(...)          the layered sound of the lunge: the mob's own scream, qf.scare.jumpscreech, static, the hit
//   lungeFx(L, t, f)      tear, RGB split and static on the frame; the static cut hides everything for ~0.14 s
//   musicBox(...)         a note-block tune that winds down and stops (the power-out)
//   beats(R)              the randomised build-up: dread lengths +-40%, fake-outs, silences
import { THREE, clamp, lerp, sstep, easeOut, pulse } from "./rig.js";
import { mcBoxGeometry } from "../../lib/mc/mobs.js";
import { VANILLA_MODELS } from "../../lib/mc/vanilla-models.js";

const h1 = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return (s - Math.floor(s)) * 2 - 1; };
// A jerky wobble in -1..1: a new random value every 1/hz s, eased between, so it reads as shaking, not swaying.
export function jit(t, seed = 0, hz = 26) {
  const x = t * hz, i = Math.floor(x), k = x - i, e = k * k * (3 - 2 * k);
  return lerp(h1(i + seed * 101.37), h1(i + 1 + seed * 101.37), e);
}
export const boxOf = (model, part) => { const p = VANILLA_MODELS[model] && VANILLA_MODELS[model].parts[part]; return p && p.boxes[0] ? p.boxes[0].slice() : null; };

// ---- the jaw -------------------------------------------------------------------------------------------------
// specs: [{ part: <Group>, box: [x,y,z,w,h,d,inflate,u,v,mirror,tw,th], rows }]: each part's box is cut `rows` texture
// rows above its bottom; the lower piece hinges at the back. The first spec gets the mouth and teeth.
// Returns set(open 0..1).
export function splitJaw(m, specs, { mouth = 0x0e0101, tongue = 0x3a0505, teeth = 0x8f866a, nTeeth = 4, max = 0.62, lower = true } = {}) {
  const jaws = [];
  const mMouth = new THREE.MeshBasicMaterial({ color: mouth }), mTongue = new THREE.MeshBasicMaterial({ color: tongue }), mTeeth = new THREE.MeshBasicMaterial({ color: teeth });
  for (const mt of [mMouth, mTongue, mTeeth]) mt.userData.noFlash = true;
  specs.forEach((s, si) => {
    const G = s.part; if (!G || !s.box) return;
    const meshes = G.children.filter((o) => o.isMesh);
    if (!meshes.length) return;
    const mat = meshes[0].material;
    const [x, y, z, w, h, d, e = 0, u, v, mir, tw, th] = s.box, r = s.rows;
    for (const o of meshes) o.visible = false;
    const up = new THREE.Mesh(mcBoxGeometry([x, y, z, w, h - r, d, e], [u, v], tw, th, !!mir), mat);
    const jg = mcBoxGeometry([x, y + h - r, z, w, r, d, e], [u, v + h - r], tw, th, !!mir);
    const full = mcBoxGeometry([x, y, z, w, h, d, e], [u, v], tw, th, !!mir);
    for (let i = 12; i < 16; i++) jg.attributes.uv.setXY(i, full.attributes.uv.getX(i), full.attributes.uv.getY(i));   // its underside is the head's
    full.dispose();
    G.add(up);
    const Ys = -(y + h - r) / 16, zf = z / 16, zb = (z + d) / 16, W3 = w / 16, D3 = d / 16;
    const hinge = new THREE.Vector3(0, Ys, zb);
    const jaw = new THREE.Group(); jaw.position.copy(hinge); G.add(jaw);
    const low = new THREE.Mesh(jg, mat); low.position.copy(hinge).negate(); jaw.add(low);
    if (si === 0) {
      const cx = -(x + w / 2) / 16, cz = (zf + zb) / 2;
      const palate = new THREE.Mesh(new THREE.BoxGeometry(W3 - 0.03, 0.035, D3 - 0.03), mMouth); palate.position.set(cx, Ys + 0.0125, cz); G.add(palate);
      const tg = new THREE.Mesh(new THREE.BoxGeometry(W3 - 0.03, 0.035, D3 - 0.03), mTongue); tg.position.set(cx, Ys - 0.0125, cz).sub(hinge); jaw.add(tg);
      // Teeth: a few uneven, yellowed one-pixel pegs (gaps where some are gone), upper hanging, lower standing.
      const px = 1 / 16, slots = Math.max(2, Math.round(w) - 2);
      const pat = [1, 0, 2, 1, 0, 1, 2, 0, 1, 1, 0, 2].slice(0, slots);   // 0: missing, 1: short, 2: long
      let placed = 0;
      pat.forEach((k, i) => {
        if (!k || placed >= nTeeth) return;
        placed++;
        const tx = -(x + 1.5 + i) / 16, hT = px * (k === 2 ? 1.6 : 1);
        const a = new THREE.Mesh(new THREE.BoxGeometry(px * 0.8, hT, px * 0.6), mTeeth); a.position.set(tx, Ys - hT / 2 + 0.004, zf + px * 0.45); G.add(a);
        if (lower && i % 3 === 1) { const b = new THREE.Mesh(new THREE.BoxGeometry(px * 0.8, px, px * 0.6), mTeeth); b.position.set(tx - px, Ys + px / 2 - 0.004, zf + px * 0.45).sub(hinge); jaw.add(b); }
      });
    }
    jaws.push(jaw);
  });
  const set = (open) => { for (const j of jaws) j.rotation.x = -max * clamp(open); };
  set(0);
  return { set, mats: { mouth: mMouth, tongue: mTongue, teeth: mTeeth } };
}

// The centre of a part's box face (front by default), in the mob pivot's frame: where the lunge puts the lens.
// Call after the mob's first anim (rest pose) and placement.
export function faceAnchor(m, part, box, { front = true } = {}) {
  const [x, y, z, w, h, d] = box;
  const p = new THREE.Vector3(-(x + w / 2) / 16, -(y + h / 2) / 16, front ? z / 16 : (z + d / 2) / 16);
  m.pivot.updateMatrixWorld(true);
  part.localToWorld(p);
  return m.pivot.worldToLocal(p);
}

// ---- the lunge ---------------------------------------------------------------------------------------------------
// The scare places the mob where it stands (R.place) every frame; from t0 on, apply(t) takes it over: it rushes
// from that pose to the lens in `rush` seconds (accelerating, so it is fastest as it hits), overshoots to 0.75 of
// `dist`, and holds there shaking until t2 = t0 + rush + hold. dist: lens to face, metres (0.3 fills a 58 deg view
// with an 8 px head). anchor: the face in the pivot's frame (faceAnchor). After t2 the scare owns the mob again.
const _qy = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI);
const _q = new THREE.Quaternion(), _qj = new THREE.Quaternion(), _e = new THREE.Euler(), _v = new THREE.Vector3(), _a = new THREE.Vector3(), _p0 = new THREE.Vector3(), _q0 = new THREE.Quaternion();
export function lunge(R, m, { t0, rush = 0.22, hold = 0.7, cut = 0.14, dist = 0.3, anchor, jitter = 1, seed = 3, roll = 0, side = 0, rise = 0 } = {}) {
  const t1 = t0 + rush, t2 = t1 + hold, t3 = t2 + cut;
  const L = { t0, t1, t2, t3, rush, hold, cut, dist };
  // The pose it rushes from: wherever the scare had it when the lunge began (read once per frame before override).
  L.apply = (t, { from = true } = {}) => {
    if (t < t0) return 0;
    const cam = R.camera, u = clamp((t - t0) / rush);
    const piv = m.pivot;
    if (from) { piv.updateMatrixWorld(true); _p0.copy(piv.position); _q0.copy(piv.quaternion); }
    // Face square to the lens, plus the shake.
    const a = jitter * (0.35 + 0.65 * sstep(0, 1, u));
    _e.set(jit(t, seed) * 0.1 * a, jit(t, seed + 3) * 0.12 * a, (jit(t, seed + 7) * 0.09 + roll) * a, "YXZ");
    _q.copy(cam.quaternion).multiply(_qy).multiply(_qj.setFromEuler(_e));
    const imp = t >= t1 ? Math.exp(-(t - t1) / 0.06) : 0;
    const d = dist * (1 - 0.25 * imp) + jit(t, seed + 11) * 0.025 * a;
    _v.set(jit(t, seed + 13) * 0.02 * a + side * (1 - u), jit(t, seed + 17) * 0.02 * a - rise * (1 - u), -d).applyQuaternion(cam.quaternion).add(cam.position);
    _a.copy(anchor).applyQuaternion(_q);
    _v.sub(_a);
    const k = u * u * (1.4 - 0.4 * u);   // accelerating into the lens
    piv.position.lerpVectors(_p0, _v, k);
    piv.quaternion.slerpQuaternions(_q0, _q, Math.min(1, u * 1.8));
    piv.visible = true;
    return u;
  };
  // How hard the head should shake (metres) for the camera's own shake.
  L.shake = (t) => 0.03 * pulse(t, [t1], 0.12) + 0.012 * (t >= t0 && t < t2 ? 1 : 0);
  return L;
}
// The frame during a lunge: a tear and RGB split on impact, static rising through the hold, the cut.
export function lungeFx(L, t, f, { tear = 1, stat = 1 } = {}) {
  const fx = f.fx || (f.fx = { tear: 0, split: 0, stat: 0 });
  if (t < L.t0) return f;
  const hold = t >= L.t1 && t < L.t2, hit = pulse(t, [L.t1], 0.1);
  const spikes = hold ? Math.max(0, jit(t, 41, 9) * 1.6 - 0.6) ** 2 : 0;   // a burst now and then, clean between
  // The face must read: the tear comes in bursts (one in three frames or so), not as a wash over the whole hold.
  fx.tear = Math.max(fx.tear, tear * (0.3 * hit + (hold ? 0.45 * spikes + 0.3 * sstep(L.t2 - 0.15, L.t2, t) : 0) + (t >= L.t3 ? 0.4 * Math.exp(-(t - L.t3) / 0.15) : 0)));
  fx.split = Math.max(fx.split, 0.45 * hit + (hold ? 0.08 + 0.3 * spikes : 0) + (t >= L.t3 ? 0.5 * Math.exp(-(t - L.t3) / 0.2) : 0));
  fx.stat = Math.max(fx.stat, stat * (hold ? 0.03 + 0.2 * sstep(L.t2 - 0.25, L.t2, t) + 0.1 * spikes : 0));
  if (t >= L.t2 && t < L.t3) { f.cut = 1; fx.stat = 1; }
  return f;
}
// The loudest moment on the page: the mob's own scream, the recorded screech, a static burst and the sub hit, all
// at once on the first frame of the rush; static under the hold and a louder burst on the cut.
export function screech(L, own = [], { volume = 1 } = {}) {
  const v = volume;
  return {
    sounds: [
      [L.t0 - 0.01, "qf.scare.jumpscreech", { volume: 1.7 * v }],
      ...own.map(([name, o = {}], i) => [L.t0 + 0.005 * i, name, { volume: 1.5 * v, ...o }]),
      [L.t0, "qf.scare.hit", { volume: 1.3 * v }],
      [L.t0 + 0.01, "qf.scare.stinger", { volume: 1.0 * v }],
      [L.t1, "qf.scare.crunch", { volume: 0.9 * v }],
      [L.t2, "qf.scare.hit", { volume: 1.0 * v }]
    ],
    loops: [[L.t0, L.t3, "qf.scare.static", { volume: 1.6 * v, fadeIn: 0.03, fadeOut: 0.04 }], [L.t2, L.t3 + 0.05, "qf.scare.static", { volume: 2.6 * v, fadeIn: 0.0, fadeOut: 0.03 }]]
  };
}

// ---- the build-up -------------------------------------------------------------------------------------------------
// R.vary(x, f) is x +- f (40% by default); R.chance(p). beats(R) hands out times along a growing timeline:
//   const B = beats(R, 0.9); B.wait(R.vary(1.8)); const tGroan = B.now; ...
export function beats(R, start = 0) {
  const B = { now: start, marks: {} };
  B.wait = (s) => { B.now += Math.max(0, s); return B.now; };
  B.mark = (name, at = B.now) => { B.marks[name] = at; return at; };
  return B;
}
// Silence: every loop stops and the ambience goes to nothing; one small sound may follow (a breath, a click, a note).
export function silence(t, { fade = 0.12 } = {}) { return [t, "@silence", { s: fade }]; }

// A note-block tune (note.harp: pitch 2^((n - 12) / 12), n 0..24) that winds down: each note a little later and lower
// than written, like a music box running out. Returns { sounds, end }.
export function musicBox(t0, notes, { step = 0.32, wind = 0.06, sag = 0.012, stopAt = notes.length, volume = 0.55, at } = {}) {
  const out = [];
  let t = t0;
  for (let i = 0; i < Math.min(stopAt, notes.length); i++) {
    const n = notes[i];
    if (n != null) out.push([t, "note.harp", { volume: volume * (1 - 0.25 * i / notes.length), pitch: Math.pow(2, (n - 12) / 12) * (1 - sag * i), at, reverb: 0.6 }]);
    t += step * (1 + wind * i * i / notes.length);
  }
  return { sounds: out, end: t };
}
// The kill's scream: a man dying (the recorded set), with the game's own death sound under it.
export function deathScream(t, { volume = 1.25, under = true } = {}) {
  return [[t, "qf.scare.death_scream", { volume }], ...(under ? [[t + 0.02, "game.player.hurt", { volume: 0.7 }]] : [])];
}
// A single-frame glimpse: true for `len` seconds after each time.
export const glimpse = (t, times, len = 0.07) => times.some((x) => t >= x && t < x + len);
