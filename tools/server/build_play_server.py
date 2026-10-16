#!/usr/bin/env python3
"""Assemble the multiplayer server friends play on, from the live pack instance.

WHY THIS IS SEPARATE FROM tools/survey/build_server.py. That server exists to
measure worldgen and drops only what cannot place a block. A play server has a
different rule -- drop what cannot run without a screen -- and different
settings: monsters on, survival, a whitelist, flight allowed. Sharing one
script would make every change to one quietly change the other.

WHY IT IS A SCRIPT AT ALL. The same reason as the survey server: a hand-built
server drifts from the pack, and a client that differs from the server by one
mod cannot join, while one that differs by one config value joins and then
plays with the wrong enchantments. So the server is never edited in place. It is
rebuilt from the instance, and configs are copied verbatim -- never overlaid
with server/config, whose enchantment IDs differ from the clients'.

Usage:
    build_play_server.py --instance <.crazycraft4 dir> --forge-install <dir> --out <server dir>

--forge-install is a directory holding a stock Forge 1.7.10-10.13.4.1558 server
install: the universal jar, minecraft_server.1.7.10.jar and libraries/. The
client's own Forge jar is hand-patched for the splash screen and must not be
used here.
"""
import argparse, fnmatch, hashlib, json, os, shutil, sys, uuid

# Mods that only run with a screen. Each stays on every client -- FML lets a
# client carry mods the server lacks, but never the reverse. Matched as a
# filename prefix.
CLIENT_ONLY = [
    ("OptiFine",            "client renderer; does not run on a dedicated server"),
    ("SoundFilters",        "client audio; crashes the server on FMLServerStopped"),
    ("CustomMenu",          "replaces the client main menu; references client classes"),
    ("DamageIndicators",    "client HUD; common code references client classes"),
    ("MobDismemberment",    "client gore rendering"),
    ("MobAmputation",       "client gore rendering"),
    ("InventoryTweaks",     "client inventory sorting"),
    ("Controlling",         "client keybind search"),
    ("journeymap",          "client map; the server half does nothing without JourneyMapServer"),
]

# QuestForgeTweaks stays: most of its patches target client classes and are
# inert here, but GraveBaublesTransformer fixes GraveStones on the server side,
# where without it every death disconnects every player.

# Kept deliberately, unlike the survey server: HatStand adds a block (clients
# with it would be refused by a server without it), Hats depends on it the other
# way round, and ColorfulMobs syncs dyed mobs from the server.

# Backups people leave next to jars. FML ignores them, but they make "which jar
# is the server running" a question with more than one answer.
JUNK = ["*.broken-*", "*.pre-*", "*.bak*", "*.disabled"]

SERVER_PROPERTIES = """\
level-name=world
level-type=DEFAULT
level-seed=
gamemode=0
difficulty=2
hardcore=false
pvp=true
online-mode={online}
white-list=true
max-players={max_players}
spawn-protection=0
view-distance={view_distance}
allow-flight=true
allow-nether=true
generate-structures=true
spawn-npcs=true
spawn-animals=true
spawn-monsters=true
enable-command-block=true
motd=Quest Forge
server-port={port}
"""

# allow-flight=true is not a cheat switch here: vanilla kicks anyone airborne for
# four seconds without creative flight, and half the pack flies -- Transformers
# jet modes, Legends heroes, OreSpawn gliding, TragicMC's Flight effect.

# view-distance is the server's biggest single cost: every player keeps
# (2r+1)^2 chunks loaded and ticking, so 8 costs 289 chunks a player and 6 costs
# 169. It must match the "Distance (in Chunks) to perform entity spawning" and
# "...counting" in config/JustAnotherSpawner/GlobalProperties.cfg. JAS scales
# each mob cap by the chunks it counts / 256, so counting 8 while only 6 are
# loaded packs the full cap into 58% of the area.

# The JVM flags shared by both start scripts. Xms equals Xmx because a server
# owns its memory: growing the heap later costs pauses and buys nothing. The GC
# log is how a pause gets told apart from a slow tick after the fact; it costs
# nothing measurable and rotates at 5 x 20 MB.
JVM_FLAGS = [
    "-Xms{xmx}", "-Xmx{xmx}",
    "-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:G1HeapRegionSize=16M",
    "-XX:+UseSplitVerifier", "-XX:+FailOverToOldVerifier", "-XX:+DisableExplicitGC",
    "-Xloggc:logs/gc.log", "-XX:+PrintGCDetails", "-XX:+PrintGCDateStamps",
    "-XX:+PrintGCApplicationStoppedTime",
    "-XX:+UseGCLogFileRotation", "-XX:NumberOfGCLogFiles=5", "-XX:GCLogFileSize=20M",
    "-Dfml.ignoreInvalidMinecraftCertificates=true", "-Dfml.ignorePatchDiscrepancies=true",
    "-Dlog4j2.formatMsgNoLookups=true",
]

