#!/usr/bin/env python3
"""Boot the pack with only the mods a trial needs.

WHY THIS EXISTS. A full-pack client takes ~3.5 minutes to reach the title screen
and ~6 GB of heap; most trials look at one block, one renderer or one mob. The
jukebox preview proved the point -- OptiFine plus qf-content loads in well under
a minute -- but it was a hand-built folder, and every other agent kept booting
all 122 jars.

A trial is a throwaway game dir under %APPDATA%\\.qf-trials\\<name>:
  mods/    copies of the live instance's jars (never hard links: a link
           makes a write into the trial a write into the live pack) -- the base set from
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
                  [--renderer angelica] [--jar BUILT.jar] [--shaderpack DIR]
    trial.py stage-angelica [--from DIR]        stage the Angelica jars + Forge 1614 (sha1-checked)
                  [--renderer angelica] [--jar BUILT.jar] [--shaderpack DIR]
    trial.py stage-angelica [--from DIR]        stage the Angelica jars + Forge 1614 (sha1-checked)
    trial.py launch NAME [--wait] [--xmx 3G] [-D key=value ...] [--commands FILE] [--foreground]
                  a client starts in the BACKGROUND: off every monitor, no taskbar button,
                  never focused (window.ps1); --foreground shows it on the desktop as before
    trial.py userbusy                           JSON: is the owner gaming? (frame times noisy)
    trial.py status                             running clients/servers, lock, RAM
    trial.py install JAR [--why TEXT]           put a built jar into the live instance
    trial.py uninstall NAME --why TEXT          take a jar out of the live instance (kept in a backup)
    trial.py stage JAR                          candidate jar for trials only (catalog "staged": true)
    trial.py bisect start|good|bad|status|reset ...   halve a mod set to find a culprit
    trial.py guard [--fix-links] [--accept]     hard links into live, live jars changed without install
    trial.py disk                               instance copies on this PC and who uses them
    trial.py stop NAME [--force]                stop this trial's own JVM (never anyone else's)
    trial.py remove NAME
"""
import argparse, datetime, fnmatch, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
LIVE = os.path.join(APPDATA, ".crazycraft4")
TRIALS = os.path.join(APPDATA, ".qf-trials")
LOCK = os.path.join(TRIALS, "client.lock")
INSTALL_LOG = os.path.join(TRIALS, "install.log")
BISECT = os.path.join(TRIALS, "bisect.json")
LIVE_MANIFEST = os.path.join(TRIALS, "live-manifest.json")
JAVA_CANDIDATES = [r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe"]
MAIN = "net.minecraft.launchwrapper.Launch"
FORGE_JAR = "forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
# `build --server --forge 1614`: Biomes O' Plenty 2.1.0.2308 refuses Forge < 1566 and
# Angelica needs 1614, so candidates like those are trialled on the last 1.7.10 Forge.
FORGE_JARS = {"1558": FORGE_JAR, "1614": "forge-1.7.10-10.13.4.1614-1.7.10-universal.jar"}
SERVER_SOURCES = [r"C:\qfs\combat", r"C:\qfs\friends", r"C:\qfs\trial-base",
                  r"C:\qfs\forge1614-install"]
RAM_BUDGET_GB = float(os.environ.get("QF_RAM_BUDGET_GB", "22"))
# Candidate jars that are not in the live pack yet (a mod being evaluated). Laid out
# like an instance (mods/, mods/1.7.10/); `trial.py stage JAR` puts them here.
# resolve() falls back to it for any catalog entry the source instance lacks, so a
# trial can load a candidate without it ever touching %APPDATA%\.crazycraft4\mods.
STAGED = os.path.join(TRIALS, "_staged")
# --renderer angelica. The jar list and hashes are the Angelica client's own manifest, so a
# slim shader trial runs exactly the stack friends install. Stock Forge 1614 is staged in
# _staged/bin/lib and swapped onto the classpath for the live 1558 jar; FalsePatternLib's
# first-boot download (~26 MB, needs internet) is staged in _staged/falsepattern.
ANGELICA_DIR = os.path.join(os.path.dirname(HERE), "angelica-client")
ANGELICA_MANIFEST = os.path.join(ANGELICA_DIR, "manifest.json")
ANGELICA_FROM = [r"C:\qfb\dl", r"C:\qfb\client-ang2"]
# Everything Angelica and its libraries write under config/ on their first boot. Several
# (mixingasm's transformer lists, angelica-compat.cfg) only take effect on the NEXT boot, and
# a trial's config/ is rebuilt from the E7 instance, which has none of them. Without them
# every trial boot is a first boot: the compat transformers that route mods' GL calls
# through Angelica's state cache are missing, the cache desyncs, and with shaders on Iris's
# full-screen quad draws with no vertex buffer bound and the JVM dies in glDrawArrays
# (CenterDepthSampler; our pack and Complementary alike, 2026-10-17).
ANGELICA_CONFIGS = ["angelica-options.json", "angelica-modules.cfg", "angelica-compat.cfg", "angelica.cfg",
                    "falsepatternlib-early.json", "gtnhlib.cfg", "gtnhlib-number-formatting.cfg",
                    "mcpatcherforge.cfg", "unimixins.properties", "notfine/notfine.cfg",
                    "mixingasm/transformer_exclusion_list.txt", "mixingasm/transformer_inclusion_list.txt",
                    "mixingasm/transformer_inclusion_list_default.txt"]

# Small top-level folders some mods read at startup. Copied, not linked: mods
# write into them (journeymap, customnpcs, hats).
COPY_DIRS = ["config", "scripts", "fonts", "customnpcs", "hats", "structures", "CustomDISkins"]
# Client data from the live instance: copied (see copy_file on why never linked).
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


def renderer_of(cat, renderer):
    if renderer in (None, "", "e7", "optifine"):
        return None
    r = cat.get("renderers", {}).get(renderer)
    if r is None:
        sys.exit(f"--renderer {renderer}: one of e7, {', '.join(cat.get('renderers', {}))}")
    return r


def resolve(cat, wanted, bundles, src, no_base=False, server=False, renderer=None):
    mods = cat["mods"]
    client_only = set(cat.get("client_only", []))
    r = renderer_of(cat, renderer)
    base = list(cat["base"])
    if r:
        base = [k for k in base if k not in r.get("base_remove", [])] + r.get("base_add", [])
    swap = r.get("swap", {}) if r else {}
    keys = [] if no_base else [k for k in base if not (server and k in client_only)]
    for b in bundles:
        if b not in cat["bundles"]:
            sys.exit(f"unknown bundle '{b}'. Bundles: {', '.join(cat['bundles'])}")
        keys += [k for k in cat["bundles"][b]["mods"] if not (server and k in client_only)]
    keys += [lookup(cat, w) for w in wanted]
    order, seen = [], set()

    def visit(k, chain):
        if k in swap:
            k = swap[k]
            if k is None:
                return
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
    staged = instance_jars(STAGED)
    picked, missing = [], []
    for k in order:
        hits = match_jar(mods[k], jars)
        if not hits and mods[k].get("staged"):
            hits = match_jar(mods[k], staged)
            jars.update({h: staged[h] for h in hits})
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


def copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copy2(src, dst)


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


def copy_pack(src, dst):
    """A shader pack (folder or zip) into a trial's shaderpacks/: a real copy, replacing the old one."""
    if is_junction(dst):
        sys.exit(f"{dst} is a junction; a trial never holds one (unlink it with `cmd /c rmdir`)")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    elif os.path.exists(dst):
        os.remove(dst)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        copy_file(src, dst)


def angelica_manifest():
    with open(ANGELICA_MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def full_sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def staged_forge(version):
    p = os.path.join(STAGED, "bin", "lib", FORGE_JARS[version])
    if not os.path.isfile(p):
        sys.exit(f"Forge {version} is not staged ({p}). Run `trial.py stage-angelica` first.")
    return p


def cmd_stage_angelica(a):
    """Copy the Angelica client's jars (manifest mods_add + forge.add) into _staged, by sha1."""
    man = angelica_manifest()
    want = [(e["file"], e["sha1"], os.path.join(STAGED, "mods", e["file"])) for e in man["mods_add"]]
    fa = man["forge"]["add"]
    want.append((fa["file"], fa["sha1"], os.path.join(STAGED, "bin", "lib", fa["file"])))
    dirs = a.from_ or ANGELICA_FROM
    bad = []
    for name, sha, dst in want:
        if os.path.isfile(dst) and full_sha1(dst) == sha:
            print(f"  ok      {name}")
            continue
        found = None
        for d in dirs:
            for root, _, files in os.walk(d):
                if name in files and full_sha1(os.path.join(root, name)) == sha:
                    found = os.path.join(root, name)
                    break
            if found:
                break
        if not found:
            bad.append(name)
            print(f"  MISSING {name} (sha1 {sha}) in {', '.join(dirs)}; download it from the manifest url")
            continue
        copy_file(found, dst)
        print(f"  staged  {name}  from {found}")
    # Angelica's own config files as templates (see ANGELICA_CONFIGS).
    td = os.path.join(STAGED, "config-angelica")
    for name in ANGELICA_CONFIGS:
        if os.path.isfile(os.path.join(td, name)):
            continue
        for d in dirs:
            src = os.path.join(d, "config", name)
            if os.path.isfile(src) and os.path.getsize(src) > 0:
                copy_file(src, os.path.join(td, name))
                print(f"  staged  config/{name}  from {src}")
                break
        else:
            bad.append(name)
            print(f"  MISSING a complete config/{name} (one an Angelica client has written) in {', '.join(dirs)}")
    fp = os.path.join(STAGED, "falsepattern")
    if not os.path.isdir(fp):
        for d in dirs:
            src = os.path.join(d, "falsepattern")
            if os.path.isdir(src):
                shutil.copytree(src, fp)
                print(f"  staged  falsepattern/  from {src}")
                break
        else:
            print("  note: no falsepattern/ to stage; the first Angelica boot downloads it (needs internet)")
    if bad:
        sys.exit(2)
    print(f"Angelica stack staged in {STAGED}")


def angelica_client_setup(d, shader):
    """The Angelica client's overlay (tools/angelica-client/overlay), as build_angelica_client.py
    applies it: vsync off, no splash memory bar, the Iris keys on F4/F8/F9. Plus Iris's debug
    output, which a shader trial always wants (compile errors in game, patched_shaders/)."""
    sys.path.insert(0, ANGELICA_DIR)
    import build_angelica_client as bac
    cd = os.path.join(d, "config")
    os.makedirs(cd, exist_ok=True)
    for name in ANGELICA_CONFIGS:
        t = os.path.join(STAGED, "config-angelica", name)
        if not os.path.isfile(t):
            sys.exit(f"no complete {name} template in {os.path.dirname(t)}: run `trial.py stage-angelica`")
        if not os.path.isfile(os.path.join(cd, name)):
            copy_file(t, os.path.join(cd, name))
    ao = os.path.join(cd, "angelica-options.json")
    base = json.load(open(ao, encoding="utf-8")) if os.path.exists(ao) else {}
    bac.merge_json(base, json.load(open(os.path.join(ANGELICA_DIR, "overlay", "config", "angelica-options.json"),
                                        encoding="utf-8")))
    with open(ao, "w", encoding="utf-8", newline="\n") as f:
        json.dump(base, f, indent=2)
    bac.merge_forge_cfg(os.path.join(cd, "angelica-modules.cfg"),
                        os.path.join(ANGELICA_DIR, "overlay", "config", "angelica-modules.cfg"))
    bac.set_keys(os.path.join(cd, "splash.properties"), {"enabled": "true"}, "=")
    bac.set_keys(os.path.join(d, "options.txt"),
                 bac.read_keys(os.path.join(ANGELICA_DIR, "overlay", "options-keys.txt"), ":"), ":")
    pack = SHADERS.get(shader, shader) if shader else "OFF"
    on = pack not in ("OFF", "")
    bac.set_keys(os.path.join(cd, "shaders.properties"),
                 {"shaderPack": pack if on else "", "enableShaders": "true" if on else "false",
                  "enableDebugOptions": "true", "saveCompiledShaders": "true",
                  "maxShadowRenderDistance": "32"}, "=")
    fp = os.path.join(STAGED, "falsepattern")
    if os.path.isdir(fp) and not os.path.isdir(os.path.join(d, "falsepattern")):
        shutil.copytree(fp, os.path.join(d, "falsepattern"))


def sync_shaderpacks(d, man):
    """Re-copy every folder pack the trial was built with, so a launch sees the latest edits."""
    for sp in man.get("shaderpacks", []):
        if os.path.isdir(sp["src"]):
            copy_pack(sp["src"], os.path.join(d, "shaderpacks", sp["name"]))


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


# Agent clients make no sound and never go fullscreen (2026-10-23: a trial went fullscreen
# over the owner's game). Applied at build and again at every launch, because options.txt
# is copied from the live instance, where the owner may have fullscreen on.
SOUND_CATEGORIES = ["master", "music", "record", "weather", "block", "hostile", "neutral", "player", "ambient"]
QUIET_OPTIONS = dict({f"soundCategory_{c}": "0.0" for c in SOUND_CATEGORIES},
                     fullscreen="false", **{"key_key.fullscreen": "0"})   # F11 unbound
# The splash chant and title music are played by qf/splash/SplashMusic (in the pack's
# patched Forge jar) through Java Sound, outside the game's volume settings. It reads
# these files from the game dir and plays nothing without them; no jar carries a copy.
SPLASH_WAVS = [os.path.join("resources", "assets", "minecraft", "sounds", "music", n)
               for n in ("splash.wav", "menu.wav")]
# Agent launches also pass -Dqf.silent=true: SplashMusic, the qf-content jukebox and
# voice chat stay silent with it (in jars built from 2026-10-23 on).
SILENT_PROPS = ["qf.silent=true"]


def rewrite_keys(path, kv, sep=":"):
    """set_option for several keys, unlinking first: never writes through a hard link."""
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    for k, v in kv.items():
        for i, l in enumerate(lines):
            if l.startswith(k + sep):
                lines[i] = f"{k}{sep}{v}"
                break
        else:
            lines.append(f"{k}{sep}{v}")
    if os.path.exists(path):
        os.remove(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def quiet_client(d):
    """No sound, no fullscreen, no F11, no microphone in a client trial dir."""
    d = os.path.abspath(d)
    if os.path.normcase(d).startswith(os.path.normcase(os.path.abspath(LIVE))):
        sys.exit(f"quiet_client: refusing to touch the live instance ({d})")
    rewrite_keys(os.path.join(d, "options.txt"), QUIET_OPTIONS)
    for rel in SPLASH_WAVS:
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            os.remove(p)
    os.makedirs(os.path.join(d, "config"), exist_ok=True)
    rewrite_keys(os.path.join(d, "config", "qf-voice.properties"), {"enabled": "false", "volume": "0"}, "=")


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

def find_server_source(given, forge_jar=FORGE_JAR):
    for s in ([given] if given else SERVER_SOURCES):
        if s and os.path.isfile(os.path.join(s, forge_jar)) \
                and os.path.isfile(os.path.join(s, "minecraft_server.1.7.10.jar")) \
                and os.path.isdir(os.path.join(s, "libraries")):
            return s
    sys.exit(f"no server dir with {forge_jar}, minecraft_server.1.7.10.jar and "
             f"libraries/ found (looked in {given or ', '.join(SERVER_SOURCES)}); pass --server-source")


def build(name, mods, bundle=(), src=LIVE, no_base=False, server=False, server_source=None,
          world=None, shader=None, overlay=(), force=False, port=None, seed="", quiet=False,
          forge="1558", renderer=None, jars=(), shaderpacks=()):
    cat = load_catalog()
    src = os.path.abspath(src)
    rend = renderer_of(cat, renderer)
    if rend and not server:
        forge = rend.get("forge", forge)
        staged_forge(forge)   # fail before building anything
    picked, missing = resolve(cat, mods, bundle, src, no_base, server, renderer)
    # --jar: a jar built from the repo (e.g. the -PqfDebugTools qf-content) stands in for the
    # live jar of the same catalog entry, or joins the set if none matches.
    for j in jars:
        j = os.path.abspath(j)
        if not os.path.isfile(j):
            sys.exit(f"--jar {j}: no such file")
        k = key_of_jar(cat, os.path.basename(j))
        rel = os.path.join("mods", os.path.basename(j))
        picked = [p for p in picked if not (k and p[0] == k)] + [(k or "--jar", rel, j)]
        missing = [m for m in missing if m != k]
    staged_missing = [m for m in missing if cat["mods"].get(m, {}).get("staged")]
    if rend and staged_missing:
        sys.exit(f"not staged yet: {', '.join(staged_missing)}. Run `trial.py stage-angelica` first.")
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
        # A real copy, never a hard link into the live instance: a link turns any
        # later `cp` onto the trial's jar into a write to the live pack (it happened
        # on 2026-10-17 and overwrote two live jars).
        copy_file(path, os.path.join(d, rel))
    # Folders a mod reads from mods/ at load time (catalog "data"); copied, never linked.
    for k in dict.fromkeys(k for k, _, _ in picked):
        for rel in cat["mods"][k].get("data", []):
            s = os.path.join(src, rel)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(d, rel), dirs_exist_ok=True)
    for sub in COPY_DIRS:
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(d, sub), dirs_exist_ok=True)
    manifest = {"built": datetime.datetime.now().isoformat(timespec="seconds"),
                "source": src, "asked": list(mods), "bundles": list(bundle),
                "side": "server" if server else "client",
                "jars": [rel for _, rel, _ in picked],
                "renderer": renderer if rend else "e7"}
    if server:
        if forge not in FORGE_JARS:
            sys.exit(f"--forge {forge}: one of {', '.join(FORGE_JARS)}")
        ss = find_server_source(server_source, FORGE_JARS[forge])
        for f in (FORGE_JARS[forge], "minecraft_server.1.7.10.jar"):
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
        manifest.update(server_source=ss, port=port, forge_jar=FORGE_JARS[forge])
    else:
        for sub in LINK_DIRS:
            s = os.path.join(src, sub)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(d, sub), dirs_exist_ok=True)
        for f in COPY_FILES:
            s = os.path.join(src, f)
            if os.path.isfile(s) and (force or not os.path.exists(os.path.join(d, f))):
                shutil.copy2(s, os.path.join(d, f))
        set_option(os.path.join(d, "options.txt"), "pauseOnLostFocus", "false")
        quiet_client(d)
        packs = []
        for sp in shaderpacks:
            sp = os.path.abspath(sp)
            if not os.path.exists(sp):
                sys.exit(f"--shaderpack {sp}: not found")
            name = os.path.basename(sp.rstrip("\\/"))
            copy_pack(sp, os.path.join(d, "shaderpacks", name))
            packs.append({"src": sp, "name": name})
        manifest["shaderpacks"] = packs
        if rend:
            # Iris reads config/shaders.properties, never optionsshaders.txt.
            angelica_client_setup(d, shader)
            manifest["forge_jar"] = staged_forge(forge)
        elif shader:
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
          a.world, a.shader, a.overlay, a.force, a.port, a.seed, forge=a.forge,
          renderer=a.renderer, jars=a.jar, shaderpacks=a.shaderpack)


