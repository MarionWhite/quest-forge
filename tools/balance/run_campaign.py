#!/usr/bin/env python3
"""
Run the enchantment combat campaign over several census servers, unattended.

Each boss is fought with the weapon and armour the quest book has put in a
player's hands by the time they reach it (see TIERS). The campaign is a queue of
jobs -- one server launch each, `-Dqf.census.combat=...` -- handed out to idle
nodes until the queue is empty. A node is a copy of the combat server built by
tools/survey/build_server.py, each with its own server-port.

Same boss, same opponent. A boss's first job samples its median stats (fifteen
settled spawns, after the pack has scaled them). Every later job against that
boss -- pairs, all levels, a wounded wielder -- is passed those stats as
Name@health/attack and does not sample again, so every row about one boss is
about one opponent, whichever node ran it. The references are kept in
refs.json in the output directory.

Resumable: a job with a finished.json is skipped. Kill this and start it again
and it carries on. Create PAUSE in the output directory to let running jobs
finish and start no new ones (another session needs the machine); delete it to
carry on.

Usage:
    py -3.10 run_campaign.py --nodes C:\\qfs\\c1 C:\\qfs\\c2 C:\\qfs\\c3 \\
        --jar ..\\..\\mods\\qf-content\\build\\libs\\QuestForgeContent-1.0.0.jar \\
        --out C:\\qfs\\campaign [--only-phase singles] [--dry-run]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

JAVA = r"C:\Program Files\Eclipse Adoptium\jdk-8.0.504.1-hotspot\bin\java.exe"
FORGE_JAR = "forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
HEAP = "-Xmx4G"

DIAMOND = "minecraft:diamond_helmet+minecraft:diamond_chestplate+minecraft:diamond_leggings+minecraft:diamond_boots"
FIERY = ("TwilightForest:item.fieryHelm+TwilightForest:item.fieryPlate+"
         "TwilightForest:item.fieryLegs+TwilightForest:item.fieryBoots")
ULTIMATE = ("OreSpawn:OreSpawn_UltimateHelmet+OreSpawn:OreSpawn_UltimateBody+"
            "OreSpawn:OreSpawn_UltimateLegs+OreSpawn:OreSpawn_UltimateBoots")
ROYAL = ("OreSpawn:OreSpawn_RoyalHelmet+OreSpawn:OreSpawn_RoyalBody+"
         "OreSpawn:OreSpawn_RoyalLegs+OreSpawn:OreSpawn_RoyalBoots")

# Quest progression: what the player holds when they meet each boss.
TIERS = [
    ("T1", "minecraft:diamond_sword", DIAMOND, [
        "TwilightForest.Naga", "TwilightForest.Twilight_Lich", "TwilightForest.Minoshroom",
        "TwilightForest.Knight_Phantom", "TwilightForest.Snow_Queen",
        "TwilightForest.Yeti_Boss", "TwilightForest.Tower_Boss"]),
    ("T2", "TragicMC:titan", FIERY, [
        "witchery.death", "witchery.lordoftorment", "witchery.leonard", "witchery.babayaga",
        "witchery.hornedHuntsman", "WitherBoss", "HardcoreEnderExpansion.EnderDemon",
        "TragicMC.Apis", "TragicMC.Kitsune", "TragicMC.DeathReaper", "TragicMC.Polaris",
        "TragicMC.TimeController", "TragicMC.Enyvil", "chocolateQuest.monking"]),
    ("T3", "OreSpawn:OreSpawn_UltimateSword", ULTIMATE, [
        "Mantis", "Mothra", "Basilisk", "Emperor_Scorpion", "The_Kraken",
        "demonmobs.rahovart"]),
    ("T4", "OreSpawn:OreSpawn_Royal", ROYAL, [
        "Mobzilla", "The_Queen", "The_King", "legends.Godzilla", "demonmobs.rahovart"]),
]

# One boss per damage model, for the expensive passes.
DEEP = {
    "T1": ["TwilightForest.Naga"],                       # linear
    "T2": ["witchery.lordoftorment"],                    # per-hit cap
    "T3": ["Mantis"],
    "T4": ["Mobzilla"],                                  # first-hit-only window
}

# Offensive enchantments that read the wielder's own health, for the
# wounded-wielder passes. (Executioner reads the target's, which the health-band
# sweep already covers in every run.)
HEALTH_CONDITIONAL = "berserk+cultist"

# Per-boss census arguments, added to every job against that boss.
BOSS_ARGS = {
    # Immune to everything but its own reflected fireballs
    # (kitsunakumaFireballExempt=true): no weapon enchantment can act on it, so
    # only its melee on the wielder -- the armour cells -- means anything.
    "TragicMC.Kitsune": ["modes=defense"],
    # Takes player hits only through its parts; the eye is the weak point a
    # player aims for (other parts take dmg/6+1).
    "TragicMC.Enyvil": ["part=enyvilEye"],
}


def jobs(pairs_only=None):
    out = []
    for tier, weapon, armour, bosses in TIERS:
        for boss in bosses:
            out.append(dict(name=f"{tier}-{boss}-singles", phase="singles", tier=tier,
                            boss=boss, args=[weapon, f"armour={armour}", "controls=5"]
                            + BOSS_ARGS.get(boss, [])))
    for tier, weapon, armour, _ in TIERS:
        for boss in DEEP[tier]:
            if "modes=defense" in BOSS_ARGS.get(boss, []):
                continue   # every later phase is offensive
            # Pairs of every melee enchantment are 666 cells a boss, about eight
            # hours; they run only over a set chosen from the singles results.
            if pairs_only:
                out.append(dict(name=f"{tier}-{boss}-pairs", phase="pairs", tier=tier,
                                boss=boss, args=[weapon, f"armour={armour}", "pairs",
                                                 "modes=melee", f"only={pairs_only}",
                                                 "controls=3"]))
            out.append(dict(name=f"{tier}-{boss}-levels", phase="levels", tier=tier, boss=boss,
                            args=[weapon, f"armour={armour}", "levels=all", "controls=3"]))
            for hp in ("0.5", "0.25"):
                out.append(dict(name=f"{tier}-{boss}-hp{hp}", phase="wounded", tier=tier,
                                boss=boss, args=[weapon, f"armour={armour}", f"hp={hp}",
                                                 "modes=melee", f"only={HEALTH_CONDITIONAL}",
                                                 "controls=3"]))
    return out


REF_LINE = re.compile(r"reference target (.+?): median of \d+ settled spawns -> maxHealth "
                      r"([0-9.]+).*?attackDamage ([0-9.NaN]+)")


class Adopted:
    """A server process this driver did not start: polled by PID."""
    def __init__(self, pid):
        self.pid = pid
        self.returncode = None

    def poll(self):
        out = subprocess.run(["tasklist", "/FI", f"PID eq {self.pid}", "/NH"],
                             capture_output=True, text=True).stdout
        if str(self.pid) in out:
            return None
        self.returncode = 0
        return 0

    def kill(self):
        subprocess.run(["taskkill", "/PID", str(self.pid), "/F"], capture_output=True)

    def wait(self):
        return 0


class Node:
    def __init__(self, path):
        self.path = path
        self.proc = None
        self.job = None
        self.started = 0.0


def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def record_ref(refs_path, refs, boss, hp, atk):
    """Add one reference, merging with refs.json on disk first, so an entry
    written by someone else while this driver ran is not saved over."""
    refs.update({k: v for k, v in load(refs_path, {}).items() if k not in refs})
    refs[boss] = [hp, atk]
    save(refs_path, refs)


def backfill_refs(out, refs_path, refs):
    """Rebuild any missing reference from finished singles jobs' own census.log.
    Recovers bosses whose name has a space, which older drivers never recorded."""
    added = []
    for job in jobs():
        if job["phase"] != "singles" or job["boss"] in refs:
            continue
        d = os.path.join(out, job["name"])
        if not os.path.exists(os.path.join(d, "finished.json")):
            continue
        try:
            with open(os.path.join(d, "census.log"), encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = REF_LINE.search(line)
                    if m:
                        record_ref(refs_path, refs, job["boss"], m.group(2), m.group(3))
                        added.append(job["boss"])
                        break
        except OSError:
            pass
    if added:
        print(time.strftime("%H:%M:%S"), "backfilled references:", ", ".join(added), flush=True)


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def launch(node, job, refs, jar):
    shutil.copy2(jar, os.path.join(node.path, "mods", os.path.basename(jar)))
    cfg = os.path.join(node.path, "config")
    for f in os.listdir(cfg):
        if f.startswith("qfcontent-census-combat"):
            os.remove(os.path.join(cfg, f))
    for f in ("census-run.log", "census-err.log"):
        try:
            os.remove(os.path.join(node.path, f))
        except OSError:
            pass
    shutil.rmtree(os.path.join(node.path, "combat"), ignore_errors=True)

    target = job["boss"]
    if target in refs:
        hp, atk = refs[target]
        target = f"{target}@{hp}/{atk}"
    request = ",".join([target] + job["args"])
    log = open(os.path.join(node.path, "census-run.log"), "wb")
    err = open(os.path.join(node.path, "census-err.log"), "wb")
    node.proc = subprocess.Popen(
        [JAVA, "-Xms2G", HEAP, "-Dfml.queryResult=confirm",
         f"-Dqf.census.combat={request}", "-jar", FORGE_JAR, "nogui"],
        cwd=node.path, stdout=log, stderr=err, stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    node.job = job
    node.started = time.time()
    print(time.strftime("%H:%M:%S"), f"{os.path.basename(node.path)}: start {job['name']}"
          f" ({request[:160]})", flush=True)


def harvest(node, out_dir, refs, refs_path, timed_out):
    job = node.job
    dest = os.path.join(out_dir, job["name"])
    os.makedirs(dest, exist_ok=True)
    cfg = os.path.join(node.path, "config")
    for f in os.listdir(cfg):
        if f.startswith("qfcontent-census-combat"):
            shutil.copy2(os.path.join(cfg, f), dest)
    log_path = os.path.join(node.path, "census-run.log")
    keep = []
    finished = False
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "[census]" in line or "Calibration" in line or "refusing" in line:
                    keep.append(line)
                    if "combat census finished" in line:
                        finished = True
                    m = REF_LINE.search(line)
                    # Keyed by the job's boss, which is what launch() looks up;
                    # the logged name has spaces ("Yeti Boss") where the job has
                    # underscores, so keying by it left five bosses without one.
                    if m and job["boss"] not in refs:
                        record_ref(refs_path, refs, job["boss"], m.group(2), m.group(3))
    except OSError:
        pass
    with open(os.path.join(dest, "census.log"), "w", encoding="utf-8") as fh:
        fh.writelines(keep)
    status = dict(job=job, node=node.path, seconds=round(time.time() - node.started),
                  finished=finished, timed_out=timed_out,
                  exit=node.proc.returncode if node.proc else None)
    save(os.path.join(dest, "finished.json" if finished else "failed.json"), status)
    print(time.strftime("%H:%M:%S"), f"{os.path.basename(node.path)}: "
          f"{'done' if finished else 'FAILED'} {job['name']} in {status['seconds']} s", flush=True)
    node.proc = None
    node.job = None
    return finished


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", nargs="+", required=True)
    ap.add_argument("--jar", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-phase")
    ap.add_argument("--bosses", help="a,b,c: only jobs against these bosses (job names, e.g. Mantis,TwilightForest.Naga)")
    ap.add_argument("--pairs-only", help="a+b+c: the enchantments the pairs phase crosses")
    ap.add_argument("--timeout-hours", type=float, default=4.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--adopt", nargs="*", help="NODE=JOB=PID of servers already running")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    refs_path = os.path.join(args.out, "refs.json")
    refs = load(refs_path, {})
    queue = [j for j in jobs(args.pairs_only)
             if not args.only_phase or j["phase"] == args.only_phase]
    if args.bosses:
        wanted = {x.strip() for x in args.bosses.split(",") if x.strip()}
        queue = [j for j in queue if j["boss"] in wanted]
    queue = [j for j in queue
             if not os.path.exists(os.path.join(args.out, j["name"], "finished.json"))]
    attempts = {}
    if args.dry_run:
        for j in queue:
            print(j["name"], j["args"])
        print(len(queue), "jobs")
        return
    backfill_refs(args.out, refs_path, refs)

    nodes = [Node(p) for p in args.nodes]
    # --adopt NODE=JOB: a server already running that job (the driver was
    # restarted under it). Watch it by PID instead of launching a duplicate.
    for spec in args.adopt or []:
        path, name, pid = spec.split("=")
        for n in nodes:
            if os.path.normcase(n.path) == os.path.normcase(path):
                job = next(j for j in queue if j["name"] == name)
                queue.remove(job)
                n.job, n.started = job, time.time()
                n.proc = Adopted(int(pid))
                attempts[name] = 1

    running_bosses = set()
    while queue or any(n.proc for n in nodes):
        for node in nodes:
            if node.proc is None:
                continue
            timed_out = time.time() - node.started > args.timeout_hours * 3600
            if node.proc.poll() is None and not timed_out:
                continue
            if timed_out and node.proc.poll() is None:
                node.proc.kill()
                node.proc.wait()
            boss, job = node.job["boss"], node.job
            ok = harvest(node, args.out, refs, refs_path, timed_out)
            running_bosses.discard(boss)
            if not ok and attempts.get(job["name"], 0) < 2:
                queue.append(job)   # one retry; a crash at boot is usually transient
        # Another session needs the machine: finish what is running, start nothing.
        if os.path.exists(os.path.join(args.out, "PAUSE")):
            time.sleep(15)
            continue
        for node in nodes:
            if node.proc is not None:
                continue
            # A boss's later jobs wait for its reference, and never run beside
            # another job on the same boss (which would sample a second one).
            pick = None
            for j in queue:
                if j["boss"] in running_bosses:
                    continue
                if j["phase"] != "singles" and j["boss"] not in refs:
                    continue
                pick = j
                break
            if pick is None:
                continue
            queue.remove(pick)
            attempts[pick["name"]] = attempts.get(pick["name"], 0) + 1
            running_bosses.add(pick["boss"])
            launch(node, pick, refs, args.jar)
            time.sleep(20)   # stagger boots; three at once thrash the disk
        time.sleep(15)
    print(time.strftime("%H:%M:%S"), "campaign complete", flush=True)


if __name__ == "__main__":
    sys.exit(main())
