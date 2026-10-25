# -*- coding: utf-8 -*-
import json, html, os
from urllib.parse import quote
d = json.load(open('catalog.json'))
CATS, MODS = d['cats'], d['mods']
by = {}
for m in MODS: by.setdefault(m['cat'], []).append(m)
for k in by: by[k].sort(key=lambda m: m['name'].lower())

def esc(s): return html.escape(s, quote=True)

# Item index data (site/items/data/items.json), used for the links from each mod to the items page.
ITEMS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'site', 'items', 'data', 'items.json')
IT = json.load(open(ITEMS_JSON, encoding='utf-8'))
IM = IT['mods']
ITEM_TOTAL = len(IT['items'])
per_mod = {}                       # items.json mod index -> number of items
for it in IT['items']: per_mod[it['m']] = per_mod.get(it['m'], 0) + 1
in_quests = {}                     # items.json mod index -> number of items some quest uses
for k in IT['qrefs']: in_quests[IT['items'][int(k)]['m']] = in_quests.get(IT['items'][int(k)]['m'], 0) + 1
by_file = {}                       # jar basename -> items.json mod indexes (empty file skipped)
for i, m in enumerate(IM):
    if m['file']: by_file.setdefault(os.path.basename(m['file']), []).append(i)

def item_line(m):
    """Small line under a mod's description linking to its items; '' if the mod has no items entry."""
    idxs = by_file.get(os.path.basename(m['file']), []) if m['file'] else []
    if not idxs: return ''
    n = sum(per_mod.get(i, 0) for i in idxs)
    q = sum(in_quests.get(i, 0) for i in idxs)
    # One items.json entry per jar: link straight to its filter. A jar split into several
    # entries (Lycanites, Wireless Redstone...) links to the index with the summed count.
    href = '../items/#mod=' + quote(IM[idxs[0]]['id'], safe='') if len(idxs) == 1 else '../items/'
    tail = f' <span class="sep">&middot;</span> {q:,} in quests' if q > 0 else ''
    return (f'<div class="items-line"><a class="items" href="{esc(href)}">'
            f'<span class="n">{n:,}</span> {"item" if n == 1 else "items"}</a>{tail}</div>')