# -------------------------------------------------------------- processes/lock

# Every process these tools start gets no console window. Run from an agent's shell, which
# has no visible console, a console program otherwise opens a new one (a Windows Terminal
# window, since that is the default terminal) and it takes focus from whatever the owner
# is doing (2026-10-23).
NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW


def ps(script):
    # Output goes through a temp file, not a pipe: a JVM started by Start-Process
    # inherits PowerShell's handles, and a pipe would then stay open -- and this
    # call would block -- until the game exited.
    import tempfile
    with tempfile.TemporaryFile() as out:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
                       stdout=out, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
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


def client_args(d, src, xmx, props, forge_jar=None):
    binp = os.path.join(src, "bin")
    libs = sorted(f for f in os.listdir(os.path.join(binp, "lib")) if f.endswith(".jar"))
    if forge_jar:
        # --renderer angelica: stock Forge 1614 in place of the live (patched 1558) universal jar.
        libs = [f for f in libs if not re.fullmatch(r"forge-1\.7\.10-.*-universal\.jar", f)]
    cp = [os.path.join(binp, "minecraft.jar")] + [os.path.join(binp, "lib", f) for f in libs] \
        + ([forge_jar] if forge_jar else [])
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


def server_args(xmx, props, forge_jar=FORGE_JAR):
    return (["-Xms512M", f"-Xmx{xmx}", "-Dlog4j2.formatMsgNoLookups=true",
             "-Dfml.queryResult=confirm"] + GC + [f"-D{p}" for p in props]
            + ["-jar", forge_jar, "nogui"])


