"""Read the owner's Shader Lab answers back from GitHub issues.

The Lab (site/shaders/) sends feedback as a GitHub issue titled
"Shader Lab feedback: round N" whose body ends in a fenced ```json block:
{round, scenes: {id: {choice, rating, note}}, overall}. This script reads those
issues from the public API, unauthenticated and read-only, and writes one file
per round:

    docs/design/shaders/feedback/rNNN.json

    py -3.10 -I tools/shaders/review/fetch_feedback.py [--round N] [--print]

It is idempotent: each file is rebuilt from the issues every run and written
only when its content changes, so re-running never duplicates an answer. If an
issue's body has no json block (a long answer pasted into a comment instead),
its comments are searched too. The unauthenticated API allows 60 requests an
hour, which is plenty.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "docs" / "design" / "shaders" / "feedback"
API = "https://api.github.com/repos/MarionWhite/quest-forge/issues?state=all&per_page=50"
UA = {"User-Agent": "quest-forge-shader-lab", "Accept": "application/vnd.github+json"}
TITLE = re.compile(r"^\s*Shader Lab feedback\b", re.I)
TITLE_N = re.compile(r"round\s+(\d+)", re.I)
BLOCK = re.compile(r"```json\s*\n(.*?)\n\s*```", re.S)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link", "") or "")
            return json.load(r), (nxt.group(1) if nxt else None)
    except urllib.error.HTTPError as e:
        sys.exit(f"fetch_feedback: {url}: HTTP {e.code} {e.read()[:300]!r}")


def issues():
    url, pages = API, 0
    while url and pages < 10:
        batch, url = get(url)
        pages += 1
        yield from batch


def parse(text):
    """The last json block in `text` that looks like Lab answers, or None."""
    for m in reversed(BLOCK.findall(text or "")):
        try:
            d = json.loads(m)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and isinstance(d.get("scenes"), dict):
            return d
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--round", type=int, help="only this round")
    ap.add_argument("--print", action="store_true", help="also print the answers")
    a = ap.parse_args()

    by_round, skipped = {}, []
    for it in issues():
        if "pull_request" in it or not TITLE.match(it.get("title") or ""):
            continue
        ans = parse(it.get("body"))
        where = "body"
        if ans is None and it.get("comments"):
            comments, _ = get(it["comments_url"] + "?per_page=100")
            for c in comments:
                ans = parse(c.get("body")) or ans
            where = "comment"
        if ans is None:
            skipped.append(f"#{it['number']} (no answers block)")
            continue
        n = ans.get("round")
        if not isinstance(n, int):
            m = TITLE_N.search(it["title"])
            n = int(m.group(1)) if m else None
        if n is None:
            skipped.append(f"#{it['number']} (no round number)")
            continue
        if a.round is not None and n != a.round:
            continue
        by_round.setdefault(n, []).append({
            "issue": it["number"], "url": it["html_url"], "user": (it.get("user") or {}).get("login"),
            "state": it.get("state"), "created_at": it.get("created_at"), "updated_at": it.get("updated_at"),
            "from": where, "answers": ans,
        })

    OUT.mkdir(parents=True, exist_ok=True)
    for n, resp in sorted(by_round.items()):
        resp.sort(key=lambda r: r["issue"])
        doc = {"round": n, "id": f"r{n:03d}",
               "note": "Built by tools/shaders/review/fetch_feedback.py from GitHub issues; the latest response is last.",
               "responses": resp}
        path = OUT / f"r{n:03d}.json"
        text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != text:
            path.write_text(text, encoding="utf-8")
            print(f"r{n:03d}: {len(resp)} response(s) -> {path.relative_to(REPO)}")
        else:
            print(f"r{n:03d}: {len(resp)} response(s), unchanged")
        if a.print:
            print(json.dumps(resp[-1]["answers"], indent=1, ensure_ascii=False))
    if not by_round:
        print("No Shader Lab feedback issues yet.")
    for s in skipped:
        print("skipped " + s)


if __name__ == "__main__":
    main()
