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
import argparse, fnmatch, hashlib, json, os, shutil, socket, subprocess, sys, uuid, zipfile

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
# The supervised way to run it (tools/server/supervisor.py, copied next to it):
# crash restart, hang detection, hourly backups, a daily restart, graceful stop.
START_SUPERVISED_BAT = """\
@echo off
rem Runs the server under supervisor.py: restart on crash, hang detection,
rem hourly backups into backups\\, a daily restart. This window is the server
rem console. Stop with Ctrl+C or by typing stop; both save the world first.
rem Settings (and the optional Discord webhook) are in supervisor.json.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -I supervisor.py %*
) else (
  python -I supervisor.py %*
)
pause
"""

SUPERVISOR_JSON = {
    "_comment": "Supervisor settings, kept across rebuilds. `py -3 supervisor.py "
                "--print-defaults` lists every key. Put the Discord webhook URL here or in "
                "the QF_DISCORD_WEBHOOK environment variable; never commit it.",
    "restart_at": "05:00",
    "backup_interval_min": 60,
    "keep_hourly": 24,
    "keep_daily": 7,
    "discord_webhook": "",
}

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


def read_properties(path):
    props = {}
    if os.path.exists(path):
        with open(path, encoding="latin-1") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
    return props


def java_command_lines():
    """(pid, command line) of every running java/javaw process."""
    if os.name != "nt":
        res = subprocess.run(["ps", "-eo", "pid=,args="], stdout=subprocess.PIPE,
                             universal_newlines=True).stdout
        rows = [l.strip().split(None, 1) for l in res.splitlines()]
        return [tuple(r) for r in rows if len(r) == 2 and "java" in r[1]]
    ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'java%'\" | "
          "ForEach-Object { [string]$_.ProcessId + [char]9 + $_.CommandLine }")
    res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                         stdout=subprocess.PIPE, universal_newlines=True).stdout
    return [tuple(l.split("\t", 1)) for l in res.splitlines() if "\t" in l]


def pid_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes          # os.kill(pid, 0) on Windows sends CTRL_C_EVENT; it is no probe
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return bool(ok) and code.value == 259          # STILL_ACTIVE


def refuse_if_running(out):
    """--force on a running server moves world/ out from under the JVM and then
    fails partway on locked jars (server-readiness.md, gap 1). Any one of these
    means something is still using the directory."""
    problems = []
    pidfile = os.path.join(out, "supervisor.pid")
    if os.path.exists(pidfile):
        try:
            with open(pidfile) as fh:
                info = json.load(fh)
        except (OSError, ValueError):
            info = {}
        for key in ("supervisor_pid", "java_pid"):
            if info.get(key) and pid_alive(info[key]):
                problems.append("%s %s (from supervisor.pid) is running" % (key, info[key]))
    props = read_properties(os.path.join(out, "server.properties"))
    port = int(props.get("server-port") or 25565)
    s = socket.socket()
    s.settimeout(1)
    if s.connect_ex(("127.0.0.1", port)) == 0:
        problems.append("something is listening on its port %d" % port)
    s.close()
    norm = os.path.normcase(os.path.abspath(out))
    for pid, cmd in java_command_lines():
        if norm in os.path.normcase(cmd):
            problems.append("java pid %s names this directory on its command line" % pid)
    # A server started from start.bat has nothing absolute on its command line,
    # so these catch it: Windows will not rename a file a process holds open
    # (the session lock, the open log), nor a directory that is a process's
    # working directory or holds an open file (the server's jars).
    level = props.get("level-name") or "world"
    for rel in (os.path.join(level, "session.lock"), os.path.join("logs", "latest.log"),
                os.path.join("logs", "fml-server-latest.log"), "."):
        p = os.path.normpath(os.path.join(out, rel))
        if not os.path.exists(p):
            continue
        probe = p + ".running-probe"
        try:
            os.rename(p, probe)
        except OSError as e:
            problems.append("cannot rename %s (%s): a process holds it open" % (p, e.strerror))
            break
        os.rename(probe, p)
    if problems:
        sys.exit("refusing to rebuild %s while it is in use:\n  %s\nStop the server first "
                 "(type stop, or Ctrl+C in the supervisor window)." % (out, "\n  ".join(problems)))


JNDI = "org/apache/logging/log4j/core/lookup/JndiLookup.class"

