#!/usr/bin/env python3
"""Count every block in a world's region files, by dimension, height and biome.

WHY THIS EXISTS. The previous ore survey counted blocks inside the running game
and wrote out totals. That put the analysis inside the measurement: every new
question -- per biome? per depth? a different definition of "ore"? -- meant
another twenty-minute generation run, and another chance for a bug in the
counting logic to go unnoticed. Worse, the two instruments it used overlapped on
only 17 of 213 blocks, so the cross-check they were supposed to give each other
was mostly not happening.

This reads finished worlds off disk instead. The region files are the game's own
output, they are kept, and they can be re-scanned in seconds when the question
changes. Nothing here models anything: it opens chunks and counts what is in
them. That is the whole design.

WHAT IT PRODUCES, per dimension:
  - blocks per chunk for every block type, split by Y level
  - the biome each column belongs to, so rates can be given per biome
  - the number of populated chunks, which is the denominator for all of it

Only chunks with TerrainPopulated=1 are counted. An unpopulated chunk has its
terrain but not its ores -- population is where WorldGenMinable runs -- so
counting one would silently dilute every rate.

Block IDs are per-world. Forge assigns them at world creation and records the
mapping in level.dat under FML/ItemData, so the names come from the save being
scanned rather than from any assumption about load order.

Usage:
    scan_regions.py <save-dir> [-o out.json] [--dim N] [--no-biomes]
"""
import argparse, collections, gzip, io, json, os, struct, sys, zlib

# ---------------------------------------------------------------- NBT

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG = 0, 1, 2, 3, 4
TAG_FLOAT, TAG_DOUBLE, TAG_BYTE_ARRAY, TAG_STRING = 5, 6, 7, 8
TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY = 9, 10, 11


def _read(f, tag):
    if tag == TAG_BYTE:   return struct.unpack(">b", f.read(1))[0]
    if tag == TAG_SHORT:  return struct.unpack(">h", f.read(2))[0]
    if tag == TAG_INT:    return struct.unpack(">i", f.read(4))[0]
    if tag == TAG_LONG:   return struct.unpack(">q", f.read(8))[0]
    if tag == TAG_FLOAT:  return struct.unpack(">f", f.read(4))[0]
    if tag == TAG_DOUBLE: return struct.unpack(">d", f.read(8))[0]
    if tag == TAG_BYTE_ARRAY:
        return f.read(struct.unpack(">i", f.read(4))[0])
    if tag == TAG_STRING:
        return f.read(struct.unpack(">H", f.read(2))[0]).decode("utf-8", "replace")
    if tag == TAG_LIST:
        item = struct.unpack(">b", f.read(1))[0]
        n = struct.unpack(">i", f.read(4))[0]
        return [_read(f, item) for _ in range(n)]
    if tag == TAG_COMPOUND:
        out = {}
        while True:
            t = f.read(1)
            if not t or t[0] == TAG_END:
                break
            ln = struct.unpack(">H", f.read(2))[0]
            # The name must be read into a variable before the value. Written as
            # out[f.read(ln)...] = _read(...) Python evaluates the right-hand
            # side first, so the value would be consumed from where the name
            # should start and every member after it lands at the wrong offset.
            name = f.read(ln).decode("utf-8", "replace")
            out[name] = _read(f, t[0])
        return out
    if tag == TAG_INT_ARRAY:
        n = struct.unpack(">i", f.read(4))[0]
        return list(struct.unpack(">%di" % n, f.read(4 * n)))
    raise ValueError("unknown NBT tag %d" % tag)


def nbt_parse(data):
    f = io.BytesIO(data)
    if f.read(1)[0] != TAG_COMPOUND:
        raise ValueError("root tag is not a compound")
    f.read(struct.unpack(">H", f.read(2))[0])
    return _read(f, TAG_COMPOUND)


