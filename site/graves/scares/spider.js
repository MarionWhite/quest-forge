// Spider (round 8, the owner's script beat by beat). The walk stops under it: it is on the ceiling just behind you,
// out of sight up there. It hisses (mob.spider.say). You look over your left shoulder: the corridor behind, nothing.
// Over your right: nothing. While you look, it creeps forward over the ceiling (its steps, faint) to above the space
// in front of you. You face forward again. A step up there, and grit trickles down in front of your face. You look
// up, slowly. It is there, upside down on the stone, its eyes on you (they glow, as in the game). It sees you see it:
// a low hiss, the legs draw in, the fangs (the two pale pixels on the 1.7.10 face, cut free here) spread. About a
// second, and it springs off the ceiling at your face. Its legs close round your head; you thrash; it bites; you go
// over backwards and it rides you down to the floor, and on your back you look up into its face as it tears at you,
// blood flying, the hearts emptying, your scream, until you die.
// (In 1.7.10 a spider climbs walls but does not walk ceilings; the owner's script puts it overhead, so it is on the
// ceiling, as in round 7. Everything else is vanilla: the model and texture, the glowing eyes layer, its sounds, the
// leap at its target.)
import { THREE, track, clamp, lerp, sstep, pulse } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs, halo, floorFall } from "./common.js";
import { boxOf, faceAnchor, silence, deathScream } from "./fnaf.js";
import { roar, blow, kick } from "./story.js";
import { mcBoxGeometry } from "../../lib/mc/mobs.js";

// A sub-box of a model box whose six faces sample the whole box's texture where they lie (the cut-free pieces keep
// the texture the whole box had there). box, sub: [x, y, z, w, h, d] in model pixels; uv, tw, th as the box's.
function subBoxGeo(box, sub, uv, tw, th) {
  const full = mcBoxGeometry(box, uv, tw, th, false), g = mcBoxGeometry(sub, uv, tw, th, false);
  const P = full.attributes.position, U = full.attributes.uv, p = g.attributes.position, u = g.attributes.uv;
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), q = new THREE.Vector3(), e1 = new THREE.Vector3(), e2 = new THREE.Vector3();
  for (let f = 0; f < 6; f++) {
    const i0 = f * 4;
    a.fromBufferAttribute(P, i0); b.fromBufferAttribute(P, i0 + 1); c.fromBufferAttribute(P, i0 + 3);
    e1.subVectors(b, a); e2.subVectors(c, a);
    for (let i = 0; i < 4; i++) {
      q.fromBufferAttribute(p, i0 + i).sub(a);
      const s = q.dot(e1) / e1.lengthSq(), t = q.dot(e2) / e2.lengthSq();
      u.setXY(i0 + i, U.getX(i0) + s * (U.getX(i0 + 1) - U.getX(i0)) + t * (U.getX(i0 + 3) - U.getX(i0)), U.getY(i0) + s * (U.getY(i0 + 1) - U.getY(i0)) + t * (U.getY(i0 + 3) - U.getY(i0)));
    }
  }
  full.dispose();
  return g;
}
// The spider's head re-cut: the front of its bottom two rows (where the texture has its fangs) becomes two mandibles,
// hinged at their outer top edges, that spread apart and snap shut; a dark mouth behind them. Returns set(open 0..1).
function mandibles(m) {
  const head = m.parts.head; if (!head) return () => {};
  const meshes = head.children.filter((o) => o.isMesh); if (!meshes.length) return () => {};
  const mat = meshes[0].material, B = [-4, -4, -8, 8, 8, 8], UV = [32, 4];
  for (const o of meshes) o.visible = false;
  const W3 = (x, y, z) => new THREE.Vector3(-x / 16, -y / 16, z / 16);
  head.add(new THREE.Mesh(subBoxGeo(B, [-4, -4, -8, 8, 6, 8], UV, 64, 32), mat));
  head.add(new THREE.Mesh(subBoxGeo(B, [-4, 2, -5, 8, 2, 5], UV, 64, 32), mat));
  const mouth = new THREE.MeshBasicMaterial({ color: 0x2a0303 }); mouth.userData.noFlash = true;
  const cav = new THREE.Mesh(new THREE.BoxGeometry(6 / 16, 1.6 / 16, 2.6 / 16), mouth); cav.position.copy(W3(0, 3, -6.6)); head.add(cav);
  // The mandibles catch more of the light than the face (the fang pixels must read); a pale fang tip under each.
  const mMat = mat.clone(); if (mMat.emissive) { mMat.emissiveIntensity = 0.5; m.ownMats = (m.ownMats || []).filter((x) => x !== mMat); }
  const fangMat = new THREE.MeshBasicMaterial({ color: 0x8f877a }); fangMat.userData.noFlash = true;
  const pieces = [[-4, 1, -2.5], [0, -1, 2.5]].map(([x0, s, fx]) => {
    const hinge = W3(x0 === -4 ? -4 : 4, 2, -6.5);
    const hg = new THREE.Group(); hg.position.copy(hinge); head.add(hg);
    const ms = new THREE.Mesh(subBoxGeo(B, [x0, 2, -8, 4, 2, 3], UV, 64, 32), mMat); ms.position.copy(hinge).negate(); hg.add(ms);
    const tip = new THREE.Mesh(new THREE.BoxGeometry(1 / 16, 1.6 / 16, 1 / 16), fangMat); tip.position.copy(W3(fx, 4.75, -7.6)).sub(hinge); hg.add(tip);
    return { hg, s };
  });
  const set = (k, lit = 0.15) => { for (const { hg, s } of pieces) { hg.rotation.z = s * 0.62 * k; hg.rotation.x = 0.18 * k; } fangMat.color.setRGB(0.56, 0.53, 0.48).multiplyScalar(clamp(0.25 + lit * 3, 0.25, 1)); mMat.emissiveIntensity = clamp(lit * 3, 0.12, 0.6); };
  return set;
}

