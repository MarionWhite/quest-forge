// The Lucky Block page: data, odds, the break, the reel, the scenes, the result sheet.
import * as THREE from 'three';
import { createStage, tex, imageLoad, avgColor, colormapSample, iconTexture, whenTexturesLoaded } from './stage.js';
import { makeMob } from './mobs.js';
import { buildReel, plaque, MOOD_COLOR, reelCurve, fillerDrops } from './reel.js';
import { buildScene, puff, burst, pointLight } from './scenes.js';
import { STRUCTS_READY } from './structures.js';

const $ = (s, r = document) => r.querySelector(s);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const params = new URLSearchParams(location.search);
const hash = {};
location.hash.slice(1).split('&').forEach((kv) => { const i = kv.indexOf('='); if (i > 0) hash[decodeURIComponent(kv.slice(0, i))] = decodeURIComponent(kv.slice(i + 1)); });
const PLAYER = 'Steve';
// structure scenes run only on loaded data: the break waits for STRUCTS_READY (or 8 s, then runs without them)
let structsReady = false;
const structsGate = Promise.race([STRUCTS_READY, new Promise((r) => setTimeout(r, 8000))]).then(() => { structsReady = true; if (st.breakBtn) st.breakBtn.disabled = false; });

// ------------------------------------------------------------------ timeline (seconds)
const T_SHATTER = 2.3;
const T_REEL = 3.0;      // camera moves to the reel
const T_SPIN = 3.7;      // the strip starts moving
const SPIN_DUR = 5.0;
const T_WIN = T_SPIN + SPIN_DUR;  // the winner flies to the dais
const T_SCENE = T_WIN + 0.9;

const POS = { player: new THREE.Vector3(3.2, 0, 0.5), dais: new THREE.Vector3(0.5, 1.0, 0.5), reel: new THREE.Vector3(0.5, 1.9, 2.5) };

const EFFECT_COLOR = { Speed: 0x5fb7ff, Slowness: 0x6c7a89, Haste: 0xe8c23a, 'Mining Fatigue': 0x7a6a4a, Strength: 0xc0392b, 'Instant Health': 0xe74c7a, 'Instant Damage': 0x7a1f1f, 'Jump Boost': 0x7de07d, Nausea: 0x6d8a4d, Regeneration: 0xff6fb1, Resistance: 0x4a6fa5, 'Fire Resistance': 0xf08a3c, 'Water Breathing': 0x3f8fd2, Invisibility: 0xcfd6e0, Blindness: 0x2b2b3a, 'Night Vision': 0x3a3ab5, Hunger: 0x8a6a2a, Weakness: 0x6b6b6b, Poison: 0x5fa02a, Wither: 0x2b2b2b, 'Health Boost': 0xf5b7d0, Absorption: 0xf0d25a, Saturation: 0xe0b070 };
const MOODS = ['jackpot', 'good', 'neutral', 'bad', 'deadly'];
const MOOD_LABEL = { jackpot: 'Jackpot', good: 'Good', neutral: 'Neutral', bad: 'Bad', deadly: 'Deadly' };

// ------------------------------------------------------------------ state
const st = {
  onscreen: true,
  data: null, drops: [], luck: 0, counts: {}, custom: false,
  cache: null, phase: 'idle', started: false, T: 0, sceneT: 0, scene: null, reel: null, winner: null,
  fx: [], shake: 0, hurtA: 0, tintC: 0x000000, tintA: 0, chatNode: null, capNode: null,
  stage: null, paused: false, visible: true, sound: false, audio: null, lastTick: -1,
  dirty: false, orig: new Map(), steveSkin: null, forced: null, lastFrame: 0, poster: false,
};
const CTX_POS = POS.player.clone();

// ------------------------------------------------------------------ weights (the mod's formula)
function weightsFor(K) {
  if (st.cache && st.cache.K === K) return st.cache;
  const drops = st.drops;
  const b = 1 / (1 - 0.0077 * Math.abs(K));
  let mn = Infinity, mx = -Infinity;
  for (const d of drops) { if (d.luck < mn) mn = d.luck; if (d.luck > mx) mx = d.luck; }
  const w = new Array(drops.length); let total = 0;
  drops.forEach((d, i) => {
    const e = K >= 0 ? d.luck - mn + 1 : mx - d.luck + 1;
    w[i] = (d.chance ?? 1) * 100 * Math.pow(b, e);
    total += w[i];
  });
  st.cache = { K, w, total };
  return st.cache;
}
const probOf = (i, K) => { const c = weightsFor(K); return c.w[i] / c.total; };
function rollIndex(K) {
  const c = weightsFor(K); let r = Math.random() * c.total;
  for (let i = 0; i < c.w.length; i++) { r -= c.w[i]; if (r < 0) return i; }
  return c.w.length - 1;
}
const clampLuck = (v) => { v = Math.round(Number(v)); if (!isFinite(v)) v = 0; return Math.max(-100, Math.min(100, v)); };
function pct(p) { const v = p * 100; if (v >= 0.1) return v.toFixed(1) + '%'; return '1 in ' + Math.round(1 / Math.max(p, 1e-9)).toLocaleString('en-US'); }

// ------------------------------------------------------------------ data
async function loadData() {
  let d = null;
  try {
    const r = await fetch('data/lucky.json', { cache: 'no-cache' });
    if (r.ok) d = await r.json();
  } catch (e) { d = null; }
  const v2 = d && Array.isArray(d.drops) && d.drops.length && 'scene' in d.drops[0];
  if (!v2) {
    try { const r2 = await fetch('sample.json'); if (r2.ok) d = await r2.json(); } catch (e) { /* keep d */ }
    st.usingSample = true;
  }
  let structures = null;
  try { const r3 = await fetch('data/structures.json'); if (r3.ok) structures = await r3.json(); } catch (e) { /* optional */ }
  st.structures = structures;
  st.data = d;
  st.drops = (d.drops || []).map((x, i) => ({ ...x, index: i, chance: x.chance ?? 1, luck: x.luck ?? 0 })).filter((x) => x.title && x.scene && Array.isArray(x.actions));
  st.crafting = d.craftingItems || [];
  return d;
}