def nbt_file(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return nbt_parse(raw)


# ------------------------------------------------------- block id -> name

def block_names(save_dir):
    """blockId -> 'modid:name', from the save's own Forge registry.

    IDs are assigned per world, so this has to come from the save being scanned.
    FML/ItemData holds one entry per registered block and item; blocks carry a
    \\x01 prefix and items \\x02, and the same numeric id can appear as both.
    Only the block entries matter here.

    Entries are retained for mods that have since been removed, which is a
    feature: a world generated with a mod that is now gone still names its
    blocks correctly instead of reporting them as unknown.
    """
    level = os.path.join(save_dir, "level.dat")
    if not os.path.exists(level):
        return {}
    try:
        root = nbt_file(level)
    except Exception as e:
        print("warning: could not read level.dat (%s)" % e, file=sys.stderr)
        return {}
    out = {}
    for entry in root.get("FML", {}).get("ItemData", []):
        key = entry.get("K", "")
        if key[:1] == "\x01":
            out[entry["V"]] = key[1:]
    return out


# ---------------------------------------------------------------- Anvil

def region_chunks(path):
    """Yield each stored chunk's Level compound from one .mca file.

    Anvil layout: a 4 KiB header of 1024 big-endian entries, three bytes of
    offset in 4 KiB sectors and one byte of length, then a 4 KiB timestamp
    table, then the chunks. Offset zero means the chunk was never written.
    """
    try:
        f = open(path, "rb")
    except OSError:
        return
    with f:
        header = f.read(4096)
        if len(header) < 4096:
            return
        for i in range(1024):
            packed = struct.unpack(">I", header[i * 4:i * 4 + 4])[0]
            offset = packed >> 8
            if not offset:
                continue
            try:
                f.seek(offset * 4096)
                head = f.read(5)
                if len(head) < 5:
                    continue
                length, scheme = struct.unpack(">IB", head)
                payload = f.read(length - 1)
                if scheme == 1:
                    payload = gzip.decompress(payload)
                elif scheme == 2:
                    payload = zlib.decompress(payload)
                else:
                    continue
                yield nbt_parse(payload).get("Level", {})
            except Exception:
                # A corrupt chunk is not worth losing the rest of the region for.
                continue


def nibble(arr, i):
    """The i-th 4-bit value of a packed nibble array (low nibble first)."""
    b = arr[i >> 1]
    return (b & 0x0F) if (i & 1) == 0 else (b >> 4)


def scan_chunk(level, counts, biome_counts, want_biomes):
    """Add one chunk's blocks to the running totals.

    Sections are 16x16x16 and only exist where the column is non-empty, so a
    missing section is genuinely all air and contributes nothing. Block ids
    above 255 live in the optional Add nibble array; ignoring it would silently
    misreport every modded block, which in this pack is most of them.

    Keyed by (id << 4) | meta, matching how the game addresses a block state.
    """
    biomes = level.get("Biomes")
    for section in level.get("Sections", []):
        base_y = section.get("Y", 0) * 16
        blocks = section.get("Blocks")
        if not blocks:
            continue
        add = section.get("Add")
        data = section.get("Data")
        for i, raw in enumerate(blocks):
            bid = raw
            if add:
                bid |= nibble(add, i) << 8
            if bid == 0:
                continue
            meta = nibble(data, i) if data else 0
            y = base_y + (i >> 8)
            key = (bid << 4) | meta
            counts[key][y] += 1
            if want_biomes and biomes:
                # Biomes are one byte per column, indexed x + z*16; within a
                # section index i the low eight bits are exactly that column.
                b = biomes[i & 0xFF]
                biome_counts[key][b & 0xFF] += 1


def dimension_of(path, save_dir):
    """Dimension id from the region file's path. Overworld has no DIMn folder."""
    rel = os.path.relpath(path, save_dir)
    for part in rel.split(os.sep):
        if part.startswith("DIM"):
            try:
                return int(part[3:])
            except ValueError:
                pass
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("save", help="world save directory (the one holding level.dat)")
    ap.add_argument("-o", "--out", default="region-scan.json")
    ap.add_argument("--dim", type=int, action="append",
                    help="restrict to this dimension; repeatable")
    ap.add_argument("--no-biomes", action="store_true",
                    help="skip per-biome tallies (faster, smaller output)")
    args = ap.parse_args()

    if not os.path.isdir(args.save):
        sys.exit("not a directory: %s" % args.save)

    names = block_names(args.save)
    print("block registry: %d blocks" % len(names))

    regions = []
    for dirpath, _, files in os.walk(args.save):
        for fn in files:
            if fn.endswith(".mca"):
                regions.append(os.path.join(dirpath, fn))
    if args.dim is not None:
        keep = set(args.dim)
        regions = [p for p in regions if dimension_of(p, args.save) in keep]
    print("region files: %d" % len(regions))

    # dim -> key -> y -> count,  and dim -> key -> biome -> count
    per_dim = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    per_biome = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    populated = collections.Counter()
    skipped = collections.Counter()

    for n, path in enumerate(sorted(regions), 1):
        dim = dimension_of(path, args.save)
        for level in region_chunks(path):
            # Population is when ores are placed. Counting a chunk that has
            # terrain but has not been populated would dilute every rate.
            if not level.get("TerrainPopulated"):
                skipped[dim] += 1
                continue
            populated[dim] += 1
            scan_chunk(level, per_dim[dim], per_biome[dim], not args.no_biomes)
        if n % 25 == 0 or n == len(regions):
            print("  %d/%d regions, %d populated chunks"
                  % (n, len(regions), sum(populated.values())))

    out = {
        "save": os.path.abspath(args.save),
        "populated_chunks": dict(populated),
        "unpopulated_skipped": dict(skipped),
        "block_names": {str(k): v for k, v in names.items()},
        "dimensions": {},
    }
    for dim, keys in per_dim.items():
        rows = {}
        for key, ys in keys.items():
            bid, meta = key >> 4, key & 15
            rows[str(key)] = {
                "block": names.get(bid, "id:%d" % bid),
                "id": bid,
                "meta": meta,
                "total": sum(ys.values()),
                "by_y": {str(y): c for y, c in sorted(ys.items())},
            }
            if not args.no_biomes and per_biome[dim].get(key):
                rows[str(key)]["by_biome"] = {
                    str(b): c for b, c in sorted(per_biome[dim][key].items())}
        out["dimensions"][str(dim)] = rows

    with open(args.out, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("wrote %s (%.1f MB)" % (args.out, os.path.getsize(args.out) / 1e6))
    print("populated chunks by dimension:")
    for dim, n in sorted(populated.items()):
        print("  dim %-5d %8d  (%d unpopulated skipped)" % (dim, n, skipped.get(dim, 0)))


if __name__ == "__main__":
    main()
