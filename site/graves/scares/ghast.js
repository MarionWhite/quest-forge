// Ghast (piston trap, deep, round 7): the floor drops you down a short shaft onto a ledge in a vast netherrack cavern
// over a lava sea. Far off, a cry; another, nearer. Then silence (round 8: no fireball before it shows itself; the owner:
// "there should only be the one after it jumpscares the player"). Either the huge white face rises slowly from below
// the edge, eyes shut, until it hangs level with you, and the eyes open; or you look down over the edge at nothing, and
// the dark beside you, and when the view comes back it is hanging there, eyes open (its one device). It charges, as in
// the game: the mouth opens with its cry, and the fireball comes out of it and across the drop at you, growing, until
// it goes off in your face and you are thrown back across the ledge, burning.
import { THREE, clamp, lerp, sstep, pulse, tex, loadImg, easeOut, track } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, explosionFX, smoke } from "./common.js";
import { pistonTrap } from "./piston.js";
import { silence, deathScream } from "./fnaf.js";
import { roar } from "./story.js";
import { whenMobTexturesLoaded } from "../../lib/mc/mobs.js";

// The cavern, as instanced blocks under the hole (cells aligned with the Krypt's grid, so the shaft lines up):
// an ellipsoid of air with a ragged skin, the ledge you land on, a lava sea, glowstone in the roof.
async function buildCavern(R, hole, ledgeY) {
  const names = ["netherrack", "soul_sand", "glowstone", "gravel"];
  const texs = await Promise.all(names.map((n) => tex("k:" + n)));
  const n3 = (a, b, c) => { const s = Math.sin(a * 12.9898 + b * 78.233 + c * 37.719) * 43758.5453; return s - Math.floor(s); };
  const air = (x, y, z) => {   // cell centre, relative to the hole's corner
    if (Math.abs(x) < 1 && Math.abs(z) < 1 && y > ledgeY) return y < -0.5;   // the shaft
    if (y > -2.5) return false;
    if (x > -3.5 && x < 3.5 && z > -6 && z < 1.6 && y < ledgeY && y > ledgeY - 3 - (z + 6) * 0.25 - Math.abs(x) * 0.4) return false;   // the ledge
    if (y < -31.5) return false;
    if (z > -2.5 && Math.abs(x) < 4.5 && y > ledgeY && y < -2.5) return true;   // the mouth of the cave the ledge sits in
    const e = (x / 17) ** 2 + ((y + 19) / 17) ** 2 + ((z - 11) / 14.5) ** 2;
    return e < 1 - 0.15 * n3(Math.floor(x / 2), Math.floor(y / 2), Math.floor(z / 2));
  };
  const cells = names.map(() => []);
  for (let x = -19.5; x <= 19.5; x++) for (let y = -32.5; y <= -1.5; y++) for (let z = -9.5; z <= 31.5; z++) {
    if (air(x, y, z)) continue;
    if (!(air(x + 1, y, z) || air(x - 1, y, z) || air(x, y + 1, z) || air(x, y - 1, z) || air(x, y, z + 1) || air(x, y, z - 1))) continue;
    const q = n3(x, y, z);
    const top = air(x, y + 1, z);
    const roof = !top && air(x, y - 1, z) && Math.hypot(x, z - 11) > 5 && Math.hypot(x, z) > 6;
    const b = roof && q < 0.22 ? 2 : top && y < -24 && q < 0.4 ? 1 : q < 0.04 ? 3 : 0;
    cells[b].push([x, y, z]);
  }
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const shade = [], nrm = geo.attributes.normal;
  for (let i = 0; i < nrm.count; i++) { const ny = nrm.getY(i), nx = nrm.getX(i); const v = ny > 0.5 ? 1 : ny < -0.5 ? 0.5 : Math.abs(nx) > 0.5 ? 0.6 : 0.8; shade.push(v, v, v); }
  geo.setAttribute("color", new THREE.Float32BufferAttribute(shade, 3));
  const group = new THREE.Group(); group.visible = false; R.add(group);
  const M = new THREE.Matrix4(), C = new THREE.Color(), P = new THREE.Vector3();
  names.forEach((n, i) => {
    const list = cells[i]; if (!list.length || !texs[i]) return;
    const im = new THREE.InstancedMesh(geo, new THREE.MeshBasicMaterial({ map: texs[i], vertexColors: true }), list.length);
    list.forEach(([x, y, z], j) => {
      R.L(hole.x + x, y, hole.z + z, P);
      im.setMatrixAt(j, M.makeTranslation(P.x, P.y, P.z));
      if (i === 2) C.setRGB(1, 0.95, 0.8);
      else { const lava = 0.95 * Math.exp(-(y + 31) / 7), glow = 0.25 * Math.exp(-Math.max(0, -(y + 3)) / 3) * (Math.abs(x) < 6 ? 1 : 0); const g = 0.07 + lava + glow + 0.04 * n3(x, z, y); C.setRGB(g * 1.05, g * 0.62 + 0.01, g * 0.42 + 0.01); }
      im.setColorAt(j, C);
    });
    im.frustumCulled = false; im.renderOrder = 6; group.add(im);
  });
  // The lava sea.
  const img = await loadImg("k:lava_still");
  const frames = [];
  if (img) for (let f = 0; f < 20; f++) {
    const c = document.createElement("canvas"); c.width = c.height = 16; c.getContext("2d").drawImage(img, 0, f * 16, 16, 16, 0, 0, 16, 16);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(40, 44); frames.push(t);
  }
  const lava = new THREE.Mesh(new THREE.PlaneGeometry(40, 44), new THREE.MeshBasicMaterial({ map: frames[0] || null }));
  lava.rotation.set(-Math.PI / 2, 0, -R.yaw0); lava.renderOrder = 6;
  R.at(lava, hole.x, -31 + 0.875, hole.z + 11); group.add(lava);   // a lava block's surface, 14/16 up
  // Through the hole, from above: the Krypt's rock under the patch would show; a quad over it sends the depth to the
  // far plane, so the cavern draws there instead.
  const punch = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
    uniforms: { c: { value: new THREE.Color(0.1, 0.03, 0.02) } },
    vertexShader: "void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: "uniform vec3 c; void main() { gl_FragColor = vec4(c, 1.0); gl_FragDepth = 1.0; }",
    depthFunc: THREE.AlwaysDepth, depthWrite: true }));
  punch.rotation.set(-Math.PI / 2, 0, 0); punch.renderOrder = 5;
  R.at(punch, hole.x, -0.996, hole.z); group.add(punch);
  return { group, animate(t) { if (frames.length) lava.material.map = frames[Math.floor(t * 10) % 20]; } };
}

