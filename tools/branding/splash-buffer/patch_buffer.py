# -*- coding: utf-8 -*-
"""Patch Forge SplashProgress IntBuffer from 4,194,304 to 16,777,216."""
from __future__ import print_function

import os
import shutil
import struct
import time
import zipfile
from pathlib import Path

INST = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4")
JAR = INST / "bin" / "lib" / "forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
WORK = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_splash-4k-buffer")
INNER = "cpw/mods/fml/client/SplashProgress.class"
OLD = 4194304
NEW = 16777216


def parse_cp(data):
    cp_count = struct.unpack(">H", data[8:10])[0]
    i = 10
    cp = [None]
    while len(cp) < cp_count:
        tag = data[i]
        if tag == 1:
            ln = struct.unpack(">H", data[i + 1 : i + 3])[0]
            cp.append(("Utf8", data[i + 3 : i + 3 + ln], i))
            i += 3 + ln
        elif tag == 3:
            v = struct.unpack(">i", data[i + 1 : i + 5])[0]
            cp.append(("Integer", v, i))
            i += 5
        elif tag == 4:
            cp.append(("Float", struct.unpack(">f", data[i + 1 : i + 5])[0], i))
            i += 5
        elif tag in (5, 6):
            cp.append(("Wide", None, i))
            cp.append(None)
            i += 9
        elif tag in (7, 8):
            cp.append(("Ref", None, i))
            i += 3
        elif tag in (9, 10, 11, 12):
            cp.append(("Ref", None, i))
            i += 5
        else:
            raise RuntimeError("unknown cp tag %s at %s" % (tag, i))
    return cp


def patch_class(data):
    cp = parse_cp(data)
    hits = [(idx, e[1], e[2]) for idx, e in enumerate(cp) if e and e[0] == "Integer"]
    print("integer constants:", [(i, v, hex(v & 0xFFFFFFFF)) for i, v, _ in hits])
    targets = [(idx, val, off) for idx, val, off in hits if val == OLD]
    if len(targets) != 1:
        raise SystemExit("expected exactly one Integer %s, found %s" % (OLD, targets))
    idx, val, off = targets[0]
    if data[off] != 3:
        raise SystemExit("tag mismatch at %s" % off)
    old_bytes = data[off + 1 : off + 5]
    expect = struct.pack(">i", OLD)
    if old_bytes != expect:
        raise SystemExit("bytes mismatch %s vs %s" % (old_bytes.hex(), expect.hex()))
    patched = bytearray(data)
    patched[off + 1 : off + 5] = struct.pack(">i", NEW)
    print("patched cp[%s] @ %s: %s -> %s" % (idx, off, OLD, NEW))
    return bytes(patched)


def rewrite_jar(new_class):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = INST / ("_backup-forge-splashbuf-%s.jar" % stamp)
    shutil.copy2(JAR, backup)
    print("backup", backup, backup.stat().st_size)

    tmp = JAR.with_suffix(".jar.tmpqf")
    stripped = []
    with zipfile.ZipFile(JAR, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            name = item.filename.replace("\\", "/")
            if name.startswith("META-INF/") and name.upper().endswith((".SF", ".RSA", ".DSA")):
                stripped.append(name)
                continue
            data = new_class if name == INNER else zin.read(item.filename)
            zout.writestr(item, data)
    os.replace(str(tmp), str(JAR))
    print("wrote", JAR, JAR.stat().st_size, "stripped", stripped or "none")

    with zipfile.ZipFile(JAR, "r") as z:
        meta = [n for n in z.namelist() if n.replace("\\", "/").startswith("META-INF/")]
        print("META-INF", meta)
        leftover = [n for n in meta if n.upper().endswith((".SF", ".RSA", ".DSA"))]
        if leftover:
            raise SystemExit("signatures remain: %s" % leftover)
        verify = z.read(INNER)
    cp = parse_cp(verify)
    ints = [e[1] for e in cp if e and e[0] == "Integer"]
    if OLD in ints:
        raise SystemExit("old buffer size still present")
    if NEW not in ints:
        raise SystemExit("new buffer size missing")
    print("jar verify ok ints", ints)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(JAR, "r") as z:
        raw = z.read(INNER)
    (WORK / "SplashProgress.class.before").write_bytes(raw)
    print("extracted", INNER, len(raw), "before")
    patched = patch_class(raw)
    (WORK / "SplashProgress.class").write_bytes(patched)
    (WORK / "SplashProgress.class.after").write_bytes(patched)
    rewrite_jar(patched)
    print("DONE patch")


if __name__ == "__main__":
    main()
