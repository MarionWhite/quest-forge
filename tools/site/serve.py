"""Preview the site locally with the same layout as the deployed GitHub Pages site.

home/ is the root and every other folder is served under its own name, as pages.yml lays it
out, so links like ../ and ../favicon.png work. Nothing is cached, so a reload shows edits.

    python3 -I tools/site/serve.py            http://127.0.0.1:8000/
    python3 -I tools/site/serve.py 8080       another port
    python3 -I tools/site/serve.py --lan      also reachable from a phone on the same Wi-Fi

Stop it with Ctrl+C. It serves only the site/ folder, which is public anyway.
"""
import argparse
import http.server
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_frames import SiteHandler  # noqa: E402  (same path mapping the frame dumps use)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", type=int, default=8000)
    ap.add_argument("--lan", action="store_true", help="listen on all interfaces, not just this machine")
    a = ap.parse_args()
    host = "0.0.0.0" if a.lan else "127.0.0.1"
    try:
        httpd = http.server.ThreadingHTTPServer((host, a.port), SiteHandler)
    except OSError as e:
        sys.exit(f"Port {a.port} is busy ({e.strerror}). Try another: python3 -I tools/site/serve.py {a.port + 1}")
    base = f"http://127.0.0.1:{a.port}"
    print(f"Serving site/ at {base}/  (Ctrl+C stops it)")
    for p in ("", "lucky/", "graves/?demo", "first-night/"):
        print(f"  {base}/{p}")
    if a.lan and lan_ip():
        print(f"From a phone on the same Wi-Fi: http://{lan_ip()}:{a.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
