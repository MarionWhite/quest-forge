// The scare overlay: everything drawn flat on a 270-line canvas that the browser scales up unsmoothed, so
// the hurt flash, cracks, splats, hearts, hotbar and the death screen all share the game's pixel grid.
import { clamp, easeOut, rngOf } from "./stage.js";

export const LH = 270;
const FONT = '"Courier New", Courier, Menlo, monospace';
const sprites = new Map();
function sprite(str, size, color) {
  const key = str + "|" + size + "|" + color;
  let s = sprites.get(key);
  if (s) return s;
  const c = document.createElement("canvas"), x = c.getContext("2d", { willReadFrequently: true });
  const font = `bold ${size}px ${FONT}`;
  x.font = font;
  const w = Math.ceil(x.measureText(str).width) + 2, h = Math.ceil(size * 1.35);
  c.width = w; c.height = h;
  x.font = font; x.textBaseline = "top"; x.fillStyle = "#fff"; x.fillText(str, 1, 1);
  const id = x.getImageData(0, 0, w, h), d = id.data;
  const col = parseInt(color.slice(1), 16), r = col >> 16, g = (col >> 8) & 255, b = col & 255;
  for (let i = 0; i < d.length; i += 4) { const on = d[i + 3] > 110; d[i] = r; d[i + 1] = g; d[i + 2] = b; d[i + 3] = on ? 255 : 0; }
  x.putImageData(id, 0, 0);
  s = { c, w, h }; sprites.set(key, s); return s;
}
export function pixText(ctx, str, cx, y, size, color, align = "center") {
  const s = sprite(str, size, color), sh = sprite(str, size, "#3a3a3a");
  const x0 = align === "center" ? Math.round(cx - s.w / 2) : Math.round(cx), o = size >= 14 ? 2 : 1;
  ctx.drawImage(sh.c, x0 + o, Math.round(y) + o); ctx.drawImage(s.c, x0, Math.round(y));
}

const HEART = ["011000110", "122212221", "132222221", "122222221", "012222210", "001222100", "000121000", "000010000"];
function heart(ctx, x, y, kind, half) {
  // kind: normal | poison | wither
  const fill = { normal: ["#ff1313", "#ff8a8a"], poison: ["#6f7b1f", "#a8b84a"], wither: ["#2b2b2b", "#555555"] }[kind];
  for (let j = 0; j < 8; j++) for (let i = 0; i < 9; i++) {
    const v = HEART[j][i];
    if (v === "0") continue;
    let col = v === "1" ? "#2a0000" : v === "3" ? fill[1] : fill[0];
    if (half && i >= 5 && v !== "1") col = "#3a1010";
    ctx.fillStyle = col; ctx.fillRect(x + i, y + j, 1, 1);
  }
}
function hotbar(ctx, LW, selected) {
  const x0 = Math.round((LW - 182) / 2), y0 = LH - 22;
  ctx.fillStyle = "#8b8b8b"; ctx.fillRect(x0, y0, 182, 22);
  ctx.fillStyle = "#373737"; ctx.fillRect(x0 + 1, y0 + 1, 180, 20);
  for (let i = 0; i < 9; i++) {
    const sx = x0 + 3 + i * 20;
    ctx.fillStyle = "#8b8b8b"; ctx.fillRect(sx, y0 + 3, 16, 16);
    ctx.fillStyle = "#555"; ctx.fillRect(sx + 1, y0 + 4, 15, 15);
  }
  ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.strokeRect(x0 + 2 + selected * 20 + 0.5, y0 + 2.5, 17, 17);
  // sword, pickaxe, torches
  const ic = (i, fn) => fn(x0 + 3 + i * 20, y0 + 3);
  ic(0, (x, y) => { ctx.fillStyle = "#cfd6dc"; for (let k = 0; k < 10; k++) ctx.fillRect(x + 13 - k, y + 2 + k, 2, 2); ctx.fillStyle = "#6a4a28"; ctx.fillRect(x + 2, y + 11, 3, 3); });
  ic(1, (x, y) => { ctx.fillStyle = "#6a4a28"; for (let k = 0; k < 9; k++) ctx.fillRect(x + 3 + k, y + 12 - k, 2, 2); ctx.fillStyle = "#9aa4aa"; ctx.fillRect(x + 3, y + 1, 10, 3); ctx.fillRect(x + 11, y + 1, 3, 6); });
  ic(2, (x, y) => { ctx.fillStyle = "#ffd040"; ctx.fillRect(x + 6, y + 2, 4, 3); ctx.fillStyle = "#6a4a28"; ctx.fillRect(x + 6, y + 5, 4, 9); });
}

