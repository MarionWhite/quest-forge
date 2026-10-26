// Shared texture loader for the Minecraft library. Paths resolve against site/lib/mc/tex/.
import * as THREE from 'three';

const manager = new THREE.LoadingManager();
let busy = false;
const waiters = [];
manager.onStart = () => { busy = true; };
manager.onLoad = () => { busy = false; while (waiters.length) waiters.shift()(); };
manager.onError = () => { /* a missing texture renders white; the load still completes */ };
const loader = new THREE.TextureLoader(manager);
const cache = new Map();

export const TEXBASE = new URL('./tex/', import.meta.url).href;

export function whenMobTexturesLoaded() {
  return new Promise((resolve) => { if (!busy) resolve(); else waiters.push(resolve); });
}

export function tex(path, o = {}) {
  const key = path + '|' + (o.wrap ? 'w' : '');
  if (cache.has(key)) return cache.get(key);
  const t = loader.load(o.url || TEXBASE + path);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;
  t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false;
  if (o.wrap) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  cache.set(key, t);
  return t;
}
