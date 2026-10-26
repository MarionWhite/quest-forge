"""Check that every sound name the site's JS uses exists in site/lib/sfx/manifest.json.

Finds string literals that look like sound event names (first dotted segment is one the bank
uses, e.g. mob.zombie.say, random.explode, qf.lucky.slam, music.krypt, orespawn:roar) and
reports any that the manifest lacks. Template strings with ${...} are listed as dynamic so a
human can check them once. Exit code 1 if anything is missing.

    python3 -I tools/site/check_sounds.py [site/lucky site/graves ...]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DEFAULT_DIRS = ["lucky", "graves", "lib/mc", "lib/qfaudio.js"]

LIT = re.compile(r"""(['"`])((?:orespawn:)?[a-z0-9_]+(?:\.[a-z0-9_${}]+)+)\1""")


def main(argv):
    events = json.loads((SITE / "lib/sfx/manifest.json").read_text())["events"]
    names = set(events)
    prefixes = {n.split(".")[0] for n in names if not n.startswith("orespawn:")}
    targets = [pathlib.Path(a) for a in argv] or [SITE / d for d in DEFAULT_DIRS]
    files = []
    for t in targets:
        t = t if t.is_absolute() else (ROOT / t if (ROOT / t).exists() else SITE / t)
        files += [t] if t.is_file() else sorted(t.rglob("*.js")) + sorted(t.rglob("*.mjs"))
    missing, dynamic, used = {}, {}, set()
    for f in files:
        text = f.read_text(errors="replace")
        for m in LIT.finditer(text):
            s = m.group(2)
            ospawn = s.startswith("orespawn:")
            if not ospawn and s.split(".")[0] not in prefixes:
                continue
            if s.endswith((".js", ".png", ".json", ".html", ".m4a", ".css")):
                continue
            line = text.count("\n", 0, m.start()) + 1
            where = f"{f.relative_to(ROOT)}:{line}"
            if "${" in s:
                dynamic.setdefault(s, []).append(where)
            elif s in names:
                used.add(s)
            else:
                missing.setdefault(s, []).append(where)
    print(f"{len(files)} files, {len(used)} sound names found in the bank, "
          f"{len(missing)} missing, {len(dynamic)} dynamic")
    for s, w in sorted(missing.items()):
        print(f"MISSING {s}  {', '.join(w[:3])}{' ...' if len(w) > 3 else ''}")
    for s, w in sorted(dynamic.items()):
        print(f"dynamic {s}  {', '.join(w[:2])}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