export default {
  death: "Steve was slain by Spider",
  async build(R) {
    const eye = R.eye;
    // ---- where it is: on the ceiling, just behind you when the walk stops; it creeps to above the space in front ----
    const sx = R.wallL < R.wallR ? -0.18 : 0.18;
    const ceilAt = (x, z) => Math.min(9, 1.6 + R.ray(x, 1.6, z, 0, 1, 0, 12));
    // The perch: flat stone (no shaft or vault over it), at the height of the ceiling over you, about 60 degrees up.
    const cHere = ceilAt(sx, 0);
    let best = null;
    for (let z = 0.7; z <= 3.21; z += 0.1) {
      const c = ceilAt(sx, z), flat = Math.abs(c - ceilAt(sx, z - 0.45)) < 0.2 && Math.abs(c - ceilAt(sx, z + 0.45)) < 0.2 && Math.abs(c - ceilAt(sx + 0.4, z)) < 0.2 && Math.abs(c - ceilAt(sx - 0.4, z)) < 0.2;
      const ideal = clamp((c - 0.6 - eye) * 0.58, 0.85, 3.2);
      const score = Math.abs(z - ideal) + (flat ? 0 : 2) + (Math.abs(c - cHere) < 0.2 ? 0 : 1);
      if (!best || score < best.score) best = { z, c, score };
    }
    const sz = best.z, ceil = best.c;
    const bz = -clamp((ceil - 1.0 - eye) / Math.tan(1.0), 0.35, 1.4);      // behind: steep enough to stay out of frame
    const sp = R.mob("Spider", { amb: [0.02, 0.02, 0.02], own: true });
    const fangs = mandibles(sp);
    // the glowing eyes layer sits on the same faces as the re-cut head: draw it just in front (no z-fighting)
    for (const mt of sp.mats.slice(1)) { mt.polygonOffset = true; mt.polygonOffsetFactor = -1; mt.polygonOffsetUnits = -4; }
    const legDonor = R.mob("Spider"); legDonor.pivot.visible = false;
    const headBox = boxOf("spider", "spiderHead");
    sp.anim(0, 0, { walk: 0 }); R.place(sp, 0, 0, 0, 0);
    const anchor = faceAnchor(sp, sp.parts.head, headBox);               // its face, in its own frame
    const eyeGlow = [halo(R, new THREE.Color(1, 0.1, 0.05), 0.16), halo(R, new THREE.Color(1, 0.1, 0.05), 0.16)];

    // ---- the dice -----------------------------------------------------------------------------------------------
    const tSay = 1.0 + R.vary(0.35, 0.5);
    const tL0 = tSay + R.vary(0.3, 0.3), tL1 = tL0 + 0.55, tL2 = tL1 + R.vary(0.5, 0.3);       // over the left shoulder
    const tR1 = tL2 + R.vary(0.95, 0.15), tR2 = tR1 + R.vary(0.5, 0.3);                     // over the right
    const tF1 = tR2 + 0.6;                                                                  // forward again
    const tDust = tF1 + R.vary(0.45, 0.3);                                                  // a step up there; grit falls
    const tUp0 = tDust + 0.95, tUp1 = tUp0 + R.vary(2.7, 0.12);                              // the slow look up
    const LS = R.vary(2.15, 0.08), RS = -R.vary(2.25, 0.08);
    const yawK = track([[0, 0], [tL0, 0], [tL1, LS, "s"], [tL2, LS + 0.05, "l"], [tR1, RS, "s"], [tR2, RS - 0.04, "l"], [tF1, 0, "s"]]);
    // its head (the face) on the ceiling at the perch, in local terms, for the look
    const perchPose = (t) => ({ x: sx, y: ceil, z: sz, yaw: R.yawTo(sx, sz, 0, 0) + 0.06 * Math.sin(t * 0.7), pitch: -0.42 });
    R.place(sp, sx, ceil, sz, R.yawTo(sx, sz, 0, 0), -0.42, Math.PI); sp.anim(0, 0, { walk: 0.05 }); sp.pivot.updateMatrixWorld(true);
    const hw = new THREE.Vector3(-(headBox[0] + headBox[3] / 2) / 16, -(headBox[1] + headBox[4] / 2) / 16, (headBox[2] + headBox[5] / 2) / 16);
    sp.parts.head.localToWorld(hw); const hL = R.toLocal(hw);
    const pUp = clamp(R.pitchTo(0, eye, 0, hL.x, hL.y, hL.z), 0.6, 1.3), yUp = R.yawTo(0, 0, hL.x, hL.z) * 0.6;
    // (up slowly: a hesitant start, steady, and slowing as it nears the stone)
    const pitchK = track([[0, -0.02], [tL0, -0.02], [tL1, -0.07], [tL2, -0.06], [(tL2 + tR1) / 2, -0.01], [tR1, -0.07], [tR2, -0.06], [tF1, -0.03], [tDust + 0.35, -0.06], [tUp0, -0.05],
      [tUp0 + 0.5, 0.06, "i"], [tUp1 - 0.7, pUp - 0.2, "l"], [tUp1, pUp, "o"]]);
    // When the face comes into frame on the way up (24 degrees under the top edge), it sees you see it.
    let tSee = tUp1;
    for (let t = tUp0; t <= tUp1; t += 0.01) if (pUp - pitchK(t) < 0.5 - 0.06 && hL.y - eye > 0) { tSee = t; break; }
    const leapD = Math.hypot(hL.x, hL.y - eye, hL.z);
    const tLeap = tSee + R.vary(1.05, 0.12), tK = tLeap + clamp(0.18 + 0.045 * leapD, 0.26, 0.45);   // seen a second; the leap
    const tFall = tK + 1.0, tFloor = tFall + 0.5, DUR = tK + 2.75;
    const hits = hitsOf([[tK + 0.03, 4, 1], [tK + 0.42, 4, -1], [tK + 0.8, 3, 1], [tFloor + 0.2, 4, -1], [DUR - 0.05, 5, 1]]);
    const bites = hits.map((h) => h.t);

    // ---- the head ---------------------------------------------------------------------------------------------------
    // Thrashing with it on your face: the head whipped side to side, decaying into the fall.
    const thr = (t) => { const u = t - tK; if (u < 0) return { y: 0, r: 0, p: 0 }; const a = Math.exp(-u * 0.5) * (1 - sstep(tFall + 0.1, tFloor, t)); return { y: a * (0.42 * Math.sin(u * 15.5) + 0.12 * Math.sin(u * 37)), r: a * 0.22 * Math.sin(u * 13 + 1.3), p: a * (0.16 * Math.sin(u * 11 + 0.4)) }; };
    const base = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t), y = yawK(t), side = Math.sin(y);
      // turning over a shoulder moves the eye a little to that side and back
      const c = { x: lerp(s.x, 0, k) - 0.07 * side, y: lerp(s.y, eye, k) - 0.02 * Math.abs(side), z: lerp(s.z, 0, k) - 0.05 * Math.abs(side), yaw: lerp(s.yaw, y, k), pitch: lerp(s.pitch, pitchK(t), k), roll: 0.04 * side * k, fov: s.fov };
      // up there: the eyes go a little to it; when it sees you, they stay on its face; a small flinch back
      c.yaw += yUp * sstep(tUp0, tUp1, t);
      c.z -= 0.06 * sstep(tSee, tSee + 0.25, t); c.y -= 0.025 * sstep(tSee, tSee + 0.25, t);
      return c;
    };
    const look = (t, c, q) => { const p = clamp(R.pitchTo(c.x, c.y, c.z, q.x, q.y, q.z), -0.8, 1.35), y = R.yawTo(c.x, c.z, q.x, q.z); return { p, y }; };
    const cam = (t) => {
      const c = base(t);
      c.near = t >= tUp0 ? 0.02 : undefined;
      if (t >= tSee - 0.2 && t < tK) {   // the eyes on it, and on it as it comes
        const q = t < tLeap ? hL : leapHead(t), l = look(t, c, q), w = t < tLeap ? 0.9 * sstep(tSee - 0.2, Math.max(tUp1, tSee + 0.6), t) : 1;
        c.pitch = lerp(c.pitch, l.p, w); c.yaw = lerp(c.yaw, c.yaw + Math.atan2(Math.sin(l.y - c.yaw), Math.cos(l.y - c.yaw)), w);
      }
      if (t >= tK) {
        // Hit in the face: thrown back, then the struggle, then over backwards to the floor.
        const c0 = cK;
        const th = thr(t), kk = kick(t, hits.slice(0, 3).map((h) => ({ t: h.t, side: h.side, amp: 0.8 })).concat(hits.slice(3).map((h) => ({ t: h.t, side: h.side, amp: 1.3 }))));
        c.x = c0.x; c.y = c0.y - 0.05 * sstep(tK, tK + 0.2, t); c.z = c0.z - 0.28 * sstep(tK, tK + 0.25, t) - 0.12 * sstep(tK + 0.3, tFall, t);
        c.yaw = c0.yaw + th.y + kk.yaw; c.roll = th.r;
        c.pitch = lerp(c0.pitch + 0.22 * Math.exp(-(t - tK) / 0.15) * sstep(tK, tK + 0.06, t), 0.25, sstep(tK + 0.15, tK + 0.6, t)) + th.p + kk.pitch;
        floorFall(c, t, tFall, { d: 0.5, side: -1, roll: 0.42, y: 0.3, pitch: 1.12, back: 0.5 });
        c.fov = c0.fov + 7 * pulse(t, [tK], 0.14) + 3 * pulse(t, bites, 0.1);
        c.near = 0.02;
      }
      const amp = 0.0015 + 0.0025 * sstep(tSay, tL1, t) * (1 - sstep(tF1, tUp0, t)) + 0.004 * sstep(tSee, tLeap, t) + 0.03 * pulse(t, [tK, tFloor - 0.02], 0.14) + 0.012 * sstep(tK, tK + 0.1, t) + 0.016 * pulse(t, bites, 0.15);
      return shake(c, t, amp, 6);
    };

    // ---- where it is ------------------------------------------------------------------------------------------------
    const crawl = (t) => { const k = sstep(tL2 - 0.1, tR1 + 0.25, t); return { x: lerp(sx + 0.35 * Math.sign(sx || 1), sx, k), z: lerp(bz, sz, k) }; };
    const _q0 = new THREE.Quaternion(), _p0 = new THREE.Vector3(), _q1 = new THREE.Quaternion(), _p1 = new THREE.Vector3(), _e = new THREE.Euler(), _v = new THREE.Vector3(), _a = new THREE.Vector3();
    const _flip = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI), _qj = new THREE.Quaternion();
    // On your face: its face at dist from the lens, square to it, the body trailing down the view (tilt); a lag behind
    // the head's thrash so it is a weight clinging, not a sticker.
    function onFace(t, dist, tilt, lagYaw, out = _p1, qout = _q1) {
      const cm = R.camera;
      _e.set(tilt + 0.05 * Math.sin(t * 9), lagYaw + 0.06 * Math.sin(t * 7.3), 0.08 * Math.sin(t * 5.1), "YXZ");
      qout.copy(cm.quaternion).multiply(_flip).multiply(_qj.setFromEuler(_e));
      out.set(0, -0.04, -dist).applyQuaternion(cm.quaternion).add(cm.position);
      _a.copy(anchor).applyQuaternion(qout);
      return out.sub(_a);
    }
    // The leap: from the ceiling to your face (its head, in local terms, for the eyes that follow it).
    const leapU = (t) => { const u = clamp((t - tLeap) / (tK - tLeap)); return u * u * (1.35 - 0.35 * u); };
    const leapHead = (t) => { const u = leapU(t), c = cam0K; return { x: lerp(hL.x, c.x, u), y: lerp(hL.y, c.y + 0.1, u) - 0.25 * Math.sin(u * Math.PI), z: lerp(hL.z, c.z + 0.35, u) }; };
    let cam0K = null, cK = null;
    cam0K = base(tK); cK = { ...base(tK) };
    { const l = look(tK, cK, { x: hL.x * 0.3, y: cK.y + 0.6, z: cK.z + 0.5 }); cK.pitch = l.p; cK.yaw = cK.yaw + Math.atan2(Math.sin(l.y - cK.yaw), Math.cos(l.y - cK.yaw)) * 0.5; }

    // ---- the lens: its legs closing round your head --------------------------------------------------------------
    const Lg = (fx, fy, tx, ty, t1, ph) => ({ from: [fx, fy], to: [tx, ty], t0: t1, t1: t1 + 0.16, z: -0.26, scale: 0.44, axis: "x-", twist: 0.16, ph, curl: 0.28 * Math.sign(fx) });
    const legs = lensLimbs(R, legDonor, "spiderLeg1", [
      Lg(-0.64, 0.24, -0.21, 0.13, tK - 0.04, 0), Lg(-0.64, -0.04, -0.23, -0.01, tK - 0.02, 1), Lg(-0.6, -0.32, -0.2, -0.17, tK, 2),
      Lg(0.64, 0.25, 0.21, 0.14, tK - 0.03, 3), Lg(0.64, -0.03, 0.24, 0.0, tK - 0.01, 4), Lg(0.6, -0.32, 0.21, -0.16, tK + 0.01, 5)
    ], { color: 0x4a4242 });

    // ---- gore: where your face is at each bite ---------------------------------------------------------------------
    // (from your neck and face, under and round its head, thrown out to the sides: not into the lens)
    for (let i = 0; i < hits.length; i++) {
      const h = hits[i], c = cam(h.t), sd = h.side;
      const cy = Math.cos(c.yaw), sy = Math.sin(c.yaw), cp = Math.cos(c.pitch), spt = Math.sin(c.pitch);
      const F = [-sy * cp, spt, cy * cp], U = [sy * spt, cp, -cy * spt], Rt = [cy, 0, sy];
      const at = [0, 1, 2].map((k) => [c.x, c.y, c.z][k] - U[k] * 0.3 + F[k] * 0.3);
      const dir = [0, 1, 2].map((k) => U[k] * 0.7 + Rt[k] * sd * 1.1 + F[k] * 0.6);
      R.burst(h.t + 0.01, at, 34, "blood", { dir, speed: 2.6, spread: 0.6, size: 0.034, life: 1.3, stick: 4 });
      R.burst(h.t + 0.03, at, 10, "blood", { dir: dir.map((v, k) => v * 0.3 - Rt[k] * sd * 1.4 + U[k] * 0.6), speed: 2.0, spread: 0.5, size: 0.03, life: 1.2, stick: 4 });
      R.burst(h.t + 0.02, at, i % 2 ? 4 : 6, "flesh", { dir: dir.map((v, k) => v * 0.8 - Rt[k] * sd * 1.6), speed: 1.7, spread: 0.5, size: 0.045, life: 1.2, stick: 4 });
    }
    // the grit that falls in front of your face when it steps up there
    // (a trickle of stone grit, pale against the dark, falling past your eyes for most of a second)
    [0, 0.12, 0.3, 0.5, 0.75].forEach((d, i) => R.burst(tDust + d, [sx * 0.5, ceil - 0.05, sz - 0.15 - 0.05 * i], i ? 4 : 7, "stone", { dir: [0, -0.2, 0], speed: 0.2, spread: 0.12, size: 0.014, life: 1.5, grav: 8, stick: 0.6 }));

    // ---- the sound ----------------------------------------------------------------------------------------------------
    const P = (q, y = ceil - 0.5) => [q.x, y, q.z];
    const steps = [];
    for (let tt = tL2 - 0.05, i = 0; tt < tR1 + 0.2; tt += R.vary(0.32, 0.25), i++) steps.push([tt, "mob.spider.step", { at: P(crawl(tt), ceil - 0.2), volume: 0.2 + 0.02 * i, pitch: 0.95 }]);
    const faceW = (t) => { const c = cam(t); return [c.x, c.y, c.z + 0.3]; };
    const sounds = [
      [tSay, "mob.spider.say", { at: P(crawl(tSay)), volume: 0.85, pitch: 0.82, reverb: 0.35 }],
      ...steps,
      [tDust, "mob.spider.step", { at: [sx, ceil - 0.2, sz], volume: 0.65, pitch: 0.85 }], [tDust + 0.04, "dig.gravel", { at: [sx, ceil - 0.2, sz - 0.4], volume: 0.12, pitch: 1.5 }],
      silence(tSee - 0.05, { fade: 0.25 }),
      [tSee + 0.22, "mob.spider.say", { at: [hL.x, hL.y, hL.z], volume: 0.9, pitch: 0.62 }],
      ...roar(tLeap, [["mob.spider.say", { at: [hL.x, hL.y, hL.z], pitch: 0.9 }]], { hit: 0.6 }),
      [tLeap + 0.02, "mob.spider.step", { at: [hL.x, hL.y, hL.z], volume: 0.9, pitch: 0.7 }],
      ...hits.flatMap((h, i) => [...blow(h.t, { volume: i ? 0.95 : 1.15, gore: i % 2 === 1 }), [h.t - 0.06, "mob.spider.say", { at: faceW(h.t), volume: 0.75, pitch: 1.0 + 0.08 * (i % 3) }]]),
      [tK + 0.2, "mob.spider.step", { volume: 0.8, pitch: 1.1 }], [tK + 0.55, "mob.spider.step", { volume: 0.8, pitch: 1.0 }], [tK + 0.95, "dig.cloth", { volume: 0.7, pitch: 0.6 }],
      ...deathScream(tK + 0.1, { volume: 1.2, under: false }),
      [tFloor - 0.02, "game.player.hurt.fall.small", { volume: 1.0 }], [tFloor, "step.stone", { volume: 0.9, pitch: 0.7 }],
      [tFloor + 0.6, "mob.spider.step", { volume: 0.7 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3 }]
    ];
    const loops = [
      [0.6, tSee - 0.05, "qf.scare.heartbeat", { volume: 0.5 }],
      [tL0, tUp0, "qf.scare.breath", { volume: 0.3, fadeIn: 0.6, fadeOut: 0.5 }],
      [tF1, tSee - 0.05, "qf.scare.drone", { volume: 0.35, fadeIn: 1.2, fadeOut: 0.2, bus: "sfx" }],
      [tSee + 0.3, tK, "qf.scare.heartbeat", { volume: 0.65, pitch: 1.35, fadeIn: 0.05, fadeOut: 0.05 }],
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.45, fadeIn: 0.02 }]
    ];

    // ---- the frame ----------------------------------------------------------------------------------------------------
    function update(t, f) {
      let open = 0, eyes = 0, own = 0.05;
      const piv = sp.pivot;
      if (t < tLeap) {
        // On the ceiling: behind you, then creeping forward over it while you look round; still, watching; when it sees
        // you see it, the head follows your face and the legs draw in.
        const q = t < tR1 + 0.3 ? crawl(t) : { x: sx, z: sz };
        const moving = t > tL2 - 0.1 && t < tR1 + 0.25;
        const pp = perchPose(t), tense = sstep(tSee, tSee + 0.6, t);
        // facing you from behind; heading forward while it creeps; turned round to face you at the perch
        // (behind you, facing you is facing forward: yaw 0; at the perch it turns round, yaw about pi)
        const ppy = pp.yaw >= 0 ? pp.yaw : pp.yaw + 2 * Math.PI;
        const yawNow = lerp(0.05 * Math.sin(t * 0.7), ppy, sstep(tR1 - 0.05, tR1 + 0.4, t));
        R.place(sp, q.x, ceil, q.z, yawNow, -0.42 - 0.12 * tense, Math.PI);
        sp.anim(moving ? t * 1.6 : t * 0.4, 0, { walk: moving ? 0.9 : 0.06 + 0.25 * tense, lookPitch: -0.3 * sstep(tSee, tSee + 0.3, t) });
        piv.visible = true;
        open = 0.15 * sstep(tSee, tSee + 0.3, t) + 0.75 * sstep(tLeap - 0.45, tLeap - 0.1, t) + 0.12 * Math.sin(t * 17) * sstep(tSee, tSee + 0.4, t);
        eyes = 1; own = 0.04 + 0.12 * sstep(tUp0 + 0.5, tSee + 0.3, t);
      } else if (t < tK) {
        // The leap: off the stone, turning over as it comes, legs out, at your face.
        const u = leapU(t);
        R.place(sp, sx, ceil, sz, perchPose(tLeap).yaw, -0.54, Math.PI); sp.anim(t * 3, 0, { walk: 1.6 }); piv.updateMatrixWorld(true);
        _p0.copy(piv.position); _q0.copy(piv.quaternion);
        onFace(t, 0.64, -0.35, 0);
        piv.position.lerpVectors(_p0, _p1, u); piv.position.y -= 0.2 * Math.sin(u * Math.PI);
        piv.quaternion.slerpQuaternions(_q0, _q1, Math.min(1, u * 1.4));
        piv.visible = true; open = 0.95; eyes = 1; own = 0.16;
      } else {
        // On you: clinging to your face as you thrash (it lags your head a little), the fangs driving in on each bite;
        // on the floor, on your chest, over your face.
        const th = thr(t), lag = thr(t - 0.07).y - th.y;
        const bite = pulse(t, bites.map((b) => b - 0.07), 0.09);
        const fl = sstep(tFall, tFloor, t);
        onFace(t, lerp(0.64, 0.68, fl) - 0.26 * bite, lerp(-0.35, -0.75, fl), lag * 1.4);
        piv.position.copy(_p1); piv.quaternion.copy(_q1);
        sp.anim(t * 2.4, 0, { walk: 1.4 - 0.6 * fl });
        piv.visible = true;
        open = 0.35 + 0.65 * pulse(t, bites.map((b) => b - 0.12), 0.12) + 0.2 * Math.sin(t * 23) * (1 - fl);
        eyes = 0.85; own = 0.14 + 0.04 * fl;
      }
      fangs(clamp(open), own);
      sp.setOwn(own);
      piv.updateMatrixWorld(true);
      eyeGlow.forEach((h, i) => {
        h.visible = eyes > 0.01 && t < tK;
        if (!h.visible) return;
        _v.set((i ? -1 : 1) * 1.5 / 16, 0.5 / 16, -8.1 / 16); sp.parts.head.localToWorld(_v); h.position.copy(_v);
        h.material.opacity = 0.5 * eyes; h.scale.setScalar(Math.min(1, _v.distanceTo(R.camera.position) / 1.6));
      });
      legs(t);
      const dark = sstep(0.3, 1.5, t), up = sstep(tUp0, tUp1, t), dead = sstep(DUR - 0.4, DUR + 0.6, t);
      f.env = { bake: 1 - 0.25 * dark - 0.2 * up - 0.15 * dead, lights: 1 - 0.3 * up - 0.2 * dead, fogMul: 1 + 0.7 * sstep(1, 3, t) };
      f.vig = [0, 0, 0, 0.3 + 0.25 * up * (t < tK ? 1 : 0.6) + 0.3 * dead]; f.vigR = 0.85;
      f.splats = [hits[0], hits[2], hits[4]].filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.2, 0.8, 0.3][i], y: [0.72, 0.3, 0.25][i], r: [9, 10, 12][i], seed: 41 + i }));
      f.black = 0.55 * sstep(DUR - 0.2, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: tR1 + 0.1, fake: tSee + 0.5, lunge: tLeap + 0.15, kill: tK + 1.4 },
      notes: { ceil: +ceil.toFixed(2), sz: +sz.toFixed(2), bz: +bz.toFixed(2), pUp: +pUp.toFixed(2), tSee: +tSee.toFixed(2), tLeap: +tLeap.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
