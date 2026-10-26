// The audit page: run the page's own resolvers over every drop and every structure and report, for
// each id, what it resolves to or FALLBACK. tools/site/audit_lucky.py loads this page headless and
// reads the JSON in <script id="dumpshot">. Nothing here draws; it only asks.
import { blockSpec, specFiles, bare } from './blockdefs.js';
import { makeBlock } from './blocks.js';
import { tileInfo } from './reel.js';
import { plan, STRUCTS_READY, VOXEL } from './structures.js';
import { makeMob, mobKey } from '../lib/mc/mobs.js';

const URL_OF = (rel) => new URL(rel, import.meta.url).href;
const fileOk = new Map();
function checkFile(f) {
  if (!fileOk.has(f)) fileOk.set(f, fetch(URL_OF('./tex/' + f), { method: 'GET', cache: 'no-store' }).then((r) => r.ok).catch(() => false));
  return fileOk.get(f);
}

// ---- blocks
async function blockRow(id, meta) {
  const spec = blockSpec(id, meta, { item: true });
  if (!spec) return { id, meta, status: 'FALLBACK', why: 'no spec' };
  if (spec.k === 'none') return { id, meta, status: 'none', kind: 'none' };
  const files = specFiles(spec);
  const missing = [];
  for (const f of files) if (!(await checkFile(f))) missing.push(f);
  let built = true, err = null;
  try { const r = makeBlock(id, meta, { item: true }); built = !r.fallback; } catch (e) { built = false; err = String(e); }
  const faces = spec.f ? Object.fromEntries(Object.entries(spec.f)) : undefined;
  const status = missing.length || !built ? 'FALLBACK' : 'ok';
  return { id, meta, status, kind: spec.k, files, faces, missing: missing.length ? missing : undefined, err: err || undefined };
}

