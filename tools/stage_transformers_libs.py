#!/usr/bin/env python3
"""Copy the four jars TransformersMod compiles against out of a live instance.

mods/transformers/build.gradle.kts declares NEI, CodeChickenLib, CodeChickenCore
and Waila as compileOnly, deliberately using THE PACK'S OWN JARS rather than the
GTNH forks on maven -- GTNH's NEI generified TemplateRecipeHandler, so the four
recipe handlers in the mod do not compile against it, and had they compiled they
would have been built against signatures the pack does not ship.

Those jars are other people's work and are not committed (see .gitignore), so a
clean checkout has an empty libs/ and the build fails on the first import. This
script fills it, on any machine, from the instance the pack actually runs.

Two details that cost time when done by hand:

  * CodeChickenLib is NOT beside the others. Prism keeps it in mods/1.7.10/,
    the version-scoped subfolder, and it carries a versioned filename.
  * build.gradle.kts names the files without versions, so they have to be
    renamed on the way in.

    stage_transformers_libs.py --instance <prism instance dir> [--repo <root>]

Idempotent: re-running against the same instance reports "unchanged".
"""

import argparse
import hashlib
import os
import shutil
import sys

# Destination name -> substrings that identify the source jar. Matching is on
# the lowercased basename, so versioned filenames are found without a pattern
# per release. The exclude list keeps "CodeChickenCore" from matching the
# CodeChickenLib entry and vice versa.
WANTED = [
    ("NotEnoughItemsuniversal.jar", ["notenoughitems"], ["addon", "plugin"]),
    ("CodeChickenLib.jar",          ["codechickenlib"], []),
    ("CodeChickenCore.jar",         ["codechickencore"], []),
    ("Waila.jar",                   ["waila"],          ["harvest", "plugin"]),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_jars(root):
    """Every .jar under the instance's mods/, at any depth."""
    hits = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".jar"):
                hits.append(os.path.join(dirpath, fn))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True,
                    help="Prism instance directory (the one holding minecraft/)")
    ap.add_argument("--repo", default=os.path.join(os.path.dirname(__file__), ".."),
                    help="repository root (default: the one this script is in)")
    args = ap.parse_args()

    mods = os.path.join(os.path.abspath(args.instance), "minecraft", "mods")
    if not os.path.isdir(mods):
        # Tolerate being pointed at the minecraft/ dir, or at mods/ itself.
        for alt in (os.path.join(os.path.abspath(args.instance), "mods"),
                    os.path.abspath(args.instance)):
            if os.path.isdir(os.path.join(alt, ".")) and \
               any(f.lower().endswith(".jar") for f in os.listdir(alt)):
                mods = alt
                break
        else:
            print("no mods directory under %s" % args.instance, file=sys.stderr)
            return 2

    dest = os.path.join(os.path.abspath(args.repo), "mods", "transformers", "libs")
    os.makedirs(dest, exist_ok=True)

    jars = find_jars(mods)
    print("instance mods: %s (%d jars)" % (mods, len(jars)))
    print("staging into:  %s\n" % dest)

    failed = 0
    for name, needles, excludes in WANTED:
        matches = []
        for path in jars:
            base = os.path.basename(path).lower()
            if any(n in base for n in needles) and not any(x in base for x in excludes):
                matches.append(path)

        if not matches:
            print("MISSING  %-30s no jar matching %s" % (name, "/".join(needles)))
            failed += 1
            continue
        if len(matches) > 1:
            # Ambiguity is a real risk: an instance can carry both a versioned
            # and an unversioned copy. Refuse rather than pick, because picking
            # wrong compiles against signatures the game does not load.
            print("AMBIGUOUS %-29s %d candidates:" % (name, len(matches)))
            for m in matches:
                print("              %s" % m)
            failed += 1
            continue

        src = matches[0]
        target = os.path.join(dest, name)
        if os.path.exists(target) and sha(target) == sha(src):
            print("unchanged %-29s %s" % (name, os.path.basename(src)))
            continue

        shutil.copy2(src, target)
        print("staged    %-29s <- %s (%d bytes)"
              % (name, os.path.relpath(src, mods), os.path.getsize(target)))

    if failed:
        print("\n%d jar(s) not staged. The build will fail on imports until they are."
              % failed)
        return 1

    print("\nAll four staged. mods/transformers now builds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