def gb(xmx):
    m = re.fullmatch(r"(\d+)([MmGg])", xmx)
    if not m:
        sys.exit(f"--xmx {xmx}: use e.g. 3G or 3072M")
    return int(m.group(1)) / (1024 if m.group(2) in "Mm" else 1)


WINDOW_PS1 = os.path.join(HERE, "window.ps1")


def window_ps(mode, *args):
    """Run window.ps1 (read-only modes) and return its parsed JSON, or None."""
    out = ps_file(WINDOW_PS1, ["-Mode", mode] + [str(x) for x in args])
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def ps_file(path, args):
    import tempfile
    with tempfile.TemporaryFile() as out:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                        "-ExecutionPolicy", "Bypass", "-File", path] + args,
                       stdout=out, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        out.seek(0)
        return out.read().decode("utf-8", "replace")


def start_window_hider(pid, d):
    """Background launch: a hidden, detached PowerShell keeps the client's windows off every
    monitor, out of the taskbar and Alt-Tab, unfocusable and never minimized, for the life
    of the JVM (window.ps1 -Mode hide). Detached like the JVM, so it outlives this call."""
    def q(s):
        return "'" + s.replace("'", "''") + "'"
    argl = subprocess.list2cmdline(["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                                    "-ExecutionPolicy", "Bypass", "-File", WINDOW_PS1,
                                    "-Mode", "hide", "-ProcessId", str(pid), "-Log", os.path.join(d, "logs", "window.log")])
    ps(f"Start-Process -FilePath powershell -ArgumentList {q(argl)} -WindowStyle Hidden")


