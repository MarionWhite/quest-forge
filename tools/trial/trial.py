#!/usr/bin/env python3
"""Boot the pack with only the mods a trial needs.

WHY THIS EXISTS. A full-pack client takes ~3.5 minutes to reach the title screen
and ~6 GB of heap; most trials look at one block, one renderer or one mob. The
jukebox preview proved the point -- OptiFine plus qf-content loads in ~10 s --
but it was a hand-built folder, and every other agent kept booting all 122 jars.

A trial is a throwaway game dir under %APPDATA%\\.qf-trials\\<name>:
  mods/    hard links to the live instance's jars -- the base set from
           catalog.json, plus what you ask for, plus everything they require
  config/  a real copy, so a mod rewriting its config cannot touch the live pack
  options  copied from the live instance; pauseOnLostFocus off
  bin/, assets/  not copied: the launch points straight at the live ones

It never writes to %APPDATA%\\.crazycraft4.

ONE CLIENT AT A TIME. A second client once made the NVIDIA driver reset the GPU
and killed the user's own game with it. `launch` refuses while any Minecraft
client is running -- the user's, another agent's, or another trial -- and holds
a lock file so two agents checking at the same moment cannot both pass.

Usage (py -3.10):
    trial.py list                           catalog, bundles, uncatalogued jars
    trial.py resolve qfcontent twilightforest   print the jar set, build nothing
    trial.py build NAME MOD... [--bundle inspect] [--world SAVE] [--shader off]
    trial.py launch NAME [--wait] [--xmx 3G] [-D key=value ...]
    trial.py status                         running clients/servers + lock holder
    trial.py remove NAME
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
LIVE = os.path.join(APPDATA, ".crazycraft4")
TRIALS = os.path.join(APPDATA, ".qf-trials")
LOCK = os.path.join(TRIALS, "client.lock")
JAVA_CANDIDATES = [r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe"]
MAIN = "net.minecraft.launchwrapper.Launch"

# Small top-level folders some mods read at startup. Copied, not linked: mods
# write into them (journeymap, customnpcs, hats).
COPY_DIRS = ["config", "scripts", "fonts", "customnpcs", "hats", "structures", "CustomDISkins"]
# Read-only data, large: hard-linked file by file.
LINK_DIRS = ["resources", "resourcepacks", "shaderpacks"]
COPY_FILES = ["options.txt", "optionsof.txt", "optionsshaders.txt", "log4j2_17-111.xml",
              "betterfps.txt", "usernamecache.json", "pack.png"]

SHADERS = {
    "off": "OFF",
    "enhanced": "Sildur's Enhanced Default v1.19 Fancy.zip",
    "vibrant": "Sildur's Vibrant Shaders v2.01 High.zip",
}


def load_catalog():
    with open(os.path.join(HERE, "catalog.json"), encoding="utf-8") as f:
        return json.load(f)


def instance_jars(src):
    """Every loadable jar in mods/ and mods/1.7.10/, as {filename: path}.
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
    hits = [rel for rel in jars if os.path.basename(rel).lower().startswith(pre)]
    return hits


def resolve(cat, wanted, bundles, src, no_base=False):
    mods = cat["mods"]
    keys = [] if no_base else list(cat["base"])
    for b in bundles:
        if b not in cat["bundles"]:
            sys.exit(f"unknown bundle '{b}'. Bundles: {', '.join(cat['bundles'])}")
        keys += cat["bundles"][b]["mods"]
    for w in wanted:
        k = lookup(cat, w)
        keys.append(k)
    order, seen = [], set()

    def visit(k, chain):
        if k in seen:
            return
        if k not in mods:
            sys.exit(f"catalog: '{chain[-1] if chain else '?'}' requires unknown entry '{k}'")
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
    """Accept a catalog key, a modid-ish name or a jar filename prefix."""
    n = name.lower().replace(".jar", "")
    mods = cat["mods"]
    if n in mods:
        return n
    hits = [k for k, e in mods.items() if e["match"].lower().startswith(n) or n.startswith(e["match"].lower().replace(".jar", ""))]
    if len(hits) == 1:
        return hits[0]
    if hits:
        sys.exit(f"'{name}' is ambiguous: {', '.join(hits)}")
    sys.exit(f"'{name}' is not in catalog.json. `trial.py list` shows every key; "
             f"if it is a new jar, add an entry.")


def link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
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


# --------------------------------------------------------------------- build

