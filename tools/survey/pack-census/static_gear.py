#!/usr/bin/env python3
"""
Static cross-check for the runtime gear census.

Reads the constants passed to Forge's material factories straight out of the
bytecode:

    EnumHelper.addArmorMaterial(String name, int durability, int[] reductions, int enchantability)
    EnumHelper.addToolMaterial(String name, int harvestLevel, int maxUses, float efficiency,
                               float damage, int enchantability)

This is NOT the source of truth. It exists so that the runtime census has
something independent to disagree with. Where the two agree, the number is solid.
Where they disagree, that disagreement is itself the finding -- it means a mod
alters the material after construction, or the item does not use its material's
values, or one of the two readers is wrong. All three are worth knowing and none
of them is visible from a single method.

A decompiler is deliberately not used. Fernflower produces nothing for some of
these jars, and the values wanted here are literal constants in the constant
pool, which javap reports exactly.

Usage: python3 static_gear.py [--mods DIR] [--json OUT]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

DEFAULT_MODS = os.path.expanduser(
    "~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/mods"
)

JAVAP = "/Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home/bin/javap"

PUSH = re.compile(
    r"^\s*(\d+):\s+(ldc\w*|bipush|sipush|iconst_\w+|fconst_\w+|newarray|anewarray|"
    r"iastore|dup|invokestatic|getstatic)\s*(.*)$"
)
CONST_REF = re.compile(r"//\s*(?:String|int|float|Method|Field)?\s*(.*)$")


def javap(class_path):
    try:
        out = subprocess.run(
            [JAVAP, "-c", "-p", "-constants", class_path],
            capture_output=True, text=True, timeout=60,
        )
        return out.stdout
    except Exception:
        return ""


def literal(op, arg):
    """The numeric or string value an instruction pushes, or None."""
    if op.startswith("iconst_"):
        tail = op.split("_")[1]
        return -1 if tail == "m1" else int(tail)
    if op.startswith("fconst_"):
        return float(op.split("_")[1])
    if op in ("bipush", "sipush"):
        m = re.match(r"\s*(-?\d+)", arg)
        return int(m.group(1)) if m else None
    if op.startswith("ldc"):
        m = CONST_REF.search(arg)
        if not m:
            return None
        val = m.group(1).strip()
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        try:
            return float(val) if ("." in val or "E" in val) else int(val)
        except ValueError:
            return val
    return None


def scan_method(lines, start, end, factory):
    """
    Decode each call to `factory`, following the shape javac emits.

    An int[] argument is not a literal; it is built on the stack:

        iconst_4          // length
        newarray int
        dup / iconst_0 / bipush v0 / iastore
        dup / iconst_1 / bipush v1 / iastore
        ...

    so the values have to be picked out of the iastore sequence rather than read
    off a flat list of pushes. Getting this wrong produces an argument list that
    looks plausible and is scrambled, which is worse than no cross-check at all --
    an array is tracked explicitly here for that reason.

    Returns, per call site: {"scalars": [...], "array": [...]}. Interpretation of
    which scalar is which is left to the caller, since the two factories have
    different signatures.
    """
    found = []
    scalars = []
    array = []
    pending_index = None
    in_array = False

    for i in range(start, end):
        m = PUSH.match(lines[i])
        if not m:
            continue
        _, op, arg = m.groups()

        if op == "invokestatic":
            if factory in arg:
                found.append({"scalars": list(scalars), "array": list(array)})
            scalars, array, in_array, pending_index = [], [], False, None
            continue

        if op == "newarray" or op == "anewarray":
            # The length was pushed immediately before; it is not an argument.
            if scalars:
                scalars.pop()
            in_array, array = True, []
            continue

        if op == "iastore":
            if pending_index is not None:
                array.append(pending_index[1])
                pending_index = None
            continue

        if op == "dup":
            continue

        v = literal(op, arg)
        if v is None:
            continue

        if in_array:
            # Inside an array the literals arrive in index/value pairs.
            if pending_index is None:
                pending_index = (v, None)
            else:
                pending_index = (pending_index[0], v)
                # An index/value pair is only committed by its iastore, so a
                # stray literal cannot slip a value into the array.
        else:
            scalars.append(v)

        if len(scalars) > 40:
            scalars = scalars[-40:]

    return found


def scan_class(class_path):
    text = javap(class_path)
    if not text:
        return [], []
    lines = text.splitlines()
    armor = scan_method(lines, 0, len(lines), "addArmorMaterial")
    tool = scan_method(lines, 0, len(lines), "addToolMaterial")
    return armor, tool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods", default=DEFAULT_MODS)
    ap.add_argument("--json", default=os.path.join(os.path.dirname(__file__), "static_gear.json"))
    ap.add_argument("--scan", default=os.path.join(os.path.dirname(__file__), "scan_jars.json"),
                    help="output of scan_jars.py, to know which classes to open")
    args = ap.parse_args()

    if not os.path.exists(JAVAP):
        raise SystemExit("javap not found at %s" % JAVAP)

    scan = json.load(open(args.scan))
    hits = scan["hits"]
    targets = {}
    for tag in ("armor-material", "tool-material"):
        for archive, classes in hits.get(tag, {}).items():
            targets.setdefault(archive, set()).update(classes)

    results = {}
    tmp = tempfile.mkdtemp(prefix="qfstatic")
    try:
        for archive, classes in sorted(targets.items()):
            # "a.jar!inner.jar" -- the scan can reach inside nested archives.
            outer = archive.split("!")[0]
            inner = archive.split("!")[1:]
            try:
                blob = open(outer, "rb").read()
                for step in inner:
                    z = zipfile.ZipFile(__import__("io").BytesIO(blob))
                    blob = z.read(step)
                z = zipfile.ZipFile(__import__("io").BytesIO(blob))
            except Exception as exc:
                results.setdefault("_errors", []).append("%s: %s" % (archive, exc))
                continue

            for cls in sorted(classes):
                try:
                    data = z.read(cls)
                except Exception:
                    continue
                path = os.path.join(tmp, os.path.basename(cls))
                with open(path, "wb") as fh:
                    fh.write(data)
                armor, tool = scan_class(path)
                if armor or tool:
                    results.setdefault(os.path.basename(archive), {})[cls] = {
                        "armor": armor, "tool": tool,
                    }
                os.remove(path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    n_arm = sum(len(v["armor"]) for m in results.values() if isinstance(m, dict)
                for v in m.values() if isinstance(v, dict))
    n_tool = sum(len(v["tool"]) for m in results.values() if isinstance(m, dict)
                 for v in m.values() if isinstance(v, dict))
    n_arm4 = sum(1 for m in results.values() if isinstance(m, dict)
                 for v in m.values() if isinstance(v, dict)
                 for c in v["armor"] if len(c["array"]) == 4)
    print("archives with material calls: %d" % len([k for k in results if not k.startswith("_")]))
    print("addArmorMaterial call sites:  %d" % n_arm)
    print("addToolMaterial call sites:   %d" % n_tool)
    print("  of which armour calls with a clean 4-value reduction array: %d" % n_arm4)

    with open(args.json, "w") as fh:
        json.dump(results, fh, indent=1)
    print("wrote %s" % args.json)


if __name__ == "__main__":
    main()
