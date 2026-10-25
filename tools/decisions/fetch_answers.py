"""Read the owner's Decisions page answers back from GitHub issues.

The Decisions page (site/decisions/) shows one card per open call. It sends the
owner's answers the way the Shader Lab does: through the relay as "round" 9000+N
for sheet N (the deployed relay then titles the issue "Shader Lab feedback: round
900N"; a relay with the sheet patch titles it "Decisions: sheet N"), or as a
prefilled GitHub issue "Decisions: sheet N". Either way the body ends in a ```json
block {round, scenes: {cardId: {choice, rating, note}}, overall}, which this script
reads with fetch_feedback.py's own parser.

    py -3.10 -I tools/decisions/fetch_answers.py [--sheet N] [--print] [--out DIR] [--issues-json FILE]

For every sheet with answers it writes docs/decisions/answers/sNNN.json:

    {sheet, id, title, responses: [raw, oldest first], resolved: {cardId: {...}}, open: [cardIds]}

`resolved` holds the owner's latest word per card (a later issue overrides an
earlier one card by card), with the option's label, whether it followed our
recommendation, and the note. It prints a Markdown summary per group, and marks
the sheet `answered` in site/decisions/sheets/index.json.

The file is idempotent: rebuilt from the issues every run, written only when its
content changes. --issues-json reads a saved issues list instead of the API (tests).
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHEETS = REPO / "site" / "decisions" / "sheets"
OUT = REPO / "docs" / "decisions" / "answers"
SHEET_BASE = 9000
LATER = "later"
TITLE = re.compile(r"^\s*(?:Decisions:\s*sheet\s+(\d+)|Shader Lab feedback:\s*round\s+(9\d{3}))\b", re.I)


def _load_ff():
    p = REPO / "tools" / "shaders" / "review" / "fetch_feedback.py"
    spec = importlib.util.spec_from_file_location("fetch_feedback", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ff = _load_ff()


def load_sheet(n):
    p = SHEETS / f"s{n:03d}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def cards(sheet):
    """[(card, group)] in page order."""
    out = []
    for g in sheet.get("groups") or []:
        for it in g.get("items") or []:
            out.append((it, g))
    return out


def collect(items, sheet_filter=None, comments=None):
    """{sheet n: [response, ...]} from GitHub issue dicts, plus a list of skipped issues."""
    by_sheet, skipped = {}, []
    for it in items:
        if "pull_request" in it:
            continue
        m = TITLE.match(it.get("title") or "")
        if not m:
            continue
        title_n = int(m.group(1)) if m.group(1) else int(m.group(2)) - SHEET_BASE
        where = "body"
        ans = ff.parse(it.get("body"))
        if ans is None and it.get("comments") and comments:
            for c in comments(it):
                ans = ff.parse(c.get("body")) or ans
            where = "comment"
        if ans is None:
            skipped.append(f"#{it['number']} (no answers block)")
            continue
        rnd = ans.get("round")
        n = rnd - SHEET_BASE if isinstance(rnd, int) and rnd >= SHEET_BASE else title_n
        if sheet_filter is not None and n != sheet_filter:
            continue
        by_sheet.setdefault(n, []).append({
            "issue": it["number"], "url": it["html_url"], "user": (it.get("user") or {}).get("login"),
            "state": it.get("state"), "created_at": it.get("created_at"), "updated_at": it.get("updated_at"),
            "from": where, "answers": ans})
    return by_sheet, skipped


def resolve(sheet, responses):
    """The owner's latest word per card: {id: {...}}, and the ids still open."""
    by_id = {it["id"]: (it, g) for it, g in cards(sheet)} if sheet else {}
    resolved = {}
    for r in sorted(responses, key=lambda r: (r.get("created_at") or "", r["issue"])):
        for cid, a in (r["answers"].get("scenes") or {}).items():
            if not isinstance(a, dict):
                continue
            choice, note = a.get("choice"), (a.get("note") or "").strip()
            if not choice and not note:
                continue
            it, g = by_id.get(cid, (None, None))
            opt = next((o for o in (it or {}).get("options", []) if o.get("key") == choice), None) if it else None
            rec = (it or {}).get("recommend")
            resolved[cid] = {
                "name": (it or {}).get("name", cid), "group": (g or {}).get("id"),
                "choice": choice, "label": (opt or {}).get("label") if opt else (LATER if choice == LATER else choice),
                "recommend": rec,
                "followed": (choice == rec) if (choice and rec and choice != LATER) else None,
                "note": note, "issue": r["issue"], "at": r.get("created_at"),
            }
    open_ids = [it["id"] for it, _ in cards(sheet) if not resolved.get(it["id"], {}).get("choice") or
                resolved[it["id"]]["choice"] == LATER] if sheet else []
    return resolved, open_ids


