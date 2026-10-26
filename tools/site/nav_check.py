#!/usr/bin/env python3
"""Proof that nobody walks through a prop on the Lucky Block page.

    nav_check.py "lucky/?idle=60000" "lucky/?scene=mob_horde&at=14000" ...

Each page is loaded like dump_frames.py does (?dump=1, headless Chrome). site/lucky/nav.js counts every
sampled position of Steve and of the ground mobs against the occupancy map and publishes
{samples, violations, first, by} as <html data-nav-stats>. Prints one line per page; exit 1 if any
page has a violation or no samples.
"""
import html, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump_frames as D


def run(exe, port, path, budget=60000, timeout=240):
    sep = "&" if "?" in path else "?"
    url = f"http://127.0.0.1:{port}/{path.lstrip('/')}{sep}dump=1"
    prof = tempfile.mkdtemp(prefix="navcheck-")
    cmd = [exe, "--headless=new", "--no-first-run", f"--user-data-dir={prof}", "--run-all-compositor-stages-before-draw",
           f"--virtual-time-budget={budget}", "--window-size=800,500", "--dump-dom", url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return None
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'data-nav-stats="([^"]*)"', out)
    return json.loads(html.unescape(m.group(1))) if m else None


def main():
    exe = D.browser()
    httpd, port = D.serve()
    bad = 0
    for p in sys.argv[1:]:
        st = run(exe, port, p)
        if not st or not st["samples"] or st["violations"]:
            bad += 1
        print(p, "->", json.dumps(st))
    httpd.shutdown()
    sys.exit(1 if bad else 0)


main()
