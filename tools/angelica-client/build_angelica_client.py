#!/usr/bin/env python3
"""Build a Quest Forge Angelica client from an OptiFine E7 game folder.

The E7 folder is only read. The new folder gets:
  bin/       the E7 bin/ with Forge 1558 swapped for stock Forge 1614
  mods/      the E7 mods minus OptiFine, FastCraft and BetterFps, plus Angelica,
             UniMixins and GTNHLib (manifest.json; sha1-checked). The E7 folder
             must already run GTNH CodeChickenCore 1.4.22 (the pack does since
             2026-10-18); the build refuses one with stock CCC + CodeChickenLib.
  config/    the E7 config plus overlay/config (vsync off, no splash memory bar)
  options    the E7 options.txt plus overlay/options-keys.txt (zoom on C, Iris keys);
             the E7 shader pack choice carried into config/shaders.properties
  LAUNCH-ANGELICA.bat
Everything else (assets, resources, scripts, shaderpacks...) comes across as
hard links when both folders are on one drive, so a second instance costs
little disk. Saves are not copied unless --with-saves.

HARD LINKS ARE THE SAME FILE. Replacing a jar in the new folder with `cp` or
Copy-Item writes through into the E7 folder's copy. Delete the file first, or
rebuild with --force --pack-jars. (The pack's own jars are always real copies.)

Usage (Windows, py -3.10 -I):
  build_angelica_client.py --to C:\\qfb\\client-ang2 --jars C:\\qfb\\dl --jars C:\\qfb\\client-ang\\mods
  build_angelica_client.py --from D:\\QuestForge --to D:\\QuestForge-Angelica --jars downloads
      [--pack-jars DIR]     QuestForgeTweaks/Content/Transformers builds to use instead of the E7 ones
      [--with-saves] [--shader off|NAME.zip] [--add-shaderpack FILE] [--force]

Never point --to at the E7 folder itself, or at %APPDATA%\\.crazycraft4: the
script refuses. Building into an existing folder needs --force and keeps its
saves/, logs/ and options.
"""
import argparse, hashlib, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
LIVE = os.path.join(APPDATA, ".crazycraft4")

# Top-level entries of an E7 folder that never come across.
SKIP_TOP = re.compile(r"^(saves|logs|crash-reports|screenshots|mods_disabled|mods-removed|mods-lite-removed|"
                      r"_lite-backup|bench|asm|debug|.*\.pre-.*|_backup.*|_work.*|TEST-LAUNCH.*\.bat|"
                      r"LAUNCH-LITE\.bat|optionsof\.txt|betterfps\.txt|optionsshaders\.txt|"
                      r"usercache\.json|modlist\.html|minetweaker\.log|.*\.jar)$", re.I)
# Kept from an existing --to folder on --force.
KEEP_ON_FORCE = {"saves", "logs", "screenshots", "crash-reports", "options.txt", "journeymap", "config"}
PACK_JARS = ("QuestForgeTweaks-1.0.jar", "QuestForgeContent-1.0.0.jar", "TransformersMod-0.6.3-qf1.jar")
SPLASH_FILES = ["resources/assets/minecraft/textures/gui/title/loading_mural.png",
                "resources/assets/minecraft/textures/gui/title/emblem_corner.png",
                "resources/assets/minecraft/textures/gui/title/splash/trough.png",
                "resources/assets/minecraft/textures/gui/title/splash/magma.png",
                "resources/assets/minecraft/sounds/music/splash.wav",
                "resources/assets/minecraft/sounds/music/menu.wav"]


def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def same_drive(a, b):
    return os.path.splitdrive(os.path.abspath(a))[0].lower() == os.path.splitdrive(os.path.abspath(b))[0].lower()


def place(src, dst, link):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.lexists(dst):
        os.remove(dst)
    if link:
        try:
            os.link(src, dst)
            return
        except OSError:
            pass
    shutil.copy2(src, dst)


# Hard links share the file with the E7 folder: a mod that rewrites one in place
# would change the E7 copy too. Only files nothing writes are linked.
LINK_DIRS = {"assets", "resources", "legends", "bin"}
LINK_EXT = (".jar", ".zip", ".pak", ".litemod")


