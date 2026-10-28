#!/usr/bin/env python3
"""Round 8 screams: real recorded men, picked by what people chose, played as recorded.

    QF_DL=<dir> QF_TMP=<dir> /opt/anaconda3/bin/python3 -I tools/music/scream_pack3.py fetch|build|audition [OUTDIR]

The owner (r8): "THE SCREAMS SOUND LIKE SHIT. Find actual fucking open source scream audio files." Nobody on the team
can hear, so nothing here judges a scream by ear or by spectrogram:
  * the pool is ranked by what people chose on Freesound: rank = Bayesian average rating (prior 3.8 over 5 ratings)
    + 0.15 * log10(downloads), from each sound page; licences CC0 1.0, CC BY 3.0 or 4.0 only (checked on the page);
  * only male voices, acted or real performances; recordings that look clipped at the source (decoded preview peak
    above +1 dBFS with >0.1% of samples above -0.3 dBFS) are left out;
  * processing is trim, fade and level, nothing else: no pitch shift, no EQ, no reverb, no layers. Level = the
    loudest 400 ms at -12 dBFS RMS (the voice skips the compressor, so this is its level in the mix), capped at
    -1 dBFS true peak. 48 kHz, 192 kbps AAC (AudioToolbox if present);
  * the manifest puts the five events on qfaudio's 'voice' bus: centred, no panner, no playbackRate change, no
    reverb send, gain at most 1, past the compressor (see site/lib/qfaudio.js).
The owner picks by ear on the audition page (`audition OUTDIR`): each candidate raw and as the game plays it.
Sources: the Freesound HQ previews (Ogg Vorbis, ~110 kbps mono), each in its own new $QF_DL/fs<ID>/ directory.
"""
import os, sys, json, re, html, math, shutil, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SFX = os.path.join(ROOT, "site", "lib", "sfx")
TMP = os.environ.get("QF_TMP", "/tmp/qf_scream3")
DL = os.environ.get("QF_DL", os.path.join(TMP, "dl"))
META = os.path.join(HERE, "scream_pack3_meta.json")
SR = 48000
LICENCES = {"publicdomain/zero/1.0": ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
            "licenses/by/4.0": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
            "licenses/by/3.0": ("CC BY 3.0", "https://creativecommons.org/licenses/by/3.0/")}

