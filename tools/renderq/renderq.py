#!/usr/bin/env python3
"""renderq: the one render queue for shader and texture rounds (2026-10-25).

Agents never launch a client for a render again. They submit a spec; one runner, started
hidden, owns the single client slot and drains the queue:

    py -3.10 -I tools/renderq/renderq.py submit spec.json      -> prints the submission id
    py -3.10 -I tools/renderq/renderq.py status                 -> state, ETA, done/total, why it waits
    py -3.10 -I tools/renderq/renderq.py wait ID                -> returns when ID is finished (background task)
    py -3.10 -I tools/renderq/renderq.py results ID             -> frames, costs, cache hits
    py -3.10 -I tools/renderq/renderq.py pause [--after-boot] "gaming"   /  resume
    py -3.10 -I tools/renderq/renderq.py cancel ID
    py -3.10 -I tools/renderq/renderq.py start                  -> start the runner hidden (wscript), if not running
    py -3.10 -I tools/renderq/renderq.py stop                   -> ask the runner to exit after stopping its client
    py -3.10 -I tools/renderq/renderq.py install-task           -> print (or --yes: create) a scheduled task that starts it

The spec (tools/renderq/README.md):
    {"name": "r008-a", "owner": "shader-agent", "priority": 0,
     "defaults": {"size": "2560x1440"},
     "prebuild": [["py", "-3.10", "-I", "tools/textures/build_qf_textures.py", "--out", "C:/qfb/textures/x.zip"]],
     "jobs": [{"tag": "rh", "preset": "3", "scenes": "ocean_sunset,golden_lit"},
              {"tag": "rm0", "preset": "3", "opts": {"QF_MOTES": 0}, "scenes": ["forest_golden"]},
              {"tag": "off9h", "preset": "off", "scenes": "ocean_sunset,golden_lit,forest_golden"}]}

What the runner does that bench_round.py did per run:
- one boot per boot key (size, world, resource packs, mods, pack), many jobs in it (batch.py);
- the owner gate: a boot starts only after `userbusy` has said idle for 5 minutes; while a boot
  runs, userbusy is sampled every minute and if the owner starts gaming the client is stopped at
  once, the steps measured before it are kept and the rest re-render later;
- one client at a time, and it yields to any other session's client or lock;
- every rendered scene goes into the cache (cache/), keyed by everything that defines its frames,
  and an identical scene is never rendered twice (shaders-off baselines above all);
- retries a crashed boot (only the missing steps, at most 3 attempts per job);
- a stall watchdog: no progress for 20 minutes writes STALLED and status.json, stops the client
  and retries; status.json carries a heartbeat, so `status` also says when the runner is dead;
- sleep and wake: a jump in the wall clock resets every timer instead of counting as a stall.
"""
import argparse, datetime, glob, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import batch  # noqa: E402
from batch import trial  # noqa: E402

RQ = batch.RQ
QUEUE = os.path.join(RQ, "queue")
DONE = os.path.join(RQ, "done")
RESULTS = os.path.join(RQ, "results")
STATUS = os.path.join(RQ, "status.json")
PAUSE = os.path.join(RQ, "PAUSE")
STOP = os.path.join(RQ, "STOP")
STALLED = os.path.join(RQ, "STALLED")
FOCUS_ALERT = os.path.join(RQ, "FOCUS-ALERT")
LOCKF = os.path.join(RQ, "runner.lock")
LOG = os.path.join(RQ, "runner.log")
HIST = os.path.join(RQ, "history.jsonl")
CONFIG = os.path.join(RQ, "config.json")
START_VBS = os.path.join(RQ, "start.vbs")

IDLE_MIN = 5            # the owner must have been idle this long before a boot
SLOT_QUIET_MIN = 3      # and no other client for this long: yields to a session's own scripted run
                        # sequence (r007's q5.sh left ~90 s between its runs)
STALL_MIN = 20          # no progress this long -> STALLED
HANG_MIN = 6            # no log growth and no progress this long -> stop the client
MAX_ATTEMPTS = 3
SLEEP_GAP_S = 150       # a loop gap longer than this was a sleep (or a frozen PC), not work
DEFAULT_BOOT_S, DEFAULT_STEP_S = 100.0, 24.0
CONFIG_DEFAULT = {"night": {"enabled": False, "start": "23:00", "end": "08:00", "max_fps": 30,
                            "power_limit_w": None}}


