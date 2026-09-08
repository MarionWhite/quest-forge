# -*- coding: utf-8 -*-
"""Dump EventHandler.onRenderHand bytecode from the disabled Morph jar."""
from __future__ import print_function

import struct
import zipfile
from pathlib import Path

JAR = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4\mods_disabled\Morph-Beta-0.9.3.jar")

# Minimal constant-pool + method dump
CP_UTF8 = 1
CP_INT = 3
CP_FLOAT = 4
CP_LONG = 5
CP_DOUBLE = 6
CP_CLASS = 7
CP_STRING = 8
CP_FIELD = 9
CP_METHOD = 10
CP_IFACE = 11
CP_NAMEANDTYPE = 12
CP_METHODHANDLE = 15
CP_METHODTYPE = 16
CP_INVOKEDYNAMIC = 18


def read_cp(data, off):
    tag = data[off]
    if tag == CP_UTF8:
        (ln,) = struct.unpack_from(">H", data, off + 1)
        s = data[off + 3 : off + 3 + ln]
        return 3 + ln, ("Utf8", s.decode("utf-8", "replace"))
    if tag in (CP_INT, CP_FLOAT):
        return 5, (tag, struct.unpack_from(">I", data, off + 1)[0])
    if tag in (CP_LONG, CP_DOUBLE):
        return 9, (tag, struct.unpack_from(">Q", data, off + 1)[0])
    if tag in (CP_CLASS, CP_STRING, CP_METHODTYPE):
        return 3, (tag, struct.unpack_from(">H", data, off + 1)[0])
    if tag in (CP_FIELD, CP_METHOD, CP_IFACE, CP_NAMEANDTYPE):
        return 5, (tag, struct.unpack_from(">HH", data, off + 1))
    if tag == CP_METHODHANDLE:
        return 4, (tag, struct.unpack_from(">BH", data, off + 1))
    if tag == CP_INVOKEDYNAMIC:
        return 5, (tag, struct.unpack_from(">HH", data, off + 1))
    raise ValueError("unknown cp tag %s at %s" % (tag, off))


def parse_class(data):
    magic, minor, major, cp_count = struct.unpack_from(">IHHH", data, 0)
    assert magic == 0xCAFEBABE
    cp = [None]
    off = 10
    i = 1
    while i < cp_count:
        size, entry = read_cp(data, off)
        cp.append(entry)
        off += size
        if entry[0] in (CP_LONG, CP_DOUBLE):
            cp.append(None)
            i += 2
        else:
            i += 1

    def utf8(idx):
        e = cp[idx]
        return e[1] if e and e[0] == "Utf8" else "?"

    def cls(idx):
        e = cp[idx]
        return utf8(e[1]) if e and e[0] == CP_CLASS else "?"

    def nat(idx):
        e = cp[idx]
        return utf8(e[1][0]) + e[1] and (utf8(e[1][0]), utf8(e[1][1]))

    access, this, super_, ifc_count = struct.unpack_from(">HHHH", data, off)
    off += 8
    off += 2 * ifc_count
    (fields_count,) = struct.unpack_from(">H", data, off)
    off += 2

    def skip_attrs(o, n):
        for _ in range(n):
            _, ln = struct.unpack_from(">HI", data, o)
            o += 6 + ln
        return o

    for _ in range(fields_count):
        _, _, _, ac = struct.unpack_from(">HHHH", data, off)
        off += 8
        off = skip_attrs(off, ac)

    (methods_count,) = struct.unpack_from(">H", data, off)
    off += 2
    methods = []
    for _ in range(methods_count):
        acc, name_i, desc_i, ac = struct.unpack_from(">HHHH", data, off)
        off += 8
        name, desc = utf8(name_i), utf8(desc_i)
        code = None
        for _a in range(ac):
            an, ln = struct.unpack_from(">HI", data, off)
            body = data[off + 6 : off + 6 + ln]
            if utf8(an) == "Code":
                code = body
            off += 6 + ln
        methods.append((name, desc, acc, code))
    return cp, methods, utf8