# key -> (freesound id, take start s, take end s, best fit, what the page says about it)
# Times are in the HQ preview. Fit: death (a man dying), scream (terror/pain), far (a scream heard from away, its own
# room), underwater (drowning), jump (a short startled cry at the lunge).
TAKES = {
    "dinsfire":   ("169628", 0.03, 6.25, "death", "\"Just a recording of me screaming\", AT3525 condenser mic"),
    "jbe_multi":  ("173944", 0.30, 3.95, "death", "first take of a 25 s set; the uploader made it for lack of good male screams"),
    "jbe2":       ("243376", 0.30, 3.00, "death", "raw, unprocessed (USB mic into Audition)"),
    "jbe1":       ("243377", 0.15, 4.70, "death", "raw, unprocessed; ends in a gasp"),
    "jbe3":       ("243381", 0.12, 2.80, "death", "raw, unprocessed"),
    "marc":       ("556976", 0.55, 3.25, "death", "first take of a 14 s set; the uploader's first voice work"),
    "archeos":    ("325548", 19.15, 22.0, "death", "a 30-year-old male actor, screams of pain and fear (24-bit)"),
    "martian":    ("530471", 7.10, 10.70, "death", "\"a paid professional actor\", torture series"),
    "oldedgar":   ("131710", 0.45, 3.20, "death", "\"a mortally wounded scream\", first of a 15 s set"),
    "warrior":    ("417539", 0.20, 1.45, "death", "voice actor: a warrior's last breath (32-bit)"),
    "thijs":      ("9432", 0.40, 3.30, "death", "torture scream recorded for film sound (Utrecht); the most downloaded male scream"),
    "akridiy":    ("759458", 0.00, 3.60, "death", "single scream, a 2002 Sony dictaphone recording"),
    "robot0":     ("270453", 0.00, 2.30, "death", "game sound studio: panic and pain, for dying characters (24-bit)"),
    "stuxer":     ("401210", 0.30, 2.85, "death", "a man's painful cry"),
    "roar":       ("265554", 0.03, 3.75, "scream", "Røde K-2 in a professional studio; a roar-scream of rage"),
    "yude2":      ("445007", 0.05, 2.40, "scream", "\"man struggling\" (24-bit)"),
    "gab1":       ("220290", 0.02, 2.10, "scream", "male, pain; UPF film-sound students"),
    "gab3":       ("220293", 0.08, 1.60, "scream", "male, pain; UPF film-sound students"),
    "bram":       ("9431", 2.95, 4.60, "scream", "film sound (Utrecht), third shout of a set"),
    "bram_oeaah": ("9425", 0.15, 1.60, "scream", "film sound (Utrecht)"),
    "adrian2":    ("220619", 0.15, 1.55, "scream", "horror scream; UPF film-sound students"),
    "adrian1":    ("219858", 0.00, 1.10, "scream", "male horror scream; UPF film-sound students"),
    "street_d":   ("548377", 8.65, 10.35, "far", "a man screaming in an empty street (24-bit): the street is the room"),
    "street_c":   ("548377", 5.65, 7.00, "far", "the same street, another take"),
    "hall13":     ("179317", 0.00, 7.00, "far", "a long cry in a reverberant hall (Zoom H4n); may be clipped at the source"),
    "drown_a":    ("752733", 0.90, 3.60, "underwater", "screamed into a bathtub, the mic under water (Zoom H6)"),
    "drown_b":    ("752733", 4.15, 7.70, "underwater", "the same recording, second half"),
    "drowning":   ("725874", 0.30, 4.50, "underwater", "a man drowning in water"),
    "rainmach":   ("583594", 29.0, 33.6, "underwater", "own scream for a film's death by water; picked from a 2:24 take"),
    "fm4":        ("695387", 0.00, 0.70, "jump", "a warrior's death cry from a sound library seller (24-bit)"),
    "fm3":        ("695386", 0.00, 0.62, "jump", "the same set"),
    "tonsil":     ("416838", 0.08, 0.80, "jump", "\"Pain! Death! Scream!\" (24-bit); 23k downloads"),
    "victim":     ("813310", 0.00, 0.90, "jump", "a man pretending to scream in pain"),
    "screamm":    ("536786", 0.00, 0.90, "jump", "a young man's terrified scream"),
}
CAP = {"death": 4.5, "scream": 4.0, "far": 8.0, "underwater": 4.5, "jump": 1.6}   # longer takes fade out over 0.5 s

# The defaults wired into the site: the best-ranked candidates of each fit (see `rank`), at most two takes per
# performer, skipping a take the audition flags as maybe clipped or flags twice, and the dictaphone recording.
# The owner's picks replace these.
DEFAULTS = {
    "qf.scare.death_scream": ["dinsfire", "jbe_multi", "jbe2", "archeos", "martian", "oldedgar", "warrior", "thijs"],
    "qf.scare.scream": ["roar", "yude2", "gab1"],
    "qf.scare.scream_far": ["street_d", "street_c"],
    "qf.scare.underwater": ["drown_a", "drown_b", "drowning"],
    "qf.scare.jumpscreech": ["fm4", "tonsil"],
}
FIT_EVENT = {"death": "qf.scare.death_scream", "scream": "qf.scare.scream", "far": "qf.scare.scream_far",
             "underwater": "qf.scare.underwater", "jump": "qf.scare.jumpscreech"}


# ---------------------------------------------------------------- fetch
def curl(u):
    return subprocess.run(["curl", "-sL", "-m", "90", "-A", "Mozilla/5.0", u], capture_output=True, check=True).stdout