# Log4Shell. The server's log4j is 2.0-beta9, inside minecraft_server.1.7.10.jar.
# -Dlog4j2.formatMsgNoLookups exists only from 2.10, so that flag in the start
# scripts does nothing here.
#
# The usual fix, deleting JndiLookup.class, KILLS THIS SERVER AT LAUNCH:
# beta9's Interpolator constructs JndiLookup directly, so the first logger
# throws NoClassDefFoundError (found by booting it, 2026-10-17; later log4j
# versions catch the missing class, this one does not). So the class is
# replaced by an inert one with the same name that resolves nothing. Its source,
# compiled with JDK 8 `javac -source 1.6 -target 1.6 -g:none` against the
# server jar:
#
#   package org.apache.logging.log4j.core.lookup;
#   import org.apache.logging.log4j.core.LogEvent;
#   public class JndiLookup implements StrLookup {
#       public String lookup(String key) { return null; }
#       public String lookup(LogEvent event, String key) { return null; }
#   }
JNDI_STUB_SHA256 = "a4c9009432d21647ca48dc5b06f38e338ef5a196d772d5e162e3f20065cc05cc"
JNDI_STUB = (
    "yv66vgAAADIADwoAAwALBwAMBwANBwAOAQAGPGluaXQ+AQADKClWAQAEQ29kZQEABmxvb2t1cAEA"
    "JihMamF2YS9sYW5nL1N0cmluZzspTGphdmEvbGFuZy9TdHJpbmc7AQBOKExvcmcvYXBhY2hlL2xv"
    "Z2dpbmcvbG9nNGovY29yZS9Mb2dFdmVudDtMamF2YS9sYW5nL1N0cmluZzspTGphdmEvbGFuZy9T"
    "dHJpbmc7DAAFAAYBAC9vcmcvYXBhY2hlL2xvZ2dpbmcvbG9nNGovY29yZS9sb29rdXAvSm5kaUxv"
    "b2t1cAEAEGphdmEvbGFuZy9PYmplY3QBAC5vcmcvYXBhY2hlL2xvZ2dpbmcvbG9nNGovY29yZS9s"
    "b29rdXAvU3RyTG9va3VwACEAAgADAAEABAAAAAMAAQAFAAYAAQAHAAAAEQABAAEAAAAFKrcAAbEA"
    "AAAAAAEACAAJAAEABwAAAA4AAQACAAAAAgGwAAAAAAABAAgACgABAAcAAAAOAAEAAwAAAAIBsAAA"
    "AAAAAA==")


def neuter_jndi(jar):
    """Swap the real JndiLookup for the inert stub. Returns True if it changed
    the jar, False if the jar has no JndiLookup or already has the stub."""
    import base64
    stub = base64.b64decode(JNDI_STUB)
    assert hashlib.sha256(stub).hexdigest() == JNDI_STUB_SHA256
    with zipfile.ZipFile(jar) as z:
        if JNDI not in z.namelist() or z.read(JNDI) == stub:
            return False
        tmp = jar + ".tmp"
        with zipfile.ZipFile(tmp, "w") as dst:
            for info in z.infolist():
                data = stub if info.filename == JNDI else z.read(info.filename)
                dst.writestr(info, data, compress_type=info.compress_type)
    os.replace(tmp, jar)
    with zipfile.ZipFile(jar) as z:
        if z.read(JNDI) != stub or z.testzip() is not None:
            sys.exit("rewriting %s failed" % jar)
    return True


def jars_with_live_jndi(root):
    """Every jar under root holding a JndiLookup that is not the stub."""
    hits = []
    for r, _, files in os.walk(root):
        for f in files:
            if f.endswith(".jar"):
                try:
                    with zipfile.ZipFile(os.path.join(r, f)) as z:
                        if JNDI in z.namelist() and hashlib.sha256(
                                z.read(JNDI)).hexdigest() != JNDI_STUB_SHA256:
                            hits.append(os.path.join(r, f))
                except (zipfile.BadZipFile, OSError):
                    pass
    return hits


