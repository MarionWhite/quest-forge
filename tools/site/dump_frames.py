#!/usr/bin/env python3
"""Deterministic frames of the site's WebGL pages (Lucky Block, the Krypt), from a terminal.

    dump_frames.py OUTDIR "lucky/?scene=anvil_trap&at=17000" "graves/?demo&grave=3" ...
    dump_frames.py OUTDIR --list shots.txt          # one "name<TAB>path" or "path" per line
    dump_frames.py OUTDIR --list shots.txt --sheet  # also OUTDIR/sheet.png, every frame labelled

Why not a screenshot: headless --screenshot races the WebGL compositor and often returns the
first idle frame however long the page has been running. Instead each page takes ?dump=1:
after its seek hook (?scene/&at/?force on lucky, ?at/?grave on graves) it waits for every
texture, renders once, and appends
    <script type="application/json" id="dumpshot">{"png": "data:image/png;base64,...", ...}</script>
This script loads the page with --dump-dom, decodes that PNG to OUTDIR/<name>.png and writes
the rest of the JSON (the page's state at that moment) to OUTDIR/<name>.json. A page that never
reaches the hook is reported as NO DUMP.

The site is served from site/ with home/ at the root, like pages.yml, by a threaded server on a
free port. Chrome (macOS, Linux) or Edge (Windows) runs headless with no window. At most
--jobs browsers run at once (default 3: more starve the machine and the pages boot badly).
"""
import argparse, base64, concurrent.futures as cf, html, http.server, json, os, re, shutil, socket
import subprocess, sys, tempfile, threading, urllib.parse

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "site")
BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser",
]


class SiteHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parts = [p for p in urllib.parse.urlparse(path).path.split("/") if p and p not in (".", "..")]
        top = parts[0] if parts else ""
        rel = parts if (top and top != "home" and os.path.isdir(os.path.join(SITE, top))) else ["home"] + parts
        full = os.path.join(SITE, *rel)
        return os.path.join(full, "index.html") if os.path.isdir(full) else full

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), SiteHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def browser():
    for b in BROWSERS:
        if os.path.isabs(b) and os.path.exists(b):
            return b
        if not os.path.isabs(b) and shutil.which(b):
            return shutil.which(b)
    sys.exit("no Chrome or Edge found")


def slug(path):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path).strip("_")[:80] or "page"


def dump_one(exe, port, name, path, outdir, size, budget, timeout):
    sep = "&" if "?" in path else "?"
    url = path if path.startswith("http") else f"http://127.0.0.1:{port}/{path.lstrip('/')}"
    url = f"{url}{sep}dump=1"
    prof = tempfile.mkdtemp(prefix="dumpframe-")
    cmd = [exe, "--headless=new", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={prof}",
           "--run-all-compositor-stages-before-draw", f"--virtual-time-budget={budget}",
           f"--window-size={size}", "--dump-dom", url]
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **kw).stdout
    except subprocess.TimeoutExpired:
        return name, "TIMEOUT"
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'<script type="application/json" id="dumpshot">(.*?)</script>', out, re.S)
    if not m:
        return name, "NO DUMP (the page never reached its ?dump hook)"
    d = json.loads(html.unescape(m.group(1)))
    png = d.pop("png", "")
    if png.startswith("data:image/png;base64,"):
        with open(os.path.join(outdir, name + ".png"), "wb") as f:
            f.write(base64.b64decode(png.split(",", 1)[1]))
    with open(os.path.join(outdir, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    return name, json.dumps(d)[:220]


def sheet(exe, outdir, names, cols=3):
    names = [n for n in names if os.path.exists(os.path.join(outdir, n + ".png"))]
    if not names:
        return
    cells = "".join(f"<figure><img src='{n}.png'><figcaption>{html.escape(n)}</figcaption></figure>" for n in names)
    page = os.path.join(outdir, "sheet.html")
    with open(page, "w", encoding="utf-8") as f:
        f.write("<!doctype html><style>body{margin:0;background:#111;display:grid;grid-template-columns:repeat(%d,1fr);gap:4px;width:1920px}"
                "figure{margin:0;position:relative}img{width:100%%;display:block}figcaption{position:absolute;top:4px;left:6px;"
                "color:#fff;font:bold 20px sans-serif;text-shadow:0 1px 3px #000}</style>%s" % (cols, cells))
    rows = (len(names) + cols - 1) // cols
    prof = tempfile.mkdtemp(prefix="dumpsheet-")
    subprocess.run([exe, "--headless=new", "--no-first-run", "--hide-scrollbars", f"--user-data-dir={prof}",
                    f"--window-size=1920,{rows * 360 + 20}", f"--screenshot={os.path.join(outdir, 'sheet.png')}",
                    "file://" + os.path.abspath(page)], capture_output=True, timeout=120)
    shutil.rmtree(prof, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("paths", nargs="*", help="site paths with their query, e.g. 'lucky/?scene=boss&at=14000'")
    ap.add_argument("--list", help="a file of 'name<TAB>path' or 'path' lines")
    ap.add_argument("--size", default="1366,900")
    ap.add_argument("--budget", type=int, default=20000, help="virtual time budget, ms")
    ap.add_argument("--timeout", type=int, default=120, help="seconds before a browser is killed")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--sheet", action="store_true", help="write OUTDIR/sheet.png as well")
    a = ap.parse_args()
    jobs = [(slug(p), p) for p in a.paths]
    if a.list:
        for line in open(a.list, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, _, path = line.partition("\t") if "\t" in line else (slug(line), "", line)
            jobs.append((name, path))
    if not jobs:
        ap.error("nothing to dump")
    os.makedirs(a.outdir, exist_ok=True)
    exe = browser()
    httpd, port = serve()
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futs = [pool.submit(dump_one, exe, port, n, p, a.outdir, a.size, a.budget, a.timeout) for n, p in jobs]
        for f in cf.as_completed(futs):
            n, msg = f.result()
            print(f"{n}\t{msg}", flush=True)
    httpd.shutdown()
    if a.sheet:
        sheet(exe, a.outdir, [n for n, _ in jobs])
        print("sheet:", os.path.join(a.outdir, "sheet.png"))


if __name__ == "__main__":
    main()