def page_facts(sid):
    """Licence, title, author, downloads, rating from the sound's own page. Refuses anything but CC0 / CC BY."""
    h = curl(f"https://freesound.org/s/{sid}/").decode("utf8", "replace")
    lic = sorted(set(re.findall(r"creativecommons\.org/(licenses/[a-z-]+/[0-9.]+|publicdomain/zero/1\.0)", h)))
    if len(lic) != 1 or lic[0] not in LICENCES: raise SystemExit(f"{sid}: licence {lic} is not CC0 / CC BY, refusing")
    t = re.search(r"<title>Freesound - (.*) by ([^<]+?)</title>", h, re.S)
    link = re.search(r'href="(/people/([^"/]+)/sounds/%s/)"' % sid, h)
    dl = re.search(r'data-sound-id="%s".*?data-num-downloads="(\d+)"' % sid, h, re.S)
    nr = re.search(r"Overall rating \((\d+) ratings?\)", h)
    rt = re.search(r'aria-label="Average rating of ([0-9.]+)"', h)
    d = re.search(r'id="soundDescriptionSection">(.*?)</div>', h, re.S)
    hq = re.search(r'https://cdn\.freesound\.org/previews/[^"]*-hq\.mp3', h)
    info = {}
    for k in ("Type", "Samplerate", "Bit depth", "Channels"):
        m = re.search(r">\s*%s\s*</[^>]+>\s*<[^>]+>\s*([^<]+)<" % re.escape(k), h)
        if m: info[k] = m.group(1).strip()
    return {"id": sid, "title": html.unescape(t.group(1).strip()) if t else sid,
            "author": link.group(2) if link else (t.group(2).strip() if t else "?"),
            "url": "https://freesound.org" + link.group(1) if link else f"https://freesound.org/s/{sid}/",
            "licence": LICENCES[lic[0]][0], "licence_url": LICENCES[lic[0]][1],
            "downloads": int(dl.group(1)) if dl else 0, "rating": float(rt.group(1)) if rt else None,
            "n_ratings": int(nr.group(1)) if nr else 0,
            "desc": html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d.group(1)))).strip()[:400] if d else "",
            "info": info, "preview": hq.group(0).replace("-hq.mp3", "-hq.ogg") if hq else None}


def fetch():
    meta = {}
    for sid in sorted({v[0] for v in TAKES.values()}, key=int):
        m = page_facts(sid); meta[sid] = m
        d = os.path.join(DL, "fs" + sid); f = os.path.join(d, "p.ogg")
        if not os.path.exists(f):
            os.makedirs(d, exist_ok=False)   # a new, empty directory per download (untrusted data)
            open(f, "wb").write(curl(m["preview"]))
        print(sid, m["licence"], m["downloads"], m["rating"], m["n_ratings"], m["title"][:50], flush=True)
    json.dump(meta, open(META, "w"), indent=1, ensure_ascii=False)


def rank(m):
    n, r = m["n_ratings"], m["rating"] or 0.0
    return (r * n + 3.8 * 5) / (n + 5) + 0.15 * math.log10(m["downloads"] + 1)


