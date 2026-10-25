#!/usr/bin/env python3
"""Measure the client profiles (full, lite, potato) with FrameBench on ONE slim Angelica trial.

One measurement cycle: the profiles back to back, the same scenes, each profile at its
target resolution (docs/design/shaders/performance-rules.md budgets are per resolution).

What it does, per profile:
  1. applies the profile to the trial with apply-profile.ps1 (the real thing: options.txt,
     angelica-options.json, angelica-modules.cfg, shaders.properties, QF_PRESET, jars aside);
  2. two measurement-only overrides: maxFps 260 (the profile's cap would cap the numbers) and
     the FPS reducer off (a background client is never focused, and the reducer's unfocused
     limit of 10 fps is what the 2026-10-25 lite/potato fly and torch scenes measured);
  3. launches through trial.py's background mode (off-screen, never fullscreen, no console)
     only when trial.py grants its lock, after the owner has been idle, with free RAM checked;
  4. waits for the JVM to exit, copies bench/<tag>.txt, the frames and the log to --out.
  Angelica 2.2.33 dies at the first world frame when a preset's shader cache is cold
  ([Load #2] pipeline rebuild); the failed boot fills the cache, so one retry is made.

Rules (hard): never the full pack, never two clients, never over the owner's game. Run
`trial.py guard` is done before and after. Give up on the lock after --lock-wait minutes.

Usage (py -3.10 -I, as a BACKGROUND task, from anywhere):
  py -3.10 -I tools/lite-client/measure_profiles.py                 # full, lite, potato
  py -3.10 -I tools/lite-client/measure_profiles.py lite potato     # a subset
Needs: C:\\qfb\\shaderdev\\jars\\QuestForgeContent-1.0.0.jar (qf-content built with
-PqfDebugTools=true, which carries FrameBench) and C:\\qfb\\world-master (the bench world).
"""
import argparse, ctypes, glob, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools", "trial"))
import trial  # noqa: E402

TRIAL_PY = os.path.join(REPO, "tools", "trial", "trial.py")
APPLY = os.path.join(HERE, "apply-profile.ps1")
PACK = os.path.join(REPO, "shaders", "QuestForge")
DEBUG_JAR = r"C:\qfb\shaderdev\jars\QuestForgeContent-1.0.0.jar"
WORLD = r"C:\qfb\world-master"
PROFILES = {"full": "2560x1440", "lite": "1920x1080", "potato": "1280x720"}
HANG_MIN = 5
MIN_FREE_RAM_GB = 6


def log(s):
    print(time.strftime("%H:%M:%S"), s, flush=True)


def free_ram_gb():
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2**30


def slot_free():
    clients = [p for p in trial.java_processes() if p["kind"] == "client"]
    held = trial.read_lock()
    held_alive = held and ((held.get("pid") and trial.pid_alive(held["pid"]))
                           or (not held.get("pid") and time.time() - held.get("at", 0) < 130))
    who = ", ".join(p["gameDir"] for p in clients) or (f"lock {held.get('trial')} ({held.get('owner')})" if held_alive else "")
    return (not clients and not held_alive), who


def wait_slot(max_min):
    t0 = time.time()
    while True:
        free, who = slot_free()
        if free:
            return True
        if time.time() - t0 > max_min * 60:
            log(f"gave up after {max_min} min: client slot busy ({who})")
            return False
        log(f"waiting for the client slot: {who}")
        time.sleep(30)


def ps_apply(args):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                        "-ExecutionPolicy", "Bypass", "-File", APPLY] + args,
                       capture_output=True, text=True, creationflags=trial.NO_WINDOW)
    return r.returncode, (r.stdout + r.stderr).strip()


def read_kv(path, sep):
    kv = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8", errors="replace"):
            l = l.strip()
            if sep in l and not l.startswith("#"):
                k, v = l.split(sep, 1)
                kv[k] = v
    return kv


