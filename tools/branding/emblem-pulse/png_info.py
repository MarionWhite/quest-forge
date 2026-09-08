# -*- coding: utf-8 -*-
import struct
import zlib
from pathlib import Path

from PIL import Image


def chunks(path):
    data = Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    i = 8
    out = []
    while i < len(data):
        ln = struct.unpack(">I", data[i : i + 4])[0]
        typ = data[i + 4 : i + 8]
        out.append((typ.decode("ascii", "replace"), ln))
        i += 12 + ln
    return out


def stats(path, label):
    print("====", label, path)
    print("size", Path(path).stat().st_size, "chunks", chunks(path))
    im = Image.open(path)
    print("pil", im.size, im.mode, im.info)
    im = im.convert("RGBA")
    px = im.load()
    opa = 0
    a0 = 0
    a0_white = 0
    a0_black = 0
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = px[x, y]
            if a == 0:
                a0 += 1
                if (r, g, b) == (255, 255, 255):
                    a0_white += 1
                if (r, g, b) == (0, 0, 0):
                    a0_black += 1
            elif a > 10:
                opa += 1
    print("opaque>10", opa, "a0", a0, "a0_white", a0_white, "a0_black", a0_black)


cur = r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4\resources\assets\minecraft\textures\gui\title\emblem_corner.png"
bak = r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4\_backup-emblem-pulse-20260904-165159\emblem_corner.png"
stats(bak, "BACKUP")
stats(cur, "CURRENT")