def trial_client_pids():
    """Pids of Minecraft clients that agents run (anything not from the live instance)."""
    live = os.path.normcase(os.path.abspath(LIVE))
    return [p["pid"] for p in java_processes()
            if p["kind"] == "client" and os.path.normcase(os.path.abspath(p["gameDir"] or LIVE)) != live]


def user_busy():
    """Is the owner gaming? A foreground window that covers its monitor, a game-store exe in the
    foreground, Windows' fullscreen/D3D notification state, or another process loading the
    GPU's 3D engine >= 40 %. Agent clients are excluded; the owner's own pack client is not."""
    ours = trial_client_pids()
    r = window_ps("userbusy", *(["-OurPids", ",".join(map(str, ours))] if ours else []))
    return r or {"busy": None, "reasons": ["window.ps1 userbusy gave no answer"]}


def cmd_userbusy(a):
    r = user_busy()
    print(json.dumps(r))
    sys.exit(1 if r.get("busy") else 0)


def start_detached(java, args, d, stdin=None):
    # Started through PowerShell Start-Process so the JVM is not a child of the
    # calling shell: a client launched from a backgrounded Bash task is reaped
    # within seconds at the title screen.
    def q(s):
        return "'" + s.replace("'", "''") + "'"
    extra = f"-RedirectStandardInput {q(stdin)} " if stdin else ""
    server = bool(stdin) or "nogui" in args
    if not server:
        # javaw: a client needs no console, and Start-Process would open a new one for
        # java.exe (a Windows Terminal window that steals focus). Its stdout/stderr are
        # still redirected to the files below.
        w = os.path.join(os.path.dirname(java), "javaw.exe")
        java = w if os.path.isfile(w) else java
    # Normal for a client: a minimized LWJGL window stalls (in the background the
    # window.ps1 hider moves it off-screen instead). Hidden for a server: its console
    # has nothing to show (logs go to files) and must never appear or take focus.
    script = (f"$p = Start-Process -FilePath {q(java)} -ArgumentList {q(subprocess.list2cmdline(args))} "
              f"-WorkingDirectory {q(d)} -WindowStyle {'Hidden' if server else 'Normal'} "
              f"-RedirectStandardOutput {q(os.path.join(d, 'stdout.log'))} "
              f"-RedirectStandardError {q(os.path.join(d, 'stderr.log'))} {extra}-PassThru; $p.Id")
    out = ps(script).strip().splitlines()
    try:
        return int(out[-1])
    except (ValueError, IndexError):
        return None