def linkable(top, rel):
    # The pack's own jars get rebuilt and copied over; a plain copy onto a hard
    # link writes straight through into the E7 folder (it happened, 2026-10-17).
    if os.path.basename(rel) in PACK_JARS or os.path.basename(rel).startswith("QuestForge"):
        return False
    if top in LINK_DIRS:
        return True
    return top in ("mods", "shaderpacks", "resourcepacks") and rel.lower().endswith(LINK_EXT)


def tree(src, dst, link, skip=None, top=None):
    """Hard-link (or copy) every file under src into dst. Never follows junctions."""
    top = top or os.path.basename(src.rstrip("\\/"))
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))
                   and not is_junction(os.path.join(root, d))]
        rel = os.path.relpath(root, src)
        for f in files:
            r = os.path.normpath(os.path.join(rel, f))
            if skip and skip(r):
                continue
            place(os.path.join(root, f), os.path.join(dst, r), link and linkable(top, r))
            n += 1
    return n


def is_junction(p):
    try:
        return bool(os.lstat(p).st_file_attributes & 0x400)   # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, AttributeError):
        return False


def find_jar(name, want_sha, dirs):
    for d in dirs:
        for root, _, files in os.walk(d):
            if name in files:
                p = os.path.join(root, name)
                if sha1(p) == want_sha:
                    return p
    return None


def set_keys(path, keys, sep):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(path) else []
    for k, v in keys.items():
        want = f"{k}{sep}{v}"
        for i, l in enumerate(lines):
            if l.startswith(k + sep):
                lines[i] = want
                break
        else:
            lines.append(want)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def read_keys(path, sep):
    out = {}
    for l in open(path, encoding="utf-8").read().splitlines():
        l = l.strip()
        if not l or l.startswith("#") or sep not in l:
            continue
        k, v = l.split(sep, 1)
        out[k] = v
    return out


