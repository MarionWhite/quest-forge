# -*- coding: utf-8 -*-
"""Build a WORK-FOLDER copy of Morph 0.9.3 with an onRenderHand reentrancy guard.

Does NOT touch the live instance mods\\ folder. The disabled jar already has
the three deleteDisplayLists NOPs (ModelHelper x2, ModelMorph x1). This script
copies that jar and injects:

    if (com.questforge.MorphHandGuard.shouldSkip()) return;
    MorphHandGuard.enter();
    try { original onRenderHand body }
    finally { MorphHandGuard.leave(); }   // leave() before every return

so OptiFine E7's ReflectorForge.renderFirstPersonHand -> RenderHandEvent
cannot recurse when Morph calls EntityRenderer.func_78476_b from inside
the handler.

Also ships com.questforge.MorphHandGuard inside the patched jar.
"""
from __future__ import print_function

import os
import shutil
import struct
import zipfile
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
INST = Path(os.environ.get("APPDATA", "")) / ".crazycraft4"
SRC_JAR = INST / "mods_disabled" / "Morph-Beta-0.9.3.jar"
OUT_JAR = HERE / "Morph-Beta-0.9.3-QF-OPTIFINE.jar"

# ---------------------------------------------------------------------------
# Constant pool
# ---------------------------------------------------------------------------
CP_UTF8, CP_INT, CP_FLOAT, CP_LONG, CP_DOUBLE = 1, 3, 4, 5, 6
CP_CLASS, CP_STRING, CP_FIELD, CP_METHOD, CP_IFACE = 7, 8, 9, 10, 11
CP_NAT, CP_MHANDLE, CP_MTYPE, CP_INVOKEDYNAMIC = 12, 15, 16, 18


def _u1(data, off):
    return data[off], off + 1


def _u2(data, off):
    return struct.unpack_from(">H", data, off)[0], off + 2


def _u4(data, off):
    return struct.unpack_from(">I", data, off)[0], off + 4


def parse_cp(data):
    magic, minor, major, count = struct.unpack_from(">IHHH", data, 0)
    if magic != 0xCAFEBABE:
        raise ValueError("not a class file")
    entries = [None]  # 1-based
    raw = [None]
    off = 10
    i = 1
    while i < count:
        start = off
        tag = data[off]
        if tag == CP_UTF8:
            ln = struct.unpack_from(">H", data, off + 1)[0]
            off = off + 3 + ln
        elif tag in (CP_INT, CP_FLOAT, CP_FIELD, CP_METHOD, CP_IFACE, CP_NAT, CP_INVOKEDYNAMIC):
            off += 5
        elif tag in (CP_CLASS, CP_STRING, CP_MTYPE):
            off += 3
        elif tag in (CP_LONG, CP_DOUBLE):
            off += 9
        elif tag == CP_MHANDLE:
            off += 4
        else:
            raise ValueError("bad cp tag %s at %s" % (tag, start))
        blob = data[start:off]
        entries.append(blob)
        raw.append(blob)
        if tag in (CP_LONG, CP_DOUBLE):
            entries.append(None)
            raw.append(None)
            i += 2
        else:
            i += 1
    return entries, off, minor, major, count


def cp_utf8(entries, idx):
    b = entries[idx]
    if b is None or b[0] != CP_UTF8:
        return None
    return b[3:].decode("utf-8")


def add_utf8(entries, s):
    """Append a Utf8 CP entry; return its 1-based index."""
    encoded = s.encode("utf-8")
    blob = bytes([CP_UTF8]) + struct.pack(">H", len(encoded)) + encoded
    entries.append(blob)
    return len(entries) - 1


def add_class(entries, name_idx):
    entries.append(bytes([CP_CLASS]) + struct.pack(">H", name_idx))
    return len(entries) - 1


def add_nat(entries, name_idx, desc_idx):
    entries.append(bytes([CP_NAT]) + struct.pack(">HH", name_idx, desc_idx))
    return len(entries) - 1