// ------------------------------------------------------------------ chrome: luck, presets, odds
function signed(n) { return (n > 0 ? '+' : n < 0 ? '\u2212' : '') + Math.abs(n); }
const itemById = (id) => st.crafting.find((x) => x.id === id) || null;
// The data's own names, with the two entries it cannot tell apart spelled out (schema: luck 36 is the enchanted apple; the fish at -20 is the pufferfish).
function ingName(item) {
  if (item.id === 'minecraft:golden_apple' && item.luck === 36) return 'Enchanted Golden Apple';
  if (item.id === 'minecraft:fish') return 'Pufferfish';
  return item.name || item.id;
}
function craftIcon(item, size = 32) {
  const s = el('span', 'ing-ic');
  s.style.width = s.style.height = size + 'px';
  if (item.icon) {
    const k = size / 32;
    s.style.backgroundImage = `url(../items/data/icons-${item.icon.s}.png)`;
    s.style.backgroundSize = `${2048 * k}px ${2048 * k}px`;
    s.style.backgroundPosition = `-${item.icon.c * size}px -${item.icon.r * size}px`;
  } else s.classList.add('blank');
  return s;
}
// The 3x3 crafting grid: the centre is the Lucky Block, the eight others are slots.
function renderTable() {
  const grid = $('#cgrid');
  grid.textContent = '';
  for (let i = 0; i < 9; i++) {
    if (i === 4) {
      const c = el('div', 'cell centre empty');
      c.setAttribute('aria-hidden', 'true');
      c.append(el('span', 'lb'));
      grid.append(c);
      continue;
    }
    const si = i < 4 ? i : i - 1;
    const item = st.slots[si] ? itemById(st.slots[si]) : null;
    if (item) {
      const b = el('button', 'cell slot slot-on');
      b.type = 'button';
      b.append(craftIcon(item, 40));
      b.setAttribute('aria-label', `Slot ${si + 1}: ${ingName(item)}, luck ${signed(item.luck)}. Click to empty it.`);
      b.onclick = () => removeSlot(si);
      grid.append(b);
    } else {
      const c = el('div', 'cell slot empty');
      c.setAttribute('aria-label', `Slot ${si + 1}, empty`);
      grid.append(c);
    }
  }
}
function renderTray() {
  const wrap = $('#ings');
  wrap.textContent = '';
  for (const item of st.crafting) {
    const b = el('button', 'ing');
    b.type = 'button';
    b.setAttribute('aria-label', `Place ${ingName(item)} in the next free slot, luck ${signed(item.luck)}`);
    b.append(craftIcon(item, 36));
    const meta = el('span', 'ing-meta');
    meta.append(el('b', '', ingName(item)), el('small', item.luck < 0 ? 'neg' : '', signed(item.luck)));
    b.append(meta);
    b.onclick = () => addIngredient(item.id);
    wrap.append(b);
  }
  if (!st.crafting.length) wrap.append(el('p', 'note', 'No crafting items in the data.'));
}
function addIngredient(id) {
  const i = st.slots.indexOf(null);
  if (i < 0) { $('#slotNote').textContent = 'All eight slots are full. Click a slot to empty it.'; return; }
  st.slots[i] = id;
  st.manual = false;
  $('#slotNote').textContent = '';
  refreshCraft();
}
function removeSlot(i) {
  st.slots[i] = null;
  st.manual = false;
  $('#slotNote').textContent = '';
  refreshCraft();
}
function refreshCraft() { renderTable(); setLuck(lumpLuck()); }
// The sum of the slots, clamped to +-100 (the mod's rule).
function lumpLuck() {
  if (st.manual) return st.manualLuck;
  let s = 0;
  for (const id of st.slots) { const it = id ? itemById(id) : null; if (it) s += it.luck || 0; }
  return clampLuck(s);
}
function setLuck(K) {
  st.luck = clampLuck(K);
  st.cache = null;
  const n = st.luck;
  $('#lukReadout').textContent = signed(n);
  $('#lukBig').textContent = signed(n);
  $('#lukMini').textContent = 'luck ' + signed(n) + (n === 0 ? ' \u00b7 natural block' : '');
  renderOdds();
}

function renderOdds() {
  const body = $('#oddsBody');
  if (!body) return;
  const q = ($('#oddsQ').value || '').trim().toLowerCase();
  const rows = st.drops.map((d, i) => ({ d, i, p: probOf(i, st.luck) }))
    .filter((r) => !q || (r.d.title + ' ' + r.d.blurb + ' ' + r.d.scene).toLowerCase().includes(q))
    .sort((a, b) => b.p - a.p);
  body.textContent = '';
  if (!rows.length) { body.append(el('p', 'note', 'Nothing matches that search.')); return; }
  $('#oddsCount').textContent = `${rows.length} of ${st.drops.length} outcomes at luck ${st.luck > 0 ? '+' : ''}${st.luck}`;
  for (const mood of MOODS) {
    const group = rows.filter((r) => r.d.mood === mood);
    if (!group.length) continue;
    const sec = el('section', 'mood');
    const h = el('h3', '', MOOD_LABEL[mood]);
    h.style.setProperty('--m', '#' + MOOD_COLOR[mood].toString(16).padStart(6, '0'));
    sec.append(h);
    const table = el('div', 'rows');
    for (const r of group) {
      const row = el('div', 'row');
      row.tabIndex = 0;
      const ic = el('span', 'ic');
      if (r.d.icon) { ic.style.backgroundImage = `url(../items/data/icons-${r.d.icon.s}.png)`; ic.style.backgroundSize = '2048px 2048px'; ic.style.backgroundPosition = `-${r.d.icon.c * 32}px -${r.d.icon.r * 32}px`; }
      else { ic.classList.add('blank'); ic.textContent = (r.d.title || '?').charAt(0); }
      const main = el('div', 'main');
      main.append(el('b', '', r.d.title), el('span', 'blurb', r.d.blurb));
      const p = el('span', 'pct', pct(r.p));
      const lk = el('span', 'lk', 'luck ' + (r.d.luck > 0 ? '+' : '') + r.d.luck);
      row.append(ic, main, p, lk);
      row.onclick = () => breakWith(r.i);
      row.onkeydown = (e) => { if (e.key === 'Enter') breakWith(r.i); };
      table.append(row);
    }
    sec.append(table);
    body.append(sec);
  }
}