def markdown(sheet, resolved, open_ids, responses):
    n = sheet["n"] if sheet else "?"
    lines = [f"## Decisions sheet {n}: {sheet.get('title', '') if sheet else ''}".rstrip(), ""]
    decided = sum(1 for v in resolved.values() if v["choice"] and v["choice"] != LATER)
    total = len(cards(sheet)) if sheet else len(resolved)
    followed = sum(1 for v in resolved.values() if v["followed"] is True)
    against = [v for v in resolved.values() if v["followed"] is False]
    lines.append(f"{decided} of {total} decided, {len(open_ids)} open or later, {followed} followed the recommendation, "
                 f"{len(against)} did not. Sources: " + ", ".join(f"#{r['issue']}" for r in responses) + ".")
    lines.append("")
    groups = sheet.get("groups") or [] if sheet else [{"id": None, "name": "Answers", "items": [{"id": k} for k in resolved]}]
    for g in groups:
        rows = [(it, resolved.get(it["id"])) for it in g.get("items") or []]
        if not any(v for _, v in rows):
            continue
        lines += [f"### {g['name']}", "", "| Card | Answer | Recommended | Note |", "|---|---|---|---|"]
        for it, v in rows:
            if not v:
                lines.append(f"| {it['id']} {it.get('name', '')} | *open* | {it.get('recommend', '')} | |")
                continue
            ans = f"**{v['choice']}** {v['label'] or ''}".strip() if v["choice"] else "*note only*"
            flag = "" if v["followed"] in (True, None) else " (differs)"
            lines.append(f"| {it['id']} {it.get('name', '')} | {ans}{flag} | {v['recommend'] or ''} | {v['note'].replace('|', '/').replace(chr(10), ' ')} |")
        lines.append("")
    overall = [r["answers"].get("overall", "").strip() for r in responses if (r["answers"].get("overall") or "").strip()]
    if overall:
        lines += ["### Overall", ""] + [f"> {o}" for o in overall] + [""]
    if open_ids:
        lines += ["### Still open", "", ", ".join(open_ids), ""]
    return "\n".join(lines)


def mark_answered(ns):
    p = SHEETS / "index.json"
    if not p.exists():
        return
    idx = json.loads(p.read_text(encoding="utf-8"))
    changed = False
    for s in idx.get("sheets", []):
        if s.get("n") in ns and not s.get("answered"):
            s["answered"] = True
            changed = True
    if changed:
        p.write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"marked answered in {p.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", type=int, help="only this sheet")
    ap.add_argument("--print", action="store_true", help="also print the raw latest answers")
    ap.add_argument("--out", help="write the answers files here instead of docs/decisions/answers (tests)")
    ap.add_argument("--issues-json", help="read this saved GitHub issues list instead of the API (tests)")
    ap.add_argument("--no-mark", action="store_true", help="don't touch sheets/index.json")
    a = ap.parse_args()

    if a.issues_json:
        items = json.loads(Path(a.issues_json).read_text(encoding="utf-8"))
        comments = None
    else:
        items = list(ff.issues())
        comments = lambda it: ff.get(it["comments_url"] + "?per_page=100")[0]
    by_sheet, skipped = collect(items, a.sheet, comments)

    out_dir = Path(a.out) if a.out else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, resp in sorted(by_sheet.items()):
        resp.sort(key=lambda r: (r.get("created_at") or "", r["issue"]))
        sheet = load_sheet(n)
        resolved, open_ids = resolve(sheet, resp)
        doc = {"sheet": n, "id": f"s{n:03d}", "title": (sheet or {}).get("title"),
               "note": "Built by tools/decisions/fetch_answers.py from GitHub issues; the latest response is last and wins card by card.",
               "responses": resp, "resolved": resolved, "open": open_ids}
        path = out_dir / f"s{n:03d}.json"
        text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != text:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"s{n:03d}: {len(resp)} response(s) -> {path}")
        else:
            print(f"s{n:03d}: {len(resp)} response(s), unchanged")
        if sheet is None:
            print(f"s{n:03d}: no sheet file {SHEETS / f's{n:03d}.json'}; answers kept raw")
        print()
        print(markdown(sheet or {"n": n, "title": "", "groups": []}, resolved, open_ids, resp))
        if a.print:
            print(json.dumps(resp[-1]["answers"], indent=1, ensure_ascii=False))
    if not by_sheet:
        print("No Decisions answers yet.")
    elif not a.no_mark and not a.out:
        mark_answered(set(by_sheet))
    for s in skipped:
        print("skipped " + s)


if __name__ == "__main__":
    main()
