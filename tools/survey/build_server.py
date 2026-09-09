#!/usr/bin/env python3
"""Assemble a headless Forge server from the live pack instance.

WHY THIS IS A SCRIPT. The previous survey server was hand-built, and it drifted
from the pack without anyone noticing: it ran HBM's ore mod, which the pack does
not have, and it never included ChocolateQuest, which the pack does. Both change
what ends up in the ground -- HBM's ore competes for the same stone, and
ChocolateQuest carves dungeons after ore is placed. Every number that server
produced describes a mod set no player has ever played.

So the server is not maintained by hand. It is rebuilt from the live instance
every time, and the only thing removed is a short list of mods that cannot place
a block in the world. That rule is the pack's own, and this script is the thing
that actually enforces it.

Usage:
    build_server.py --instance <prism-minecraft-dir> --out <server-dir>
"""
import argparse, os, shutil, sys

# Mods that cannot place a block in the world, so removing them cannot change
# what the survey measures. Matched as a filename prefix. Anything that touches
# worldgen, ores, dimensions or biomes stays in, whatever it costs to boot.
CLIENT_ONLY = [
    ("OptiFine",            "client renderer; does not run on a dedicated server at all"),
    ("SoundFilters",        "client audio (paulscode); crashes on FMLServerStopped"),
    ("Hats.jar",            "cosmetic headwear rendering"),
    ("HatStand",            "depends on Hats"),
    ("CustomMenu",          "replaces the client main menu"),
    ("DamageIndicators",    "client HUD damage numbers"),
    ("ColorfulMobsMC",      "client mob tinting"),
    ("MobAmputation",       "client gore rendering"),
    ("MobDismemberment",    "client gore rendering"),
    ("InventoryTweaks",     "client inventory sorting"),
]

SERVER_PROPERTIES = """\
level-name={level}
level-type=DEFAULT
level-seed={seed}
gamemode=1
online-mode=false
spawn-protection=0
max-tick-time=-1
view-distance=6
spawn-npcs=false
spawn-animals=false
spawn-monsters=false
generate-structures=true
allow-nether=true
motd=QuestForge survey
server-port={port}
"""


def excluded(name):
    for prefix, why in CLIENT_ONLY:
        if name.startswith(prefix) or name == prefix:
            return why
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True,
                    help="the pack's minecraft/ directory (mods/, config/ live here)")
    ap.add_argument("--out", required=True, help="server directory to create")
    ap.add_argument("--forge", help="Forge universal jar (default: found near the instance)")
    ap.add_argument("--vanilla", help="minecraft_server.1.7.10.jar")
    ap.add_argument("--libraries", help="Forge server libraries/ directory")
    ap.add_argument("--seed", default="", help="world seed (blank = random)")
    ap.add_argument("--level", default="survey", help="world folder name")
    ap.add_argument("--port", type=int, default=25599)
    ap.add_argument("--force", action="store_true", help="overwrite an existing --out")
    args = ap.parse_args()

    inst = os.path.abspath(args.instance)
    out = os.path.abspath(args.out)
    if not os.path.isdir(os.path.join(inst, "mods")):
        sys.exit("no mods/ under %s -- is that the instance's minecraft directory?" % inst)
    if os.path.exists(out):
        if not args.force:
            sys.exit("%s already exists (use --force to replace)" % out)
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "mods"))

    # --- jars -------------------------------------------------------------
    for label, given, pattern in (("forge", args.forge, "forge-1.7.10"),
                                  ("vanilla", args.vanilla, "minecraft_server")):
        src = given
        if not src:
            # Prism keeps the Forge jar beside the instance; the vanilla server
            # jar is not part of a client install and usually has to be supplied.
            for root in (os.path.dirname(inst), inst):
                for dirpath, _, files in os.walk(root):
                    for fn in files:
                        if fn.startswith(pattern) and fn.endswith(".jar"):
                            src = os.path.join(dirpath, fn)
                            break
                    if src:
                        break
                if src:
                    break
        if not src or not os.path.exists(src):
            sys.exit("could not find the %s jar; pass --%s" % (label, label))
        shutil.copy2(src, os.path.join(out, os.path.basename(src)))
        print("%-8s %s" % (label + ":", os.path.basename(src)))

    if args.libraries and os.path.isdir(args.libraries):
        shutil.copytree(args.libraries, os.path.join(out, "libraries"))
        print("libraries: copied")

    # --- mods -------------------------------------------------------------
    kept = dropped = 0
    for entry in sorted(os.listdir(os.path.join(inst, "mods"))):
        src = os.path.join(inst, "mods", entry)
        why = excluded(entry)
        if why:
            print("  drop %-42s %s" % (entry, why))
            dropped += 1
            continue
        dst = os.path.join(out, "mods", entry)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        kept += 1
    print("mods: %d kept, %d dropped" % (kept, dropped))

    # --- config and scripts ----------------------------------------------
    for name in ("config", "scripts"):
        src = os.path.join(inst, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(out, name))
            print("%s: copied" % name)

    with open(os.path.join(out, "eula.txt"), "w") as fh:
        fh.write("eula=true\n")
    with open(os.path.join(out, "server.properties"), "w") as fh:
        fh.write(SERVER_PROPERTIES.format(level=args.level, seed=args.seed, port=args.port))

    # A visible statement of what this server is, so nobody has to guess later
    # the way we had to guess about the last one.
    with open(os.path.join(out, "BUILT-FROM.txt"), "w") as fh:
        fh.write("Assembled by tools/survey/build_server.py\n")
        fh.write("Source instance: %s\n" % inst)
        fh.write("Mods kept: %d   dropped: %d\n\n" % (kept, dropped))
        fh.write("Dropped (client-only; cannot place a block, so cannot affect the survey):\n")
        for prefix, why in CLIENT_ONLY:
            fh.write("  %-20s %s\n" % (prefix, why))
        fh.write("\nEverything else is present, including ChocolateQuest, which the\n")
        fh.write("previous survey server never loaded.\n")

    print("\nserver ready at %s" % out)
    print("sanity-check it with:  python3 tools/survey/pregen.py --server %s --dim 0 --radius 5"
          % out)


if __name__ == "__main__":
    main()
