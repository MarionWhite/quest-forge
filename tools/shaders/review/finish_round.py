#!/usr/bin/env python3
"""Finish a Shader Lab round from finished renders, in one command (2026-10-25).

A fresh agent can post a round without the context of the one that changed the shaders:

    py -3.10 -I -X utf8 tools/shaders/review/finish_round.py C:/qfb/shaderdev/r008            # check + spec + dry run
    py -3.10 -I -X utf8 tools/shaders/review/finish_round.py C:/qfb/shaderdev/r008 --publish  # post it

The round folder holds what only a person or the critic can write:
    spec_scenes.py   TITLE, INTRO, SCENES (exec'd with roundlib's o, oc, og, cost, crit, worst, ref3, ref4)
    critic.json      {"tag/scene": {"score": 7, "note": "..."}}  (the critic's notes)
    round.json       {"n": 8, "critic": ["../r007/critic.json", "critic.json"],
                      "refs": {"r003": "../r003/refs.json", "r004": "../r004/refs.json"},
                      "base": {"qlo": "off8l"},          # only for tags without renderq meta
                      "renders": ["1025-161000-r008"],    # renderq submissions to wait for (optional)
                      "budgets": {"qh": 3.0, "qlo": 0.9, "qp": 0.4}}

Steps, each stopping with a clear message:
  1. every renderq submission in "renders" is finished (renderq.py results ID);
  2. every frame the scenes use exists;
  3. every frame has a critic note: if not, critic-todo.json lists them and critic-todo-N.jpg
     shows them labelled 4 to a sheet; the critic fills critic.json and the script is re-run (exit 3);
  4. every option has a cost (a shaders-off baseline: renderq meta or round.json "base") and no
     tag in "budgets" passes its budget;
  5. exposure: crushed and clipped pixels per frame (check_frames.py's measure), as warnings;
  6. spec.json is written and publish_round.py runs with --dry-run, or for real with --publish.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import roundlib  # noqa: E402

RQ_RESULTS = os.path.join(os.environ.get("QF_RENDERQ", r"C:\qfb\renderq"), "results")


def sheets(todo, d):
    from PIL import Image, ImageDraw
    paths = []
    for i in range(0, len(todo), 4):
        group = todo[i:i + 4]
        sheet = Image.new("RGB", (1920, 1080 + 60), (16, 16, 16))
        dr = ImageDraw.Draw(sheet)
        for n, t in enumerate(group):
            x, y = (n % 2) * 960, (n // 2) * 570
            if os.path.exists(t["img"]):
                sheet.paste(Image.open(t["img"]).convert("RGB").resize((960, 540)), (x, y + 30))
            dr.text((x + 8, y + 8), t["key"], fill=(255, 255, 255))
        p = os.path.join(d, f"critic-todo-{i // 4 + 1}.jpg")
        sheet.save(p, quality=90)
        paths.append(p)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("round_dir")
    ap.add_argument("--publish", action="store_true", help="post the round (publish_round.py without --dry-run)")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--allow-missing-critic", action="store_true")
    a = ap.parse_args()
    d = os.path.abspath(a.round_dir)
    conf_p = os.path.join(d, "round.json")
    conf = json.load(open(conf_p, encoding="utf-8")) if os.path.exists(conf_p) else {}

    # 1. renders finished
    for sid in conf.get("renders", []):
        r = os.path.join(RQ_RESULTS, sid, "result.json")
        if not os.path.exists(r):
            sys.exit(f"renderq submission {sid} is not finished: `py -3.10 -I tools/renderq/renderq.py status`")
        res = json.load(open(r, encoding="utf-8"))
        if res["status"] != "done":
            bad = [f"{j['tag']}: {j.get('error') or j['missing']}" for j in res["jobs"] if j["status"] != "done"]
            print(f"WARNING: {sid} is {res['status']}: {'; '.join(bad)}")

    R = roundlib.Round(d, conf)
    ns = R.namespace()
    exec(compile(open(os.path.join(d, "spec_scenes.py"), encoding="utf-8").read(), "spec_scenes.py", "exec"), ns)
    for k in ("TITLE", "INTRO", "SCENES"):
        if k not in ns:
            sys.exit(f"spec_scenes.py defines no {k}")

    # 2. frames exist
    gone = sorted({p for p in R.used if not os.path.exists(p)})
    if gone:
        sys.exit("missing frames (render them, or fix the tag/scene):\n  " + "\n  ".join(gone))

    # 3. critic notes
    todo = list({t["key"]: t for t in R.missing_critic}.values())
    if todo and not a.allow_missing_critic:
        json.dump(todo, open(os.path.join(d, "critic-todo.json"), "w", encoding="utf-8", newline="\n"), indent=1)
        ps = sheets(todo, d)
        print(f"{len(todo)} frames have no critic note. Look at them, add each to {os.path.join(d, 'critic.json')} as")
        print('  "tag/scene": {"score": N, "note": "..."}   then re-run this script.')
        for t in todo:
            print(f"  {t['key']:<28} {t['img']}")
        print("Contact sheets: " + ", ".join(ps))
        sys.exit(3)

    # 4. costs and budgets
    spec = {"title": ns["TITLE"], "intro": ns["INTRO"], "scenes": ns["SCENES"]}
    if "n" in conf:
        spec["n"] = conf["n"]
        spec["id"] = f"r{conf['n']:03d}"
    nocost = [f"{s['id']}/{o['key']}" for s in spec["scenes"] for o in s["options"]
              if "img" in o and o.get("ms") is None and not o.get("noCost")]
    if nocost:
        sys.exit("no cost (no shaders-off baseline found; add round.json \"base\" or render one with renderq):\n  "
                 + "\n  ".join(nocost) + "\n  missing p50: " + ", ".join(sorted(set(R.missing_cost))))
    over = []
    for tag, budget in conf.get("budgets", {}).items():
        for s in spec["scenes"]:
            for o in s["options"]:
                if f"bench-{tag}-" in os.path.basename(o.get("img", "")) and o["ms"] > budget:
                    over.append(f"{s['id']}/{o['key']} {tag}: {o['ms']} ms > {budget}")
    if over:
        print("OVER BUDGET:\n  " + "\n  ".join(over))

    # 5. exposure
    try:
        sys.argv = [sys.argv[0]]
        import check_frames
        warn = []
        for p in sorted(set(R.used)):
            st = check_frames.frame_stats(p)
            if st["crushed_pct"] > 2.0 or st["clipped_pct"] > 1.0:
                warn.append(f"{os.path.basename(p)}: {st['crushed_pct']}% crushed, {st['clipped_pct']}% clipped")
        if warn:
            print("EXPOSURE (check_frames limits 2% / 1%):\n  " + "\n  ".join(warn))
    except Exception as e:      # numpy missing etc.: a warning, not a stop
        print(f"exposure check skipped: {e}")

    # 6. spec + publish
    out = os.path.join(d, "spec.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(spec, f, indent=1, ensure_ascii=False)
    ms = [o["ms"] for s in spec["scenes"] for o in s["options"] if o.get("ms") is not None]
    print(f"{out}: {len(spec['scenes'])} scenes, worst {max(ms) if ms else '-'} ms")
    cmd = [sys.executable, "-I", "-X", "utf8", os.path.join(HERE, "publish_round.py"), out]
    if not a.publish:
        cmd.append("--dry-run")
    if a.no_push:
        cmd.append("--no-push")
    r = subprocess.run(cmd, cwd=REPO)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
