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


def jobs():
    out = []
    for tier, weapon, armour, bosses in TIERS:
        for boss in bosses:
            out.append(dict(name=f"{tier}-{boss}-singles", phase="singles", tier=tier,
                            boss=boss, args=[weapon, f"armour={armour}", "controls=3"]))
    for tier, weapon, armour, _ in TIERS:
        for boss in DEEP[tier]:
            out.append(dict(name=f"{tier}-{boss}-pairs", phase="pairs", tier=tier, boss=boss,
                            args=[weapon, f"armour={armour}", "pairs", "modes=melee",
                                  "controls=3"]))
            out.append(dict(name=f"{tier}-{boss}-levels", phase="levels", tier=tier, boss=boss,
                            args=[weapon, f"armour={armour}", "levels=all", "controls=3"]))
            for hp in ("0.5", "0.25"):
                out.append(dict(name=f"{tier}-{boss}-hp{hp}", phase="wounded", tier=tier,
                                boss=boss, args=[weapon, f"armour={armour}", f"hp={hp}",
                                                 "modes=melee", f"only={HEALTH_CONDITIONAL}",
                                                 "controls=3"]))
    return out


REF_LINE = re.compile(r"reference target (\S+): median of \d+ settled spawns -> maxHealth "
                      r"([0-9.]+).*?attackDamage ([0-9.NaN]+)")


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
                    if m and m.group(1) not in refs:
                        refs[m.group(1)] = [m.group(2), m.group(3)]
                        save(refs_path, refs)
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
    ap.add_argument("--timeout-hours", type=float, default=4.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    refs_path = os.path.join(args.out, "refs.json")
    refs = load(refs_path, {})
    queue = [j for j in jobs() if not args.only_phase or j["phase"] == args.only_phase]
    queue = [j for j in queue
             if not os.path.exists(os.path.join(args.out, j["name"], "finished.json"))]
    attempts = {}
    if args.dry_run:
        for j in queue:
            print(j["name"], j["args"])
        print(len(queue), "jobs")
        return

    nodes = [Node(p) for p in args.nodes]
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