# ---------------------------------------------------------------- the take: trim, fade, level
def decode(sid, rate=SR):
    """The preview as float (no int16 step, so a preview that decodes above 0 dBFS is not clipped here)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(DL, "fs" + sid, "p.ogg"),
                          "-af", "aresample=resampler=soxr:precision=28", "-ar", str(rate), "-ac", "1", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def ramp(y, a, r):
    y = y.copy(); A, R = int(a * SR), min(int(r * SR), len(y))
    if A: y[:A] *= np.sin(np.linspace(0, np.pi / 2, A)) ** 2
    if R: y[-R:] *= np.cos(np.linspace(0, np.pi / 2, R)) ** 2
    return y


def true_peak(y): return np.max(np.abs(resample_poly(y, 4, 1))) + 1e-12


def loudest(y, win=0.4):
    n = int(win * SR); c = np.concatenate([[0], np.cumsum(y ** 2)])
    if len(y) <= n: return math.sqrt(c[-1] / max(1, len(y)))
    return math.sqrt(np.max(c[n:] - c[:-n]) / n)


def take(key):
    sid, a, b, fit, _ = TAKES[key]
    y = decode(sid)
    y = y[max(0, int((a - 0.02) * SR)):min(len(y), int((b + 0.05) * SR))]
    cap = CAP[fit]
    if len(y) > cap * SR: y = ramp(y[:int(cap * SR)], 0.005, 0.5)
    else: y = ramp(y, 0.005, 0.04)
    g = min(10 ** (-12 / 20) / (loudest(y) + 1e-12), 10 ** (-1 / 20) / true_peak(y))
    return y * g


def encoder():
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return ["-c:a", "aac_at", "-aac_at_mode", "cvbr", "-b:a", "192k"] if " aac_at " in enc else ["-c:a", "aac", "-b:a", "192k"]


ENC = None


def encode(y, path):
    global ENC
    ENC = ENC or encoder()
    os.makedirs(TMP, exist_ok=True)
    wav = os.path.join(TMP, "enc.wav")
    for _ in range(4):
        wavfile.write(wav, SR, y.astype(np.float32))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ac", "1", "-ar", str(SR), *ENC, "-movflags", "+faststart", path], check=True)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-"], capture_output=True).stdout
        pk = 20 * math.log10(np.max(np.abs(np.frombuffer(raw, np.float32))) + 1e-12)
        if pk <= -0.8: break
        y = y * 10 ** ((-1.0 - pk) / 20)
    os.remove(wav)
    return pk


# ---------------------------------------------------------------- build: the site's files
def save(event, keys):
    files = []
    old = json.load(open(os.path.join(SFX, "manifest.json")))["events"].get(event, {"files": []})["files"]
    for i, k in enumerate(keys):
        rel = "qf/" + event[3:].replace(".", "_") + f"{i + 1}.m4a"
        pk = encode(take(k), os.path.join(SFX, rel))
        print(f"  {rel:34} {k:11} peak {pk:+.1f} dBFS", flush=True)
        files.append(rel)
    for f in old:   # variants of an earlier build that this one no longer has
        if f not in files and os.path.exists(os.path.join(SFX, f)): os.remove(os.path.join(SFX, f))
    mp = os.path.join(SFX, "manifest.json"); m = json.load(open(mp))
    m["events"][event] = {"files": files, "volume": 1, "pitch": 1, "bus": "voice"}
    json.dump({"events": dict(sorted(m["events"].items()))}, open(mp, "w"), indent=1)


def merge_sources(meta):
    """sources.json and README.md: the Freesound recordings the five events use now, with their licences."""
    used = {}
    for ev, keys in DEFAULTS.items():
        for k in keys: used.setdefault(TAKES[k][0], set()).add(ev)
    sp = os.path.join(SFX, "sources.json"); s = json.load(open(sp))
    s["sources"] = [x for x in s["sources"] if not x["id"].startswith("fs")]
    for sid in sorted(used, key=int):
        m = meta[sid]
        s["sources"].append({"id": "fs" + sid, "title": m["title"], "url": m["url"], "author": m["author"],
                             "licence": m["licence"], "licence_url": m["licence_url"], "files": [f"{sid} (HQ preview)"],
                             "used_for": "the recorded voice, trimmed, faded and levelled only"})
    for ev, keys in DEFAULTS.items(): s["events"][ev] = ["fs" + sid for sid in dict.fromkeys(TAKES[k][0] for k in keys)]
    s["note"] = ("Round 8: the screams (qf.scare.death_scream, scream, scream_far, underwater, jumpscreech) are single real "
                 "recordings of a man, from Freesound.org, CC0 1.0 or CC BY 3.0/4.0 (licence checked on each sound page; "
                 "the CC BY authors are credited here, in README.md and on site/lib/sfx/credits.html). They are trimmed, "
                 "faded and levelled, nothing else, and play on qfaudio's 'voice' bus. The other pack sources are CC0 1.0 "
                 "from OpenGameArt.org. Nothing is NC, nothing is from a game. Synthesised layers are our own. "
                 "qf.mood.far_* are the bank's Mojang mob sounds reprocessed: flagged \"mojang\": true in manifest.json "
                 "and dropped by build_sfx.py --own-only.")
    json.dump(s, open(sp, "w"), indent=1, ensure_ascii=False)
    rp = os.path.join(SFX, "README.md"); t = open(rp).read()
    t = t.split("\n## Freesound")[0].rstrip("\n") + "\n"
    t += ("\n## Freesound recordings (round 8 screams; one real voice per file)\n\n"
          "| Sound | Author | Licence | Events |\n|---|---|---|---|\n")
    for sid in sorted(used, key=int):
        m = meta[sid]; ev = ", ".join(sorted(e.split(".")[-1] for e in used[sid]))
        t += f"| [{m['title']}]({m['url']}) | {m['author']} | [{m['licence']}]({m['licence_url']}) | {ev} |\n"
    t += ("\nBuilt by `tools/music/scream_pack3.py` from the Freesound HQ previews: trim, fade and level only (no pitch, "
          "EQ or reverb), 48 kHz, 192 kbps AAC. The owner chooses them on the audition page the script writes.\n")
    open(rp, "w").write(t)
    credits(meta, used)


def credits(meta, used):
    rows = "".join(
        f'<tr><td><a href="{html.escape(meta[s]["url"])}">{html.escape(meta[s]["title"])}</a></td><td>{html.escape(meta[s]["author"])}</td>'
        f'<td><a href="{meta[s]["licence_url"]}">{meta[s]["licence"]}</a></td><td>{", ".join(sorted(e.split(".")[-1] for e in used[s]))}</td></tr>\n'
        for s in sorted(used, key=int))
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sound credits</title>
<style>
:root{{--bg:#0f0e0d;--ink:#e9e4dc;--muted:#9a9187;--rule:#2c2824;--link:#e0a96d}}
@media (prefers-color-scheme:light){{:root{{--bg:#f6f3ee;--ink:#1d1a17;--muted:#6b635b;--rule:#ddd5ca;--link:#9a5a17}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:880px;margin:0 auto;padding:40px 16px 64px}}
h1{{font-size:22px;margin:0 0 6px}} p{{color:var(--muted);margin:0 0 22px}}
table{{width:100%;border-collapse:collapse;font-size:14px}} td,th{{text-align:left;padding:8px 10px 8px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{color:var(--muted);font-weight:500}} a{{color:var(--link)}}
.wrap{{overflow-x:auto}}
</style></head><body><main>
<h1>Sound credits</h1>
<p>The screams on the Graves page are real recordings from <a href="https://freesound.org">Freesound</a>, used under the
licences below; they are trimmed, faded and levelled, nothing else. The other sounds are our own or CC0 (see
<a href="https://github.com/MarionWhite/quest-forge/blob/main/site/lib/sfx/README.md">the sound bank's README</a>).</p>
<div class="wrap"><table><thead><tr><th>Recording</th><th>Author</th><th>Licence</th><th>Used for</th></tr></thead>
<tbody>
{rows}</tbody></table></div>
</main></body></html>
"""
    open(os.path.join(SFX, "credits.html"), "w").write(page)


