// The scare overlay: the 1.7.10 in-game HUD and death screen, drawn with the game's own GUI textures
// (icons.png, widgets.png, the ascii.png font) at the game's GUI scale, on a canvas over the Krypt stage.
//   const hud = await createHud(stageEl)
//   hud.draw(f, t)       f from rig.evaluate: hp, hpPrev, blink, hpMode, hurt, fire, tints, white, black, death, chat, ...
//   hud.hit(x, y)        which death-screen button a stage-relative point is on ("respawn" | "title" | null)
import { loadImg, clamp, rngOf } from "./rig.js";

const ITEMS = ["item_iron_sword", "item_stone_pickaxe", "k:torch_on", "item_bread", "item_apple"];

export async function createHud(host) {
  const [icons, widgets, font, fire, ...items] = await Promise.all(["icons", "widgets", "ascii", "fire_layer_1", ...ITEMS].map(loadImg));
  const canvas = document.createElement("canvas");
  canvas.className = "qfs-hud";
  canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;z-index:9;pointer-events:none;image-rendering:pixelated;image-rendering:crisp-edges";
  host.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  const H = { canvas, ctx, w: 320, h: 240, scale: 1, btn: {}, enabledAt: 1 };

  // ---- the font: glyph widths read from the texture, as FontRenderer.readFontTexture does --------------------
  const widths = new Array(256).fill(8);
  const tints = new Map();
  if (font) {
    const c = document.createElement("canvas"); c.width = font.width; c.height = font.height;
    const x = c.getContext("2d"); x.drawImage(font, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height).data, cs = c.width / 16;
    for (let ch = 0; ch < 256; ch++) {
      const col = ch % 16, row = (ch / 16) | 0;
      let last = -1;
      for (let px = cs - 1; px >= 0 && last < 0; px--) for (let py = 0; py < cs; py++) if (d[((row * cs + py) * c.width + col * cs + px) * 4 + 3] > 0) { last = px; break; }
      widths[ch] = ch === 32 ? 4 : last + 2;
    }
  }
  function tinted(hex) {
    if (!tints.has(hex)) {
      const c = document.createElement("canvas"); c.width = font.width; c.height = font.height;
      const x = c.getContext("2d"); x.drawImage(font, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = hex; x.fillRect(0, 0, c.width, c.height);
      tints.set(hex, c);
    }
    return tints.get(hex);
  }
  const COL = { 0: "#000000", 1: "#0000aa", 2: "#00aa00", 3: "#00aaaa", 4: "#aa0000", 5: "#aa00aa", 6: "#ffaa00", 7: "#aaaaaa", 8: "#555555", 9: "#5555ff", a: "#55ff55", b: "#55ffff", c: "#ff5555", d: "#ff55ff", e: "#ffff55", f: "#ffffff" };
  const shadowOf = (hex) => { const n = parseInt(hex.slice(1), 16); const s = (n & 0xfcfcfc) >> 2; return "#" + s.toString(16).padStart(6, "0"); };
  const width = (s) => { let w = 0; for (let i = 0; i < s.length; i++) { if (s[i] === "§") { i++; continue; } w += widths[s.charCodeAt(i) & 255]; } return w; };
  function run(s, x, y, color, sc = 1, shadowPass = false) {
    let col = color;
    for (let i = 0; i < s.length; i++) {
      if (s[i] === "§") { const k = COL[s[i + 1]]; if (k) col = shadowPass ? shadowOf(k) : k; i++; continue; }
      const ch = s.charCodeAt(i) & 255;
      if (ch !== 32 && font) ctx.drawImage(tinted(col), (ch % 16) * 8, ((ch / 16) | 0) * 8, 8, 8, Math.round(x), Math.round(y), 8 * sc, 8 * sc);
      x += widths[ch] * sc;
    }
  }
  H.text = (s, x, y, color = "#ffffff", { shadow = true, scale = 1 } = {}) => {
    if (shadow) run(s, x + scale, y + scale, shadowOf(color), scale, true);
    run(s, x, y, color, scale);
  };
  H.center = (s, cx, y, color = "#ffffff", o = {}) => H.text(s, cx - width(s) * (o.scale || 1) / 2, y, color, o);
  H.width = width;

  // ---- sizing: GuiScale "auto" (ScaledResolution) ------------------------------------------------------------
  H.size = () => {
    const W = host.clientWidth || innerWidth, Ht = host.clientHeight || innerHeight;
    let s = 1; while (W / (s + 1) >= 320 && Ht / (s + 1) >= 240) s++;
    H.scale = s; H.w = Math.ceil(W / s); H.h = Math.ceil(Ht / s);
    if (canvas.width !== H.w || canvas.height !== H.h) { canvas.width = H.w; canvas.height = H.h; }
  };
  H.size();
  const blit = (img, sx, sy, sw, sh, dx, dy, dw = sw, dh = sh) => { if (img) ctx.drawImage(img, sx, sy, sw, sh, Math.round(dx), Math.round(dy), dw, dh); };
  H.blit = blit;

  // ---- the in-game HUD (GuiIngame.renderGameOverlay) ----------------------------------------------------------------
  function hotbar(f) {
    const { w, h } = H, x0 = w / 2 - 91;
    blit(widgets, 0, 0, 182, 22, x0, h - 22);
    blit(widgets, 0, 22, 24, 24, x0 - 1 + (f.hotbar || 0) * 20, h - 22 - 1);
    items.forEach((im, i) => { if (im && !(f.burnt && f.burnt[i])) blit(im, 0, 0, 16, 16, w / 2 - 90 + i * 20 + 2, h - 16 - 3); });
    // Experience: the bar and the level in green with a black outline.
    blit(icons, 0, 64, 182, 5, x0, h - 32 + 3);
    blit(icons, 0, 69, Math.round(182 * 0.37), 5, x0, h - 32 + 3);
    const s = "7", lx = (w - width(s)) / 2, ly = h - 31 - 4;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) H.text(s, lx + dx, ly + dy, "#000000", { shadow: false });
    H.text(s, lx, ly, "#80ff20", { shadow: false });
  }
  function hearts(f, t) {
    const { w, h } = H, left = w / 2 - 91, top = h - 39;
    const hp = Math.ceil(clamp(f.hp, 0, 20)), prev = Math.ceil(clamp(f.hpPrev ?? f.hp, 0, 20));
    const i2 = 16 + (f.hpMode === "poison" ? 36 : f.hpMode === "wither" ? 72 : 0), hl = f.blink ? 1 : 0;
    const rnd = rngOf(Math.floor(t * 20) * 31 + 7);
    for (let i = 9; i >= 0; i--) {
      const x = left + i * 8;
      let y = top;
      if (hp <= 4) y += Math.floor(rnd() * 2);
      blit(icons, 16 + hl * 9, 0, 9, 9, x, y);
      if (hl) { if (i * 2 + 1 < prev) blit(icons, i2 + 54, 0, 9, 9, x, y); if (i * 2 + 1 === prev) blit(icons, i2 + 63, 0, 9, 9, x, y); }
      if (i * 2 + 1 < hp) blit(icons, i2 + 36, 0, 9, 9, x, y);
      if (i * 2 + 1 === hp) blit(icons, i2 + 45, 0, 9, 9, x, y);
    }
    // Food, full.
    const right = w / 2 + 91;
    for (let i = 0; i < 10; i++) { const x = right - i * 8 - 9; blit(icons, 16, 27, 9, 9, x, top); blit(icons, 52, 27, 9, 9, x, top); }
    // Air (suffocating in a slime, under water): the bubbles over the food.
    if (f.air != null) {
      const n = Math.ceil(clamp(f.air) * 10), pop = Math.ceil(clamp(f.air) * 10) - Math.floor(clamp(f.air) * 10);
      for (let i = 0; i < n; i++) blit(icons, i < n - pop ? 16 : 25, 18, 9, 9, right - i * 8 - 9, top - 10);
    }
  }
  // The 1.7.10 burning overlay (ItemRenderer.renderFireInFirstPerson): two fire_layer_1 quads at the bottom corners.
  function fireOverlay(amt, t) {
    if (!fire) return;
    const { w, h } = H, fr = Math.floor(t * 20) % 32;
    ctx.globalAlpha = 0.9 * clamp(amt);
    // A unit quad half a block in front of the eye at the hand's 70 degree field: 1.43 screen heights square,
    // its top at 0.215 of the height, its centre 0.24 blocks either side (0.343 screen heights).
    const qh = h * 1.43, qw = qh * Math.cos(10 * Math.PI / 180);
    for (let i = 0; i < 2; i++) {
      const cx = w / 2 + (i ? 1 : -1) * 0.343 * h;
      ctx.save();
      ctx.translate(Math.round(cx), Math.round(h * 0.215 + qh / 2));
      ctx.scale(-1, 1);   // both quads run u from max to min
      ctx.drawImage(fire, 0, fr * 16, 16, 16, -qw / 2, -qh / 2, qw, qh);
      ctx.restore();
    }
    ctx.globalAlpha = 1;
  }
  function chat(line) {
    const { h } = H, y = h - 48 + 20;
    ctx.fillStyle = "rgba(0,0,0,0.5)"; ctx.fillRect(2, y - 9, 324, 9);
    H.text(line, 2, y - 8, "#ffffff");
  }
  function button(label, x, y, state) {   // state 0 disabled, 1 normal, 2 hover (GuiButton)
    blit(widgets, 0, 46 + state * 20, 100, 20, x, y);
    blit(widgets, 200 - 100, 46 + state * 20, 100, 20, x + 100, y);
    H.center(label, x + 100, y + 6, state === 0 ? "#a0a0a0" : state === 2 ? "#ffffa0" : "#e0e0e0");
  }
  // GuiGameOver.drawScreen: the red gradient, "You died!" at twice the size, the score, two buttons.
  function deathScreen(f, t) {
    const { w, h } = H, d = clamp(f.death);
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, `rgba(80,0,0,${(0x60 / 255 * d).toFixed(3)})`); g.addColorStop(1, `rgba(128,48,48,${(0xa0 / 255 * d).toFixed(3)})`);
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    if (d < 1) return;
    H.center("You died!", w / 2, 60, "#ffffff", { scale: 2 });
    H.center("Score: §e" + (f.score ?? 0), w / 2, 100, "#ffffff");
    const on = (f.deadFor ?? 9) >= 1;
    const bx = w / 2 - 100;
    H.btn = { respawn: [bx, h / 4 + 72, 200, 20], title: [bx, h / 4 + 96, 200, 20], on };
    button("Respawn", bx, h / 4 + 72, on ? (f.hover === "respawn" ? 2 : 1) : 0);
    button("Title screen", bx, h / 4 + 96, on ? (f.hover === "title" ? 2 : 1) : 0);
  }
  function glitch(amt, t) {
    const rng = rngOf(Math.floor(t * 18) + 5), n = Math.floor(3 + amt * 12), { w, h } = H;
    for (let i = 0; i < n; i++) {
      const y = Math.floor(rng() * h), hh = 1 + Math.floor(rng() * 8), x = Math.floor(rng() * w * 0.6), ww = 20 + Math.floor(rng() * w * 0.6);
      const c = rng(); ctx.fillStyle = c < 0.45 ? `rgba(170,40,255,${(0.3 + amt * 0.4).toFixed(2)})` : c < 0.7 ? "rgba(0,0,0,0.85)" : c < 0.85 ? "rgba(255,255,255,0.6)" : "rgba(224,121,250,0.6)";
      ctx.fillRect(x, y, ww, hh);
    }
    for (let i = 0; i < amt * 90; i++) { ctx.fillStyle = rng() < 0.5 ? "#e079fa" : "#000"; ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), 1, 1); }
  }
  // Blocky blood on the lens: square GUI pixels that run down.
  function splats(list, t) {
    const { w, h } = H;
    for (const s of list) {
      const age = t - s.t0; if (age < 0) continue;
      const rng = rngOf(s.seed || 1), cx = s.x * w, cy = s.y * h, R = (s.r || 16) * Math.min(1, age / 0.08);
      for (let i = 0; i < 22; i++) {
        const a = rng() * 6.283, dd = Math.sqrt(rng()) * R, sz = 2 + Math.floor(rng() * 4);
        ctx.fillStyle = i % 4 === 0 ? "#4a0000" : i % 5 === 0 ? "#c01010" : "#7e0606";
        ctx.fillRect(Math.round(cx + Math.cos(a) * dd), Math.round(cy + Math.sin(a) * dd), sz, sz);
      }
      for (let i = 0; i < 3; i++) {
        const dx = Math.round(cx + (rng() - 0.5) * R), len = Math.min(10 + rng() * 40, Math.max(0, age - 0.1) * (14 + rng() * 26));
        ctx.fillStyle = "#7e0606"; ctx.fillRect(dx, Math.round(cy), 2, Math.round(len));
      }
    }
  }

  H.draw = (f, t) => {
    const { w, h } = H;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, w, h);
    for (const tn of f.tints || []) if (tn[3] > 0.003) { ctx.fillStyle = `rgba(${tn[0]},${tn[1]},${tn[2]},${Math.min(1, tn[3]).toFixed(3)})`; ctx.fillRect(0, 0, w, h); }
    if (f.vig && f.vig[3] > 0.003) {
      const g = ctx.createRadialGradient(w / 2, h / 2, h * (f.vigIn ?? 0.3), w / 2, h / 2, h * (f.vigR ?? 0.95));
      g.addColorStop(0, `rgba(${f.vig[0]},${f.vig[1]},${f.vig[2]},0)`); g.addColorStop(1, `rgba(${f.vig[0]},${f.vig[1]},${f.vig[2]},${Math.min(1, f.vig[3]).toFixed(3)})`);
      ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    }
    if (f.splats && f.splats.length) splats(f.splats, t);
    if (f.glitch > 0.01) glitch(f.glitch, t);
    if (f.fire > 0.01) fireOverlay(f.fire, t);
    if (f.hurt > 0.01) { ctx.fillStyle = `rgba(190,0,0,${(f.hurt * 0.22).toFixed(3)})`; ctx.fillRect(0, 0, w, h); }
    if (f.white > 0.003) { ctx.fillStyle = `rgba(255,255,255,${clamp(f.white).toFixed(3)})`; ctx.fillRect(0, 0, w, h); }
    if (f.black > 0.003) { ctx.fillStyle = `rgba(0,0,0,${clamp(f.black).toFixed(3)})`; ctx.fillRect(0, 0, w, h); }
    if (f.hud !== false) { hotbar(f); hearts(f, t); }
    if (f.chat) chat(f.chat);
    if (f.death > 0.003) deathScreen(f, t);
  };
  // Stage-relative CSS pixels -> a death-screen button.
  H.hit = (x, y) => {
    const b = H.btn; if (!b || !b.on) return null;
    const gx = x / H.scale, gy = y / H.scale;
    for (const k of ["respawn", "title"]) { const r = b[k]; if (r && gx >= r[0] && gx < r[0] + r[2] && gy >= r[1] && gy < r[1] + r[3]) return k; }
    return null;
  };
  H.dispose = () => canvas.remove();
  return H;
}