START_BAT = """\
@echo off
rem Saintscore reads mods\\saintspack\\Packs.txt relative to the working
rem directory and crashes preInit without it, so always start from here.
cd /d "%~dp0"
if not exist logs mkdir logs
"{java}" {flags} ^
 -jar {forge} nogui
pause
"""

# Rented hosts almost always run Linux. A panel host (Pterodactyl and the like)
# ignores this file and asks for the same flags in its own startup field; copy
# them from here. It must be Java 8: Forge 1.7.10 does not start on anything newer.
START_SH = """\
#!/bin/sh
# Saintscore reads mods/saintspack/Packs.txt relative to the working
# directory and crashes preInit without it, so always start from here.
cd "$(dirname "$0")"
mkdir -p logs
exec java {flags} \\
 -jar {forge} nogui
"""


def offline_uuid(name):
    """The UUID an offline-mode server gives a player: Java's
    UUID.nameUUIDFromBytes("OfflinePlayer:" + name).

    WHY. With online-mode=false, the console's `whitelist add <name>` still asks
    Mojang for the UUID of the *paid* account with that name, while the joining
    player is identified by this name-derived one. They never match, so every
    whitelisted friend is refused with "You are not white-listed" -- found by
    joining the server, not by reading it.
    """
    h = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    h[6] = (h[6] & 0x0F) | 0x30
    h[8] = (h[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(h)))


def write_whitelist(out, players):
    path = os.path.join(out, "whitelist.json")
    entries = []
    if os.path.exists(path):
        with open(path) as fh:
            entries = json.load(fh)
    known = {e["name"].lower() for e in entries}
    for name in players:
        if name.lower() not in known:
            entries.append({"uuid": offline_uuid(name), "name": name})
    with open(path, "w") as fh:
        json.dump(entries, fh, indent=2)
    print("whitelist: %s" % ", ".join(e["name"] for e in entries))


def drop_reason(name):
    for prefix, why in CLIENT_ONLY:
        if name.startswith(prefix):
            return why
    return None


def is_junk(name):
    return any(fnmatch.fnmatch(name, pat) for pat in JUNK)


