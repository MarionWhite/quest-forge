#!/usr/bin/env python3
"""Build the one shipping zip, "QF Textures": QF v0 (vanilla designs, Faithful 32x where chosen,
calmer grass, vibrance, connected glass, LabPBR maps) merged with the modded v1 output (ores on
Faithful stone, Faithful backports, modded connected textures, emissive maps).

    py -3.10 -I tools/textures/build_ship.py --out C:\\qfb\\textures\\QFTextures.zip

Runs tools/textures/build_qf_textures.py and build_modded_textures.py into a work folder next to
--out, then merges: one pack.mcmeta (resourcepacks/QFTextures/pack.mcmeta, the shipping
description), one CREDITS.txt (v0's hand-written credits, then v1's generated per-file records),
LICENSE-Faithful.txt once, and every other member of both zips. The two builds share no member
path (v0 is the minecraft domain and Faithful's glass CTM, v1 the mod domains and mcpatcher/ctm/qf),
which the merge asserts. Prints the size and sha256 for docs/design/textures/direction.md.

Decision 0006: the zip ships with the pack (build_client_release.py --textures) and the client
profiles select it. The repo never holds the zip: it carries vanilla's and the mods' pixels.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "resourcepacks", "QFTextures")
SHARED = {"pack.mcmeta", "CREDITS.txt", "LICENSE-Faithful.txt"}


def run(script, *args):
    cmd = [sys.executable, "-I", os.path.join(HERE, script)] + list(args)
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=r"C:\qfb\textures\QFTextures.zip")
    ap.add_argument("--only", default=r"C:\qfb\textures\top-modded.txt", help="the modded build's map list")
    ap.add_argument("--work", help="folder for the two intermediate zips (default: <out dir>\\_ship)")
    ap.add_argument("--keep-parts", action="store_true", help="leave the intermediate zips in --work")
    ap.add_argument("--skip-build", action="store_true", help="merge the intermediate zips already in --work")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    work = a.work or os.path.join(os.path.dirname(out), "_ship")
    os.makedirs(work, exist_ok=True)
    v0, v1 = os.path.join(work, "QFTextures-v0.zip"), os.path.join(work, "QFTextures-modded-v1.zip")
    if not a.skip_build:
        run("build_qf_textures.py", "--out", v0)
        run("build_modded_textures.py", "--out", v1, "--only", a.only)

    za, zb = zipfile.ZipFile(v0), zipfile.ZipFile(v1)
    na, nb = set(za.namelist()), set(zb.namelist())
    clash = (na & nb) - SHARED
    if clash:
        sys.exit("the two builds both write %d members, e.g. %s" % (len(clash), sorted(clash)[:5]))
    meta = json.load(open(os.path.join(SRC, "pack.mcmeta"), encoding="utf-8"))
    meta["pack"]["description"] = ("Quest Forge Textures. Vanilla designs with Faithful 32x (faithfulpack.net) detail, "
                                   "connected glass, modded ores on Faithful stone, LabPBR maps. Credits inside.")
    credits = za.read("CREDITS.txt").decode("utf-8").rstrip() + "\n\n" + zb.read("CREDITS.txt").decode("utf-8")
    tmp = out + ".building"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps(meta, indent=1, ensure_ascii=False))
        z.writestr("CREDITS.txt", credits)
        z.writestr("LICENSE-Faithful.txt", za.read("LICENSE-Faithful.txt"))
        n = 0
        for src, names in ((za, na), (zb, nb)):
            for m in sorted(names):
                if m in SHARED or m.endswith("/"):
                    continue
                z.writestr(m, src.read(m))
                n += 1
    os.replace(tmp, out)
    if not a.keep_parts:
        za.close(), zb.close()
        for p in (v0, v1):
            os.remove(p)
    size = os.path.getsize(out)
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print("QF Textures: %d members (+ pack.mcmeta, CREDITS.txt, LICENSE-Faithful.txt) -> %s" % (n, out))
    print("size %d bytes (%.1f MB)  sha256 %s" % (size, size / 1e6, sha))


if __name__ == "__main__":
    main()