def cmd_launch(a):
    guard_check("launch")
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
    sync_shaderpacks(d, man)
    quiet_client(d)
    args = client_args(d, src, a.xmx, SILENT_PROPS + a.D, man.get("forge_jar") if man.get("renderer", "e7") != "e7" else None)
    if a.join:
        # Vanilla's --server/--port: the client connects as soon as the menu is up.
        host, _, port = a.join.rpartition(":")
        if not host or not port.isdigit():
            sys.exit(f"--join {a.join}: use HOST:PORT, e.g. 127.0.0.1:25600")
        args += ["--server", host, "--port", port]
    if a.size:
        w, _, h = a.size.lower().partition("x")
        if not (w.isdigit() and h.isdigit()):
            sys.exit(f"--size {a.size}: use WIDTHxHEIGHT, e.g. 1920x1080")
        args += ["--width", w, "--height", h]
    clear_logs(d, "client")
    write_bat(d, java, args)
    background = not a.foreground
    busy = user_busy()
    fg_before = window_ps("foreground") or {}
    pid = start_detached(java, args, d)
    if not pid:
        os.remove(LOCK)
        sys.exit("launch failed: Start-Process returned no pid")
    if background:
        start_window_hider(pid, d)
    me["pid"] = pid
    write_lock(me)
    with open(os.path.join(d, "pid"), "w") as f:
        f.write(str(pid))
    print(f"launched client trial {a.name}: pid {pid}, {len(man['jars'])} jars, -Xmx{a.xmx}"
          f"{', background (off-screen, no taskbar, no focus)' if background else ', foreground'}")
    print(f"  log: {os.path.join(d, 'logs', 'latest.log')}")
    if busy.get("busy"):
        print("  owner busy (frame times will be noisy): " + "; ".join(busy.get("reasons", [])))
    info = {"trial": a.name, "pid": pid, "background": background, "at": time.time(),
            "userbusy": busy, "foreground_before": fg_before.get("hwnd")}
    with open(os.path.join(d, "launch.json"), "w", encoding="utf-8") as f:
        json.dump(info, f)
    print("launch-info: " + json.dumps(info))
    if a.wait:
        sys.exit(wait_loaded(d, pid, a.timeout, "client", unminimize=not background))


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
    args = server_args(a.xmx, a.D, man.get("forge_jar", FORGE_JAR))
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


def wait_loaded(d, pid, timeout, side, unminimize=True):
    """Follow the FML log until loaded, a crash, or the JVM exits.
    Bounded and quiet: run it as a background task, not a foreground sleep loop."""
    log = os.path.join(d, "logs", "latest.log")
    t0, pos, classes, hits = time.time(), 0, set(), 0
    need = 2 if side == "client" else 1
    # A background client's window.ps1 hider restores it instead (and keeps it off-screen).
    unminimized = side == "server" or not unminimize
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


# --------------------------------------------------------------------- guard

def fsutil_links(path):
    """Every other path that is the same file on disk (hard links), via fsutil."""
    r = subprocess.run(["fsutil", "hardlink", "list", path], capture_output=True, text=True, creationflags=NO_WINDOW)
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    out = []
    for line in r.stdout.splitlines():
        q = line.strip()
        if q:
            q = drive + q if q.startswith("\\") else q
            if os.path.normcase(os.path.abspath(q)) != os.path.normcase(os.path.abspath(path)):
                out.append(q)
    return out


def live_link_report():
    """Live jars that have a second name somewhere. A write to that other name is
    a write to the live pack -- how two live jars were overwritten on 2026-10-17."""
    found = {}
    for rel, p in instance_jars(LIVE).items():
        try:
            if os.stat(p).st_nlink > 1:
                found[rel] = fsutil_links(p)
        except OSError:
            pass
    return found


def live_hashes():
    return {rel: sha1(p) for rel, p in instance_jars(LIVE).items()}