CSS = """
:root{
  --paper:#E9EAE4; --surface:#F7F8F3; --sunk:#DFE1DA;
  --ink:#171B19; --ink-2:#3E4642; --muted:#6A726C; --rule:#CDD1C8;
  --ember:#A33F17; --ember-ink:#8E3712; --patina:#2C4A43;
  --shadow:rgba(23,27,25,.07);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#111412; --surface:#191D1A; --sunk:#0C0F0D;
    --ink:#E7E9E2; --ink-2:#C2C7BE; --muted:#8B948B; --rule:#282E29;
    --ember:#E58A55; --ember-ink:#EFA274; --patina:#7FB6A6;
    --shadow:rgba(0,0,0,.4);
  }
}
:root[data-theme="dark"]{
  --paper:#111412; --surface:#191D1A; --sunk:#0C0F0D;
  --ink:#E7E9E2; --ink-2:#C2C7BE; --muted:#8B948B; --rule:#282E29;
  --ember:#E58A55; --ember-ink:#EFA274; --patina:#7FB6A6;
  --shadow:rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Source Serif 4",Georgia,"Times New Roman",serif;
  font-size:16px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
h1,h2,h3,.ui{font-family:Archivo,"Helvetica Neue",Arial,sans-serif}
.mono{font-family:"JetBrains Mono",ui-monospace,"SFMono-Regular",Menlo,monospace}

/* ---- masthead ---- */
header.mast{padding:56px 0 30px;border-bottom:2px solid var(--ink)}
.kicker{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--ember-ink);margin:0 0 14px}
h1{font-size:clamp(42px,8vw,76px);line-height:.94;font-weight:800;letter-spacing:-.032em;
  margin:0;text-wrap:balance}
h1 .amp{color:var(--ember);font-weight:600}
.lede{max-width:60ch;margin:20px 0 0;font-size:17.5px;color:var(--ink-2)}
.specs{display:flex;flex-wrap:wrap;gap:0 26px;margin:26px 0 0;
  font-family:"JetBrains Mono",monospace;font-size:11.5px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.specs b{color:var(--ink);font-weight:500}
.specs a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--rule)}
.specs a:hover{color:var(--ink-2);border-color:var(--ink-2)}
.also{display:flex;flex-wrap:wrap;gap:6px 22px;margin:18px 0 0;font-family:Archivo,sans-serif;font-size:14px}
.also a{color:var(--ember-ink);text-decoration:none;border-bottom:1px solid var(--ember);font-weight:600}
.also a:hover{color:var(--ink);border-color:var(--ink)}

/* ---- site nav, the same strip every page carries ---- */
nav.site{border-bottom:1px solid var(--rule);background:var(--surface)}
nav.site .wrap{display:flex;align-items:center;gap:2px 18px;flex-wrap:wrap;min-height:50px;padding-top:6px;padding-bottom:6px}
nav.site .brand{display:flex;align-items:center;gap:9px;font-family:Archivo,sans-serif;font-weight:800;font-size:15px;
  letter-spacing:-.01em;color:var(--ink);text-decoration:none;margin-right:auto}
nav.site .brand img{width:22px;height:22px;border-radius:4px}
nav.site a:not(.brand){font-family:Archivo,sans-serif;font-size:13.5px;font-weight:500;color:var(--ink-2);text-decoration:none;
  padding:4px 1px;border-bottom:2px solid transparent}
nav.site a:not(.brand):hover{color:var(--ink);border-color:var(--rule)}
nav.site a[aria-current="page"]{color:var(--ember-ink);border-color:var(--ember)}
nav.site .theme{margin-left:4px;display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;padding:0;border:1px solid transparent;border-radius:50%;background:none;color:var(--ink-2);cursor:pointer}
nav.site .theme:hover{color:var(--ink);border-color:var(--rule)}
nav.site .theme:focus-visible{outline:2px solid var(--ember);outline-offset:1px}
nav.site .theme svg{width:17px;height:17px;display:none}
nav.site .theme[data-mode="auto"] .i-auto,nav.site .theme[data-mode="light"] .i-light,nav.site .theme[data-mode="dark"] .i-dark{display:block}
footer a{color:var(--ink-2);text-decoration:none;border-bottom:1px solid var(--rule)}
footer a:hover{color:var(--ember-ink);border-color:var(--ember)}

/* ---- sticky control bar ---- */
.bar{position:sticky;top:0;z-index:20;background:var(--paper);
  border-bottom:1px solid var(--rule);padding:12px 0 11px;
  box-shadow:0 6px 18px -14px var(--shadow)}
.bar-in{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
#q{flex:0 0 236px;font-family:"JetBrains Mono",monospace;font-size:12.5px;
  padding:7px 11px;color:var(--ink);background:var(--surface);
  border:1px solid var(--rule);border-radius:2px}
#q::placeholder{color:var(--muted)}
#q:focus{outline:2px solid var(--ember);outline-offset:1px;border-color:transparent}
nav.chips{display:flex;flex-wrap:wrap;gap:5px 7px;flex:1}
nav.chips a{font-family:Archivo,sans-serif;font-size:12px;font-weight:500;
  text-decoration:none;color:var(--ink-2);padding:3px 9px;border-radius:2px;
  border:1px solid transparent;white-space:nowrap}
nav.chips a:hover{border-color:var(--rule);color:var(--ink)}
nav.chips a:focus-visible{outline:2px solid var(--ember);outline-offset:1px}
nav.chips a .n{font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--muted);
  margin-left:5px;font-variant-numeric:tabular-nums}
nav.chips a.last{color:var(--patina)}
#count{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--muted);
  font-variant-numeric:tabular-nums;white-space:nowrap}

/* ---- sections ---- */
section{padding:54px 0 10px;scroll-margin-top:64px}
.sec-head{padding-bottom:9px;border-bottom:1px solid var(--ink);margin-bottom:6px}
.sec-title{display:flex;align-items:baseline;gap:12px}
h2{font-size:26px;font-weight:700;letter-spacing:-.018em;margin:0;line-height:1.15}
.sec-note{max-width:58ch;margin:6px 0 0;font-size:14.5px;color:var(--muted);line-height:1.45}
.tally{font-family:"JetBrains Mono",monospace;font-size:10.5px;color:var(--muted);
  letter-spacing:.11em;text-transform:uppercase;white-space:nowrap;
  border:1px solid var(--rule);border-radius:2px;padding:1px 6px;translate:0 -2px}

.grid{column-count:2;column-gap:46px}
.mod{padding:15px 0 14px;border-bottom:1px solid var(--rule);
  break-inside:avoid;-webkit-column-break-inside:avoid}
.mod-top{display:flex;align-items:baseline;gap:10px}
.mod h3{font-size:16.5px;font-weight:600;margin:0;letter-spacing:-.006em;line-height:1.3}
.dots{flex:1;border-bottom:1px dotted var(--rule);transform:translateY(-3px);min-width:12px}
.ver{font-family:"JetBrains Mono",monospace;font-size:10.5px;color:var(--muted);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.mod p{margin:5px 0 0;font-size:14.5px;line-height:1.5;color:var(--ink-2);max-width:56ch}
.mod .items-line{margin:6px 0 0;font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.mod .items{color:var(--muted);text-decoration:none;border-bottom:1px dotted var(--rule)}
.mod .items:hover{color:var(--ink);border-color:var(--ink)}
.mod .items:focus-visible{outline:2px solid var(--ember);outline-offset:1px}
.mod .items .n{color:var(--ember-ink)}

/* ---- the quiet section ---- */
#Under{margin-top:44px;background:var(--sunk);padding:40px 0 30px;
  border-top:1px solid var(--rule)}
#Under .sec-head{border-bottom-color:var(--patina)}
#Under h2{color:var(--patina)}
#Under .grid{column-count:3;column-gap:36px}
#Under .mod{padding:12px 0 11px}
#Under .mod h3{font-size:14.5px;font-weight:600}
#Under .mod p{font-size:13px;line-height:1.45;color:var(--muted);max-width:46ch}
#Under .ver{font-size:10px}
#Under .mod .items-line{font-size:10px;margin-top:4px}

.empty{display:none;padding:40px 0;font-size:15px;color:var(--muted)}
body.no-hits .empty{display:block}
.hidden{display:none !important}

footer{padding:30px 0 56px;border-top:1px solid var(--rule);margin-top:30px;
  font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--muted)}
footer .wrap{display:flex;flex-wrap:wrap;gap:6px 22px}

@media (max-width:1000px){ #Under .grid{column-count:2} }
@media (max-width:860px){
  .wrap{padding:0 20px}
  .grid,#Under .grid{column-count:1}
  header.mast{padding:38px 0 24px}
  #q{flex:1 1 100%}
  h2{font-size:23px}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
html{scroll-behavior:smooth}
"""

