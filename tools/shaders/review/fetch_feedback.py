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

Pasted answers are found too: a json block on one line (a phone paste folds the
newlines into spaces), a block inside a json string such as `overall` (feedback
copied into the overall box and sent again), or a bare {"round": .., "scenes": ..}
object anywhere in the body. The candidate with the most answered scenes wins;
on a tie, the last one.

Since round 3 the Lab sends a compressed line instead of the json block:

    qf-answers-v2:<base64url of raw-deflated {r, s: {id: [choice, rating, note]}, o}>

and, when even that is too long for one issue URL, splits it over issues titled
"Shader Lab feedback: round N (part k/m)", each holding
`qf-answers-v2:<id>:<k>/<m>:<chunk>`. The chunks of one submission (same round and
id) are joined in part order and decoded together; a submission missing a part is
reported as skipped until the rest arrives. Both forms map back to the same
{round, scenes: {id: {choice, rating, note}}, overall} answers as the json block.

Reference images: the relay commits images the owner attached to
docs/design/shaders/feedback/attachments/rNNN/ and lists them in the issue as

    <!-- qf-attachments-v1: [{"scene", "name", "path", "url"}, ...] -->

Each response then gets "attachments": [{scene, name, path, url}] (scene is the
scene id, or "_overall" for the overall comment). An image that isn't in the
working tree yet (no git pull since) is downloaded to its path, unless
--no-images. Only paths under that folder with a .jpg/.png/.webp name are
accepted, and only from this repo's raw URLs, since anyone can open an issue.
"""
import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "docs" / "design" / "shaders" / "feedback"
API = "https://api.github.com/repos/MarionWhite/quest-forge/issues?state=all&per_page=50"
UA = {"User-Agent": "quest-forge-shader-lab", "Accept": "application/vnd.github+json"}
TITLE = re.compile(r"^\s*Shader Lab feedback\b", re.I)
TITLE_N = re.compile(r"round\s+(\d+)", re.I)
ATT_LIST = re.compile(r"<!--\s*qf-attachments-v1:\s*(\[.*?\])\s*-->", re.S)
ATT_PATH = re.compile(r"^docs/design/shaders/feedback/attachments/r\d{3,4}/[A-Za-z0-9][A-Za-z0-9_-]{0,120}\.(?:jpg|png|webp)$")
RAW = "https://raw.githubusercontent.com/MarionWhite/quest-forge/main/"
MAX_IMG = 3 * 1024 * 1024
MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")


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


V2 = re.compile(r"qf-answers-v2:(?:([a-z0-9]+):(\d+)/(\d+):)?([A-Za-z0-9_-]+)")


def decode_v2(b64):
    """base64url -> raw deflate -> short json -> {round, scenes, overall}, or None if it doesn't decode."""
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4)), -15)
        d = json.loads(raw.decode("utf-8"))
    except (ValueError, zlib.error, UnicodeDecodeError):
        return None
    if not (isinstance(d, dict) and isinstance(d.get("s"), dict)):
        return None
    scenes = {}
    for sid, v in d["s"].items():
        v = list(v) + [None, None, ""][len(v):] if isinstance(v, list) else [None, None, ""]
        scenes[sid] = {"choice": v[0], "rating": v[1], "note": v[2] if v[2] is not None else ""}
    return {"round": d.get("r"), "scenes": scenes, "overall": d.get("o") or ""}


def v2_blocks(text):
    """(single answers or None, [(id, k, m, chunk), ...]) for the qf-answers-v2 lines in `text`."""
    single, parts = None, []
    for m in V2.finditer(text or ""):
        if m.group(1):
            parts.append((m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)))
        else:
            single = decode_v2(m.group(4)) or single
    return single, parts


MARK = re.compile(r"```json|\{\s*\"round\"")
DEC = json.JSONDecoder()


def _candidates(text, depth=0):
    """Every Lab-answers dict in `text`, outermost first, including ones nested in strings."""
    if not text or depth > 4:
        return
    seen = set()
    for m in MARK.finditer(text):
        start = text.find("{", m.start())
        if start < 0 or start in seen:
            continue
        seen.add(start)
        try:
            d, _ = DEC.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if not (isinstance(d, dict) and isinstance(d.get("scenes"), dict)):
            continue
        yield d
        for v in d.values():
            if isinstance(v, str) and "{" in v:
                yield from _candidates(v, depth + 1)


def parse(text):
    """The Lab answers in `text`: a qf-answers-v2 line if there is one, else the json block
    with the most answered scenes (the last on a tie), or None."""
    single, _ = v2_blocks(text)
    if single is not None:
        return single
    found = list(_candidates(text))
    best = None
    for d in found:
        if best is None or len(d["scenes"]) >= len(best["scenes"]):
            best = d
    # Answers pasted into another submission's `overall`: keep what the owner wrote before
    # the paste (the wrapper has fewer answered scenes and a block inside its overall).
    for w in found:
        outer = w.get("overall")
        if best is None or w is best or len(w["scenes"]) >= len(best["scenes"]) or not isinstance(outer, str):
            continue
        m = MARK.search(outer)
        if m:
            pre = outer[:m.start()].split("Shader Lab feedback for round")[0].strip()
            if pre:
                best = dict(best, preamble=pre)
                break
    return best


