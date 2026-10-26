// More things for Steve to do. Each activity is a generator in the same style as steve.js (yield seconds, or a
// function(dt) -> done), built on the brain's own tools through `k`, so they share one pose, one nav map, one
// way of holding things. Every sound is a real 1.7.10 event from the pack's own list, used the way the game uses it:
// the eating sound every four ticks and a burp at the end, the bow's pitch from the draw, the note block's
// pitch 2^((note-12)/12), the shears' own sound, hay for the target. Animals come from critters.js.
import * as THREE from 'three';
import { tex, TINT, glowTexture } from './stage.js';
import { heartSprite } from './fx.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);

export function makeActs(k) {
  const { b, R, snd, fx, hold, setArm, freeArm, relax, walkTo, standAt, faceYaw, faceAt, armSwing, onCleanup, ignoring, spawnItem, placeBlock, breakBlock, crackMesh, palette, nav, L, camp, crit, yawFor, wrapA, smooth, lerp, clamp, entity, jump, showBang, world, setVoxel, TAU, dirOf, R_P, cam, waitItems, tap, play } = k;
  const sheep = crit.list.find((c) => c.kind === 'Sheep'), cow = crit.list.find((c) => c.kind === 'Cow'), wolf = crit.list.find((c) => c.kind === 'Wolf');
  // a framed shot: Steve and the thing he works on, from a 3/4 angle that is clear of props, animals and the fire's glare
  const frame = (tx, tz, D = 3.4, H = 1.2, az = 0.5) => { cam.want = true; cam.spec = { target: V(tx, 0.5, tz), D, H, az }; };
  const lookAt = (x, y, z) => { b.head.target = V(x, y, z); };
  const poof = (p, n = 8) => fx.dust(p, n);
  // a short use-item swing with the arm up in front, held for `secs`
  function* tapOn(n = 1, gap = 0.3) { yield* tap(n, gap); }
  // crumbs of an item while it is eaten (the game's itemcrack particles)
  const CRUMB = { bread: [0xc99a4a, 0xa87a30, 0xe0b96a], apple: [0xd02828, 0xe8e0a0, 0x9a1c1c], beef_raw: [0xc43c3c, 0xe06060], wheat: [0xc9b250, 0xa8923a], bucket_milk: [0xffffff, 0xeeeeee] };
  const mouth = () => { const d = dirOf(b.yaw); return { x: b.x + d.x * 0.25, y: b.y + 1.45, z: b.z + d.z * 0.25 }; };
  const heartsAt = (p, n = 4) => {
    for (let i = 0; i < n; i++) {
      const s = heartSprite(); s.scale.set(0.22, 0.22, 1);
      const g = new THREE.Group(); g.add(s);
      g.position.set(p.x + R(-0.3, 0.3), p.y + R(0, 0.2), p.z + R(-0.3, 0.3));
      let t = -i * 0.12;
      s.material.opacity = 0;
      entity(g, (dt) => { t += dt; if (t < 0) return false; g.position.y += dt * 0.55; s.material.opacity = Math.min(1, t * 6) * Math.max(0, 1 - t / 1.1); return t > 1.1; });
    }
  };
  const green = (p, n = 8) => fx.sparks(p, 0x4fe066, n, { speed: 0.7 });

  // =============================================================== farming: harvest, replant, bone meal
  function* actHarvest() {
    yield* walkTo(-5.5, -3.5);
    frame(-6.5, -3.5, 6.5, 2.4, 0.5);
    const col = camp.crops.filter((c) => c.stage === 7 && c.x > -7);
    if (!col.length) return;
    onCleanup(() => camp.cropsReset());
    for (const c of col) {
      yield* faceAt(c.x, c.z);
      lookAt(c.x, 0.5, c.z);
      yield 0.2;
      yield* armSwing(1, 0.3, () => {
        c.setStage(-1);
        snd('dig.grass', { pos: { x: c.x, y: 0.5, z: c.z }, volume: 0.8, pitch: [0.9, 1.1] });
        fx.chips({ x: c.x, y: 0.5, z: c.z }, [0x7ba03a, 0xc9a64a, 0x9bbf4a], 8, { speed: 1, up: 1 });
        spawnItem({ item: 'wheat' }, { x: c.x, y: 0.6, z: c.z }, { x: R(-0.2, 0.2), y: 3, z: R(0.3, 0.8) }, { pickAt: 0.9 });
        if (R() < 0.85) spawnItem({ item: 'seeds_wheat' }, { x: c.x, y: 0.6, z: c.z }, { x: R(-0.3, 0.3), y: 3, z: R(0.3, 0.8) }, { pickAt: 0.9 });
      });
      yield 0.3;
    }
    yield 0.5; yield* waitItems();
    // sow the seeds again
    hold({ item: 'seeds_wheat' });
    for (const c of col) {
      yield* faceAt(c.x, c.z); lookAt(c.x, 0.2, c.z);
      yield* tapOn(1, 0.3);
      c.setStage(0);
      snd('dig.grass', { pos: { x: c.x, y: 0.3, z: c.z }, volume: 0.6, pitch: [0.9, 1.1] });
    }
    // bone meal: each use pushes the crop on by 2 to 5 stages, with the green glitter
    hold({ item: 'dye_powder_white' });
    for (const c of col) {
      yield* faceAt(c.x, c.z); lookAt(c.x, 0.3, c.z);
      let n = 0;
      while (c.stage < 7 && n++ < 4) {
        yield* tapOn(1, 0.35);
        c.setStage(Math.min(7, c.stage + 2 + Math.floor(R() * 4)));
        green({ x: c.x, y: 0.4, z: c.z }, 10);
      }
    }
    b.head.target = null;
    hold({ item: 'wheat' }); setArm('r', 1.3, 0); b.head.tpitch = 0.25;
    yield 1.6;
    hold(null);
  }

  // =============================================================== a sapling, bone meal, a tree, and the axe
  function oakTree(cx, cz) {
    const g = new THREE.Group();
    g.position.set(cx + 0.5, 0, cz + 0.5);
    const lt = tex('blocks/log_oak_top.png'), ls = tex('blocks/log_oak.png');
    const logM = [ls, ls, lt, lt, ls, ls].map((t) => new THREE.MeshLambertMaterial({ map: t }));
    const leafM = new THREE.MeshLambertMaterial({ map: tex('blocks/leaves_oak.png'), color: TINT.foliage, alphaTest: 0.5, side: THREE.DoubleSide });
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const logs = [], leaves = [];
    const h = 4;
    for (let y = 0; y < h; y++) { const m = new THREE.Mesh(geo, logM); m.position.set(0, y + 0.5, 0); m.castShadow = m.receiveShadow = true; m.visible = false; g.add(m); logs.push(m); }
    const top = h;
    const layers = [{ y: top - 3, r: 2, cut: true }, { y: top - 2, r: 2, cut: true }, { y: top - 1, r: 2, cut: true }, { y: top, r: 1, cut: false }, { y: top + 1, r: 1, cut: true }];
    let i = 0;
    for (const Lr of layers) for (let dx = -Lr.r; dx <= Lr.r; dx++) for (let dz = -Lr.r; dz <= Lr.r; dz++) {
      if (dx === 0 && dz === 0 && Lr.y < top) continue;
      if (Lr.cut && Math.abs(dx) === Lr.r && Math.abs(dz) === Lr.r && (i++ % 3)) continue;
      const m = new THREE.Mesh(geo, leafM); m.position.set(dx, Lr.y + 0.5, dz); m.castShadow = m.receiveShadow = true; m.visible = false; g.add(m); leaves.push(m);
    }
    world.add(g);
    return { g, logs, leaves, dispose() { world.remove(g); } };
  }
  function* actSapling() {
    const sp = L.sapling, cx = sp.cx, cz = sp.cz, X = cx + 0.5, Z = cz + 0.5;
    yield* walkTo(X - 1.2, Z + 0.3);
    yield* faceAt(X, Z);
    frame(L.sapling.cx + 0.5, L.sapling.cz + 0.5, 9, 3, -0.7);
    hold({ item: 'blocks/sapling_oak' });
    yield 0.3;
    // plant it
    lookAt(X, 0.1, Z);
    yield* tapOn(1, 0.3);
    const sap = new THREE.Group();
    for (const a of [0.78, -0.78]) { const q = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), new THREE.MeshLambertMaterial({ map: tex('blocks/sapling_oak.png'), alphaTest: 0.5, side: THREE.DoubleSide, color: TINT.foliage })); q.position.y = 0.45; q.rotation.y = a; sap.add(q); }
    sap.position.set(X, 0, Z);
    world.add(sap);
    onCleanup(() => world.remove(sap));
    snd('dig.grass', { pos: { x: X, y: 0.2, z: Z }, volume: 0.7, pitch: [0.9, 1.1] });
    fx.chips({ x: X, y: 0.15, z: Z }, [0x6a8a30, 0x866043], 5, { speed: 0.6 });
    yield 0.6;
    // bone meal: a few tries; the sapling takes on the last one
    hold({ item: 'dye_powder_white' });
    const tries = 2 + Math.floor(R() * 2);
    for (let i = 0; i < tries; i++) { yield* tapOn(1, 0.5); green({ x: X, y: 0.5, z: Z }, 10); yield 0.4; }
    // it grows: the trunk rises, then the canopy fills in
    world.remove(sap);
    const tree = oakTree(cx, cz);
    onCleanup(() => tree.dispose());
    hold(null); relax();
    b.head.tpitch = -0.5;
    let t = 0;
    yield (dt) => {
      t += dt;
      tree.logs.forEach((m, i) => { m.visible = t > i * 0.14; });
      const lk = (t - 0.5) / 0.9;
      tree.leaves.forEach((m, i) => { m.visible = lk > (i % 17) / 17 * 0.8; });
      return t > 1.8;
    };
    green({ x: X, y: 1.5, z: Z }, 14);
    snd('random.pop', { pos: { x: X, y: 1, z: Z }, volume: 0.5, pitch: 1.4 });
    lookAt(X, 4.2, Z);
    yield 2.0;
    // and he chops it down for the wood: the logs go one by one, the leaves rot away and drop an apple
    b.head.target = null; b.head.tpitch = 0;
    hold({ item: 'iron_axe' });
    for (let i = 0; i < 2; i++) {
      lookAt(X, 1.2 + i, Z);
      const p = { x: X, y: 0.5 + i, z: Z };
      const crack = crackMesh(p.x, p.y, p.z);
      yield* armSwing(3, 0.3, (n) => { crack.set((n + 1) * 3); snd('dig.wood', { pos: p, volume: 0.8, pitch: [0.9, 1.1] }); });
      crack.remove();
      tree.logs[i].visible = false;
      fx.chips(p, palette('log_oak.png'), 12, { speed: 1.6, up: 1.2 });
      spawnItem({ block: 'log_oak' }, p, { x: R(-0.3, 0.3), y: 3, z: 1.1 }, { pickAt: 0.7 });
    }
    // the upper trunk and the canopy decay with no ground under them
    hold(null); relax();
    let a = 0;
    yield (dt) => {
      a += dt;
      const lk = a / 1.4;
      tree.logs[2].visible = a < 0.2; tree.logs[3].visible = a < 0.4;
      tree.leaves.forEach((m, i) => { if (m.visible && lk > (i % 13) / 13) { m.visible = false; if (i % 3 === 0) fx.chips({ x: X + m.position.x, y: m.position.y, z: Z + m.position.z }, [0x4a7a2c, 0x5a8a34, 0x3a6a24], 2, { speed: 0.5, up: 0.2 }); } });
      return a > 2.0;
    };
    snd('dig.grass', { pos: { x: X, y: 2, z: Z }, volume: 0.6, pitch: 0.8 });
    spawnItem({ item: 'apple' }, { x: X + 0.6, y: 3, z: Z + 0.3 }, { x: 0, y: 1, z: 0.2 }, { pickAt: 0.8 });
    spawnItem({ item: 'blocks/sapling_oak' }, { x: X - 0.6, y: 3, z: Z + 0.3 }, { x: 0, y: 1, z: 0.2 }, { pickAt: 0.8 });
    tree.dispose();
    yield 1.0; yield* waitItems();
  }

  // =============================================================== a snack
  function* actEat() {
    const food = R() < 0.5 ? 'bread' : 'apple';
    yield* walkTo(L.dance.x + 1.0, L.dance.z - 0.4);
    yield* faceYaw(yawFor(-0.3, 1));
    frame(b.x, b.z, 3.2, 1.2, 0.6);
    hold({ item: food });
    onCleanup(() => hold(null));
    yield 0.6;
    // item use lasts 32 ticks; from tick 7 on, every fourth tick plays random.eat with crumbs, then the burp
    let t = 0, n = 0;
    b.head.tpitch = 0.1;
    yield (dt) => {
      t += dt;
      const a = Math.sin(t * 22) * 0.08;
      setArm('r', 2.05 + a, -0.35);
      if (t > 0.35 && t > 0.35 + n * 0.2) {
        n++;
        snd('random.eat', { pos: mouth(), volume: 0.5, pitch: [0.9, 1.15] });
        fx.chips(mouth(), CRUMB[food], 4, { speed: 0.6, up: 0.5, size: 0.04, life: 0.5 });
      }
      return t >= 1.6;
    };
    freeArm('r');
    hold(null);
    snd('random.burp', { volume: 0.5, pitch: [0.95, 1.05] });
    b.head.tpitch = -0.1;
    yield 0.9;
  }

  // =============================================================== the dog
  function* actDog() {
    hold({ item: 'beef_raw' });
    onCleanup(() => { hold(null); crit.hold(wolf, false); });
    crit.hold(wolf, true);
    const d = dirOf(b.yaw);
    yield* standAt(L.dance.x - 2.4, L.dance.z - 1.0, yawFor(1, 1));
    frame(b.x, b.z, 3.2, 1.2, 0.6);
    // he holds the meat out and whistles the dog over
    setArm('r', 1.5, -0.1);
    b.head.target = V(wolf.x, 0.6, wolf.z);
    yield 0.4;
    const gx = b.x + dirOf(b.yaw).x * 1.1, gz = b.z + dirOf(b.yaw).z * 1.1;
    yield crit.go(wolf, gx, gz, 2.6);
    wolf.moving = false;
    yield crit.face(wolf, b.x, b.z, 9);
    play('mob.wolf.panting', { pos: { x: wolf.x, y: 0.6, z: wolf.z }, volume: 0.5, ref: 5 });
    yield 0.5;
    // the wolf eats: head down, the game's eating sound, crumbs, then the hearts
    wolf.pitchT = 0.7;
    freeArm('r'); hold(null);
    for (let i = 0; i < 4; i++) { snd('random.eat', { pos: { x: wolf.x, y: 0.5, z: wolf.z }, volume: 0.5, pitch: [0.9, 1.2] }); fx.chips({ x: wolf.x, y: 0.4, z: wolf.z }, CRUMB.beef_raw, 3, { speed: 0.5, up: 0.4, size: 0.04, life: 0.5 }); yield 0.22; }
    wolf.pitchT = 0;
    heartsAt({ x: wolf.x, y: 0.9, z: wolf.z }, 5);
    snd('mob.wolf.bark', { pos: { x: wolf.x, y: 0.6, z: wolf.z }, volume: 0.6, pitch: [1.0, 1.15], ref: 5 });
    yield 0.6;
    // a pat on the head (the arm comes down and rubs), the tail going
    b.head.tpitch = 0.4; setArm('r', 1.0, 0.1); yield 0.35; setArm('r', 0.8, 0.1); yield 0.35; setArm('r', 1.0, 0.1); yield 0.6;
    freeArm('r');
    yield 0.5;
    crit.hold(wolf, false);
  }

  // =============================================================== shearing and milking
  function* approach(c, gap = 1.05) {
    crit.hold(c, true);
    const dx = b.x - c.x, dz = b.z - c.z, d = Math.hypot(dx, dz) || 1;
    const px = c.x + (dx / d) * gap, pz = c.z + (dz / d) * gap;
    yield* walkTo(px, pz);
    c.path = null;
    yield* faceAt(c.x, c.z);
  }
  function* actShear() {
    if (!sheep || sheep.sheared) return;
    onCleanup(() => crit.hold(sheep, false));
    yield* approach(sheep);
    frame(sheep.x, sheep.z, 3.4, 1.2, 0.5);
    hold({ item: 'shears' });
    onCleanup(() => hold(null));
    lookAt(sheep.x, 0.8, sheep.z);
    yield 0.4;
    yield* tapOn(2, 0.25);
    const p = { x: sheep.x, y: 0.8, z: sheep.z };
    snd('mob.sheep.shear', { pos: p, volume: 0.9, pitch: 1 });
    crit.shear(sheep, true);
    sheep.regrowT = 40;
    fx.chips(p, [0xf2f2f2, 0xe0e0e0, 0xd0d0d0], 14, { speed: 1.2, up: 0.8 });
    for (let i = 0; i < 2 + Math.floor(R() * 2); i++) spawnItem({ block: 'wool_colored_white' }, p, { x: R(-0.6, 0.6), y: 3, z: R(0.6, 1.2) }, { pickAt: 0.9 });
    yield 0.5;
    snd('mob.sheep.say', { pos: p, volume: 0.6, pitch: 1.1 });
    yield 0.6; yield* waitItems();
    hold(null); b.head.target = null;
    yield 0.4;
  }
  function* actMilk() {
    if (!cow) return;
    onCleanup(() => crit.hold(cow, false));
    hold({ item: 'bucket_empty' });
    onCleanup(() => hold(null));
    yield* approach(cow, 1.15);
    frame(cow.x, cow.z, 3.4, 1.2, 0.5);
    lookAt(cow.x, 0.6, cow.z);
    yield 0.4;
    yield* tapOn(1, 0.5);
    snd('mob.cow.say', { pos: { x: cow.x, y: 1, z: cow.z }, volume: 0.6, pitch: [0.95, 1.05] });
    hold({ item: 'bucket_milk' });
    yield 0.5;
    crit.hold(cow, false);
    b.head.target = null;
    // he drinks it right there: item use plays random.drink every four ticks
    b.head.tpitch = -0.1;
    let t = 0, n = 0;
    yield (dt) => {
      t += dt;
      setArm('r', 2.0 + Math.sin(t * 20) * 0.05, -0.3);
      if (t > 0.35 && t > 0.35 + n * 0.2) { n++; snd('random.drink', { pos: mouth(), volume: 0.5, pitch: [0.9, 1.1] }); fx.chips(mouth(), CRUMB.bucket_milk, 3, { speed: 0.5, up: 0.4, size: 0.04, life: 0.5 }); }
      return t >= 1.5;
    };
    freeArm('r');
    hold({ item: 'bucket_empty' });
    yield 0.9;
  }

  // =============================================================== torches at dusk
  function torchMesh() {
    const g = new THREE.BoxGeometry(2 / 16, 10 / 16, 2 / 16);
    const uv = g.attributes.uv;
    const set = (f, u0, v0, u1, v1) => { const o = f * 4; uv.setXY(o, u0, v1); uv.setXY(o + 1, u1, v1); uv.setXY(o + 2, u0, v0); uv.setXY(o + 3, u1, v0); };
    for (const f of [0, 1, 4, 5]) set(f, 7 / 16, 0, 9 / 16, 10 / 16);
    set(2, 7 / 16, 0.5, 9 / 16, 10 / 16); set(3, 7 / 16, 0, 9 / 16, 2 / 16);
    const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ map: tex('blocks/torch_on.png'), alphaTest: 0.4 }));
    m.position.y = 5 / 16;
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture('rgba(255,170,70,1)'), color: 0xffa050, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.7 }));
    glow.scale.set(0.9, 0.9, 1); glow.position.y = 0.75;
    const grp = new THREE.Group(); grp.add(m, glow);
    return { grp, glow };
  }
  function* actTorches() {
    const spots = [[4.2, 3.2], [3.9, 5.4], [4.6, 7.2]].map(([x, z]) => nav.nearestFree(x, z, 0.3));
    hold({ item: 'blocks/torch_on' });
    onCleanup(() => hold(null));
    const placed = [];
    for (const s of spots) {
      yield* walkTo(s.x + 0.9, s.z + 0.2);
      yield* faceAt(s.x, s.z);
      lookAt(s.x, 0.1, s.z);
      yield 0.2;
      yield* tapOn(1, 0.3);
      const t = torchMesh();
      t.grp.position.set(s.x, 0, s.z);
      world.add(t.grp);
      const ent = entity(new THREE.Group(), (dt) => { t.glow.material.opacity = 0.62 + 0.12 * Math.sin(b.t * 13 + s.x) + 0.06 * Math.sin(b.t * 27); if (R() < dt * 2) fx.sparks({ x: s.x, y: 0.7, z: s.z }, 0xffb050, 1, { speed: 0.1 }); return false; });
      onCleanup(() => { world.remove(t.grp); const i = b.items.indexOf(ent); if (i >= 0) b.items.splice(i, 1); });
      placed.push({ t, s, ent });
      snd('dig.wood', { pos: { x: s.x, y: 0.3, z: s.z }, volume: 0.8, pitch: [0.9, 1.1] });
      yield 0.3;
    }
    // back up and take a look at the lit path
    yield* walkTo(spots[0].x + 1.8, spots[0].z - 1.8);
    frame(4.2, 5.4, 6.5, 2.2, 0.5);
    b.head.target = null; b.head.tyaw = 0.4;
    yield 2.4;
    // then pick them up again, a swing each
    hold({ item: 'wood_pickaxe' });
    for (const p of placed.reverse()) {
      yield* walkTo(p.s.x + 0.9, p.s.z + 0.2);
      yield* faceAt(p.s.x, p.s.z);
      yield* armSwing(1, 0.3, () => {
        world.remove(p.t.grp);
        const i = b.items.indexOf(p.ent); if (i >= 0) b.items.splice(i, 1);
        snd('dig.wood', { pos: { x: p.s.x, y: 0.3, z: p.s.z }, volume: 0.8, pitch: [0.85, 1] });
        fx.chips({ x: p.s.x, y: 0.4, z: p.s.z }, [0xa07e48, 0xffb040], 6, { speed: 0.8 });
        spawnItem({ item: 'blocks/torch_on' }, { x: p.s.x, y: 0.5, z: p.s.z }, { x: 0, y: 2.5, z: 0.3 }, { pickAt: 0.5 });
      });
      yield 0.3;
    }
    yield* waitItems();
  }

  // =============================================================== reading on the log
  function* actRead() {
    yield* walkTo(L.seatApproach.x, L.seatApproach.z);
    yield* faceYaw(Math.PI);
    frame(L.seatPos.x, L.seatPos.z, 5.2, 2.2, 0.9);
    ignoring('low');
    yield* walkTo(L.seatPos.x, L.seatPos.z, { straight: true, speed: 1.1 });
    yield* faceYaw(Math.PI);
    b.sitT = 1; b.sitStep = 'wood';
    onCleanup(() => { b.sitT = 0; hold(null); });
    hold({ item: 'book_normal' });
    setArm('r', 1.25, -0.2); setArm('l', 1.25, 0.2);
    b.head.tpitch = 0.45;
    yield 1.2;
    for (let i = 0; i < 4; i++) {
      b.head.tyaw = 0.06; yield R(1.6, 2.4);
      // turn the page
      setArm('r', 1.45, -0.05); yield 0.25; setArm('r', 1.25, -0.2); b.head.tyaw = -0.06;
      yield R(1.4, 2.2);
      if (i === 1) { b.head.tpitch = 0.05; yield 0.8; b.head.tpitch = 0.45; }
    }
    hold(null); b.sitT = 0; relax();
    yield 0.6;
    yield* walkTo(L.seatApproach.x, L.seatApproach.z, { straight: true, speed: 1.1 });
  }

  // =============================================================== archery
  function arrowMesh() {
    const t = tex('entity/arrow.png');
    const mat = new THREE.MeshLambertMaterial({ map: t, alphaTest: 0.3, side: THREE.DoubleSide, emissive: 0x303030 });
    const g = new THREE.Group();
    const shaft = (rot) => {
      const q = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.12), mat);
      const uv = q.geometry.attributes.uv, u0 = 0, u1 = 0.5, v0 = 1 - 10 / 32, v1 = 1 - 5 / 32;
      uv.setXY(0, u0, v1); uv.setXY(1, u1, v1); uv.setXY(2, u0, v0); uv.setXY(3, u1, v0);
      q.rotation.x = rot; return q;
    };
    g.add(shaft(0), shaft(Math.PI / 2));
    for (const rot of [0, Math.PI / 2]) {
      const q = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 0.14), mat);
      const uv = q.geometry.attributes.uv; uv.setXY(0, 0, 1); uv.setXY(1, 5 / 32, 1); uv.setXY(2, 0, 1 - 5 / 32); uv.setXY(3, 5 / 32, 1 - 5 / 32);
      q.rotation.y = Math.PI / 2; q.rotation.x = rot; q.position.x = -0.46; g.add(q);
    }
    return g;
  }
  function* actBow() {
    const T = L.target, S0 = L.shoot;
    // the hay bale target
    const hs = tex('blocks/hay_block_side.png'), ht = tex('blocks/hay_block_top.png');
    const hay = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), [hs, hs, ht, ht, hs, hs].map((x) => new THREE.MeshLambertMaterial({ map: x })));
    hay.position.set(T.x, 0.5, T.z); hay.castShadow = hay.receiveShadow = true;
    world.add(hay);
    const box = nav.add('hay', T.x - 0.5, T.z - 0.5, T.x + 0.5, T.z + 0.5, 'solid');
    onCleanup(() => { world.remove(hay); nav.remove(box); hold(null); });
    snd('step.cloth', { pos: { x: T.x, y: 0.5, z: T.z }, volume: 0.5 });
    yield* walkTo(S0.x, S0.z);
    yield* faceAt(T.x, T.z);
    frame(3.5, 5.8, 8.5, 2, 0.3);
    const arrows = [];
    onCleanup(() => { for (const a of arrows) world.remove(a); });
    for (let shot = 0; shot < 3; shot++) {
      hold({ item: 'bow_standby' });
      setArm('r', 1.5, -0.05); setArm('l', 1.45, 0.15);
      lookAt(T.x, 1.0, T.z);
      yield 0.5;
      // draw: bow_pulling_0, _1, _2 (the game's stages), a breath at full draw
      hold({ item: 'bow_pulling_0' }); yield 0.25;
      hold({ item: 'bow_pulling_1' }); yield 0.25;
      hold({ item: 'bow_pulling_2' }); yield R(0.3, 0.6);
      // release
      const dir = dirOf(b.yaw);
      const dist = Math.hypot(T.x - b.x, T.z - b.z);
      const v = 17, g = 20, sin2 = clamp(g * dist / (v * v), 0, 0.99);
      const pitch = 0.5 * Math.asin(sin2) + R(-0.02, 0.025);
      const yawErr = R(-0.03, 0.03);
      const cs = Math.cos(yawErr), sn = Math.sin(yawErr);
      const hx = dir.x * cs - dir.z * sn, hz = dir.x * sn + dir.z * cs;
      snd('random.bow', { pos: { x: b.x, y: 1.4, z: b.z }, volume: 1, pitch: [1.12, 1.33] });
      hold({ item: 'bow_standby' });
      const arrow = arrowMesh();
      arrow.position.set(b.x + dir.x * 0.5, b.y + 1.35, b.z + dir.z * 0.5);
      world.add(arrow); arrows.push(arrow);
      const vel = V(hx * Math.cos(pitch) * v, Math.sin(pitch) * v, hz * Math.cos(pitch) * v);
      let stuck = false, wob = 0;
      const e = entity(new THREE.Group(), (dt) => {
        if (stuck) { wob += dt; arrow.rotation.z = Math.sin(wob * 60) * 0.12 * Math.max(0, 1 - wob / 0.25); return false; }
        vel.y -= g * dt;
        arrow.position.addScaledVector(vel, dt);
        arrow.quaternion.setFromUnitVectors(V(1, 0, 0), vel.clone().normalize());
        const ax = arrow.position.x, ay = arrow.position.y, az = arrow.position.z;
        if (ax > T.x - 0.5 && ax < T.x + 0.5 && az > T.z - 0.5 && az < T.z + 0.5 && ay < 1 && ay > 0) {
          stuck = true;
          arrow.position.addScaledVector(vel.clone().normalize(), 0.12);
          snd('random.bowhit', { pos: arrow.position, volume: 1, pitch: [1.1, 1.33] });
          fx.chips(arrow.position, [0xc9a64a, 0xa8892f], 6, { speed: 0.6, up: 0.5 });
        } else if (ay < 0.02) { stuck = true; arrow.position.y = 0.02; snd('random.bowhit', { pos: arrow.position, volume: 0.6, pitch: 1.3 }); }
        return false;
      });
      onCleanup(() => { const i = b.items.indexOf(e); if (i >= 0) b.items.splice(i, 1); });
      yield 0.5;
      relax();
      b.head.target = null;
      yield R(0.6, 1.1);
    }
    yield 0.6;
    // collect the arrows
    yield* walkTo(T.x - 1.5, T.z + 0.1);
    for (const a of arrows) { snd('random.pop', { pos: a.position, volume: 0.6, pitch: [1.1, 1.4] }); world.remove(a); yield 0.25; }
    arrows.length = 0;
    hold(null);
    yield 0.4;
  }

  // =============================================================== the note block
  function* actNotes() {
    yield* walkTo(L.noteStand.x, L.noteStand.z);
    yield* faceYaw(0);
    frame(L.note.cx + 0.5, L.note.cz + 0.5, 3.8, 1.4, -1.5);
    lookAt(L.note.cx + 0.5, 0.6, L.note.cz + 0.5);
    const P = { x: L.note.cx + 0.5, y: 1.1, z: L.note.cz + 0.5 };
    // block under it is grass/dirt: harp. Each right-click raises the pitch one semitone (note 0..24)
    const tune = [12, 12, 19, 19, 21, 21, 19, 17, 17, 16, 16, 14, 14, 12];
    const pitchOf = (n) => Math.pow(2, (n - 12) / 12);
    const colorOf = (n) => { const f = n / 24; const r = Math.max(0, Math.sin((f + 0) * TAU) * 0.5 + 0.5), g = Math.max(0, Math.sin((f + 1 / 3) * TAU) * 0.5 + 0.5), bl = Math.max(0, Math.sin((f + 2 / 3) * TAU) * 0.5 + 0.5); return (Math.round(r * 255) << 16) | (Math.round(g * 255) << 8) | Math.round(bl * 255); };
    // tuning: a few right-clicks climbing from the first note
    for (let n = 0; n < 4; n++) { yield* tapOn(1, 0.18); snd('note.harp', { pos: P, volume: 1, pitch: pitchOf(n * 2 + 10), ref: 8 }); }
    yield 0.4;
    // then the tune, one punch per note
    for (let i = 0; i < tune.length; i++) {
      setArm('r', 1.25, -0.12); yield 0.06; setArm('r', 0.95, -0.12);
      const n = tune[i];
      snd('note.harp', { pos: P, volume: 1, pitch: pitchOf(n), ref: 8 });
      fx.sparks(P, colorOf(n), 2, { speed: 0.25 });
      b.head.tpitch = 0.12; yield 0.14; b.head.tpitch = 0;
      yield i === 6 || i === 13 ? 0.62 : 0.3;
    }
    yield 0.5;
  }

  // =============================================================== the dirt hut
  function* actHut() {
    const H = L.hut, x0 = H.cx, z0 = H.cz;
    const cells = [];
    for (let dx = 0; dx < 3; dx++) for (let dz = 0; dz < 3; dz++) {
      const edge = dx === 0 || dx === 2 || dz === 0 || dz === 2;
      const door = dx === 1 && dz === 2;
      for (let y = 0; y < 2; y++) if (edge && !door) cells.push([x0 + dx, y, z0 + dz]);
      if (door) cells.push([x0 + dx, 1, z0 + dz, 'top']);
      cells.push([x0 + dx, 2, z0 + dz, 'roof']);
    }
    cells.sort((p, q) => p[1] - q[1]);
    // the roof's centre goes last so he can place it from the doorway
    const stand = { x: x0 + 1.5, z: z0 + 3.45 };
    yield* walkTo(stand.x, stand.z);
    yield* faceAt(x0 + 1.5, z0 + 1.5);
    frame(5.5, 0.5, 8, 3, 0.6);
    hold({ block: 'dirt' });
    onCleanup(() => hold(null));
    const blocks = [];
    for (const [cx, cy, cz] of cells) {
      lookAt(cx + 0.5, cy + 0.5, cz + 0.5);
      yield* armSwing(1, 0.28, () => { blocks.push(placeBlock('dirt.png', cx + 0.5, cy, cz + 0.5)); });
      yield 0.12;
    }
    b.head.target = null; relax(); hold(null);
    yield 0.9;
    // step inside, have a look round, come out
    yield* walkTo(x0 + 1.5, z0 + 1.5);
    b.head.tyaw = 0.7; yield 0.8; b.head.tyaw = -0.7; yield 0.8; b.head.tyaw = 0;
    yield* walkTo(x0 + 1.5, z0 + 3.2);
    yield* faceAt(x0 + 1.5, z0 + 1.5);
    yield 0.5;
    // and break it down again, the roof first, with a shovel
    hold({ item: 'wood_shovel' });
    for (const blk of blocks.reverse()) {
      const p = { x: blk.m.position.x, y: blk.m.position.y, z: blk.m.position.z };
      lookAt(p.x, p.y, p.z);
      yield* armSwing(1, 0.26, () => { snd('dig.gravel', { pos: p, volume: 0.7, pitch: [0.9, 1.1] }); });
      breakBlock(blk, p, 'dirt.png');
      if (R() < 0.3) spawnItem({ block: 'dirt' }, p, { x: R(-0.3, 0.3), y: 3, z: 1.4 }, { pickAt: 0.6 });
      yield 0.1;
    }
    yield 0.7; yield* waitItems();
    hold(null);
  }

  // =============================================================== skipping a stone on the pond
  function* actStones() {
    const sp = L.pond.stand;
    yield* walkTo(sp.x + 0.6, sp.z + 0.6);
    frame(-3, 3, 4.8, 1.6, 0.8);
    // pick up a flat stone from the shore
    b.crouchT = 1; b.head.tpitch = 0.4; yield 0.6;
    snd('random.pop', { volume: 0.4, pitch: 1.3 });
    hold({ item: 'flint' });
    b.crouchT = 0; yield 0.4;
    onCleanup(() => hold(null));
    yield* standAt(sp.x, sp.z, Math.PI / 2);
    b.head.tpitch = 0;
    for (let n = 0; n < 2; n++) {
      yield 0.5;
      setArm('r', -0.6, 0); yield 0.3;
      hold(null);
      setArm('r', 1.4, 0);
      snd('random.bow', { volume: 0.5, pitch: 0.4 / (R() * 0.4 + 0.8) });
      // the stone: low and fast, three skips and a sink, a ring at each touch
      const stone = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.05, 0.12), new THREE.MeshLambertMaterial({ map: tex('blocks/stone.png') }));
      stone.position.set(b.x - 0.4, 1.05, b.z);
      world.add(stone);
      let t = 0, skips = 0, vy = 0.2, vx = -6.5 + R(-0.5, 0.5);
      const e = entity(new THREE.Group(), (dt) => {
        t += dt;
        stone.position.x += vx * dt; stone.position.y += vy * dt; vy -= 9 * dt;
        stone.rotation.y += dt * 12;
        if (stone.position.y < -0.08) {
          const wp = { x: stone.position.x, y: -0.08, z: stone.position.z };
          fx.splash(wp, 5);
          if (skips < 3) { skips++; vy = 1.6 - skips * 0.35; vx *= 0.8; snd('liquid.splash', { pos: wp, volume: 0.25, pitch: 1.5 + skips * 0.15 }); stone.position.y = -0.07; }
          else { snd('liquid.splash', { pos: wp, volume: 0.5, pitch: 1.1 }); world.remove(stone); return true; }
        }
        return stone.position.x < -3.9 && stone.position.y < -0.07 ? (world.remove(stone), true) : false;
      });
      onCleanup(() => { world.remove(stone); const i = b.items.indexOf(e); if (i >= 0) b.items.splice(i, 1); });
      lookAt(stone.position.x - 2.0, -0.1, stone.position.z);
      yield 1.2;
      b.head.target = null; freeArm('r');
      if (n === 0) { b.head.tpitch = 0.2; yield 0.5; setArm('r', 0.2, 0.5); yield 0.7; freeArm('r'); hold({ item: 'flint' }); }
    }
    hold(null);
    yield 0.5;
  }

  // =============================================================== the enchanting table
  function* actEnchant() {
    yield* walkTo(L.enchantStand.x, L.enchantStand.z);
    yield* faceYaw(0);
    frame(L.enchant.cx + 0.5, L.enchant.cz + 0.5, 3.8, 1.4, 1.5);
    lookAt(L.enchant.cx + 0.5, 1.0, L.enchant.cz + 0.5);
    hold({ item: 'iron_pickaxe' });
    onCleanup(() => hold(null));
    yield 1.4; // the book swings open to face him
    yield* tapOn(1, 0.4);
    snd('random.click', { pos: { x: L.enchant.cx + 0.5, y: 1, z: L.enchant.cz + 0.9 }, volume: 0.5, pitch: 1.2 });
    yield 1.0;
    snd('random.click', { pos: { x: L.enchant.cx + 0.5, y: 1, z: L.enchant.cz + 0.9 }, volume: 0.5, pitch: 1 });
    yield 0.5;
    // enchanted: the level-up chime, glitter round the tool
    snd('random.levelup', { volume: 0.7, pitch: 1 });
    snd('random.orb', { volume: 0.6, pitch: 0.9 });
    for (let i = 0; i < 3; i++) { fx.sparks({ x: L.enchant.cx + 0.5, y: 1.2, z: L.enchant.cz + 0.6 }, i % 2 ? 0xb888ff : 0xe0c8ff, 8, { speed: 0.9 }); yield 0.15; }
    hold({ item: 'diamond_pickaxe' });
    yield 0.4;
    b.head.target = null; b.head.tpitch = -0.2;
    setArm('r', 1.65, 0);
    snd('random.levelup', { volume: 0.25, pitch: 1.6 });
    yield 1.6;
    hold(null);
  }

  // =============================================================== the brewing stand
  function* actBrew() {
    yield* walkTo(L.brewStand.x, L.brewStand.z);
    yield* faceYaw(0);
    frame(L.brew.cx + 0.5, L.brew.cz + 0.5, 4.2, 1.5, -1.5);
    const BX = L.brew.cx + 0.5, BZ = L.brew.cz + 0.5;
    lookAt(BX, 0.6, BZ);
    onCleanup(() => { camp.brew.setBottles(0); hold(null); });
    hold({ item: 'potion_bottle_empty' });
    yield 0.4;
    for (let i = 0; i < 3; i++) { yield* tapOn(1, 0.2); camp.brew.setBottles(i + 1, 0x3f76e4); snd('random.click', { pos: { x: BX, y: 0.8, z: BZ + 0.4 }, volume: 0.4, pitch: [1.0, 1.3] }); }
    hold(null);
    yield 0.6;
    // it brews: smoke at the top, the bottles turn colour
    let t = 0;
    const col = [0x3f76e4, 0xc04ae0, 0xe0409a, 0xe8a030][Math.floor(R() * 4)];
    yield (dt) => {
      t += dt;
      if (R() < dt * 10) fx.dust({ x: BX, y: 0.95, z: BZ }, 1, { color: 0x9a9a9a });
      if (t > 3 && t - dt <= 3) camp.brew.setBottles(3, col);
      b.head.tyaw = Math.sin(t * 0.9) * 0.2;
      return t > 4.5;
    };
    b.head.tyaw = 0;
    snd('random.pop', { pos: { x: BX, y: 0.8, z: BZ }, volume: 0.6, pitch: 1.2 });
    camp.brew.setBottles(0);
    hold({ item: 'potion_bottle_drinkable' });
    yield* tapOn(1, 0.3);
    // and drinks one
    let a = 0, n = 0;
    b.head.target = null; b.head.tpitch = -0.15;
    yield (dt) => {
      a += dt;
      setArm('r', 2.0 + Math.sin(a * 20) * 0.05, -0.3);
      if (a > 0.35 && a > 0.35 + n * 0.2) { n++; snd('random.drink', { pos: mouth(), volume: 0.5, pitch: [0.9, 1.1] }); }
      return a >= 1.4;
    };
    freeArm('r');
    fx.sparks({ x: b.x, y: 1.2, z: b.z }, col, 14, { speed: 0.9 });
    hold({ item: 'potion_bottle_empty' });
    yield 1.0;
    hold(null);
  }

  // =============================================================== sprint-jump onto a block
  function* actParkour() {
    const bx = 1.0, bz = 8.2; // out on the grass, a block of cobblestone to jump onto
    const start = { x: -2.6, z: 8.2 };
    yield* walkTo(start.x, start.z);
    yield* faceAt(bx + 0.5, bz);
    frame(0, 8.2, 6.5, 1.8, 0.3);
    const blk = placeBlockFree(bx, bz);
    yield 0.8;
    // sprint at it, jump at the last stride, land on top, a fist in the air, hop off again
    b.state = 'run';
    const target = { x: bx - 0.55, z: bz };
    yield* walkTo(target.x, target.z, { sprint: true, speed: 5.6, straight: true, onStep: (dt, d) => { if (d < 1.4 && !b.air && b.floor === 0 && b.y < 0.05) { jump(7.2); b.floor = 1; } } });
    ignoring('placed');
    b.floor = 1;
    let u = 0;
    const x0 = b.x;
    yield (dt) => { u += dt; b.x = lerp(x0, bx + 0.5, Math.min(1, u / 0.45)); b.ampT = 1; b.phase += dt * 10; return !b.air && u > 0.45; };
    snd('step.stone', { volume: 0.6 });
    fx.dust({ x: bx + 0.5, y: 1, z: bz }, 6);
    b.ampT = 0; b.leanT = 0;
    setArm('r', 3.0, 0.2); b.head.tpitch = -0.2;
    yield 0.9;
    freeArm('r'); b.head.tpitch = 0;
    b.floor = 0;
    yield 0.3;
    jump(4.2); b.x += 0.0;
    u = 0; const x1 = b.x;
    yield (dt) => { u += dt; b.x = lerp(x1, bx + 1.4, Math.min(1, u / 0.4)); return !b.air && u > 0.3; };
    snd('step.grass', { volume: 0.5 });
    world.remove(blk.m); nav.remove(blk.box);
    b.ign.delete('placed');
    yield 0.4;
  }
  function placeBlockFree(x, z) { const blk = placeBlock('cobblestone.png', x + 0.5, 0, z); return blk; }

  // =============================================================== the hole he dug
  function* actHole() {
    const hx = 1, hz = 3; // the cell
    const cx = hx + 0.5, cz = hz + 0.5;
    yield* walkTo(cx + 1.9, cz + 0.1);
    yield* faceAt(cx, cz);
    frame(1.5, 3.5, 5.2, 2, 0.6);
    hold({ item: 'wood_shovel' });
    onCleanup(() => { hold(null); setVoxel(hx, -1, hz, 'grass'); });
    lookAt(cx, 0, cz);
    yield 0.3;
    yield* armSwing(4, 0.33, (i) => { snd('dig.grass', { pos: { x: cx, y: 0, z: cz }, volume: 0.8, pitch: [0.85, 1] }); fx.chips({ x: cx, y: 0.1, z: cz }, [0x6a8a30, 0x866043, 0x7a5c38], 4, { speed: 0.8 }); });
    setVoxel(hx, -1, hz, null);
    spawnItem({ block: 'dirt' }, { x: cx, y: 0.3, z: cz }, { x: 0.8, y: 3, z: 0.3 }, { pickAt: 0.8 });
    fx.chips({ x: cx, y: 0.2, z: cz }, [0x866043, 0x6f4f36], 12, { speed: 1.4, up: 1.4 });
    yield 0.8; yield* waitItems();
    hold(null); freeArm('r'); relax();
    // pleased with himself he strolls off past it, looking at the sky, and walks straight in
    yield* walkTo(cx + 1.9, cz + 0.1);
    yield 0.3;
    b.head.target = V(cx - 6, 14, cz); // the clouds
    let fell = false;
    ignoring('dais');
    yield* walkTo(cx - 2.2, cz, { straight: true, speed: 1.4, onStep: () => { if (!fell && b.x < hx + 1.0) { fell = true; b.floor = -1; b.air = true; b.vy = 0; snd('qf.exclaim', { volume: 0.5, pitch: 1.1 }); showBang(); } } });
    // (he ends the walk climbing out on the far side)
    b.head.target = null;
    yield 0.2;
    b.floor = 0;
    relax();
    yield 0.5;
    b.head.tpitch = 0.45; b.head.tyaw = 0.6; yield 0.7; b.head.tyaw = 0;
    setArm('r', 2.6, -0.5); yield 0.3; setArm('r', 2.75, -0.45); yield 0.3; freeArm('r');
    // fill it back in
    yield* walkTo(cx - 1.9, cz + 0.1);
    yield* faceAt(cx, cz);
    hold({ block: 'dirt' });
    yield* armSwing(1, 0.3, () => { setVoxel(hx, -1, hz, 'grass'); snd('dig.grass', { pos: { x: cx, y: 0, z: cz }, volume: 0.8, pitch: 1 }); fx.chips({ x: cx, y: 0.1, z: cz }, [0x6a8a30, 0x866043], 8, { speed: 0.8 }); });
    hold(null);
    yield 0.5;
  }

  // =============================================================== a creeper at his back
  function* actCreeper() {
    const spot = { x: -4.4, z: 1.1 };
    yield* walkTo(spot.x, spot.z);
    yield* faceAt(L.fireCenter.x, L.fireCenter.z);
    lookAt(L.fireCenter.x, 1.2, L.fireCenter.z);
    const m = crit.spawn('Creeper', -7.5, 7.4);
    onCleanup(() => { crit.remove(m); });
    cam.want = true;
    // humming at the fire, back to the camp's edge, while it walks up on him
    const go = crit.go(m, spot.x + 0.4, spot.z + 1.9, 0.95);
    let nodT = 0;
    yield (dt) => {
      nodT += dt;
      b.head.tpitch = Math.sin(nodT * 3) * 0.04;
      return go(dt) || Math.hypot(m.x - b.x, m.z - b.z) < 2.0;
    };
    // at two blocks it stops and the fuse starts: the hiss, and it swells
    m.path = null; m.moving = false;
    snd('creeper.primed', { pos: { x: m.x, y: 0.8, z: m.z }, volume: 1, pitch: 1 });
    let h = 0, noticed = false, nt = 0;
    yield (dt) => {
      h = Math.min(0.9, h + dt * 0.9); m.hiss = h;
      nt += dt;
      if (nt > 0.55 && !noticed) {
        // his head snaps round first, then his body
        noticed = true; b.head.target = null; b.head.tyaw = 1.1; showBang(); snd('qf.exclaim', { volume: 0.8 });
      }
      return nt > 1.0;
    };
    b.head.tyaw = 0;
    // sprint away; out of range the fuse runs down again
    const away = nav.nearestFree(spot.x + 8.5, spot.z + 3.2, R_P);
    const flee = walkTo(away.x, away.z, { sprint: true, speed: 5.6 });
    let ft = 0;
    const fl = flee[Symbol.iterator]();
    for (;;) {
      const r = fl.next();
      if (r.done) break;
      const v = r.value;
      if (typeof v === 'function') { yield (dt) => { ft += dt; if (ft > 0.55) m.hiss = Math.max(0, m.hiss - dt * 0.7); return v(dt); }; } else yield v;
    }
    yield (dt) => { m.hiss = Math.max(0, m.hiss - dt * 0.9); return m.hiss <= 0; };
    m.hiss = 0;
    b.head.target = V(m.x, 1, m.z);
    yield 1.0;
    // phew
    b.head.target = null; b.head.tpitch = 0.3;
    setArm('r', 2.5, -0.3); yield 0.4; setArm('r', 2.4, -0.3); yield 0.4; freeArm('r');
    snd('mob.creeper.say', { pos: { x: m.x, y: 0.8, z: m.z }, volume: 0.6, pitch: 0.9 });
    // it shuffles off the way it came
    yield crit.go(m, -9.5, 9.5, 1.0);
    crit.remove(m);
    b.head.tpitch = 0;
    yield 0.6;
  }

  return {
    harvest: actHarvest, sapling: actSapling, eat: actEat, dog: actDog, shear: actShear, milk: actMilk, torches: actTorches,
    read: actRead, bow: actBow, notes: actNotes, hut: actHut, stones: actStones, enchant: actEnchant, brew: actBrew,
    parkour: actParkour, hole: actHole, creeper: actCreeper,
  };
}