def add_methodref(entries, cls_idx, nat_idx):
    entries.append(bytes([CP_METHOD]) + struct.pack(">HH", cls_idx, nat_idx))
    return len(entries) - 1


# Instruction sizes for a linear walk (no lookupswitch/tableswitch in this method).
INSN_LEN = {
    0x00: 1, 0x01: 1, 0x02: 1, 0x03: 1, 0x04: 1, 0x05: 1, 0x06: 1, 0x07: 1, 0x08: 1,
    0x09: 1, 0x0A: 1, 0x0B: 1, 0x0C: 1, 0x0D: 1, 0x0E: 1, 0x0F: 1,
    0x10: 2, 0x11: 3, 0x12: 2, 0x13: 3, 0x14: 3,
    0x15: 2, 0x16: 2, 0x17: 2, 0x18: 2, 0x19: 2,
    0x1A: 1, 0x1B: 1, 0x1C: 1, 0x1D: 1, 0x1E: 1, 0x1F: 1,
    0x20: 1, 0x21: 1, 0x22: 1, 0x23: 1, 0x24: 1, 0x25: 1,
    0x26: 1, 0x27: 1, 0x28: 1, 0x29: 1, 0x2A: 1, 0x2B: 1, 0x2C: 1, 0x2D: 1,
    0x2E: 1, 0x2F: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 1, 0x35: 1,
    0x36: 2, 0x37: 2, 0x38: 2, 0x39: 2, 0x3A: 2,
    0x3B: 1, 0x3C: 1, 0x3D: 1, 0x3E: 1, 0x3F: 1,
    0x40: 1, 0x41: 1, 0x42: 1, 0x43: 1, 0x44: 1, 0x45: 1,
    0x46: 1, 0x47: 1, 0x48: 1, 0x49: 1, 0x4A: 1, 0x4B: 1, 0x4C: 1, 0x4D: 1, 0x4E: 1,
    0x4F: 1, 0x50: 1, 0x51: 1, 0x52: 1, 0x53: 1, 0x54: 1, 0x55: 1, 0x56: 1,
    0x57: 1, 0x58: 1, 0x59: 1, 0x5A: 1, 0x5B: 1, 0x5C: 1, 0x5D: 1, 0x5E: 1, 0x5F: 1,
    0x60: 1, 0x61: 1, 0x62: 1, 0x63: 1, 0x64: 1, 0x65: 1, 0x66: 1, 0x67: 1,
    0x68: 1, 0x69: 1, 0x6A: 1, 0x6B: 1, 0x6C: 1, 0x6D: 1, 0x6E: 1, 0x6F: 1,
    0x70: 1, 0x71: 1, 0x72: 1, 0x73: 1, 0x74: 1, 0x75: 1, 0x76: 1, 0x77: 1,
    0x78: 1, 0x79: 1, 0x7A: 1, 0x7B: 1, 0x7C: 1, 0x7D: 1, 0x7E: 1, 0x7F: 1,
    0x80: 1, 0x81: 1, 0x82: 1, 0x83: 1,
    0x84: 3, 0x85: 1, 0x86: 1, 0x87: 1, 0x88: 1, 0x89: 1, 0x8A: 1, 0x8B: 1,
    0x8C: 1, 0x8D: 1, 0x8E: 1, 0x8F: 1, 0x90: 1, 0x91: 1, 0x92: 1, 0x93: 1,
    0x94: 1, 0x95: 1, 0x96: 1, 0x97: 1, 0x98: 1,
    0x99: 3, 0x9A: 3, 0x9B: 3, 0x9C: 3, 0x9D: 3, 0x9E: 3,
    0x9F: 3, 0xA0: 3, 0xA1: 3, 0xA2: 3, 0xA3: 3, 0xA4: 3, 0xA5: 3, 0xA6: 3,
    0xA7: 3, 0xA8: 3, 0xA9: 2, 0xAA: None, 0xAB: None,
    0xAC: 1, 0xAD: 1, 0xAE: 1, 0xAF: 1, 0xB0: 1, 0xB1: 1,
    0xB2: 3, 0xB3: 3, 0xB4: 3, 0xB5: 3, 0xB6: 3, 0xB7: 3, 0xB8: 3,
    0xB9: 5, 0xBA: 5, 0xBB: 3, 0xBC: 2, 0xBD: 3, 0xBE: 1, 0xBF: 1,
    0xC0: 3, 0xC1: 3, 0xC2: 1, 0xC3: 1, 0xC4: None, 0xC5: 4,
    0xC6: 3, 0xC7: 3, 0xC8: 5, 0xC9: 5,
}


