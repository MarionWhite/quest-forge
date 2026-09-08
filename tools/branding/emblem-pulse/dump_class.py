# -*- coding: utf-8 -*-
"""Dump constant pool and methods from a Java class file."""
from __future__ import print_function
import struct
import sys
from pathlib import Path


def parse_cp(data):
    cp_count = struct.unpack(">H", data[8:10])[0]
    i = 10
    cp = [None]
    while len(cp) < cp_count:
        tag = data[i]
        start = i
        if tag == 1:
            ln = struct.unpack(">H", data[i + 1 : i + 3])[0]
            val = data[i + 3 : i + 3 + ln]
            cp.append(("Utf8", val, start))
            i += 3 + ln
        elif tag == 3:
            cp.append(("Integer", struct.unpack(">i", data[i + 1 : i + 5])[0], start))
            i += 5
        elif tag == 4:
            cp.append(("Float", struct.unpack(">f", data[i + 1 : i + 5])[0], start))
            i += 5
        elif tag == 5:
            cp.append(("Long", struct.unpack(">q", data[i + 1 : i + 9])[0], start))
            cp.append(None)
            i += 9
        elif tag == 6:
            cp.append(("Double", struct.unpack(">d", data[i + 1 : i + 9])[0], start))
            cp.append(None)
            i += 9
        elif tag == 7:
            cp.append(("Class", struct.unpack(">H", data[i + 1 : i + 3])[0], start))
            i += 3
        elif tag == 8:
            cp.append(("String", struct.unpack(">H", data[i + 1 : i + 3])[0], start))
            i += 3
        elif tag in (9, 10, 11):
            kind = {9: "Fieldref", 10: "Methodref", 11: "InterfaceMethodref"}[tag]
            c, n = struct.unpack(">HH", data[i + 1 : i + 5])
            cp.append((kind, (c, n), start))
            i += 5
        elif tag == 12:
            n, d = struct.unpack(">HH", data[i + 1 : i + 5])
            cp.append(("NameAndType", (n, d), start))
            i += 5
        elif tag == 15:
            cp.append(("MethodHandle", data[i + 1 : i + 4], start))
            i += 4
        elif tag == 16:
            cp.append(("MethodType", struct.unpack(">H", data[i + 1 : i + 3])[0], start))
            i += 3
        elif tag == 18:
            cp.append(("InvokeDynamic", struct.unpack(">HH", data[i + 1 : i + 5]), start))
            i += 5
        else:
            raise RuntimeError("unknown cp tag %s at %s" % (tag, i))
    return cp, i


def u1(data, i):
    return data[i], i + 1


def u2(data, i):
    return struct.unpack(">H", data[i : i + 2])[0], i + 2


def u4(data, i):
    return struct.unpack(">I", data[i : i + 4])[0], i + 4


def utf(cp, idx):
    e = cp[idx]
    if e and e[0] == "Utf8":
        return e[1].decode("utf-8", "replace")
    return "?%s" % idx


def dump(path):
    data = Path(path).read_bytes()
    magic, minor, major, cpc = struct.unpack(">IHHH", data[:10])
    print("FILE", path)
    print("version", major, minor, "cp", cpc, "size", len(data))
    cp, i = parse_cp(data)
    print("--- constant pool ---")
    for idx, e in enumerate(cp):
        if e is None:
            continue
        kind, val, _ = e
        extra = ""
        if kind == "Utf8":
            extra = val.decode("utf-8", "replace")
        elif kind == "Class":
            extra = utf(cp, val)
        elif kind == "String":
            extra = utf(cp, val)
        elif kind in ("Fieldref", "Methodref", "InterfaceMethodref"):
            c, n = val
            nt = cp[n]
            extra = "%s.%s" % (
                utf(cp, cp[c][1]) if cp[c][0] == "Class" else c,
                ("%s:%s" % (utf(cp, nt[1][0]), utf(cp, nt[1][1]))) if nt and nt[0] == "NameAndType" else n,
            )
        elif kind == "NameAndType":
            extra = "%s:%s" % (utf(cp, val[0]), utf(cp, val[1]))
        else:
            extra = str(val)
        print("%4d %-18s %s" % (idx, kind, extra))

    access, i = u2(data, i)
    this, i = u2(data, i)
    sup, i = u2(data, i)
    ic, i = u2(data, i)
    i += 2 * ic
    fc, i = u2(data, i)
    print("--- fields %s this=%s super=%s ---" % (fc, utf(cp, cp[this][1]), utf(cp, cp[sup][1])))
    for _ in range(fc):
        fa, i = u2(data, i)
        fn, i = u2(data, i)
        fd, i = u2(data, i)
        ac, i = u2(data, i)
        print(" field", utf(cp, fn), utf(cp, fd))
        for _a in range(ac):
            an, i = u2(data, i)
            al, i = u4(data, i)
            i += al
    mc, i = u2(data, i)
    print("--- methods %s ---" % mc)
    for _ in range(mc):
        ma, i = u2(data, i)
        mn, i = u2(data, i)
        md, i = u2(data, i)
        ac, i = u2(data, i)
        print(" method", utf(cp, mn), utf(cp, md), "attrs", ac)
        for _a in range(ac):
            an, i = u2(data, i)
            al, i = u4(data, i)
            name = utf(cp, an)
            blob = data[i : i + al]
            i += al
            if name == "Code":
                max_stack, max_locals, code_len = struct.unpack(">HHI", blob[:8])
                code = blob[8 : 8 + code_len]
                print("  Code stack=%s locals=%s len=%s hex=%s" % (max_stack, max_locals, code_len, code.hex()))
    print("DONE")


if __name__ == "__main__":
    dump(sys.argv[1])
