"""Check and publish a Decisions sheet for site/decisions/.

    py -3.10 -I tools/decisions/sheet.py check  SHEET.json
    py -3.10 -I tools/decisions/sheet.py publish SHEET.json [--keep-open]

A sheet is a JSON file: {n, id, title, intro, status, created, groups: [{id, name,
blurb, source: {text, href}, items: [{id, name, question, context, links, options:
[{key, label, desc}], recommend, why, notePrompt}]}]}. Card ids and option keys
must satisfy the relay's rules (the page sends them as the Lab's scene ids and
choices): ids ^[a-z0-9][a-z0-9-]{0,63}$, keys ^[A-Za-z0-9-]{1,16}$, "later" is
reserved. `check` validates those and the sizes the relay accepts. `publish` copies
the file into site/decisions/sheets/sNNN.json, adds or updates its row in
index.json, closes any other open sheet (unless --keep-open), and prints the git
commands: the site deploys when site/** is pushed to main.
"""
import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHEETS = REPO / "site" / "decisions" / "sheets"
SID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
CHOICE = re.compile(r"^[A-Za-z0-9-]{1,16}$")
MAX_ANSWER_BYTES = 60 * 1024   # the relay's cap on the answers body
MAX_SCENES = 100


def check(sheet):
    errs, n = [], 0
    ids = set()
    if not isinstance(sheet.get("n"), int) or not 1 <= sheet["n"] <= 999:
        errs.append("n must be an integer 1-999")
    if sheet.get("id") != f"s{sheet.get('n', 0):03d}":
        errs.append(f"id must be s{sheet.get('n', 0):03d}")
    for k in ("title", "intro"):
        if not sheet.get(k):
            errs.append(f"missing {k}")
    for g in sheet.get("groups") or []:
        if not g.get("id") or not g.get("name"):
            errs.append("every group needs id and name")
        for it in g.get("items") or []:
            n += 1
            cid = it.get("id", "")
            if not SID.match(cid):
                errs.append(f"bad card id {cid!r}")
            if cid in ids:
                errs.append(f"duplicate card id {cid}")
            ids.add(cid)
            keys = [o.get("key") for o in it.get("options") or []]
            if len(keys) < 2:
                errs.append(f"{cid}: needs at least two options")
            for k in keys:
                if not isinstance(k, str) or not CHOICE.match(k) or k.lower() == "later":
                    errs.append(f"{cid}: bad option key {k!r}")
            if len(set(keys)) != len(keys):
                errs.append(f"{cid}: duplicate option keys")
            if it.get("recommend") not in keys:
                errs.append(f"{cid}: recommend must be one of {keys}")
            for k in ("name", "question"):
                if not it.get(k):
                    errs.append(f"{cid}: missing {k}")
    if n > MAX_SCENES:
        errs.append(f"{n} cards; the relay takes at most {MAX_SCENES}")
    # Worst case the owner writes 300 characters on every card: must stay under the relay's cap.
    worst = {"round": 9000 + (sheet.get("n") or 0), "scenes": {i: {"choice": "A", "rating": None, "note": "x" * 300} for i in ids}, "overall": "x" * 2000}
    size = len(json.dumps(worst).encode("utf-8"))
    if size > MAX_ANSWER_BYTES:
        errs.append(f"worst-case answers {size} bytes exceed the relay's {MAX_ANSWER_BYTES}")
    return errs, n


def publish(path, keep_open):
    sheet = json.loads(path.read_text(encoding="utf-8"))
    errs, n = check(sheet)
    if errs:
        sys.exit("not published:\n  " + "\n  ".join(errs))
    SHEETS.mkdir(parents=True, exist_ok=True)
    dest = SHEETS / f"{sheet['id']}.json"
    if path.resolve() != dest.resolve():
        shutil.copyfile(path, dest)
    idx_p = SHEETS / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {"sheets": []}
    today = datetime.date.today().isoformat()
    row = {"n": sheet["n"], "id": sheet["id"], "title": sheet["title"], "status": sheet.get("status", "open"),
           "created": sheet.get("created") or today, "items": n, "answered": False}
    rows = [r for r in idx["sheets"] if r.get("n") != sheet["n"]]
    old = next((r for r in idx["sheets"] if r.get("n") == sheet["n"]), None)
    if old:
        row["answered"] = bool(old.get("answered"))
    if not keep_open and row["status"] == "open":
        for r in rows:
            if r.get("status") == "open":
                r["status"] = "closed"
    rows.append(row)
    rows.sort(key=lambda r: r["n"])
    idx["sheets"] = rows
    idx_p.write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    rel = lambda p: p.relative_to(REPO).as_posix()
    print(f"published {rel(dest)} ({n} cards) and updated {rel(idx_p)}")
    print("then:\n  git add", rel(dest), rel(idx_p), "\n  git commit -m 'Decisions: sheet", sheet["n"], "'\n  git push")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("sheet")
    p = sub.add_parser("publish"); p.add_argument("sheet"); p.add_argument("--keep-open", action="store_true")
    a = ap.parse_args()
    path = Path(a.sheet)
    if a.cmd == "check":
        sheet = json.loads(path.read_text(encoding="utf-8"))
        errs, n = check(sheet)
        if errs:
            sys.exit(f"{n} cards, {len(errs)} problem(s):\n  " + "\n  ".join(errs))
        print(f"ok: {n} cards in {len(sheet.get('groups') or [])} groups")
    else:
        publish(path, a.keep_open)


if __name__ == "__main__":
    main()