def walk_code(code):
    """Yield (pc, opcode, length)."""
    pc = 0
    n = len(code)
    while pc < n:
        op = code[pc]
        if op == 0xC4:  # wide
            if code[pc + 1] == 0x84:
                ln = 6
            else:
                ln = 4
        elif op == 0xAA:  # tableswitch
            pad = (4 - ((pc + 1) % 4)) % 4
            low, high = struct.unpack_from(">ii", code, pc + 1 + pad + 4)
            ln = 1 + pad + 12 + 4 * (high - low + 1)
        elif op == 0xAB:  # lookupswitch
            pad = (4 - ((pc + 1) % 4)) % 4
            npairs = struct.unpack_from(">i", code, pc + 1 + pad + 4)[0]
            ln = 1 + pad + 8 + 8 * npairs
        else:
            ln = INSN_LEN.get(op)
            if ln is None:
                raise ValueError("unhandled opcode 0x%02X at %s" % (op, pc))
        yield pc, op, ln
        pc += ln


def parse_code_attr(body):
    max_stack, max_locals, code_len = struct.unpack_from(">HHI", body, 0)
    off = 8
    code = body[off : off + code_len]
    off += code_len
    exc_n, off = _u2(body, off)
    excs = []
    for _ in range(exc_n):
        start, end, handler, catch = struct.unpack_from(">HHHH", body, off)
        excs.append([start, end, handler, catch])
        off += 8
    attr_n, off = _u2(body, off)
    attrs = []
    for _ in range(attr_n):
        name_i, ln = struct.unpack_from(">HI", body, off)
        attrs.append((name_i, body[off + 6 : off + 6 + ln]))
        off += 6 + ln
    return max_stack, max_locals, code, excs, attrs


def build_code_attr(max_stack, max_locals, code, excs, attrs):
    out = BytesIO()
    out.write(struct.pack(">HHI", max_stack, max_locals, len(code)))
    out.write(code)
    out.write(struct.pack(">H", len(excs)))
    for start, end, handler, catch in excs:
        out.write(struct.pack(">HHHH", start, end, handler, catch))
    out.write(struct.pack(">H", len(attrs)))
    for name_i, abody in attrs:
        out.write(struct.pack(">HI", name_i, len(abody)))
        out.write(abody)
    return out.getvalue()


def shift_stackmap(attr_body, insert_at, inserted):
    """Add `inserted` bytes to the first frame that starts at/after insert_at.

    StackMapTable offset_deltas are relative. Inserting at pc 0 only bumps
    the first frame's delta. Inserting later bumps the frame that covers
    that pc (the first frame whose cumulative offset >= insert_at).
    """
    if not attr_body:
        return attr_body
    nframes, off = _u2(attr_body, 0)
    out = BytesIO()
    out.write(struct.pack(">H", nframes))
    pos = -1
    applied = False
    for _ in range(nframes):
        frame_start = off
        kind = attr_body[off]
        off += 1
        if kind <= 63:  # same_frame
            delta = kind
            new_pos = pos + delta + 1
            if (not applied) and new_pos >= insert_at:
                delta += inserted
                applied = True
            if delta <= 63:
                out.write(bytes([delta]))
            else:
                # promote to same_frame_extended
                out.write(bytes([251]) + struct.pack(">H", delta))
            pos = new_pos if not (applied and new_pos >= insert_at and False) else pos
            # pos tracking: original positions
            pos = (pos - delta - 1) + (kind + 1)  # restore orig then
            pos = pos  # messy — recompute properly below
        else:
            # fall through to generic rebuild
            pass
    # Safer: full rewrite with correct pos tracking
    return _shift_stackmap_full(attr_body, insert_at, inserted)


