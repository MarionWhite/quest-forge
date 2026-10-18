"""Post a Shader Lab round to the project's GitHub Pages site.

The Lab is the static page at site/shaders/ (live at
https://marionwhite.github.io/quest-forge/shaders/). A round is a JSON file plus
its images; this script builds both from a spec, updates the round list,
commits only those paths and pushes, which deploys the site.

    py -3.10 -I tools/shaders/review/publish_round.py SPEC.json [--dry-run] [--no-push]
    py -3.10 -I tools/shaders/review/publish_round.py --round 0 --calibration C:/qfb/shaderdev/calibration/manifest.json

SPEC.json has the round schema, with local image paths (absolute, or relative to
the spec file):

    {"n": 12, "title": "...", "intro": "...",
     "scenes": [{"id": "golden", "name": "...", "question": "...", "notePrompt": "...",
                 "options": [{"key": "A", "label": "...", "img": "C:/qfb/.../a.png",
                              "critic": "...", "ms": 4.1,
                              "ref": {"img": "...", "credit": "<Artist>, <licence>, via Wikimedia Commons",
                                      "source": "https://commons.wikimedia.org/wiki/File:..."}}]}]}

`n` defaults to the next free number. Images become 1920 px JPEG q90 (references
1600 px) in site/shaders/rounds/rNNN/. Posting a round closes the previous open
round, except r000, which stays open until docs/design/shaders/feedback/r000.json
exists (fetch_feedback.py writes it).

--round N re-publishes an existing round from its own JSON (use it with
--calibration to add the calibration renders to r000 later). --calibration takes a
manifest [{question, key, label, scene, path, ms}] and attaches each render to the
option `key` of the scene whose id is `question`, adding the option if it is new.

Only our own renders, and openly licensed references with a credit line, belong
here: the site is public.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[3]
ROUNDS = REPO / "site" / "shaders" / "rounds"
FEEDBACK = REPO / "docs" / "design" / "shaders" / "feedback"
RENDER_W, REF_W = 1920, 1600
TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


def die(msg):
    sys.exit("publish_round: " + msg)


def resolve(p, base):
    p = Path(p)
    return p if p.is_absolute() else (base / p)


def put_image(src, dst, width, quality, dry):
    """Copy src to dst as a JPEG at most `width` wide. A JPEG that is already small
    enough is copied byte for byte, so re-publishing never re-compresses it."""
    if not src.is_file():
        die(f"image not found: {src}")
    if src.resolve() == dst.resolve():
        return "in place"
    with Image.open(src) as im:
        small_jpeg = im.format == "JPEG" and im.width <= width
        size = im.size
        if dry:
            return f"{size[0]}x{size[1]} -> {dst.name}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if small_jpeg:
            dst.write_bytes(src.read_bytes())
        else:
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    return f"{size[0]}x{size[1]} -> {dst.name}"


def merge_calibration(spec, manifest_path):
    entries = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    base = Path(manifest_path).parent
    scenes = {s["id"]: s for s in spec["scenes"]}
    for e in entries:
        s = scenes.get(e.get("question"))
        if s is None:
            print(f"  calibration: no scene '{e.get('question')}' in the round, skipped {e.get('path')}")
            continue
        opt = next((o for o in s["options"] if o["key"] == e["key"]), None)
        if opt is None:
            opt = {"key": e["key"], "label": e.get("label") or e["key"]}
            s["options"].append(opt)
            s["options"].sort(key=lambda o: o["key"])
        opt["img"] = str(resolve(e["path"], base))
        if e.get("ms") is not None:
            opt["ms"] = e["ms"]
        if e.get("scene") and not opt.get("critic"):
            opt["critic"] = f"Calibration render: {e['scene']}."
    return spec


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if check and r.returncode:
        die(f"git {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="round spec JSON with local image paths")
    ap.add_argument("--round", type=int, help="re-publish this existing round from its own JSON")
    ap.add_argument("--calibration", help="calibration manifest to merge into the round")
    ap.add_argument("--dry-run", action="store_true", help="print what would happen; write nothing")
    ap.add_argument("--no-push", action="store_true", help="commit but do not push")
    ap.add_argument("--no-git", action="store_true", help="write files only; no commit, no push")
    ap.add_argument("--keep-open", action="store_true", help="do not close earlier open rounds")
    a = ap.parse_args()
    if bool(a.spec) == (a.round is not None):
        die("give a SPEC.json or --round N (not both)")

    index_path = ROUNDS / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"rounds": []}

    if a.round is not None:
        src = ROUNDS / f"r{a.round:03d}.json"
        if not src.exists():
            die(f"{src} does not exist")
        spec, base = json.loads(src.read_text(encoding="utf-8")), ROUNDS
    else:
        spec, base = json.loads(Path(a.spec).read_text(encoding="utf-8")), Path(a.spec).resolve().parent
    if a.calibration:
        spec = merge_calibration(spec, a.calibration)

    n = spec.get("n")
    if n is None:
        n = max([r["n"] for r in index["rounds"]] + [-1]) + 1
    rid = spec.get("id") or f"r{n:03d}"
    if not re.fullmatch(r"r\d{3}", rid):
        die(f"bad round id {rid!r}")
    out_dir = ROUNDS / rid
    print(f"Round {n} ({rid}): {spec.get('title', '')}")

    scenes = []
    for s in spec["scenes"]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", s["id"]):
            die(f"scene id {s['id']!r} must be lower-case letters, digits and dashes")
        opts = []
        for o in s.get("options", []):
            o = dict(o)
            if o.get("img"):
                dst = out_dir / f"{s['id']}-{o['key']}.jpg"
                print(f"  {s['id']}/{o['key']}: {put_image(resolve(o['img'], base), dst, RENDER_W, 90, a.dry_run)}")
                o["img"] = f"{rid}/{dst.name}"
            if o.get("ref"):
                ref = dict(o["ref"])
                if not ref.get("credit") or not ref.get("source"):
                    die(f"{s['id']}/{o['key']}: a reference needs `credit` and `source` (licence terms)")
                dst = out_dir / f"ref-{s['id']}-{o['key']}.jpg"
                print(f"  {s['id']}/{o['key']} ref: {put_image(resolve(ref['img'], base), dst, REF_W, 88, a.dry_run)}")
                ref["img"] = f"{rid}/{dst.name}"
                o["ref"] = ref
            opts.append(o)
        scenes.append({**s, "options": opts})

    round_doc = {
        "n": n, "id": rid,
        "title": spec.get("title", f"Round {n}"),
        "intro": spec.get("intro", ""),
        "status": spec.get("status", "open"),
        "created": spec.get("created") or datetime.date.today().isoformat(),
        "scenes": scenes,
    }
    if spec.get("credits"):
        round_doc["credits"] = spec["credits"]

    # The round list: upsert this round, close the earlier open ones.
    touched = [ROUNDS / f"{rid}.json"]
    entries = {r["id"]: r for r in index["rounds"]}
    entries[rid] = {"n": n, "id": rid, "title": round_doc["title"], "status": round_doc["status"],
                    "created": round_doc["created"], "scenes": len(scenes)}
    closed = []
    if round_doc["status"] == "open" and not a.keep_open:
        for e in entries.values():
            if e["id"] == rid or e["status"] != "open" or e["n"] > n:
                continue
            if e["id"] == "r000" and not (FEEDBACK / "r000.json").exists():
                print("  r000 stays open: no feedback yet")
                continue
            e["status"] = "closed"
            closed.append(e["id"])
    for e in entries.values():
        e["feedback"] = (FEEDBACK / f"{e['id']}.json").exists()
    index = {"rounds": sorted(entries.values(), key=lambda e: e["n"])}

    if a.dry_run:
        print(f"  would close: {closed or 'nothing'}")
        print(json.dumps(index, indent=1))
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    (ROUNDS / f"{rid}.json").write_text(json.dumps(round_doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for cid in closed:
        p = ROUNDS / f"{cid}.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            d["status"] = "closed"
            p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            touched.append(p)
    index_path.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    touched += [index_path, out_dir]
    print(f"  wrote {rid}.json, index.json; closed {closed or 'nothing'}")
    if a.no_git:
        return

    # Commit only these paths: other sessions share the working tree.
    paths = [str(p.relative_to(REPO)).replace(os.sep, "/") for p in touched]
    git("add", "--", *paths)
    if not git("diff", "--cached", "--quiet", "--", *paths, check=False).returncode:
        print("  nothing changed; no commit")
    else:
        msg = f"Shader Lab: post round {n} ({round_doc['title']})\n\n{TRAILER}\n"
        git("commit", "--only", "-m", msg, "--", *paths)
        print("  committed " + git("rev-parse", "--short", "HEAD").stdout.strip())
    if a.no_push:
        return
    if git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != "main":
        die("not on main; commit made, push it yourself")
    git("fetch", "origin", "main")
    if git("merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode:
        r = git("merge", "--no-edit", "origin/main", check=False)
        if r.returncode:
            git("merge", "--abort", check=False)
            die("origin/main has commits that do not merge cleanly; merge by hand, then push")
    git("push", "origin", "HEAD:main")
    print("  pushed; Pages deploys in a minute or two: https://marionwhite.github.io/quest-forge/shaders/")


if __name__ == "__main__":
    main()