// ------------------------------------------------------------------ overlays
function say(text, o = {}) {
  const c = $('#caption');
  c.textContent = text;
  c.dataset.at = o.at || 'bottom';
  c.classList.add('on');
}
function hideCaption() { $('#caption').classList.remove('on'); }
function setTint(hex, a) {
  st.tintC = hex; st.tintA = Math.max(st.tintA, a);
}
function applyOverlays() {
  $('#hurt').style.opacity = String(Math.min(1, st.hurtA));
  const t = $('#tint');
  t.style.background = '#' + st.tintC.toString(16).padStart(6, '0');
  t.style.opacity = String(Math.min(0.9, st.tintA));
}
function flashScreen(color, peak, dur) {
  const f = $('#flash');
  f.style.background = color;
  f.animate([{ opacity: peak }, { opacity: 0 }], { duration: Math.max(120, dur * 1000), easing: 'ease-out' });
}
// Minecraft chat line from font/ascii.png (8px glyphs, 16 per row), colour codes honoured.
const FONT = new Image();
FONT.src = new URL('./tex/font/ascii.png', import.meta.url).href;
const MC = { 0: '#000000', 1: '#0000AA', 2: '#00AA00', 3: '#00AAAA', 4: '#AA0000', 5: '#AA00AA', 6: '#FFAA00', 7: '#AAAAAA', 8: '#555555', 9: '#5555FF', a: '#55FF55', b: '#55FFFF', c: '#FF5555', d: '#FF55FF', e: '#FFFF55', f: '#FFFFFF' };
function mcChat(text) {
  const raw = String(text || '').replace(/\{player\}|#playerName/g, PLAYER).replace(/#([0-9a-fk-or])/g, '§$1');
  const cv = document.createElement('canvas');
  const scale = 3;
  const plain = raw.replace(/§./g, '');
  const width = Math.min(1000, Math.max(160, plain.length * 8 * scale + 36));
  cv.width = width; cv.height = 8 * scale + 26;
  const g = cv.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,0.42)';
  g.fillRect(0, 0, cv.width, cv.height);
  g.imageSmoothingEnabled = false;
  const draw = (x, y, color, ch) => {
    const code = ch.charCodeAt(0);
    if (code < 32 || code > 127) return x + 8 * scale;
    const sx = (code % 16) * 8, sy = Math.floor(code / 16) * 8;
    if (!FONT.complete || !FONT.naturalWidth) { g.fillStyle = color; g.fillRect(x, y, 6 * scale, 8 * scale); return x + 8 * scale; }
    g.globalCompositeOperation = 'source-over';
    // shadow in the darker tone, then the glyph in colour
    const tmp = document.createElement('canvas'); tmp.width = 8; tmp.height = 8;
    const tg = tmp.getContext('2d'); tg.drawImage(FONT, sx, sy, 8, 8, 0, 0, 8, 8);
    tg.globalCompositeOperation = 'source-in'; tg.fillStyle = color; tg.fillRect(0, 0, 8, 8);
    g.drawImage(tmp, x + scale, y + scale, 8 * scale, 8 * scale);
    return x + 8 * scale;
  };
  const parts = raw.split(/(§.)/);
  let color = '#FFFFFF', x = 18;
  for (const p of parts) {
    if (/^§./.test(p)) { const c = p[1].toLowerCase(); if (MC[c]) color = MC[c]; else if (c === 'r') color = '#FFFFFF'; continue; }
    for (const ch of p) x = draw(x, 13, color, ch);
  }
  return cv;
}
function chatLine(text) {
  const host = $('#chat');
  host.textContent = '';
  const cv = mcChat(text);
  cv.className = 'mcchat';
  host.append(cv);
  host.classList.add('on');
  st.chatNode = host;
}
function clearOverlays() {
  hideCaption();
  $('#chat').classList.remove('on');
  $('#chat').textContent = '';
  st.hurtA = 0; st.tintA = 0;
}