def _vti_size(data, off):
    tag = data[off]
    if tag in (7, 8):  # Object, Uninitialized
        return 3
    return 1


def _shift_stackmap_full(attr_body, insert_at, inserted):
    nframes, off = _u2(attr_body, 0)
    pieces = []
    pos = -1
    applied = False
    for _ in range(nframes):
        kind = attr_body[off]
        start = off
        off += 1
        if kind <= 63:
            delta = kind
            rest = b""
        elif 64 <= kind <= 127:
            delta = kind - 64
            n = _vti_size(attr_body, off)
            rest = attr_body[off : off + n]
            off += n
        elif kind == 247:
            delta, off = _u2(attr_body, off)
            n = _vti_size(attr_body, off)
            rest = struct.pack(">H", delta) + attr_body[off : off + n]
            off += n
            kind_out_prefix = bytes([247])
            new_pos = pos + delta + 1
            if (not applied) and new_pos >= insert_at:
                delta += inserted
                applied = True
            pieces.append(bytes([247]) + struct.pack(">H", delta) + rest[2:])
            pos = new_pos
            continue
        elif 248 <= kind <= 250:
            delta, off = _u2(attr_body, off)
            rest = b""
            new_pos = pos + delta + 1
            if (not applied) and new_pos >= insert_at:
                delta += inserted
                applied = True
            pieces.append(bytes([kind]) + struct.pack(">H", delta))
            pos = new_pos
            continue
        elif kind == 251:
            delta, off = _u2(attr_body, off)
            new_pos = pos + delta + 1
            if (not applied) and new_pos >= insert_at:
                delta += inserted
                applied = True
            pieces.append(bytes([251]) + struct.pack(">H", delta))
            pos = new_pos
            continue
        elif 252 <= kind <= 254:
            delta, off = _u2(attr_body, off)
            nloc = kind - 251
            rest_start = off
            for _l in range(nloc):
                off += _vti_size(attr_body, off)
            rest = attr_body[rest_start:off]
            new_pos = pos + delta + 1
            if (not applied) and new_pos >= insert_at:
                delta += inserted
                applied = True
            pieces.append(bytes([kind]) + struct.pack(">H", delta) + rest)
            pos = new_pos
            continue
        elif kind == 255:
            delta, off = _u2(attr_body, off)
            nloc, off = _u2(attr_body, off)
            rest_parts = [struct.pack(">H", nloc)]
            for _l in range(nloc):
                n = _vti_size(attr_body, off)
                rest_parts.append(attr_body[off : off + n])
                off += n
            nstack, off = _u2(attr_body, off)
            rest_parts.append(struct.pack(">H", nstack))
            for _s in range(nstack):
                n = _vti_size(attr_body, off)
                rest_parts.append(attr_body[off : off + n])
                off += n
            rest = b"".join(rest_parts)
            new_pos = pos + delta + 1
            if (not applied) and new_pos >= insert_at:
                delta += inserted
                applied = True
            pieces.append(bytes([255]) + struct.pack(">H", delta) + rest)
            pos = new_pos
            continue
        else:
            raise ValueError("bad stackmap frame %s" % kind)

        # same / same_locals_1_stack compact forms
        new_pos = pos + delta + 1
        bump = 0
        if (not applied) and new_pos >= insert_at:
            bump = inserted
            applied = True
        new_delta = delta + bump
        if kind <= 63:
            if new_delta <= 63:
                pieces.append(bytes([new_delta]))
            else:
                pieces.append(bytes([251]) + struct.pack(">H", new_delta))
        else:
            # 64-127 same_locals_1_stack_item
            if new_delta <= 63:
                pieces.append(bytes([64 + new_delta]) + rest)
            else:
                pieces.append(bytes([247]) + struct.pack(">H", new_delta) + rest)
        pos = new_pos
    out = BytesIO()
    out.write(struct.pack(">H", nframes))
    for p in pieces:
        out.write(p)
    return out.getvalue()