def mod_html(m):
    ver = f'<span class="ver">{esc(m["ver"])}</span>' if m['ver'] else ''
    dots = '<span class="dots"></span>' if m['ver'] else ''
    return (f'<article class="mod" data-s="{esc((m["name"]+" "+m["desc"]).lower())}">'
            f'<div class="mod-top"><h3>{esc(m["name"])}</h3>{dots}{ver}</div>'
            f'<p>{esc(m["desc"])}</p>{item_line(m)}</article>')

chips, sections = [], []
for key, label, note in CATS:
    items = by.get(key, [])
    cls = ' class="last"' if key == 'Under' else ''
    chips.append(f'<a href="#{key}"{cls} data-chip="{key}">{label}<span class="n">{len(items)}</span></a>')
    inner = ('<div class="sec-head">'
             f'<div class="sec-title"><h2>{label}</h2>'
             f'<span class="tally">{len(items)} mods</span></div>'
             f'<p class="sec-note">{note}</p></div>'
             '<div class="grid">' + ''.join(mod_html(m) for m in items) + '</div>')
    if key == 'Under':
        sections.append(f'<section id="{key}" data-sec="{key}"><div class="wrap">{inner}</div></section>')
    else:
        sections.append(f'<section id="{key}" data-sec="{key}" class="wrap">{inner}</section>')

JS = """
const q=document.getElementById('q'),cnt=document.getElementById('count'),
 mods=[...document.querySelectorAll('.mod')],secs=[...document.querySelectorAll('[data-sec]')];
const TOTAL=mods.length;
function run(){
  const t=q.value.trim().toLowerCase();
  let n=0;
  mods.forEach(m=>{const hit=!t||m.dataset.s.includes(t);m.classList.toggle('hidden',!hit);if(hit)n++;});
  secs.forEach(s=>{
    const vis=s.querySelectorAll('.mod:not(.hidden)').length;
    s.classList.toggle('hidden',vis===0);
    const tally=s.querySelector('.tally');
    if(tally) tally.textContent=(t?vis+' of '+s.querySelectorAll('.mod').length:vis+' mods');
    const chip=document.querySelector('[data-chip="'+s.dataset.sec+'"]');
    if(chip) chip.classList.toggle('hidden',vis===0);
  });
  document.body.classList.toggle('no-hits',n===0);
  cnt.textContent=t?n+' / '+TOTAL:TOTAL+' mods';
}
q.addEventListener('input',run);
q.addEventListener('keydown',e=>{if(e.key==='Escape'){q.value='';run();}});
run();
"""

# Theme toggle: head script (no flash of the wrong theme), then the button and the click script.
THEME_HEAD = """<script>(function(){try{var t=localStorage.getItem('qf-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}})()</script>"""