export function createOverlay(host) {
  const canvas = document.createElement("canvas");
  canvas.className = "qfs-fx";
  host.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  const o = { canvas, ctx, LW: 480, btn: { x: 0, y: 0, w: 0, h: 0 } };
  o.size = (w, h) => { o.LW = Math.max(200, Math.round(LH * w / h)); canvas.width = o.LW; canvas.height = LH; };
  o.draw = (f, t) => draw(o, f, t);
  return o;
}

function draw(o, f, t) {
  const { ctx, LW } = o;
  ctx.clearRect(0, 0, LW, LH);
  ctx.imageSmoothingEnabled = false;
  for (const tn of f.tints || []) { if (tn[3] > 0.003) { ctx.fillStyle = `rgba(${tn[0]},${tn[1]},${tn[2]},${tn[3].toFixed(3)})`; ctx.fillRect(0, 0, LW, LH); } }
  if (f.vig && f.vig[3] > 0.003) {
    const g = ctx.createRadialGradient(LW / 2, LH / 2, LH * 0.25, LW / 2, LH / 2, LH * (f.vigR || 0.95));
    g.addColorStop(0, `rgba(${f.vig[0]},${f.vig[1]},${f.vig[2]},0)`);
    g.addColorStop(1, `rgba(${f.vig[0]},${f.vig[1]},${f.vig[2]},${f.vig[3].toFixed(3)})`);
    ctx.fillStyle = g; ctx.fillRect(0, 0, LW, LH);
  }
  if (f.fire > 0.01) fire(ctx, LW, f.fire, t);
  if (f.bubbles > 0.01) bubbles(ctx, LW, f.bubbles, t, f.bubbleCol || "#9be86a");
  for (const s of f.splats || []) splat(ctx, LW, s, t);
  for (const c of f.cracks || []) crack(ctx, LW, c, t);
  for (const s of f.slashes || []) slash(ctx, LW, s, t);
  if (f.glitch > 0.01) glitch(ctx, LW, f.glitch, t);
  if (f.hurt > 0.003) {
    ctx.fillStyle = `rgba(210,0,0,${(f.hurt * 0.5).toFixed(3)})`; ctx.fillRect(0, 0, LW, LH);
    const g = ctx.createRadialGradient(LW / 2, LH / 2, LH * 0.2, LW / 2, LH / 2, LH * 0.9);
    g.addColorStop(0, "rgba(120,0,0,0)"); g.addColorStop(1, `rgba(120,0,0,${(f.hurt * 0.8).toFixed(3)})`);
    ctx.fillStyle = g; ctx.fillRect(0, 0, LW, LH);
  }
  if (f.white > 0.003) { ctx.fillStyle = `rgba(255,255,255,${clamp(f.white).toFixed(3)})`; ctx.fillRect(0, 0, LW, LH); }
  if (f.black > 0.003) { ctx.fillStyle = `rgba(0,0,0,${clamp(f.black).toFixed(3)})`; ctx.fillRect(0, 0, LW, LH); }
  if (f.hud && !(f.death > 0.5)) hud(ctx, LW, f, t);
  if (f.death > 0.003) death(o, f, t);
}

function hud(ctx, LW, f, t) {
  hotbar(ctx, LW, 0);
  const x0 = Math.round((LW - 182) / 2), y = LH - 22 - 11;
  const hp = clamp(f.hpShown ?? f.hp, 0, 20), rng = rngOf(Math.floor(t * 8));
  for (let i = 0; i < 10; i++) {
    const full = hp >= (i + 1) * 2, half = !full && hp >= i * 2 + 1;
    const shake = hp <= 6 && hp > 0 ? Math.floor(rng() * 3) - 1 : 0;
    // empty container
    heart(ctx, x0 + i * 8, y + shake, "normal", false);
    if (!full && !half) { ctx.fillStyle = "#1a0505"; ctx.fillRect(x0 + i * 8 + 1, y + shake + 1, 7, 5); }
    else if (half) { ctx.fillStyle = "#1a0505"; ctx.fillRect(x0 + i * 8 + 5, y + shake + 1, 4, 5); }
    if (f.hpMode && f.hpMode !== "normal" && (full || half)) heart(ctx, x0 + i * 8, y + shake, f.hpMode, half);
  }
}