// ---- walking a drop's actions
function* actionsOf(acts, path = '') {
  for (const a of acts || []) {
    yield [a, path];
    if (a.t === 'choice') for (const [i, o] of (a.options || []).entries()) yield* actionsOf(o, path + 'choice' + i + '/');
    if (a.t === 'then') yield* actionsOf(a.actions, path + 'then/');
  }
}
const BAD_TEXT = [[/§/, 'leftover §'], [/#/, 'leftover #'], [/NBTTag|ench=|display=|Lore=|=\(|\)\)|\\"/, 'raw NBT']];
function textIssues(field, raw) {
  if (raw == null || raw === '') return [];
  const s = String(raw);
  // colour codes are drawn by the page; what must not appear is what is left after they are read
  const clean = s.replace(/§[0-9a-fk-or]/gi, '').replace(/#[0-9a-fk-or]/gi, '');
  const out = [];
  for (const [re, why] of BAD_TEXT) if (re.test(clean)) out.push({ field, text: s.slice(0, 120), why });
  return out;
}

const TILE_ITEM = { effect: 'minecraft:potion', xp: 'minecraft:experience_bottle', expbottle: 'minecraft:experience_bottle', fireworks: 'minecraft:fireworks' };
const realBlocks = (a) => (a.blocks || []).filter((b) => bare(b.id) !== 'air' && bare(b.id) !== 'fire');
// the same rule as build_lucky.tile_for, written again here so the two can disagree
function mainAction(acts) {
  for (const a of acts || []) if (a.t === 'block' && realBlocks(a).length >= 10) return { kind: 'build', id: 'top' };
  for (const a of acts || []) if (a.t === 'then') for (const b of a.actions || []) if (b.t === 'block' && realBlocks(b).length >= 10) return { kind: 'build', id: 'then' };
  for (const a of acts || []) {
    if (a.t === 'entity' && a.id === 'luckyegg') return { kind: 'item', id: 'minecraft:egg' };
    if (a.t === 'entity' && a.id !== 'random') return { kind: 'mob', id: a.id };
    if (a.t === 'item' && a.id !== 'random') return { kind: 'item', id: a.id };
    if (a.t === 'block' || a.t === 'falling') {
      const r = realBlocks(a);
      if (r.length) return { kind: 'block', id: r[0].id };
    }
    if (a.t === 'tnt' || a.t === 'explosion') return { kind: 'block', id: 'minecraft:tnt' };
    if (a.t === 'structure') return { kind: 'structure', id: a.id };
    if (TILE_ITEM[a.t]) return { kind: 'item', id: TILE_ITEM[a.t] };
    if (a.t === 'choice') for (const o of a.options || []) { const r = mainAction(o); if (r.id !== '?') return r; }
  }
  return { kind: 'text', id: '?' };
}

async function auditDrop(d) {
  const row = { index: d.index, title: d.title, scene: d.scene, blocks: [], items: [], entities: [], equipment: [], text: [], issues: [] };
  const seenB = new Set(), seenI = new Set(), seenE = new Set();
  for (const f of ['title', 'blurb']) row.text.push(...textIssues(f, d[f]));
  for (const [a] of actionsOf(d.actions)) {
    if (a.t === 'block' || a.t === 'falling') {
      for (const b of a.blocks || []) {
        const k = b.id + '#' + (b.meta || 0);
        if (seenB.has(k)) continue;
        seenB.add(k);
        row.blocks.push(await blockRow(b.id, b.meta || 0));
      }
    } else if (a.t === 'tnt') {
      if (!seenB.has('tnt')) { seenB.add('tnt'); row.blocks.push(await blockRow('minecraft:tnt', 0)); }
    } else if (a.t === 'item') {
      const k = a.id + '|' + JSON.stringify(a.icon);
      if (!seenI.has(k)) { seenI.add(k); row.items.push({ id: a.id, name: a.name, icon: a.icon || null, status: a.icon || a.id === 'random' ? 'ok' : 'FALLBACK' }); }
      row.text.push(...textIssues('item.display', a.display), ...textIssues('item.name', a.name));
      for (const l of a.lore || []) row.text.push(...textIssues('item.lore', l));
    } else if (a.t === 'command') {
      if (a.gives) row.items.push({ id: a.gives.id, name: a.gives.name, icon: a.gives.icon || null, status: a.gives.icon ? 'ok' : 'FALLBACK', via: 'command' });
    } else if (a.t === 'entity') {
      const ids = [a.id, ...(a.riding || []).map((r) => (typeof r === 'string' ? r : r && r.id)).filter(Boolean)];
      for (const id of ids) {
        if (seenE.has(id)) continue;
        seenE.add(id);
        if (id === 'Item') { row.entities.push({ id, mobKey: 'item', status: 'ok' }); continue; }
        if (id === 'luckyegg') { row.entities.push({ id, mobKey: 'egg scene', status: 'ok', note: 'drawn by the eggs scene, not a mob model' }); continue; }
        let unknown = true, err = null;
        try { unknown = !!makeMob(id, {}).unknown; } catch (e) { err = String(e); }
        row.entities.push({ id, mobKey: mobKey(id), status: unknown ? 'FALLBACK' : 'ok', err: err || undefined });
      }
      for (const e of a.equipment || []) if (!row.equipment.includes(e)) row.equipment.push(e);
      row.text.push(...textIssues('entity.display', a.display), ...textIssues('entity.name', a.name));
    } else if (a.t === 'message') {
      row.text.push(...textIssues('message', a.text));
    } else if (a.t === 'then') {
      row.text.push(...textIssues('then.label', a.label));
    }
  }
  // the reel tile
  const info = tileInfo(d);
  const main = mainAction(d.actions);
  const t = d.tile || {};
  const tid = t.id || (t.kind === 'build' ? t.from : null) || t.text || null;
  const same = d.scene === 'dud' || (t.kind === main.kind && tid === main.id) || (t.kind === 'text' && main.kind === 'text');
  row.tile = { kind: t.kind, id: tid, art: info.art, ok: info.ok, main, matches: !!same };
  if (!info.ok) row.issues.push('tile has no picture: ' + JSON.stringify(t));
  if (!same) row.issues.push('tile ' + JSON.stringify(t) + ' differs from the main action ' + JSON.stringify(main));
  for (const b of row.blocks) if (b.status === 'FALLBACK') row.issues.push('block ' + b.id + '#' + b.meta + ' FALLBACK');
  for (const i of row.items) if (i.status === 'FALLBACK') row.issues.push('item ' + i.id + ' FALLBACK');
  for (const e of row.entities) if (e.status === 'FALLBACK') row.issues.push('entity ' + e.id + ' FALLBACK');
  for (const x of row.text) row.issues.push('text ' + x.field + ': ' + x.why + ' in ' + JSON.stringify(x.text));
  return row;
}

async function auditStructures() {
  await STRUCTS_READY;
  const out = {};
  const res = await fetch(URL_OF('./data/structures.json')).then((r) => r.json());
  for (const key of Object.keys(res)) {
    const pl = plan(key);
    const row = { name: res[key].name, blocks: [], terrain: [], text: [], issues: [] };
    const seen = new Set();
    for (const c of pl ? pl.cells : []) {
      const k = c.id + '#' + c.meta;
      if (!seen.has(k)) { seen.add(k); row.blocks.push(await blockRow(c.id, c.meta)); }
      if (c.y < 0 && !VOXEL[bare(c.id)]) row.terrain.push({ id: c.id, why: 'no terrain voxel (drawn as a model)', note: true });
      if (c.lines) for (const l of c.lines) row.text.push(...textIssues('sign', l));
    }
    for (const b of row.blocks) if (b.status === 'FALLBACK') row.issues.push('block ' + b.id + '#' + b.meta + ' FALLBACK');
    for (const x of row.text) row.issues.push('text ' + x.field + ': ' + x.why);
    out[key] = row;
  }
  return out;
}

function publish(obj) {
  const el = document.createElement('script');
  el.type = 'application/json'; el.id = 'dumpshot';
  el.textContent = JSON.stringify(obj);
  document.body.appendChild(el);
}

async function main() {
  await STRUCTS_READY;
  const lucky = await fetch(URL_OF('./data/lucky.json')).then((r) => r.json());
  const drops = [];
  for (const d of lucky.drops) drops.push(await auditDrop(d));
  const structures = await auditStructures();
  const issues = drops.reduce((n, d) => n + d.issues.length, 0) + Object.values(structures).reduce((n, s) => n + s.issues.length, 0);
  const result = { drops, structures, summary: { drops: drops.length, structures: Object.keys(structures).length, issues, dropsWithIssues: drops.filter((d) => d.issues.length).length } };
  document.getElementById('out').textContent = JSON.stringify(result.summary);
  publish(result);
}
main().catch((e) => publish({ error: String((e && e.stack) || e) }));