def merge_json(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge_json(base[k], v)
        else:
            base[k] = v
    return base


def merge_forge_cfg(path, overlay):
    """Set B:/I:/S:/D: keys from an overlay Forge config into an existing one."""
    over = {}
    for l in open(overlay, encoding="utf-8").read().splitlines():
        m = re.match(r"\s*([BISD]:[\w\"]+)=(.*)$", l)
        if m:
            over[m.group(1)] = m.group(2)
    if not os.path.exists(path):
        shutil.copy2(overlay, path)
        return sorted(over)
    lines = open(path, encoding="utf-8").read().splitlines()
    for i, l in enumerate(lines):
        m = re.match(r"(\s*)([BISD]:[\w\"]+)=(.*)$", l)
        if m and m.group(2) in over:
            lines[i] = f"{m.group(1)}{m.group(2)}={over[m.group(2)]}"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return sorted(over)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", default=LIVE, help="E7 game folder to copy (read only; default the live instance)")
    ap.add_argument("--to", required=True, help="new Angelica game folder")
    ap.add_argument("--jars", action="append", default=[], help="folder(s) holding the jars in manifest.json")
    ap.add_argument("--bin", help="folder holding minecraft.jar, lib/, natives/ (default <from>/bin)")
    ap.add_argument("--pack-jars", help="folder with QuestForgeTweaks/Content/Transformers builds to use")
    ap.add_argument("--with-saves", action="store_true")
    ap.add_argument("--shader", help="off, or a shader pack zip name in shaderpacks/ (default: the E7 choice)")
    ap.add_argument("--add-shaderpack", action="append", default=[], help="shader pack zip to add")
    ap.add_argument("--force", action="store_true", help="rebuild an existing folder (keeps saves, logs, options, config)")
    a = ap.parse_args()

    src, dst = os.path.abspath(a.src), os.path.abspath(a.to)
    man = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
    if os.path.normcase(dst) in (os.path.normcase(src), os.path.normcase(LIVE)) or \
            os.path.normcase(dst).startswith(os.path.normcase(src) + os.sep):
        sys.exit(f"refusing: --to {dst} is the E7 folder (or inside it)")
    if not os.path.isfile(os.path.join(src, "options.txt")) or not os.path.isdir(os.path.join(src, "mods")):
        sys.exit(f"{src} does not look like a Quest Forge game folder (no options.txt / mods)")
    binsrc = os.path.abspath(a.bin) if a.bin else os.path.join(src, "bin")
    if not os.path.isfile(os.path.join(binsrc, "minecraft.jar")):
        sys.exit(f"no minecraft.jar in {binsrc}; pass --bin")
    fresh = not os.path.exists(dst) or not os.listdir(dst)
    if not fresh and not a.force:
        sys.exit(f"{dst} exists; --force rebuilds it (keeping {', '.join(sorted(KEEP_ON_FORCE))})")

    # Since 2026-10-18 the E7 pack itself runs GTNH CodeChickenCore, so the Angelica build
    # no longer swaps it. An E7 folder from before that would come across with stock CCC.
    smods = os.path.join(src, "mods")
    lacks = [m for m in man.get("source_must_have", [])
             if not os.path.isfile(os.path.join(smods, *m["file"].split("/")))
             or sha1(os.path.join(smods, *m["file"].split("/"))) != m["sha1"]]
    stale = [m for m in man.get("source_must_not_have", [])
             if os.path.exists(os.path.join(smods, *m["file"].split("/")))]
    if lacks or stale:
        for m in lacks:
            print(f"the E7 folder lacks mods/{m['file']} (sha1 {m['sha1']}): {m['why']}\n      {m['url']}")
        for m in stale:
            print(f"the E7 folder still has mods/{m['file']}: {m['why']}")
        sys.exit("update the E7 folder to the current pack first (GTNH CodeChickenCore since 2026-10-18)")

    # Resolve every added jar first, so a missing download stops before anything is written.
    dirs = [os.path.abspath(d) for d in a.jars]
    forge = man["forge"]["add"]
    adds = {forge["file"]: find_jar(forge["file"], forge["sha1"], dirs)}
    for m in man["mods_add"]:
        adds[m["file"]] = find_jar(m["file"], m["sha1"], dirs)
    missing = [f for f, p in adds.items() if not p]
    if missing:
        print("missing (or wrong sha1) in --jars:")
        for f in missing:
            e = forge if f == forge["file"] else next(m for m in man["mods_add"] if m["file"] == f)
            print(f"  {f}  sha1 {e['sha1']}\n      {e['url']}")
        sys.exit(2)

    link = same_drive(src, dst)
    os.makedirs(dst, exist_ok=True)
    keep = set() if fresh else {k for k in KEEP_ON_FORCE if os.path.exists(os.path.join(dst, k))}
    for sub in ("mods", "bin"):
        p = os.path.join(dst, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
    print(f"{src}  ->  {dst}  ({'hard links' if link else 'copies'})")

    # 1. The game folder, minus what never comes across.
    for name in sorted(os.listdir(src)):
        s = os.path.join(src, name)
        if SKIP_TOP.match(name) or name in keep or name == "bin" or is_junction(s):
            continue
        if name == "saves" and not a.with_saves:
            continue
        if os.path.isdir(s):
            n = tree(s, os.path.join(dst, name), link,
                     skip=(lambda r: re.search(r"\.jar\.(broken|pre|bak)", r, re.I)) if name == "mods" else None)
            print(f"  {name}/  {n} files")
        else:
            place(s, os.path.join(dst, name), False)    # small files: real copies
    if a.with_saves and "saves" not in keep and os.path.isdir(os.path.join(src, "saves")):
        print(f"  saves/  {tree(os.path.join(src, 'saves'), os.path.join(dst, 'saves'), False)} files (copied)")

    # 2. bin/ with Forge swapped.
    n = tree(binsrc, os.path.join(dst, "bin"), link,
             skip=lambda r: os.path.basename(r) == man["forge"]["remove"] or ".jar.pre-" in r)
    place(adds[forge["file"]], os.path.join(dst, "bin", "lib", forge["file"]), link)
    print(f"  bin/  {n} files, Forge {man['forge']['remove']} -> {forge['file']}")

    # 3. mods: out, in, and the pack's own builds.
    md = os.path.join(dst, "mods")
    for m in man["mods_remove"]:
        p = os.path.join(md, *m["file"].split("/"))
        if os.path.exists(p):
            note = "" if sha1(p) == m["sha1"] else "  (not the pack's build, removed anyway)"
            os.remove(p)
            print(f"  - mods/{m['file']}{note}")
        else:
            print(f"  - mods/{m['file']}  (was not there)")
    for pat in man["never_add"]:
        rx = re.compile(pat["file"].replace(".", r"\.").replace("*", ".*") + "$", re.I)
        for f in os.listdir(md):
            if rx.match(f):
                os.remove(os.path.join(md, f))
                print(f"  - mods/{f}  ({pat['why']})")
    for m in man["mods_add"]:
        place(adds[m["file"]], os.path.join(md, m["file"]), link)
        print(f"  + mods/{m['file']}")
    if a.pack_jars:
        for j in PACK_JARS:
            p = os.path.join(a.pack_jars, j)
            if os.path.isfile(p):
                place(p, os.path.join(md, j), False)
                print(f"  * mods/{j}  from {a.pack_jars} (sha1 {sha1(p)[:12]})")

    # 4. Config overlay and options.
    cd = os.path.join(dst, "config")
    os.makedirs(cd, exist_ok=True)
    ao = os.path.join(cd, "angelica-options.json")
    base = json.load(open(ao, encoding="utf-8")) if os.path.exists(ao) else {}
    merge_json(base, json.load(open(os.path.join(HERE, "overlay", "config", "angelica-options.json"), encoding="utf-8")))
    with open(ao, "w", encoding="utf-8", newline="\n") as f:
        json.dump(base, f, indent=2)
    keys = merge_forge_cfg(os.path.join(cd, "angelica-modules.cfg"),
                           os.path.join(HERE, "overlay", "config", "angelica-modules.cfg"))
    print(f"  config: angelica-options.json vsync_mode=OFF; angelica-modules.cfg {', '.join(keys)}")
    set_keys(os.path.join(cd, "splash.properties"), {"enabled": "true"}, "=")
    if "options.txt" not in keep:
        set_keys(os.path.join(dst, "options.txt"), read_keys(os.path.join(HERE, "overlay", "options-keys.txt"), ":"), ":")
        print("  options.txt: zoom on C, Iris keys F4/F8/F9, vsync off")

    # 5. Shader packs: Angelica reads config/shaders.properties, not optionsshaders.txt.
    for z in a.add_shaderpack:
        place(z, os.path.join(dst, "shaderpacks", os.path.basename(z)), False)
    pack = a.shader
    if pack is None:
        so = os.path.join(src, "optionsshaders.txt")
        pack = read_keys(so, "=").get("shaderPack", "OFF") if os.path.exists(so) else "OFF"
    on = pack.lower() not in ("off", "", "(internal)") and os.path.exists(os.path.join(dst, "shaderpacks", pack))
    set_keys(os.path.join(cd, "shaders.properties"),
             {"shaderPack": pack if on else "", "enableShaders": "true" if on else "false"}, "=")
    print(f"  shaders: {pack if on else 'off'}")

    # 6. Launcher and a record of what was done.
    shutil.copy2(os.path.join(HERE, "LAUNCH-ANGELICA.bat"), os.path.join(dst, "LAUNCH-ANGELICA.bat"))
    gone = [f for f in SPLASH_FILES if not os.path.isfile(os.path.join(dst, f))]
    with open(os.path.join(dst, "ANGELICA-CLIENT.txt"), "w", encoding="utf-8") as f:
        f.write(f"Built by tools/angelica-client/build_angelica_client.py from {src}\n")
        f.write("Forge: " + forge["file"] + "\nAdded: " + ", ".join(m["file"] for m in man["mods_add"]) + "\n")
        f.write("Removed: " + ", ".join(m["file"] for m in man["mods_remove"]) + "\n")
    if gone:
        print("WARNING: loading-screen files missing (the splash falls back to Forge's):")
        for g in gone:
            print("   " + g)
    print(f"done. Start it with {os.path.join(dst, 'LAUNCH-ANGELICA.bat')}")


if __name__ == "__main__":
    main()
