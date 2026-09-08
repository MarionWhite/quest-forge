# -*- coding: utf-8 -*-
"""Raise is already done in cfg. Patch SplashProgress pulse + strengthen emblem bloom + rewrite Forge jar."""
from __future__ import print_function

import math
import os
import shutil
import struct
import time
import zipfile
from pathlib import Path

from PIL import Image, ImageFilter

INST = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4")
JAR = INST / "bin" / "lib" / "forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
WORK = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_emblem-pulse")
EMBLEM = INST / "resources" / "assets" / "minecraft" / "textures" / "gui" / "title" / "emblem_corner.png"
SP_INNER = "cpw/mods/fml/client/SplashProgress.class"
TEX_INNER = "cpw/mods/fml/client/SplashProgress$Texture.class"
PERIOD_MS = 2500.0
PULSE_MID = 0.775
PULSE_AMP = 0.225
OMEGA = 2.0 * math.pi / PERIOD_MS  # sin(t*omega) period 2.5s


# ---------- classfile ----------
def _u2(n):
    return struct.pack(">H", n)


def _u4(n):
    return struct.pack(">I", n)


class ClassFile(object):
    def __init__(self, data):
        self.magic_minor_major = data[:8]
        cp_count = struct.unpack(">H", data[8:10])[0]
        i = 10
        self.cp = [None]  # 1-based
        while len(self.cp) < cp_count:
            tag = data[i]
            if tag == 1:
                ln = struct.unpack(">H", data[i + 1 : i + 3])[0]
                self.cp.append(data[i : i + 3 + ln])
                i += 3 + ln
            elif tag in (7, 8, 16):
                self.cp.append(data[i : i + 3])
                i += 3
            elif tag in (3, 4, 9, 10, 11, 12, 18):
                self.cp.append(data[i : i + 5])
                i += 5
            elif tag in (5, 6):
                self.cp.append(data[i : i + 9])
                self.cp.append(None)
                i += 9
            elif tag == 15:
                self.cp.append(data[i : i + 4])
                i += 4
            else:
                raise RuntimeError("bad cp tag %s at %s" % (tag, i))
        self.rest = bytearray(data[i:])

    def cp_count(self):
        return len(self.cp)

    def utf(self, idx):
        e = self.cp[idx]
        if e is None or e[0] != 1:
            return None
        ln = struct.unpack(">H", e[1:3])[0]
        return e[3 : 3 + ln].decode("utf-8")

    def find_utf8(self, s):
        raw = s.encode("utf-8")
        for i, e in enumerate(self.cp):
            if e and e[0] == 1:
                ln = struct.unpack(">H", e[1:3])[0]
                if e[3 : 3 + ln] == raw:
                    return i
        return None

    def add_utf8(self, s):
        existing = self.find_utf8(s)
        if existing:
            return existing
        raw = s.encode("utf-8")
        self.cp.append(bytes([1]) + _u2(len(raw)) + raw)
        return len(self.cp) - 1

    def add_class(self, name):
        ni = self.add_utf8(name)
        self.cp.append(bytes([7]) + _u2(ni))
        return len(self.cp) - 1

    def add_nat(self, name, desc):
        self.cp.append(bytes([12]) + _u2(self.add_utf8(name)) + _u2(self.add_utf8(desc)))
        return len(self.cp) - 1

    def add_methodref(self, cls_idx, name, desc):
        self.cp.append(bytes([10]) + _u2(cls_idx) + _u2(self.add_nat(name, desc)))
        return len(self.cp) - 1

    def add_float(self, v):
        self.cp.append(bytes([4]) + struct.pack(">f", v))
        return len(self.cp) - 1

    def add_double(self, v):
        self.cp.append(bytes([6]) + struct.pack(">d", v))
        self.cp.append(None)
        return len(self.cp) - 2

    def find_class(self, name):
        want = self.find_utf8(name)
        if not want:
            return None
        for i, e in enumerate(self.cp):
            if e and e[0] == 7 and struct.unpack(">H", e[1:3])[0] == want:
                return i
        return None

    def find_fieldref(self, cls_name, field, desc):
        cls = self.find_class(cls_name)
        fn = self.find_utf8(field)
        fd = self.find_utf8(desc)
        if not (cls and fn and fd):
            return None
        nat = None
        for i, e in enumerate(self.cp):
            if e and e[0] == 12:
                n, d = struct.unpack(">HH", e[1:5])
                if n == fn and d == fd:
                    nat = i
                    break
        if not nat:
            return None
        for i, e in enumerate(self.cp):
            if e and e[0] == 9:
                c, n = struct.unpack(">HH", e[1:5])
                if c == cls and n == nat:
                    return i
        return None

    def find_methodref(self, cls_name, name, desc):
        cls = self.find_class(cls_name)
        mn = self.find_utf8(name)
        md = self.find_utf8(desc)
        if not (cls and mn and md):
            return None
        nat = None
        for i, e in enumerate(self.cp):
            if e and e[0] == 12:
                n, d = struct.unpack(">HH", e[1:5])
                if n == mn and d == md:
                    nat = i
                    break
        if not nat:
            return None
        for i, e in enumerate(self.cp):
            if e and e[0] == 10:
                c, n = struct.unpack(">HH", e[1:5])
                if c == cls and n == nat:
                    return i
        return None

    def _split_rest(self):
        r = self.rest
        i = 0
        access = struct.unpack(">H", r[i : i + 2])[0]
        i += 2
        this = struct.unpack(">H", r[i : i + 2])[0]
        i += 2
        sup = struct.unpack(">H", r[i : i + 2])[0]
        i += 2
        ic = struct.unpack(">H", r[i : i + 2])[0]
        i += 2 + 2 * ic
        fc = struct.unpack(">H", r[i : i + 2])[0]
        i += 2
        for _ in range(fc):
            i += 6
            ac = struct.unpack(">H", r[i : i + 2])[0]
            i += 2
            for _a in range(ac):
                i += 2
                al = struct.unpack(">I", r[i : i + 4])[0]
                i += 4 + al
        fields_end = i
        mc = struct.unpack(">H", r[i : i + 2])[0]
        i += 2
        methods = []
        for _ in range(mc):
            start = i
            i += 6
            ac = struct.unpack(">H", r[i : i + 2])[0]
            i += 2
            for _a in range(ac):
                i += 2
                al = struct.unpack(">I", r[i : i + 4])[0]
                i += 4 + al
            methods.append(bytearray(r[start:i]))
        methods_end = i
        return r[:fields_end], methods, r[methods_end:]

    def method_name_desc(self, method_bytes):
        mn = struct.unpack(">H", method_bytes[2:4])[0]
        md = struct.unpack(">H", method_bytes[4:6])[0]
        return self.utf(mn), self.utf(md)

    def replace_method_code(self, name, desc, max_stack, max_locals, code, extra_attrs=b""):
        head, methods, tail = self._split_rest()
        code_name = self.find_utf8("Code")
        if not code_name:
            raise RuntimeError("no Code utf8")
        found = False
        new_methods = []
        for m in methods:
            mn, md = self.method_name_desc(m)
            if mn == name and md == desc:
                access = m[0:6]  # flags + name + desc
                # rebuild: 1 attribute = Code
                body = _u2(max_stack) + _u2(max_locals) + _u4(len(code)) + code
                body += _u2(0)  # no exceptions
                # extra_attrs is already u2 count + attrs, or empty meaning 0 attrs
                if extra_attrs:
                    body += extra_attrs
                else:
                    body += _u2(0)
                code_attr = _u2(code_name) + _u4(len(body)) + body
                m = bytearray(access + _u2(1) + code_attr)
                found = True
            new_methods.append(m)
        if not found:
            raise RuntimeError("method %s%s not found" % (name, desc))
        self.rest = bytearray(head + _u2(len(new_methods)) + b"".join(new_methods) + tail)

    def add_method(self, access, name_idx, desc_idx, code_attr_bytes):
        head, methods, tail = self._split_rest()
        method = _u2(access) + _u2(name_idx) + _u2(desc_idx) + _u2(1) + code_attr_bytes
        methods.append(bytearray(method))
        self.rest = bytearray(head + _u2(len(methods)) + b"".join(methods) + tail)

    def to_bytes(self):
        out = bytearray(self.magic_minor_major)
        out += _u2(len(self.cp))
        for e in self.cp:
            if e is None:
                continue
            out += e
        out += self.rest
        return bytes(out)


