#!/usr/bin/env python3
"""Build site/lib/sfx/ from Minecraft 1.7.10's and OreSpawn's sounds (local game files).

    python3 tools/site/build_sfx.py --own-only # drop the game sounds, keep qf.* and music.*
    python3 tools/site/build_sfx.py            # transcode game sounds, write manifest.json
    python3 tools/site/build_sfx.py --qf       # also merge the site's own sounds (needs the
                                               # synth venv; see tools/music/site_cues.py)

Sources are read from the CrazyCraft4 instance on the Mac: the 1.7.10 asset index (events from
the object for minecraft/sounds.json) and mods/orespawn.zip. Each ogg becomes a mono AAC .m4a
(22.05 kHz, 56 kbps, 40 kbps for OreSpawn, leading silence trimmed) so Safari decodes it and positional audio works.
The qf.* and music.* entries are kept: this script only rewrites minecraft and orespawn events.
"""
import json, os, re, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SFX = os.path.join(ROOT, "site", "lib", "sfx")
CC = os.path.expanduser("~/Library/Application Support/crazycraft4")
ASSETS = os.path.join(CC, "assets")
FFMPEG = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
KEEP = ("mob", "random", "dig", "step", "liquid", "fire", "ambient", "game", "portal",
        "fireworks", "damage", "note")
BITRATE = "56k"

def encode(src_bytes, dst, br=BITRATE):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    af = "silenceremove=start_periods=1:start_threshold=-55dB:start_silence=0.004"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", "pipe:0", "-af", af, "-ac", "1", "-ar", "22050",
                    "-c:a", "aac", "-b:a", br, "-movflags", "+faststart", dst],
                   input=src_bytes, check=True)

def pitch_for(name):
    if name.startswith(("step.", "dig.")): return [0.8, 1.2]
    if name.startswith(("damage.", "random.hurt", "random.bowhit", "random.break", "random.pop", "random.orb")): return [0.8, 1.2]
    if name.startswith("mob."): return [0.9, 1.1]
    if name.startswith(("random.explode", "random.anvil", "random.chest", "random.door", "random.click", "fireworks.")): return [0.9, 1.1]
    if name.startswith("liquid.") or name.startswith("fire."): return [0.9, 1.1]
    return 1

def bus_for(name):
    if name.startswith("ambient."): return "ambient"
    if name in ("random.click", "random.pop"): return "ui"
    return "sfx"

def volume_for(name):
    if name.startswith(("step.", "dig.")): return 0.8
    if name.startswith("ambient."): return 0.9
    return 1

def main():
    if "--own-only" in sys.argv or not os.path.isdir(ASSETS):
        # Rebuild without Mojang's or OreSpawn's sounds: drop them, keep our own qf.* / music.* entries.
        import shutil
        for d in os.listdir(SFX):
            if d != "qf" and os.path.isdir(os.path.join(SFX, d)): shutil.rmtree(os.path.join(SFX, d))
        mp = os.path.join(SFX, "manifest.json")
        old = json.load(open(mp))["events"] if os.path.exists(mp) else {}
        json.dump({"events": {k: v for k, v in old.items() if k.startswith(("qf.", "music."))}}, open(mp, "w"), indent=1)
        print("own sounds only"); return
    idx = json.load(open(os.path.join(ASSETS, "indexes", "1.7.10.json")))["objects"]
    def obj(key):
        h = idx[key]["hash"]; return os.path.join(ASSETS, "objects", h[:2], h)
    table = json.load(open(obj("minecraft/sounds.json")))
    jobs, events = {}, {}
    for name, ev in table.items():
        if name.split(".")[0] not in KEEP and not name.startswith("tile.piston") and name != "creeper.primed": continue
        files = []
        for s in ev["sounds"]:
            s = s["name"] if isinstance(s, dict) else s
            key = f"minecraft/sounds/{s}.ogg"
            if key not in idx: continue
            rel = s + ".m4a"; files.append(rel)
            jobs[rel] = ("mc", key)
        if files:
            e = {"files": files, "volume": volume_for(name), "pitch": pitch_for(name), "bus": bus_for(name)}
            events[name] = e
    for alias, src in (("random.fuse", "creeper.primed"), ("random.glass", "dig.glass"), ("liquid.splash", "random.splash")):
        if src in events and alias not in events: events[alias] = dict(events[src])
    for w, src in (("idle", "idle"), ("hurt", "hit"), ("death", "death")):   # 1.7.10 has no witch sounds: a villager, pitched down
        if f"mob.villager.{src}" in events: events[f"mob.witch.{w}"] = {**events[f"mob.villager.{src}"], "pitch": [0.55, 0.7]}
    z = zipfile.ZipFile(os.path.join(CC, "mods", "orespawn.zip"))
    ore = json.loads(z.read("assets/orespawn/sounds.json"))
    for name, ev in ore.items():
        files = []
        for s in ev["sounds"]:
            key = f"assets/orespawn/sounds/{s}.ogg"
            if key not in z.namelist(): continue
            rel = f"orespawn/{s}.m4a"; files.append(rel); jobs[rel] = ("ore", key)
        if files:
            events[f"orespawn:{name}"] = {"files": files, "volume": 1, "pitch": [0.95, 1.05], "bus": "sfx"}
            for f in files:   # each variant is also addressable on its own: orespawn:roar1
                b = os.path.basename(f)[:-4]
                if len(files) > 1 and b != name: events.setdefault(f"orespawn:{b}", {"files": [f], "volume": 1, "pitch": [0.95, 1.05], "bus": "sfx"})
    def run(item):
        rel, (kind, key) = item
        data = open(obj(key), "rb").read() if kind == "mc" else z.read(key)
        encode(data, os.path.join(SFX, rel))
    todo = [i for i in jobs.items() if not os.path.exists(os.path.join(SFX, i[0]))]
    print(f"{len(jobs)} files ({len(todo)} to encode), {len(events)} events")
    z_lock = None
    # zipfile reads are not thread safe: pre-read ore data serially
    cache = {k: z.read(k) for (_, (kd, k)) in todo if kd == "ore"}
    def run2(item):
        rel, (kind, key) = item
        data = open(obj(key), "rb").read() if kind == "mc" else cache[key]
        encode(data, os.path.join(SFX, rel), "40k" if kind == "ore" else BITRATE)
    with ThreadPoolExecutor(8) as ex: list(ex.map(run2, todo))
    mpath = os.path.join(SFX, "manifest.json")
    old = json.load(open(mpath))["events"] if os.path.exists(mpath) else {}
    mine = {k: v for k, v in old.items() if k.startswith(("qf.", "music."))}
    events.update(mine)
    json.dump({"events": dict(sorted(events.items()))}, open(mpath, "w"), indent=1)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(SFX) for f in fs)
    print(f"bank {size/1e6:.2f} MB, {len(events)} events")

if __name__ == "__main__": main()