def cmd_build(a):
    cat = load_catalog()
    src = os.path.abspath(a.source)
    picked, missing = resolve(cat, a.mods, a.bundle, src, a.no_base)
    if missing:
        print(f"note: no jar in {src} for: {', '.join(missing)}")
    d = trial_dir(a.name)
    if os.path.exists(d):
        if not a.force:
            sys.exit(f"{d} exists. --force rebuilds it (its world and logs are kept).")
        holder = read_lock()
        if holder and holder.get("trial") == a.name and pid_alive(holder.get("pid")):
            sys.exit(f"trial {a.name} is running (pid {holder['pid']}); quit it first")
        for sub in ["mods"] + COPY_DIRS + LINK_DIRS:
            p = os.path.join(d, sub)
            if os.path.isdir(p):
                shutil.rmtree(p)
    os.makedirs(d, exist_ok=True)

    for k, rel, path in picked:
        link_or_copy(path, os.path.join(d, rel))
    for sub in COPY_DIRS:
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(d, sub), dirs_exist_ok=True)
    for sub in LINK_DIRS:
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            link_tree(s, os.path.join(d, sub))
    for f in COPY_FILES:
        s = os.path.join(src, f)
        if os.path.isfile(s) and (a.force or not os.path.exists(os.path.join(d, f))):
            shutil.copy2(s, os.path.join(d, f))
    # Configs and scripts from the repo (or anywhere) on top -- how you trial a
    # change to pack/config before it is installed.
    for ov in a.overlay:
        for sub in os.listdir(ov):
            s = os.path.join(ov, sub)
            if os.path.isdir(s) and sub in ("config", "scripts", "resourcepacks"):
                shutil.copytree(s, os.path.join(d, sub), dirs_exist_ok=True)
    set_option(os.path.join(d, "options.txt"), "pauseOnLostFocus", "false")
    if a.shader:
        set_option(os.path.join(d, "optionsshaders.txt"), "shaderPack",
                   SHADERS.get(a.shader, a.shader), sep="=")
    if a.world:
        ws = a.world if os.path.isdir(a.world) else os.path.join(src, "saves", a.world)
        if not os.path.isdir(ws):
            sys.exit(f"world not found: {ws}")
        wd = os.path.join(d, "saves", os.path.basename(ws.rstrip("\\/")))
        if os.path.exists(wd):
            shutil.rmtree(wd)
        shutil.copytree(ws, wd, ignore=shutil.ignore_patterns("session.lock"))

    manifest = {"built": datetime.datetime.now().isoformat(timespec="seconds"),
                "source": src, "asked": a.mods, "bundles": a.bundle,
                "jars": [rel for _, rel, _ in picked]}
    with open(os.path.join(d, "trial.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    size = sum(os.path.getsize(p) for _, _, p in picked) / 1e6
    total = sum(os.path.getsize(p) for p in instance_jars(src).values()) / 1e6
    print(f"built {d}")
    print(f"  {len(picked)} of {len(instance_jars(src))} jars, {size:.0f} of {total:.0f} MB:")
    for k, rel, _ in picked:
        print(f"    {os.path.basename(rel)}")
    print(f"next: py -3.10 {os.path.relpath(__file__)} launch {a.name} --wait")


# -------------------------------------------------------------- processes/lock

def ps(script):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True)
    return r.stdout


def java_processes():
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
        elif "nogui" in cmdline or "runServer" in cmdline or "minecraft_server" in cmdline:
            kind = "server"
        else:
            continue
        m = re.search(r'--gameDir\s+"?([^"]+?)"?\s+--', cmdline)
        x = re.search(r"-Xmx(\S+)", cmdline)
        procs.append({"pid": int(pid), "kind": kind, "gameDir": m.group(1) if m else "",
                      "xmx": x.group(1) if x else "?"})
    return procs


def pid_alive(pid):
    if not pid:
        return False
    out = ps(f"if (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue) {{ 'yes' }}")
    return "yes" in out


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


def build_args(d, src, xmx, props):
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
        "-Xms1024M", f"-Xmx{xmx}", "-XX:MaxPermSize=256M",
        "-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:G1HeapRegionSize=16M",
        "-XX:ParallelGCThreads=4", "-XX:ConcGCThreads=2",
        "-XX:+UseSplitVerifier", "-XX:+FailOverToOldVerifier",
        "-XX:+UseCompressedOops", "-XX:+DisableExplicitGC", "-XX:-OmitStackTraceInFastThrow",
    ] + [f"-D{p}" for p in props]
    game = [MAIN, "--username", "Dev", "--accessToken", "0",
            "--uuid", "00000000-0000-0000-0000-000000000000",
            "--version", "1.7.10", "--assetIndex", "1.7.10",
            "--tweakClass", "cpw.mods.fml.common.launcher.FMLTweaker",
            "--gameDir", d, "--assetsDir", os.path.join(src, "assets"),
            "--userProperties", "{}"]
    return jvm + ["-cp", ";".join(cp)] + game