function splat(ctx, LW, s, t) {
  const age = t - s.t0;
  if (age < 0) return;
  const k = easeOut(age / 0.14), R = s.r * k, rng = rngOf(s.seed || 1);
  const cx = s.x * LW, cy = s.y * LH, col = s.col || "#8a0303", dk = s.dk || "#4a0000", hl = s.hl || "#c81414";
  for (let i = 0; i < 26; i++) {
    const a = rng() * 6.283, d = Math.sqrt(rng()) * R, sz = 2 + Math.floor(rng() * (R / 5 + 2));
    const x = Math.round(cx + Math.cos(a) * d), y = Math.round(cy + Math.sin(a) * d * 0.9);
    ctx.fillStyle = i % 5 === 0 ? dk : i % 7 === 0 ? hl : col; ctx.fillRect(x, y, sz, sz);
  }
  ctx.fillStyle = col; ctx.fillRect(Math.round(cx - R * 0.35), Math.round(cy - R * 0.3), Math.round(R * 0.7), Math.round(R * 0.6));
  const nd = 3 + Math.floor(rng() * 3);
  for (let i = 0; i < nd; i++) {
    const dx = Math.round(cx + (rng() - 0.5) * R * 1.3), w = 2 + Math.floor(rng() * 2);
    const maxLen = 12 + rng() * 55, len = Math.min(maxLen, Math.max(0, age - 0.12) * (22 + rng() * 40));
    ctx.fillStyle = col; ctx.fillRect(dx, Math.round(cy), w, Math.round(len));
    ctx.fillStyle = hl; ctx.fillRect(dx, Math.round(cy + len), w, 2);
  }
}

