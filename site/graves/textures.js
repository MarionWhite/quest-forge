// Canvas textures for the Wall of Graves: the mod's stone with a faint weathering layer, the chiselled name
// and year, the smooth stone treatment of the statues, and the sky and glow sprites.
import { rng } from "./data.js";

const cache = new Map();
export function loadImage(url, cors = false) {
  if (!cache.has(url)) {
    cache.set(url, new Promise((resolve, reject) => {
      const im = new Image();
      if (cors) im.crossOrigin = "anonymous";
      im.onload = () => resolve(im);
      im.onerror = () => reject(new Error("image " + url));
      im.src = url;
    }));
  }
  return cache.get(url);
}
export function canvas(w, h) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; return c;
}
export function baseCanvas(img, size) {
  const c = canvas(size, size), x = c.getContext("2d");
  x.imageSmoothingEnabled = false;
  x.drawImage(img, 0, 0, size, size);
  return c;
}

// Faint weathering, at most about a quarter opacity overall: moss low down and in the crevices, two or
// three hairline cracks, a slight darkening at the edges, and sparse lichen dots. S is the canvas size.
export function weather(ctx, S, seed) {
  const r = rng(seed), u = S / 64;
  ctx.save();
  // Edges darker, as if the arrises have weathered.
  const edge = (x0, y0, x1, y1, gx0, gy0, gx1, gy1) => {
    const g = ctx.createLinearGradient(gx0, gy0, gx1, gy1);
    g.addColorStop(0, "rgba(8,9,10,0.14)"); g.addColorStop(1, "rgba(8,9,10,0)");
    ctx.fillStyle = g; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  };
  edge(0, 0, S, 3 * u, 0, 0, 0, 3 * u); edge(0, 0, 3 * u, S, 0, 0, 3 * u, 0);
  edge(0, S - 3 * u, S, S, 0, S, 0, S - 3 * u); edge(S - 3 * u, 0, S, S, S, 0, S - 3 * u, 0);
  // Moss: low down and in the crevices only.
  for (let i = 0; i < 70; i++) {
    const x = r() * S, y = (0.66 + r() * 0.34) * S, rad = (0.5 + r() * 1.3) * u;
    ctx.globalAlpha = 0.07 + r() * 0.1;
    ctx.fillStyle = r() < 0.6 ? "#3c5a2c" : "#56763a";
    ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fill();
  }
  // Hairline cracks.
  ctx.globalAlpha = 0.3; ctx.strokeStyle = "#0d0e0f"; ctx.lineWidth = Math.max(0.6, S / 800);
  for (let i = 0; i < 2 + Math.floor(r() * 2); i++) {
    let x = r() * S, y = r() < 0.5 ? 0 : r() * S * 0.4;
    ctx.beginPath(); ctx.moveTo(x, y);
    for (let k = 0; k < 6; k++) { x += (r() - 0.5) * 5 * u; y += (r() * 2 + 0.8) * u; ctx.lineTo(x, y); }
    ctx.stroke();
  }
  // Lichen: a few pale dots.
  for (let i = 0; i < 12; i++) {
    ctx.globalAlpha = 0.18 + r() * 0.07;
    ctx.fillStyle = "#c4ca9a";
    ctx.beginPath(); ctx.arc(r() * S, r() * S, (0.35 + r() * 0.4) * u, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

// Fit a name on a line of the engraving: the largest size, condensed a little, that fits the width.
function fitTitle(ctx, text, maxW, size, maxLines) {
  for (let fs = size; fs > size * 0.4; fs *= 0.92) {
    ctx.font = `700 ${fs}px Archivo, "Helvetica Neue", Arial, sans-serif`;
    const words = text.split(/\s+/), lines = []; let cur = "";
    for (const w of words) {
      const t = cur ? cur + " " + w : w;
      if (ctx.measureText(t).width * 0.86 > maxW && cur) { lines.push(cur); cur = w; } else cur = t;
    }
    if (cur) lines.push(cur);
    if (lines.length <= maxLines) return { fs, lines };
  }
  return { fs: size * 0.4, lines: [text] };
}

// The chiselled name and year on the face: a dark inset, the letters dark with a light bevel under them.
// rect is in texture units of the mod's texture (tw x th); title and sub are strings.
export function engraveName(ctx, S, tw, th, rect, title, sub, seed = 1) {
  const [px, py, pw, ph] = rect;
  const sx = S / tw, sy = S / th;
  const x0 = px * sx, y0 = py * sy, W = pw * sx, H = ph * sy, cx = x0 + W / 2;
  ctx.save();
  ctx.beginPath(); ctx.rect(x0, y0, W, H); ctx.clip();
  ctx.fillStyle = "rgba(10,11,12,0.13)"; ctx.fillRect(x0, y0, W, H);
  const bw = Math.max(1.5, S / 300);
  ctx.fillStyle = "rgba(0,0,0,0.42)";
  ctx.fillRect(x0 + bw, y0 + bw, W - bw * 2, bw); ctx.fillRect(x0 + bw, y0 + bw, bw, H - bw * 2);
  ctx.fillStyle = "rgba(236,236,228,0.38)";
  ctx.fillRect(x0 + bw, y0 + H - bw * 2, W - bw * 2, bw); ctx.fillRect(x0 + W - bw * 2, y0 + bw, bw, H - bw * 2);
  const maxW = W * 0.9;
  const t = fitTitle(ctx, title, maxW, H * 0.2, 3);
  const subFs = Math.max(6, t.fs * 0.3);
  const lh = t.fs * 1.08;
  let y = y0 + H * 0.5 - ((t.lines.length - 1) * lh) / 2 - (sub ? subFs * 0.8 : 0);
  const draws = [];
  for (const line of t.lines) draws.push([line, y, `700 ${t.fs}px Archivo, "Helvetica Neue", Arial, sans-serif`, true]), y += lh;
  if (sub) draws.push([sub, y + subFs * 0.6, `500 ${subFs}px "JetBrains Mono", ui-monospace, Menlo, monospace`, false]);
  for (const [line, yy, font, big] of draws) {
    ctx.font = font; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.save(); ctx.translate(cx, yy); ctx.scale(big ? 0.86 : 1, 1);
    ctx.fillStyle = "rgba(236,236,228,0.36)"; ctx.fillText(line, 0, Math.max(0.8, t.fs * 0.045));
    ctx.fillStyle = "rgba(18,19,20,0.92)"; ctx.fillText(line, 0, 0);
    ctx.restore();
  }
  ctx.restore();
  void seed;
}

// The statues and the angel: the skin's luminance mapped into a narrow stone range, no weathering.
export function statueSkin(img, S) {
  // The 64 x 64 skin at its own pixels; a legacy 64 x 32 skin gets its left limbs from the right ones.
  const k = canvas(64, 64), kx = k.getContext("2d", { willReadFrequently: true });
  kx.imageSmoothingEnabled = false;
  kx.drawImage(img, 0, 0);
  if (img.naturalHeight <= 32) {
    kx.drawImage(k, 0, 16, 16, 16, 16, 48, 16, 16);
    kx.drawImage(k, 40, 16, 16, 16, 32, 48, 16, 16);
  }
  const d = kx.getImageData(0, 0, 64, 64), p = d.data;
  const lo = [0x6e, 0x6a, 0x70], hi = [0xc9, 0xc4, 0xcc];
  for (let i = 0; i < p.length; i += 4) {
    if (p[i + 3] < 8) continue;
    const l = (0.299 * p[i] + 0.587 * p[i + 1] + 0.114 * p[i + 2]) / 255;
    for (let c = 0; c < 3; c++) p[i + c] = lo[c] + (hi[c] - lo[c]) * l;
  }
  kx.putImageData(d, 0, 0);
  const c = canvas(S, S), x = c.getContext("2d");
  x.imageSmoothingEnabled = false;
  x.drawImage(k, 0, 0, S, S);
  return c;
}

// Radial glow, used for torch light and for the far lamps.
export function glowCanvas(color = "255,160,70") {
  const S = 128, c = canvas(S, S), x = c.getContext("2d");
  const g = x.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  g.addColorStop(0, `rgba(${color},1)`);
  g.addColorStop(0.25, `rgba(${color},0.45)`);
  g.addColorStop(0.6, `rgba(${color},0.08)`);
  g.addColorStop(1, `rgba(${color},0)`);
  x.fillStyle = g; x.fillRect(0, 0, S, S);
  return c;
}

// Soft dot for ash and dust.
export function dotCanvas(color = "220,215,230") {
  const S = 32, c = canvas(S, S), x = c.getContext("2d");
  const g = x.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  g.addColorStop(0, `rgba(${color},1)`); g.addColorStop(0.5, `rgba(${color},0.5)`); g.addColorStop(1, `rgba(${color},0)`);
  x.fillStyle = g; x.fillRect(0, 0, S, S);
  return c;
}

// The violet shattered sky seen through the ceiling: a gradient with cracks of lighter shard lines.
export function skyCanvas(seed = 9) {
  const W = 1024, H = 1024, c = canvas(W, H), x = c.getContext("2d");
  const g = x.createRadialGradient(W / 2, H * 0.62, 40, W / 2, H / 2, W * 0.7);
  g.addColorStop(0, "#f2d6e8"); g.addColorStop(0.18, "#b9a2e6"); g.addColorStop(0.5, "#5b3f9a");
  g.addColorStop(0.85, "#1d1438"); g.addColorStop(1, "#0e0b12");
  x.fillStyle = g; x.fillRect(0, 0, W, H);
  const r = rng(seed);
  x.lineCap = "round";
  for (let i = 0; i < 46; i++) {
    let px = r() * W, py = r() * H;
    x.strokeStyle = `rgba(236,220,255,${0.12 + r() * 0.3})`; x.lineWidth = 0.7 + r() * 2.2;
    x.beginPath(); x.moveTo(px, py);
    for (let k = 0; k < 5; k++) { px += (r() - 0.5) * 140; py += (r() - 0.5) * 140; x.lineTo(px, py); }
    x.stroke();
  }
  for (let i = 0; i < 260; i++) {
    x.fillStyle = `rgba(255,240,255,${0.2 + r() * 0.6})`;
    x.fillRect(r() * W, r() * H, 1 + r() * 2, 1 + r() * 2);
  }
  return c;
}