def shift_line_numbers(body, insert_at, inserted):
    n, off = _u2(body, 0)
    out = BytesIO()
    out.write(struct.pack(">H", n))
    for _ in range(n):
        start, line = struct.unpack_from(">HH", body, off)
        off += 4
        if start >= insert_at:
            start += inserted
        out.write(struct.pack(">HH", start, line))
    return out.getvalue()


def shift_local_vars(body, insert_at, inserted):
    n, off = _u2(body, 0)
    out = BytesIO()
    out.write(struct.pack(">H", n))
    for _ in range(n):
        start, length, name, desc, index = struct.unpack_from(">HHHHH", body, off)
        off += 10
        end = start + length
        if start >= insert_at:
            start += inserted
        if end >= insert_at:
            end += inserted
        length = end - start
        out.write(struct.pack(">HHHHH", start, length, name, desc, index))
    return out.getvalue()


# ---------------------------------------------------------------------------
# MorphHandGuard.class (hand-assembled, Java 6 / major 50)
# ---------------------------------------------------------------------------
def build_hand_guard_class():
    """public class com.questforge.MorphHandGuard { public static boolean rendering;
    public static boolean shouldSkip() { return rendering; }
    public static void enter() { rendering = true; }
    public static void leave() { rendering = false; }
    }
    """
    # Constant pool (1-based)
    # 1 Utf8 com/questforge/MorphHandGuard
    # 2 Class #1
    # 3 Utf8 java/lang/Object
    # 4 Class #3
    # 5 Utf8 rendering
    # 6 Utf8 Z
    # 7 Utf8 shouldSkip
    # 8 Utf8 ()Z
    # 9 Utf8 enter
    # 10 Utf8 ()V
    # 11 Utf8 leave
    # 12 Utf8 Code
    # 13 NameAndType #5 #6
    # 14 Fieldref #2 #13
    # 15 Utf8 <init>
    cp = []

    def u(s):
        b = s.encode("utf-8")
        cp.append(bytes([1]) + struct.pack(">H", len(b)) + b)
        return len(cp)

    def cls(i):
        cp.append(bytes([7]) + struct.pack(">H", i))
        return len(cp)

    def nat(a, b):
        cp.append(bytes([12]) + struct.pack(">HH", a, b))
        return len(cp)

    def field(c, n):
        cp.append(bytes([9]) + struct.pack(">HH", c, n))
        return len(cp)

    i_this = u("com/questforge/MorphHandGuard")
    c_this = cls(i_this)
    i_obj = u("java/lang/Object")
    c_obj = cls(i_obj)
    i_ren = u("rendering")
    i_z = u("Z")
    i_skip = u("shouldSkip")
    i_bool = u("()Z")
    i_enter = u("enter")
    i_void = u("()V")
    i_leave = u("leave")
    i_code = u("Code")
    i_init = u("<init>")
    n_ren = nat(i_ren, i_z)
    f_ren = field(c_this, n_ren)
    n_init = nat(i_init, i_void)

    def method(name_i, desc_i, max_stack, max_locals, code):
        code_attr = struct.pack(">HHI", max_stack, max_locals, len(code)) + code
        code_attr += struct.pack(">H", 0)  # no exceptions
        code_attr += struct.pack(">H", 0)  # no code attrs
        attr = struct.pack(">HI", i_code, len(code_attr)) + code_attr
        return struct.pack(">HHHH", 0x0009, name_i, desc_i, 1) + attr  # public static, 1 attr

    skip_code = struct.pack(">BH", 0xB2, f_ren) + bytes([0xAC])  # getstatic; ireturn
    enter_code = bytes([0x04]) + struct.pack(">BH", 0xB3, f_ren) + bytes([0xB1])
    leave_code = bytes([0x03]) + struct.pack(">BH", 0xB3, f_ren) + bytes([0xB1])
    init_code = bytes([0x2A, 0xB7]) + struct.pack(">H", 0)  # placeholder

    # We need Object.<init> methodref
    i_obj_init_name = i_init
    i_obj_init_desc = i_void
    n_obj_init = nat(i_obj_init_name, i_obj_init_desc)
    m_obj_init = len(cp) + 1
    cp.append(bytes([10]) + struct.pack(">HH", c_obj, n_obj_init))

    init_code = bytes([0x2A]) + struct.pack(">BH", 0xB7, m_obj_init) + bytes([0xB1])

    methods = b""
    # <init> public
    code_attr = struct.pack(">HHI", 1, 1, len(init_code)) + init_code + struct.pack(">HH", 0, 0)
    methods += struct.pack(">HHHH", 0x0001, i_init, i_void, 1)
    methods += struct.pack(">HI", i_code, len(code_attr)) + code_attr
    methods += method(i_skip, i_bool, 1, 0, skip_code)
    methods += method(i_enter, i_void, 1, 0, enter_code)
    methods += method(i_leave, i_void, 1, 0, leave_code)

    out = BytesIO()
    out.write(struct.pack(">IHHH", 0xCAFEBABE, 0, 50, len(cp) + 1))
    for e in cp:
        out.write(e)
    out.write(struct.pack(">HHHH", 0x0021, c_this, c_obj, 0))  # public super, no ifaces
    out.write(struct.pack(">H", 1))  # 1 field
    out.write(struct.pack(">HHHH", 0x0009, i_ren, i_z, 0))  # public static boolean, no attrs
    out.write(struct.pack(">H", 4))  # 4 methods
    out.write(methods)
    out.write(struct.pack(">H", 0))  # no class attrs
    return out.getvalue()


