"""Write a superflat, creative, peaceful, no-mobs, noon-forever singleplayer world.

    py -3.10 tools/trial/make_flat_world.py C:\\qfb\\x\\world-flat [--name "Flat"] [--seed 1]

Only level.dat is written; the game generates the (trivial) chunks on first load.
Such a world is the right scene for a memory or render measurement: nothing in it
but what the probe places, so two runs differ only in the thing under test.

FML's own tag is left out on purpose: a level.dat without one is read as a fresh
world and gets the current block and item ids written into it, which is correct
here because there are no chunks whose ids could disagree.
"""
import argparse
import gzip
import os
import struct
import time

T_BYTE, T_INT, T_LONG, T_STRING, T_COMPOUND = 1, 3, 4, 8, 10


def _name(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def byte(v):
    return T_BYTE, struct.pack(">b", v)


def int_(v):
    return T_INT, struct.pack(">i", v)


def long_(v):
    return T_LONG, struct.pack(">q", v)


def string(v):
    return T_STRING, _name(v)


def compound(d):
    out = b""
    for k, (t, payload) in d.items():
        out += struct.pack(">b", t) + _name(k) + payload
    return T_COMPOUND, out + b"\x00"


def level_dat(name, seed):
    now = int(time.time() * 1000)
    data = compound({
        "version": int_(19133),
        "initialized": byte(1),
        "LevelName": string(name),
        "generatorName": string("flat"),
        "generatorVersion": int_(0),
        "generatorOptions": string(""),
        "RandomSeed": long_(seed),
        "MapFeatures": byte(0),
        "LastPlayed": long_(now),
        "SizeOnDisk": long_(0),
        "allowCommands": byte(1),
        "hardcore": byte(0),
        "GameType": int_(1),
        "Time": long_(0),
        "DayTime": long_(6000),
        "SpawnX": int_(0),
        "SpawnY": int_(4),
        "SpawnZ": int_(0),
        "raining": byte(0),
        "rainTime": int_(1000000),
        "thundering": byte(0),
        "thunderTime": int_(1000000),
        "GameRules": compound({
            "doDaylightCycle": string("false"),
            "doMobSpawning": string("false"),
            "doFireTick": string("false"),
            "keepInventory": string("true"),
            "mobGriefing": string("false"),
        }),
    })
    t, payload = compound({"Data": data})
    return struct.pack(">b", t) + _name("") + payload


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", help="world folder to create (its basename is the save name)")
    ap.add_argument("--name", help="LevelName (default: the folder's name)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if os.path.exists(os.path.join(out, "level.dat")):
        raise SystemExit(f"{out} already has a level.dat; delete it first")
    os.makedirs(out, exist_ok=True)
    with gzip.open(os.path.join(out, "level.dat"), "wb") as f:
        f.write(level_dat(a.name or os.path.basename(out), a.seed))
    print(f"wrote {os.path.join(out, 'level.dat')} (flat, creative, peaceful rules, noon)")


if __name__ == "__main__":
    main()