function crack(ctx, LW, c, t) {
  const age = t - c.t0;
  if (age < 0) return;
  const k = clamp(age / 0.12), n = c.arms || 9, rng = rngOf(c.seed || 3);
  const cx = c.x * LW, cy = c.y * LH, len = (c.len || 90) * k;
  for (let pass = 0; pass < 2; pass++) {
    ctx.strokeStyle = pass ? "rgba(235,235,235,0.85)" : "rgba(0,0,0,0.55)";
    ctx.lineWidth = 1; ctx.beginPath();
    const off = pass ? 0 : 1;
    for (let i = 0; i < n; i++) {
      let a = (i / n) * 6.283 + (rng() - 0.5) * 0.5, x = cx + off, y = cy + off;
      ctx.moveTo(Math.round(x) + 0.5, Math.round(y) + 0.5);
      const segs = 4 + Math.floor(rng() * 3);
      for (let s = 0; s < segs; s++) {
        a += (rng() - 0.5) * 0.7; const d = (len / segs) * (0.6 + rng() * 0.8);
        x += Math.cos(a) * d; y += Math.sin(a) * d;
        ctx.lineTo(Math.round(x) + 0.5, Math.round(y) + 0.5);
        if (rng() < 0.3) { ctx.moveTo(Math.round(x) + 0.5, Math.round(y) + 0.5); const b = a + (rng() - 0.5) * 2; ctx.lineTo(Math.round(x + Math.cos(b) * d * 0.7) + 0.5, Math.round(y + Math.sin(b) * d * 0.7) + 0.5); ctx.moveTo(Math.round(x) + 0.5, Math.round(y) + 0.5); }
      }
    }
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.fillRect(Math.round(cx) - 2, Math.round(cy) - 2, 4, 4);
}

function slash(ctx, LW, s, t) {
  const age = t - s.t0;
  if (age < 0 || age > 0.5) return;
  const k = clamp(age / 0.07), fade = 1 - clamp((age - 0.1) / 0.4);
  const cx = s.x * LW, cy = s.y * LH, L = (s.len || 220) * k, a = s.ang || 0.6;
  const dx = Math.cos(a), dy = Math.sin(a), nx = -dy, ny = dx;
  ctx.fillStyle = s.col || `rgba(255,255,255,${(0.9 * fade).toFixed(3)})`;
  if (!s.col) ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.moveTo(cx - dx * L / 2, cy - dy * L / 2);
  ctx.lineTo(cx + nx * 5 * fade, cy + ny * 5 * fade);
  ctx.lineTo(cx + dx * L / 2, cy + dy * L / 2);
  ctx.lineTo(cx - nx * 2, cy - ny * 2);
  ctx.closePath(); ctx.fill();
  ctx.fillStyle = `rgba(160,0,0,${(0.7 * fade).toFixed(3)})`;
  ctx.beginPath(); ctx.moveTo(cx - dx * L / 2, cy - dy * L / 2 + 3); ctx.lineTo(cx + dx * L / 2, cy + dy * L / 2 + 3); ctx.lineTo(cx + dx * L / 2, cy + dy * L / 2 + 9); ctx.closePath(); ctx.fill();
}

function fire(ctx, LW, amt, t) {
  const cols = ["#7a1000", "#c83000", "#ff6a00", "#ffb020", "#ffe070"];
  for (let x = 0; x < LW; x += 4) {
    const n = Math.sin(x * 0.37 + t * 11) * 0.5 + Math.sin(x * 0.11 - t * 7) * 0.5 + Math.sin(x * 0.9 + t * 17) * 0.25;
    const h = LH * clamp(amt * (0.55 + 0.35 * n) + (amt - 0.4) * 0.5);
    for (let l = 0; l < cols.length; l++) {
      const hh = h * (1 - l * 0.18);
      if (hh <= 0) continue;
      ctx.fillStyle = cols[l]; ctx.fillRect(x, LH - Math.round(hh / 4) * 4, 4, Math.round(hh / 4) * 4);
    }
  }
  ctx.fillStyle = `rgba(255,90,0,${(amt * 0.25).toFixed(3)})`; ctx.fillRect(0, 0, LW, LH);
}

function bubbles(ctx, LW, amt, t, col) {
  const rng = rngOf(99);
  for (let i = 0; i < 40 * amt; i++) {
    const x = rng() * LW, sp = 8 + rng() * 22, y = (LH - ((t * sp + rng() * LH) % (LH + 20))) + 10, r = 3 + Math.floor(rng() * 7);
    ctx.fillStyle = "rgba(255,255,255,0.28)"; ctx.fillRect(Math.round(x), Math.round(y), r, r);
    ctx.fillStyle = "rgba(20,70,10,0.25)"; ctx.fillRect(Math.round(x) + 1, Math.round(y) + 1, r - 2, r - 2);
  }
}

function glitch(ctx, LW, amt, t) {
  const rng = rngOf(Math.floor(t * 18) + 5), n = Math.floor(3 + amt * 14);
  for (let i = 0; i < n; i++) {
    const y = Math.floor(rng() * LH), h = 2 + Math.floor(rng() * 14), x = Math.floor(rng() * LW * 0.6), w = 40 + Math.floor(rng() * LW * 0.6);
    const c = rng(); ctx.fillStyle = c < 0.4 ? `rgba(170,40,255,${(0.35 + amt * 0.4).toFixed(2)})` : c < 0.7 ? "rgba(255,255,255,0.7)" : c < 0.85 ? "rgba(0,0,0,0.85)" : "rgba(255,0,120,0.5)";
    ctx.fillRect(x, y, w, h);
  }
  for (let i = 0; i < amt * 120; i++) { ctx.fillStyle = rng() < 0.5 ? "#fff" : "#a030ff"; ctx.fillRect(Math.floor(rng() * LW), Math.floor(rng() * LH), 2, 2); }
}

function death(o, f, t) {
  const { ctx, LW } = o, d = clamp(f.death);
  const g = ctx.createLinearGradient(0, 0, 0, LH);
  g.addColorStop(0, `rgba(80,0,0,${(0.38 * d).toFixed(3)})`); g.addColorStop(1, `rgba(128,48,48,${(0.63 * d).toFixed(3)})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, LW, LH);
  if (d < 0.6) return;
  ctx.save(); ctx.globalAlpha = clamp((d - 0.6) / 0.4);
  pixText(ctx, "You died!", LW / 2, 52, 24, "#ffffff");
  pixText(ctx, f.deathLine || "You died", LW / 2, 84, 11, "#ffffff");
  pixText(ctx, "Score: " + (f.score ?? 0), LW / 2, 102, 11, "#ffff55");
  const bw = 200, bh = 20, bx = Math.round(LW / 2 - bw / 2), by = 128;
  o.btn = { x: bx / LW, y: by / LH, w: bw / LW, h: bh / LH };
  const hov = !!f.btnHover;
  ctx.fillStyle = "#000"; ctx.fillRect(bx - 1, by - 1, bw + 2, bh + 2);
  ctx.fillStyle = hov ? "#7a7ea8" : "#6f6f6f"; ctx.fillRect(bx, by, bw, bh);
  ctx.fillStyle = hov ? "#a5a9d0" : "#a0a0a0"; ctx.fillRect(bx, by, bw - 1, 1); ctx.fillRect(bx, by, 1, bh - 1);
  ctx.fillStyle = hov ? "#41446a" : "#3a3a3a"; ctx.fillRect(bx + 1, by + bh - 2, bw - 1, 2); ctx.fillRect(bx + bw - 2, by + 1, 2, bh - 1);
  pixText(ctx, "Respawn", LW / 2, by + 4, 11, hov ? "#ffffa0" : "#ffffff");
  ctx.restore();
}
