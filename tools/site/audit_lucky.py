#!/usr/bin/env python3
"""Audit every Lucky Block drop and structure with the page's own resolvers.

    python3 -I tools/site/audit_lucky.py              # table of problems; exit 1 on any FALLBACK or mismatch
    python3 -I tools/site/audit_lucky.py --all        # also list every resolved id
    python3 -I tools/site/audit_lucky.py --json OUT   # keep the full JSON

It loads site/lucky/audit.html in headless Chrome (served like dump_frames.py does). The page asks
blockdefs.js, blocks.js, the mob library and the reel which picture each block, item, mob and tile
resolves to, and puts the answer in <script id="dumpshot">. Equipment ids are resolved here
against items.json (the page's armour renderer is the mobs task). Exit 1 when any id is FALLBACK, any
reel tile does not match its drop's main action, or any text keeps a raw code.
"""
import argparse, html, json, os, re, subprocess, sys, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dump_frames as df  # noqa: E402
import build_lucky as bl  # noqa: E402


# Ids the Lucky Block config spells differently from what the mod registers: in 1.7.10 the registry
# lookup is case sensitive, so the game finds no such item and the drop gives nothing for it.
# Checked against OreSpawnMain (registers OreSpawn_SeaMonsterScale and OreSpawn_TRexTooth, and no royal sword).
CONFIG_TYPOS = {
    "OreSpawn:OreSpawn_SeamonsterScale": "the mod registers OreSpawn_SeaMonsterScale",
    "OreSpawn:OreSpawn_TRexRooth": "the mod registers OreSpawn_TRexTooth",
    "OreSpawn:OreSpawn_RoyalSword": "OreSpawn registers no Royal Sword",
}


def run(timeout, budget):
    exe = df.browser()
    httpd, port = df.serve()
    prof = tempfile.mkdtemp(prefix="auditlucky-")
    cmd = [exe, "--headless=new", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={prof}",
           "--run-all-compositor-stages-before-draw", f"--virtual-time-budget={budget}",
           "--window-size=1000,800", "--dump-dom", f"http://127.0.0.1:{port}/lucky/audit.html"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout).stdout
    finally:
        shutil.rmtree(prof, ignore_errors=True)
        httpd.shutdown()
    m = re.search(r'<script type="application/json" id="dumpshot">(.*?)</script>', out, re.S)
    if not m:
        sys.exit("NO AUDIT (the page never finished; try --budget 60000)")
    return json.loads(html.unescape(m.group(1)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--budget", type=int, default=60000)
    a = ap.parse_args()
    res = run(a.timeout, a.budget)
    if "error" in res:
        sys.exit("audit page error: " + res["error"])
    idx = bl.ItemIndex(bl.ITEMS)
    bad = 0
    equip_seen = {}
    notes = []
    for d in res["drops"]:
        keep = []
        for i in d["issues"]:
            m = re.match(r"item (\S+) FALLBACK", i)
            if m and m.group(1) in CONFIG_TYPOS:
                notes.append("drop %d %s: %s is a config typo (%s); nothing drops for it" % (d["index"], d["title"], m.group(1), CONFIG_TYPOS[m.group(1)]))
            else:
                keep.append(i)
        d["issues"] = keep
    for d in res["drops"]:
        for e in d["equipment"]:
            if e not in equip_seen:
                nsn = e if ":" in e else "minecraft:" + e
                icon, how = idx.icon_for(nsn, None)
                equip_seen[e] = icon is not None
            if not equip_seen[e] and e in CONFIG_TYPOS:
                notes.append("drop %d %s: equipment %s is a config typo (%s)" % (d["index"], d["title"], e, CONFIG_TYPOS[e]))
            elif not equip_seen[e]:
                d["issues"].append("equipment " + e + " FALLBACK (no icon in items.json)")
    problems = []
    for d in res["drops"]:
        for i in d["issues"]:
            problems.append(("drop %d %s [%s]" % (d["index"], d["title"], d["scene"]), i))
    for k, s in res["structures"].items():
        for i in s["issues"]:
            problems.append(("structure " + k, i))
    if a.all:
        print("== block ids")
        seen = {}
        for d in res["drops"]:
            for b in d["blocks"]:
                seen[(b["id"], b["meta"])] = b
        for s in res["structures"].values():
            for b in s["blocks"]:
                seen[(b["id"], b["meta"])] = b
        for (i, m), b in sorted(seen.items()):
            print("  %-48s meta %-2s %-9s %-8s %s" % (i, m, b["status"], b.get("kind", ""), ", ".join(sorted(set((b.get("faces") or {}).values())))[:90]))
        print("== entities")
        ents = {}
        for d in res["drops"]:
            for e in d["entities"]:
                ents[e["id"]] = e
        for i, e in sorted(ents.items()):
            print("  %-34s -> %-24s %s" % (i, e["mobKey"], e["status"]))
        print("== equipment")
        for e, ok in sorted(equip_seen.items()):
            print("  %-48s %s" % (e, "ok" if ok else "FALLBACK"))
    for n in sorted(set(notes)):
        print("note:", n)
    print("%d drops, %d structures, %d problems" % (len(res["drops"]), len(res["structures"]), len(problems)))
    last = None
    for who, i in problems:
        if who != last:
            print(who)
            last = who
        print("   -", i)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