def copy_tree(src, dst):
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if is_junk(n)])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True, help="the client instance (mods/, config/ live here)")
    ap.add_argument("--forge-install", required=True, help="stock Forge 1.7.10 server install")
    ap.add_argument("--out", required=True, help="server directory to create")
    ap.add_argument("--ccl", help="patched CodeChickenLib jar to use instead of the client's")
    ap.add_argument("--java", default=r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe")
    ap.add_argument("--xmx", default="10G",
                    help="server heap; 10G suits 10-15 players on a 12 GB host")
    ap.add_argument("--port", type=int, default=25565)
    ap.add_argument("--max-players", type=int, default=15)
    ap.add_argument("--view-distance", type=int, default=6,
                    help="keep equal to JAS's spawning/counting distance (see SERVER_PROPERTIES)")
    ap.add_argument("--online-mode", default="true",
                    help="false only for a local test with offline-launched clients; a "
                         "public offline server lets anyone join under any name")
    ap.add_argument("--player", action="append", default=[],
                    help="whitelist this name (repeatable). With online-mode=false this is "
                         "the only reliable way: the console's `whitelist add` stores the "
                         "wrong UUID. With online-mode=true use `whitelist add` instead.")
    ap.add_argument("--force", action="store_true",
                    help="rebuild an existing --out; its world/ and player lists are kept")
    args = ap.parse_args()
    # Checked before anything is deleted, so a bad command line costs nothing.
    if args.player and args.online_mode.lower() == "true":
        sys.exit("--player writes offline-mode UUIDs; with --online-mode true add players "
                 "with `whitelist add <name>` in the server console instead")

    inst, out, fi = (os.path.abspath(p) for p in (args.instance, args.out, args.forge_install))
    if not os.path.isdir(os.path.join(inst, "mods")):
        sys.exit("no mods/ under %s" % inst)

    # A rebuild must never cost the friends their world. Everything else in the
    # directory is derived and is thrown away; these are carried across.
    keep = ["world", "ops.json", "whitelist.json", "banned-players.json", "banned-ips.json"]
    stash = out + ".keep"
    if os.path.exists(out):
        if not args.force:
            sys.exit("%s already exists (use --force to rebuild it; the world is kept)" % out)
        if os.path.exists(stash):
            sys.exit("%s exists from an interrupted rebuild; restore it by hand first" % stash)
        os.makedirs(stash)
        for name in keep:
            if os.path.exists(os.path.join(out, name)):
                shutil.move(os.path.join(out, name), os.path.join(stash, name))
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "mods"))

    # --- Forge server -----------------------------------------------------
    forge = None
    for fn in os.listdir(fi):
        if fn.startswith("forge-1.7.10") and fn.endswith("-universal.jar"):
            forge = fn
            shutil.copy2(os.path.join(fi, fn), os.path.join(out, fn))
        elif fn.startswith("minecraft_server") and fn.endswith(".jar"):
            shutil.copy2(os.path.join(fi, fn), os.path.join(out, fn))
    if not forge or not os.path.isdir(os.path.join(fi, "libraries")):
        sys.exit("%s is not a Forge server install (universal jar + libraries/)" % fi)
    shutil.copytree(os.path.join(fi, "libraries"), os.path.join(out, "libraries"))
    print("forge:   %s" % forge)

    # --- mods ---------------------------------------------------------------
    kept = dropped = 0
    for entry in sorted(os.listdir(os.path.join(inst, "mods"))):
        src = os.path.join(inst, "mods", entry)
        if is_junk(entry):
            continue
        why = drop_reason(entry)
        if why:
            print("  drop %-40s %s" % (entry, why))
            dropped += 1
            continue
        dst = os.path.join(out, "mods", entry)
        copy_tree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
        kept += 1
    print("mods:    %d kept, %d dropped" % (kept, dropped))

    # CodeChickenLib's WorldExtension.unloadChunk NPEs when a chunk unloads
    # mid-generation; the patched build guards it. CCL has no @Mod, so the
    # server may differ from clients here without refusing anyone.
    if args.ccl:
        libdir = os.path.join(out, "mods", "1.7.10")
        for fn in os.listdir(libdir):
            if fn.startswith("CodeChickenLib"):
                os.remove(os.path.join(libdir, fn))
        shutil.copy2(args.ccl, os.path.join(libdir, "CodeChickenLib-1.7.10-1.1.3.138-universal.jar"))
        print("ccl:     patched build from %s" % args.ccl)

    # --- config, scripts and content ----------------------------------------
    # config/ is copied verbatim from the client. Enchantment, potion and biome
    # IDs are not synced in 1.7.10; they agree only because both sides read the
    # same files. legends/ holds the prebuilt maps six Legends dimensions copy
    # out on first load (see tools/survey/build_server.py).
    for name in ("config", "scripts", "legends", "structures"):
        src = os.path.join(inst, name)
        if os.path.isdir(src):
            copy_tree(src, os.path.join(out, name))
            print("%-8s copied" % (name + ":"))

    for name in keep:
        if os.path.exists(os.path.join(stash, name)):
            shutil.move(os.path.join(stash, name), os.path.join(out, name))
            print("kept:    %s" % name)
    if os.path.isdir(stash):
        os.rmdir(stash)

    if args.player:
        write_whitelist(out, args.player)

    with open(os.path.join(out, "eula.txt"), "w") as fh:
        fh.write("eula=true\n")
    with open(os.path.join(out, "server.properties"), "w") as fh:
        fh.write(SERVER_PROPERTIES.format(online=args.online_mode, port=args.port,
                                          max_players=args.max_players,
                                          view_distance=args.view_distance))
    flags = [f.format(xmx=args.xmx) for f in JVM_FLAGS]
    with open(os.path.join(out, "start.bat"), "w", newline="\r\n") as fh:
        fh.write(START_BAT.format(java=args.java, forge=forge,
                                  flags=" ^\n ".join(" ".join(flags[i:i + 4])
                                                     for i in range(0, len(flags), 4))))
    with open(os.path.join(out, "start.sh"), "w", newline="\n") as fh:
        fh.write(START_SH.format(forge=forge,
                                 flags=" \\\n ".join(" ".join(flags[i:i + 4])
                                                     for i in range(0, len(flags), 4))))

    # JAS keeps its own spawn radius; a mismatch with view-distance silently
    # changes mob density (see the note above SERVER_PROPERTIES).
    jas = os.path.join(out, "config", "JustAnotherSpawner", "GlobalProperties.cfg")
    if os.path.exists(jas):
        with open(jas) as fh:
            props = json.load(fh)
        for key in ("Distance (in Chunks) to perform entity spawning",
                    "Distance (in Chunks) to perform entity counting"):
            if props.get(key) != args.view_distance:
                print("WARNING: JAS %r is %s but view-distance is %d"
                      % (key, props.get(key), args.view_distance))

    with open(os.path.join(out, "BUILT-FROM.txt"), "w") as fh:
        fh.write("Assembled by tools/server/build_play_server.py\n")
        fh.write("Source instance: %s\n" % inst)
        fh.write("Mods kept: %d   dropped: %d\n\n" % (kept, dropped))
        fh.write("Dropped from the server (every client keeps them):\n")
        for prefix, why in CLIENT_ONLY:
            fh.write("  %-18s %s\n" % (prefix, why))
        fh.write("\nRebuild after ANY mod or config change on the clients; never edit here.\n")

    print("\nserver ready at %s -- start it with start.bat" % out)


if __name__ == "__main__":
    main()
