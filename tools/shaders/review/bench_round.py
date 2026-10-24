#!/usr/bin/env python3
"""Render and measure one shader round on a slim Angelica trial (review-loop.md, step 2).

A full-pack Angelica boot takes 3-5 minutes; this boots tools/trial/trial.py's slim
Angelica set (Forge 1614, Angelica, UniMixins, GTNHLib + qf-content's debug build for
FrameBench + Twilight Forest for modded leaves) in about a minute, then lets FrameBench fly
the view scenes in tools/shaders/review/views-world-master.txt and quit.

Each round:
  1. waits until no Minecraft client runs and the trial lock is free (one client at a time);
  2. rebuilds the trial from copies (never links), with a fresh copy of the world and of
     the shader pack from the repo (shaders/QuestForge);
  3. sets the preset (QF_PRESET in shaderpacks/QuestForge.txt), the window size and an
     uncapped frame rate (maxFps 260 = unlimited; vsync_mode OFF comes from the trial);
  4. launches with -Dqf.bench=1 and waits for the JVM to exit. The client runs in the
     background (trial.py: off every monitor, no taskbar button, never focused) unless
     --foreground; if the owner is gaming at any check (trial.py userbusy, every minute), the round's
     frame times are marked noisy in bench/<tag>.userbusy.json; a background run first waits until
     the owner has been idle for 5 minutes (trial.wait_user_idle), so it never renders over a game;
   - guarded (2026-10-23): before each launch config/shaders.properties must ask for the pack (or for
     shaders off); after it the log must show the pack loaded and compiled, else the run is INVALID,
     its frames are discarded and it is re-run once; a client with no log progress for 5 min is
     stopped (this trial only) and retried once;
  5. copies bench/<tag>.txt and the frames into ROUNDS (default C:\\qfb\\shaderdev\\rounds),
     laid out as check_frames.py expects (--client ROUNDS), and prints any shader error.

Usage (py -3.10 -I, run it as a BACKGROUND task):
  bench_round.py --tag r1-high --preset 3 --size 2560x1440
  bench_round.py --tag off-1080 --preset off --size 1920x1080 --scenes static,plains_noon
  bench_round.py --tag r1-ids --preset 3 --debug-view 1 --scenes gallery
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TRIAL_PY = os.path.join(REPO, "tools", "trial", "trial.py")
sys.path.insert(0, os.path.dirname(TRIAL_PY))
import trial  # noqa: E402

PACK = os.path.join(REPO, "shaders", "QuestForge")
VIEWS = os.path.join(HERE, "views-world-master.txt")
GALLERY = os.path.join(HERE, "gallery-shader.txt")
DEBUG_JAR = r"C:\qfb\shaderdev\jars\QuestForgeContent-1.0.0.jar"
WORLD = r"C:\qfb\world-master"
ROUNDS = r"C:\qfb\shaderdev\rounds"
ALL_SCENES = "static,plains_noon,forest_golden,golden_lit,shore_noon,shore_sunset,shore_dusk,night_full,night_new,night_moon,underwater,torch,gallery"
SHADER_ERR = re.compile(r"(error|Error|ERROR|Failed to|failed to|Exception).*(shader|Shader|program|GLSL|Iris|iris)"
                        r"|(shader|Shader|Iris|iris).*(error|Error|ERROR|failed|Failed)")


def wait_for_gpu(max_min, quiet_min):
    """Wait until no client has run for quiet_min minutes. Shader rounds yield the one client
    slot: other sessions (the live-game and release tests) take priority (2026-10-17)."""
    t0 = time.time()
    free_since = None
    while True:
        clients = [p for p in trial.java_processes() if p["kind"] == "client"]
        held = trial.read_lock()
        # A lock without a pid is a launch in progress for its first 120 s (trial.take_lock).
        held_alive = held and ((held.get("pid") and trial.pid_alive(held["pid"]))
                               or (not held.get("pid") and time.time() - held.get("at", 0) < 130))
        if not clients and not held_alive:
            free_since = free_since or time.time()
            if time.time() - free_since >= quiet_min * 60:
                return
            time.sleep(30)
            continue
        free_since = None
        who = ", ".join(p["gameDir"] for p in clients) or f"lock {held.get('trial')}"
        if time.time() - t0 > max_min * 60:
            sys.exit(f"gave up after {max_min} min: a client is still running ({who})")
        print(f"  waiting: client running ({who})", flush=True)
        time.sleep(60)


def set_kv(path, kv, sep):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(path) else []
    for k, v in kv.items():
        for i, l in enumerate(lines):
            if l.startswith(k + sep):
                lines[i] = f"{k}{sep}{v}"
                break
        else:
            lines.append(f"{k}{sep}{v}")
    if os.path.exists(path):
        os.remove(path)   # never write through a link
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def run_client(a, d, cmd, t0, busy):
    """Launch, follow until exit. True if it died early after a pipeline rebuild.
    Appends a `trial.user_busy()` sample to busy every minute while the client runs."""
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=trial.NO_WINDOW)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        sys.exit(f"launch failed ({r.returncode})")
    pid = int(open(os.path.join(d, "pid")).read().strip())
    shown = 0
    log = os.path.join(d, "logs", "latest.log")
    last_size, last_change = -1, time.time()
    hung = False
    while trial.pid_alive(pid):
        # A client started from a non-interactive shell can come up minimized and stall.
        # In the background (default) trial.py's window.ps1 hider restores it and keeps it
        # off-screen; in the foreground SW_SHOWNOACTIVATE shows it without stealing focus.
        if a.foreground and shown < 3 and time.time() - t0 > 10 + 20 * shown:
            trial.ps("Add-Type -Name W -Namespace Q -MemberDefinition '[DllImport(\"user32.dll\")] "
                     "public static extern bool ShowWindow(System.IntPtr h, int c);'; "
                     f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
                     "if ($p -and $p.MainWindowHandle -ne 0) { [Q.W]::ShowWindow($p.MainWindowHandle, 4) | Out-Null }")
            shown += 1
        if time.time() - t0 > 60 * len(busy):
            busy.append(trial.user_busy())
        if time.time() - t0 > a.timeout_min * 60:
            print("timeout: stopping the trial")
            subprocess.run([sys.executable, "-I", TRIAL_PY, "stop", a.name], creationflags=trial.NO_WINDOW)
            break
        # Hung client (2026-10-23 gf3: a cache-miss retry froze at world join with no log line
        # for 18 min): no log growth for HANG_MIN minutes -> stop this trial only.
        size = os.path.getsize(log) if os.path.exists(log) else 0
        if size != last_size:
            last_size, last_change = size, time.time()
        elif time.time() - last_change > HANG_MIN * 60:
            print(f"HUNG: no log progress for {HANG_MIN} min: stopping the trial")
            subprocess.run([sys.executable, "-I", TRIAL_PY, "stop", a.name], creationflags=trial.NO_WINDOW)
            hung = True
            break
        time.sleep(10)
    held = trial.read_lock()
    if held and held.get("pid") == pid and os.path.exists(trial.LOCK):
        os.remove(trial.LOCK)
    took = time.time() - t0
    print(f"client exited after {took:.0f} s")
    log = os.path.join(d, "logs", "latest.log")
    rebuilt = os.path.exists(log) and "[Load #2]" in open(log, encoding="utf-8", errors="replace").read()
    return (took < 120 and rebuilt) or hung


HANG_MIN = 5


def shader_config_ok(d, pack):
    """Pre-launch: the trial's Angelica config must ask for `pack` (or for shaders off when pack is None).
    2026-10-23 gh: a whole High round rendered vanilla because enableShaders was false at boot."""
    p = os.path.join(d, "config", "shaders.properties")
    kv = {}
    if os.path.exists(p):
        for l in open(p, encoding="utf-8", errors="replace"):
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                kv[k.strip()] = v.strip()
    want = {"enableShaders": "true", "shaderPack": pack} if pack else {"enableShaders": "false"}
    bad = {k: kv.get(k) for k, v in want.items() if kv.get(k) != v}
    return want, bad


def shader_log_ok(log, pack):
    """Post-run: the client log must show the pack loaded and compiled (or shaders off)."""
    if not os.path.exists(log):
        return False, "no client log"
    t = open(log, encoding="utf-8", errors="replace").read()
    if pack:
        if "Shaders are disabled" in t:
            return False, "log: Shaders are disabled"
        if f"Using shaderpack: {pack}" not in t:
            return False, f"log: no 'Using shaderpack: {pack}'"
        if "createProg name=" not in t:
            return False, "log: no shader program was compiled"
        return True, "pack loaded and compiled"
    return ("Shaders are disabled" in t), "shaders off" if "Shaders are disabled" in t else "log: shaders were ON in an off run"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--preset", required=True, help="0-4 (Potato..Ultra), or off for shaders off")
    ap.add_argument("--size", default="2560x1440")
    ap.add_argument("--scenes", default=ALL_SCENES)
    ap.add_argument("--debug-view", type=int, default=0, help="QF_DEBUG_VIEW (1 material IDs, 2 normals)")
    ap.add_argument("--opt", action="append", default=[], metavar="KEY=VALUE", help="extra pack option")
    ap.add_argument("--reference", metavar="ZIP",
                    help="render this pack instead (unmodified; e.g. Complementary as a reference frame only)")
    ap.add_argument("--resourcepack", action="append", default=[], metavar="ZIP",
                    help="resource pack for this trial only (e.g. Faithful 32x), under the source's packs")
    ap.add_argument("--source", default=trial.LIVE, help="instance the trial copies jars, config and options from")
    ap.add_argument("--mods", default="qfcontent,twilightforest", help="catalog keys beyond the base set")
    ap.add_argument("--reload", default="", metavar="SCENES",
                    help="call Iris.reload() (the F9 key) before these scenes, comma-separated")
    ap.add_argument("--world", default=WORLD,
                    help="world the trial copies (e.g. tools/textures/build_showcase.py's copy with the texture wall)")
    ap.add_argument("--name", default="shaderdev", help="trial name")
    ap.add_argument("--xmx", default="3G")
    ap.add_argument("--wait-min", type=int, default=240, help="how long to wait for the GPU")
    ap.add_argument("--timeout-min", type=int, default=20)
    ap.add_argument("--quiet-min", type=float, default=10,
                    help="launch only after no client has run for this long (yield to other sessions)")
    ap.add_argument("--foreground", action="store_true",
                    help="show the client on the desktop (trial.py launch --foreground); default is background")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.]+", a.tag) or "-" in a.tag:
        sys.exit("--tag: letters, digits, _ and . only (check_frames.py matches bench-<tag>*.png)")

    wait_for_gpu(a.wait_min, a.quiet_min)
    shader = "off" if a.preset == "off" else "QuestForge"
    packs = [PACK]
    if a.reference:
        shader = os.path.basename(a.reference)
        packs = [a.reference]
    man = trial.build(a.name, [m for m in a.mods.split(",") if m], src=a.source, world=a.world, shader=shader, force=True,
                      renderer="angelica", jars=[DEBUG_JAR], shaderpacks=packs, quiet=True,
                      resourcepacks=a.resourcepack)
    d = trial.trial_dir(a.name)
    set_kv(os.path.join(d, "options.txt"), {"maxFps": "260", "fullscreen": "false",
                                             "pauseOnLostFocus": "false", "enableVsync": "false"}, ":")
    opts = {"QF_DEBUG_VIEW": str(a.debug_view)}
    if a.preset != "off":
        opts["QF_PRESET"] = a.preset
    for o in a.opt:
        k, v = o.split("=", 1)
        opts[k] = v
    if not a.reference:
        set_kv(os.path.join(d, "shaderpacks", "QuestForge.txt"), opts, "=")
    for sub in ("bench", "screenshots"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    for old in glob.glob(os.path.join(d, "screenshots", f"bench-{a.tag}*.png")) + [os.path.join(d, "bench", a.tag + ".txt")]:
        if os.path.exists(old):
            os.remove(old)
    shutil.rmtree(os.path.join(d, "patched_shaders"), ignore_errors=True)

    props = ["qf.bench=1", f"qf.bench.tag={a.tag}", f"qf.bench.scenes={a.scenes}", f"qf.bench.views={VIEWS}",
             f"qf.bench.gallery={GALLERY}", "fml.queryResult=confirm"]
    cmd = [sys.executable, "-I", TRIAL_PY, "launch", a.name, "--size", a.size, "--xmx", a.xmx, "--owner", "shader-dev",
           "--idle-min", "1"]
    if a.foreground:
        cmd.append("--foreground")
    for p in props:
        cmd += ["-D", p]
    if a.reload:
        cmd += ["-D", f"qf.bench.reload={a.reload}"]
    result = os.path.join(d, "bench", a.tag + ".txt")
    log = os.path.join(d, "logs", "latest.log")
    busy = []
    pack = None if shader == "off" else (os.path.basename(packs[0]) if a.reference else "QuestForge")
    invalid = None
    for attempt in (1, 2, 3):
        want, bad = shader_config_ok(d, pack)
        if bad:
            print(f"  PRECHECK: config/shaders.properties has {bad}, want {want}: rewriting it")
            set_kv(os.path.join(d, "config", "shaders.properties"), want, "=")
            want, bad = shader_config_ok(d, pack)
            if bad:
                sys.exit(f"PRECHECK failed: config/shaders.properties still has {bad}")
        if not a.foreground:
            # Wait out the owner's game here, before the timeout clock starts; the launch's own
            # gate then needs a single idle check.
            trial.wait_user_idle(5, a.wait_min)
        t0 = time.time()
        busy.append(trial.user_busy())
        crashed_early = run_client(a, d, cmd, t0, busy)
        ok, why = shader_log_ok(log, pack)
        invalid = None if ok else why
        if os.path.exists(result) and invalid:
            print(f"  INVALID run ({why}): discarding its frames and re-running once")
            os.remove(result)
            for old in glob.glob(os.path.join(d, "screenshots", f"bench-{a.tag}*.png")):
                os.remove(old)
            if attempt < 3:
                continue
        if os.path.exists(result) or not crashed_early or attempt == 3:
            break
        # Angelica 2.2.33: when the pack's transform misses the shader disk cache, Iris builds
        # the pipeline before the game's last resource reload and again after it ([Load #2]);
        # the rebuilt pipeline's full-screen quad then draws with a stale VAO and the JVM dies
        # at the first world frame. The failed boot has filled the cache, so the retry loads once.
        print("  early crash after a pipeline rebuild ([Load #2]): retrying once with the warm shader cache")

    if os.path.exists(log):
        errs = [l.strip() for l in open(log, encoding="utf-8", errors="replace") if SHADER_ERR.search(l)]
        for l in errs[:40]:
            print("  LOG " + l[:300])
        os.makedirs(os.path.join(ROUNDS, "logs"), exist_ok=True)
        shutil.copy2(log, os.path.join(ROUNDS, "logs", a.tag + ".log"))
    for sub in ("bench", "screenshots"):
        os.makedirs(os.path.join(ROUNDS, sub), exist_ok=True)
    # Frame times taken while the owner games share the GPU: mark them, don't trust them.
    reasons = sorted({r for b in busy for r in b.get("reasons", [])}) if any(b.get("busy") for b in busy) else []
    with open(os.path.join(ROUNDS, "bench", a.tag + ".userbusy.json"), "w", encoding="utf-8") as f:
        json.dump({"noisy": bool(reasons), "reasons": reasons, "background": not a.foreground, "checks": busy}, f)
    if reasons:
        print("NOISY: owner gaming during the round -- frame times are not comparable: " + "; ".join(reasons))
    if os.path.exists(result):
        shutil.copy2(result, os.path.join(ROUNDS, "bench", a.tag + ".txt"))
        print(open(result, encoding="utf-8").read())
    else:
        print("NO RESULT FILE" + (f" (INVALID: {invalid})" if invalid else ""))
    shots = glob.glob(os.path.join(d, "screenshots", f"bench-{a.tag}*.png"))
    for s in shots:
        shutil.copy2(s, os.path.join(ROUNDS, "screenshots", os.path.basename(s)))
    print(f"{len(shots)} frames -> {os.path.join(ROUNDS, 'screenshots')}")
    ps = os.path.join(d, "patched_shaders")
    if os.path.isdir(ps):
        dst = os.path.join(ROUNDS, "patched", a.tag)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(ps, dst)
    sys.exit(0 if os.path.exists(result) else 1)


if __name__ == "__main__":
    main()