# ---------------------------------------------------------------------------
# Patch EventHandler.onRenderHand
# ---------------------------------------------------------------------------
PREFIX_LEN = 10  # shouldSkip + ifeq + return + enter
LEAVE_LEN = 3


def patch_event_handler(class_bytes):
    entries, rest_off, minor, major, old_count = parse_cp(class_bytes)
    # Add MorphHandGuard refs
    u_owner = add_utf8(entries, "com/questforge/MorphHandGuard")
    c_owner = add_class(entries, u_owner)
    u_skip = add_utf8(entries, "shouldSkip")
    u_bool = add_utf8(entries, "()Z")
    n_skip = add_nat(entries, u_skip, u_bool)
    m_skip = add_methodref(entries, c_owner, n_skip)
    u_enter = add_utf8(entries, "enter")
    u_void = add_utf8(entries, "()V")
    n_enter = add_nat(entries, u_enter, u_void)
    m_enter = add_methodref(entries, c_owner, n_enter)
    u_leave = add_utf8(entries, "leave")
    n_leave = add_nat(entries, u_leave, u_void)
    m_leave = add_methodref(entries, c_owner, n_leave)

    new_count = len(entries)
    # rebuild header + cp
    head = struct.pack(">IHHH", 0xCAFEBABE, minor, major, new_count)
    cp_blob = b"".join(e for e in entries[1:] if e is not None)

    rest = class_bytes[rest_off:]
    off = 0
    access, off = _u2(rest, off)
    this, off = _u2(rest, off)
    super_, off = _u2(rest, off)
    ifc_n, off = _u2(rest, off)
    ifaces = rest[off : off + 2 * ifc_n]
    off += 2 * ifc_n
    fields_n, off = _u2(rest, off)

    def skip_member(o):
        _a, _n, _d, ac = struct.unpack_from(">HHHH", rest, o)
        o += 8
        attrs = []
        for _ in range(ac):
            ni, ln = struct.unpack_from(">HI", rest, o)
            attrs.append((ni, rest[o + 6 : o + 6 + ln]))
            o += 6 + ln
        return o, (_a, _n, _d, attrs)

    fields = []
    for _ in range(fields_n):
        off, mem = skip_member(off)
        fields.append(mem)

    methods_n, off = _u2(rest, off)
    methods = []
    patched = False
    for _ in range(methods_n):
        off, mem = skip_member(off)
        acc, name_i, desc_i, attrs = mem
        name = cp_utf8(entries, name_i)
        desc = cp_utf8(entries, desc_i)
        if name == "onRenderHand":
            new_attrs = []
            for ni, abody in attrs:
                aname = cp_utf8(entries, ni)
                if aname == "Code":
                    new_attrs.append((ni, patch_code(abody, entries, m_skip, m_enter, m_leave)))
                    patched = True
                else:
                    new_attrs.append((ni, abody))
            methods.append((acc, name_i, desc_i, new_attrs))
        else:
            methods.append(mem)
    if not patched:
        raise RuntimeError("onRenderHand Code attribute not found")

    class_attrs_n, off = _u2(rest, off)
    class_attrs = []
    for _ in range(class_attrs_n):
        ni, ln = struct.unpack_from(">HI", rest, off)
        class_attrs.append((ni, rest[off + 6 : off + 6 + ln]))
        off += 6 + ln

    out = BytesIO()
    out.write(head)
    out.write(cp_blob)
    out.write(struct.pack(">HHHH", access, this, super_, ifc_n))
    out.write(ifaces)
    out.write(struct.pack(">H", len(fields)))
    for acc, ni, di, attrs in fields:
        out.write(struct.pack(">HHHH", acc, ni, di, len(attrs)))
        for ani, ab in attrs:
            out.write(struct.pack(">HI", ani, len(ab)))
            out.write(ab)
    out.write(struct.pack(">H", len(methods)))
    for acc, ni, di, attrs in methods:
        out.write(struct.pack(">HHHH", acc, ni, di, len(attrs)))
        for ani, ab in attrs:
            out.write(struct.pack(">HI", ani, len(ab)))
            out.write(ab)
    out.write(struct.pack(">H", len(class_attrs)))
    for ani, ab in class_attrs:
        out.write(struct.pack(">HI", ani, len(ab)))
        out.write(ab)
    return out.getvalue()