def now_s():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{now_s()}] {msg}"
    try:
        print(line, flush=True)
    except (OSError, ValueError, AttributeError):
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def jdump(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def jload(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def config():
    c = json.loads(json.dumps(CONFIG_DEFAULT))
    for k, v in (jload(CONFIG, {}) or {}).items():
        if isinstance(v, dict):
            c.setdefault(k, {}).update(v)
        else:
            c[k] = v
    return c


# ------------------------------------------------------------------ submit

def normalize(spec):
    defaults = dict(batch.JOB_DEFAULTS, **spec.get("defaults", {}))
    jobs, tags = [], set()
    for raw in spec["jobs"]:
        j = dict(defaults, **raw)
        if not batch.TAG_RE.fullmatch(j.get("tag", "")) or "-" in j["tag"]:
            sys.exit(f"tag {j.get('tag')!r}: letters, digits, _ and . only")
        if j["tag"] in tags:
            sys.exit(f"tag {j['tag']} twice in one spec")
        tags.add(j["tag"])
        j["preset"] = str(j["preset"])
        if j["preset"] not in ("0", "1", "2", "3", "4", "off"):
            sys.exit(f"{j['tag']}: preset 0-4 or off")
        if not re.fullmatch(r"\d+x\d+", j["size"]):
            sys.exit(f"{j['tag']}: size WIDTHxHEIGHT")
        if isinstance(j["scenes"], str):
            j["scenes"] = [s for s in j["scenes"].split(",") if s]
        if isinstance(j["resourcepacks"], str):
            j["resourcepacks"] = [j["resourcepacks"]]
        if j["mode"] not in ("cost", "shot"):
            sys.exit(f"{j['tag']}: mode cost (frame times count) or shot (pictures only)")
        if j["mode"] == "shot" and not j.get("measure"):
            j["measure"] = 20
        for k in ("world", "views", "rounds"):
            j[k] = os.path.abspath(j[k])
        j["resourcepacks"] = [os.path.abspath(r) for r in j["resourcepacks"]]
        if j.get("reference"):
            j["reference"] = os.path.abspath(j["reference"])
        if not os.path.isfile(os.path.join(j["world"], "level.dat")):
            sys.exit(f"{j['tag']}: no world (level.dat) in {j['world']}")
        views = batch.views_table(j["views"])
        bad = [s for s in j["scenes"] if s not in views and s not in ("static", "fly", "torch", "torch_wall", "gallery")]
        if bad:
            sys.exit(f"{j['tag']}: unknown scenes {bad} (not in {j['views']})")
        jobs.append(j)
    return jobs


def cmd_submit(a):
    spec = jload(a.spec)
    if not spec or "jobs" not in spec:
        sys.exit(f"{a.spec}: not a renderq spec (needs a jobs list)")
    jobs = normalize(spec)
    pending = {j["tag"]: s["id"] for s in load_subs() for j in s["jobs"] if j["status"] == "pending"}
    clash = [j["tag"] for j in jobs if j["tag"] in pending]
    if clash and not a.replace:
        sys.exit(f"tags already queued: {', '.join(f'{t} ({pending[t]})' for t in clash)}; --replace drops them there")
    snaps = {}
    for j in jobs:
        if j["preset"] == "off":
            j["pack_dir"], j["pack_sig"] = None, None
        elif j.get("reference"):
            j["pack_dir"], j["pack_sig"] = j["reference"], batch.path_sig(j["reference"])
        else:
            src = os.path.abspath(j.get("pack") or batch.PACK)
            if src not in snaps:
                snaps[src] = batch.snapshot_pack(src)
            j["pack_dir"], j["pack_sig"] = snaps[src]
        j.update(status="pending", todo=list(j["scenes"]), done={}, attempts=0, cached=[])
    os.makedirs(QUEUE, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", spec.get("name") or os.path.splitext(os.path.basename(a.spec))[0])
    sid = time.strftime("%m%d-%H%M%S-") + name
    for j in jobs:
        j["submission"] = sid
    if clash:
        for s in load_subs():
            for j in s["jobs"]:
                if j["tag"] in clash and j["status"] == "pending":
                    j["status"] = "replaced"
            save_sub(s)
    sub = {"id": sid, "name": name, "owner": spec.get("owner", ""), "priority": spec.get("priority", 0),
           "submitted": time.time(), "spec": os.path.abspath(a.spec), "prebuild": spec.get("prebuild", []),
           "prebuild_done": not spec.get("prebuild"), "jobs": jobs, "status": "pending",
           "notify": spec.get("notify")}
    save_sub(sub)
    steps = sum(len(j["todo"]) for j in jobs)
    print(f"submitted {sid}: {len(jobs)} jobs, {steps} scene renders (cache hits are found at boot time)")
    print(f"  results: {os.path.join(RESULTS, sid, 'result.json')}  (renderq.py wait {sid})")
    if not runner_alive():
        print("  NOTE: the runner is not running: `renderq.py start`")


def load_subs():
    out = []
    for p in sorted(glob.glob(os.path.join(QUEUE, "*.json"))):
        s = jload(p)
        if s:
            out.append(s)
    out.sort(key=lambda s: (-s.get("priority", 0), s["submitted"]))
    return out


def save_sub(s):
    os.makedirs(QUEUE, exist_ok=True)
    jdump(os.path.join(QUEUE, s["id"] + ".json"), s)


# ------------------------------------------------------------------ runner state

def runner_alive():
    lk = jload(LOCKF)
    if not lk:
        return False
    st = jload(STATUS, {})
    # The heartbeat is the cheap test; the pid check covers a runner that is mid-boot-build.
    if time.time() - st.get("heartbeat", 0) < 180:
        return True
    return trial.pid_alive(lk.get("pid"))


def history():
    rows = []
    try:
        for l in open(HIST, encoding="utf-8"):
            try:
                rows.append(json.loads(l))
            except ValueError:
                pass
    except OSError:
        pass
    return rows[-30:]


def rates():
    """Measured boot overhead (launch to first step) and seconds per step, from recent boots."""
    h = [r for r in history() if r.get("steps_done")]
    boot = [r["boot_s"] for r in h if r.get("boot_s")]
    step = [r["step_s"] for r in h if r.get("step_s")]
    med = lambda v, d: sorted(v)[len(v) // 2] if v else d
    return med(boot, DEFAULT_BOOT_S), med(step, DEFAULT_STEP_S)


def queue_summary(subs):
    total = done = 0
    on, off = set(), set()
    for s in subs:
        for j in s["jobs"]:
            total += len(j["scenes"])
            done += len(j["scenes"]) - len(j["todo"]) if j["status"] == "pending" else len(j["scenes"])
            if j["status"] == "pending" and j["todo"]:
                k = json.loads(batch.boot_key(j))
                pack = k.pop("pack")
                (on if j["preset"] != "off" else off).add((json.dumps(k, sort_keys=True), pack))
    # shaders-off jobs ride along in any boot with the same size, world, packs and mods
    bases = {b for b, _ in on}
    return total, done, len(on) + len({b for b, _ in off if b not in bases})


class Runner:
    def __init__(self, a):
        self.a = a
        self.state, self.explain, self.current = "starting", "", None
        self.last_loop = time.time()
        self.memo = {}
        self.state_since = time.time()
        self.ran_last = False

    # status.json: what `renderq status` and the owner's phone-side agents read
    def status(self, state=None, explain=None, current="keep"):
        if state and state != self.state:
            self.state, self.state_since = state, time.time()
        if explain is not None:
            self.explain = explain
        if current != "keep":
            self.current = current
        subs = load_subs()
        total, done, nboots = queue_summary(subs)
        boot_s, step_s = rates()
        left = total - done
        # every boot still to run costs its boot time; the running boot's is spent once it renders
        spent = boot_s if self.current and self.current.get("step") else 0
        eta = max(nboots * boot_s + left * step_s - spent, 0) if left else 0
        st = {"heartbeat": time.time(), "heartbeat_at": now_s(), "runner_pid": os.getpid(),
              "state": self.state, "since": self.state_since, "explain": self.explain,
              "current": self.current, "done": done, "total": total, "boots_left": nboots,
              "eta_s": round(eta), "eta_at": time.strftime("%H:%M", time.localtime(time.time() + eta)) if left else None,
              "rates": {"boot_s": round(boot_s), "step_s": round(step_s, 1)},
              "paused": jload(PAUSE) if os.path.exists(PAUSE) else None,
              "stalled": jload(STALLED) if os.path.exists(STALLED) else None,
              "submissions": [{"id": s["id"], "owner": s.get("owner"),
                               "jobs": len(s["jobs"]),
                               "done": sum(len(j["scenes"]) - len(j["todo"]) for j in s["jobs"]),
                               "total": sum(len(j["scenes"]) for j in s["jobs"])} for s in subs]}
        os.makedirs(RQ, exist_ok=True)
        jdump(STATUS, st)

    def tick(self):
        """Once per loop: notice a sleep (a long gap) so it never counts as a stall."""
        gap = time.time() - self.last_loop
        self.last_loop = time.time()
        if gap > SLEEP_GAP_S:
            log(f"woke after a {gap / 60:.0f} min gap (sleep?): timers reset")
            return True
        return False

    def nap(self, s):
        end = time.time() + s
        while time.time() < end:
            if os.path.exists(STOP):
                return
            time.sleep(min(5, max(0.1, end - time.time())))
            self.status()

    # ---------------------------------------------------------------- the loop
    def run(self):
        os.makedirs(RQ, exist_ok=True)
        lk = jload(LOCKF)
        if lk and lk.get("pid") != os.getpid() and trial.pid_alive(lk.get("pid")):
            sys.exit(f"a runner is already running (pid {lk['pid']})")
        jdump(LOCKF, {"pid": os.getpid(), "at": time.time()})
        log(f"runner started, pid {os.getpid()}, repo {batch.REPO}")
        try:
            while not os.path.exists(STOP):
                self.tick()
                self.once()
        finally:
            if os.path.exists(STOP):
                os.remove(STOP)
            self.status("stopped", "the runner exited", current=None)
            try:
                os.remove(LOCKF)
            except OSError:
                pass
            log("runner exited")

    def once(self):
        if os.path.exists(PAUSE):
            p = jload(PAUSE, {})
            self.status("paused", f"paused {p.get('at', '')}: {p.get('why', '')} (renderq.py resume)", current=None)
            return self.nap(15)
        subs = load_subs()
        self.finish_cancelled(subs)
        subs = [s for s in load_subs() if s["status"] == "pending"]
        if os.path.exists(FOCUS_ALERT):
            self.status("paused", "FOCUS-ALERT: our client took the foreground; nothing launches until it is "
                        "cleared (delete FOCUS-ALERT, then resume)", current=None)
            return self.nap(15)
        if not subs:
            self.status("idle", "queue empty", current=None)
            if self.a.once:
                return self.exit_once()
            return self.nap(10)
        night = self.night_now()
        for s in subs:
            if not s.get("prebuild_done") and self.eligible(s, night):
                self.prebuild(s)
        subs = [s for s in load_subs() if s["status"] == "pending"]
        self.memo = {}
        for s in subs:
            if s.get("prebuild_done"):
                self.resolve_cache(s)
                self.finalize(s)
        subs = [s for s in load_subs() if s["status"] == "pending"]
        group = self.pick(subs, night)
        if not group:
            if subs:
                why = "night: only screenshot (mode shot) jobs run now" if night else "nothing eligible"
                self.status("waiting", why, current=None)
                return self.nap(60)
            return
        if self.a.dry_run:
            steps = batch.plan_steps(self.dedupe(group))
            log(f"DRY RUN: would boot {len(group)} jobs ({', '.join(j['tag'] for j in group)}), "
                f"{len(steps)} steps: {steps}")
            for j in group:
                j["status"], j["error"] = "failed", "dry run"
            self.save_group(group)
            return
        if not self.slot_free():
            return self.nap(30)
        if not self.owner_idle():
            return self.nap(60)
        self.run_boot(group, night)
        self.ran_last = True

    def exit_once(self):
        open(STOP, "w").close()

    def night_now(self):
        n = config()["night"]
        if not n.get("enabled"):
            return None
        h = datetime.datetime.now().strftime("%H:%M")
        a, b = n["start"], n["end"]
        inside = (a <= h < b) if a < b else (h >= a or h < b)
        return n if inside else None

    def eligible(self, s, night):
        return any(j["status"] == "pending" and j["todo"] and (not night or j["mode"] == "shot") for j in s["jobs"])

    def prebuild(self, s):
        """A submission's build steps (e.g. the texture pack) run once, before its first boot."""
        self.status("prebuild", f"{s['id']}: running {len(s['prebuild'])} build step(s)")
        for cmd in s["prebuild"]:
            log(f"prebuild {s['id']}: {subprocess.list2cmdline(cmd)}")
            t0 = time.time()
            r = subprocess.run(cmd, cwd=batch.REPO, capture_output=True, text=True, creationflags=trial.NO_WINDOW)
            out = (r.stdout + r.stderr).strip()
            log(f"  exit {r.returncode} after {time.time() - t0:.0f} s; {out[-600:]}")
            if r.returncode != 0:
                for j in s["jobs"]:
                    j["status"], j["error"] = "failed", f"prebuild failed: {out[-400:]}"
                s["prebuild_done"] = True
                s["prebuild_s"] = round(time.time() - t0)
                save_sub(s)
                return self.finalize(s)
        s["prebuild_done"] = True
        save_sub(s)

    def resolve_cache(self, s):
        changed = False
        for j in s["jobs"]:
            if j["status"] != "pending" or j.get("fresh") or not j["todo"]:
                continue
            for sc in list(j["todo"]):
                e = batch.cache_get(batch.cache_key(j, sc, self.memo))
                if e:
                    j["done"][sc] = batch.from_cache(e, j["tag"], j["rounds"])
                    j["todo"].remove(sc)
                    j["cached"].append(sc)
                    changed = True
        if changed:
            save_sub(s)

    def finalize(self, s):
        """Jobs with nothing left get their bench/<tag>.txt; a submission with no pending job gets
        results/<id>/result.json and moves to done/."""
        for j in s["jobs"]:
            if j["status"] == "pending" and not j["todo"]:
                batch.write_job_result(j, j["done"], j["rounds"], j["size"])
                j["status"] = "done"
                log(f"job {j['tag']} done ({len(j['cached'])} of {len(j['scenes'])} scenes from the cache)")
        save_sub(s)
        if any(j["status"] == "pending" for j in s["jobs"]):
            return
        res = {"id": s["id"], "owner": s.get("owner"), "finished": now_s(), "spec": s.get("spec"),
               "status": "done" if all(j["status"] == "done" for j in s["jobs"]) else "partial", "jobs": []}
        for j in s["jobs"]:
            sc = {}
            for name, lines in j["done"].items():
                m = re.match(r"\S+\s+frames\s+(\d+)\s+mean\s+([\d.]+) fps\s+p50\s+([\d.]+) ms\s+p99\s+([\d.]+)", lines[0])
                sc[name] = {"p50_ms": float(m.group(3)) if m else None, "p99_ms": float(m.group(4)) if m else None,
                            "frames": [os.path.join(j["rounds"], "screenshots", n) for n in batch.block_shots(lines)],
                            "cached": name in j["cached"]}
            res["jobs"].append({"tag": j["tag"], "status": j["status"], "preset": j["preset"], "size": j["size"],
                                "opts": j["opts"], "error": j.get("error"), "incidents": j.get("incidents", []),
                                "txt": os.path.join(j["rounds"], "bench", j["tag"] + ".txt"),
                                "missing": j["todo"] if j["status"] != "done" else [], "scenes": sc})
        os.makedirs(os.path.join(RESULTS, s["id"]), exist_ok=True)
        jdump(os.path.join(RESULTS, s["id"], "result.json"), res)
        s["status"] = res["status"]
        os.makedirs(DONE, exist_ok=True)
        jdump(os.path.join(DONE, s["id"] + ".json"), s)
        os.remove(os.path.join(QUEUE, s["id"] + ".json"))
        log(f"submission {s['id']} {res['status']}: {os.path.join(RESULTS, s['id'], 'result.json')}")

    def finish_cancelled(self, subs):
        for s in subs:
            c = os.path.join(QUEUE, s["id"] + ".cancel")
            if os.path.exists(c):
                for j in s["jobs"]:
                    if j["status"] == "pending":
                        j["status"], j["error"] = "cancelled", "cancelled"
                save_sub(s)
                os.remove(c)
                self.finalize(s)

    def pick(self, subs, night):
        """The next boot: the first pending job's boot key, and every pending job (any submission)
        that shares it. Shaders-off jobs share any pack's boot."""
        jobs = [j for s in subs if s.get("prebuild_done") for j in s["jobs"]
                if j["status"] == "pending" and j["todo"] and (not night or j["mode"] == "shot")]
        if not jobs:
            return None
        lead = jobs[0]
        def base(j):
            k = json.loads(batch.boot_key(j))
            k.pop("pack")
            return json.dumps(k, sort_keys=True)
        pack = lead.get("pack_sig") if lead["preset"] != "off" else next(
            (j.get("pack_sig") for j in jobs if base(j) == base(lead) and j["preset"] != "off"), None)
        group = [j for j in jobs if base(j) == base(lead) and (j["preset"] == "off" or j.get("pack_sig") == pack)]
        if night:
            for j in group:
                j["night"] = night
        return group[: self.a.max_jobs]

    def slot_free(self):
        # Clients only: a server (the friends' server, a census node) holds no GPU slot; it only
        # counts toward trial.py's RAM budget, which `launch` checks itself (2026-10-25: a
        # `status | grep "no Minecraft clients"` gate stalled r007's queue on the friends' server).
        clients = [p for p in trial.java_processes() if p["kind"] == "client"]
        held = trial.read_lock()
        held_alive = held and ((held.get("pid") and trial.pid_alive(held["pid"]))
                               or (not held.get("pid") and time.time() - held.get("at", 0) < 130))
        if clients or held_alive:
            who = ", ".join(p["gameDir"] for p in clients) or f"lock {held.get('trial')}"
            self.status("waiting-client", f"another client holds the one slot: {who}")
            self.slot_since = None
            self.ran_last = False      # another session uses the slot: yield to its next run too
            return False
        if self.ran_last:
            return True        # no other client seen since our own boot: nobody to yield to
        self.slot_since = getattr(self, "slot_since", None) or time.time()
        if time.time() - self.slot_since < SLOT_QUIET_MIN * 60:
            self.status("waiting-client", f"slot free for {(time.time() - self.slot_since) / 60:.1f} of the "
                        f"{SLOT_QUIET_MIN} min that let another session's next run go first")
            return False
        return True

    def owner_idle(self):
        b = trial.user_busy()
        if b.get("busy") is False and trial.idle_for() >= IDLE_MIN * 60 - 5:
            return True
        if b.get("busy"):
            self.status("waiting-owner", "owner busy: " + "; ".join(b.get("reasons", [])))
        elif b.get("busy") is None:
            self.status("waiting-owner", "userbusy gave no answer: " + "; ".join(b.get("reasons", [])))
        else:
            self.status("waiting-owner", f"owner idle for {trial.idle_for() / 60:.1f} of the {IDLE_MIN} min needed")
        return False

    # ---------------------------------------------------------------- one boot
    def dedupe(self, group):
        """The same frames asked for twice (an off baseline in two submissions) render once; the
        copy is served from the cache on the next loop."""
        seen, plan = set(), []
        for j in group:
            t = []
            for sc in j["todo"]:
                k = batch.cache_key(j, sc, self.memo)
                if k not in seen:
                    seen.add(k)
                    t.append(sc)
            if t:
                plan.append(dict(j, todo=t))
        return plan

    def run_boot(self, group, night):
        boot_id = "b" + time.strftime("%m%d%H%M%S")
        plan = self.dedupe(group)
        steps_total = sum(len(j["todo"]) for j in plan)
        log(f"boot {boot_id}: {len(group)} jobs ({', '.join(j['tag'] for j in group)}), {steps_total} steps, "
            f"{group[0]['size']}{', night cap' if night else ''}")
        self.status("booting", f"building the trial for {len(group)} jobs",
                    current={"boot": boot_id, "jobs": [j["tag"] for j in group], "steps": steps_total, "step": 0})
        t_build = time.time()
        try:
            d, cmd, info = batch.prepare_boot(boot_id, plan, log)
        except SystemExit as e:
            log(f"  boot setup failed: {e}")
            for j in group:
                j["attempts"] += 1
                if j["attempts"] >= MAX_ATTEMPTS:
                    j["status"], j["error"] = "failed", f"setup failed: {e}"
            self.save_group(group)
            return self.nap(60)
        pl = self.power_cap(night)
        if not self.slot_free():
            return
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=trial.NO_WINDOW)
        log("  " + r.stdout.strip().replace("\n", "\n  ")[-800:])
        if r.returncode != 0:
            log(f"  launch failed ({r.returncode}): {r.stderr.strip()[-400:]}")
            self.power_restore(pl)
            return self.nap(60)
        pid = int(open(os.path.join(d, "pid")).read().strip())
        outcome, busy_from, first_step_at = self.watch(d, pid, boot_id, steps_total, t0, [j["tag"] for j in plan])
        self.power_restore(pl)
        held = trial.read_lock()
        if held and held.get("pid") == pid and os.path.exists(trial.LOCK):
            os.remove(trial.LOCK)
        took = time.time() - t0
        probs, errs = batch.log_checks(d, plan, info)
        for e in errs[:20]:
            log("  LOG " + e)
        got = {} if probs else batch.collect(d, plan, lambda j: j["rounds"], busy_from, info, log, self.memo)
        n = 0
        planned = {j["tag"]: j["todo"] for j in plan}
        for j in group:
            for sc, lines in got.get(j["tag"], {}).items():
                j["done"][sc] = lines
                if sc in j["todo"]:
                    j["todo"].remove(sc)
                    n += 1
            missed = [sc for sc in planned.get(j["tag"], []) if sc in j["todo"]]
            if missed:
                # every boot that left this job's scenes undone, for results/status
                j.setdefault("incidents", []).append(f"{boot_id} {outcome}: {len(missed)} scene(s) left"
                                                     + (f" ({'; '.join(probs)})" if probs else ""))
            if missed and outcome not in ("busy", "paused", "stopped"):
                j["attempts"] += 1
                if j["attempts"] >= MAX_ATTEMPTS:
                    j["status"], j["error"] = "failed", f"{outcome} {MAX_ATTEMPTS} times; {'; '.join(probs)}"
        if probs:
            log(f"  INVALID boot ({'; '.join(probs)}): its frames are not used")
        # keep the client log next to the frames, as bench_round did
        rl = os.path.join(group[0]["rounds"], "logs")
        os.makedirs(rl, exist_ok=True)
        if os.path.exists(os.path.join(d, "logs", "latest.log")):
            shutil.copy2(os.path.join(d, "logs", "latest.log"), os.path.join(rl, boot_id + ".log"))
        step_s = (time.time() - first_step_at) / n if first_step_at and n else None
        row = {"boot": boot_id, "at": now_s(), "outcome": outcome, "jobs": [j["tag"] for j in group],
               "steps": steps_total, "steps_done": n, "wall_s": round(took), "build_s": round(t0 - t_build),
               "boot_s": round(first_step_at - t0) if first_step_at else None,
               "step_s": round(step_s, 1) if step_s else None, "night": bool(night), "size": group[0]["size"]}
        with open(HIST, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        log(f"boot {boot_id} {outcome}: {n}/{steps_total} steps in {took:.0f} s "
            f"(build {row['build_s']} s, boot {row['boot_s']} s, {row['step_s']} s/step)")
        self.save_group(group)

    def save_group(self, group):
        subs = {s["id"]: s for s in load_subs()}
        for j in group:
            s = subs.get(j["submission"])
            if not s:
                continue
            for i, k in enumerate(s["jobs"]):
                if k["tag"] == j["tag"]:
                    j.pop("night", None)
                    s["jobs"][i] = j
        for s in subs.values():
            save_sub(s)
            self.finalize(s)

    def watch(self, d, pid, boot_id, steps_total, t0, tags=()):
        """Follow the client until it exits. Returns (outcome, busy_from, first_step_at)."""
        prog = os.path.join(d, "bench", "_progress.txt")
        logf = os.path.join(d, "logs", "latest.log")
        last_prog, last_prog_t = None, time.time()
        last_size, last_size_t = -1, time.time()
        last_busy_check, last_idle_at = 0, time.time()
        first_step_at, outcome, busy_from = None, "crashed", None
        stalled_written = False
        seen_focus = 0
        limit = 15 * 60 + steps_total * 120
        while trial.pid_alive(pid):
            if self.tick():
                last_prog_t = last_size_t = time.time()
            p = open(prog, encoding="utf-8", errors="replace").read() if os.path.exists(prog) else ""
            kv = dict(l.split(" ", 1) for l in p.splitlines() if " " in l)
            if p and p != last_prog:
                last_prog, last_prog_t = p, time.time()
                if stalled_written and os.path.exists(STALLED):
                    os.remove(STALLED)
                    stalled_written = False
            step = int(kv.get("step", "0 0").split()[0]) if kv else 0
            if step >= 1 and not first_step_at:
                first_step_at = time.time()
            size = os.path.getsize(logf) if os.path.exists(logf) else 0
            if size != last_size:
                last_size, last_size_t = size, time.time()
            self.status("rendering" if step else "booting",
                        f"step {step}/{steps_total}: {kv.get('tag', '')} {kv.get('scene', '')} ({kv.get('stage', 'boot')})",
                        current={"boot": boot_id, "pid": pid, "jobs": list(tags), "steps": steps_total, "step": max(step - 1, 0),
                                 "tag": kv.get("tag"), "scene": kv.get("scene"), "stage": kv.get("stage"),
                                 "elapsed_s": round(time.time() - t0)})
            stop = None
            # window.ps1's focus guard (10-50 ms) logs every time our client was the foreground
            # window and hands focus back. That must never happen: stop, pause the queue, alert.
            fl = os.path.join(d, "logs", "focus.log")
            focus = [l.strip() for l in open(fl, encoding="utf-8", errors="replace")] if os.path.exists(fl) else []
            if len(focus) > seen_focus:
                for l in focus[seen_focus:]:
                    log("  FOCUS (handed back): " + l)
                seen_focus = len(focus)
            # LWJGL takes the foreground once at window creation when the owner is idle and the guard
            # hands it straight back (": ok"). Anything else is the failure that must never happen.
            focus = [l for l in focus if not l.endswith(": ok")]
            if focus:
                jdump(FOCUS_ALERT, {"at": now_s(), "boot": boot_id, "lines": focus[:20]})
                jdump(PAUSE, {"at": now_s(), "why": "FOCUS: our client was the foreground window (see FOCUS-ALERT); "
                              "find out why before resuming", "after_boot": False})
                log("  FOCUS STOLEN: " + " | ".join(focus[:3]))
            if os.path.exists(PAUSE) and not (jload(PAUSE, {}) or {}).get("after_boot"):
                stop, outcome = "paused", "paused"
            elif os.path.exists(STOP):
                stop, outcome = "runner stop", "stopped"
            elif time.time() - last_busy_check >= 60:
                last_busy_check = time.time()
                b = trial.user_busy()
                if b.get("busy"):
                    stop, outcome, busy_from = "owner busy: " + "; ".join(b.get("reasons", [])), "busy", last_idle_at
                else:
                    last_idle_at = time.time()
            if not stop and time.time() - last_prog_t > STALL_MIN * 60:
                stop, outcome = f"STALLED: no progress for {STALL_MIN} min", "stalled"
                jdump(STALLED, {"at": now_s(), "boot": boot_id, "progress": kv, "log_bytes": size})
                stalled_written = True
            elif not stop and time.time() - last_size_t > HANG_MIN * 60 and time.time() - last_prog_t > HANG_MIN * 60:
                stop, outcome = f"hung: no log or progress for {HANG_MIN} min", "hung"
            elif not stop and time.time() - t0 > limit:
                stop, outcome = f"timeout after {limit // 60} min", "timeout"
            if stop:
                log(f"  stopping the client: {stop}")
                subprocess.run([sys.executable, "-I", batch.TRIAL_PY, "stop", batch.TRIAL],
                               capture_output=True, creationflags=trial.NO_WINDOW)
                time.sleep(5)
                break
            time.sleep(10)
        else:
            # the client wrote its last progress ("stage done") right before it shut down
            last = open(prog, encoding="utf-8", errors="replace").read() if os.path.exists(prog) else ""
            outcome = "finished" if "stage done" in last else "crashed"
        if outcome == "finished" and os.path.exists(STALLED) and stalled_written:
            os.remove(STALLED)
        return outcome, busy_from, first_step_at

    # ---------------------------------------------------------------- night cap
    def power_cap(self, night):
        if not night or not night.get("power_limit_w"):
            return None
        q = subprocess.run(["nvidia-smi", "--query-gpu=power.limit", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, creationflags=trial.NO_WINDOW)
        old = q.stdout.strip().split("\n")[0] if q.returncode == 0 else None
        r = subprocess.run(["nvidia-smi", "-pl", str(night["power_limit_w"])], capture_output=True, text=True,
                           creationflags=trial.NO_WINDOW)
        log(f"  nvidia-smi -pl {night['power_limit_w']}: exit {r.returncode} {(r.stdout + r.stderr).strip()[:200]}")
        return old if r.returncode == 0 else None

    def power_restore(self, old):
        if old:
            r = subprocess.run(["nvidia-smi", "-pl", str(float(old))], capture_output=True, text=True,
                               creationflags=trial.NO_WINDOW)
            log(f"  power limit restored to {old} W: exit {r.returncode}")


# ------------------------------------------------------------------ CLI

def cmd_run(a):
    Runner(a).run()


def cmd_start(a):
    if runner_alive():
        print(f"runner already running (pid {(jload(LOCKF) or {}).get('pid')})")
        return
    os.makedirs(RQ, exist_ok=True)
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.isfile(pyw):
        sys.exit(f"no pythonw.exe next to {sys.executable}")
    me = os.path.abspath(__file__)
    # wscript runs the runner with no window at all (window style 0) and returns at once.
    with open(START_VBS, "w", encoding="utf-8") as f:
        f.write('Set sh = CreateObject("WScript.Shell")\r\n'
                f'sh.Run """{pyw}"" -I ""{me}"" run", 0, False\r\n')
    subprocess.run(["wscript.exe", "//B", "//Nologo", START_VBS], creationflags=trial.NO_WINDOW)
    for _ in range(20):
        time.sleep(1)
        if jload(LOCKF):
            print(f"runner started (pid {jload(LOCKF)['pid']}); log {LOG}")
            return
    print(f"runner did not report in 20 s; see {LOG}")


def cmd_stop(a):
    open(STOP, "w").close()
    print("asked the runner to stop (it stops its client first, keeping finished steps)")


def cmd_pause(a):
    jdump(PAUSE, {"at": now_s(), "why": " ".join(a.why) or "owner asked", "after_boot": a.after_boot})
    print("paused" + (" after the current boot" if a.after_boot else ": a running client is stopped within 10 s, "
                      "finished steps are kept") + ". `renderq.py resume` to go on.")


def cmd_resume(a):
    for p in (PAUSE, STALLED):
        if os.path.exists(p):
            os.remove(p)
    print("resumed")


def fmt_dur(s):
    s = int(s or 0)
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


def cmd_status(a):
    st = jload(STATUS)
    if a.json:
        print(json.dumps(st, indent=1))
        return
    if not st:
        print("no status yet: the runner has never run (`renderq.py start`)")
        return
    age = time.time() - st.get("heartbeat", 0)
    alive = age < 180
    print(f"runner: {'alive' if alive else 'NOT RUNNING (last heartbeat ' + fmt_dur(age) + ' ago; renderq.py start)'}"
          f"  pid {st.get('runner_pid')}")
    print(f"state:  {st['state']} for {fmt_dur(time.time() - st.get('since', time.time()))}: {st.get('explain', '')}")
    c = st.get("current")
    if c:
        print(f"boot:   {c.get('boot')} jobs {','.join(c.get('jobs', []) or [])} step {c.get('step')}/{c.get('steps')}"
              f" {c.get('tag') or ''} {c.get('scene') or ''} {c.get('stage') or ''}")
    print(f"queue:  {st['done']}/{st['total']} scene renders done, {st.get('boots_left')} boot(s) to go; "
          f"ETA {fmt_dur(st['eta_s'])}" + (f" (~{st['eta_at']}, if the owner stays idle)" if st.get("eta_at") else "")
          + f"; measured {st['rates']['boot_s']} s/boot, {st['rates']['step_s']} s/scene")
    for s in st.get("submissions", []):
        print(f"  {s['id']:<40} {s['done']}/{s['total']}  {s.get('owner') or ''}")
    if st.get("paused"):
        print(f"PAUSED: {st['paused']}")
    if st.get("stalled"):
        print(f"STALLED: {st['stalled']}")
    fa = jload(FOCUS_ALERT)
    if fa:
        print(f"FOCUS STOLEN ({fa['at']}, boot {fa['boot']}): our client was the foreground window. The queue is paused;")
        print(f"  {FOCUS_ALERT} has the lines. Delete it and `resume` only once the cause is understood.")


def cmd_wait(a):
    p = os.path.join(RESULTS, a.id, "result.json")
    t0 = time.time()
    while not os.path.exists(p):
        if time.time() - t0 > a.timeout_min * 60:
            sys.exit(f"not finished after {a.timeout_min} min; `renderq.py status`")
        time.sleep(20)
    cmd_results(a)


def cmd_results(a):
    p = os.path.join(RESULTS, a.id, "result.json")
    r = jload(p)
    if not r:
        q = jload(os.path.join(QUEUE, a.id + ".json"))
        sys.exit(f"{a.id}: not finished" + (f" ({sum(len(j['todo']) for j in q['jobs'])} renders left)" if q else
                                            " (no such submission)"))
    if a.json:
        print(json.dumps(r, indent=1))
        return
    print(f"{r['id']}: {r['status']}, finished {r['finished']}   ({p})")
    for j in r["jobs"]:
        hits = sum(1 for s in j["scenes"].values() if s["cached"])
        print(f"  {j['tag']:<10} {j['status']:<8} preset {j['preset']:<3} {j['size']:<10} {len(j['scenes'])} scenes"
              f" ({hits} cached)  {j['txt']}" + (f"  MISSING {j['missing']}" if j["missing"] else "")
              + (f"  {j['error']}" if j.get("error") else ""))
        for inc in j.get("incidents", []):
            print(f"      retried after {inc}")


def cmd_cancel(a):
    if not os.path.exists(os.path.join(QUEUE, a.id + ".json")):
        sys.exit(f"{a.id}: not queued")
    open(os.path.join(QUEUE, a.id + ".cancel"), "w").close()
    print(f"{a.id}: cancel asked; the runner drops its pending jobs (a running boot finishes its current step)")


def cmd_install_task(a):
    cmd = ["schtasks", "/Create", "/TN", "QuestForge renderq", "/SC", "MINUTE", "/MO", "10", "/F",
           "/TR", f'wscript.exe //B //Nologo "{START_VBS}"']
    print("A per-user task, no admin needed: every 10 minutes it runs start.vbs, which starts the runner only")
    print("when none is alive, so it also brings the runner back after a crash, a reboot or a logoff.")
    print("  " + subprocess.list2cmdline(cmd))
    if not a.yes:
        print("(not created: pass --yes to create it; `schtasks /Delete /TN \"QuestForge renderq\" /F` removes it)")
        return
    if not os.path.exists(START_VBS):
        sys.exit("run `renderq.py start` once first (it writes start.vbs)")
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=trial.NO_WINDOW)
    print((r.stdout + r.stderr).strip())


def cmd_cache(a):
    n, size = 0, 0
    for dp, dn, fn in os.walk(batch.CACHE):
        for f in fn:
            size += os.path.getsize(os.path.join(dp, f))
            n += f == "meta.json"
    print(f"{n} cached scene renders, {size / 1e6:.0f} MB in {batch.CACHE}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("submit"); p.add_argument("spec"); p.add_argument("--replace", action="store_true")
    p.set_defaults(f=cmd_submit)
    p = sp.add_parser("run", help="the runner loop (use `start`, which runs it hidden)")
    p.add_argument("--once", action="store_true", help="exit when the queue is empty")
    p.add_argument("--max-jobs", type=int, default=40, help="jobs per boot")
    p.add_argument("--dry-run", action="store_true", help="plan boots, never build or launch (tests)")
    p.set_defaults(f=cmd_run)
    sp.add_parser("start").set_defaults(f=cmd_start)
    sp.add_parser("stop").set_defaults(f=cmd_stop)
    p = sp.add_parser("pause"); p.add_argument("why", nargs="*"); p.add_argument("--after-boot", action="store_true")
    p.set_defaults(f=cmd_pause)
    sp.add_parser("resume").set_defaults(f=cmd_resume)
    p = sp.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(f=cmd_status)
    p = sp.add_parser("wait"); p.add_argument("id"); p.add_argument("--timeout-min", type=int, default=600)
    p.add_argument("--json", action="store_true"); p.set_defaults(f=cmd_wait)
    p = sp.add_parser("results"); p.add_argument("id"); p.add_argument("--json", action="store_true")
    p.set_defaults(f=cmd_results)
    p = sp.add_parser("cancel"); p.add_argument("id"); p.set_defaults(f=cmd_cancel)
    p = sp.add_parser("install-task"); p.add_argument("--yes", action="store_true"); p.set_defaults(f=cmd_install_task)
    sp.add_parser("cache").set_defaults(f=cmd_cache)
    a = ap.parse_args()
    if a.cmd == "run" and sys.stdout is None:
        sys.stdout = sys.stderr = open(os.devnull, "w")   # pythonw: no console; log() writes runner.log
    a.f(a)


if __name__ == "__main__":
    main()
