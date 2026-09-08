#!/usr/bin/env python3
"""
Static marker scan across every mod archive in the live pack.

This is NOT the source of truth -- the runtime census is. This exists to answer
"where should I look, and did the runtime census miss a whole category?".

It walks the mods directory recursively, opens every .jar/.zip (including
archives nested inside archives, which is how orespawn.zip and MCHeli.zip ship),
and records, per archive, which classes reference each marker string. Constant
pool strings and the class's own constant-pool type entries both show up as raw
bytes in the classfile, so a plain substring test over the classfile bytes finds
both "this class implements ISpecialArmor" and "this class merely mentions it".
That over-reports, which is the safe direction for a "where to look" tool.

Usage:  python3 scan_jars.py [--mods DIR] [--json OUT.json]
"""

import argparse
import io
import json
import os
import zipfile

DEFAULT_MODS = os.path.expanduser(
    "~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/mods"
)

# Marker -> why we care.
MARKERS = {
    # Armour pipeline. Any class implementing ISpecialArmor supplies its own
    # absorption and completely bypasses the damageReduceAmount model that
    # Mitigation.java assumes, so this decides whether that model is complete.
    b"ISpecialArmor": "special-armor",
    b"ArmorProperties": "special-armor-props",
    b"damageReduceAmount": "armor-points",
    b"addArmorMaterial": "armor-material",
    b"ArmorMaterial": "armor-material-ref",
    # Weapons.
    b"addToolMaterial": "tool-material",
    b"getDamageVsEntity": "weapon-damage",
    b"func_150931_i": "weapon-damage-srg",   # ItemSword.getDamageVsEntity, srg name
    b"attackDamage": "attack-damage-field",
    b"generic.attackDamage": "attack-damage-attr",
    # Damage interception -- a mob overriding these can clamp or ignore a hit,
    # which is what makes multiplier enchantments worthless against it.
    b"attackEntityFrom": "damage-intercept",
    b"func_70097_a": "damage-intercept-srg",
    b"damageEntity": "damage-entity",
    b"func_70665_d": "damage-entity-srg",
    # Mob stats.
    b"SharedMonsterAttributes": "mob-attributes",
    b"applyEntityAttributes": "mob-attributes-apply",
    b"func_110147_ax": "mob-attributes-apply-srg",
    b"maxHealth": "max-health",
    # Registration, to enumerate what a mod adds.
    b"EntityRegistry": "entity-registry",
    b"registerModEntity": "entity-register",
    b"GameRegistry": "game-registry",
}


def walk_archive(data, name, depth, out):
    """Recurse into one archive's bytes, recording marker hits per class."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data)) if depth else zipfile.ZipFile(name)
    except Exception as exc:
        out.setdefault("_errors", []).append("%s: %s" % (name, exc))
        return

    with z:
        for info in z.infolist():
            if info.is_dir():
                continue
            entry = info.filename
            low = entry.lower()
            try:
                blob = z.read(info)
            except Exception as exc:
                out.setdefault("_errors", []).append("%s!%s: %s" % (name, entry, exc))
                continue

            if low.endswith((".jar", ".zip")) and depth < 3:
                walk_archive(blob, "%s!%s" % (name, entry), depth + 1, out)
                continue

            if not low.endswith(".class"):
                continue

            for marker, tag in MARKERS.items():
                if marker in blob:
                    out.setdefault(tag, {}).setdefault(name, []).append(entry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods", default=DEFAULT_MODS)
    ap.add_argument("--json", default=os.path.join(os.path.dirname(__file__), "scan_jars.json"))
    args = ap.parse_args()

    archives = []
    for root, _dirs, files in os.walk(args.mods):
        for f in sorted(files):
            if f.lower().endswith((".jar", ".zip")):
                archives.append(os.path.join(root, f))

    out = {}
    for path in sorted(archives):
        walk_archive(None, path, 0, out)

    # Report: for each marker, how many archives and classes matched.
    print("archives scanned: %d\n" % len(archives))
    print("%-26s %8s %8s" % ("marker", "archives", "classes"))
    print("%-26s %8s %8s" % ("-" * 26, "-" * 8, "-" * 8))
    for tag in sorted(k for k in out if not k.startswith("_")):
        per = out[tag]
        print("%-26s %8d %8d" % (tag, len(per), sum(len(v) for v in per.values())))

    errs = out.get("_errors", [])
    if errs:
        print("\nerrors: %d" % len(errs))
        for e in errs[:20]:
            print("  " + e)

    with open(args.json, "w") as fh:
        json.dump({"archives": archives, "hits": out}, fh, indent=1)
    print("\nwrote %s" % args.json)


if __name__ == "__main__":
    main()