def cmd_launch(a):
    d = trial_dir(a.name)
    man_p = os.path.join(d, "trial.json")
    if not os.path.isfile(man_p):
        sys.exit(f"no trial '{a.name}'. Build it first.")
    with open(man_p, encoding="utf-8") as f:
        man = json.load(f)
    src = man["source"]

    running = [p for p in java_processes() if p["kind"] == "client"]
    if running:
        print("refusing to launch: a Minecraft client is already running.")
        for p in running:
            print(f"  pid {p['pid']}  -Xmx{p['xmx']}  {p['gameDir']}")
        print("Two clients at once has reset the GPU and killed both. Wait for it to exit,\n"
              "or ask whoever owns it. (`trial.py status` shows who holds the lock.)")
        sys.exit(2)
    me = {"trial": a.name, "pid": None, "at": time.time(),
          "owner": a.owner or os.environ.get("CLAUDE_SESSION_NAME", "")}
    held = take_lock(me)
    if held:
        sys.exit(f"refusing to launch: lock held by trial '{held.get('trial')}' "
                 f"(pid {held.get('pid')}, owner {held.get('owner') or '?'})")

    java = find_java()
    args = build_args(d, src, a.xmx, a.D)
    logs = os.path.join(d, "logs")
    os.makedirs(logs, exist_ok=True)
    for stale in ("fml-client-latest.log", "latest.log"):
        try:
            os.remove(os.path.join(logs, stale))
        except OSError:
            pass
    with open(os.path.join(d, "LAUNCH.bat"), "w", encoding="utf-8") as f:
        f.write("@echo off\r\nrem written by tools/trial/trial.py -- same command the agent ran\r\n")
        f.write(subprocess.list2cmdline([java] + args) + "\r\npause\r\n")

    # Started through PowerShell Start-Process so the JVM is not a child of the
    # calling shell: a client launched from a backgrounded Bash task is reaped
    # within seconds at the title screen.
    def q(s):
        return "'" + s.replace("'", "''") + "'"
    arglist = subprocess.list2cmdline(args)
    script = (f"$p = Start-Process -FilePath {q(java)} -ArgumentList {q(arglist)} "
              f"-WorkingDirectory {q(d)} -WindowStyle Normal "
              f"-RedirectStandardOutput {q(os.path.join(d, 'stdout.log'))} "
              f"-RedirectStandardError {q(os.path.join(d, 'stderr.log'))} -PassThru; $p.Id")
    out = ps(script).strip().splitlines()
    try:
        pid = int(out[-1])
    except (ValueError, IndexError):
        os.remove(LOCK)
        sys.exit(f"launch failed: {out}")
    me["pid"] = pid
    write_lock(me)
    print(f"launched trial {a.name}: pid {pid}, {len(man['jars'])} jars, -Xmx{a.xmx}")
    print(f"  log: {os.path.join(logs, 'fml-client-latest.log')}")
    if a.wait:
        sys.exit(wait_loaded(d, pid, a.timeout))


LOADED = re.compile(r"Forge Mod Loader has successfully loaded (\d+) mods")
FAIL = re.compile(r"(MissingModsException|requires mods \[|DuplicateModsFoundException|"
                  r"NoClassDefFoundError: (\S+)|ClassNotFoundException: (\S+)|"
                  r"There was a critical error|---- Minecraft Crash Report ----)")


