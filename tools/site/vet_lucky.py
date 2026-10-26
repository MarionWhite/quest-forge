#!/usr/bin/env python3
"""Vet every Lucky Block outcome: one deterministic frame per drop, a table of what is wrong.

    python3 -I tools/site/vet_lucky.py OUTDIR                 all drops, sheets per scene key
    python3 -I tools/site/vet_lucky.py OUTDIR --only 153,162  just those drop indexes
    python3 -I tools/site/vet_lucky.py OUTDIR --keys boss,pet only those scene keys
    python3 -I tools/site/vet_lucky.py OUTDIR --no-sheets     table only

For each drop it loads  lucky/?force=<i>&at=<ms>&sfxlog&dump=1  with tools/site/dump_frames.py's
server and browser, at a moment inside the scene (AT below, seconds after the scene starts), and
reads two things from the page: the dump JSON (phase, scene key) and the scene's own report
(site/lucky/fx.js finishReport, written into <script id="qf-scene-report"> in ?dump mode, also
under `sceneReport` in the dump JSON when the page puts it there): counts of mobs, items, blocks
and particles, the sounds it played, and whether the shot's subjects are inside the camera frustum
and how tall they read on screen.

A drop is BROKEN when: the page never dumped, the scene threw (errors in the report, or the
generic crash guard ran), nothing was made at all, no subject is inside the frame, or the main
subject is off-screen. It is WEAK when the main subject is under 5% of the frame height or over
150%, or it played no sound. Coverage: every scene key in lucky.json must have an implementation
in site/lucky/*.js, and the generic scene must not be assigned to any drop.

Outputs in OUTDIR: vet.txt (the table), vet.json, frames/<i>.png, sheets/<key>.png (one per scene
key, at most 12 frames, each labelled with the drop index and title).
"""
import argparse, base64, concurrent.futures as cf, html, importlib.util, json, os, re, shutil
import subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LUCKY = os.path.join(ROOT, "site", "lucky")
T_SCENE = 9.6  # app.js: T_WIN + 0.9

# seconds into the scene at which the frame is taken: late enough that the subject is in, early
# enough that the scene has not ended (scene durations are 4 to 12 s)
AT = {
    "item_drop": 2.4, "item_set": 3.0, "fireworks_loot": 3.0, "chest": 3.2, "message": 3.0, "effect": 2.6,
    "falling_column": 3.4, "placed_blocks": 3.4, "explosion": 2.0, "tnt_rain": 4.0, "expbottle_rain": 3.6,
    "xp_burst": 3.6, "bedrock_problem": 2.4, "dud": 2.4, "lightning": 5.0, "jens_hole": 3.6,
    "mob_spawn": 3.8, "mob_horde": 4.6, "mob_tower": 3.8, "pet": 4.2, "villager_trader": 3.6,
    "boss": 6.2, "apocalypse": 6.5, "anvil_trap": 6.0, "lava_trap": 4.4, "water_trap": 4.4,
    "pit_trap": 3.6, "fort": 4.0, "temple": 4.6, "lucky_choice": 3.2, "trapped_chest": 3.6,
    "troll_ore": 3.4, "wishing_well": 8.4, "sky_temple": 9.0, "ground_temple": 8.4,
}


