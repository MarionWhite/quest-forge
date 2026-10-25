#!/usr/bin/env python3
"""Turn a raw client game folder into a Prism Launcher instance zip.

    python3.10 -I tools/release/build_prism_instance.py --raw C:\\qfs\\release\\QuestForge-OptiFine --out C:\\qfs\\release\\prism

Input is one edition's raw game folder, the layout tools/release/build_client_release.py
writes (bin\\, mods\\, config\\, assets\\, resources\\ ...). Output, under --out:

  QuestForge-client-instance-optifine.zip     one top folder, "Quest Forge\\"
  QuestForge-client-instance-optifine.zip.sha1  "<sha1>  <zip name>", for the upload
  (and -angelica for the Angelica edition)

The zip holds one Prism instance:

  Quest Forge\\instance.cfg            name, icon, JVM args, 8 GB memory defaults (the installer sets the rest)
  Quest Forge\\mmc-pack.json           LWJGL 2.9.4-nightly-20150209, Minecraft 1.7.10, Forge (local jar)
  Quest Forge\\patches\\net.minecraftforge.json
  Quest Forge\\libraries\\forge-...jar  the Forge jar, flat, as Prism's MMC-hint "local" lookup expects
  Quest Forge\\minecraft\\             the game folder: mods, config, scripts, resources, assets\\mcheli ...
  Quest Forge\\questforge-release.json release name, edition, date, pack fingerprint
  Quest Forge\\SHA1SUMS.txt           sha1 of every file above (except itself); the installer checks it
  Quest Forge\\questforge-tools\\        apply-lite.ps1 and its profiles, for the friend installer
  Quest Forge\\perf-preset.command     the Mac preset switcher (its paths are relative to this folder)
  Quest Forge\\icon.png

WHAT IS NOT IN THE ZIP, AND WHY.
  bin\\minecraft.jar, bin\\natives, bin\\lib\\*  Prism downloads the vanilla client, the LWJGL natives
      for the friend's OS and every library Minecraft 1.7.10 needs. Shipping them would also ship
      the wrong OS's natives. The release page says so, and the play page depends on it.
  assets\\objects, assets\\skins, assets\\virtual  vanilla sound and texture objects: Prism fetches
      them by the 1.7.10 asset index (assets\\indexes is kept: it is small). assets\\mcheli IS kept:
      MCHeli loads its helicopters from there, and no mod jar has them.
  Only the Forge jar from bin\\lib is kept, and only as libraries\\<jar>, the one place Prism
      looks for a local library.
  The same exclusions as build_client_release.py: saves, logs, crash reports, screenshots, backup and
  work folders, *.pre-* / *.broken-* snapshots, the JourneyMap map cache (its config is kept), personal
  caches, the Windows launchers, the raw Mac launcher, hs_err logs, and player-name.txt.

The raw folder is only read. Every file in the zip is a real copy; nothing is linked.

ZIP LAYOUT. Prism's zip import (InstanceImportTask) finds instance.cfg wherever it is and takes its
folder as the instance root, so the single top folder works for "Add instance -> Import" and for
unzipping straight into the instances folder. The installer relies on the same layout.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LITE = os.path.join(REPO, "tools", "lite-client")

MC_VERSION = "1.7.10"
LWJGL = "2.9.4-nightly-20150209"
# The Forge build each edition ships. The OptiFine edition is the hand-patched 1558 jar; Angelica
# is stock 1614 (tools/angelica-client/manifest.json). Anything else is a wrong build: refuse it.
EDITIONS = {
    "optifine": {"instance": "Quest Forge", "forge": "10.13.4.1558", "forge_tag": "1558",
                 "forge_name": "Forge (Quest Forge patched splash jar, local)"},
    "angelica": {"instance": "Quest Forge Angelica", "forge": "10.13.4.1614", "forge_tag": "1614",
                 "forge_name": "Forge (Quest Forge Angelica, stock 1614, local)"},
}
EDITION_LABEL = {"optifine": "OptiFine", "angelica": "Angelica"}
FORGE_JAR = re.compile(r"^forge-1\.7\.10-(10\.13\.4\.\d+)-1\.7\.10-universal\.jar$")
# The 8 GB row of the RAM table (docs/setup/hosting-a-server.md; the installer picks the real row).
DEFAULT_MIN_MB, DEFAULT_MAX_MB = 1024, 3072
NOTES = ("Quest Forge ({ed}) for Prism Launcher. Minecraft 1.7.10 + Forge {forge}. Java 8 x64 only. "
         "Install with the Quest Forge installer, or import this zip in Prism.")

# Top-level entries of the raw folder that are never shipped (same idea as build_client_release.py).
EXCLUDE = re.compile(
    r"^(saves|logs|crash-reports|screenshots|mods_disabled|mods-removed|mods-lite-removed|_lite-backup|"
    r"bench|asm|debug|usercache\.json|usernamecache\.json|nicknames\.json|player-name\.txt|modlist\.html|"
    r"minetweaker\.log|SHA1SUMS\.txt|SHA1SUMS|\.DS_Store|Thumbs\.db|hs_err_pid.*\.log|"
    r"PLAY(-ANGELICA)?\.bat|TEST-LAUNCH.*|LAUNCH-.*|launch-questforge-mac\.command|"
    r"_(backup|work|qf-backups|perf-backup).*|.*\.pre-.*|.*\.broken-.*|.*\.bak-.*|.*\.batch-tmp|.*\.jar\.pre.*)$",
    re.I)
# Folders of the raw game folder shipped as they are (bin/ is handled separately; assets/ too).
COPY_DIRS = ["mods", "config", "scripts", "resources", "resourcepacks", "shaderpacks", "fonts",
             "customnpcs", "hats", "structures", "CustomDISkins", "legends"]
# Files at the top of the raw game folder that go into minecraft/ (same list as build_client_release.py).
COPY_FILES = ["options.txt", "optionsof.txt", "optionsshaders.txt", "log4j2_17-111.xml", "betterfps.txt",
              "pack.png", "questforge.ico", "tf-tutorials.txt"]
ASSET_EXCLUDE = {"objects", "skins", "virtual"}
# The lite/potato tooling the friend installer runs (the rest of tools/lite-client is repo-only).
LITE_SHIP = ["apply-lite.ps1", "client-only-drop.txt", "jvm-args.txt", "README.md"]
LITE_SHIP_DIRS = ["profiles"]

# The library list of the real Prism instance's patches/net.minecraftforge.json (Forge 1.7.10 needs these).
FORGE_LIBRARIES = [
    {"name": "net.minecraft:launchwrapper:1.12"},
    {"name": "org.ow2.asm:asm-all:5.0.3"},
    {"name": "com.typesafe.akka:akka-actor_2.11:2.3.3", "url": "https://maven.minecraftforge.net/"},
    {"name": "com.typesafe:config:1.2.1", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-actors-migration_2.11:1.1.0", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-compiler:2.11.1", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang.plugins:scala-continuations-library_2.11:1.0.2", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang.plugins:scala-continuations-plugin_2.11.1:1.0.2", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-library:2.11.1", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-parser-combinators_2.11:1.0.1", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-reflect:2.11.1", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-swing_2.11:1.0.1", "url": "https://maven.minecraftforge.net/"},
    {"name": "org.scala-lang:scala-xml_2.11:1.0.2", "url": "https://maven.minecraftforge.net/"},
    {"name": "lzma:lzma:0.0.1"},
    {"name": "com.google.guava:guava:17.0"},
    {"name": "org.apache.commons:commons-lang3:3.3.2"},
]


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_pack_fingerprint():
    """tools/pack_fingerprint.py, loaded by path (the script is run with -I, so its folder is not on sys.path)."""
    path = os.path.join(HERE, "..", "pack_fingerprint.py")
    spec = importlib.util.spec_from_file_location("pack_fingerprint", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pack_info(config_dir):
    """{'date', 'fingerprint'} of the config folder, or None when the packcheck list is not there."""
    try:
        pf = load_pack_fingerprint()
        files, _reviewed = pf.read_list()
        fp, _ = pf.fingerprint(config_dir, files)
        return {"date": pf.pack_date(config_dir), "fingerprint": fp}
    except (OSError, SystemExit) as e:
        print("warning: no pack fingerprint (%s); questforge-release.json will say null" % e)
        return None


def jvm_args():
    """The one-line Java argument string from tools/lite-client/jvm-args.txt (the play page's copy)."""
    with open(os.path.join(LITE, "jvm-args.txt"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("-XX:+UseG1GC"):
                return line.strip()
    raise SystemExit("tools/lite-client/jvm-args.txt has no Java argument line")


def excluded(name):
    return EXCLUDE.match(name) is not None


def copy_tree(src, dst):
    """Copy a folder tree, skipping excluded names at any depth. Real copies only. Returns the file count."""
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if not excluded(d))
        rel = os.path.relpath(root, src)
        for f in sorted(files):
            if excluded(f):
                continue
            target = os.path.join(dst, rel, f)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(os.path.join(root, f), target)
            n += 1
    return n


def cfg_text(edition, release_notes, uuid_hex, has_icon):
    e = EDITIONS[edition]
    rows = [
        ("ConfigVersion", "1.3"),
        ("InstanceType", "OneSix"),
        ("MaxMemAlloc", str(DEFAULT_MAX_MB)),
        ("MinMemAlloc", str(DEFAULT_MIN_MB)),
        ("PermGen", "256"),
        ("OverrideCommands", "false"),
        ("OverrideConsole", "false"),
        ("OverrideGameTime", "false"),
        ("OverrideJavaArgs", "true"),
        ("OverrideJavaLocation", "false"),
        ("OverrideMemory", "true"),
        ("OverrideMiscellaneous", "false"),
        ("OverrideNativeWorkarounds", "false"),
        ("OverridePerformance", "false"),
        ("OverrideWindow", "false"),
        ("JvmArgs", '"%s"' % jvm_args()),
        ("iconKey", "questforge" if has_icon else "default"),
        ("name", e["instance"]),
        ("notes", release_notes),
        ("uuid", uuid_hex),
    ]
    return "[General]\n" + "".join("%s=%s\n" % kv for kv in rows)


def mmc_pack(edition):
    e = EDITIONS[edition]
    return {
        "components": [
            {"cachedName": "LWJGL 2", "cachedVersion": LWJGL, "cachedVolatile": True,
             "dependencyOnly": True, "uid": "org.lwjgl", "version": LWJGL},
            {"cachedName": "Minecraft", "cachedRequires": [{"suggests": LWJGL, "uid": "org.lwjgl"}],
             "cachedVersion": MC_VERSION, "important": True, "uid": "net.minecraft", "version": MC_VERSION},
            {"cachedName": e["forge_name"],
             "cachedRequires": [{"equals": MC_VERSION, "uid": "net.minecraft"}],
             "cachedVersion": e["forge"], "uid": "net.minecraftforge", "version": e["forge"]},
        ],
        "formatVersion": 1,
    }


def forge_patch(edition, jar_name):
    e = EDITIONS[edition]
    libs = [{"name": "net.minecraftforge:forge:1.7.10-%s-1.7.10:universal" % e["forge"],
             "MMC-hint": "local"}] + FORGE_LIBRARIES
    return {
        "+tweakers": ["cpw.mods.fml.common.launcher.FMLTweaker"],
        "formatVersion": 1,
        "libraries": libs,
        "mainClass": "net.minecraft.launchwrapper.Launch",
        "name": e["forge_name"],
        "order": 5,
        "requires": [{"equals": MC_VERSION, "uid": "net.minecraft"}],
        "uid": "net.minecraftforge",
        "version": e["forge"],
    }


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=4)
        f.write("\n")


def write_sha1sums(instance_dir):
    rows = []
    for root, _, files in os.walk(instance_dir):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, instance_dir).replace(os.sep, "/")
            if rel == "SHA1SUMS.txt":
                continue
            rows.append((rel, sha1_file(p)))
    rows.sort()
    with open(os.path.join(instance_dir, "SHA1SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        for rel, digest in rows:
            f.write("%s  %s\n" % (digest, rel))
    return len(rows)


def stage_instance(raw, edition, release, built, icon, stage, instance_name):
    """Lay out the instance under stage/<instance_name>. Returns the instance folder and a summary dict."""
    e = EDITIONS[edition]
    game = os.path.join(raw, "bin")
    forge = [f for f in os.listdir(os.path.join(game, "lib")) if FORGE_JAR.match(f)] \
        if os.path.isdir(os.path.join(game, "lib")) else []
    if len(forge) != 1:
        raise SystemExit("bin\\lib must hold exactly one Forge 1.7.10 universal jar, found %s" % forge)
    jar = forge[0]
    if e["forge"] not in jar:
        raise SystemExit("%s is not the %s Forge jar of the %s edition" % (jar, e["forge"], edition))
    for needed in ("mods", "config", os.path.join("assets", "mcheli", "helicopters")):
        if not os.path.isdir(os.path.join(raw, needed)):
            raise SystemExit("raw folder lacks %s" % needed)

    inst = os.path.join(stage, instance_name)
    game_dst = os.path.join(inst, "minecraft")
    counts = {}
    for d in COPY_DIRS:
        s = os.path.join(raw, d)
        if os.path.isdir(s):
            counts[d] = copy_tree(s, os.path.join(game_dst, d))
    assets = os.path.join(raw, "assets")
    n = 0
    for entry in sorted(os.listdir(assets)):
        if entry in ASSET_EXCLUDE or excluded(entry):
            continue
        s = os.path.join(assets, entry)
        n += copy_tree(s, os.path.join(game_dst, "assets", entry)) if os.path.isdir(s) \
            else _copy_file(s, os.path.join(game_dst, "assets", entry))
    counts["assets"] = n
    jm = os.path.join(raw, "journeymap", "config")
    if os.path.isdir(jm):
        counts["journeymap/config"] = copy_tree(jm, os.path.join(game_dst, "journeymap", "config"))
    for f in COPY_FILES:
        s = os.path.join(raw, f)
        if os.path.isfile(s):
            _copy_file(s, os.path.join(game_dst, f))

    # The Forge jar goes to libraries/, flat. Prism resolves MMC-hint "local" libraries there.
    _copy_file(os.path.join(game, "lib", jar), os.path.join(inst, "libraries", jar))
    write_json(os.path.join(inst, "patches", "net.minecraftforge.json"), forge_patch(edition, jar))
    write_json(os.path.join(inst, "mmc-pack.json"), mmc_pack(edition))

    pinfo = pack_info(os.path.join(raw, "config"))
    notes = NOTES.format(ed=EDITION_LABEL[edition], forge=e["forge"])
    with open(os.path.join(inst, "instance.cfg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(cfg_text(edition, notes, uuid.uuid5(uuid.NAMESPACE_URL, "questforge-prism:" + edition).hex,
                         icon is not None))
    write_json(os.path.join(inst, "questforge-release.json"), {
        "format": 1,
        "instance": instance_name,
        "edition": edition,
        "release": release,
        "built": built,
        "minecraft": MC_VERSION,
        "forge": e["forge"],
        "forgeJar": jar,
        "lwjgl": LWJGL,
        "pack": pinfo,
        "sha1sums": "SHA1SUMS.txt",
    })
    if icon:
        _copy_file(icon, os.path.join(inst, "icon.png"))
    _copy_file(os.path.join(LITE, "perf-preset.command"), os.path.join(inst, "perf-preset.command"))
    for f in LITE_SHIP:
        _copy_file(os.path.join(LITE, f), os.path.join(inst, "questforge-tools", "lite-client", f))
    for d in LITE_SHIP_DIRS:
        copy_tree(os.path.join(LITE, d), os.path.join(inst, "questforge-tools", "lite-client", d))
    return inst, counts, pinfo


def _copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return 1


def build(raw, out, edition, release, built, icon, instance_name=None):
    raw = os.path.abspath(raw)
    out = os.path.abspath(out)
    if not os.path.isdir(raw):
        raise SystemExit("no raw game folder at %s" % raw)
    instance_name = instance_name or EDITIONS[edition]["instance"]
    os.makedirs(out, exist_ok=True)
    zip_name = "QuestForge-client-instance-%s.zip" % edition
    zip_path = os.path.join(out, zip_name)
    if os.path.exists(zip_path):
        raise SystemExit("%s exists; remove it first (this script never overwrites a release)" % zip_path)
    with tempfile.TemporaryDirectory(prefix="qf-prism-") as stage:
        inst, counts, pinfo = stage_instance(raw, edition, release, built, icon, stage, instance_name)
        for k in sorted(counts):
            print("  %-18s %6d files" % (k, counts[k]))
        n = write_sha1sums(inst)
        # Zip entries are "<instance name>/...", written in sorted order.
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(stage):
                dirs.sort()
                for f in sorted(files):
                    p = os.path.join(root, f)
                    z.write(p, os.path.relpath(p, stage).replace(os.sep, "/"))
    digest = sha1_file(zip_path)
    with open(zip_path + ".sha1", "w", encoding="utf-8", newline="\n") as f:
        f.write("%s  %s\n" % (digest, zip_name))
    print("%s: %d files, %.0f MB, sha1 %s" % (zip_name, n, os.path.getsize(zip_path) / 1e6, digest))
    print("pack fingerprint: %s" % (pinfo["fingerprint"] if pinfo else "none"))
    return zip_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True, help="one edition's raw game folder (read only)")
    ap.add_argument("--out", required=True, help="folder for the zip and its .sha1")
    ap.add_argument("--edition", choices=sorted(EDITIONS), help="default: from the folder name")
    ap.add_argument("--release", help="release name written to questforge-release.json (default: the build date)")
    ap.add_argument("--date", help="build date YYYY-MM-DD (default: today)")
    ap.add_argument("--icon", help="PNG for the instance icon (default: pack/resourcepack/pack.png)")
    ap.add_argument("--instance-name", help="folder and display name (default per edition)")
    a = ap.parse_args(argv)
    edition = a.edition or ("angelica" if "angelica" in os.path.basename(os.path.abspath(a.raw)).lower() else "optifine")
    built = a.date or datetime.date.today().isoformat()
    icon = a.icon or os.path.join(REPO, "pack", "resourcepack", "pack.png")
    if not os.path.isfile(icon):
        icon = None
    build(a.raw, a.out, edition, a.release or built, built, icon, a.instance_name)


if __name__ == "__main__":
    main()