def attachments(text):
    """The images a relay issue lists: [{scene, name, path, url}], keeping only safe paths."""
    out, seen = [], set()
    for m in ATT_LIST.finditer(text or ""):
        try:
            lst = json.loads(m.group(1))
        except ValueError:
            continue
        for a in lst if isinstance(lst, list) else []:
            if not isinstance(a, dict):
                continue
            path, scene = a.get("path"), a.get("scene")
            if not (isinstance(path, str) and ATT_PATH.match(path) and isinstance(scene, str)) or path in seen:
                continue
            seen.add(path)
            url = a.get("url") if isinstance(a.get("url"), str) and a["url"].startswith(RAW) else RAW + path
            out.append({"scene": scene, "name": str(a.get("name") or "")[:80], "path": path, "url": url})
    return out


def download(att):
    """Fetch one listed image into the working tree if it isn't there. -> 'have' | 'got' | error text."""
    dest = REPO / att["path"]
    if dest.exists():
        return "have"
    req = urllib.request.Request(RAW + att["path"], headers={"User-Agent": UA["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read(MAX_IMG + 1)
    except (urllib.error.URLError, OSError) as e:
        return f"download failed ({e})"
    if len(data) > MAX_IMG or not data.startswith(MAGIC) or (data.startswith(b"RIFF") and data[8:12] != b"WEBP"):
        return "not an image, skipped"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return "got"


def collect(items, round_filter=None, comments=None):
    """Group the Lab answers in GitHub issue dicts by round: ({n: [response, ...]}, [skipped, ...]).
    `comments(issue)` returns an issue's comment dicts (used when the body has no answers)."""
    by_round, skipped, partial = {}, [], {}

    def meta(it, where):
        return {"issue": it["number"], "url": it["html_url"], "user": (it.get("user") or {}).get("login"),
                "state": it.get("state"), "created_at": it.get("created_at"), "updated_at": it.get("updated_at"),
                "from": where}

    def add(n, resp, it):
        if round_filter is None or n == round_filter:
            atts = attachments(it.get("body"))
            if atts:
                resp["attachments"] = atts
            by_round.setdefault(n, []).append(resp)

    for it in items:
        if "pull_request" in it or not TITLE.match(it.get("title") or ""):
            continue
        m = TITLE_N.search(it["title"])
        title_n = int(m.group(1)) if m else None
        where = "body"
        parts = v2_blocks(it.get("body"))[1]
        ans = parse(it.get("body"))
        if ans is None and not parts and it.get("comments") and comments:
            for c in comments(it):
                ans = parse(c.get("body")) or ans
                parts += v2_blocks(c.get("body"))[1]
            where = "comment"
        if ans is None and parts:
            for pid, k, total, chunk in parts:
                partial.setdefault((title_n, pid), {"total": total, "chunks": {}})["chunks"][k] = (chunk, meta(it, where))
            continue
        if ans is None:
            skipped.append(f"#{it['number']} (no answers block)")
            continue
        n = ans.get("round")
        if not isinstance(n, int):
            n = title_n
        if n is None:
            skipped.append(f"#{it['number']} (no round number)")
            continue
        add(n, dict(meta(it, where), answers=ans), it)

    for (title_n, pid), p in sorted(partial.items(), key=lambda kv: (kv[0][0] or -1, kv[0][1])):
        have = p["chunks"]
        missing = [k for k in range(1, p["total"] + 1) if k not in have]
        nums = ", ".join(f"#{have[k][1]['issue']}" for k in sorted(have))
        if missing:
            skipped.append(f"{nums} (round {title_n} submission {pid}: waiting for part(s) "
                           f"{', '.join(map(str, missing))} of {p['total']})")
            continue
        ans = decode_v2("".join(have[k][0] for k in range(1, p["total"] + 1)))
        if ans is None:
            skipped.append(f"{nums} (round {title_n} submission {pid}: parts don't decode)")
            continue
        n = ans.get("round") if isinstance(ans.get("round"), int) else title_n
        first = have[1][1]
        add(n, dict(first, parts=[have[k][1]["issue"] for k in range(1, p["total"] + 1)], answers=ans), {})
    return by_round, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--round", type=int, help="only this round")
    ap.add_argument("--print", action="store_true", help="also print the answers")
    ap.add_argument("--no-images", action="store_true", help="record attached images but don't download missing ones")
    a = ap.parse_args()

    by_round, skipped = collect(issues(), a.round,
                                lambda it: get(it["comments_url"] + "?per_page=100")[0])

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
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"r{n:03d}: {len(resp)} response(s) -> {path.relative_to(REPO)}")
        else:
            print(f"r{n:03d}: {len(resp)} response(s), unchanged")
        atts = [x for r in resp for x in r.get("attachments", [])]
        if atts:
            res = {} if a.no_images else {x["path"]: download(x) for x in atts}
            got = sum(v == "got" for v in res.values())
            print(f"r{n:03d}: {len(atts)} attached image(s)" + ("" if a.no_images else f", {got} downloaded"))
            for pth, v in res.items():
                if v not in ("have", "got"):
                    print(f"  {pth}: {v}")
        if a.print:
            print(json.dumps(resp[-1]["answers"], indent=1, ensure_ascii=False))
    if not by_round:
        print("No Shader Lab feedback issues yet.")
    for s in skipped:
        print("skipped " + s)


if __name__ == "__main__":
    main()
