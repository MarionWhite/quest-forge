// The Lucky Block page: data, odds, the break, the reel, the scenes, the result sheet.
import * as THREE from 'three';
import { createStage, tex, imageLoad, avgColor, colormapSample, iconTexture, whenTexturesLoaded } from './stage.js';
import * as MOBS from './mobs.js';
import { audio } from '../lib/qfaudio.js';
import { createBrain } from './steve.js';
import { buildCamp, L } from './camp.js';
import { buildReel, plaque, MOOD_COLOR, reelCurve, fillerDrops } from './reel.js';
import { buildScene, puff, burst, pointLight } from './scenes.js';
import { STRUCTS_READY } from './structures.js';

// Everything that goes wrong on the page is kept for the dump hook.
const ERRORS = [];
addEventListener('error', (e) => { ERRORS.push(String(e.message || e.error || 'error') + (e.filename ? ' @' + String(e.filename).split('/').pop() + ':' + e.lineno : '')); });
addEventListener('unhandledrejection', (e) => { ERRORS.push('rejection: ' + String((e.reason && (e.reason.stack || e.reason.message)) || e.reason)); });
const SFXNAMES = [];
const SFXLOG = new URLSearchParams(location.search).has('sfxlog');
function play(name, o) { if (SFXLOG) { SFXNAMES.push(name); console.info('sfx', name); } return audio.play(name, o); }

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
  stage: null, paused: false, visible: true, lastTick: -1, clock: 0, pre: 0,
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
    .filter((r) => !q || (strip(r.d.title) + ' ' + strip(r.d.blurb) + ' ' + r.d.scene).toLowerCase().includes(q))
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
      else { ic.classList.add('blank'); ic.textContent = (strip(r.d.title) || '?').charAt(0); }
      const main = el('div', 'main');
      main.append(el('b', '', strip(r.d.title)), el('span', 'blurb', strip(r.d.blurb)));
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
// Minecraft colour codes as coloured spans (never the raw "section e"); tuned to read on the dark sheet.
const MC_UI = { 0: '#9aa0a6', 1: '#7580ff', 2: '#3fd95c', 3: '#2fd0d0', 4: '#ff6060', 5: '#d467e6', 6: '#ffb02e', 7: '#cfcfcf', 8: '#9a9a9a', 9: '#8a94ff', a: '#55ff55', b: '#55ffff', c: '#ff6b6b', d: '#ff7bff', e: '#ffee55', f: '#ffffff' };
function colored(text, into) {
  const out = into || document.createDocumentFragment();
  const raw = String(text || '').replace(/\{player\}|#playerName/g, PLAYER).replace(/#([0-9a-fk-or])/g, '\u00a7$1');
  let color = null, bold = false, it = false, ul = false, sk = false;
  for (const part of raw.split(/(\u00a7.)/)) {
    if (/^\u00a7./.test(part)) {
      const c = part[1].toLowerCase();
      if (MC_UI[c]) { color = MC_UI[c]; bold = it = ul = sk = false; }
      else if (c === 'r') { color = null; bold = it = ul = sk = false; }
      else if (c === 'l') bold = true; else if (c === 'o') it = true; else if (c === 'n') ul = true; else if (c === 'm') sk = true;
      continue;
    }
    if (!part) continue;
    const sp = document.createElement('span');
    sp.textContent = part;
    if (color) sp.style.color = color;
    if (bold) sp.style.fontWeight = '800';
    if (it) sp.style.fontStyle = 'italic';
    if (ul || sk) sp.style.textDecoration = (ul ? 'underline ' : '') + (sk ? 'line-through' : '');
    out.append(sp);
  }
  return out;
}
const coloredEl = (tag, cls, text) => { const n = el(tag, cls); colored(text, n); return n; };
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
  head.append(el('p', 'kicker', `${MOOD_LABEL[drop.mood] || 'Outcome'} · ${drop.scene.replace(/_/g, ' ')}`), coloredEl('h2', '', drop.title), coloredEl('p', 'blurb', drop.blurb));
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
      if (a.t === 'then') body.append(coloredEl('span', 'then-l', 'If ' + (d.text.charAt(0).toLowerCase() + d.text.slice(1))));
      else body.append(coloredEl('span', 'st-t', d.text));
      if (d.sub) body.append(coloredEl('small', 'st-s', d.sub));
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
  close.onclick = () => closeResult();
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
    S: st.stage, drop, fx: st.fx, play, particles: st.stage.fx, pos: CTX_POS, dais: POS.dais.clone(), steve: st.stage.steve,
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
// The sequence: the block falls (0 to T_SLAM), slams the dais; Steve stops what he is doing, shows a "!",
// sprints over, hops up and mines it (BREAK_AT s of swings); it shatters (T = T_SHATTER from here on),
// the camera glides to the reel, the reel spins, the scene plays, the sheet opens. Close goes back to idle.
const T_SLAM = 0.6;
const BREAK_AT = 1.7;     // seconds of mining after Steve has arrived
const HIT_AT = [0.2, 0.7, 1.2, 1.7];
const CRACK_AT = [2, 5, 7, 9];

let brain = null, camp = null;
const cf = { pos: new THREE.Vector3(), vel: new THREE.Vector3(), look: new THREE.Vector3(), lvel: new THREE.Vector3(), fov: 38, fvel: 0 };

// A critically damped follow: the velocity is continuous, so the camera never jumps.
function damp1(cur, vel, target, omega, dt) {
  const x = omega * dt, e = 1 / (1 + x + 0.48 * x * x + 0.235 * x * x * x);
  const ch = cur - target, tmp = (vel + omega * ch) * dt;
  return [target + (ch + tmp) * e, (vel - omega * tmp) * e];
}
function dampV(cur, vel, target, omega, dt) {
  for (const k of ['x', 'y', 'z']) { const r = damp1(cur[k], vel[k], target[k], omega, dt); cur[k] = r[0]; vel[k] = r[1]; }
}
function followStep(want, omega, dt) {
  dt = Math.max(dt, 1e-4);
  dampV(cf.pos, cf.vel, want.pos, omega, dt);
  dampV(cf.look, cf.lvel, want.look, omega, dt);
  const r = damp1(cf.fov, cf.fvel, want.fov ?? 38, omega, dt); cf.fov = r[0]; cf.fvel = r[1];
}
function followSet(c) { cf.pos.copy(c.pos); cf.look.copy(c.look); cf.fov = c.fov ?? 38; cf.vel.set(0, 0, 0); cf.lvel.set(0, 0, 0); cf.fvel = 0; }

function syncSize() { const cv = st.stage.renderer.domElement; if (cv.clientWidth && cv.clientHeight) st.stage.setSize(cv.clientWidth, cv.clientHeight); }
function aspectNow() { const c = st.stage && st.stage.renderer.domElement; return c && c.clientWidth && c.clientHeight ? c.clientWidth / c.clientHeight : 1.7; }

function resetStage() {
  const S = st.stage;
  st.scene = null;
  sceneCamFn = null;
  if (st.reel) { S.reelLayer.remove(st.reel.group); st.reel.dispose(); st.reel = null; }
  S.setBlockHere(false);
  S.clearTemp();
  S.clearFragments();
  S.crack.visible = false;
  S.fx.clear();
  st.fx.length = 0;
  restoreVoxels();
  rebuildIfDirty();
  S.setNight(0);
  S.sunDrop(0);
  S.torchFx = null;
  const sr = S.steve.root;
  sr.visible = true; sr.scale.set(1, 1, 1);
  if (S.steve.parts && S.steve.parts.head) S.steve.parts.head.visible = true;
  S.steve.mat.emissive.setRGB(0.3, 0.3, 0.3);
  if (brain) brain.freeze();
  clearOverlays();
  st.lastTick = -1;
  S.enableDof(false);
}

let breakToken = 0;
// Screen dip to black while the world is swapped under it.
function dip(fn) {
  const d = $('#dip');
  if (!d || REDUCED) { fn(); return; }
  d.style.transition = 'opacity .3s ease';
  d.style.opacity = '1';
  setTimeout(() => { fn(); requestAnimationFrame(() => { d.style.transition = 'opacity .6s ease'; d.style.opacity = '0'; }); }, 320);
}
function pickIndex(forceIndex) {
  let idx = forceIndex;
  if (idx == null) idx = st.forced != null ? st.forced : rollIndex(st.luck);
  if (idx == null || !st.drops[idx]) idx = rollIndex(st.luck);
  return idx;
}
// Break a block: from idle, or "Break another" from the result sheet.
function breakWith(forceIndex) {
  if (!st.stage || !structsReady) return;
  $('#titleBox').classList.add('away');
  st.hold = false;
  if (st.phase !== 'idle' && st.phase !== 'result') return;
  $('#sheet').hidden = true;
  const idx = pickIndex(forceIndex);
  const go = () => { resetStage(); followSet(idleCam(st.clock || 0, aspectNow())); beginSequence(idx); if (REDUCED) seekTo(1e6, true); };
  updateBreakLabels(true);
  const wasResult = st.phase === 'result';
  if (wasResult) { const last = sceneCamFn ? sceneCamFn(st.sceneDur) : idleCam(0, 1); followSet({ pos: last.pos, look: last.look, fov: last.fov }); }
  st.phase = 'starting';
  if (wasResult) dip(go); else go();
}
function beginSequence(idx) {
  const S = st.stage;
  st.winnerIndex = idx;
  st.winner = st.drops[idx];
  st.started = true;
  st.pre = 0; st.T = 0; st.sceneT = 0;
  st.phase = 'drop';
  st.breakToken = ++breakToken;
  st.slammed = st.shatterDone = st.reelBuilt = st.sceneBuilt = st.revealed = false;
  st.lastCrack = -1; st.hits = 0; st.arrive = -1; st.kick = 0;
  st.palette = st.palette || [0xffffff];
  S.setBlockHere(true);
  S.lb.visible = true; S.lb.scale.set(1, 1, 1); S.lb.rotation.set(0, 0.4, 0);
  S.lb.position.set(0.5, 18, 0.5);
  S.halo.position.copy(S.lb.position);
  brain.call();
  play('qf.whoosh', { volume: 0.95 });
  audio.music('music.lucky', { fade: 4, volume: 0.5 });
  updateBreakLabels(true);
}
function updateBreakLabels(busy) {
  const b = st.breakBtn;
  b.disabled = busy;
  b.textContent = busy ? 'Breaking' : 'Break it';
}
function closeResult() {
  if (st.phase !== 'result') { $('#sheet').hidden = true; return; }
  $('#sheet').hidden = true;
  st.phase = 'closing';
  play('qf.ui.close', { volume: 0.7 });
  const last = sceneCamFn ? sceneCamFn(st.sceneDur) : idleCam(0, 1);
  followSet({ pos: last.pos, look: last.look, fov: last.fov });
  dip(returnToIdle);
}
function returnToIdle() {
  resetStage();
  st.phase = 'idle'; st.started = false; st.sceneT = 0; st.T = 0;
  brain.resume();
  updateBreakLabels(false);
}

function shoulderCam() {
  return { pos: new THREE.Vector3(3.7, 2.8, 3.7), look: new THREE.Vector3(1.0, 1.55, 0.5), fov: 38 };
}
function idleCam(t, aspect = 1.7) {
  const a = 0.55 + 0.18 * Math.sin(t * 0.13);
  const narrow = Math.max(0, 1.1 - aspect);
  const R = 11.4 + narrow * 18;
  return { pos: new THREE.Vector3(2.4 + Math.sin(a) * R, 3.4 + narrow * 4.5 + Math.sin(t * 0.21) * 0.2, 0.5 + Math.cos(a) * R), look: new THREE.Vector3(1.6 + narrow * 0.6, 2.0 - narrow * 2.9, 0.5), fov: 38 + narrow * 42 };
}
// The idle shot follows Steve: close enough that what he is doing reads, from a little above the
// dais and the campfire, gliding as he walks (the follow camera smooths every change).
function idleWant(t, aspect) {
  const base = idleCam(t, aspect);
  if (!brain) return base;
  const p = brain.pos();
  const narrow = Math.max(0, 1.1 - aspect);
  const focus = new THREE.Vector3(p.x, p.y + 1.0, p.z);
  const dir = base.pos.clone().sub(base.look); dir.y = 0; dir.normalize();
  const dist = 10.2 + narrow * 10;
  const pos = focus.clone().addScaledVector(dir, dist); pos.y = p.y + 3.6 + narrow * 3;
  // keep a hint of the dais in the frame: bias the focus a little toward it
  focus.lerp(new THREE.Vector3(0.5, 1.2, 0.5), 0.22);
  return { pos, look: focus, fov: 36 + narrow * 30 };
}
function reelCam(aspect) {
  const dist = aspect < 0.9 ? 6.4 : 4.9;
  return { pos: new THREE.Vector3(POS.reel.x, POS.reel.y + 0.25, POS.reel.z + dist), look: new THREE.Vector3(POS.reel.x, POS.reel.y - 0.05, POS.reel.z), fov: 38 };
}
const ease = (x) => { x = Math.max(0, Math.min(1, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const mix = (a, b, k) => ({ pos: a.pos.clone().lerp(b.pos, k), look: a.look.clone().lerp(b.look, k), fov: (a.fov ?? 38) + ((b.fov ?? 38) - (a.fov ?? 38)) * k });

// Hermite glide from the camera as it was at the shatter (with its velocity) to the reel: no velocity jump.
const T_PAN_END = T_REEL + 1.4;
function hermite(p0, v0, p1, D, u) {
  const u2 = u * u, u3 = u2 * u;
  return p0 * (2 * u3 - 3 * u2 + 1) + v0 * D * (u3 - 2 * u2 + u) + p1 * (-2 * u3 + 3 * u2);
}
function panCam(T, aspect) {
  const rc = reelCam(aspect), s = st.camShatter;
  const D = T_PAN_END - T_SHATTER, u = Math.max(0, Math.min(1, (T - T_SHATTER) / D));
  const out = { pos: new THREE.Vector3(), look: new THREE.Vector3(), fov: 38 };
  for (const k of ['x', 'y', 'z']) {
    out.pos[k] = hermite(s.pos[k], s.vel[k] * 0.8, rc.pos[k], D, u);
    out.look[k] = hermite(s.look[k], s.lvel[k] * 0.8, rc.look[k], D, u);
  }
  out.fov = hermite(s.fov, s.fvel * 0.8, rc.fov, D, u);
  out.pos.y += 0.7 * Math.pow(Math.sin(Math.PI * u), 2);   // a gentle arc up and over, zero slope at both ends
  return out;
}
// The camera at a given point of the post-shatter timeline.
function camForTimeline(T, aspect) {
  if (T < T_PAN_END && st.camShatter) return panCam(T, aspect);
  const rc = reelCam(aspect);
  if (T < T_WIN) return rc;
  const idle0 = idleCam(0, aspect);
  if (T < T_SCENE) return mix(rc, idle0, ease((T - T_WIN) / (T_SCENE - T_WIN)));
  const ts = T - T_SCENE;
  const sc = sceneCamFn ? sceneCamFn(ts) : idle0;
  return mix(idle0, sc, ease(ts / 0.9));
}
let sceneCamFn = null;

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
  st.stage.reel = reel;
}

const particleScale = () => {
  const S = st.stage;
  return S.renderer.domElement.height / (2 * Math.tan((S.camera.fov * Math.PI / 180) / 2));
};

// What happens every step whatever the phase: Steve, particles, fragments, effects. Never skipped.
function stepWorld(dt) {
  const S = st.stage;
  st.clock = (st.clock || 0) + dt;
  brain.update(dt, S.camera.position);
  camp.update(st.clock);
  S.fx.update(dt, particleScale());
  S.stepFragments(dt);
  for (let i = st.fx.length - 1; i >= 0; i--) { if (st.fx[i].update && st.fx[i].update(dt)) st.fx.splice(i, 1); }
  st.kick = Math.max(0, (st.kick || 0) - dt * 4);
  // idle ambience: the odd bird, far off
  st.ambT = (st.ambT ?? 12) - dt;
  if (st.ambT <= 0) { st.ambT = 14 + Math.random() * 16; if (audio.has('orespawn:birds')) play('orespawn:birds', { pos: { x: -9, y: 6, z: -7 }, volume: 0.22, ref: 8 }); }
  // the follow camera (idle, the fall, the run, the mining)
  const ph = st.phase;
  if (ph === 'idle' || ph === 'closing' || ph === 'starting' || ph === 'drop' || ph === 'run' || ph === 'mine') {
    const aspect = aspectNow();
    const idle = idleCam(st.clock, aspect);
    let want = ph === 'idle' || ph === 'closing' || ph === 'starting' ? idleWant(st.clock, aspect) : idle, om = ph === 'idle' ? 2.6 : 3.4;
    if (ph === 'mine') { want = shoulderCam(); om = 3.4; }
    else if (ph === 'drop' || ph === 'run') {
      const sp = brain.pos();
      want = { pos: idle.pos, look: idle.look.clone().lerp(new THREE.Vector3(sp.x, sp.y + 1, sp.z), 0.28), fov: idle.fov - 1.5 };
    }
    followStep(want, om, dt);
  }
}

function slam() {
  const S = st.stage;
  st.slammed = true;
  S.lb.position.set(0.5, 1.5, 0.5);
  S.halo.position.copy(S.lb.position);
  play('qf.case_slam', { volume: 1 });
  S.fx.ring({ x: 0.5, y: 1, z: 0.5 }, 44, { speed: 4.6 });
  S.fx.dust({ x: 0.5, y: 1.05, z: 0.5 }, 14);
  S.fx.sparks({ x: 0.5, y: 1.2, z: 0.5 }, 0xd8b8ff, 14, { speed: 2.2 });
  st.shake = Math.max(st.shake, 0.4);
  st.kick = 1;
  S.flashTorches(0xffb060, { amp: 1.1, dur: 0.9, freq: 0, tint: 0.4, now: st.clock });
  // a shock ring over the dais top
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.1, 40), new THREE.MeshBasicMaterial({ color: 0xffe2c0, transparent: true, opacity: 0.4, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  ring.rotation.x = -Math.PI / 2; ring.position.set(0.5, 1.04, 0.5);
  S.temp.add(ring);
  let t = 0;
  st.fx.push({ update(dt) { t += dt; const k = t / 0.55; ring.scale.setScalar(1 + k * 3.4); ring.material.opacity = 0.4 * (1 - k); if (k >= 1) { S.temp.remove(ring); ring.geometry.dispose(); ring.material.dispose(); return true; } return false; } });
}

function shatterNow() {
  const S = st.stage;
  st.shatterDone = true;
  S.crack.visible = false;
  S.shatter(56, 1);
  S.setBlockHere(false);
  S.lb.visible = false;
  play('random.break', { volume: 0.9, pitch: 0.9 });
  play('dig.glass', { volume: 0.7, pitch: 0.85 });
  play('random.pop', { volume: 0.7, pitch: 0.7 });
  flashScreen('#ffe2b8', 0.55, 0.45);
  st.shake = Math.max(st.shake, 0.26);
  S.fx.chips({ x: 0.5, y: 1.5, z: 0.5 }, st.palette, 36, { speed: 2.6, up: 1.6, size: 0.1, life: 1.2 });
  S.fx.sparks({ x: 0.5, y: 1.5, z: 0.5 }, 0xffe0a0, 22, { speed: 2.4 });
  burst(makeCtx(st.winner), POS.dais.clone().setY(1.4), { n: 40, colors: st.palette, size: 0.18, speed: 3.2, up: 2.8, life: 0.9, gravity: 9 });
  st.camShatter = { pos: cf.pos.clone(), vel: cf.vel.clone(), look: cf.look.clone(), lvel: cf.lvel.clone(), fov: cf.fov, fvel: cf.fvel };
  st.phase = 'reel';
  st.T = T_SHATTER;
  brain.afterBreak();
}

function stepTimeline(dt) {
  const S = st.stage;
  stepWorld(dt);
  const ph = st.phase;
  if (ph === 'idle' || ph === 'closing' || ph === 'starting') { rebuildIfDirty(); return; }
  // ---- before the shatter: the fall, the run, the mining
  if (ph === 'drop' || ph === 'run' || ph === 'mine') {
    st.pre += dt;
    const P = st.pre;
    if (!st.slammed) {
      const k = Math.min(1, P / T_SLAM);
      S.lb.position.y = 1.5 + 16.5 * (1 - k * k);
      S.lb.rotation.y = 0.4 + (1 - k) * 2.2;
      S.halo.position.copy(S.lb.position);
      S.fx.sparks({ x: 0.5, y: S.lb.position.y + 0.3, z: 0.5 }, 0xc8a8ff, 1, { speed: 0.3 });
      if (k >= 1) { slam(); }
    } else {
      // squash and spring back after the slam
      const a = P - T_SLAM;
      if (a < 0.3) { const sq = 1 - 0.2 * Math.sin(Math.min(1, a / 0.3) * Math.PI) * Math.exp(-a * 3); S.lb.scale.set(1 + (1 - sq) * 0.6, sq, 1 + (1 - sq) * 0.6); } else S.lb.scale.set(1, 1, 1);
    }
    const bs = brain.state();
    if (ph === 'drop' && bs === 'run') st.phase = 'run';
    if (bs === 'mine' && st.phase !== 'mine') { st.phase = 'mine'; st.arrive = P; }
    if (st.phase === 'mine' && st.slammed) {
      const mc = Math.max(0, brain.mineClock());
      while (st.hits < HIT_AT.length && mc >= HIT_AT[st.hits]) {
        const i = st.hits++;
        if (i < HIT_AT.length - 1) {
          S.crack.visible = true;
          S.crackMat.map = tex('blocks/destroy_stage_' + CRACK_AT[i] + '.png');
          S.crackMat.needsUpdate = true;
          play('dig.stone', { pos: { x: 0.5, y: 1.5, z: 0.5 }, ref: 7, volume: 0.85, pitch: 0.8 + i * 0.07 });
          chips(10);
          st.shake = Math.max(st.shake, 0.06);
          S.lb.scale.set(1.04, 0.97, 1.04);
        } else {
          shatterNow();
          break;
        }
      }
    }
    if (st.phase === 'mine' && st.hits < HIT_AT.length) S.lb.scale.lerp(new THREE.Vector3(1, 1, 1), Math.min(1, dt * 12));
    if (st.phase !== 'reel') { rebuildIfDirty(); return; }
    return;
  }
  // ---- after the shatter: the timeline the reel and the scenes were written against
  st.T += dt;
  const T = st.T;
  if (T >= T_REEL && !st.reelBuilt && !st.sceneBuilt) buildReelNow();
  if (st.reel && T >= T_REEL && T < T_WIN) {
    const u = clamp01((T - T_SPIN) / SPIN_DUR);
    const p = u <= 0 ? 0 : reelCurve(u, st.reel.win, 0.34);
    const speed = (st.reel.lastP !== undefined ? (p - st.reel.lastP) / Math.max(dt, 1e-3) : 0);
    st.reel.set(p, speed);
    st.reel.lastP = p;
    st.reel.spinAll(st.clock);
    // a tick as each plaque passes the marker; the pitch climbs a little as the reel slows
    const cell = Math.floor(p + 0.5);
    if (cell !== st.lastTick) { if (st.lastTick >= 0 && T >= T_SPIN) tick(Math.abs(speed)); st.lastTick = cell; }
  }
  if (st.reel && T >= T_WIN) {
    if (!st.revealed) {
      st.revealed = true;
      const mood = st.winner.mood || 'neutral';
      const col = MOOD_COLOR[mood] || 0xf2c14e;
      S.flashTorches(col, { amp: mood === 'jackpot' ? 1.5 : mood === 'deadly' ? 1.3 : 1.0, dur: 3.2, freq: mood === 'jackpot' ? 4 : 2.5, now: st.clock });
      play('qf.reel_land', { volume: 0.8 });
      play('qf.reveal.' + mood, { volume: 1 });
      audio.duck('sfx', 0.35, 3.2);
    }
    // the marker line would cut through the landed item: fade it out
    const mk = clamp01(1 - (T - T_WIN) / 0.3);
    for (const c of st.reel.group.children) if (!st.reel.tiles.includes(c)) { c.scale.x = Math.max(0.001, mk); c.visible = mk > 0; }
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
      S.fx.sparks({ x: 0.5, y: 1.4, z: 0.5 }, MOOD_COLOR[st.winner.mood] || 0xf2c14e, 24, { speed: 2.8 });
      flashScreen('#ffffff', 0.5, 0.4);
      st.shake = Math.max(st.shake, 0.18);
    }
    if (T >= T_SCENE) { S.reelLayer.remove(st.reel.group); st.reel.dispose(); st.reel = null; }
  }
  if (T >= T_SCENE) {
    if (!st.sceneBuilt) {
      st.sceneBuilt = true;
      st.phase = 'scene';
      if (st.reel) { S.reelLayer.remove(st.reel.group); st.reel.dispose(); st.reel = null; }
      brain.freeze();
      const ctx = makeCtx(st.winner);
      const sc = buildScene(st.winner.scene, ctx);
      st.scene = sc;
      sceneCamFn = sc.cam;
      st.sceneDur = sc.dur;
      st.fx.length = 0;
      S.steve.mat.emissive.setRGB(0.3, 0.3, 0.3);
      S.setBlockHere(false);
      rebuildIfDirty();
      st.sceneCtx = ctx;
    }
    st.sceneT = T - T_SCENE;
    if (st.scene) {
      try { st.scene.update(st.sceneT, dt); } catch (e) { if (!st.sceneErr) { st.sceneErr = true; console.error('scene.update', e); } }
      if (st.phase === 'scene' && st.sceneT >= st.sceneDur) { st.phase = 'result'; showResult(); }
    }
  }
  rebuildIfDirty();
}
function clamp01(x) { return Math.max(0, Math.min(1, x)); }
function chips(n) {
  const c = POS.dais.clone();
  st.stage.fx.chips({ x: 0.5, y: 1.5, z: 0.5 }, st.palette, n, { speed: 1.8, up: 1.2, size: 0.08 });
  void c;
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

// The reel tick: from the bank if it has one, otherwise a short synthesized click on the UI bus.
function tick(speed = 0) {
  const norm = Math.min(1, speed / 14);
  const pitch = 0.92 + 0.3 * (1 - norm);
  if (SFXLOG) SFXNAMES.push('qf.reel_tick');
  if (audio.has('qf.reel_tick')) { audio.play('qf.reel_tick', { pitch, volume: 0.6 + 0.3 * norm }); return; }
  const ctx = audio.context(), bus = audio.busNode('ui');
  if (!ctx || !bus) return;
  const o = ctx.createOscillator(), g = ctx.createGain(), t0 = ctx.currentTime;
  o.type = 'square'; o.frequency.value = 1500 * pitch;
  g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(0.12, t0 + 0.002); g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.045);
  o.connect(g); g.connect(bus); o.start(t0); o.stop(t0 + 0.05);
}

function showResult() {
  clearOverlays();
  $('#titleBox').classList.remove('away');
  const K = st.luck;
  const p = probOf(st.winnerIndex, K);
  renderSheet(st.winner, p);
  updateBreakLabels(false);
}

// Steve's behaviour fast-forwarded with no one watching (?idle=ms, optionally ?act=<activity> first).
function prepIdle(ms) {
  brain.reset();
  if (params.get('act')) brain.start(params.get('act'));
  brain.fastForward(ms, st.stage.camera.position);
  st.clock = ms / 1000;
}

// Seek the whole sequence (the dump hook): o.pre = seconds into the fall/run, o.mine = seconds of mining,
// otherwise T is the post-shatter timeline (the reel at 3.7 s, the scene at 9.6 s) as before.
function seekTo(T, hold, o = {}) {
  syncSize();
  resetStage();
  st.started = true;
  st.clock = 0;
  if (st.idleMs) { prepIdle(st.idleMs); }
  followSet(idleWant(st.clock, aspectNow()));
  brain.resume();
  beginSequence(st.winnerIndex);
  const step = 1 / 60;
  let guard = 0;
  const limit = 120000;
  if (o.pre != null) { while (st.pre < o.pre && ['drop', 'run', 'mine'].includes(st.phase) && guard++ < limit) stepTimeline(step); }
  else if (o.mine != null) { while (guard++ < limit && ['drop', 'run', 'mine'].includes(st.phase) && !(st.phase === 'mine' && brain.mineClock() >= o.mine)) stepTimeline(step); }
  else { while (guard++ < limit && st.phase !== 'result' && !(st.phase !== 'drop' && st.phase !== 'run' && st.phase !== 'mine' && st.T >= T)) stepTimeline(step); }
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
  stepTimeline(dt);
  renderFrame(dt);
}
function currentCam(aspect) {
  const ph = st.phase;
  if (ph === 'reel' || ph === 'scene') return camForTimeline(st.T, aspect);
  if (ph === 'result') return sceneCamFn ? sceneCamFn(st.sceneDur) : idleCam(st.clock || 0, aspect);
  return { pos: cf.pos.clone(), look: cf.look.clone(), fov: cf.fov };
}
function renderFrame(dt, still) {
  const S = st.stage;
  const aspect = S.camera.aspect || 1;
  let cam = currentCam(aspect);
  const sh = st.shake;
  if (sh > 0) {
    cam = { pos: cam.pos.clone().add(new THREE.Vector3((Math.random() - 0.5) * sh, (Math.random() - 0.5) * sh, (Math.random() - 0.5) * sh)), look: cam.look.clone(), fov: cam.fov };
    st.shake = Math.max(0, sh - dt * 2.6);
  }
  if (st.kick > 0) cam = { pos: cam.pos, look: cam.look, fov: (cam.fov ?? 38) - 4 * st.kick * st.kick };
  S.lbMat.emissiveIntensity = 0.5 + 0.12 * Math.sin((st.clock || 0) * 1.7);
  S.enableDof(st.phase === 'scene' && st.sceneT < 1.6 && S.quality === 'high');
  const clk = st.clock || 0;
  S.frame(clk, still ? 0 : dt, { cam });
  audio.updateListener(S.camera);
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
  const mobsReady = (MOBS.whenMobTexturesLoaded ? MOBS.whenMobTexturesLoaded() : Promise.resolve());
  // textures arrive asynchronously; a frame rendered before they land is black silhouettes
  Promise.all([whenTexturesLoaded(), mobsReady]).then(() => new Promise((r) => setTimeout(r, 60)))
    .then(() => Promise.all([whenTexturesLoaded(), mobsReady])).then(() => dumpNow());
}
function dumpNow() {
  try {
    syncSize();
    if (st.phase === 'idle') followSet(idleWant(st.clock, aspectNow()));
    renderFrame(0, true);
    let report = null;
    try { report = st.scene && st.scene.report ? st.scene.report() : null; } catch (e) { report = { error: String(e) }; }
    const el = document.createElement('script');
    el.type = 'application/json';
    el.id = 'dumpshot';
    el.textContent = JSON.stringify({
      phase: st.phase, T: st.T, pre: st.pre, scene: st.winner && st.winner.scene, index: st.winnerIndex, built: !!st.sceneBuilt,
      steve: brain ? { state: brain.state(), activity: brain.activity(), x: +brain.x().toFixed(2), z: +brain.z().toFixed(2) } : null,
      caption: ($('#caption') || {}).textContent || '', chat: ($('#chat') || {}).textContent || '',
      errors: ERRORS, sfx: SFXNAMES, sceneReport: report,
      png: st.stage.renderer.domElement.toDataURL('image/png'),
    });
    document.body.appendChild(el);
  } catch (e) { console.error('dumpShot', e); ERRORS.push('dumpShot: ' + e); }
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
  setupMute();
  if (!webgl) {
    $('#poster').hidden = false;
    $('#stageBar').hidden = true;
    $('#noGL').hidden = false;
    renderOdds();
    return;
  }
  st.breakBtn = $('#breakBtn');
  st.breakBtn.addEventListener('click', () => breakWith(null));
  addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !e.target.closest('input,button,select,textarea,summary,a,details,[tabindex="0"]')) { e.preventDefault(); if (!st.breakBtn.disabled) breakWith(null); }
    if (e.key === 'Escape' && st.phase === 'result') closeResult();
  });
  const quality = (matchMedia('(max-width: 720px)').matches || matchMedia('(pointer: coarse)').matches) ? 'low' : 'high';
  st.quality = quality;
  const reserve = [...L.obstacles];
  for (const k of ['tableStand', 'furnaceStand', 'chestStand', 'seatApproach']) reserve.push([L[k].x - 0.9, L[k].z - 0.9, L[k].x + 0.9, L[k].z + 0.9]);
  for (const k of ['build', 'dance', 'pillar', 'sneak', 'sunset']) reserve.push([L[k].x - 1, L[k].z - 1, L[k].x + 1, L[k].z + 1]);
  reserve.push([L.pond.stand.x - 0.8, L.pond.stand.z - 0.8, L.pond.stand.x + 0.8, L.pond.stand.z + 0.8], [L.tree.stand.x - 0.8, L.tree.stand.z - 0.8, L.tree.stand.x + 0.8, L.tree.stand.z + 0.8]);
  try {
    st.stage = await createStage(cvs, { quality, reserve });
  } catch (e) {
    console.error(e);
    ERRORS.push('createStage: ' + e);
    $('#poster').hidden = false; $('#stageBar').hidden = true; $('#noGL').hidden = false;
    renderOdds();
    return;
  }
  const S = st.stage;
  S.steve.root.position.copy(POS.player);
  camp = buildCamp(S);
  brain = createBrain({ S, camp, fx: S.fx, play, seed: params.has('seed') ? Number(params.get('seed')) : (params.has('dump') ? 11 : Math.floor(Math.random() * 1e6)) });
  if (params.has('noshadow')) S.renderer.shadowMap.enabled = false;
  const resize = () => {
    const w = cvs.clientWidth, h = cvs.clientHeight;
    if (w && h) S.setSize(w, h);
  };
  addEventListener('resize', resize);
  resize();
  S.enableDof(false);
  samplePalette();
  followSet(idleCam(0, aspectNow()));
  const io = new IntersectionObserver((es) => { st.onscreen = es[0].isIntersecting; }, { threshold: 0 });
  io.observe(cvs);
  document.addEventListener('visibilitychange', () => { last = performance.now(); });
  renderOdds();
  $('#stageBar').hidden = false;
  $('#breakBtn').disabled = !structsReady;
  $('#skinForm').addEventListener('submit', (e) => { e.preventDefault(); loadSkin($('#skinName').value.trim()); });
  // the URL hooks: ?scene=, ?at=, ?atm=, ?pre=, ?reel=, ?idle=, #demo=
  st.idleMs = params.has('idle') ? Math.max(0, Number(params.get('idle')) || 0) : 0;
  const want = hashDemo() || (params.has('scene') ? params.get('scene') : null);
  const seqHook = params.has('reel') || params.has('at') || params.has('atm') || params.has('pre') || want;
  if (!seqHook) {
    if (st.idleMs) {
      prepIdle(st.idleMs);
      followSet(idleWant(st.clock, aspectNow()));
      st.hold = params.has('dump');
      renderFrame(0, true);
      dumpShot();
    }
    startLoop();
    return;
  }
  if (params.has('reel')) {
    const frac = Math.max(0, Math.min(1, Number(params.get('reel'))));
    st.winnerIndex = pickIndex(params.has('force') ? Number(params.get('force')) : null);
    seekTo(T_SPIN + frac * SPIN_DUR + 0.0001, true);
    dumpShot();
    startLoop();
    return;
  }
  await structsGate;
  const idx = params.has('force') ? Number(params.get('force')) : (want ? findScene(want) : null);
  if (idx != null) st.forced = idx;
  st.winnerIndex = pickIndex(idx);
  st.started = true;
  $('#titleBox').classList.add('away');
  if (params.has('pre')) seekTo(0, true, { pre: Number(params.get('pre')) / 1000 });
  else if (params.has('atm')) seekTo(0, true, { mine: Number(params.get('atm')) / 1000 });
  else if (params.has('at')) {
    const ms = Number(params.get('at'));
    if (ms < T_SHATTER * 1000) seekTo(0, true, { pre: ms / 1000 }); else seekTo(ms / 1000, true);
  } else seekTo(T_SCENE + 0.95, true);
  if (params.has('closetest')) {
    // test hook: close the result as the Close button does (no dip), run a second, then dump
    st.phase = 'closing'; returnToIdle(); st.hold = true;
    for (let i = 0; i < Number(params.get('closetest')) * 60; i++) stepTimeline(1 / 60);
    renderFrame(0, true);
  }
  dumpShot();
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

// The speaker toggle in the stage bar.
function setupMute() {
  const b = $('#mute');
  if (!b) return;
  const show = () => {
    const m = audio.isMuted();
    b.dataset.muted = m ? '1' : '0';
    b.setAttribute('aria-pressed', m ? 'true' : 'false');
    b.setAttribute('aria-label', m ? 'Sound is off. Turn it on' : 'Sound is on. Turn it off');
    b.title = m ? 'Sound off' : 'Sound on';
  };
  b.addEventListener('click', () => { audio.setMuted(!audio.isMuted()); });
  audio.onMute(show);
  show();
}

// A skin from the visitor's name: 64x64 skins are cropped to the old 64x32 layout the rig uses.
async function loadSkin(name) {
  if (!name) return;
  const url = 'https://api.mineatar.io/skin/' + encodeURIComponent(name);
  try {
    const img = await imageLoad(url);
    if (!img) throw new Error('no skin');
    let src = img;
    if (img.height >= 64) {
      const c = document.createElement('canvas'); c.width = 64; c.height = 32;
      c.getContext('2d').drawImage(img, 0, 0, 64, 32, 0, 0, 64, 32);
      src = c;
    }
    const t = new THREE.Texture(src);
    t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.needsUpdate = true;
    st.stage.steve.mat.map = t; st.stage.steve.mat.emissiveMap = t; st.stage.steve.mat.needsUpdate = true;
    $('#skinNote').textContent = 'Showing the skin of ' + name + '.';
  } catch (e) {
    $('#skinNote').textContent = 'No skin for that name. Showing Steve.';
  }
}

boot();
