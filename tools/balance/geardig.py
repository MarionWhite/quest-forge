#!/usr/bin/env python3
"""Read armour and tool material values straight out of the pack's mod jars.

EnumHelper.addArmorMaterial(name, durability, int[] reductions, enchantability) and
addToolMaterial(name, harvest, durability, efficiency, damage, enchantability) both
take their numbers as bytecode constants, so javap can read them without a
decompiler -- which matters here because fernflower produced nothing for OreSpawn.
"""
import os, re, subprocess, sys, zipfile, tempfile, shutil, json

MODS = os.path.expanduser("~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/mods")

TARGETS = ["orespawn", "TragicMC", "Lycanites", "TwilightForest", "railcraft", "Railcraft",
           "HardcoreEnderExpansion", "ProjectE", "Witchery", "MineBlade", "chocolateQuest",
           "1Legends", "Origin", "saintspack", "SaintsPack", "ICBM", "enderutilities",
           "AdventureBackpack", "Baubles"]

CONST = re.compile(r'(?:iconst_(\d)|bipush\s+(-?\d+)|sipush\s+(-?\d+)|ldc\s+(-?[\d.]+)|ldc2_w\s+(-?[\d.]+))')

def consts_in(lines):
    out = []
    for ln in lines:
        m = CONST.search(ln)
        if m:
            v = next(g for g in m.groups() if g is not None)
            out.append(float(v) if '.' in v else int(v))
    return out

def scan_jar(path):
    found = {"armor": [], "tool": []}
    tmp = tempfile.mkdtemp()
    try:
        try:
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist() if n.endswith(".class")]
                z.extractall(tmp, members=names)
        except Exception as e:
            return found, f"unreadable: {e}"
        classes = []
        for root, _, files in os.walk(tmp):
            for f in files:
                if f.endswith(".class"):
                    classes.append(os.path.join(root, f))
        # only disassemble classes whose constant pool mentions the helpers
        interesting = []
        for c in classes:
            try:
                blob = open(c, "rb").read()
            except Exception:
                continue
            if b"addArmorMaterial" in blob or b"addToolMaterial" in blob:
                interesting.append(c)
        for c in interesting:
            try:
                out = subprocess.run(["javap", "-p", "-c", c], capture_output=True,
                                     text=True, timeout=90).stdout
            except Exception:
                continue
            lines = out.splitlines()
            for i, ln in enumerate(lines):
                if "addArmorMaterial" in ln and "invokestatic" in ln:
                    window = lines[max(0, i - 40):i]
                    strs = re.findall(r'//\s*String (\S+)', "\n".join(window))
                    nums = consts_in(window)
                    found["armor"].append({"name": strs[-1] if strs else "?", "consts": nums[-12:]})
                if "addToolMaterial" in ln and "invokestatic" in ln:
                    window = lines[max(0, i - 30):i]
                    strs = re.findall(r'//\s*String (\S+)', "\n".join(window))
                    nums = consts_in(window)
                    found["tool"].append({"name": strs[-1] if strs else "?", "consts": nums[-10:]})
        return found, None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    for f in sorted(os.listdir(MODS)):
        if not (f.endswith(".jar") or f.endswith(".zip")):
            continue
        if not any(t.lower() in f.lower() for t in TARGETS):
            continue
        res, err = scan_jar(os.path.join(MODS, f))
        if err:
            print(f"## {f}: {err}")
            continue
        if not res["armor"] and not res["tool"]:
            continue
        print(f"\n## {f}")
        for a in res["armor"]:
            print(f"   ARMOR {a['name']:<24} {a['consts']}")
        for t in res["tool"]:
            print(f"   TOOL  {t['name']:<24} {t['consts']}")