def measurement_overrides(d):
    """Measurement only, never part of a profile: no frame cap, no FPS reducer."""
    trial.set_option(os.path.join(d, "options.txt"), "maxFps", "260")
    ao = os.path.join(d, "config", "angelica-options.json")
    j = json.load(open(ao, encoding="utf-8"))
    j.setdefault("reducer", {})["enabled"] = False
    os.remove(ao)
    with open(ao, "w", encoding="utf-8", newline="\n") as f:
        json.dump(j, f, indent=2)


def run_profile(a, prof, size):
    d = trial.trial_dir(a.name)
    rc, out = ps_apply(["-Instance", d, "-Profile", prof])
    log(f"apply-profile {prof}: rc {rc}\n" + "\n".join("    " + l for l in out.splitlines()))
    if rc != 0:
        return None, "apply failed"
    measurement_overrides(d)
    sp = read_kv(os.path.join(d, "config", "shaders.properties"), "=")
    po = read_kv(os.path.join(d, "shaderpacks", "QuestForge.txt"), "=")
    log(f"  shaders.properties: enableShaders={sp.get('enableShaders')} shaderPack={sp.get('shaderPack')}; QF_PRESET={po.get('QF_PRESET')}")
    if sp.get("enableShaders") != "true" or sp.get("shaderPack") != "QuestForge":
        return None, "shader config wrong"
    tag = f"prof_{prof}"
    for old in glob.glob(os.path.join(d, "screenshots", f"bench-{tag}*.png")) + [os.path.join(d, "bench", tag + ".txt")]:
        if os.path.exists(old):
            os.remove(old)
    os.makedirs(os.path.join(d, "bench"), exist_ok=True)

    if not wait_slot(a.lock_wait):
        return None, "lock not granted"
    t0 = time.time()
    while free_ram_gb() < MIN_FREE_RAM_GB:
        if time.time() - t0 > 10 * 60:
            return None, f"free RAM stayed under {MIN_FREE_RAM_GB} GB"
        log(f"free RAM {free_ram_gb():.1f} GB < {MIN_FREE_RAM_GB}: waiting")
        time.sleep(30)
    try:
        trial.wait_user_idle(5, a.lock_wait)
    except SystemExit as e:
        return None, f"owner busy: {e}"
    free, who = slot_free()
    if not free:
        return None, f"lock taken while waiting for idle ({who})"
    cmd = [sys.executable, "-I", TRIAL_PY, "launch", a.name, "--size", size, "--xmx", a.xmx, "--owner", "lite-profile",
           "--idle-min", "1", "-D", "qf.bench=1", "-D", f"qf.bench.tag={tag}", "-D", f"qf.bench.scenes={a.scenes}",
           "-D", "fml.queryResult=confirm"]
    log(f"launch {prof} at {size}, free RAM {free_ram_gb():.1f} GB")
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=trial.NO_WINDOW)
    log(r.stdout.strip())
    if r.returncode != 0:
        log(r.stderr.strip())
        return None, f"launch refused ({r.returncode})"
    pid = int(open(os.path.join(d, "pid")).read().strip())
    t0 = time.time()
    logp = os.path.join(d, "logs", "latest.log")
    last_size, last_change = -1, time.time()
    busy = [trial.user_busy()]
    note = ""
    while trial.pid_alive(pid):
        if time.time() - t0 > 60 * len(busy):
            busy.append(trial.user_busy())
        if time.time() - t0 > a.timeout_min * 60:
            note = "timeout"
            subprocess.run([sys.executable, "-I", TRIAL_PY, "stop", a.name], creationflags=trial.NO_WINDOW)
            break
        size_now = os.path.getsize(logp) if os.path.exists(logp) else 0
        if size_now != last_size:
            last_size, last_change = size_now, time.time()
        elif time.time() - last_change > HANG_MIN * 60:
            note = "hung"
            subprocess.run([sys.executable, "-I", TRIAL_PY, "stop", a.name], creationflags=trial.NO_WINDOW)
            break
        time.sleep(10)
    held = trial.read_lock()
    if held and held.get("pid") == pid and os.path.exists(trial.LOCK):
        os.remove(trial.LOCK)
    took = time.time() - t0
    log(f"client exited after {took:.0f} s {note}")
    text = open(logp, encoding="utf-8", errors="replace").read() if os.path.exists(logp) else ""
    shader_ok = "Using shaderpack: QuestForge" in text and "createProg name=" in text and "Shaders are disabled" not in text
    noisy = sorted({r for b in busy for r in b.get("reasons", [])})
    result = os.path.join(d, "bench", tag + ".txt")
    os.makedirs(a.out, exist_ok=True)
    if os.path.exists(logp):
        shutil.copy2(logp, os.path.join(a.out, tag + ".log"))
    for s in glob.glob(os.path.join(d, "screenshots", f"bench-{tag}*.png")):
        shutil.copy2(s, a.out)
    if not os.path.exists(result):
        tail = [l.strip() for l in text.splitlines() if "FrameBench" in l][-10:]
        early = took < 120 and "[Load #2]" in text
        return None, f"no result file ({note or 'exited'} after {took:.0f} s; early_load2={early}); shader_ok={shader_ok}; " + " | ".join(tail)
    shutil.copy2(result, os.path.join(a.out, tag + ".txt"))
    body = "\n".join(l for l in open(result, encoding="utf-8").read().splitlines()
                     if l.split(" ")[0] in ("tag", "static", "fly", "torch", "torch_wall", "gallery") or l.startswith("  screenshot"))
    with open(os.path.join(a.out, tag + ".meta.json"), "w", encoding="utf-8") as f:
        json.dump({"profile": prof, "size": size, "scenes": a.scenes, "shader_ok": shader_ok, "noisy": noisy,
                   "took_s": round(took), "at": time.strftime("%Y-%m-%d %H:%M")}, f)
    return body, ("OK" if shader_ok else "shader NOT confirmed in log") + (f"; NOISY: {noisy}" if noisy else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profiles", nargs="*", default=list(PROFILES), help="full lite potato (default: all three)")
    ap.add_argument("--out", default=r"C:\qfb\lite-profiles", help="where results, frames and logs are copied")
    ap.add_argument("--scenes", default="static,fly,torch")
    ap.add_argument("--name", default="liteprof", help="trial name")
    ap.add_argument("--xmx", default="3G")
    ap.add_argument("--lock-wait", type=float, default=20, help="minutes to wait for the client slot")
    ap.add_argument("--timeout-min", type=int, default=20)
    ap.add_argument("--keep", action="store_true", help="keep the trial afterwards (default: trial.py remove)")
    a = ap.parse_args()
    bad = [p for p in a.profiles if p not in PROFILES]
    if bad:
        sys.exit(f"unknown profile(s): {', '.join(bad)}")
    for p in (DEBUG_JAR, WORLD):
        if not os.path.exists(p):
            sys.exit(f"missing: {p}")

    subprocess.run([sys.executable, "-I", TRIAL_PY, "guard"], creationflags=trial.NO_WINDOW)
    trial.build(a.name, ["qfcontent", "twilightforest"], world=WORLD, shader="QuestForge", force=True,
                renderer="angelica", jars=[DEBUG_JAR], shaderpacks=[PACK], quiet=True)
    log(f"built trial {a.name}")
    summary = []
    for prof in a.profiles:
        size = PROFILES[prof]
        body, note = run_profile(a, prof, size)
        if body is None and "early_load2=True" in note:
            log(f"== {prof}: early crash after a pipeline rebuild ([Load #2]); retrying once with the warm shader cache")
            body, note = run_profile(a, prof, size)
        summary.append((prof, size, note, body))
        log(f"== {prof} @ {size}: {note}\n{body or ''}")
        if note == "lock not granted":
            break
    if not a.keep:
        subprocess.run([sys.executable, "-I", TRIAL_PY, "remove", a.name], creationflags=trial.NO_WINDOW)
    subprocess.run([sys.executable, "-I", TRIAL_PY, "guard"], creationflags=trial.NO_WINDOW)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "summary.txt"), "a", encoding="utf-8") as f:
        f.write(f"\n##### {time.strftime('%Y-%m-%d %H:%M')} scenes {a.scenes}\n")
        for prof, size, note, body in summary:
            f.write(f"=== {prof} @ {size}: {note}\n{body or ''}\n")
    log("done; results in " + a.out)


if __name__ == "__main__":
    main()