def patch_code(code_attr, entries, m_skip, m_enter, m_leave):
    max_stack, max_locals, code, excs, attrs = parse_code_attr(code_attr)

    # Prefix: if (shouldSkip()) return; enter();
    #   invokestatic shouldSkip()Z
    #   ifeq +4          ; 3-byte ifeq, offset 4 -> next insn after return
    #   return
    #   invokestatic enter()V
    prefix = (
        struct.pack(">BH", 0xB8, m_skip)
        + struct.pack(">Bh", 0x99, 4)
        + bytes([0xB1])
        + struct.pack(">BH", 0xB8, m_enter)
    )
    assert len(prefix) == PREFIX_LEN

    # Find original RETURN / ATHROW pcs so we can insert leave() before them.
    # After prefix, those pcs shift by PREFIX_LEN, then each earlier leave adds 3.
    orig_exits = []
    for pc, op, ln in walk_code(code):
        if op in (0xB1, 0xAC, 0xAD, 0xAE, 0xAF, 0xB0, 0xBF):
            orig_exits.append(pc)
    if not orig_exits:
        raise RuntimeError("no return in onRenderHand")

    # Build new code: prefix + original with leave() before each exit
    leave_insn = struct.pack(">BH", 0xB8, m_leave)
    pieces = [prefix]
    last = 0
    extra = 0
    shifted_exits = []
    for pc in orig_exits:
        pieces.append(code[last:pc])
        pieces.append(leave_insn)
        shifted_exits.append(PREFIX_LEN + pc + extra)
        extra += LEAVE_LEN
        last = pc
    pieces.append(code[last:])
    new_code = b"".join(pieces)
    inserted_total = PREFIX_LEN + LEAVE_LEN * len(orig_exits)

    def map_pc(p):
        # prefix at 0, then leave() before each original exit
        bump = PREFIX_LEN
        for ep in orig_exits:
            if p > ep:
                bump += LEAVE_LEN
            elif p == ep:
                bump += LEAVE_LEN  # the original insn moves after leave
        return p + bump

    new_excs = []
    for start, end, handler, catch in excs:
        new_excs.append([map_pc(start), map_pc(end), map_pc(handler), catch])

    # Attribute name indices still valid (we only appended CP entries).
    # Drop StackMapTable: TEST-LAUNCH.bat already passes
    # -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier, and a rewritten
    # frame table is the easiest way to get a VerifyError. Line numbers
    # stay so crash stacks still point at onRenderHand.
    new_attrs = []
    for ni, abody in attrs:
        aname = cp_utf8(entries, ni)
        if aname == "StackMapTable":
            print("  dropped StackMapTable from onRenderHand (old verifier failover)")
            continue
        elif aname == "LineNumberTable":
            ln = abody
            ln = shift_line_numbers(ln, 0, PREFIX_LEN)
            for ep in reversed(orig_exits):
                ln = shift_line_numbers(ln, PREFIX_LEN + ep, LEAVE_LEN)
            new_attrs.append((ni, ln))
        elif aname in ("LocalVariableTable", "LocalVariableTypeTable"):
            lv = abody
            lv = shift_local_vars(lv, 0, PREFIX_LEN)
            for ep in reversed(orig_exits):
                lv = shift_local_vars(lv, PREFIX_LEN + ep, LEAVE_LEN)
            new_attrs.append((ni, lv))
        else:
            new_attrs.append((ni, abody))

    if max_stack < 1:
        max_stack = 1
    print(
        "  patched onRenderHand: code %s -> %s, exits=%s, prefix=%s"
        % (len(code), len(new_code), orig_exits, PREFIX_LEN)
    )
    return build_code_attr(max_stack, max_locals, new_code, new_excs, new_attrs)