// ------------------------------------------------------------------ descriptions for the sheet
function strip(text) { return String(text || '').replace(/\{player\}|#playerName/g, PLAYER).replace(/#([0-9a-fk-or])/g, '').replace(/§./g, ''); }
function amountText(a) {
  if (!a) return '';
  const [lo, hi] = a.amount || [1, 1];
  return lo === hi ? String(lo) : `${lo} to ${hi}`;
}
function describe(a) {
  const out = { icon: null, text: '', sub: null, kids: null, cls: '' };
  switch (a.t) {
    case 'item': out.icon = a.icon; out.text = `${amountText(a) ? amountText(a) + ' ' : ''}${a.display || a.name || a.id}`; if (a.ench?.length) out.sub = a.ench.map((e) => `${e[0]} ${e[1]}`).join(', '); break;
    case 'entity': out.text = `${amountText(a)} ${a.display ? a.display + ', the ' : ''}${a.name || a.id}`; if (a.riding?.length) out.sub = 'riding ' + a.riding.join(', '); if (a.spread) out.sub = (out.sub ? out.sub + ' · ' : '') + 'spread ' + a.spread; break;
    case 'xp': out.text = `${amountText(a)} experience orbs`; break;
    case 'tnt': out.text = `${amountText(a)} TNT${a.launched ? ', launched' : ''}`; break;
    case 'expbottle': out.text = `${amountText(a)} experience bottles`; break;
    case 'lightning': out.text = 'A lightning bolt'; break;
    case 'fireworks': out.text = `${amountText(a)} fireworks`; break;
    case 'structure': out.text = a.name || a.id; break;
    case 'falling': out.text = `${(a.blocks || []).length} blocks fall from the sky`; break;
    case 'block': out.text = `${(a.blocks || []).length} blocks placed`; break;
    case 'effect': out.text = `${a.name || 'Effect'}${a.level > 0 ? ' ' + roman(a.level) : ''}${a.duration ? ' for ' + Math.round(a.duration / 20) + 's' : ''}`; out.cls = a.harmful ? 'bad' : ''; break;
    case 'message': out.text = `Chat: ${strip(a.text)}`; break;
    case 'command': out.text = a.gives ? `Gives ${a.gives.name || a.gives.id}` : strip(a.text); break;
    case 'time': out.text = `Time set to ${a.name || a.value}`; break;
    case 'particle': out.text = `${a.id} particles`; break;
    case 'explosion': out.text = `Explosion, power ${a.power}`; break;
    case 'choice': out.text = `One of ${a.options?.length || 0} options rolled`; out.kids = (a.options || []).map((opt, i) => ({ label: `Option ${i + 1}`, acts: opt })); break;
    case 'then': out.text = a.label || 'A second table'; out.kids = [{ label: null, acts: a.actions || [] }]; out.then = true; break;
    default: out.text = a.name || a.id || a.t || 'Something happens';
  }
  return out;
}
function roman(n) { const m = [[10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']]; let s = ''; let v = n + 1; for (const [k, r] of m) while (v >= k) { s += r; v -= k; } return s; }

function renderSheet(drop, p) {
  const sh = $('#sheet');
  sh.textContent = '';
  const head = el('div', 'sh-head');
  head.append(el('p', 'kicker', `${MOOD_LABEL[drop.mood] || 'Outcome'} · ${drop.scene.replace(/_/g, ' ')}`), el('h2', '', drop.title), el('p', 'blurb', drop.blurb));
  head.append(el('p', 'odds-line', `This had a ${pct(p)} chance at luck ${st.luck > 0 ? '+' : ''}${st.luck}.`));
  sh.append(head);
  const list = el('ol', 'timeline');
  const addActs = (acts, depth, parent) => {
    for (const a of acts || []) {
      if (a.t === 'block' && (!a.blocks || !a.blocks.length)) continue;
      const d = describe(a);
      const li = el('li', 'step-row' + (depth ? ' nested' : '') + (d.cls ? ' ' + d.cls : ''));
      const ic = el('span', 'ic');
      if (d.icon) { ic.style.backgroundImage = `url(../items/data/icons-${d.icon.s}.png)`; ic.style.backgroundSize = '2048px 2048px'; ic.style.backgroundPosition = `-${d.icon.c * 32}px -${d.icon.r * 32}px`; }
      else { ic.classList.add('blank'); ic.textContent = a.t === 'then' ? '→' : (a.t || '').charAt(0).toUpperCase(); }
      li.append(ic);
      const body = el('div', 'st-body');
      if (a.t === 'then') body.append(el('span', 'then-l', 'If ' + (d.text.charAt(0).toLowerCase() + d.text.slice(1))));
      else body.append(el('span', 'st-t', d.text));
      if (d.sub) body.append(el('small', 'st-s', d.sub));
      li.append(body);
      parent.append(li);
      if (d.kids) {
        for (const k of d.kids) {
          if (k.label) { const lab = el('li', 'choice-l', k.label + (k.acts?.length ? '' : ' (nothing)')); parent.append(lab); }
          addActs(k.acts, depth + 1, parent);
        }
      }
    }
  };
  addActs(drop.actions, 0, list);
  sh.append(list);
  const foot = el('div', 'sh-foot');
  const again = el('button', 'btn', 'Break another');
  again.type = 'button';
  again.onclick = () => { breakWith(null); };
  const close = el('button', 'btn ghost', 'Close');
  close.type = 'button';
  close.onclick = () => { sh.hidden = true; };
  foot.append(again, close);
  sh.append(foot);
  sh.hidden = false;
}

// ------------------------------------------------------------------ the context a scene gets
function expand(list, n) {
  const out = [];
  for (const e of list) {
    const [lo, hi] = e.amount || [1, 1];
    const k = Math.max(1, Math.round(lo + Math.random() * Math.max(0, hi - lo)));
    for (let i = 0; i < k && out.length < n; i++) out.push(e);
    if (out.length >= n) break;
  }
  return out;
}
function flatten(acts, out = []) {
  for (const a of acts || []) {
    out.push(a);
    if (a.t === 'then') flatten(a.actions, out);
    if (a.t === 'choice') for (const o of a.options || []) flatten(o, out);
  }
  return out;
}
function makeCtx(drop) {
  const acts = flatten(drop.actions);
  const ctx = {
    S: st.stage, drop, fx: st.fx, pos: CTX_POS, dais: POS.dais.clone(), steve: st.stage.steve,
    say, hurt: (a) => { st.hurtA = Math.max(st.hurtA, a); }, tint: (hex, a) => setTint(hex, a), shake: (a) => { st.shake = Math.max(st.shake, a); },
    flashScreen, chat: chatLine, explode: (pos, power) => explodeAt(pos, power),
    setVoxel: (x, y, z, id) => setVoxel(x, y, z, id),
    entities: (n) => {
      const list = acts.filter((a) => a.t === 'entity' && a.id !== 'Item');
      const e = expand(list, n);
      if (!e.length) return [{ id: 'Zombie' }, { id: 'Skeleton' }, { id: 'Creeper' }].slice(0, Math.min(n, 3)).map((x, i) => ({ ...x, amount: [1, 1] }));
      return e.map((x) => ({ id: x.id, name: x.name, color: x.color === 'random' ? null : null, size: x.size, riding: x.riding, display: x.display }));
    },
    items: (n) => {
      const list = acts.filter((a) => a.t === 'item' || (a.t === 'entity' && a.id === 'Item') || (a.t === 'command' && a.gives));
      const out = [];
      for (const a of list) {
        const g = a.t === 'command' ? a.gives : a;
        const lo = (g.amount && g.amount[0]) || 1;
        out.push({ icon: g.icon || null, name: g.display || g.name || g.id, id: g.id, ench: g.ench });
        if (out.length >= n) break;
        void lo;
      }
      return out.slice(0, n);
    },
    blocks: () => {
      const b = acts.find((a) => a.t === 'falling' || a.t === 'block');
      return b ? b.blocks : [];
    },
    stacks: () => {
      const list = acts.filter((a) => a.t === 'entity' && a.riding && a.riding.length);
      return list.length ? list.slice(0, 3).map((e) => [e.id, ...e.riding]) : [['Zombie', 'Zombie', 'Zombie']];
    },
    bossTitle: null,
    chatText: (acts.find((a) => a.t === 'message') || {}).text || '',
    effectName: null, effectColor: null,
  };
  const ef = acts.find((a) => a.t === 'effect');
  if (ef) { ctx.effectName = ef.name || 'Effect'; ctx.effectColor = EFFECT_COLOR[ef.name] ?? 0x9d7bff; }
  if (drop.scene === 'boss') ctx.bossTitle = drop.title;
  return ctx;
}

// Voxel edits: the original is kept so the stage can be restored after each break.
function setVoxel(x, y, z, id) {
  const key = x + ',' + y + ',' + z;
  if (!st.orig.has(key)) st.orig.set(key, st.stage.vox.get(x, y, z));
  st.stage.vox.set(x, y, z, id || null);
  st.dirty = true;
}
function restoreVoxels() {
  for (const [key, id] of st.orig) {
    const [x, y, z] = key.split(',').map(Number);
    st.stage.vox.set(x, y, z, id);
  }
  if (st.orig.size) st.dirty = true;
  st.orig.clear();
}
function explodeAt(pos, power = 1) {
  const S = st.stage;
  puff(makeCtx(st.winner || { actions: [] }), pos, { n: 26, size: 0.6 });
  st.shake = Math.max(st.shake, 0.25 * power);
  burst(makeCtx(st.winner || { actions: [] }), pos.clone().setY(pos.y + 0.2), { n: 36, colors: [0xffd27a, 0xf08a3c, 0x6e6a78], size: 0.2, speed: 3.4, up: 1.6, life: 0.8, additive: true, gravity: 5 });
  const l = pointLight(makeCtx(st.winner || { actions: [] }), 0xffa050, 6, 6, pos.clone());
  S.temp.add(l);
  st.fx.push({ t: 0, update(dt) { this.t += dt; l.intensity = Math.max(0, 6 * (1 - this.t / 0.5)); if (this.t > 0.5) { S.temp.remove(l); return true; } return false; } });
}
function rebuildIfDirty() {
  if (st.dirty) { st.stage.rebuildTerrain(); st.dirty = false; }
}

// ------------------------------------------------------------------ break, reel, scene, result
function resetStage() {
  st.scene = null;
  sceneCamFn = null;
  if (st.reel) { st.stage.reelLayer.remove(st.reel.group); st.reel.dispose(); st.reel = null; }
  st.stage.clearTemp();
  st.stage.clearFragments();
  st.stage.crack.visible = false;
  st.fx.length = 0;
  restoreVoxels();
  rebuildIfDirty();
  st.stage.setNight(0);
  st.stage.sunDrop(0);
  st.stage.lb.visible = true;
  st.stage.halo.visible = true;
  st.stage.steve.root.rotation.set(0, Math.PI / 2, 0);
  st.stage.steve.root.position.set(3.2, 0, 0.5);
  if (st.stage.steve.parts && st.stage.steve.parts.head) st.stage.steve.parts.head.visible = true;
  st.stage.steve.mat.emissive.setRGB(0.05, 0.05, 0.05);
  clearOverlays();
  st.lastTick = -1;
  st.stage.enableDof(false);
}

let breakToken = 0;
// The whole sequence is driven by a clock: step(dt) advances it, and seek(T) replays to T.
function breakWith(forceIndex) {
  if (!st.stage || !structsReady) return;
  $('#titleBox').classList.add('away');
  st.hold = false;
  if (st.phase !== 'idle' && st.phase !== 'result') return;
  $('#sheet').hidden = true;
  resetStage();
  const K = st.luck;
  let idx = forceIndex;
  if (idx == null) idx = st.forced != null ? st.forced : rollIndex(K);
  if (idx == null || !st.drops[idx]) idx = rollIndex(K);
  st.winnerIndex = idx;
  st.winner = st.drops[idx];
  st.started = true;
  st.T = 0;
  st.phase = 'break';
  st.breakToken = ++breakToken;
  st.shatterDone = false;
  st.reelBuilt = false;
  st.sceneBuilt = false;
  st.sceneT = 0;
  st.lastCrack = -1;
  st.palette = st.palette || [0xffffff];
  if (REDUCED) seekTo(1e6, true);
  updateBreakLabels(true);
}
function updateBreakLabels(busy) {
  const b = st.breakBtn;
  b.disabled = busy;
  b.textContent = busy ? 'Breaking' : 'Break it';
}

function shoulderCam() {
  return { pos: new THREE.Vector3(4.7, 2.5, 2.7), look: new THREE.Vector3(0.7, 1.5, 0.5) };
}
function idleCam(t) {
  const a = 0.55 + 0.18 * Math.sin(t * 0.13);
  const R = 11.4;
  return { pos: new THREE.Vector3(1.5 + Math.sin(a) * R, 4.3 + Math.sin(t * 0.21) * 0.25, 0.5 + Math.cos(a) * R), look: new THREE.Vector3(1.4, 1.2, 0.5), fov: 38 };
}
function reelCam(aspect) {
  const dist = aspect < 0.9 ? 6.4 : 4.9;
  return { pos: new THREE.Vector3(POS.reel.x, POS.reel.y + 0.25, POS.reel.z + dist), look: new THREE.Vector3(POS.reel.x, POS.reel.y - 0.05, POS.reel.z), fov: 38 };
}
const ease = (x) => { x = Math.max(0, Math.min(1, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const mix = (a, b, k) => ({ pos: a.pos.clone().lerp(b.pos, k), look: a.look.clone().lerp(b.look, k), fov: (a.fov ?? 38) + ((b.fov ?? 38) - (a.fov ?? 38)) * k });

// The camera at a given point of the break/reel.
function camForTimeline(T, aspect) {
  const idle = idleCam(st.clock || 0);
  const sh = shoulderCam();
  if (T < 0.9) return mix(idle, { pos: sh.pos, look: sh.look, fov: 40 }, ease(T / 0.9));
  if (T < T_REEL) return { pos: sh.pos.clone().lerp(new THREE.Vector3(4.2, 2.3, 2.2), (T - 0.9) / 2.1 * 0.3), look: sh.look, fov: 40 };
  if (T < T_SCENE) {
    const rc = reelCam(aspect);
    const k = ease((T - T_REEL) / 1.0);
    const from = { pos: sh.pos.clone().lerp(new THREE.Vector3(4.2, 2.3, 2.2), 0.3), look: sh.look.clone(), fov: 40 };
    if (T < T_REEL + 1.0) return mix(from, rc, k);
    if (T < T_WIN) return rc;
    // the winner flies into the dais; the camera settles back to the stage
    const k2 = ease((T - T_WIN) / (T_SCENE - T_WIN));
    return mix(rc, sceneCam0(), k2);
  }
  return sceneCamAt(T - T_SCENE);
}
let sceneCamFn = null;
function sceneCam0() { return sceneCamFn ? sceneCamFn(0) : idleCam(0); }
function sceneCamAt(ts) {
  if (!sceneCamFn) return idleCam(st.clock || 0);
  if (st.phase === 'result') return sceneCamFn(st.sceneDur || 0);
  return sceneCamFn(ts);
}

function buildReelNow() {
  const drops = st.drops;
  const N = 60, win = 52;
  const filler = fillerDrops(() => rollIndex(st.luck), N, win, drops).map((d, i) => (i === win ? st.winner : d));
  const reel = buildReel(st.stage, filler, st.winner, N, win);
  reel.group.position.copy(POS.reel);
  st.stage.reelLayer.add(reel.group);
  st.reel = reel;
  st.reel.N = N; st.reel.win = win;
  st.reelBuilt = true;
  const S = st.stage;
  // the strip sits between the camera and the stage: the winner's plaque is the one at the marker
  S.reel = reel;
  void S;
}

function stepTimeline(dt) {
  const S = st.stage;
  st.clock = (st.clock || 0) + dt;
  const T = st.T;
  if (st.phase === 'idle') { return; }
  // crack and swing in the break
  if (T < T_SHATTER) {
    const cp = clamp01((T - 0.9) / (T_SHATTER - 0.9));
    if (T >= 0.5) {
      const p = ((T - 0.5) % 0.5) / 0.5; // the 1.7.10 swing repeats each hit
      swing(p);
    }
    if (T >= 0.9) {
      S.crack.visible = true;
      const stage = Math.min(9, Math.floor(cp * 10));
      if (stage !== st.lastCrack) {
        st.lastCrack = stage;
        S.crackMat.map = tex('blocks/destroy_stage_' + stage + '.png');
        S.crackMat.needsUpdate = true;
        chips(10);
      }
    }
  }
  if (!st.shatterDone && T >= T_SHATTER) {
    st.shatterDone = true;
    S.crack.visible = false;
    S.shatter(56, 1);
    flashScreen('#ffe2b8', 0.55, 0.45);
    st.shake = Math.max(st.shake, 0.22);
    burst(makeCtx(st.winner), POS.dais.clone().setY(1.4), { n: 60, colors: st.palette, size: 0.18, speed: 3.2, up: 2.8, life: 0.9, gravity: 9 });
    st.phase = 'reel';
  }
  if (T >= T_SHATTER) S.stepFragments(dt);
  if (T >= T_REEL && !st.reelBuilt) buildReelNow();
  if (st.reel && T >= T_REEL && T < T_WIN + 0.0) {
    // spin
    const u = clamp01((T - T_SPIN) / SPIN_DUR);
    const p = u <= 0 ? 0 : reelCurve(u, st.reel.win, 0.34);
    const speed = (st.reel.lastP !== undefined ? (p - st.reel.lastP) / Math.max(dt, 1e-3) : 0);
    st.reel.set(p, speed);
    st.reel.lastP = p;
    st.reel.spinAll(st.clock);
    // ticks as tiles pass the marker
    const cell = Math.floor(p + 0.5);
    if (cell !== st.lastTick) { if (st.lastTick >= 0 && st.sound && T >= T_SPIN) tick(); st.lastTick = cell; }
  }
  if (st.reel && T >= T_WIN) {
    // the winner flies into the dais
    const k = ease(clamp01((T - T_WIN) / 0.7));
    const tile = st.reel.tiles[st.reel.win];
    const wp = new THREE.Vector3(POS.reel.x, POS.reel.y, POS.reel.z);
    tile.position.set(0, 0, 0);
    st.reel.tiles.forEach((t2) => { if (t2 !== tile) t2.visible = false; });
    tile.position.copy(new THREE.Vector3(0, 0, 0).lerp(POS.dais.clone().sub(wp).add(new THREE.Vector3(0, 0.5, 0.2)), k));
    const pulse = 1 + 0.12 * Math.sin(Math.PI * clamp01((T - T_WIN) / 0.5));
    tile.scale.setScalar(pulse * (1 - 0.75 * k));
    tile.rotation.y = k * Math.PI * 2;
    if (!st.reel.burst && k >= 1) {
      st.reel.burst = true;
      burst(makeCtx(st.winner), POS.dais.clone().setY(1.4), { n: 80, colors: [0xffffff, MOOD_COLOR[st.winner.mood] || 0xf2c14e, 0xffe08a], size: 0.22, speed: 3.6, up: 3, life: 1.1, additive: true, gravity: 4 });
      flashScreen('#ffffff', 0.5, 0.4);
      st.shake = Math.max(st.shake, 0.18);
    }
    if (T >= T_SCENE) { st.stage.reelLayer.remove(st.reel.group); st.reel.dispose(); st.reel = null; }
  }
  if (T >= T_SCENE) {
    if (!st.sceneBuilt) {
      st.sceneBuilt = true;
      st.phase = 'scene';
            if (st.reel) { st.stage.reelLayer.remove(st.reel.group); st.reel.dispose(); st.reel = null; }
      const ctx = makeCtx(st.winner);
      const sc = buildScene(st.winner.scene, ctx);
      st.scene = sc;
      sceneCamFn = sc.cam;
      st.sceneDur = sc.dur;
      st.fx.length = 0;
      st.stage.steve.mat.emissive.setRGB(0.05, 0.05, 0.05);
      st.stage.lb.visible = false;
      st.stage.halo.visible = false;
      rebuildIfDirty();
      st.sceneCtx = ctx;
    }
    st.sceneT = T - T_SCENE;
    if (st.scene) {
      st.scene.update(st.sceneT, dt);
      if (st.sceneT >= st.sceneDur) { st.phase = 'result'; showResult(); }
    }
  }
  for (let i = st.fx.length - 1; i >= 0; i--) { if (st.fx[i].update && st.fx[i].update(dt)) st.fx.splice(i, 1); }
  rebuildIfDirty();
}
function clamp01(x) { return Math.max(0, Math.min(1, x)); }
function swing(p) {
  // ModelBiped.setRotationAngles, the arm swing of a hit
  const f1 = 1 - (1 - p) ** 3;
  const f2 = Math.sin(f1 * Math.PI);
  const f3 = Math.sin(p * Math.PI) * -0.7;
  const s = st.stage.steve;
  s.parts.rArm.rotation.x = f2 * 1.2 + f3;
  s.parts.body.rotation.y = Math.sin(Math.sqrt(p) * Math.PI * 2) * 0.2;
}
function chips(n) {
  const S = st.stage;
  const c = POS.dais.clone();
  const cols = st.palette;
  burst(makeCtx(st.winner), c.clone().setY(1.5), { n, colors: cols, size: 0.12, speed: 1.6, up: 1.2, life: 0.8, gravity: 9 });
}
async function samplePalette() {
  const img = await imageLoad(new URL('./tex/blocks/lucky_block.png', import.meta.url).href);
  if (!img) return;
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, img.width, img.height).data;
  const out = [];
  for (let i = 0; i < 40; i++) {
    const px = Math.floor(Math.random() * img.width) * 4 + Math.floor(Math.random() * img.height) * img.width * 4;
    if (d[px + 3] > 200) out.push((d[px] << 16) | (d[px + 1] << 8) | d[px + 2]);
  }
  st.palette = out.length ? out : [0xffffff];
}

function tick() {
  try {
    if (!st.audio) st.audio = new (window.AudioContext || window.webkitAudioContext)();
    const ctx = st.audio;
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.type = 'square'; o.frequency.value = 1800;
    g.gain.setValueAtTime(0.05, ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.035);
    o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.04);
  } catch (e) { /* audio is optional */ }
}

function showResult() {
  clearOverlays();
  $('#titleBox').classList.remove('away');
  const K = st.luck;
  const p = probOf(st.winnerIndex, K);
  renderSheet(st.winner, p);
  updateBreakLabels(false);
}

// Seek the whole sequence to T (ms-accurate by stepping at 60 fps).
function seekTo(T, hold) {
  resetStage();
  st.started = true;
  st.phase = 'break';
  st.T = 0; st.clock = 0;
  const step = 1 / 60;
  while (st.T < T) {
    const dt = Math.min(step, T - st.T);
    st.T += dt;
    stepTimeline(dt);
    if (st.phase === 'result') break;
  }
  st.hold = !!hold;
  renderFrame(0, true);
}

// ------------------------------------------------------------------ the loop
let last = 0;
function frame(now) {
  requestAnimationFrame(frame);
  if (!st.stage || st.paused || !st.onscreen || document.hidden) { last = now; return; }
  // guard the first frames: a canvas with no size has nothing to draw into
  if (!st.stage.renderer.domElement.clientHeight || !st.stage.renderer.domElement.clientWidth) { last = now; return; }
  const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
  last = now;
  if (st.hold) { renderFrame(0, true); return; }
  if (st.started && st.phase !== 'result') {
    st.T += dt;
    stepTimeline(dt);
  } else {
    st.clock = (st.clock || 0) + dt;
  }
  renderFrame(dt);
}
function renderFrame(dt, still) {
  const S = st.stage;
  const aspect = S.camera.aspect || 1;
  let cam;
  if (!st.started) cam = idleCam(st.clock || 0);
  else if (st.phase === 'result') cam = sceneCamFn ? sceneCamFn(st.sceneDur) : idleCam(st.clock || 0);
  else cam = camForTimeline(st.T, aspect);
  const sh = st.shake;
  if (sh > 0) {
    cam = { pos: cam.pos.clone().add(new THREE.Vector3((Math.random() - 0.5) * sh, (Math.random() - 0.5) * sh, (Math.random() - 0.5) * sh)), look: cam.look.clone(), fov: cam.fov };
    st.shake = Math.max(0, sh - dt * 2.6);
  }
  // the idle steve breathes and looks at the camera
  const s = S.steve;
  if (!st.started || st.phase === 'idle' || st.phase === 'result' || st.phase === 'reel') {
    if (!st.started || st.phase === 'idle') s.anim((st.clock || 0), dt, { walk: 0 });
  }
  if (st.started && st.phase === 'break') {
    // while breaking the arm is driven by the swing; the rest of the rig idles
    s.anim(st.T, 0, { walk: 0, still: true });
  }
  const look = Math.atan2(cam.pos.x - (S.steve.root.position.x), cam.pos.z - S.steve.root.position.z) - S.steve.root.rotation.y;
  s.parts.head.rotation.y = Math.max(-0.5, Math.min(0.5, Math.atan2(Math.sin(look), Math.cos(look))));
  S.lbMat.emissiveIntensity = 0.5 + 0.12 * Math.sin((st.clock || 0) * 1.7);
  S.enableDof(st.phase === 'scene' && st.sceneT < 1.6 && S.quality === 'high');
  const clk = st.clock || 0;
  S.frame(clk, still ? 0 : dt, { cam });
  applyOverlays();
  st.hurtA = Math.max(0, st.hurtA - dt * 1.2);
  st.tintA = Math.max(0, st.tintA - dt * 0.6);
  if (st.tintA <= 0) st.tintC = 0x000000;
}
// Turn on the stage rendering and the timeline only while it is on screen.
function startLoop() {
  requestAnimationFrame((t) => { last = t; requestAnimationFrame(frame); });
}
// ?dump: after a seek, render once more and put the frame into the DOM as a data URL, so a
// headless browser can read a deterministic picture of the seeked state (`--dump-dom`) without
// racing the compositor. Also records the state the frame was taken in.
function dumpShot() {
  if (!params.has('dump') || !st.stage) return;
  // textures arrive asynchronously; a frame rendered before they land is black silhouettes
  whenTexturesLoaded().then(() => new Promise((r) => setTimeout(r, 50))).then(whenTexturesLoaded).then(() => dumpNow());
}
function dumpNow() {
  try {
    renderFrame(0, true);
    const el = document.createElement('script');
    el.type = 'application/json';
    el.id = 'dumpshot';
    el.textContent = JSON.stringify({
      phase: st.phase, T: st.T, scene: st.winner && st.winner.scene, index: st.winnerIndex, built: !!st.sceneBuilt,
      caption: ($('#caption') || {}).textContent || '', chat: ($('#chat') || {}).textContent || '',
      png: st.stage.renderer.domElement.toDataURL('image/png'),
    });
    document.body.appendChild(el);
  } catch (e) { console.error('dumpShot', e); }
}

// ------------------------------------------------------------------ boot
async function boot() {
  const d = await loadData();
  if (!d) { $('#noData').hidden = false; return; }
  const cvs = $('#cv');
  const webgl = (() => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch (e) { return false; } })();
  // chrome first, so the page is usable before the stage loads
  st.slots = Array(8).fill(null);
  if (params.has('slots')) params.get('slots').split(',').slice(0, 8).forEach((id, i) => { if (itemById(id)) st.slots[i] = id; });
  renderTable();
  renderTray();
  // luck: the hooks, then the counts
  const hookLuck = params.has('luck') ? clampLuck(params.get('luck')) : null;
  if (hookLuck !== null) { st.manual = true; st.manualLuck = hookLuck; setLuck(hookLuck); } else setLuck(lumpLuck());
  if (params.has('force')) st.forced = Number(params.get('force'));
  if (params.has('odds')) $('#odds').open = true;
  const oddsQ = $('#oddsQ');
  oddsQ.addEventListener('input', renderOdds);
  $('#odds').addEventListener('toggle', () => renderOdds());
  $('#snd').addEventListener('change', (e) => { st.sound = e.target.checked; if (st.sound && !st.audio) { try { st.audio = new (window.AudioContext || window.webkitAudioContext)(); } catch (err) { /* no audio */ } } });
  if (!webgl) {
    $('#poster').hidden = false;
    $('#stageBar').hidden = true;
    $('#noGL').hidden = false;
    renderOdds();
    return;
  }
  st.breakBtn = $('#breakBtn');
  st.breakBtn.addEventListener('click', () => breakWith(null));
  addEventListener('keydown', (e) => { if (e.code === 'Space' && !e.target.closest('input,button,select,textarea,summary,a,details,[tabindex="0"]')) { e.preventDefault(); if (!st.breakBtn.disabled) breakWith(null); } });
  const quality = (matchMedia('(max-width: 720px)').matches || matchMedia('(pointer: coarse)').matches) ? 'low' : 'high';
  st.quality = quality;
  try {
    st.stage = await createStage(cvs, { quality });
  } catch (e) {
    console.error(e);
    $('#poster').hidden = false; $('#stageBar').hidden = true; $('#noGL').hidden = false;
    renderOdds();
    return;
  }
  const S = st.stage;
  S.steve.root.position.copy(POS.player);
  const resize = () => {
    const w = cvs.clientWidth, h = cvs.clientHeight;
    if (w && h) S.setSize(w, h);
  };
  addEventListener('resize', resize);
  resize();
  S.enableDof(false);
  samplePalette();
  // the reel and the scene read the structures and the table; start the loop
  const io = new IntersectionObserver((es) => { st.onscreen = es[0].isIntersecting; }, { threshold: 0 });
  io.observe(cvs);
  document.addEventListener('visibilitychange', () => { last = performance.now(); });
  // hooks
  hookCamera();
  renderOdds();
  $('#stageBar').hidden = false;
  $('#breakBtn').disabled = !structsReady;
  $('#skinForm').addEventListener('submit', (e) => { e.preventDefault(); loadSkin($('#skinName').value.trim()); });
  // the URL hooks: ?scene=, ?at=, ?reel=, #demo=
  const want = hashDemo() || (params.has('scene') ? params.get('scene') : null);
  if (params.has('reel')) {
    const frac = Math.max(0, Math.min(1, Number(params.get('reel'))));
    breakWith(params.has('force') ? Number(params.get('force')) : null);
    // freeze on the reel at the fraction
    seekTo(T_SPIN + frac * SPIN_DUR + 0.0001, true);
    dumpShot();
    startLoop();
    return;
  }
  await structsGate;
  if (params.has('at') || want) {
    const idx = params.has('force') ? Number(params.get('force')) : (want ? findScene(want) : null);
    if (want && idx == null) { /* no drop with that scene: play the generic */ }
    const at = params.has('at') ? Number(params.get('at')) / 1000 : T_SCENE + 0.01;
    resetStage();
    st.started = true;
    st.forced = idx != null ? idx : st.forced;
    breakWith(idx);
    seekTo(params.has('at') ? at : T_SCENE + 0.01, true);
    dumpShot();
    startLoop();
    return;
  }
  startLoop();
}
function findScene(key) {
  const i = st.drops.findIndex((d) => d.scene === key);
  return i >= 0 ? i : null;
}
function hashDemo() {
  if (!hash.demo) return null;
  const want = hash.demo;
  const byScene = st.drops.findIndex((d) => d.scene === want || d.mood === want);
  if (byScene >= 0) { st.forced = byScene; return want; }
  return null;
}
function hookCamera() {}

async function loadSkin(name) {
  if (!name) return;
  const url = 'https://api.mineatar.io/skin/' + encodeURIComponent(name);
  try {
    const img = await imageLoad(url);
    if (!img) throw new Error('no skin');
    const t = new THREE.Texture(img);
    t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.needsUpdate = true;
    st.stage.steve.mat.map = t; st.stage.steve.mat.needsUpdate = true;
    $('#skinNote').textContent = 'Showing the skin of ' + name + '.';
  } catch (e) {
    $('#skinNote').textContent = 'No skin for that name. Showing Steve.';
  }
}

boot();