def wait_loaded(d, pid, timeout):
    """Follow the FML log until the title screen, a crash, or the JVM exits."""
    log = os.path.join(d, "logs", "fml-client-latest.log")
    t0, pos, classes = time.time(), 0, set()
    unminimized = False
    while time.time() - t0 < timeout:
        if os.path.exists(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                chunk = f.read()
                pos = f.tell()
            for line in chunk.splitlines():
                m = LOADED.search(line)
                if m:
                    print(f"loaded {m.group(1)} mods in {time.time() - t0:.0f} s")
                    return 0
                m = FAIL.search(line)
                if m:
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
            print(f"client exited after {time.time() - t0:.0f} s without finishing load")
            break
        time.sleep(2)
    else:
        print(f"still loading after {timeout} s; it is left running")
        return 1
    if classes:
        suggest_owner(classes)
    crash = os.path.join(d, "crash-reports")
    if os.path.isdir(crash):
        latest = max((os.path.join(crash, f) for f in os.listdir(crash)), key=os.path.getmtime, default=None)
        if latest:
            print(f"  crash report: {latest}")
    return 3


def suggest_owner(classes):
    """Name the live jar that defines each missing class, so the catalog can learn it."""
    cat = load_catalog()
    jars = instance_jars(LIVE)
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
        if owner:
            key = next((k for k, e in cat["mods"].items() if owner.lower().startswith(e["match"].lower())), "?")
            print(f"  missing {c} -> lives in {owner} (catalog key '{key}'): add it to the trial, "
                  f"and to 'requires' in catalog.json")
        else:
            print(f"  missing {c} -> not in any pack jar (a client-only class on a server, or a dead integration)")


# --------------------------------------------------------------- misc commands

def cmd_status(a):
    procs = java_processes()
    if not procs:
        print("no Minecraft clients or servers running")
    for p in procs:
        print(f"{p['kind']:6} pid {p['pid']:<6} -Xmx{p['xmx']:<6} {p['gameDir'] or '(server; see its cwd)'}")
    held = read_lock()
    if held:
        alive = pid_alive(held.get("pid"))
        print(f"lock: trial '{held.get('trial')}' pid {held.get('pid')} owner {held.get('owner') or '?'}"
              f" {'(running)' if alive else '(stale)'}")
    if os.path.isdir(TRIALS):
        names = [n for n in os.listdir(TRIALS) if os.path.isfile(os.path.join(TRIALS, n, "trial.json"))]
        if names:
            print("trials: " + ", ".join(sorted(names)))


def cmd_list(a):
    cat = load_catalog()
    jars = instance_jars(LIVE)
    mb = lambda k: sum(os.path.getsize(jars[h]) for h in match_jar(cat["mods"][k], jars)) / 1e6
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
        print(f"  {k:18} {mb(k):6.1f} MB  {e['role']}{req}")
    covered = {h for e in cat["mods"].values() for h in match_jar(e, jars)}
    stray = [os.path.basename(j) for j in jars if j not in covered]
    if stray:
        print("NOT IN CATALOG (a trial can never load these -- add entries):")
        for s in stray:
            print(f"  {s}")


def cmd_resolve(a):
    picked, missing = resolve(load_catalog(), a.mods, a.bundle, os.path.abspath(a.source), a.no_base)
    for k, rel, p in picked:
        print(f"{k:18} {os.path.getsize(p) / 1e6:7.1f} MB  {rel}")
    if missing:
        print(f"no jar for: {', '.join(missing)}")


def cmd_remove(a):
    d = trial_dir(a.name)
    held = read_lock()
    if held and held.get("trial") == a.name and pid_alive(held.get("pid")):
        sys.exit(f"trial {a.name} is running (pid {held['pid']})")
    # Hard links and copies only -- no junctions -- so a recursive delete
    # cannot reach the live instance.
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

    p = sp.add_parser("build"); p.add_argument("name"); mods_args(p)
    p.add_argument("--world", help="save name in the source's saves/, or a path; copied in")
    p.add_argument("--shader", help="off | enhanced | vibrant | <zip name> (default: as live)")
    p.add_argument("--overlay", action="append", default=[],
                   help="dir whose config/ scripts/ resourcepacks/ go on top, e.g. the repo's pack/")
    p.add_argument("--force", action="store_true", help="rebuild an existing trial")
    p.set_defaults(fn=cmd_build)

    p = sp.add_parser("launch"); p.add_argument("name")
    p.add_argument("--xmx", default="3G", help="heap; the slim set rarely needs more than 3G")
    p.add_argument("-D", action="append", default=[], metavar="KEY=VALUE", help="system property")
    p.add_argument("--wait", action="store_true", help="follow the log until loaded / crashed")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--owner", help="who to name in the lock (default: $CLAUDE_SESSION_NAME)")
    p.set_defaults(fn=cmd_launch)

    p = sp.add_parser("resolve"); mods_args(p); p.set_defaults(fn=cmd_resolve)
    sp.add_parser("list").set_defaults(fn=cmd_list)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    p = sp.add_parser("remove"); p.add_argument("name"); p.set_defaults(fn=cmd_remove)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