def stackmap_same(offset):
    """First frame at bytecode offset `offset` with same locals, empty stack."""
    # previous_offset = -1; offset = -1 + delta + 1 => delta = offset
    delta = offset
    if delta <= 63:
        body = bytes([delta])
    else:
        body = bytes([251]) + _u2(delta)
    return body


# ---------- patches ----------
def patch_splashprogress(data):
    cf = ClassFile(data)
    ints = []
    for e in cf.cp:
        if e and e[0] == 3:
            ints.append(struct.unpack(">i", e[1:5])[0])
    if 16777216 not in ints:
        raise SystemExit("SplashProgress missing IntBuffer 16777216; ints=%s" % ints)

    sys_cls = cf.find_class("java/lang/System")
    gl_cls = cf.find_class("org/lwjgl/opengl/GL11")
    forge_field = cf.find_fieldref(
        "cpw/mods/fml/client/SplashProgress",
        "forgeTexture",
        "Lcpw/mods/fml/client/SplashProgress$Texture;",
    )
    if not (sys_cls and gl_cls and forge_field):
        raise SystemExit("missing System/GL11/forgeTexture refs")

    millis = cf.add_methodref(sys_cls, "currentTimeMillis", "()J")
    math_cls = cf.add_class("java/lang/Math")
    sin = cf.add_methodref(math_cls, "sin", "(D)D")
    glcolor = cf.add_methodref(gl_cls, "glColor4f", "(FFFF)V")
    omega = cf.add_double(OMEGA)
    amp = cf.add_float(PULSE_AMP)
    mid = cf.add_float(PULSE_MID)
    name_i = cf.add_utf8("pulseIfForge")
    desc_i = cf.add_utf8("(Lcpw/mods/fml/client/SplashProgress$Texture;)V")
    # methodref for Texture.bind to call — created in Texture class, not here

    def u2b(idx):
        return _u2(idx)

    code = bytearray()
    # aload_0
    code += b"\x2a"
    # getstatic forgeTexture
    code += b"\xb2" + u2b(forge_field)
    # if_acmpne skip (placeholder)
    if_pos = len(code)
    code += b"\xa6\x00\x00"
    # currentTimeMillis
    code += b"\xb8" + u2b(millis)
    code += b"\x8a"  # l2d
    code += b"\x14" + u2b(omega)  # ldc2_w
    code += b"\x6b"  # dmul
    code += b"\xb8" + u2b(sin)
    code += b"\x90"  # d2f
    code += b"\x13" + u2b(amp)  # ldc_w
    code += b"\x6a"  # fmul
    code += b"\x13" + u2b(mid)
    code += b"\x62"  # fadd
    code += b"\x59\x59\x0c"  # dup dup fconst_1
    code += b"\xb8" + u2b(glcolor)
    skip = len(code)
    code += b"\xb1"  # return
    branch = skip - if_pos
    code[if_pos + 1 : if_pos + 3] = _u2(branch)

    sm_name = cf.find_utf8("StackMapTable")
    sm_body = _u2(1) + stackmap_same(skip)
    extra = _u2(1) + _u2(sm_name) + _u4(len(sm_body)) + sm_body

    code_name = cf.find_utf8("Code")
    body = _u2(4) + _u2(1) + _u4(len(code)) + bytes(code) + _u2(0) + extra
    code_attr = _u2(code_name) + _u4(len(body)) + body
    cf.add_method(0x0009, name_i, desc_i, code_attr)  # public static

    out = cf.to_bytes()
    print(
        "SplashProgress pulseIfForge skip=%s branch=%s omega=%s amp=%s mid=%s millis=%s sin=%s glc=%s size %s->%s"
        % (skip, branch, omega, amp, mid, millis, sin, glcolor, len(data), len(out))
    )
    return out