def build():
    meta = json.load(open(META))
    for ev, keys in DEFAULTS.items():
        print("building", ev, flush=True); save(ev, keys)
    merge_sources(meta)


# ---------------------------------------------------------------- the audition page
def audition(out):
    meta = json.load(open(META))
    for d in ("raw", "game", "whole"): os.makedirs(os.path.join(out, d), exist_ok=True)
    default_of = {k: ev for ev, ks in DEFAULTS.items() for k in ks}
    order = sorted(TAKES, key=lambda k: -rank(meta[TAKES[k][0]]))
    rows = []
    for n, k in enumerate(order, 1):
        sid, a, b, fit, note = TAKES[k]; m = meta[sid]
        raw = decode(sid, 44100)   # the preview's own rate; no gain, a 3 ms ramp at each cut so the cut does not click
        r = raw[max(0, int((a - 0.02) * 44100)):int((b + 0.05) * 44100)].copy()
        k3 = int(0.003 * 44100); r[:k3] *= np.linspace(0, 1, k3); r[-k3:] *= np.linspace(1, 0, k3)
        wavfile.write(os.path.join(out, "raw", f"{n:02d}.wav"), 44100, r.astype(np.float32))
        g = take(k)
        encode(g, os.path.join(out, "game", f"{n:02d}.m4a"))
        whole = os.path.join(out, "whole", f"fs{sid}.ogg")
        if not os.path.exists(whole): shutil.copyfile(os.path.join(DL, "fs" + sid, "p.ogg"), whole)
        raw_peak = 20 * math.log10(np.max(np.abs(r)) + 1e-12)
        crest = 20 * math.log10(true_peak(g) / (loudest(g) + 1e-12))
        flags = []   # facts about the file, not a verdict on the scream
        if raw_peak > 1.0: flags.append("the preview peaks %+.1f dBFS: it may be clipped at the source" % raw_peak)
        if crest < 8.0: flags.append("its peaks sit only %.1f dB over its loudest moment: compressed or limited when recorded" % crest)
        if m["info"].get("Type", "").lower().startswith("mp3"): flags.append("uploaded as an MP3")
        rows.append(dict(n=n, key=k, sid=sid, a=a, b=b, fit=fit, note=note, title=m["title"], author=m["author"], url=m["url"],
                         licence=m["licence"], downloads=m["downloads"], rating=m["rating"], n_ratings=m["n_ratings"],
                         rank=round(rank(m), 2), raw_peak=round(raw_peak, 1), crest=round(crest, 1), flags=flags,
                         len=round(len(g) / SR, 1), default=default_of.get(k)))
        print(n, k, flush=True)
    json.dump(rows, open(os.path.join(out, "candidates.json"), "w"), indent=1, ensure_ascii=False)
    open(os.path.join(out, "index.html"), "w").write(page_html(rows))
    print("wrote", os.path.join(out, "index.html"))