THEME_JS = """<script>(function(){var b=document.querySelector('[data-theme-toggle]');if(!b)return;var h=document.documentElement,mq=matchMedia('(prefers-color-scheme: dark)');function mode(){try{var t=localStorage.getItem('qf-theme');return t==='light'||t==='dark'?t:'auto'}catch(e){return 'auto'}}function sys(){return mq.matches?'dark':'light'}function show(){var m=mode();b.dataset.mode=m;var s=m==='auto'?'Theme follows your system ('+sys()+')':'Theme: '+m;b.title=s+'. Click to switch.';b.setAttribute('aria-label',s)}b.addEventListener('click',function(){var m=mode(),s=sys(),n=(m==='auto'||m===s)?(s==='dark'?'light':'dark'):'auto';try{if(n==='auto')localStorage.removeItem('qf-theme');else localStorage.setItem('qf-theme',n)}catch(e){}if(n==='auto')h.removeAttribute('data-theme');else h.setAttribute('data-theme',n);show()});if(mq.addEventListener)mq.addEventListener('change',show);show()})();</script>"""

THEME_BUTTON = """<button class="theme" type="button" data-theme-toggle aria-label="Theme" title="Theme"><svg class="i-auto" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18V3z" fill="currentColor"/><circle cx="12" cy="12" r="8.25" fill="none" stroke="currentColor" stroke-width="1.5"/></svg><svg class="i-light" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="currentColor"/><g stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/></g></svg><svg class="i-dark" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" fill="currentColor"/></svg></button>"""

doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mod list · Quest Forge</title>
<meta name="description" content="Every mod in the Quest Forge modpack for Minecraft 1.7.10, sorted into what it adds, with a line on what each one actually does.">
<meta name="theme-color" content="#E9EAE4">
<link rel="icon" href="../favicon.png" type="image/png">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
{THEME_HEAD}
<style>{CSS}</style>
</head>
<body>

<nav class="site" aria-label="Site"><div class="wrap">
  <a class="brand" href="../"><img src="../favicon.png" alt="">Quest Forge</a>
  <a href="../play/">Get the pack</a>
  <a href="../first-night/">First night</a>
  <a href="./" aria-current="page">Mods</a>
  <a href="../items/">Items</a>
  <a href="../worlds/">Worlds</a>
  <a href="../enchantments/">Enchantments</a>
  <a href="../ore-atlas/">Ore atlas</a>
  <a href="../online/">Server</a>
  {THEME_BUTTON}
</div></nav>

<header class="mast"><div class="wrap">
  <p class="kicker">Minecraft 1.7.10 &middot; Modpack Contents</p>
  <h1>Quest&nbsp;Forge</h1>
  <p class="lede">A quest-driven kitchen-sink pack: eleven categories of content mods stacked on a
  Better Questing spine, from the Twilight Forest to a working TARDIS. Here's everything that's in it,
  and what each piece actually does.</p>
  <div class="specs">
    <span><b>111</b> mod files</span>
    <span><a href="../items/"><b>{ITEM_TOTAL:,}</b> items indexed</a></span>
    <span><b>141</b> registered mods</span>
    <span>Minecraft <b>1.7.10</b></span>
    <span>Forge <b>10.13.4.1558</b></span>
    <span>Java <b>8</b></span>
  </div>
  <p class="also"><a href="../items/">Browse every item, recipe and quest use &rarr;</a><a href="../play/">Get the pack &rarr;</a></p>
</div></header>

<div class="bar"><div class="wrap bar-in">
  <input id="q" type="search" placeholder="filter mods…" aria-label="Filter mods" autocomplete="off">
  <nav class="chips" aria-label="Categories">{''.join(chips)}</nav>
  <span id="count">111 mods</span>
</div></div>

{''.join(sections)}

<div class="wrap"><p class="empty">No mods match that filter.</p></div>

<footer><div class="wrap">
  <span>Generated from the live instance</span>
  <span>Load order resolved by Forge</span>
  <span>Performance &amp; background mods listed last</span>
  <a href="../">Home</a><a href="../items/">Item index</a><a href="../worlds/">Worlds</a><a href="../enchantments/">Enchantments</a>
  <a href="https://github.com/MarionWhite/quest-forge">Source on GitHub</a>
</div></footer>

<script>{JS}</script>
{THEME_JS}
</body>
</html>
"""
# Served at /mods/ (the site root is the homepage, site/home/).
open('../../site/mods/index.html','w',encoding='utf-8',newline='').write(doc)
print("written", len(doc), "bytes;", len(MODS), "mods")