def patch_texture(data):
    cf = ClassFile(data)
    sp_cls = cf.find_class("cpw/mods/fml/client/SplashProgress")
    name_field = None
    # name fieldref already used in bind as #121
    pulse = cf.add_methodref(
        sp_cls,
        "pulseIfForge",
        "(Lcpw/mods/fml/client/SplashProgress$Texture;)V",
    )
    name_field = 121
    bind_tex = 125
    code = bytearray()
    code += b"\x2a"  # aload_0
    code += b"\xb8" + _u2(pulse)
    code += b"\x11\x0d\xe1"  # sipush 3553
    code += b"\x2a"
    code += b"\xb4" + _u2(name_field)
    code += b"\xb8" + _u2(bind_tex)
    code += b"\xb1"
    cf.replace_method_code("bind", "()V", 2, 1, bytes(code))
    out = cf.to_bytes()
    print("Texture.bind pulseIfForge=%s size %s->%s hex=%s" % (pulse, len(data), len(out), bytes(code).hex()))
    return out


def rewrite_jar(new_sp, new_tex):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = INST / ("_backup-emblem-pulse-%s" % stamp)
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(JAR, backup_dir / JAR.name)
    shutil.copy2(EMBLEM, backup_dir / "emblem_corner.png")
    spawn = INST / "config" / "lycanitesmobs" / "lycanitesmobs-spawning.cfg"
    shutil.copy2(spawn, backup_dir / "lycanitesmobs-spawning.cfg")
    print("backup", backup_dir)

    tmp = JAR.with_suffix(".jar.tmpqf")
    stripped = []
    with zipfile.ZipFile(JAR, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            name = item.filename.replace("\\", "/")
            if name.startswith("META-INF/") and name.upper().endswith((".SF", ".RSA", ".DSA")):
                stripped.append(name)
                continue
            if name == SP_INNER:
                data = new_sp
            elif name == TEX_INNER:
                data = new_tex
            else:
                data = zin.read(item.filename)
            zout.writestr(item, data)
    os.replace(str(tmp), str(JAR))
    print("wrote", JAR, JAR.stat().st_size, "stripped", stripped or "none")

    with zipfile.ZipFile(JAR, "r") as z:
        leftover = [
            n
            for n in z.namelist()
            if n.replace("\\", "/").startswith("META-INF/") and n.upper().endswith((".SF", ".RSA", ".DSA"))
        ]
        if leftover:
            raise SystemExit("signatures remain: %s" % leftover)
        sp = z.read(SP_INNER)
        tex = z.read(TEX_INNER)
    if b"pulseIfForge" not in sp or b"pulseIfForge" not in tex:
        raise SystemExit("pulseIfForge missing after jar write")
    # keep prior patches
    if struct.pack(">i", 16777216) not in sp:
        # Integer CP is tag 3 + big-endian int
        if b"\x03\x01\x00\x00\x00" not in sp:
            # 16777216 = 0x01000000
            pass
    cf = ClassFile(sp)
    ints = [struct.unpack(">i", e[1:5])[0] for e in cf.cp if e and e[0] == 3]
    if 16777216 not in ints:
        raise SystemExit("buffer size lost: %s" % ints)
    print("jar verify ok ints contain 16777216; META-INF signatures stripped")
    return backup_dir


def enhance_emblem():
    im = Image.open(EMBLEM).convert("RGBA")
    if im.size != (1024, 1024):
        raise SystemExit("emblem must stay 1024x1024, got %s" % (im.size,))
    px = im.load()
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gpx = glow.load()
    orange_n = 0
    for y in range(1024):
        for x in range(1024):
            r, g, b, a = px[x, y]
            if a > 24 and r >= 150 and r > g + 20 and g > b - 10:
                orange_n += 1
                nr = min(255, r + 22)
                ng = min(255, g + 10)
                nb = min(255, b + 4)
                px[x, y] = (nr, ng, nb, a)
                gpx[x, y] = (255, min(255, 90 + g // 2), 28, min(200, 70 + a // 3))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=3.6))
    # modest overlay so stone stays; bloom around gem/cracks lifts
    out = Image.alpha_composite(im, Image.blend(Image.new("RGBA", im.size, (0, 0, 0, 0)), glow, 0.42))
    opx = out.load()
    # white RGB under alpha 0; no dark square
    dark_square = 0
    for y in range(1024):
        for x in range(1024):
            r, g, b, a = opx[x, y]
            if a == 0:
                if (r, g, b) != (255, 255, 255):
                    dark_square += 1
                opx[x, y] = (255, 255, 255, 0)
    out.save(EMBLEM, "PNG")
    print("emblem bloom orange_pixels=%s cleared_transparent=%s saved %s" % (orange_n, dark_square, EMBLEM.stat().st_size))


def verify_logo_quad():
    with zipfile.ZipFile(JAR, "r") as z:
        data = z.read("cpw/mods/fml/client/SplashProgress$3.class")
    cf = ClassFile(data)
    floats = [struct.unpack(">f", e[1:5])[0] for e in cf.cp if e and e[0] == 4]
    print("SplashProgress$3 floats", floats)
    for need in (-1600.0, -840.0, 1320.0, 2240.0):
        if not any(abs(f - need) < 0.01 for f in floats):
            raise SystemExit("large logo quad missing %s" % need)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    enhance_emblem()
    with zipfile.ZipFile(JAR, "r") as z:
        sp = z.read(SP_INNER)
        tex = z.read(TEX_INNER)
    (WORK / "SplashProgress.class.before").write_bytes(sp)
    (WORK / "SplashProgress$Texture.class.before").write_bytes(tex)
    new_sp = patch_splashprogress(sp)
    new_tex = patch_texture(tex)
    (WORK / "SplashProgress.class").write_bytes(new_sp)
    (WORK / "SplashProgress$Texture.class").write_bytes(new_tex)
    rewrite_jar(new_sp, new_tex)
    verify_logo_quad()
    print("DONE pulse patch")


if __name__ == "__main__":
    main()