def load_live_manifest():
    try:
        with open(LIVE_MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_live_manifest(hashes):
    os.makedirs(TRIALS, exist_ok=True)
    with open(LIVE_MANIFEST, "w", encoding="utf-8") as f:
        json.dump({"at": datetime.datetime.now().isoformat(timespec="seconds"), "jars": hashes}, f, indent=1)


def live_drift():
    """(changed, added, removed) since the manifest, i.e. live jars that changed
    without `install`. None if there is no manifest yet."""
    m = load_live_manifest()
    if m is None:
        return None
    old, now = m["jars"], live_hashes()
    changed = sorted(k for k in now if k in old and now[k] != old[k])
    added = sorted(k for k in now if k not in old)
    removed = sorted(k for k in old if k not in now)
    return changed, added, removed


def guard_check(context, strict=False):
    """Run before launch/install. Prints problems; with strict, exits on drift."""
    links = live_link_report()
    if links:
        print(f"WARNING ({context}): {len(links)} live jar(s) are hard-linked elsewhere; a write to any of")
        print("  these paths overwrites the live pack. Fix: `trial.py guard --fix-links`.")
        for rel, others in sorted(links.items()):
            for o in others:
                print(f"    {os.path.basename(rel)}  <->  {o}")
    drift = live_drift()
    if drift is None:
        save_live_manifest(live_hashes())
        print(f"guard: no live manifest yet; recorded the current {len(instance_jars(LIVE))} jars as the baseline")
        return
    changed, added, removed = drift
    if changed or added or removed:
        print(f"ALERT ({context}): the live mods/ changed WITHOUT `trial.py install`:")
        for k in changed:
            p = os.path.join(LIVE, k)
            when = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M")
            print(f"    changed  {k}  (modified {when})")
        for k in added:
            print(f"    added    {k}")
        for k in removed:
            print(f"    removed  {k}")
        print("  Find out what wrote it before going on. If the change is intended, record it with")
        print("  `trial.py guard --accept`; otherwise restore the previous jar from its _backup-install-* copy.")
        if strict:
            sys.exit(3)


def cmd_guard(a):
    if a.fix_links:
        links = live_link_report()
        procs = java_processes()
        fixed = skipped = 0
        for rel, others in links.items():
            for o in others:
                d = os.path.normcase(o)
                # Never touch the live instance itself, and never a dir a JVM runs from.
                if os.path.normcase(LIVE) in d:
                    continue
                busy = [p for p in procs if any(os.path.normcase(x) in d for x in
                        [p["gameDir"]] if x) or (os.path.dirname(os.path.dirname(d)) in os.path.normcase(p["cmd"]))]
                if busy:
                    print(f"  skip (in use by pid {busy[0]['pid']}): {o}")
                    skipped += 1
                    continue
                tmp = o + ".unlink"
                shutil.copyfile(o, tmp)
                os.remove(o)
                os.replace(tmp, o)
                fixed += 1
        print(f"guard: replaced {fixed} hard link(s) with copies; {skipped} skipped")
    if a.accept:
        save_live_manifest(live_hashes())
        print("guard: current live jars recorded as the baseline")
        return
    links = live_link_report()
    drift = live_drift()
    guard_check("guard")
    if not links and drift is not None and not any(drift):
        print(f"guard: OK. No hard links into the live mods/; all {len(instance_jars(LIVE))} live jars match the manifest.")


def cmd_install(a):
    """The one way a jar goes into the live instance.

    Agents used to Copy-Item builds straight over .crazycraft4\\mods while the user
    played and while other agents were building servers from it. This refuses
    while anything runs from the live instance, replaces atomically (a reader
    sees the old jar or the new one, never half of one), keeps the old jar out
    of mods/ so FML cannot load both, and logs who did it.
    """
    # An unexplained change to the live pack is investigated, not installed over.
    if not a.force:
        guard_check("install", strict=True)
    jar = os.path.abspath(a.jar)
    if not os.path.isfile(jar) or not jar.lower().endswith(".jar"):
        sys.exit(f"not a jar: {jar}")
    if jar.lower().endswith("-dev.jar"):
        sys.exit("that is the deobfuscated -dev jar; it crashes in the pack with NoSuchMethodError. "
                 "Install build/libs/<name>.jar (the reobfuscated one).")
    if not a.force:
        refuse_if_live_in_use("install")
    name = os.path.basename(jar)
    mods = os.path.join(LIVE, "mods")
    dst = os.path.join(mods, a.as_name or name)
    # --replace: the jar this one supersedes under another file name (a version bump,
    # or GTNH CodeChickenCore-1.4.22.jar for stock CodeChickenCore.jar). It leaves
    # mods/ in the same step, so neither "both loaded" nor "neither there" is ever left behind.
    rep = find_live_jar(a.replace) if a.replace else None
    if rep and os.path.normcase(os.path.join(LIVE, rep)) == os.path.normcase(dst):
        rep = None
    if not os.path.isfile(dst):
        cat = load_catalog()
        k = key_of_jar(cat, name)
        same = [r for r in instance_jars(LIVE)
                if k and r != rep and key_of_jar(cat, os.path.basename(r)) == k]
        if same:
            sys.exit(f"{name} would sit next to {', '.join(same)}; FML would load both. "
                     f"Pass --replace {os.path.basename(same[0])} (or --as it) to replace it.")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(LIVE, f"_backup-install-{stamp}")
    old_sha = None
    if os.path.isfile(dst):
        old_sha = sha1(dst)
        if old_sha == sha1(jar):
            print(f"{os.path.basename(dst)} is already that build ({old_sha}); nothing to do")
            return
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(dst, os.path.join(bdir, os.path.basename(dst)))
    tmp = dst + ".installing"
    shutil.copy2(jar, tmp)
    os.replace(tmp, dst)
    rep_sha = None
    if rep:
        rep_sha = sha1(os.path.join(LIVE, rep))
        rdst = os.path.join(bdir, os.path.relpath(rep, "mods"))
        os.makedirs(os.path.dirname(rdst), exist_ok=True)
        os.replace(os.path.join(LIVE, rep), rdst)
    os.makedirs(TRIALS, exist_ok=True)
    who = a.owner or os.environ.get("CLAUDE_SESSION_NAME", "?")
    line = (f"{stamp}\t{who}\t{os.path.basename(dst)}\t{old_sha or '-'} -> {sha1(dst)}\t"
            f"{jar}\t{a.why or ''}" + (f" (replaces {rep} {rep_sha})" if rep else "") + "\n")
    with open(INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"installed {os.path.basename(dst)} ({old_sha or 'new'} -> {sha1(dst)})"
          + (f"; previous kept in _backup-install-{stamp}" if old_sha else ""))
    if rep:
        print(f"replaced {rep} ({rep_sha}); kept in {rdst}")
    print(f"logged in {INSTALL_LOG}")
    m = load_live_manifest() or {"jars": {}}
    jars = m["jars"]
    jars[os.path.relpath(dst, LIVE)] = sha1(dst)
    if rep:
        jars.pop(rep, None)
    save_live_manifest(jars)


def find_live_jar(pattern):
    """The one live jar a name means: a path under mods/ (1.7.10/x.jar), a file name, or a glob."""
    want = pattern.replace("/", os.sep).replace("\\", os.sep)
    if want.lower().startswith("mods" + os.sep):
        want = want[5:]
    hits = [rel for rel in instance_jars(LIVE)
            if fnmatch.fnmatch(os.path.relpath(rel, "mods").lower(), want.lower())
            or (os.sep not in want and fnmatch.fnmatch(os.path.basename(rel).lower(), want.lower()))]
    if len(hits) != 1:
        found = ", ".join(hits) if hits else "nothing"
        sys.exit(f"'{pattern}' must name exactly one live jar under mods/; it matches {found}")
    return hits[0]


def refuse_if_live_in_use(verb):
    """Exit while the user's game, or a server running from the live instance, is up."""
    live_users = [p for p in java_processes()
                  if os.path.normcase(LIVE) in os.path.normcase(p["cmd"]) and
                  (p["kind"] == "server" or os.path.normcase(p["gameDir"]) == os.path.normcase(LIVE))]
    if live_users:
        print(f"refusing to {verb}: the live instance is in use (the user's game, or a server built from it):")
        for p in live_users:
            print(f"  {p['kind']} pid {p['pid']} {p['gameDir']}")
        print("A jar changed under a running game is not what that game loaded. Wait for it to exit.")
        sys.exit(2)


def cmd_uninstall(a):
    """The one way a jar leaves the live instance: the mirror of `install`.

    Removing a jar changes the pack as much as adding one (a missing library is a
    crash at the next start; a missing mod deletes its blocks from every world
    that loads without it), so it gets the same checks: guard first, refuse while
    anything runs from the live instance, refuse if another live jar still needs
    it, keep the jar in _backup-install-<time>/, and log it.
    """
    if not a.why:
        sys.exit("uninstall needs --why: the install log is how the next person learns why a jar is gone")
    if not a.force:
        guard_check("uninstall", strict=True)
    live = instance_jars(LIVE)
    rel = find_live_jar(a.jar)
    if not a.force:
        refuse_if_live_in_use("uninstall")
    # A jar another live jar requires (catalog `requires`) leaves that one broken.
    cat = load_catalog()
    k = key_of_jar(cat, os.path.basename(rel))
    if k and not a.force:
        others = [r for r in live if r != rel and key_of_jar(cat, os.path.basename(r)) == k]
        needers = sorted({os.path.basename(r) for r in live if r != rel and
                          k in cat["mods"].get(key_of_jar(cat, os.path.basename(r)) or "", {}).get("requires", [])})
        if needers and not others:
            sys.exit(f"{os.path.basename(rel)} is '{k}', which these live jars require: {', '.join(needers)}. "
                     f"Uninstall or update them first, or fix catalog.json if the requirement is gone.")
    src = live[rel]
    old_sha = sha1(src)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(LIVE, f"_backup-install-{stamp}")
    dst = os.path.join(bdir, os.path.relpath(rel, "mods"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    # A move on one volume is a rename: the jar is in mods/ or in the backup, never half of each.
    os.replace(src, dst)
    os.makedirs(TRIALS, exist_ok=True)
    who = a.owner or os.environ.get("CLAUDE_SESSION_NAME", "?")
    with open(INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(f"{stamp}\t{who}\tUNINSTALL {rel}\t{old_sha} -> -\t{dst}\t{a.why}\n")
    print(f"uninstalled {rel} ({old_sha}); kept in _backup-install-{stamp}\\{os.path.relpath(rel, 'mods')}")
    print(f"  undo: trial.py install \"{dst}\" --as {os.path.relpath(rel, 'mods')} --why \"undo uninstall\"")
    print(f"logged in {INSTALL_LOG}")
    m = load_live_manifest() or {"jars": {}}
    m["jars"].pop(rel, None)
    save_live_manifest(m["jars"])


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


def cmd_stage(a):
    """Copy a candidate jar into the staging dir; it is loadable by catalog entries marked "staged"."""
    if not os.path.isfile(a.jar):
        sys.exit(f"no such jar: {a.jar}")
    dst = os.path.join(STAGED, "mods", os.path.basename(a.jar))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(a.jar, dst)
    cat = load_catalog()
    k = key_of_jar(cat, os.path.basename(a.jar))
    print(f"staged {dst} ({os.path.getsize(dst) / 1e6:.1f} MB, sha1 {sha1(dst)})")
    if not k:
        print("  no catalog entry matches it yet: add one with \"staged\": true")
    elif not cat["mods"][k].get("staged"):
        print(f"  catalog entry '{k}' lacks \"staged\": true, so trials still take the live jar")


def cmd_resolve(a):
    picked, missing = resolve(load_catalog(), a.mods, a.bundle, os.path.abspath(a.source), a.no_base, a.server,
                              a.renderer)
    for k, rel, p in picked:
        print(f"{k:18} {os.path.getsize(p) / 1e6:7.1f} MB  {rel}")
    if missing:
        print(f"no jar for: {', '.join(missing)}")


def cmd_stop(a):
    """Stop a trial's own JVM -- and nothing else. The pid comes from the trial's
    pid file and must still have the trial dir on its command line, so a reused
    pid can never take down someone else's game."""
    d = trial_dir(a.name)
    try:
        with open(os.path.join(d, "pid")) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        sys.exit(f"trial {a.name} has no pid file; it was never launched")
    mine = [p for p in java_processes() if p["pid"] == pid and os.path.normcase(d) in os.path.normcase(p["cmd"] + p["gameDir"])]
    if not mine:
        # A server's cwd is not on its command line; fall back to the pid file plus liveness.
        if not pid_alive(pid):
            print(f"trial {a.name} is not running")
            return
        if man_side(a.name) != "server":
            sys.exit(f"pid {pid} is alive but is not trial {a.name}'s client; not touching it")
    if man_side(a.name) == "server" and not a.force:
        print(f"server trials stop cleanly with a 'stop' console command (--commands); "
              f"use --force to kill pid {pid} instead")
        sys.exit(2)
    ps(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
    held = read_lock()
    if held and held.get("pid") == pid:
        os.remove(LOCK)
    print(f"stopped trial {a.name} (pid {pid})")


def man_side(name):
    return read_manifest(name).get("side", "client")


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
        p.add_argument("--renderer", default="e7", help="e7 (OptiFine, the default) or angelica (catalog 'renderers')")

    p = sp.add_parser("build"); p.add_argument("name"); mods_args(p)
    p.add_argument("--world", help="save name in the source's saves/, or a path; copied in")
    p.add_argument("--shader", help="client: off | enhanced | vibrant | <zip name> (default: as live)")
    p.add_argument("--overlay", action="append", default=[],
                   help="dir whose config/ scripts/ resourcepacks/ go on top, e.g. the repo's pack/")
    p.add_argument("--server-source", help="dir holding the Forge/vanilla server jars and libraries/")
    p.add_argument("--port", type=int, help="server port (default: first free from 25600)")
    p.add_argument("--forge", default="1558", help="server: Forge build, 1558 (the pack's) or 1614")
    p.add_argument("--seed", default="", help="server world seed")
    p.add_argument("--force", action="store_true", help="rebuild an existing trial")
    p.add_argument("--jar", action="append", default=[],
                   help="a built jar (copied) that replaces the live jar of the same catalog entry")
    p.add_argument("--shaderpack", action="append", default=[],
                   help="client: shader pack folder or zip, copied into shaderpacks/ (folders re-copied on every launch)")
    p.set_defaults(fn=cmd_build)
    p = sp.add_parser("stage-angelica", help="stage the Angelica client's jars and Forge 1614 (sha1-checked)")
    p.add_argument("--from", dest="from_", action="append", help="where to look (default: C:\\qfb\\dl, C:\\qfb\\client-ang2)")
    p.set_defaults(fn=cmd_stage_angelica)

    p = sp.add_parser("launch"); p.add_argument("name")
    p.add_argument("--xmx", default="3G", help="heap; the slim set rarely needs more than 3G")
    p.add_argument("-D", action="append", default=[], metavar="KEY=VALUE", help="system property")
    p.add_argument("--wait", action="store_true", help="follow the log until loaded / crashed")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--commands", help="server: file of console commands fed on stdin")
    p.add_argument("--join", metavar="HOST:PORT", help="client: connect to this server once the menu is up")
    p.add_argument("--size", metavar="WxH", help="client: window size, e.g. 1920x1080 (shader budgets are per resolution)")
    p.add_argument("--owner", help="who to name in the lock (default: $CLAUDE_SESSION_NAME)")
    p.add_argument("--foreground", action="store_true",
                   help="client: show the window on the desktop (the old behaviour); default is background")
    p.set_defaults(fn=cmd_launch)

    p = sp.add_parser("install"); p.add_argument("jar")
    p.add_argument("--as", dest="as_name", help="filename in mods/ to replace (default: the jar's own)")
    p.add_argument("--replace", help="a live jar under another name that this one supersedes; moved to the "
                                     "backup in the same step (name or path under mods/, globs allowed)")
    p.add_argument("--why", help="one line for the install log")
    p.add_argument("--owner", help="who to log (default: $CLAUDE_SESSION_NAME)")
    p.add_argument("--force", action="store_true", help="install even though the live instance is in use")
    p.set_defaults(fn=cmd_install)

    p = sp.add_parser("uninstall", help="move a live jar into _backup-install-<time>/ (logged)")
    p.add_argument("jar", help="file name or path under mods/ (1.7.10/x.jar), globs allowed; must match one jar")
    p.add_argument("--why", help="one line for the install log (required)")
    p.add_argument("--owner", help="who to log (default: $CLAUDE_SESSION_NAME)")
    p.add_argument("--force", action="store_true", help="skip the guard, in-use and required-by checks")
    p.set_defaults(fn=cmd_uninstall)

    p = sp.add_parser("bisect"); p.add_argument("action", choices=["start", "good", "bad", "status", "reset"])
    p.add_argument("--name", default="bisect")
    p.add_argument("mods", nargs="*", help="start: suspects (default: every non-base mod)")
    p.add_argument("--keep", action="append", default=[], help="start: always loaded, never a suspect")
    p.add_argument("--bundle", action="append", default=[])
    p.add_argument("--server", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_bisect)

    p = sp.add_parser("stage"); p.add_argument("jar"); p.set_defaults(fn=cmd_stage)
    p = sp.add_parser("resolve"); mods_args(p); p.set_defaults(fn=cmd_resolve)
    sp.add_parser("list").set_defaults(fn=cmd_list)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    sp.add_parser("userbusy", help="JSON: is the owner gaming? exit 1 if so (frame times noisy)").set_defaults(fn=cmd_userbusy)
    p = sp.add_parser("guard", help="hard links into the live pack, and live jars changed without install")
    p.add_argument("--fix-links", action="store_true", help="replace hard links outside the live pack with copies")
    p.add_argument("--accept", action="store_true", help="record the current live jars as intended")
    p.set_defaults(fn=cmd_guard)
    sp.add_parser("disk").set_defaults(fn=cmd_disk)
    p = sp.add_parser("stop"); p.add_argument("name")
    p.add_argument("--force", action="store_true", help="kill a server trial instead of asking for a clean stop")
    p.set_defaults(fn=cmd_stop)
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