def load_dump_frames():
    spec = importlib.util.spec_from_file_location("dump_frames", os.path.join(HERE, "dump_frames.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fetch(df, exe, port, i, ms, outdir, size, budget, timeout):
    path = f"lucky/?force={i}&at={ms}&sfxlog&dump=1"
    url = f"http://127.0.0.1:{port}/{path}"
    prof = tempfile.mkdtemp(prefix="vetlucky-")
    cmd = [exe, "--headless=new", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={prof}",
           "--run-all-compositor-stages-before-draw", f"--virtual-time-budget={budget}",
           f"--window-size={size}", "--dump-dom", url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return {"index": i, "status": "TIMEOUT"}
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'<script type="application/json" id="dumpshot">(.*?)</script>', out, re.S)
    if not m:
        return {"index": i, "status": "NO DUMP"}
    d = json.loads(html.unescape(m.group(1)))
    png = d.pop("png", "")
    if png.startswith("data:image/png;base64,"):
        with open(os.path.join(outdir, "frames", f"{i}.png"), "wb") as f:
            f.write(base64.b64decode(png.split(",", 1)[1]))
    rep = d.get("sceneReport")
    if rep is None:
        r = re.search(r'<script type="application/json" id="qf-scene-report">(.*?)</script>', out, re.S)
        if r:
            try:
                rep = json.loads(html.unescape(r.group(1)))
            except ValueError:
                rep = None
    d["index"] = i
    d["report"] = rep
    d["status"] = "ok"
    return d


def judge(drop, d):
    """Returns (broken reasons, weak reasons)."""
    bad, weak = [], []
    if d["status"] != "ok":
        return [d["status"]], weak
    rep = d.get("report")
    if d.get("scene") != drop["scene"]:
        bad.append("scene mismatch %s" % d.get("scene"))
    if d.get("phase") not in ("scene", "result"):
        bad.append("phase " + str(d.get("phase")))
    if not rep:
        return bad + ["no scene report"], weak
    if rep.get("errors"):
        bad.append("errors: " + "; ".join(rep["errors"])[:80])
    made = rep["mobs"] + rep["items"] + rep["blocks"] + rep["particles"]
    subs = rep.get("subjects") or []
    mains = [s for s in subs if s.get("main")] or subs
    if made == 0 and drop["scene"] not in ("dud", "message", "effect", "bedrock_problem"):
        bad.append("nothing made")
    if subs and not any(s["inFrustum"] for s in subs):
        bad.append("no subject in frame")
    elif mains and not any(s["inFrustum"] for s in mains):
        bad.append("main subject off-screen")
    if mains:
        best = max(s["screenH"] for s in mains if s["inFrustum"]) if any(s["inFrustum"] for s in mains) else 0
        if best and best < 0.05:
            weak.append("tiny %.2f" % best)
        if best > 1.5:
            weak.append("huge %.2f" % best)
    if not rep.get("sfx"):
        weak.append("silent")
    return bad, weak


def coverage(doc):
    src = ""
    for f in os.listdir(LUCKY):
        if f.endswith(".js"):
            src += open(os.path.join(LUCKY, f), encoding="utf-8").read()
    have = set(re.findall(r"(?:SCENES|STRUCT|MOB_SCENES|WELL_SCENES)\.([a-z_]+)\s*=", src))
    keys = sorted({d["scene"] for d in doc["drops"]})
    missing = [k for k in keys if k not in have]
    generic = [d["index"] for d in doc["drops"] if d["scene"] == "generic"]
    return keys, missing, generic


def make_sheets(df, exe, outdir, doc, results, per_key=12):
    os.makedirs(os.path.join(outdir, "sheets"), exist_ok=True)
    by = {}
    for d in doc["drops"]:
        by.setdefault(d["scene"], []).append(d)
    paths = []
    for key, drops in sorted(by.items()):
        have = [d for d in drops if os.path.exists(os.path.join(outdir, "frames", f"{d['index']}.png"))]
        if not have:
            continue
        if len(have) > per_key:  # broken ones first, then an even spread
            bad = [d for d in have if results[d["index"]]["bad"]][:per_key // 2]
            rest = [d for d in have if d not in bad]
            step = max(1, len(rest) // (per_key - len(bad)))
            have = (bad + rest[::step])[:per_key]
        cells = "".join("<figure><img src='../frames/%d.png'><figcaption>%d %s%s</figcaption></figure>" % (
            d["index"], d["index"], html.escape(d["title"][:34]), " [BAD]" if results[d["index"]]["bad"] else "") for d in have)
        page = os.path.join(outdir, "sheets", key + ".html")
        with open(page, "w", encoding="utf-8") as f:
            f.write("<!doctype html><style>body{margin:0;background:#111;display:grid;grid-template-columns:repeat(3,636px);gap:4px;width:1920px}"
                    "figure{margin:0;position:relative}img{width:636px;height:355px;display:block}figcaption{position:absolute;top:4px;left:6px;"
                    "color:#fff;font:bold 20px sans-serif;text-shadow:0 1px 3px #000}</style>" + cells)
        rows = (len(have) + 2) // 3
        png = os.path.join(outdir, "sheets", key + ".png")
        prof = tempfile.mkdtemp(prefix="vetsheet-")
        subprocess.run([exe, "--headless=new", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={prof}",
                        f"--window-size=1920,{rows * 359 + 10}", f"--screenshot={png}", "file://" + os.path.abspath(page)],
                       capture_output=True, timeout=120)
        shutil.rmtree(prof, ignore_errors=True)
        paths.append(png)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("--only", help="comma list of drop indexes")
    ap.add_argument("--keys", help="comma list of scene keys")
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--size", default="1366,900")
    ap.add_argument("--budget", type=int, default=30000)
    ap.add_argument("--timeout", type=int, default=150)
    ap.add_argument("--at", type=float, help="override: seconds into the scene")
    a = ap.parse_args()
    doc = json.load(open(os.path.join(LUCKY, "data", "lucky.json"), encoding="utf-8"))
    keys, missing, generic = coverage(doc)
    print("scene keys in the table: %d; with no implementation: %s; drops on the generic scene: %s" % (len(keys), missing or "none", generic or "none"))
    drops = doc["drops"]
    if a.only:
        want = {int(x) for x in a.only.split(",")}
        drops = [d for d in drops if d["index"] in want]
    if a.keys:
        want = set(a.keys.split(","))
        drops = [d for d in drops if d["scene"] in want]
    os.makedirs(os.path.join(a.outdir, "frames"), exist_ok=True)
    df = load_dump_frames()
    exe = df.browser()
    httpd, port = df.serve()
    res = {}
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futs = {}
        for d in drops:
            sec = a.at if a.at is not None else AT.get(d["scene"], 3.5)
            futs[pool.submit(fetch, df, exe, port, d["index"], int((T_SCENE + sec) * 1000), a.outdir, a.size, a.budget, a.timeout)] = d
        for f in cf.as_completed(futs):
            d = futs[f]
            r = f.result()
            bad, weak = judge(d, r)
            r["bad"], r["weak"] = bad, weak
            res[d["index"]] = r
            print("%4d %-16s %-5s %s" % (d["index"], d["scene"], "BAD" if bad else ("weak" if weak else "ok"), "; ".join(bad + weak)), flush=True)
    httpd.shutdown()
    lines = ["idx  scene            verdict  mobs items blocks parts sfx  title / reasons"]
    for d in drops:
        r = res[d["index"]]
        rep = r.get("report") or {}
        lines.append("%-4d %-16s %-7s %5s %5s %6s %5s %4s  %s%s" % (
            d["index"], d["scene"], "BAD" if r["bad"] else ("weak" if r["weak"] else "ok"),
            rep.get("mobs", "-"), rep.get("items", "-"), rep.get("blocks", "-"), rep.get("particles", "-"),
            sum((rep.get("sfx") or {}).values()) if rep else "-", d["title"][:40],
            ("  <- " + "; ".join(r["bad"] + r["weak"])) if (r["bad"] or r["weak"]) else ""))
    nb = sum(1 for r in res.values() if r["bad"])
    nw = sum(1 for r in res.values() if r["weak"] and not r["bad"])
    lines.append("")
    lines.append("drops vetted %d: broken %d, weak %d, ok %d; coverage missing %s; generic %s" % (len(res), nb, nw, len(res) - nb - nw, missing or "none", generic or "none"))
    with open(os.path.join(a.outdir, "vet.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(a.outdir, "vet.json"), "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in res.items()}, f, indent=1)
    print("\n" + lines[-1])
    if not a.no_sheets:
        for p in make_sheets(df, exe, a.outdir, {"drops": drops}, res):
            print("sheet:", p)
    print("table:", os.path.join(a.outdir, "vet.txt"))
    return 1 if nb or missing or generic else 0


if __name__ == "__main__":
    sys.exit(main())
