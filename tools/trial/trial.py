#!/usr/bin/env python3
"""Boot the pack with only the mods a trial needs.

WHY THIS EXISTS. A full-pack client takes ~3.5 minutes to reach the title screen
and ~6 GB of heap; most trials look at one block, one renderer or one mob. The
jukebox preview proved the point -- OptiFine plus qf-content loads in well under
a minute -- but it was a hand-built folder, and every other agent kept booting
all 122 jars.

A trial is a throwaway game dir under %APPDATA%\\.qf-trials\\<name>:
  mods/    hard links to the live instance's jars -- the base set from
           catalog.json, plus what you ask for, plus everything they require
  config/  a real copy, so a mod rewriting its config cannot touch the live pack
  options  copied from the live instance; pauseOnLostFocus off
  bin/, assets/  not copied: a client launch points straight at the live ones

`--server` builds a dedicated server instead: the same resolution minus the
client-only jars, with the Forge/vanilla server jars and libraries/ hard-linked
from an existing server dir.

Nothing here writes to %APPDATA%\\.crazycraft4 except `install`, which is the
one sanctioned way to put a jar there (it refuses while the live game is up,
keeps a backup, and logs who installed what).

ONE CLIENT AT A TIME. A second client once made the NVIDIA driver reset the GPU
and killed the user's own game with it. Launching a client refuses while any
Minecraft client is running and holds a lock file so two agents checking at the
same moment cannot both pass. Servers do not touch the GPU, but they all share
the same RAM: a server launch refuses when the heaps of every running Minecraft
JVM plus the new one would pass the budget (QF_RAM_BUDGET_GB, default 22).

Usage (py -3.10):
    trial.py list                               catalog, bundles, uncatalogued jars
    trial.py resolve qfcontent twilightforest   print the jar set, build nothing
    trial.py build NAME MOD... [--bundle inspect] [--world SAVE] [--shader off] [--server]
    trial.py launch NAME [--wait] [--xmx 3G] [-D key=value ...] [--commands FILE]
    trial.py status                             running clients/servers, lock, RAM
    trial.py install JAR [--why TEXT]           put a built jar into the live instance
    trial.py bisect start|good|bad|status|reset ...   halve a mod set to find a culprit
    trial.py disk                               instance copies on this PC and who uses them
    trial.py remove NAME
"""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
LIVE = os.path.join(APPDATA, ".crazycraft4")
TRIALS = os.path.join(APPDATA, ".qf-trials")
LOCK = os.path.join(TRIALS, "client.lock")
INSTALL_LOG = os.path.join(TRIALS, "install.log")
BISECT = os.path.join(TRIALS, "bisect.json")
JAVA_CANDIDATES = [r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe"]
MAIN = "net.minecraft.launchwrapper.Launch"
FORGE_JAR = "forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
SERVER_SOURCES = [r"C:\qfs\combat", r"C:\qfs\friends", r"C:\qfs\trial-base"]
RAM_BUDGET_GB = float(os.environ.get("QF_RAM_BUDGET_GB", "22"))

# Small top-level folders some mods read at startup. Copied, not linked: mods
# write into them (journeymap, customnpcs, hats).
COPY_DIRS = ["config", "scripts", "fonts", "customnpcs", "hats", "structures", "CustomDISkins"]
# Read-only client data, large: hard-linked file by file.
LINK_DIRS = ["resources", "resourcepacks", "shaderpacks"]
COPY_FILES = ["options.txt", "optionsof.txt", "optionsshaders.txt", "log4j2_17-111.xml",
              "betterfps.txt", "usernamecache.json", "pack.png"]

SHADERS = {
    "off": "OFF",
    "enhanced": "Sildur's Enhanced Default v1.19 Fancy.zip",
    "vibrant": "Sildur's Vibrant Shaders v2.01 High.zip",
}

SERVER_PROPERTIES = """\
level-name=world
level-seed={seed}
gamemode=1
difficulty=2
online-mode=false
spawn-protection=0
max-tick-time=-1
view-distance=6
spawn-npcs=false
spawn-animals=false
spawn-monsters=false
generate-structures=true
allow-nether=true
motd=QuestForge trial {name}
server-port={port}
"""


def load_catalog():
    with open(os.path.join(HERE, "catalog.json"), encoding="utf-8") as f:
        return json.load(f)


def instance_jars(src):
    """Every loadable jar in mods/ and mods/1.7.10/, as {relpath: path}.
    FML only loads *.jar / *.zip, so the .pre-* backups sitting in mods/ are skipped."""
    out = {}
    for sub in ("mods", os.path.join("mods", "1.7.10")):
        d = os.path.join(src, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if os.path.isfile(p) and f.lower().endswith((".jar", ".zip")):
                out[os.path.join(sub, f)] = p
    return out


def match_jar(entry, jars):
    pre = entry["match"].lower()
    return [rel for rel in jars if os.path.basename(rel).lower().startswith(pre)]


def key_of_jar(cat, filename):
    f = filename.lower()
    best = None
    for k, e in cat["mods"].items():
        m = e["match"].lower()
        if f.startswith(m) and (best is None or len(m) > len(cat["mods"][best]["match"])):
            best = k
    return best


def resolve(cat, wanted, bundles, src, no_base=False, server=False):
    mods = cat["mods"]
    client_only = set(cat.get("client_only", []))
    keys = [] if no_base else [k for k in cat["base"] if not (server and k in client_only)]
    for b in bundles:
        if b not in cat["bundles"]:
            sys.exit(f"unknown bundle '{b}'. Bundles: {', '.join(cat['bundles'])}")
        keys += [k for k in cat["bundles"][b]["mods"] if not (server and k in client_only)]
    keys += [lookup(cat, w) for w in wanted]
    order, seen = [], set()

    def visit(k, chain):
        if k in seen:
            return
        if k not in mods:
            sys.exit(f"catalog: '{chain[-1] if chain else '?'}' requires unknown entry '{k}'")
        if server and k in client_only:
            sys.exit(f"'{k}' is client-only and cannot run on a server"
                     + (f" (required by {' -> '.join(chain)})" if chain else ""))
        seen.add(k)
        for r in mods[k].get("requires", []):
            visit(r, chain + [k])
        order.append(k)

    for k in keys:
        visit(k, [])
    jars = instance_jars(src)
    picked, missing = [], []
    for k in order:
        hits = match_jar(mods[k], jars)
        if not hits:
            missing.append(k)
        picked += [(k, h, jars[h]) for h in hits]
    return picked, missing


def lookup(cat, name):
    """Accept a catalog key or a jar filename prefix."""
    n = name.lower().replace(".jar", "")
    mods = cat["mods"]
    if n in mods:
        return n
    hits = [k for k, e in mods.items()
            if e["match"].lower().startswith(n) or n.startswith(e["match"].lower().replace(".jar", ""))]
    if len(hits) == 1:
        return hits[0]
    if hits:
        sys.exit(f"'{name}' is ambiguous: {', '.join(hits)}")
    sys.exit(f"'{name}' is not in catalog.json. `trial.py list` shows every key; "
             f"if it is a new jar, add an entry.")


def link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def link_tree(src, dst):
    for root, _, files in os.walk(src):
        for f in files:
            s = os.path.join(root, f)
            link_or_copy(s, os.path.join(dst, os.path.relpath(s, src)))


def set_option(path, key, value, sep=":"):
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    done = False
    for i, l in enumerate(lines):
        if l.startswith(key + sep):
            lines[i] = f"{key}{sep}{value}"
            done = True
    if not done:
        lines.append(f"{key}{sep}{value}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def trial_dir(name):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        sys.exit("trial name: letters, digits, _ . - only")
    return os.path.join(TRIALS, name)


def read_manifest(name):
    p = os.path.join(trial_dir(name), "trial.json")
    if not os.path.isfile(p):
        sys.exit(f"no trial '{name}'. Build it first.")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------- build

def find_server_source(given):
    for s in ([given] if given else SERVER_SOURCES):
        if s and os.path.isfile(os.path.join(s, FORGE_JAR)) \
                and os.path.isfile(os.path.join(s, "minecraft_server.1.7.10.jar")) \
                and os.path.isdir(os.path.join(s, "libraries")):
            return s
    sys.exit("no server dir with the Forge universal jar, minecraft_server.1.7.10.jar and "
             f"libraries/ found (looked in {given or ', '.join(SERVER_SOURCES)}); pass --server-source")


def build(name, mods, bundle=(), src=LIVE, no_base=False, server=False, server_source=None,
          world=None, shader=None, overlay=(), force=False, port=None, seed="", quiet=False):
    cat = load_catalog()
    src = os.path.abspath(src)
    picked, missing = resolve(cat, mods, bundle, src, no_base, server)
    if missing and not quiet:
        print(f"note: no jar in {src} for: {', '.join(missing)}")
    d = trial_dir(name)
    if os.path.exists(d):
        if not force:
            sys.exit(f"{d} exists. --force rebuilds it (its world and logs are kept).")
        if trial_running(name):
            sys.exit(f"trial {name} is running; quit it first")
        for sub in ["mods"] + COPY_DIRS + LINK_DIRS:
            p = os.path.join(d, sub)
            if os.path.isdir(p):
                shutil.rmtree(p)
    os.makedirs(d, exist_ok=True)

    for _, rel, path in picked:
        link_or_copy(path, os.path.join(d, rel))
    for sub in COPY_DIRS:
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(d, sub), dirs_exist_ok=True)
    manifest = {"built": datetime.datetime.now().isoformat(timespec="seconds"),
                "source": src, "asked": list(mods), "bundles": list(bundle),
                "side": "server" if server else "client",
                "jars": [rel for _, rel, _ in picked]}
    if server:
        ss = find_server_source(server_source)
        for f in (FORGE_JAR, "minecraft_server.1.7.10.jar"):
            link_or_copy(os.path.join(ss, f), os.path.join(d, f))
        if not os.path.isdir(os.path.join(d, "libraries")):
            link_tree(os.path.join(ss, "libraries"), os.path.join(d, "libraries"))
        port = port or free_port()
        with open(os.path.join(d, "eula.txt"), "w") as f:
            f.write("eula=true\n")
        props = os.path.join(d, "server.properties")
        if force or not os.path.exists(props) or port:
            with open(props, "w") as f:
                f.write(SERVER_PROPERTIES.format(seed=seed, name=name, port=port))
        manifest.update(server_source=ss, port=port)
    else:
        for sub in LINK_DIRS:
            s = os.path.join(src, sub)
            if os.path.isdir(s):
                link_tree(s, os.path.join(d, sub))
        for f in COPY_FILES:
            s = os.path.join(src, f)
            if os.path.isfile(s) and (force or not os.path.exists(os.path.join(d, f))):
                shutil.copy2(s, os.path.join(d, f))
        set_option(os.path.join(d, "options.txt"), "pauseOnLostFocus", "false")
        if shader:
            set_option(os.path.join(d, "optionsshaders.txt"), "shaderPack",
                       SHADERS.get(shader, shader), sep="=")
    # Configs and scripts from the repo (or anywhere) on top -- how you trial a
    # change to pack/config before it is installed.
    for ov in overlay:
        for sub in os.listdir(ov):
            s = os.path.join(ov, sub)
            if os.path.isdir(s) and sub in ("config", "scripts", "resourcepacks"):
                shutil.copytree(s, os.path.join(d, sub), dirs_exist_ok=True)
    if world:
        ws = world if os.path.isdir(world) else os.path.join(src, "saves", world)
        if not os.path.isdir(ws):
            sys.exit(f"world not found: {ws}")
        # A server always loads level-name=world; a client lists saves/.
        wd = os.path.join(d, "world") if server else os.path.join(d, "saves", os.path.basename(ws.rstrip("\\/")))
        if os.path.exists(wd):
            shutil.rmtree(wd)
        shutil.copytree(ws, wd, ignore=shutil.ignore_patterns("session.lock"))

    with open(os.path.join(d, "trial.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    if not quiet:
        size = sum(os.path.getsize(p) for _, _, p in picked) / 1e6
        alljars = instance_jars(src)
        total = sum(os.path.getsize(p) for p in alljars.values()) / 1e6
        print(f"built {manifest['side']} trial {d}")
        print(f"  {len(picked)} of {len(alljars)} jars, {size:.0f} of {total:.0f} MB:")
        for _, rel, _ in picked:
            print(f"    {os.path.basename(rel)}")
        if server:
            print(f"  port {manifest['port']}, server jars from {manifest['server_source']}")
        print(f"next: py -3.10 tools/trial/trial.py launch {name} --wait")
    return manifest


def cmd_build(a):
    build(a.name, a.mods, a.bundle, a.source, a.no_base, a.server, a.server_source,
          a.world, a.shader, a.overlay, a.force, a.port, a.seed)


# -------------------------------------------------------------- processes/lock

def ps(script):
    # Output goes through a temp file, not a pipe: a JVM started by Start-Process
    # inherits PowerShell's handles, and a pipe would then stay open -- and this
    # call would block -- until the game exited.
    import tempfile
    with tempfile.TemporaryFile() as out:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       stdout=out, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        out.seek(0)
        return out.read().decode("utf-8", "replace")


def java_processes():
    """Every Minecraft JVM on the machine, client or server, whoever started it."""
    out = ps("@(Get-CimInstance Win32_Process -Filter \"Name like 'java%'\" | "
             "Select-Object ProcessId, CommandLine) | ConvertTo-Json -Compress")
    try:
        rows = json.loads(out) if out.strip() else []
    except ValueError:
        sys.exit(f"could not read the process list: {out[:200]}")
    if isinstance(rows, dict):
        rows = [rows]
    procs = []
    for r in rows:
        pid, cmdline = r["ProcessId"], r.get("CommandLine") or ""
        if MAIN in cmdline:
            kind = "client"
        elif "nogui" in cmdline or "GradleStart" in cmdline or "minecraft_server" in cmdline:
            kind = "server"
        else:
            continue
        m = re.search(r'--gameDir\s+"?([^"]+?)"?\s+--', cmdline)
        x = re.search(r"-Xmx(\d+)([MmGg])", cmdline)
        gb = (int(x.group(1)) / (1024 if x.group(2) in "Mm" else 1)) if x else 4.0
        procs.append({"pid": int(pid), "kind": kind, "gameDir": m.group(1) if m else "",
                      "xmx_gb": gb, "cmd": cmdline})
    return procs


def pid_alive(pid):
    if not pid:
        return False
    out = ps(f"if (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue) {{ 'yes' }}")
    return "yes" in out


def trial_running(name):
    p = os.path.join(trial_dir(name), "pid")
    try:
        with open(p) as f:
            return pid_alive(int(f.read().strip()))
    except (OSError, ValueError):
        return False


def read_lock():
    try:
        with open(LOCK, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def take_lock(info):
    os.makedirs(TRIALS, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            held = read_lock() or {}
            age = time.time() - held.get("at", 0)
            # A lock with no live java behind it is stale -- the launch it guarded
            # died or quit. The pid is written only once java has started, so
            # give a fresh lock 120 s to get there.
            if (held.get("pid") and not pid_alive(held["pid"])) or (not held.get("pid") and age > 120):
                os.remove(LOCK)
                continue
            return held
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(info, f)
        return None
    return read_lock()


def write_lock(info):
    with open(LOCK, "w", encoding="utf-8") as f:
        json.dump(info, f)


def ports_in_use():
    out = ps("Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
             "ForEach-Object { $_.LocalPort }")
    used = {int(x) for x in out.split() if x.isdigit()}
    if os.path.isdir(TRIALS):
        for n in os.listdir(TRIALS):
            try:
                with open(os.path.join(TRIALS, n, "trial.json"), encoding="utf-8") as f:
                    p = json.load(f).get("port")
                if p:
                    used.add(int(p))
            except (OSError, ValueError):
                pass
    # Ports other sessions' server dirs are configured for, running or not --
    # a benchmark between runs is not listening, but its next run will be.
    for root in (r"C:\qfs", r"C:\qfb", r"C:\qfm"):
        if not os.path.isdir(root):
            continue
        for n in os.listdir(root):
            try:
                with open(os.path.join(root, n, "server.properties"), encoding="utf-8", errors="replace") as f:
                    m = re.search(r"^server-port=(\d+)", f.read(), re.M)
                if m:
                    used.add(int(m.group(1)))
            except OSError:
                pass
    return used


def free_port(start=25600):
    used = ports_in_use()
    p = start
    while p in used:
        p += 1
    return p


# -------------------------------------------------------------------- launch

def find_java():
    for j in JAVA_CANDIDATES:
        if os.path.isfile(j):
            return j
    for base in (r"C:\Program Files\Java", r"C:\Program Files\Eclipse Adoptium"):
        if os.path.isdir(base):
            for d in sorted(os.listdir(base)):
                for p in (os.path.join(base, d, "bin", "java.exe"), os.path.join(base, d, "jre", "bin", "java.exe")):
                    if ("1.8" in d or "8.0" in d) and os.path.isfile(p):
                        return p
    sys.exit("Java 8 not found")


GC = ["-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:G1HeapRegionSize=16M",
      "-XX:ParallelGCThreads=4", "-XX:ConcGCThreads=2", "-XX:+UseCompressedOops",
      "-XX:+DisableExplicitGC", "-XX:-OmitStackTraceInFastThrow", "-XX:MaxPermSize=256M"]


def client_args(d, src, xmx, props):
    binp = os.path.join(src, "bin")
    cp = [os.path.join(binp, "minecraft.jar")] + sorted(
        os.path.join(binp, "lib", f) for f in os.listdir(os.path.join(binp, "lib")) if f.endswith(".jar"))
    jvm = [
        "-Djava.net.preferIPv4Stack=true",
        "-Dfml.ignoreInvalidMinecraftCertificates=true",
        "-Dfml.ignorePatchDiscrepancies=true",
        "-Dlog4j2.formatMsgNoLookups=true",
        f"-Dlog4j.configurationFile={os.path.join(d, 'log4j2_17-111.xml')}",
        f"-Djava.library.path={os.path.join(binp, 'natives')}",
        "-Xms1024M", f"-Xmx{xmx}", "-XX:+UseSplitVerifier", "-XX:+FailOverToOldVerifier",
    ] + GC + [f"-D{p}" for p in props]
    game = [MAIN, "--username", "Dev", "--accessToken", "0",
            "--uuid", "00000000-0000-0000-0000-000000000000",
            "--version", "1.7.10", "--assetIndex", "1.7.10",
            "--tweakClass", "cpw.mods.fml.common.launcher.FMLTweaker",
            "--gameDir", d, "--assetsDir", os.path.join(src, "assets"),
            "--userProperties", "{}"]
    return jvm + ["-cp", ";".join(cp)] + game


def server_args(xmx, props):
    return (["-Xms512M", f"-Xmx{xmx}", "-Dlog4j2.formatMsgNoLookups=true",
             "-Dfml.queryResult=confirm"] + GC + [f"-D{p}" for p in props]
            + ["-jar", FORGE_JAR, "nogui"])


def gb(xmx):
    m = re.fullmatch(r"(\d+)([MmGg])", xmx)
    if not m:
        sys.exit(f"--xmx {xmx}: use e.g. 3G or 3072M")
    return int(m.group(1)) / (1024 if m.group(2) in "Mm" else 1)


def start_detached(java, args, d, stdin=None):
    # Started through PowerShell Start-Process so the JVM is not a child of the
    # calling shell: a client launched from a backgrounded Bash task is reaped
    # within seconds at the title screen.
    def q(s):
        return "'" + s.replace("'", "''") + "'"
    extra = f"-RedirectStandardInput {q(stdin)} " if stdin else ""
    script = (f"$p = Start-Process -FilePath {q(java)} -ArgumentList {q(subprocess.list2cmdline(args))} "
              f"-WorkingDirectory {q(d)} -WindowStyle {'Minimized' if stdin or 'nogui' in args else 'Normal'} "
              f"-RedirectStandardOutput {q(os.path.join(d, 'stdout.log'))} "
              f"-RedirectStandardError {q(os.path.join(d, 'stderr.log'))} {extra}-PassThru; $p.Id")
    out = ps(script).strip().splitlines()
    try:
        return int(out[-1])
    except (ValueError, IndexError):
        return None


def cmd_launch(a):
    man = read_manifest(a.name)
    d = trial_dir(a.name)
    if man.get("side") == "server":
        return launch_server(a, man, d)
    src = man["source"]
    running = [p for p in java_processes() if p["kind"] == "client"]
    if running:
        print("refusing to launch: a Minecraft client is already running.")
        for p in running:
            print(f"  pid {p['pid']}  -Xmx{p['xmx_gb']:g}G  {p['gameDir']}")
        print("Two clients at once has reset the GPU and killed both. Wait for it to exit,\n"
              "or ask whoever owns it. (`trial.py status` shows who holds the lock.)")
        sys.exit(2)
    check_ram(gb(a.xmx))
    me = {"trial": a.name, "pid": None, "at": time.time(),
          "owner": a.owner or os.environ.get("CLAUDE_SESSION_NAME", "")}
    held = take_lock(me)
    if held:
        sys.exit(f"refusing to launch: lock held by trial '{held.get('trial')}' "
                 f"(pid {held.get('pid')}, owner {held.get('owner') or '?'})")

    java = find_java()
    args = client_args(d, src, a.xmx, a.D)
    clear_logs(d, "client")
    write_bat(d, java, args)
    pid = start_detached(java, args, d)
    if not pid:
        os.remove(LOCK)
        sys.exit("launch failed: Start-Process returned no pid")
    me["pid"] = pid
    write_lock(me)
    with open(os.path.join(d, "pid"), "w") as f:
        f.write(str(pid))
    print(f"launched client trial {a.name}: pid {pid}, {len(man['jars'])} jars, -Xmx{a.xmx}")
    print(f"  log: {os.path.join(d, 'logs', 'latest.log')}")
    if a.wait:
        sys.exit(wait_loaded(d, pid, a.timeout, "client"))


def check_ram(new_gb):
    procs = java_processes()
    used = sum(p["xmx_gb"] for p in procs)
    if used + new_gb > RAM_BUDGET_GB:
        print(f"refusing to launch: Minecraft JVMs already reserve {used:g} GB of heap; "
              f"+{new_gb:g} GB would pass the {RAM_BUDGET_GB:g} GB budget (QF_RAM_BUDGET_GB).")
        for p in procs:
            print(f"  {p['kind']:6} pid {p['pid']:<6} -Xmx{p['xmx_gb']:g}G  {p['gameDir'] or server_dir(p['pid'])}")
        print("Wait for one to finish, or run with a smaller --xmx.")
        sys.exit(2)


def server_dir(pid):
    # Windows does not expose another process's cwd cheaply; the trial pid files can.
    if os.path.isdir(TRIALS):
        for n in os.listdir(TRIALS):
            try:
                with open(os.path.join(TRIALS, n, "pid")) as f:
                    if int(f.read().strip()) == pid:
                        return trial_dir(n)
            except (OSError, ValueError):
                pass
    return "(server outside .qf-trials)"


def launch_server(a, man, d):
    if trial_running(a.name):
        sys.exit(f"trial {a.name} is already running")
    port = man.get("port")
    listening = ps("Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
                   "ForEach-Object { $_.LocalPort }").split()
    if port and str(port) in listening:
        sys.exit(f"port {port} is taken (a leftover server keeps appending to the old files); "
                 f"`build --force --port N` or stop it first")
    check_ram(gb(a.xmx))
    java = find_java()
    args = server_args(a.xmx, a.D)
    clear_logs(d, "server")
    write_bat(d, java, args)
    pid = start_detached(java, args, d, stdin=os.path.abspath(a.commands) if a.commands else None)
    if not pid:
        sys.exit("launch failed: Start-Process returned no pid")
    with open(os.path.join(d, "pid"), "w") as f:
        f.write(str(pid))
    print(f"launched server trial {a.name}: pid {pid}, port {port}, {len(man['jars'])} jars, -Xmx{a.xmx}")
    print(f"  log: {os.path.join(d, 'logs', 'latest.log')}")
    if a.wait:
        sys.exit(wait_loaded(d, pid, a.timeout, "server"))


def clear_logs(d, side):
    logs = os.path.join(d, "logs")
    os.makedirs(logs, exist_ok=True)
    for stale in (f"fml-{side}-latest.log", "latest.log"):
        try:
            os.remove(os.path.join(logs, stale))
        except OSError:
            pass


def write_bat(d, java, args):
    with open(os.path.join(d, "LAUNCH.bat"), "w", encoding="utf-8") as f:
        f.write("@echo off\r\nrem written by tools/trial/trial.py -- same command the agent ran\r\n")
        f.write(f'cd /d "{d}"\r\n' + subprocess.list2cmdline([java] + args) + "\r\npause\r\n")


# The pack's log4j2_17-111.xml writes only latest.log (no fml-client-latest.log),
# so that is the file followed. The client reloads resources twice -- after
# preInit and again after postInit -- and each reload restarts the sound engine,
# so the SECOND "Sound engine started" is the title screen (true of a 2-mod
# trial and of the full 142-mod pack alike). "Done (" is a server's ready line.
LOADED = {"client": re.compile(r"Sound engine started"),
          "server": re.compile(r"Done \(([\d.]+)s\)!")}
FAIL = re.compile(r"(MissingModsException|requires mods \[|DuplicateModsFoundException|"
                  r"NoClassDefFoundError: (\S+)|ClassNotFoundException: (\S+)|"
                  r"There was a critical error|---- Minecraft Crash Report ----|FAILED TO BIND)")


def wait_loaded(d, pid, timeout, side):
    """Follow the FML log until loaded, a crash, or the JVM exits.
    Bounded and quiet: run it as a background task, not a foreground sleep loop."""
    log = os.path.join(d, "logs", "latest.log")
    t0, pos, classes, hits = time.time(), 0, set(), 0
    need = 2 if side == "client" else 1
    unminimized = side == "server"
    while time.time() - t0 < timeout:
        if os.path.exists(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                chunk = f.read()
                pos = f.tell()
            for line in chunk.splitlines():
                m = LOADED[side].search(line)
                if m:
                    hits += 1
                if m and hits >= need:
                    what = "title screen" if side == "client" else "server ready"
                    print(f"loaded: {what} after {time.time() - t0:.0f} s")
                    return 0
                m = FAIL.search(line)
                # Soft integrations probe for absent mods and log ClassNotFound
                # at WARN (Waila alone logs a dozen); only errors count.
                if m and "/WARN]" not in line and "/INFO]" not in line:
                    print("  " + line.strip()[:240])
                    for c in (m.group(2), m.group(3)):
                        if c:
                            classes.add(c.replace("/", ".").rstrip(":"))
        if not unminimized and time.time() - t0 > 8:
            # Launched from a non-interactive shell the window can start minimized
            # and the client stalls. SW_SHOWNOACTIVATE: visible, no focus steal.
            ps("Add-Type -Name W -Namespace Q -MemberDefinition '[DllImport(\"user32.dll\")] "
               "public static extern bool ShowWindow(System.IntPtr h, int c);'; "
               f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
               "if ($p -and $p.MainWindowHandle -ne 0) { [Q.W]::ShowWindow($p.MainWindowHandle, 4) | Out-Null }")
            unminimized = True
        if not pid_alive(pid):
            print(f"{side} exited after {time.time() - t0:.0f} s without finishing load")
            break
        time.sleep(2)
    else:
        print(f"still loading after {timeout} s; it is left running")
        return 1
    if classes:
        suggest_owner(classes, d)
    crash = os.path.join(d, "crash-reports")
    if os.path.isdir(crash):
        latest = max((os.path.join(crash, f) for f in os.listdir(crash)), key=os.path.getmtime, default=None)
        if latest:
            print(f"  crash report: {latest}")
    return 3


def suggest_owner(classes, d):
    """Name the live jar that defines each missing class, so the catalog can learn it."""
    cat = load_catalog()
    jars = instance_jars(LIVE)
    loaded = {os.path.basename(r).lower() for r in instance_jars(d)}
    for c in sorted(classes):
        path = c.replace(".", "/") + ".class"
        owner = None
        for rel, p in jars.items():
            try:
                with zipfile.ZipFile(p) as z:
                    z.getinfo(path)
                owner = os.path.basename(rel)
                break
            except (KeyError, zipfile.BadZipFile, OSError):
                continue
        if owner and owner.lower() in loaded:
            print(f"  {c} is in {owner}, which IS loaded -- it failed because of another missing class above")
        elif owner:
            print(f"  missing {c} -> lives in {owner} (catalog key '{key_of_jar(cat, owner)}'): add it to "
                  f"the trial, and to 'requires' in catalog.json")
        else:
            print(f"  missing {c} -> not in any pack jar (a client-only class on a server, or a dead integration)")


# ------------------------------------------------------------------- install

def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def cmd_install(a):
    """The one way a jar goes into the live instance.

    Agents used to Copy-Item builds straight over .crazycraft4\\mods while the user
    played and while other agents were building servers from it. This refuses
    while anything runs from the live instance, replaces atomically (a reader
    sees the old jar or the new one, never half of one), keeps the old jar out
    of mods/ so FML cannot load both, and logs who did it.
    """
    jar = os.path.abspath(a.jar)
    if not os.path.isfile(jar) or not jar.lower().endswith(".jar"):
        sys.exit(f"not a jar: {jar}")
    if jar.lower().endswith("-dev.jar"):
        sys.exit("that is the deobfuscated -dev jar; it crashes in the pack with NoSuchMethodError. "
                 "Install build/libs/<name>.jar (the reobfuscated one).")
    live_users = [p for p in java_processes()
                  if os.path.normcase(LIVE) in os.path.normcase(p["cmd"]) and
                  (p["kind"] == "server" or os.path.normcase(p["gameDir"]) == os.path.normcase(LIVE))]
    if live_users and not a.force:
        print("refusing to install: the live instance is in use (the user's game, or a server built from it):")
        for p in live_users:
            print(f"  {p['kind']} pid {p['pid']} {p['gameDir']}")
        print("A jar swapped under a running game is not what that game loaded. Wait for it to exit.")
        sys.exit(2)
    name = os.path.basename(jar)
    mods = os.path.join(LIVE, "mods")
    dst = os.path.join(mods, a.as_name or name)
    if not os.path.isfile(dst):
        cat = load_catalog()
        k = key_of_jar(cat, name)
        same = [r for r in instance_jars(LIVE) if k and key_of_jar(cat, os.path.basename(r)) == k]
        if same:
            sys.exit(f"{name} would sit next to {', '.join(same)}; FML would load both. "
                     f"Pass --as {os.path.basename(same[0])} to replace it.")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    old_sha = None
    if os.path.isfile(dst):
        old_sha = sha1(dst)
        if old_sha == sha1(jar):
            print(f"{os.path.basename(dst)} is already that build ({old_sha}); nothing to do")
            return
        bdir = os.path.join(LIVE, f"_backup-install-{stamp}")
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(dst, os.path.join(bdir, os.path.basename(dst)))
    tmp = dst + ".installing"
    shutil.copy2(jar, tmp)
    os.replace(tmp, dst)
    os.makedirs(TRIALS, exist_ok=True)
    who = a.owner or os.environ.get("CLAUDE_SESSION_NAME", "?")
    line = (f"{stamp}\t{who}\t{os.path.basename(dst)}\t{old_sha or '-'} -> {sha1(dst)}\t"
            f"{jar}\t{a.why or ''}\n")
    with open(INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"installed {os.path.basename(dst)} ({old_sha or 'new'} -> {sha1(dst)})"
          + (f"; previous kept in _backup-install-{stamp}" if old_sha else ""))
    print(f"logged in {INSTALL_LOG}")


# -------------------------------------------------------------------- bisect

def cmd_bisect(a):
    """Halve a suspect set until one jar is left.

    start: the suspects (default: every non-base mod in the live pack) are split;
    the first half is built as trial NAME. Reproduce, then say `good` (bug gone)
    or `bad` (bug still there); the next half is built. Libraries ride along
    with whatever needs them, so they are never suspects themselves.
    """
    cat = load_catalog()
    if a.action == "start":
        if os.path.exists(BISECT) and not a.force:
            sys.exit(f"a bisect is in progress ({BISECT}); `bisect reset` or --force")
        if a.mods:
            suspects = [lookup(cat, m) for m in a.mods]
        else:
            present = {key_of_jar(cat, os.path.basename(r)) for r in instance_jars(LIVE)}
            suspects = sorted(k for k in present if k and cat["mods"][k]["role"] == "mod"
                              and k not in cat["base"])
        keep = [lookup(cat, m) for m in a.keep]
        suspects = [s for s in suspects if s not in keep]
        if a.server:
            suspects = [s for s in suspects if s not in cat.get("client_only", [])]
        st = {"name": a.name, "suspects": suspects, "keep": keep, "server": a.server,
              "bundle": a.bundle, "history": []}
    else:
        if not os.path.exists(BISECT):
            sys.exit("no bisect in progress")
        with open(BISECT, encoding="utf-8") as f:
            st = json.load(f)
        if a.action == "reset":
            os.remove(BISECT)
            print("bisect state cleared (the trial dir is left; `remove` it when done)")
            return
        if a.action == "status":
            print(json.dumps(st, indent=1))
            return
        half = st["testing"]
        rest = [s for s in st["suspects"] if s not in half]
        st["history"].append({"tested": half, "result": a.action})
        st["suspects"] = half if a.action == "bad" else rest
    if len(st["suspects"]) <= 1:
        print(f"culprit: {st['suspects'][0] if st['suspects'] else 'none -- the bug is in the kept set'}"
              f" (after {len(st['history'])} boots)")
        os.remove(BISECT) if os.path.exists(BISECT) else None
        return
    half = st["suspects"][: len(st["suspects"]) // 2]
    st["testing"] = half
    build(st["name"], st["keep"] + half, st["bundle"], server=st["server"], force=True, quiet=True)
    with open(BISECT, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    steps = max(1, (len(st["suspects"]) - 1).bit_length())
    print(f"{len(st['suspects'])} suspects left (~{steps} more boots). Trial '{st['name']}' now has "
          f"{len(half)}: {', '.join(half)}")
    print(f"launch it, reproduce, then `trial.py bisect bad` (still broken) or `good` (fixed)")


# ---------------------------------------------------------------------- disk

def dir_size(p):
    total = 0
    for root, dirs, files in os.walk(p):
        # Never follow junctions: a junction into the live instance would be
        # counted (and, for a careless delete, wiped) as if it were this dir's.
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))
                   and not is_junction(os.path.join(root, d))]
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def is_junction(p):
    try:
        return bool(os.stat(p, follow_symlinks=False).st_file_attributes & 0x400)
    except (OSError, AttributeError):
        return False


def cmd_disk(a):
    """Every game/server dir on this PC with its size, age and whether a JVM uses it.
    Read-only: it lists candidates; deleting is a decision for the user."""
    roots = [APPDATA, r"C:\qfs", r"C:\qfb", r"C:\qfm", TRIALS]
    cands = []
    for r in roots:
        if not os.path.isdir(r):
            continue
        for n in os.listdir(r):
            p = os.path.join(r, n)
            if not os.path.isdir(p) or p == TRIALS:
                continue
            if any(os.path.exists(os.path.join(p, x)) for x in ("mods", "client", "server", "options.txt")):
                cands.append(p)
    procs = java_processes()
    rows = []
    for p in cands:
        np_ = os.path.normcase(p)
        users = [str(x["pid"]) for x in procs if np_ in os.path.normcase(x["cmd"]) or
                 os.path.normcase(x["gameDir"]).startswith(np_)]
        junctions = [n for n in os.listdir(p) if is_junction(os.path.join(p, n))]
        newest = max((os.path.getmtime(os.path.join(p, n)) for n in os.listdir(p)), default=0)
        logs = os.path.join(p, "logs")
        logm = max((os.path.getmtime(os.path.join(logs, n)) for n in os.listdir(logs)), default=0)             if os.path.isdir(logs) else 0
        rows.append((dir_size(p) / 1e9, p, users, junctions, max(newest, logm), logm))
    for size, p, users, junctions, newest, logm in sorted(rows, reverse=True):
        age = (time.time() - newest) / 86400
        # A server's cwd is not in its command line; a log written in the last
        # two minutes is the cheap tell that something is running there.
        if users:
            flag = f"IN USE by pid {','.join(users)}"
        elif time.time() - logm < 120:
            flag = "ACTIVE (log < 2 min)"
        else:
            flag = f"idle {age:.1f} d" if age < 1 else f"idle {age:.0f} d"
        if os.path.normcase(p) == os.path.normcase(LIVE):
            flag = "LIVE INSTANCE"
        print(f"{size:6.2f} GB  {flag:22} {p}" + (f"  JUNCTIONS: {', '.join(junctions)}" if junctions else ""))
    backups = [n for n in os.listdir(LIVE) if n.startswith(("_backup", "_work")) or ".pre-" in n]
    bsize = sum(dir_size(os.path.join(LIVE, n)) if os.path.isdir(os.path.join(LIVE, n))
                else os.path.getsize(os.path.join(LIVE, n)) for n in backups) / 1e9
    print(f"\n{len(backups)} backup/work entries inside the live instance: {bsize:.2f} GB")
    stale = [f for f in os.listdir(os.path.join(LIVE, "mods")) if re.search(r"\.(jar|zip)\.", f)]
    if stale:
        print(f"{len(stale)} jar backups inside live mods/ (FML ignores them): {', '.join(stale)}")


# --------------------------------------------------------------- misc commands

def cmd_status(a):
    procs = java_processes()
    if not procs:
        print("no Minecraft clients or servers running")
    for p in procs:
        where = p["gameDir"] or server_dir(p["pid"])
        print(f"{p['kind']:6} pid {p['pid']:<6} {('-Xmx%gG' % p['xmx_gb']):9} {where}")
    used = sum(p["xmx_gb"] for p in procs)
    print(f"heap reserved: {used:g} of {RAM_BUDGET_GB:g} GB budget")
    held = read_lock()
    if held:
        alive = pid_alive(held.get("pid"))
        print(f"client lock: trial '{held.get('trial')}' pid {held.get('pid')} owner {held.get('owner') or '?'}"
              f" {'(running)' if alive else '(stale)'}")
    if os.path.exists(BISECT):
        print(f"bisect in progress: {BISECT}")
    if os.path.isdir(TRIALS):
        names = [n for n in os.listdir(TRIALS) if os.path.isfile(os.path.join(TRIALS, n, "trial.json"))]
        if names:
            print("trials: " + ", ".join(sorted(names)))


def cmd_list(a):
    cat = load_catalog()
    jars = instance_jars(LIVE)
    co = set(cat.get("client_only", []))

    def mb(k):
        return sum(os.path.getsize(jars[h]) for h in match_jar(cat["mods"][k], jars)) / 1e6
    print("base (every trial):")
    for k in cat["base"]:
        print(f"  {k:18} {mb(k):6.1f} MB  {cat['mods'][k].get('why', '')}")
    print("bundles:")
    for b, e in cat["bundles"].items():
        print(f"  --bundle {b:10} {' '.join(e['mods']):45} {e['why']}")
    print("mods:")
    for k, e in sorted(cat["mods"].items()):
        if e["role"] == "base":
            continue
        req = f" requires {','.join(e['requires'])}" if e.get("requires") else ""
        print(f"  {k:18} {mb(k):6.1f} MB  {e['role']}{' client-only' if k in co else ''}{req}")
    covered = {h for e in cat["mods"].values() for h in match_jar(e, jars)}
    stray = [os.path.basename(j) for j in jars if j not in covered]
    if stray:
        print("NOT IN CATALOG (a trial can never load these -- add entries):")
        for s in stray:
            print(f"  {s}")


def cmd_resolve(a):
    picked, missing = resolve(load_catalog(), a.mods, a.bundle, os.path.abspath(a.source), a.no_base, a.server)
    for k, rel, p in picked:
        print(f"{k:18} {os.path.getsize(p) / 1e6:7.1f} MB  {rel}")
    if missing:
        print(f"no jar for: {', '.join(missing)}")


def cmd_remove(a):
    d = trial_dir(a.name)
    if trial_running(a.name):
        sys.exit(f"trial {a.name} is running")
    # Hard links and copies only -- no junctions -- so a recursive delete
    # cannot reach the live instance. Checked anyway.
    for root, dirs, _ in os.walk(d):
        for x in dirs:
            if is_junction(os.path.join(root, x)):
                sys.exit(f"{os.path.join(root, x)} is a junction; unlink it with `cmd /c rmdir` first")
    shutil.rmtree(d)
    print(f"removed {d}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    def mods_args(p):
        p.add_argument("mods", nargs="*", help="catalog keys or jar name prefixes (see `list`)")
        p.add_argument("--bundle", action="append", default=[], help="named group from catalog.json")
        p.add_argument("--no-base", action="store_true", help="skip the base visual/perf set (rarely right)")
        p.add_argument("--source", default=LIVE, help="instance to take jars/config from (default: live)")
        p.add_argument("--server", action="store_true", help="dedicated server; client-only jars dropped")

    p = sp.add_parser("build"); p.add_argument("name"); mods_args(p)
    p.add_argument("--world", help="save name in the source's saves/, or a path; copied in")
    p.add_argument("--shader", help="client: off | enhanced | vibrant | <zip name> (default: as live)")
    p.add_argument("--overlay", action="append", default=[],
                   help="dir whose config/ scripts/ resourcepacks/ go on top, e.g. the repo's pack/")
    p.add_argument("--server-source", help="dir holding the Forge/vanilla server jars and libraries/")
    p.add_argument("--port", type=int, help="server port (default: first free from 25600)")
    p.add_argument("--seed", default="", help="server world seed")
    p.add_argument("--force", action="store_true", help="rebuild an existing trial")
    p.set_defaults(fn=cmd_build)

    p = sp.add_parser("launch"); p.add_argument("name")
    p.add_argument("--xmx", default="3G", help="heap; the slim set rarely needs more than 3G")
    p.add_argument("-D", action="append", default=[], metavar="KEY=VALUE", help="system property")
    p.add_argument("--wait", action="store_true", help="follow the log until loaded / crashed")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--commands", help="server: file of console commands fed on stdin")
    p.add_argument("--owner", help="who to name in the lock (default: $CLAUDE_SESSION_NAME)")
    p.set_defaults(fn=cmd_launch)

    p = sp.add_parser("install"); p.add_argument("jar")
    p.add_argument("--as", dest="as_name", help="filename in mods/ to replace (default: the jar's own)")
    p.add_argument("--why", help="one line for the install log")
    p.add_argument("--owner", help="who to log (default: $CLAUDE_SESSION_NAME)")
    p.add_argument("--force", action="store_true", help="install even though the live instance is in use")
    p.set_defaults(fn=cmd_install)

    p = sp.add_parser("bisect"); p.add_argument("action", choices=["start", "good", "bad", "status", "reset"])
    p.add_argument("--name", default="bisect")
    p.add_argument("mods", nargs="*", help="start: suspects (default: every non-base mod)")
    p.add_argument("--keep", action="append", default=[], help="start: always loaded, never a suspect")
    p.add_argument("--bundle", action="append", default=[])
    p.add_argument("--server", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_bisect)

    p = sp.add_parser("resolve"); mods_args(p); p.set_defaults(fn=cmd_resolve)
    sp.add_parser("list").set_defaults(fn=cmd_list)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    sp.add_parser("disk").set_defaults(fn=cmd_disk)
    p = sp.add_parser("remove"); p.add_argument("name"); p.set_defaults(fn=cmd_remove)
    # Mods may come before or after any option (`build x --force a b`); argparse
    # alone stops collecting positionals at the first option.
    a, extra = ap.parse_known_args()
    if extra:
        if hasattr(a, "mods") and not any(x.startswith("-") for x in extra):
            a.mods += extra
        else:
            ap.error(f"unrecognized arguments: {' '.join(extra)}")
    a.fn(a)


if __name__ == "__main__":
    main()
