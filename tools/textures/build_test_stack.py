"""Merge the settled Shader Lab texture picks into ONE private resource pack for the owner's test copy.

    py -3.10 -I tools/textures/build_test_stack.py --out "C:/qfb/textures/test/QF Textures (settled picks).zip"

The packs are stacked bottom -> top exactly as the renderq jobs the owner judged stacked them (a later
pack's file replaces an earlier one's), then written as one zip:

  1. QF Textures, r016 build: Stay True leaves and crops (r011/r012), connected metals B (r013), frost
     gems (r015 E) and round 14's calmed look on Chisel's Simple Diamond / Smooth Emerald (r016).
  2. Round 12's packs set (r013 A): Patrix mobs, Faithless items/potions/books (CIT), lettered TNT,
     Soartex bookshelves, Conquest particles/weather/ambient sounds.
  3. Round 12's GUI set (r013 A): Faithless screens and creative tabs. Its gui/icons.png and
     gui/widgets.png are DROPPED: every HUD design was rejected, so the HUD stays as the live game's
     (vanilla icons, QuestForge.zip's widgets).
  4. Conquest's snow golem (r014 D).

The output holds copied pack art (Stay True, Faithless, Patrix, Soartex, Conquest; owner's call,
CLAUDE.md Licences): private game only, NEVER commit it or put it on the public site.
"""
import argparse, os, zipfile

TEX = "C:/qfb/textures"
STACK = [  # bottom -> top
    (f"{TEX}/r016/QF-gems-frost-chiselcalm.zip", "QF Textures: Stay True foliage, connected metals B (r013), frost gems (r015 E), Chisel calm (r016)"),
    (f"{TEX}/r013/QF-r012-packs-final.zip", "round 12 packs (r013 A): Patrix mobs, Faithless items/CIT, TNT, Soartex shelves, Conquest particles"),
    (f"{TEX}/r013/QF-r012-gui-final.zip", "round 12 GUI (r013 A): Faithless screens and creative tabs"),
    (f"{TEX}/r014/QF-r014-golem-conquest.zip", "Conquest snow golem (r014 D)"),
]
HUD = {"assets/minecraft/textures/gui/icons.png", "assets/minecraft/textures/gui/widgets.png"}
DESC = "Quest Forge settled picks (private test pack): QF Textures r016 + round 12 mobs/items/GUI + Conquest snow golem"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-hud", action="store_true", help="keep the GUI set's icons.png/widgets.png")
    a = ap.parse_args()
    files, credits = {}, []
    for path, what in STACK:
        z = zipfile.ZipFile(path)
        n = 0
        for i in z.infolist():
            name = i.filename
            if name.endswith("/") or name == "pack.mcmeta" or name == "pack.png":
                continue
            if name in HUD and not a.keep_hud:
                print(f"  dropped {name} ({os.path.basename(path)}: HUD stays as live)")
                continue
            if name.upper().startswith("CREDITS") or name.upper().startswith("LICENSE"):
                credits.append((f"{os.path.basename(path)}/{name}", z.read(name)))
                continue
            files[name] = (z, i)
            n += 1
        print(f"  {n:5d} files  {os.path.basename(path)}  ({what})")
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as w:
        w.writestr("pack.mcmeta", '{\n "pack": {\n  "pack_format": 1,\n  "description": "%s"\n }\n}\n' % DESC)
        w.writestr("README-STACK.txt", "Merged by tools/textures/build_test_stack.py, bottom -> top:\n"
                   + "".join(f"  {os.path.basename(p)}: {w_}\n" for p, w_ in STACK)
                   + "Private: copied pack art. Never redistribute this zip.\n")
        seen = set()
        for name, data in credits:
            base = name.split("/", 1)[1]
            if base in seen:
                base = name.replace("/", "--")
            seen.add(base)
            w.writestr(base, data)
        for name in sorted(files):
            z, i = files[name]
            w.writestr(i, z.read(i), compress_type=zipfile.ZIP_DEFLATED)
    if os.path.exists(out):
        os.remove(out)
    os.replace(tmp, out)
    print(f"wrote {out}: {len(files)} files, {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
