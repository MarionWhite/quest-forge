// Review frames for the Krypt's own mob skins (tools/textures/mobs/paint_mobs.py), for tools/site/dump_frames.py:
//   graves/?dump=1&skinreview=Zombie&dist=6&ang=0      the mob on the floor `dist` blocks ahead of the Krypt's dump
//                                                       camera, turned `ang` degrees from facing it (45: three-quarter)
//   &aimy=1.7   the height above the mob's floor the camera looks at (default 0.6 of its height)
//   &t=0        its idle animation time      &vanillaskins   the same frame in the vanilla skin
//   &scale=0.4  shrinks it (a ghast's face is in the ceiling of most corridors at full size)
// It is lit like the scares' mobs (the Krypt's torches plus a fixed ambient, patchBake) and replaces #dumpshot with
// its frame, as mood.js and scares.js do. skins.js imports this only under ?skinreview: visitors never load it.
import * as THREE from "three";
import { makeMob, whenMobTexturesLoaded } from "../../../lib/mc/mobs.js";
import { patchBake } from "../../krypt.js";

const QS = new URLSearchParams(location.search);
const wait = async (fn, max = 30000) => {
  const t0 = performance.now();
  while (!fn() && performance.now() - t0 < max) await new Promise((r) => setTimeout(r, 120));
  return fn();
};

export async function review() {
  const kr = await wait(() => (window.__krypt && window.__krypt.scene ? window.__krypt : null));
  const shot = await wait(() => document.getElementById("dumpshot"));
  if (!kr || !shot) return;
  const errors = [];
  let base = {}, png = "", info = {};
  try {
    base = JSON.parse(shot.textContent);
    kr.takeover(true);
    const cam = kr.camera;
    const pos = new THREE.Vector3().fromArray(base.pos), look = new THREE.Vector3().fromArray(base.look);
    const fwd = look.clone().sub(pos).setY(0).normalize();
    const id = QS.get("skinreview") || "Zombie";
    const dist = Number(QS.get("dist") ?? 6), ang = Number(QS.get("ang") ?? 0);
    const at = pos.clone().addScaledVector(fwd, dist);
    let by = Math.floor(pos.y);
    for (let n = 0; n < 12 && !kr.solidAt(at.x, by + 0.5, at.z); n++) by--;
    at.y = by + 1;
    const m = makeMob(id, QS.has("scale") ? { scale: Number(QS.get("scale")) } : {});
    m.anim(Number(QS.get("t") ?? 0), 0, { walk: 0 });
    const amb = new THREE.Vector3(0.26, 0.25, 0.25);
    m.root.traverse((o) => {
      if (!o.isMesh || !o.material) return;
      for (const mt of [].concat(o.material)) if (mt.isMeshLambertMaterial) patchBake(mt, { fixed: amb });
    });
    const pivot = new THREE.Group();
    pivot.rotation.order = "YXZ";
    pivot.add(m.root);
    pivot.position.copy(at);
    pivot.rotation.y = Math.atan2(-(pos.x - at.x), -(pos.z - at.z)) + ang * Math.PI / 180;   // a mob's front is -z
    kr.scene.add(pivot);
    await whenMobTexturesLoaded();
    cam.position.copy(pos);
    cam.lookAt(at.x, at.y + (QS.has("aimy") ? Number(QS.get("aimy")) : m.height * 0.6), at.z);
    cam.updateMatrixWorld(true);
    kr.composer.render();
    png = kr.renderer.domElement.toDataURL("image/png");
    info = { skinreview: id, vanilla: QS.has("vanillaskins"), dist, ang, at: at.toArray().map((v) => +v.toFixed(2)),
      blocked: kr.solidAt(at.x, at.y + 0.5, at.z), height: +m.height.toFixed(2) };
  } catch (e) { errors.push(String((e && e.stack) || e)); }
  shot.remove();
  const sc = document.createElement("script");
  sc.type = "application/json"; sc.id = "dumpshot";
  sc.textContent = JSON.stringify({ ...base, png: png || base.png, ...info, errors: (base.errors || []).concat(errors) });
  document.body.appendChild(sc);
}
