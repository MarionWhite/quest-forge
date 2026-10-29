"""One client boot that renders many render jobs (tools/renderq, 2026-10-25).

A job is one bench tag: a preset (or shaders off), option overrides, a scene list. Jobs that
share a boot key (window size, world, resource packs, mods, shader pack, night cap) render in
ONE boot: FrameBench's batch mode (-Dqf.bench.jobs) switches between them with Iris.reload()
and Iris.toggleShaders, instead of one 2-5 minute boot per option set.

Why every boot starts with shaders OFF: Angelica 2.2.33 crashes at the first world frame when
the pack's transform misses the shader disk cache at boot (the pipeline is built before the
game's last resource reload and again after it, [Load #2], and the rebuilt full-screen quad
draws with a stale VAO). Every option set or shader edit is a new cache key, so bench_round's
first launch crashed on every run of round 7 (49 s, then a 5-minute idle wait and a second
boot). Iris.toggleShaders(true) in the world builds the pipeline once, after every resource
reload, so it never takes that path.

This module has no queue logic: renderq.py groups jobs into boots and calls run_boot().
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TRIAL_PY = os.path.join(REPO, "tools", "trial", "trial.py")
REVIEW = os.path.join(REPO, "tools", "shaders", "review")
sys.path.insert(0, os.path.dirname(TRIAL_PY))
import trial  # noqa: E402

RQ = os.environ.get("QF_RENDERQ", r"C:\qfb\renderq")
JARS = os.path.join(RQ, "jars")
DEBUG_JAR = os.environ.get("QF_RENDERQ_JAR", os.path.join(JARS, "QuestForgeContent-1.0.0.jar"))  # FrameBench, batch mode
CACHE = os.path.join(RQ, "cache")
SNAP = os.path.join(RQ, "snap")
BOOTS = os.path.join(RQ, "boots")
TRIAL = "renderq"
PACK = os.path.join(REPO, "shaders", "QuestForge")
VIEWS = os.path.join(REVIEW, "views-world-master.txt")
GALLERY = os.path.join(REVIEW, "gallery-shader.txt")
WORLD = r"C:\qfb\world-master"
ROUNDS = r"C:\qfb\shaderdev\rounds"
MODS = "qfcontent,twilightforest"
TAG_RE = re.compile(r"[A-Za-z0-9_.]+")
SCENE_LINE = re.compile(r"^(\w+)\s+(frames\s|no frames recorded)")
SHADER_ERR = re.compile(r"(error|Error|ERROR|Failed to|failed to|Exception).*(shader|Shader|program|GLSL|Iris|iris)"
                        r"|(shader|Shader|Iris|iris).*(error|Error|ERROR|failed|Failed)")

JOB_DEFAULTS = {"preset": "3", "size": "2560x1440", "world": WORLD, "resourcepacks": [], "reference": None,
                "mods": MODS, "opts": {}, "debug_view": 0, "mode": "cost", "fresh": False, "xmx": "3G",
                "warm": 160, "measure": 0, "views": VIEWS, "rounds": ROUNDS, "cit": False,
                "jars": [], "props": [], "rps_top": []}


# ------------------------------------------------------------------ hashing / keys

def sha1_file(p, _memo={}):
    st = os.stat(p)
    k = (os.path.abspath(p), st.st_size, st.st_mtime_ns)
    if k not in _memo:
        h = hashlib.sha1()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        _memo[k] = h.hexdigest()
    return _memo[k]


def tree_sig(root, content=True):
    """Hash of a folder: every file's relative path plus its bytes (content=True) or its size and
    mtime (content=False: for a 200 MB world, where a stat is enough)."""
    h = hashlib.sha1()
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for n in sorted(fn):
            if n == "session.lock":
                continue
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, root).replace("\\", "/")
            h.update(rel.encode())
            if content:
                h.update(sha1_file(p).encode())
            else:
                st = os.stat(p)
                h.update(f"{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()


def path_sig(p):
    """A pack's identity. A zip by its entries (name, CRC, size), not its bytes: a rebuilt pack with
    the same content but new timestamps is the same pack and keeps its cached frames."""
    if not p:
        return None
    if os.path.isdir(p):
        return tree_sig(p)
    if p.lower().endswith(".zip"):
        import zipfile
        try:
            with zipfile.ZipFile(p) as z:
                ents = sorted(f"{i.filename}:{i.CRC}:{i.file_size}" for i in z.infolist())
            return "zip:" + hashlib.sha1("|".join(ents).encode()).hexdigest()
        except zipfile.BadZipFile:
            pass
    return sha1_file(p)


def snapshot_pack(src=PACK):
    """Copy the shader pack as it is NOW into snap/<hash>/QuestForge. A submitted job renders this
    copy, so the author can keep editing shaders/QuestForge while the job waits in the queue
    (before, an edit between a run's two launches broke it: NEXT.md, 2026-10-19 TRAP)."""
    sig = tree_sig(src)
    dst = os.path.join(SNAP, sig[:16], os.path.basename(src.rstrip("\\/")))
    if not os.path.isdir(dst):
        tmp = dst + ".tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(src, tmp)
        os.replace(tmp, dst)
    return dst, sig


def views_table(path):
    out = {}
    if path and os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#"):
                out[l.split()[0]] = " ".join(l.split())
    return out


def scene_sig(job, scene):
    """What defines a scene's picture: its line in the views file (camera, time, ticks), or the
    gallery list for the gallery, or the FrameBench build for a built-in scene."""
    v = views_table(job["views"]).get(scene)
    if v:
        return "view:" + v
    if scene == "gallery":
        return "gallery:" + sha1_file(GALLERY)
    return "builtin:" + scene


def mods_sig(mods):
    """The jars the trial would load (catalog resolution, Angelica renderer) and the FrameBench jar."""
    cat = trial.load_catalog()
    picked, _ = trial.resolve(cat, [m for m in mods.split(",") if m], (), trial.LIVE, False, False, "angelica")
    parts = sorted(f"{os.path.basename(rel)}:{os.path.getsize(p)}" for _, rel, p in picked if os.path.exists(p))
    parts.append("framebench:" + sha1_file(DEBUG_JAR))
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


# Resource packs switch in the world (FrameBench `rps`, with shaders off for the reload), so jobs
# with different packs share a boot. False puts the packs back into the boot key.
RPS_IN_GAME = True


def boot_key(job):
    """Jobs with the same boot key render in one boot. Shaders-off jobs ignore the pack."""
    on = job["preset"] != "off"
    rps = [] if RPS_IN_GAME else [os.path.normcase(os.path.abspath(r)) for r in job["resourcepacks"]]
    return json.dumps({"size": job["size"], "world": os.path.normcase(os.path.abspath(job["world"])),
                       "rps": rps,
                       "mods": job["mods"], "xmx": job["xmx"], "night": bool(job.get("night")),
                       "cit": bool(job.get("cit")),
                       # jars/props only when set, so every other job's boot key is unchanged
                       **({"jars": job["jars"]} if job.get("jars") else {}),
                       **({"props": job["props"]} if job.get("props") else {}),
                       "views": os.path.normcase(os.path.abspath(job["views"])),
                       "pack": (job.get("pack_sig") if on else None)}, sort_keys=True)


def options_text(job):
    """The option file a job renders with (shaderpacks/QuestForge.txt). bench_round copied the
    live instance's file, which has no QuestForge.txt, and set these keys: same result."""
    kv = {"QF_DEBUG_VIEW": str(job.get("debug_view", 0))}
    if job["preset"] != "off" and not job.get("reference"):
        kv["QF_PRESET"] = str(job["preset"])
    for k, v in job["opts"].items():
        kv[k] = str(v)
    if job.get("reference"):
        kv = {k: str(v) for k, v in job["opts"].items()}
    return "".join(f"{k}={v}\n" for k, v in kv.items())


def env_sig(job, memo):
    k = boot_key(job) + "|" + "|".join(job["resourcepacks"]) + "|^" + "|".join(job.get("rps_top") or [])
    if k not in memo:
        memo[k] = {"size": job["size"], "world": tree_sig(job["world"], content=False),
                   "rps": [path_sig(r) for r in job["resourcepacks"]], "mods": mods_sig(job["mods"]),
                   "night": bool(job.get("night"))}
        if job.get("rps_top"):     # only when set, so every other job's key is unchanged
            memo[k]["rps_top"] = [path_sig(r) for r in job["rps_top"]]
        if job.get("cit"):
            memo[k]["cit"] = True
        if job.get("jars"):
            memo[k]["jars"] = [f"{os.path.basename(j)}:{sha1_file(j)}" for j in job["jars"]]
        if job.get("props"):
            memo[k]["props"] = list(job["props"])
    return memo[k]


def cache_key(job, scene, memo):
    on = job["preset"] != "off"
    d = {"env": env_sig(job, memo), "scene": scene_sig(job, scene), "measure": job.get("measure", 0),
         "state": {"pack": job.get("pack_sig"), "opts": options_text(job)} if on else "off"}
    if job.get("burst"):
        d["burst"] = job["burst"]   # only burst jobs carry it: every other key is unchanged
    return hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------ result blocks

def parse_blocks(text):
    """A FrameBench result (txt or .part) -> {scene: [lines]}; a block runs from a scene line to
    the next one."""
    out, cur = {}, None
    for l in text.splitlines():
        m = SCENE_LINE.match(l)
        if m:
            cur = m.group(1)
            out[cur] = [l]
        elif cur and l.startswith(" "):
            out[cur].append(l)
    return out


def block_wall(lines):
    for l in lines:
        m = re.match(r"\s+wall (\d+)", l)
        if m:
            return int(m.group(1)) / 1000.0
    return None


def block_shots(lines):
    return [l.split("screenshots/", 1)[1].strip() for l in lines if "screenshot screenshots/" in l]


BURST_FRAME = re.compile(r"-f\d{3}\.png$")


def block_burst(lines):
    """A block's burst: (frame names, capture times in ms) or ([], [])."""
    frames = [s for s in block_shots(lines) if BURST_FRAME.search(s)]
    times = []
    for l in lines:
        m = re.match(r"\s+burst .*; times ([\d ]+)$", l)
        if m:
            times = [int(t) for t in m.group(1).split()]
    return frames, times


def cache_get(key):
    d = os.path.join(CACHE, key[:2], key)
    m = os.path.join(d, "meta.json")
    if not os.path.exists(m):
        return None
    meta = json.load(open(m, encoding="utf-8"))
    if not all(os.path.exists(os.path.join(d, s)) for s in meta["shots"]):
        return None
    return d, meta


def cache_put(key, lines, shots_dir, tag, scene, info):
    d = os.path.join(CACHE, key[:2], key)
    tmp = d + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    names = []
    for s in block_shots(lines):
        src = os.path.join(shots_dir, s)
        if os.path.exists(src):
            # stored without the tag: bench-<tag>-ocean_sunset-b.png -> ocean_sunset-b.png
            n = s[len(f"bench-{tag}"):].lstrip("-") or "_static.png"
            shutil.copy2(src, os.path.join(tmp, n))
            names.append(n)
    with open(os.path.join(tmp, "block.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(tmp, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(dict(info, tag=tag, scene=scene, shots=names, at=time.time()), f, indent=1)
    shutil.rmtree(d, ignore_errors=True)
    os.replace(tmp, d)


def from_cache(entry, tag, rounds):
    """Materialise a cached scene under a new tag: frames into rounds/screenshots, its block lines
    with the screenshot names rewritten."""
    d, meta = entry
    os.makedirs(os.path.join(rounds, "screenshots"), exist_ok=True)
    out = []
    for n in meta["shots"]:
        name = f"bench-{tag}.png" if n == "_static.png" else f"bench-{tag}-{n}"
        shutil.copy2(os.path.join(d, n), os.path.join(rounds, "screenshots", name))
    old = f"bench-{meta['tag']}"
    for l in open(os.path.join(d, "block.txt"), encoding="utf-8").read().splitlines():
        out.append(l.replace("screenshots/" + old, "screenshots/bench-" + tag))
    out.append(f"  cached from {meta['tag']} {time.strftime('%Y-%m-%d %H:%M', time.localtime(meta['at']))}")
    return out


# ------------------------------------------------------------------ one boot

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


def enable_cit(path):
    """Turn on the custom_item_textures module (enabled, items, enchantments) in a trial's
    mcpatcherforge.cfg. Written fresh (rm first): config files may be links."""
    lines = open(path, encoding="utf-8").read().splitlines()
    sect = None
    for i, l in enumerate(lines):
        t = l.strip()
        if t.endswith("{"):
            sect = t[:-1].strip()
        elif t == "}":
            sect = None
        elif sect == "custom_item_textures" and t in ("B:enabled=false", "B:items=false", "B:enchantments=false"):
            lines[i] = l.replace("=false", "=true")
    os.remove(path)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def plan_steps(jobs):
    """Scene-major order: each scene is placed and its chunks built once, then every job that
    wants it is measured there in turn (a reload rebuilds chunk meshes in seconds; a teleport
    reloads chunks and can take the full 45 s settle). Off jobs go first in each scene."""
    order = []
    for j in jobs:
        for s in j["todo"]:
            if s not in order:
                order.append(s)
    steps = []
    for i, s in enumerate(order):
        js = [j for j in jobs if s in j["todo"]]
        off = [j for j in js if j["preset"] == "off"]
        on = [j for j in js if j["preset"] != "off"]
        if i % 2:
            on.reverse()     # snake order: the last option set of one scene is the first of the next
        steps += [(j["tag"], s) for j in off + on]
    return steps


def prepare_boot(boot_id, jobs, log):
    """Build the trial and write the jobs file. Returns (trial dir, launch command, info)."""
    j0 = jobs[0]
    on = [j for j in jobs if j["preset"] != "off"]
    ref = next((j["reference"] for j in on if j.get("reference")), None)
    pack_dir = ref or (on[0]["pack_dir"] if on else None)
    pack_name = os.path.basename(pack_dir.rstrip("\\/")) if pack_dir else None
    t0 = time.time()
    rps_all = list(dict.fromkeys(r for j in jobs for r in j["resourcepacks"] + list(j.get("rps_top") or [])))
    trial.build(TRIAL, [m for m in j0["mods"].split(",") if m], world=j0["world"],
                shader=pack_name or "off", force=True, renderer="angelica", jars=[DEBUG_JAR] + list(j0.get("jars") or []),
                shaderpacks=[pack_dir] if pack_dir else [], quiet=True, resourcepacks=rps_all)
    d = trial.trial_dir(TRIAL)
    # FrameBench loads save 0, so the boot's world must be the only save. FML also leaves a 108 MB
    # backup zip of the world on every boot that confirms an ID remap (shaderdev's saves/ held
    # 507 of them, 52 GB, on 2026-10-25): this trial keeps none.
    sv = os.path.join(d, "saves")
    keep = os.path.basename(j0["world"].rstrip("\\/"))
    for n in os.listdir(sv) if os.path.isdir(sv) else []:
        if n != keep:
            p = os.path.join(sv, n)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    if j0.get("cit"):
        # MCPatcher custom item textures (potion bottles, enchanted-book covers): switched on in
        # THIS trial's config only, never the live instance's (boot_key keeps cit boots apart).
        enable_cit(os.path.join(d, "config", "mcpatcherforge.cfg"))
    log(f"  built trial {d} in {time.time() - t0:.0f} s")
    # Each job's resource pack list, as trial.build orders them (ours at the bottom, the source's
    # own packs, QuestForge.zip on top, then the job's rps_top above even that: a HUD that must
    # replace QuestForge.zip's widgets.png); the boot starts with the first step's.
    opt = os.path.join(d, "options.txt")
    cur = []
    for l in open(opt, encoding="utf-8", errors="replace"):
        if l.startswith("resourcePacks:"):
            try:
                cur = json.loads(l.split(":", 1)[1])
            except ValueError:
                cur = []
    ours = {os.path.basename(r.rstrip("\\/")) for r in rps_all}
    base = [c for c in cur if c not in ours]
    rps_of = {j["tag"]: [os.path.basename(r.rstrip("\\/")) for r in j["resourcepacks"]] + base
              + [os.path.basename(r.rstrip("\\/")) for r in (j.get("rps_top") or [])] for j in jobs}
    night = j0.get("night") or {}
    set_kv(os.path.join(d, "options.txt"), {"maxFps": str(night.get("max_fps", 260)), "fullscreen": "false",
                                             "pauseOnLostFocus": "false", "enableVsync": "false"}, ":")
    # Boot with shaders OFF (module docstring): the pack is named, so toggleShaders(true) finds it.
    set_kv(os.path.join(d, "config", "shaders.properties"),
           {"shaderPack": pack_name or "", "enableShaders": "false"}, "=")
    bd = os.path.join(BOOTS, boot_id)
    os.makedirs(bd, exist_ok=True)
    target = os.path.join(d, "shaderpacks", (pack_name + ".txt") if pack_name else "none.txt")
    lines = [f"# renderq boot {boot_id}", f"target {target}", "boot off"]
    first_opts = None
    for j in jobs:
        op = "-"
        if j["preset"] != "off":
            op = os.path.join(bd, f"opts-{j['tag']}.txt")
            with open(op, "w", encoding="utf-8", newline="\n") as f:
                f.write(options_text(j))
            first_opts = first_opts or op
        lines.append(f"job {j['tag']} {'off' if j['preset'] == 'off' else 'on'} {int(j['warm'])} "
                     f"{int(j.get('measure') or 0)} {op}")
    if rps_all:
        lines += [f"rps {j['tag']} " + "|".join(rps_of[j["tag"]]) for j in jobs]
    for j in jobs:
        b = j.get("burst")
        if b:
            lines.append(f"burst {j['tag']} {int(b['frames'])} {int(b['interval_ms'])}"
                         + ("".join(f" {int(v)}" for v in b["crop"]) if b.get("crop") else ""))
    steps = plan_steps(jobs)
    lines += [f"step {t} {s}" for t, s in steps]
    if rps_all and steps:
        set_kv(opt, {"resourcePacks": json.dumps(rps_of[steps[0][0]], separators=(",", ":"))}, ":")
    jf = os.path.join(bd, "jobs.txt")
    with open(jf, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    if first_opts:
        if os.path.exists(target):
            os.remove(target)
        shutil.copy2(first_opts, target)
    for sub in ("bench", "screenshots"):
        p = os.path.join(d, sub)
        shutil.rmtree(p, ignore_errors=True)
        os.makedirs(p)
    shutil.rmtree(os.path.join(d, "patched_shaders"), ignore_errors=True)
    props = ["qf.bench=1", "qf.bench.resetTime=1", f"qf.bench.tag={boot_id}", f"qf.bench.jobs={jf}", f"qf.bench.views={j0['views']}",
             f"qf.bench.gallery={GALLERY}", "fml.queryResult=confirm"]
    props += list(j0.get("props") or [])
    cmd = [sys.executable, "-I", TRIAL_PY, "launch", TRIAL, "--size", j0["size"], "--xmx", j0["xmx"],
           "--owner", "renderq", "--idle-min", "1"]
    for p in props:
        cmd += ["-D", p]
    return d, cmd, {"steps": steps, "pack": pack_name, "jobs_file": jf, "boot_dir": bd}


def collect(d, jobs, rounds_of, busy_from, info, log, memo):
    """After the client exits: per job, the scenes rendered in this boot (from bench/<tag>.txt or,
    after a crash or a stop, bench/<tag>.part). Steps whose wall time is at or after busy_from were
    measured while the owner was (maybe) gaming: dropped, so they re-render later.
    Returns {tag: {scene: lines}}."""
    got = {}
    for j in jobs:
        tag = j["tag"]
        txt = os.path.join(d, "bench", tag + ".txt")
        part = os.path.join(d, "bench", tag + ".part")
        src = txt if os.path.exists(txt) else part if os.path.exists(part) else None
        blocks = parse_blocks(open(src, encoding="utf-8", errors="replace").read()) if src else {}
        keep = {}
        for s, lines in blocks.items():
            if s not in j["todo"]:
                continue
            w = block_wall(lines)
            if busy_from and (w is None or w >= busy_from - 15):
                continue
            if any("no frames recorded" in l for l in lines[:1]):
                continue
            if any("incident no-terrain" in l for l in lines):
                # FrameBench found no client chunks round the camera (r008 boot b1026000221 shot
                # sky over void): not cached, so the retry renders it again.
                log(f"  {tag}/{s}: no terrain loaded, dropped for a retry")
                continue
            shots = block_shots(lines)
            if not all(os.path.exists(os.path.join(d, "screenshots", s2)) for s2 in shots):
                continue
            keep[s] = lines
        got[tag] = keep
        rounds = rounds_of(j)
        os.makedirs(os.path.join(rounds, "screenshots"), exist_ok=True)
        for s, lines in keep.items():
            for n in block_shots(lines):
                shutil.copy2(os.path.join(d, "screenshots", n), os.path.join(rounds, "screenshots", n))
            cache_put(cache_key(j, s, memo), lines, os.path.join(d, "screenshots"), tag, s,
                          {"mode": j["mode"], "boot": os.path.basename(info["boot_dir"])})
    return got


def log_checks(d, jobs, info):
    """The pack must have loaded and compiled when an on job ran (the 2026-10-23 guard)."""
    log = os.path.join(d, "logs", "latest.log")
    if not os.path.exists(log):
        return ["no client log"], []
    t = open(log, encoding="utf-8", errors="replace").read()
    probs = []
    if any(j["preset"] != "off" for j in jobs) and info.get("pack"):
        if "createProg name=" not in t and "Total shaderpack load time" not in t:
            probs.append("log: no shader program was compiled")
    errs = [l.strip()[:300] for l in t.splitlines() if SHADER_ERR.search(l)][:40]
    return probs, errs


def write_job_result(j, blocks, rounds, size):
    """bench/<tag>.txt in rounds, in the single-run format (check_frames, make_spec, costs read it),
    plus <tag>.meta.json saying what the frames are (for finish_round's baseline lookup)."""
    os.makedirs(os.path.join(rounds, "bench"), exist_ok=True)
    lines = [f"tag {j['tag']}  display {size}"]
    for s in j["scenes"]:
        lines += blocks.get(s, [f"{s:<7} no frames recorded"])
    with open(os.path.join(rounds, "bench", j["tag"] + ".txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    meta = {k: j.get(k) for k in ("tag", "preset", "size", "world", "resourcepacks", "reference", "mods", "opts",
                                  "debug_view", "mode", "pack_sig", "scenes", "submission", "burst")}
    meta["night"] = bool(j.get("night"))
    meta["noisy"] = False
    with open(os.path.join(rounds, "bench", j["tag"] + ".meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    with open(os.path.join(rounds, "bench", j["tag"] + ".userbusy.json"), "w", encoding="utf-8") as f:
        json.dump({"noisy": False, "reasons": [], "background": True, "checks": [],
                   "note": "renderq drops any step measured while the owner was busy"}, f)
