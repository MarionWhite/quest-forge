"""Make the install icons for the items index (site/items/).

Reads pack/resourcepack/pack.png (256x256, 8-bit RGBA, non-interlaced pixel art) and writes:

- site/items/icon-512.png: an exact 2x nearest-neighbour upscale, done in pure Python
  (zlib + struct), so every pixel stays a hard square. sips would blur it.
- site/items/icon-192.png: a resize with macOS sips (sips -z 192 192).

Run from anywhere:  python3 -I tools/site/make_pwa_icons.py
"""

import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "pack" / "resourcepack" / "pack.png"
OUT_DIR = ROOT / "site" / "items"
BPP = 4  # RGBA, 8 bits per channel


def read_png(path):
    """Decode an 8-bit RGBA, non-interlaced PNG into (width, height, rows of bytes)."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path} is not a PNG")
    pos, idat, w, h = 8, [], 0, 0
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, ctype, interlace) != (8, 6, 0):
                raise SystemExit("expected 8-bit RGBA, non-interlaced PNG")
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(b"".join(idat))
    stride = w * BPP
    rows, prev, p = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for x in range(stride):
            a = line[x - BPP] if x >= BPP else 0  # left, already reconstructed
            b = prev[x]                           # up
            c = prev[x - BPP] if x >= BPP else 0  # up-left
            if f == 0:
                continue
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pred) & 255
            else:
                raise SystemExit(f"unknown filter type {f}")
        rows.append(bytes(line))
        prev = line
    return w, h, rows


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def write_png(path, w, h, rows):
    """Write RGBA rows with filter type 0 on every scanline."""
    raw = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def upscale2x(rows):
    """Duplicate every pixel horizontally and every row vertically."""
    out = []
    for row in rows:
        wide = bytearray()
        for i in range(0, len(row), BPP):
            px = row[i:i + BPP]
            wide += px + px
        out.append(bytes(wide))
        out.append(bytes(wide))
    return out


def main():
    w, h, rows = read_png(SRC)
    if (w, h) != (256, 256):
        raise SystemExit(f"expected 256x256 source, got {w}x{h}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out512 = OUT_DIR / "icon-512.png"
    write_png(out512, w * 2, h * 2, upscale2x(rows))
    out192 = OUT_DIR / "icon-192.png"
    subprocess.run(["sips", "-z", "192", "192", str(SRC), "--out", str(out192)], check=True,
                   stdout=subprocess.DEVNULL)
    print(f"wrote {out192}")
    print(f"wrote {out512}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
