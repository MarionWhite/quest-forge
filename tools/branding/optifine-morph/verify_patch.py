# -*- coding: utf-8 -*-
from __future__ import print_function
import struct
import zipfile
from pathlib import Path
import inspect_eventhandler as ie

JAR = Path(__file__).resolve().parent / "Morph-Beta-0.9.3-QF-OPTIFINE.jar"


def walk(code):
    return list(ie.walk_code(code) if hasattr(ie, "walk_code") else _walk(code))


def _walk(code):
    from patch_morph_optifine import walk_code
    return walk_code(code)


def main():
    from patch_morph_optifine import walk_code, parse_code_attr, parse_cp, cp_utf8

    with zipfile.ZipFile(JAR) as z:
        print("entries:", [n for n in z.namelist() if "HandGuard" in n or "EventHandler" in n])
        guard = z.read("com/questforge/MorphHandGuard.class")
        handler = z.read("morph/common/core/EventHandler.class")
        helper = z.read("morph/client/model/ModelHelper.class")
        model = z.read("morph/client/model/ModelMorph.class")

    print("guard magic", guard[:4].hex(), "size", len(guard))
    print("helper pop-nop", helper.count(bytes([0x57, 0x00, 0x00])))
    print("model pop-nop", model.count(bytes([0x57, 0x00, 0x00])))

    cp, methods, utf8 = ie.parse_class(handler)
    for name, desc, acc, code in methods:
        if name != "onRenderHand":
            continue
        print("==== patched onRenderHand ====")
        ie.disasm(code, cp, utf8, limit=20)
        max_stack, max_locals, body, excs, attrs = parse_code_attr(code)
        print("code_len", len(body), "excs", len(excs), "attrs", len(attrs))
        pcs = set()
        render = 0
        returns = 0
        for pc, op, ln in walk_code(body):
            pcs.add(pc)
            if op == 0xB6:
                idx = struct.unpack_from(">H", body, pc + 1)[0]
                ref = ie.cp_ref(cp, idx, utf8)
                if "func_78476_b" in ref:
                    render += 1
                    print("  renderHand at", pc, ref)
            if op == 0xB1:
                returns += 1
                print("  return at", pc)
            if op == 0xB8:
                idx = struct.unpack_from(">H", body, pc + 1)[0]
                ref = ie.cp_ref(cp, idx, utf8)
                if "HandGuard" in ref:
                    print("  guard call at", pc, ref)
        # branch target check
        bad = 0
        for pc, op, ln in walk_code(body):
            if op in (0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xC6, 0xC7):
                off = struct.unpack_from(">h", body, pc + 1)[0]
                tgt = pc + off
                if tgt not in pcs and tgt != len(body):
                    print("  BAD branch", pc, "->", tgt)
                    bad += 1
        print("renderHand invokes", render, "returns", returns, "bad branches", bad)


if __name__ == "__main__":
    main()
