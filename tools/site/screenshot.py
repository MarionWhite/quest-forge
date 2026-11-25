#!/usr/bin/env python3
"""Screenshot a page of the static site with headless Edge, from a terminal, with
no window.

    screenshot.py online/            out.png            # serves site/ locally, shoots /online/
    screenshot.py "online/?demo"     out.png --size 1200x1600
    screenshot.py https://example/   out.png            # any URL, no local server

The site's pages fetch their own JSON (config.json, a feed), which a file:// URL
cannot do, so a relative path is served from the repo's site/ folder by a
throwaway http.server on a free port, with home/ at the root like the Pages
workflow. Edge is started with CREATE_NO_WINDOW (0x08000000) and
--headless=new, so nothing appears on the owner's screen; it exits by itself
once the screenshot is written. The PNG is the page at --size (default
1100x900 CSS pixels, device scale 1; Edge will not go narrower than about 500).
"""
import argparse, http.server, os, socket, subprocess, sys, threading, time, urllib.parse

EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "site")


class SiteHandler(http.server.SimpleHTTPRequestHandler):
    """site/home/ at /, every other site folder under its own name (pages.yml's layout)."""
    def translate_path(self, path):
        path = urllib.parse.urlparse(path).path
        parts = [p for p in path.split("/") if p and p not in (".", "..")]
        top = parts[0] if parts else ""
        if top and os.path.isdir(os.path.join(SITE, top)) and top != "home":
            rel = parts
        else:
            rel = ["home"] + parts
        full = os.path.join(SITE, *rel)
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        return full

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), SiteHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", help="a path under site/ (served locally) or a full URL")
    ap.add_argument("out", help="the PNG to write")
    ap.add_argument("--size", default="1100x900", help="viewport WxH in CSS pixels")
    ap.add_argument("--wait-ms", type=int, default=2500, help="time for fetches and fonts before the shot")
    ap.add_argument("--edge", help="path to msedge.exe")
    ap.add_argument("--dark", action="store_true", help="prefer the dark colour scheme")
    args = ap.parse_args()
    edge = args.edge or next((e for e in EDGE if os.path.exists(e)), None)
    if not edge:
        sys.exit("msedge.exe not found; pass --edge")
    httpd = None
    if "://" in args.page:
        url = args.page
    else:
        httpd, port = serve()
        url = "http://127.0.0.1:%d/%s" % (port, args.page.lstrip("/"))
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    w, h = args.size.lower().split("x")
    # Edge's automatic page darkening (WebContentsForceDark) is on in headless
    # runs here: it painted the light homepage black with blue links. Off, the
    # page's own prefers-color-scheme rules decide; --dark asks for the dark ones.
    cmd = [edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", "--mute-audio", "--force-device-scale-factor=1",
           "--disable-features=WebContentsForceDark,ForcedColors",
           # Headless Edge here reports forced colours (Windows high contrast: black
           # pages, #8080FF links) unless told otherwise.
           "--blink-settings=forcedColors=0,preferredColorScheme=%d" % (1 if args.dark else 0),
           "--window-size=%s,%s" % (w, h), "--virtual-time-budget=%d" % args.wait_ms,
           "--user-data-dir=%s" % os.path.join(os.environ.get("TEMP", "."), "qf-shot-profile"),
           "--screenshot=%s" % out, url]
    flags = 0x08000000 if os.name == "nt" else 0      # CREATE_NO_WINDOW
    t0 = time.time()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags, timeout=120)
    if httpd:
        httpd.shutdown()
    if not os.path.exists(out):
        print(res.stdout.decode("utf-8", "replace")[-2000:])
        sys.exit("no screenshot written (edge exit %d)" % res.returncode)
    print("%s (%d bytes, %.1f s) <- %s" % (out, os.path.getsize(out), time.time() - t0, url))


if __name__ == "__main__":
    main()