def verify_nops(zbytes, name, expect):
    n = zbytes.count(bytes([0x57, 0x00, 0x00]))
    print("  %s pop-nop count: %s (expect %s)" % (name, n, expect))
    if n < expect:
        print("  WARNING: display-list NOPs missing on %s" % name)


def main():
    if not SRC_JAR.is_file():
        raise SystemExit("source Morph jar missing: %s" % SRC_JAR)

    print("Source:", SRC_JAR)
    print("Output:", OUT_JAR)

    with zipfile.ZipFile(SRC_JAR, "r") as zin:
        helper = zin.read("morph/client/model/ModelHelper.class")
        model = zin.read("morph/client/model/ModelMorph.class")
        handler = zin.read("morph/common/core/EventHandler.class")
        verify_nops(helper, "ModelHelper", 2)
        verify_nops(model, "ModelMorph", 1)

        guard = build_hand_guard_class()
        if guard[:4] != b"\xca\xfe\xba\xbe":
            raise RuntimeError("guard class magic")
        print("  MorphHandGuard.class %s bytes" % len(guard))

        patched = patch_event_handler(handler)
        print("  EventHandler.class %s -> %s bytes" % (len(handler), len(patched)))

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "morph/common/core/EventHandler.class":
                    data = patched
                zout.writestr(info, data)
            zout.writestr("com/questforge/MorphHandGuard.class", guard)

    OUT_JAR.write_bytes(buf.getvalue())
    print("Wrote", OUT_JAR, OUT_JAR.stat().st_size, "bytes")
    print("Live mods\\ was NOT touched. Morph stays disabled until the owner copies this jar.")


if __name__ == "__main__":
    main()
