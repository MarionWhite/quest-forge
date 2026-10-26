// Contact sheets for the accuracy audit (see gallery.html). The page draws into one 2D canvas and,
// under ?dump=1, appends it as a data URL in <script id="dumpshot"> for tools/site/dump_frames.py.
import { frontCanvas, blockIcon } from './reel.js';
import { whenTexturesLoaded } from './stage.js';
import { whenMobTexturesLoaded } from '../lib/mc/mobs.js';
import { bare } from './blockdefs.js';
import { plan, STRUCTS_READY } from './structures.js';

const Q = new URLSearchParams(location.search);
const U = (rel) => new URL(rel, import.meta.url).href;

async function allBlocks(lucky) {
  const seen = new Map();
  const add = (id, meta) => { if (bare(id) !== 'air' && bare(id) !== 'fire') seen.set(id + '#' + (meta || 0), { id, meta: meta || 0 }); };
  const walk = (acts) => {
    for (const a of acts || []) {
      if (a.t === 'block' || a.t === 'falling') for (const b of a.blocks || []) add(b.id, b.meta);
      if (a.t === 'tnt') add('minecraft:tnt', 0);
      if (a.t === 'choice') for (const o of a.options || []) walk(o);
      if (a.t === 'then') walk(a.actions);
    }
  };
  for (const d of lucky.drops) walk(d.actions);
  await STRUCTS_READY;
  const st = await fetch(U('./data/structures.json')).then((r) => r.json());
  for (const k of Object.keys(st)) { const pl = plan(k); for (const c of pl ? pl.cells : []) add(c.id, c.meta); }
  add('lucky:lucky_block', 0);
  return [...seen.values()].sort((a, b) => (a.id + a.meta).localeCompare(b.id + b.meta));
}

function publish(canvas, extra = {}) {
  const el = document.createElement('script');
  el.type = 'application/json'; el.id = 'dumpshot';
  el.textContent = JSON.stringify({ png: canvas.toDataURL('image/png'), ...extra });
  document.body.appendChild(el);
}
const settle = async (ms) => { await whenTexturesLoaded(); await whenMobTexturesLoaded(); await new Promise((r) => setTimeout(r, ms)); await whenTexturesLoaded(); };

async function main() {
  const lucky = await fetch(U('./data/lucky.json')).then((r) => r.json());
  const cols = Number(Q.get('cols')) || (Q.has('tiles') ? 8 : 8);
  let cells = [];
  if (Q.has('tiles')) {
    const [a, b] = Q.get('tiles').split('-').map(Number);
    for (const d of lucky.drops.slice(a, (b ?? a) + 1)) cells.push({ label: d.index + ' ' + d.title, draw: (g, x, y, w, h) => g.drawImage(frontCanvas(d), x, y, w, h), tile: true });
  } else {
    let list;
    if (Q.get('blocks') === 'all') list = await allBlocks(lucky);
    else list = Q.get('blocks').split(',').map((s) => { const [id, m] = s.split('@'); return { id: id.includes(':') ? id : 'minecraft:' + id, meta: Number(m) || 0 }; });
    if (Q.has('from')) list = list.slice(Number(Q.get('from')), Number(Q.get('to')) || undefined);
    const yaw = Q.has('yaw') ? (Number(Q.get('yaw')) * Math.PI) / 180 : -Math.PI / 4;
    for (const b of list) {
      const o = { yaw, world: Q.has('world'), falling: Q.has('falling'), lines: Q.has('lines') ? ['', ...Q.get('lines').split('|'), ''] : undefined };
      cells.push({ label: bare(b.id) + (b.meta ? '@' + b.meta : ''), draw: (g, x, y, w, h) => { const r = blockIcon(b.id, b.meta, o); if (r && r.canvas) g.drawImage(r.canvas, x, y, w, h); else { g.fillStyle = '#f0f'; g.fillRect(x, y, w, h); } } });
    }
  }
  const cw = Q.has('tiles') ? 184 : 150, ch = Q.has('tiles') ? 200 : 168;
  const rows = Math.ceil(cells.length / cols);
  const c = document.createElement('canvas');
  c.width = cols * cw; c.height = rows * ch;
  document.body.appendChild(c);
  const g = c.getContext('2d');
  const paint = () => {
    g.fillStyle = '#1b1624'; g.fillRect(0, 0, c.width, c.height);
    cells.forEach((cell, i) => {
      const x = (i % cols) * cw, y = Math.floor(i / cols) * ch;
      g.imageSmoothingEnabled = true;
      cell.draw(g, x + 2, y + 2, cw - 4, ch - 22);
      g.fillStyle = '#ece6f2'; g.font = '12px ui-monospace, Menlo, monospace'; g.textAlign = 'center';
      g.fillText(cell.label.slice(0, 26), x + cw / 2, y + ch - 6);
    });
  };
  paint();
  await settle(1200);
  paint();
  await settle(600);
  paint();
  if (Q.has('dump')) publish(c, { cells: cells.length });
}
main().catch((e) => { const el = document.createElement('script'); el.type = 'application/json'; el.id = 'dumpshot'; el.textContent = JSON.stringify({ error: String((e && e.stack) || e) }); document.body.appendChild(el); });