def page_html(rows):
    fitname = {"death": "death scream", "scream": "scream", "far": "scream far", "underwater": "underwater", "jump": "jump screech"}
    tr = []
    for r in rows:
        dflt = f'<span class="def">in the game now: {r["default"].split(".")[-1]}</span>' if r["default"] else ""
        rating = f'{r["rating"]:.1f}' if r["rating"] else "none"
        tr.append(f"""<tr data-n="{r['n']}"{' class="isdef"' if r['default'] else ''}>
<td class="num">{r['n']}</td>
<td class="play"><button data-src="raw/{r['n']:02d}.wav" title="the take as recorded">Raw</button><button data-src="game/{r['n']:02d}.m4a" class="g" title="the file the site plays, as the game plays it">In game</button></td>
<td><a href="{html.escape(r['url'])}">{html.escape(r['title'])}</a> <span class="by">by {html.escape(r['author'])}</span>{dflt}
<div class="note">{html.escape(r['note'])}. Take {r['a']:.2f} to {r['b']:.2f} s of the <a href="whole/fs{r['sid']}.ogg">whole recording</a>; {r['len']} s in the game.</div>{''.join('<div class="flag">' + html.escape(f) + '</div>' for f in r['flags'])}</td>
<td class="facts">{r['downloads']:,} downloads<br><span class="sep"> · </span>{rating} stars ({r['n_ratings']})<br><span class="sep"> · </span>{r['licence']}</td>
<td class="fit">{fitname[r['fit']]}<select aria-label="use number {r['n']} for"><option value="">—</option><option>death</option><option>scream</option><option>far</option><option>underwater</option><option>jump</option><option>no</option></select></td>
</tr>""")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scream audition</title>
<style>
:root{{--bg:#111010;--card:#1a1817;--ink:#ece6dd;--muted:#9b9288;--rule:#2d2925;--accent:#e2a15f;--def:#7fc29b;--warn:#d98b7a}}
@media (prefers-color-scheme:light){{:root{{--bg:#f7f4ef;--card:#fff;--ink:#1d1a17;--muted:#6b635b;--rule:#e2dbd1;--accent:#a65d14;--def:#25744a;--warn:#a8402b}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:32px 16px 120px}}
h1{{font-size:24px;margin:0 0 8px}} .lede{{color:var(--muted);max-width:760px;margin:0 0 20px}}
table{{width:100%;border-collapse:collapse}} td{{padding:10px 8px;border-bottom:1px solid var(--rule);vertical-align:top}}
td.num{{font:600 20px/1 ui-monospace,Menlo,monospace;color:var(--accent);width:2.2em;padding-top:14px}}
td.play{{white-space:nowrap;width:1%}} button{{font:inherit;font-size:13px;padding:7px 12px;margin:0 6px 6px 0;border-radius:6px;border:1px solid var(--rule);background:var(--card);color:var(--ink);cursor:pointer}}
button.g{{border-color:var(--accent)}} button.on{{background:var(--accent);color:#111;border-color:var(--accent)}}
a{{color:var(--accent)}} .by{{color:var(--muted)}} .note{{color:var(--muted);font-size:13px;margin-top:3px}}
.def{{display:inline-block;margin-left:8px;font-size:12px;padding:1px 7px;border-radius:10px;border:1px solid var(--def);color:var(--def)}}
tr.isdef td.num{{color:var(--def)}} .sep{{display:none}} .flag{{font-size:12px;color:var(--warn);margin-top:2px}} .flag::before{{content:"! "}}
td.facts{{font-size:13px;color:var(--muted);white-space:nowrap;width:1%}} td.fit{{font-size:13px;color:var(--muted);width:1%;white-space:nowrap}}
select{{display:block;margin-top:6px;font:inherit;font-size:13px;background:var(--card);color:var(--ink);border:1px solid var(--rule);border-radius:6px;padding:4px}}
#picks{{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--rule);padding:10px 16px;font:13px/1.4 ui-monospace,Menlo,monospace}}
#picks .wrap{{max-width:1100px;margin:0 auto;display:flex;gap:12px;align-items:center;flex-wrap:wrap}} #picktext{{flex:1;min-width:240px}}
@media (max-width:700px){{table,tbody,tr,td{{display:block;width:auto!important}} td.facts,td.fit{{white-space:normal}} td.facts br{{display:none}} .sep{{display:inline}} tr{{border-bottom:1px solid var(--rule);padding:8px 0}} td{{border:0;padding:4px 0}}}}
</style></head><body><main>
<h1>Scream audition</h1>
<p class="lede">{len(rows)} real recordings of a man screaming, CC0 or CC BY, best-rated first: Freesound's average rating
(weighted by how many people rated it) plus its downloads. <b>Raw</b> is the take exactly as recorded, at its own level.
<b>In game</b> is the file the site plays, played the way the game now plays it: centred, no pitch change, no filter, no
reverb; only trimmed, faded and levelled. The green numbers are in the game now: the best-ranked of each use, at most
two per performer, none flagged as maybe clipped. The "!" lines are measured facts about the file, not a verdict on the
scream. Reply with numbers, for example "death 3, 5, 9; jump 31", or set the menus and copy the line at the bottom.</p>
<table><tbody>
{''.join(tr)}
</tbody></table></main>
<div id="picks"><div class="wrap"><span id="picktext">No picks yet.</span><button id="copy">Copy</button></div></div>
<script>
const a = new Audio(); let cur = null;
document.querySelectorAll('td.play button').forEach((b) => b.addEventListener('click', () => {{
  if (cur === b && !a.paused) {{ a.pause(); b.classList.remove('on'); cur = null; return; }}
  if (cur) cur.classList.remove('on');
  a.src = b.dataset.src; a.currentTime = 0; a.play(); b.classList.add('on'); cur = b;
}}));
a.addEventListener('ended', () => {{ if (cur) cur.classList.remove('on'); cur = null; }});
function picks() {{
  const by = {{}};
  document.querySelectorAll('tr[data-n]').forEach((tr) => {{ const v = tr.querySelector('select').value; if (v) (by[v] = by[v] || []).push(tr.dataset.n); }});
  const t = Object.entries(by).map(([k, v]) => k + ' ' + v.join(', ')).join('; ');
  document.getElementById('picktext').textContent = t || 'No picks yet.';
  return t;
}}
document.querySelectorAll('select').forEach((s) => s.addEventListener('change', picks));
document.getElementById('copy').addEventListener('click', () => {{ const t = picks(); if (navigator.clipboard) navigator.clipboard.writeText(t).catch(() => {{}}); }});
</script>
</body></html>
"""


def main():
    a = sys.argv[1:]
    if a and a[0] == "fetch": fetch(); return
    if a and a[0] == "audition": audition(a[1] if len(a) > 1 else os.path.join(TMP, "audition")); return
    if a and a[0] == "build": build(); return
    print(__doc__)


if __name__ == "__main__":
    main()