def write_manifest(out):
    """sha256 of every server jar, mod and config file. The world is only valid
    with exactly these: Transformers assigns material IDs at first load, and a
    missing mod deletes its items. Each backup carries a copy, so a restore can
    rebuild the same set. Check it with `sha256sum -c MANIFEST.sha256`."""
    lines = []
    tops = [f for f in os.listdir(out) if f.endswith(".jar")] + ["mods", "config"]
    for top in sorted(tops):
        p = os.path.join(out, top)
        files = [p] if os.path.isfile(p) else sorted(
            os.path.join(r, f) for r, _, fs in os.walk(p) for f in fs)
        for f in files:
            h = hashlib.sha256()
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            lines.append("%s *%s" % (h.hexdigest(), os.path.relpath(f, out).replace(os.sep, "/")))
    with open(os.path.join(out, "MANIFEST.sha256"), "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(lines)


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
    # These four default to None: on a rebuild the kept server.properties wins
    # unless the option is given. First build: 25565, 15, 6, true.
    ap.add_argument("--port", type=int)
    ap.add_argument("--max-players", type=int)
    ap.add_argument("--view-distance", type=int,
                    help="keep equal to JAS's spawning/counting distance (see SERVER_PROPERTIES)")
    ap.add_argument("--online-mode",
                    help="false only for a local test with offline-launched clients; a "
                         "public offline server lets anyone join under any name")
    ap.add_argument("--player", action="append", default=[],
                    help="whitelist this name (repeatable). With online-mode=false this is "
                         "the only reliable way: the console's `whitelist add` stores the "
                         "wrong UUID. With online-mode=true use `whitelist add` instead.")
    ap.add_argument("--force", action="store_true",
                    help="rebuild an existing --out; its world, player lists, server.properties, "
                         "logs, crash reports, backups and supervisor.json are kept")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    old_props = read_properties(os.path.join(out, "server.properties"))
    defaults = {"server-port": "25565", "max-players": "15", "view-distance": "6",
                "online-mode": "true"}
    given = {"server-port": args.port, "max-players": args.max_players,
             "view-distance": args.view_distance, "online-mode": args.online_mode}
    eff = {k: str(v).lower() if v is not None else old_props.get(k, defaults[k])
           for k, v in given.items()}
    # Checked before anything is deleted, so a bad command line costs nothing.
    if args.player and eff["online-mode"] == "true":
        sys.exit("--player writes offline-mode UUIDs; with --online-mode true add players "
                 "with `whitelist add <name>` in the server console instead")

    inst, fi = (os.path.abspath(p) for p in (args.instance, args.forge_install))
    if not os.path.isdir(os.path.join(inst, "mods")):
        sys.exit("no mods/ under %s" % inst)

    # A rebuild must never cost the friends their world. Everything else in the
    # directory is derived and is thrown away; these are carried across:
    # server.properties, because console and hand changes (MOTD, idle timeout,
    # RCON) would vanish otherwise; logs/ and crash-reports/, because they are
    # the evidence for whatever prompted the rebuild; backups/, obviously.
    level = old_props.get("level-name") or "world"
    keep = [level, "ops.json", "whitelist.json", "banned-players.json", "banned-ips.json",
            "usercache.json", "server.properties", "logs", "crash-reports", "backups",
            "supervisor.json"]
    stash = out + ".keep"
    if os.path.exists(out):
        if not args.force:
            sys.exit("%s already exists (use --force to rebuild it; the world is kept)" % out)
        refuse_if_running(out)
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
    for fn in os.listdir(out):
        if fn.startswith("minecraft_server") and fn.endswith(".jar"):
            if neuter_jndi(os.path.join(out, fn)):
                print("log4j:   JndiLookup in %s replaced by an inert stub (Log4Shell)" % fn)
    # Mods are only reported: some check their own signatures, and FML does not
    # put a second log4j in front of the server's anyway.
    left = jars_with_live_jndi(out)
    if [p for p in left if not p.startswith(os.path.join(out, "mods"))]:
        sys.exit("a live JndiLookup is still in: %s" % ", ".join(left))
    for p in left:
        print("WARNING: %s bundles its own JndiLookup (not modified)" % p)

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
    props_path = os.path.join(out, "server.properties")
    template = SERVER_PROPERTIES.format(online=eff["online-mode"], port=eff["server-port"],
                                        max_players=eff["max-players"],
                                        view_distance=eff["view-distance"])
    if os.path.exists(props_path):
        # Kept from the last build: change only what this command line asked
        # for, and add any key the template has gained since.
        with open(props_path, encoding="latin-1") as fh:
            lines = fh.read().splitlines()
        have = {l.split("=", 1)[0] for l in lines if "=" in l and not l.startswith("#")}
        for i, l in enumerate(lines):
            k = l.split("=", 1)[0]
            if given.get(k) is not None and l != "%s=%s" % (k, eff[k]):
                print("server.properties: %s -> %s" % (l, eff[k]))
                lines[i] = "%s=%s" % (k, eff[k])
        for l in template.splitlines():
            if l.split("=", 1)[0] not in have:
                print("server.properties: added %s" % l)
                lines.append(l)
        with open(props_path, "w", encoding="latin-1") as fh:
            fh.write("\n".join(lines) + "\n")
    else:
        with open(props_path, "w") as fh:
            fh.write(template)
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
            if props.get(key) != int(eff["view-distance"]):
                print("WARNING: JAS %r is %s but view-distance is %s"
                      % (key, props.get(key), eff["view-distance"]))

    # --- supervisor -----------------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    shutil.copy2(os.path.join(here, "supervisor.py"), os.path.join(out, "supervisor.py"))
    with open(os.path.join(out, "start-supervised.bat"), "w", newline="\r\n") as fh:
        fh.write(START_SUPERVISED_BAT)
    if not os.path.exists(os.path.join(out, "supervisor.json")):
        with open(os.path.join(out, "supervisor.json"), "w") as fh:
            json.dump(SUPERVISOR_JSON, fh, indent=2)
    print("supervisor: installed; start the server with start-supervised.bat")

    print("manifest: %d files hashed into MANIFEST.sha256" % write_manifest(out))

    with open(os.path.join(out, "BUILT-FROM.txt"), "w") as fh:
        fh.write("Assembled by tools/server/build_play_server.py\n")
        fh.write("Source instance: %s\n" % inst)
        fh.write("Mods kept: %d   dropped: %d\n\n" % (kept, dropped))
        fh.write("Dropped from the server (every client keeps them):\n")
        for prefix, why in CLIENT_ONLY:
            fh.write("  %-18s %s\n" % (prefix, why))
        fh.write("\nminecraft_server jar: JndiLookup.class replaced by an inert stub (Log4Shell).\n")
        fh.write("sha256 of every jar and config file: MANIFEST.sha256 (`sha256sum -c`).\n")
        fh.write("\nRebuild after ANY mod or config change on the clients; never edit here.\n")

    print("\nserver ready at %s -- start it with start-supervised.bat" % out)


if __name__ == "__main__":
    main()