OPNAMES = {
    0x00: "nop",
    0x01: "aconst_null",
    0x02: "iconst_m1",
    0x03: "iconst_0",
    0x04: "iconst_1",
    0x05: "iconst_2",
    0x12: "ldc",
    0x13: "ldc_w",
    0x15: "iload",
    0x19: "aload",
    0x1A: "iload_0",
    0x1B: "iload_1",
    0x2A: "aload_0",
    0x2B: "aload_1",
    0x2C: "aload_2",
    0x2D: "aload_3",
    0x57: "pop",
    0x59: "dup",
    0x9A: "ifne",
    0x99: "ifeq",
    0xA0: "if_icmpne",
    0x9F: "if_icmpeq",
    0xA7: "goto",
    0xB0: "areturn",
    0xB1: "return",
    0xB2: "getstatic",
    0xB3: "putstatic",
    0xB4: "getfield",
    0xB6: "invokevirtual",
    0xB7: "invokespecial",
    0xB8: "invokestatic",
    0xB9: "invokeinterface",
    0xBB: "new",
    0xC0: "checkcast",
    0xC6: "ifnull",
    0xC7: "ifnonnull",
}


def cp_ref(cp, idx, utf8):
    e = cp[idx]
    if e is None:
        return "?"
    tag = e[0]
    if tag == "Utf8":
        return e[1]
    if tag == CP_STRING:
        return 'ldc "%s"' % utf8(e[1])
    if tag == CP_CLASS:
        return utf8(e[1])
    if tag in (CP_FIELD, CP_METHOD, CP_IFACE):
        cls_i, nat_i = e[1]
        nat = cp[nat_i]
        name = utf8(nat[1][0])
        desc = utf8(nat[1][1])
        owner = utf8(cp[cls_i][1])
        return "%s.%s%s" % (owner, name, desc)
    return str(e)


def disasm(code_attr, cp, utf8, limit=80):
    max_stack, max_locals, code_len = struct.unpack_from(">HHI", code_attr, 0)
    code = code_attr[8 : 8 + code_len]
    print("  max_stack=%s max_locals=%s code_len=%s" % (max_stack, max_locals, code_len))
    pc = 0
    shown = 0
    while pc < len(code) and shown < limit:
        op = code[pc]
        name = OPNAMES.get(op, "op_%02X" % op)
        extra = ""
        n = 1
        if op in (0x12,):  # ldc
            extra = " " + cp_ref(cp, code[pc + 1], utf8)
            n = 2
        elif op in (0x13, 0xB2, 0xB3, 0xB4, 0xB6, 0xB7, 0xB8, 0xBB, 0xC0):
            idx = struct.unpack_from(">H", code, pc + 1)[0]
            extra = " " + cp_ref(cp, idx, utf8)
            n = 3
        elif op in (0x99, 0x9A, 0x9F, 0xA0, 0xA7, 0xC6, 0xC7):
            off = struct.unpack_from(">h", code, pc + 1)[0]
            extra = " -> %s" % (pc + off)
            n = 3
        elif op in (0x15, 0x19):
            extra = " %s" % code[pc + 1]
            n = 2
        print("  %4d: %s%s" % (pc, name, extra))
        pc += n
        shown += 1
    if pc < len(code):
        print("  ... %s bytes left" % (len(code) - pc))


def main():
    with zipfile.ZipFile(JAR) as z:
        data = z.read("morph/common/core/EventHandler.class")
    cp, methods, utf8 = parse_class(data)
    print("methods:")
    for name, desc, acc, code in methods:
        mark = " <<<" if name == "onRenderHand" else ""
        print("  %s %s acc=%s code=%s%s" % (name, desc, acc, code is not None, mark))
    for name, desc, acc, code in methods:
        if name == "onRenderHand":
            print("\n==== onRenderHand %s ====" % desc)
            disasm(code, cp, utf8, limit=120)
            # count renderHand invokes
            code_len = struct.unpack_from(">I", code, 4)[0]
            body = code[8 : 8 + code_len]
            print("\ninvokevirtual/static in method:")
            pc = 0
            while pc < len(body):
                op = body[pc]
                if op in (0xB6, 0xB8, 0xB2) and pc + 2 < len(body):
                    idx = struct.unpack_from(">H", body, pc + 1)[0]
                    ref = cp_ref(cp, idx, utf8)
                    if "renderHand" in ref or "func_78476" in ref or "HandGuard" in ref or "getInt" in ref:
                        print("  pc %s op %02X %s" % (pc, op, ref))
                    pc += 3
                elif op == 0x12:
                    pc += 2
                elif op in (0x13, 0x99, 0x9A, 0x9F, 0xA0, 0xA7, 0xC6, 0xC7, 0xB3, 0xB4, 0xB7, 0xBB, 0xC0):
                    pc += 3
                elif op in (0x15, 0x19):
                    pc += 2
                else:
                    pc += 1


if __name__ == "__main__":
    main()