export default {
  death: "Steve was fireballed by Ghast",
  async build(R) {
    const [partTex, boomTex, fbTex, gImg, gsImg] = await Promise.all([tex("particles"), tex("explosion"), tex("item_fireball"), loadImg("mc:entity/ghast/ghast"), loadImg("mc:entity/ghast/ghast_shooting")]);
    const r = mulberry(R.seed * 17 + 1);
    const LEDGE = -7;
    const click = R.vary(1.1, 0.3);
    const trap = await pistonTrap(R, { click, open: click + R.vary(0.7, 0.3), D: -LEDGE, room: false });
    const hole = trap.hole;
    const cave = await buildCavern(R, hole, LEDGE);
    // The ghast's three faces: shut, eyes open (rows 4-5 of ghast_shooting), and shooting.
    const face = (rows) => {
      const c = document.createElement("canvas"); c.width = 64; c.height = 32; const x = c.getContext("2d");
      if (gImg) x.drawImage(gImg, 0, 0);
      if (gsImg) for (const [y0, y1] of rows) x.drawImage(gsImg, 16, 16 + y0, 16, y1 - y0, 16, 16 + y0, 16, y1 - y0);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; return t;
    };
    const G = R.mob("Ghast", { amb: [0.3, 0.26, 0.24], own: true });
    // A skin over the vanilla texture (the Krypt's mob skins: a painted face, eyes shut, at 4x): its own three faces,
    // the eyes opened and the mouth opened where its painting has them, so the face never changes style mid-scare.
    await whenMobTexturesLoaded(); await new Promise((res) => setTimeout(res, 0)); await whenMobTexturesLoaded();
    let skin = null;
    G.root.traverse((o) => { const im = o.isMesh && o.material && o.material.map && o.material.map.image; if (!skin && im && im.width > 64) skin = im; });
    const skinFace = (eyes, mouth) => {
      const sc = skin.width / 64, c = document.createElement("canvas"); c.width = skin.width; c.height = skin.height;
      const x = c.getContext("2d"); x.drawImage(skin, 0, 0);
      const oval = (cx, cy, rx, ry, col) => { x.fillStyle = col; x.beginPath(); x.ellipse((16 + cx) * sc, (16 + cy) * sc, rx * sc, ry * sc, 0, 0, Math.PI * 2); x.fill(); };
      if (eyes) for (const cx of [3.75, 12.25]) { oval(cx, 9.3, 1.35, 0.6, "#241818"); oval(cx, 9.3, 0.55, 0.42, "#c80c0c"); oval(cx, 9.3, 0.22, 0.2, "#ff5a4a"); }
      if (mouth) { oval(7.8, 12.7, 1.05, 2.0, "#1c1010"); oval(7.8, 12.9, 0.62, 1.45, "#c80c0c"); }
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; return t;
    };
    const faces = skin ? [skinFace(false, false), skinFace(true, false), skinFace(true, true)] : [face([]), face([[4, 6]]), face([[4, 6], [9, 16]])];
    G.root.traverse((o) => { if (o.isMesh && o.material && o.material.map) { o.material.map = faces[0]; if (o.material.emissiveMap) o.material.emissiveMap = faces[0]; } });
    const setFace = (i) => G.root.traverse((o) => { if (o.isMesh && o.material && o.material.map !== faces[i] && o.material.map) { o.material.map = faces[i]; o.material.emissiveMap = faces[i]; } });
    G.anim(0, 0, {}); R.place(G, 0, -20, 8, Math.PI);

    // ---- the dice -------------------------------------------------------------------------------------------
    const T_LOOK = trap.land + 0.3, T_CRY1 = T_LOOK + R.vary(1.3, 0.3), T_CRY2 = T_CRY1 + R.vary(0.65, 0.3);
    const T_SIL = T_CRY2 + 0.8;
    const rise = R.chance(0.5), side = R.pick([-1, 1]);
    const T_RISE = T_SIL + R.vary(0.7, 0.3), T_UP = T_RISE + R.vary(1.4, 0.2), T_EYES = T_UP + R.vary(0.6, 0.3);
    const T_DOWN = T_SIL + 0.2, T_SIDE = T_DOWN + R.vary(1.5, 0.3), T_BACKV = T_SIDE + 0.6 + R.vary(0.8, 0.4);
    // The charge: the mouth opens with its cry (t0); the fireball leaves it (T_SHOOT) and crosses the drop (T_HIT).
    // (on the look-back its charge warble is what turns the head back; it opens its mouth on its own clock after it)
    const t0 = rise ? T_EYES + R.vary(0.85, 0.4) : T_BACKV + R.vary(0.42, 0.25);
    const T_SHOOT = t0 + R.vary(0.55, 0.2), T_HIT = T_SHOOT + 0.6, DUR = T_HIT + 1.5;
    const gz = hole.z + 7.2, gx = hole.x - 0.3;   // it hangs out over the drop in front of the ledge
    const camEye = LEDGE + R.eye;
    // Its pivot (the body is 2.25 to 6.75 m above it at scale 4.5): up from far below until the face is level with yours.
    // (on the look-back it has floated in out of the dark while you looked away: it is still settling as you turn back)
    const drift = (t) => (rise ? 0 : 1 - easeOut(sstep(T_SIDE, T_BACKV + 0.2, t)));
    const gY = (t) => (rise ? lerp(LEDGE - 24, camEye - 5.1, easeOut(sstep(T_RISE, T_UP, t))) : camEye - 5.1 - 2.2 * drift(t)) + Math.sin(t * 1.4) * 0.15;
    const hits = hitsOf([[trap.land, 4, 1], [T_HIT, 11, -1], [T_HIT + 0.5, 2, 1], [DUR, 2, -1]]);

    // ---- the camera ------------------------------------------------------------------------------------------
    const K = [[T_LOOK, 0, -0.5], [T_LOOK + 0.9, 0.15, -0.75], [T_CRY1 + 0.5, 0.9, -0.2], [T_CRY2 + 0.5, -0.5, -0.25]];
    if (rise) K.push([T_RISE + 0.2, 0, -0.62], [T_UP, 0, -0.05], [T_EYES + 0.1, 0, -0.06], [t0, 0, -0.1]);
    else K.push([T_DOWN + 0.5, 0, -0.95], [T_SIDE, 0.05 * side, -0.9], [T_SIDE + 0.6, side * 1.5, -0.2], [T_BACKV, side * 1.55, -0.2, "l"], [T_BACKV + 0.28, 0, -0.06, "x"]);
    const yawT = track(K.map((k) => [k[0], k[1], k[3]])), pitchT = track(K.map((k) => [k[0], k[2], k[3]]));
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      let c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov };
      c = trap.cam(t, c);
      if (t > T_LOOK) {
        const kk = sstep(T_LOOK, T_LOOK + 0.4, t);
        c.yaw = lerp(c.yaw, yawT(t), kk); c.pitch = lerp(c.pitch, pitchT(t), kk); c.x = lerp(c.x, hole.x, kk); c.z = lerp(c.z, hole.z + 0.6 * sstep(T_LOOK, T_LOOK + 1, t), kk);
        if (rise) c.fov = s.fov - 8 * sstep(T_UP, t0, t);
        c.near = t >= t0 - 0.1 ? 0.05 : undefined;
        // It comes at you: the head pulls back a little from it, and the field narrows on it.
        const come = sstep(T_SHOOT, T_HIT, t) * (t < T_HIT ? 1 : 0);
        c.z -= 0.12 * come; c.pitch += 0.04 * come; c.fov -= 6 * come;
      }
      if (t > T_HIT) {   // blown back off your feet onto the ledge, looking up past the edge of the roof
        const k2 = easeOut((t - T_HIT) / 0.45);
        c.z -= 1.4 * k2; c.y = lerp(c.y, LEDGE + 0.3, k2); c.pitch = lerp(c.pitch, 0.75, k2); c.roll = lerp(0, 0.5, k2);
      }
      return shake(c, t, 0.0015 + 0.004 * (rise ? sstep(T_RISE, T_UP, t) : 0) + 0.006 * sstep(t0, T_HIT, t) * (t < T_HIT ? 1 : 0) + 0.035 * pulse(t, [trap.land, T_HIT], 0.2), 9);
    };
    const boom = explosionFX(R, T_HIT, [hole.x, camEye - 0.1, hole.z + 1.2], boomTex, { n: 14, spread: 1.4, seed: 21 });
    const ember = [];
    for (let i = 0; i < 50; i++) ember.push({ t0: T_LOOK + r() * (DUR - T_LOOK), at: [gx + (r() - 0.5) * 14, LEDGE - 22 + r() * 6, gz + (r() - 0.5) * 14], v: [(r() - 0.5) * 0.3, 1.5 + r() * 2, (r() - 0.5) * 0.3], life: 2.5, size: 0.1, tile: 49, color: [1, 0.65, 0.3], grav: -0.2, fog: false, add: true });
    for (let i = 0; i < 30; i++) ember.push({ t0: trap.land + r() * (DUR - trap.land), at: [hole.x + (r() - 0.5) * 18, LEDGE - 24 + r() * 4, hole.z + 8 + (r() - 0.5) * 14], v: [0, 2 + r() * 2, 0], life: 3, size: 0.1, tile: 49, color: [1, 0.6, 0.25], grav: -0.1, fog: false, add: true });
    const fx = particles(R, partTex, [...ember, ...smoke([hole.x, camEye, hole.z + 1.0], T_HIT + 0.05, 16, { spread: 1.6, window: 0.6, life: 2, size: 0.45, rise: 0.8, seed: 23 })]);
    // Its fireball: out of the mouth (the front of the body, low) and across the drop to your face, growing as it comes.
    const fb2 = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: fbTex, transparent: true, alphaTest: 0.1, fog: false }));
    fb2.renderOrder = 8; fb2.visible = false; R.add(fb2);
    fb2.onBeforeRender = function (rr, sc, cm) { this.quaternion.copy(cm.quaternion); this.updateMatrixWorld(); };
    const mouthAt = (t) => [gx, gY(t) + 2.25 + 1.0, gz - 2.3], faceAt = [hole.x, camEye - 0.05, hole.z + 1.0];
    const lavaLight = R.ownLight(R.light(0xff6a20, 0, 40, 0.6));
    const fbLight = R.ownLight(R.light(0xffa040, 0, 9, 1.4));
    const sounds = [
      ...trap.sounds,
      [trap.land + 0.4, "liquid.lava", { at: [hole.x, -31, hole.z + 10], volume: 0.6 }],
      [T_CRY1, "mob.ghast.moan", { at: [hole.x - 14, LEDGE - 6, hole.z + 22], volume: 0.7, pitch: 0.9, reverb: 0.9 }],
      [T_CRY2, "mob.ghast.affectionate_scream", { at: [hole.x + 9, LEDGE - 10, hole.z + 14], volume: 0.8, reverb: 0.8 }],
      silence(T_SIL, { fade: 0.6 }),
      ...(rise ? [[T_RISE + 0.6, "mob.ghast.moan", { at: [gx, LEDGE - 6, gz], volume: 0.5, pitch: 0.7, reverb: 0.5 }], [T_EYES, "mob.ghast.charge", { at: [gx, camEye, gz], volume: 0.9 }]]
        : [[T_SIDE - 0.3, "mob.ghast.moan", { at: [hole.x + side * 6, LEDGE - 2, hole.z + 2], volume: 0.3, pitch: 0.6, reverb: 0.7 }], [T_BACKV - 0.15, "mob.ghast.charge", { at: [gx, camEye, gz], volume: 0.9 }]]),
      // The charge: its cry as the mouth opens; the fireball out of it.
      ...(rise ? [[t0 - 0.05, "mob.ghast.charge", { at: [gx, camEye, gz], volume: 1.2 }]] : []),
      ...roar(t0 + 0.05, [["mob.ghast.scream", { at: [gx, camEye, gz], pitch: 0.75 }], ["mob.ghast.affectionate_scream", { at: [gx, camEye, gz], pitch: 0.65, volume: 1.0 }]], { hit: 0.5 }),
      [T_SHOOT, "mob.ghast.fireball", { at: [gx, camEye - 0.5, gz - 2.3], volume: 1.3 }],
      [T_SHOOT + 0.3, "fire.fire", { volume: 0.6 }],
      [T_HIT, "random.explode", { volume: 1.2 }], [T_HIT + 0.01, "qf.scare.hit", { volume: 1 }], [T_HIT, "game.player.hurt"],
      [T_HIT + 0.03, "@muffle", { hz: 300, s: 3 }], ...deathScream(T_HIT + 0.15, { volume: 1.35 }),
      [T_HIT + 0.5, "game.player.hurt"], [T_HIT + 0.55, "fire.fire", { volume: 0.9 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.5, T_SIL, "qf.scare.heartbeat", { volume: 0.5 }],
      [trap.land, T_SIL, "liquid.lava", { at: [hole.x, -28, hole.z + 10], volume: 0.5, fadeIn: 0.8 }],
      [T_SIL + 0.8, t0 - 0.05, "qf.scare.heartbeat", { volume: 0.4, fadeIn: 0.8, fadeOut: 0.02 }],
      ...(rise ? [[T_RISE, t0 - 0.05, "qf.scare.drone", { volume: 0.5, fadeIn: 0.8, fadeOut: 0.03, pitch: 0.7, bus: "sfx" }]] : []),
      [T_HIT + 0.05, DUR + 1, "qf.scare.ringing", { volume: 0.5, fadeIn: 0.05, fadeOut: 1.5 }]
    ];
    function update(t, f) {
      trap.update(t, f);
      cave.group.visible = t >= trap.open;
      cave.animate(t);
      const cl = R.toLocal(R.camera.position), y = gY(t);
      G.pivot.visible = rise ? t >= T_RISE && t < T_HIT + 0.05 : t >= T_SIDE + 0.62 && t < T_HIT + 0.05;
      const gzt = gz + 5 * drift(t);
      R.place(G, gx, y, gzt, R.yawTo(gx, gzt, cl.x, cl.z));
      G.anim(t, 0, {});
      setFace(t >= t0 && t < T_SHOOT + 0.5 ? 2 : (rise ? t >= T_EYES : t >= T_SIDE + 0.62) ? 1 : 0);
      G.setOwn(0.28 + 0.12 * (t >= t0 ? 1 : 0) + 0.25 * pulse(t, [T_SHOOT], 0.3));
      // Its fireball, across the drop at you.
      const kb = (t - T_SHOOT) / (T_HIT - T_SHOOT);
      fb2.visible = kb >= 0 && kb < 1;
      if (fb2.visible) { const m = mouthAt(T_SHOOT); R.at(fb2, lerp(m[0], faceAt[0], kb), lerp(m[1], faceAt[1], kb), lerp(m[2], faceAt[2], kb)); fb2.scale.setScalar(1.1 + 0.15 * Math.sin(t * 40)); fb2.rotation.z = t * 5; }
      boom(t); fx(t);
      R.L(gx, LEDGE - 18, gz, lavaLight.position); lavaLight.intensity = t >= trap.open ? 1.6 * (1 - 0.35 * sstep(T_SIL, T_SIL + 1, t) * (1 - sstep(t0, t0 + 0.1, t))) : 0;
      if (fb2.visible) fbLight.position.copy(fb2.position);
      fbLight.intensity = fb2.visible ? 4 + 3 * kb : 6 * pulse(t, [T_HIT], 0.3);
      const inCave = sstep(trap.tFall, trap.tFall + 0.3, t), sil = sstep(T_SIL, T_SIL + 1, t) * (1 - sstep(t0, t0 + 0.1, t));
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t), lights: 1 - 0.5 * inCave, fogMul: lerp(1 + 0.4 * sstep(1, 3, t), 0.55, inCave) * (1 + 0.5 * sil), fog: [0.16 * (1 - 0.5 * sil), 0.04, 0.02, inCave] };
      f.white = t >= T_HIT ? 1 - sstep(T_HIT + 0.1, T_HIT + 0.9, t) : 0;
      f.fire = t >= T_HIT ? 1 : 0;
      f.vig = [40, 8, 0, 0.3 + 0.2 * inCave + 0.2 * sil + 0.25 * sstep(T_HIT, DUR, t)]; f.vigR = 0.9;
      f.black = 0.3 * sstep(DUR - 0.2, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: rise ? T_UP + 0.2 : T_DOWN + 0.9, fake: rise ? T_EYES + 0.2 : T_SIDE + 0.7, lunge: T_SHOOT + 0.35, kill: T_HIT + 0.6 },
      notes: { fits: trap.fits, rise, fireballs: 1, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
