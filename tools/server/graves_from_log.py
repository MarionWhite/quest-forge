#!/usr/bin/env python3
"""Turn Minecraft server death messages into the Wall of Graves feed.

Reads one or more server logs (logs/latest.log, rotated *.log.gz) and writes the
JSON that site/graves/ reads. Stdlib only, Python 3.10+. Run it with `python3 -I`
or `py -3.10 -I` so nothing in the current directory is imported by accident.

    python3 -I graves_from_log.py --out graves.json logs/latest.log logs/2026-10-24-1.log.gz
    python3 -I graves_from_log.py --demo logs/latest.log          # print parsed lines, write nothing

Dates. The log has times only ("[HH:MM:SS]"), so each file's date comes from, in order:
  1. a YYYY-MM-DD in the file name (vanilla rotates to 2026-10-24-1.log.gz),
  2. --date YYYY-MM-DD,
  3. the file's modification time (good for latest.log, read the server's clock).
Inside one file a time that goes backwards means midnight passed, so the date advances.
Times are read in the host's local time zone and written as UTC.

Deaths only. A line counts when it is a Server-thread INFO message whose text starts
with a player name and then a vanilla 1.7.10 death template (death.attack.*). Chat
lines start with "<name>" and are skipped. Positions and dimensions are not in the
vanilla death line, so they are written as null; see tools/server/README-graves.md.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys

LINE = re.compile(r"^\[(\d\d:\d\d:\d\d)\] \[Server thread/INFO\]: (.*)$")
JOIN = re.compile(r"^([A-Za-z0-9_]{1,16})\[/[0-9.:]+\] logged in")
NAME = r"[A-Za-z0-9_]{1,16}"

# Vanilla 1.7.10 en_US.lang death.attack.* templates. %1$s is the victim (matched
# separately, at the start), %2$s the killer or the thing they were escaping or
# fighting, %3$s the held item. Each entry: (key, template body, cause).
# cause is the default category; a known player as the killer turns it into "player".
TEMPLATES = [
    # Copied from assets/minecraft/lang/en_US.lang in the 1.7.10 server jar (every death.attack.* key).
    ("death.attack.anvil", "was squashed by a falling anvil", "other"),
    ("death.attack.arrow", "was shot by %2$s", "mob"),
    ("death.attack.arrow.item", "was shot by %2$s using %3$s", "mob"),
    ("death.attack.cactus", "was pricked to death", "other"),
    ("death.attack.cactus.player", "walked into a cactus whilst trying to escape %2$s", "other"),
    ("death.attack.drown", "drowned", "drown"),
    ("death.attack.drown.player", "drowned whilst trying to escape %2$s", "drown"),
    ("death.attack.explosion", "blew up", "explosion"),
    ("death.attack.explosion.player", "was blown up by %2$s", "explosion"),
    ("death.attack.fall", "hit the ground too hard", "fall"),
    ("death.attack.fallingBlock", "was squashed by a falling block", "other"),
    ("death.attack.fireball", "was fireballed by %2$s", "mob"),
    ("death.attack.fireball.item", "was fireballed by %2$s using %3$s", "mob"),
    ("death.attack.generic", "died", "other"),
    ("death.attack.inFire", "went up in flames", "other"),
    ("death.attack.inFire.player", "walked into fire whilst fighting %2$s", "other"),
    ("death.attack.indirectMagic", "was killed by %2$s using magic", "mob"),
    ("death.attack.indirectMagic.item", "was killed by %2$s using %3$s", "mob"),
    ("death.attack.inWall", "suffocated in a wall", "other"),
    ("death.attack.lava", "tried to swim in lava", "lava"),
    ("death.attack.lava.player", "tried to swim in lava to escape %2$s", "lava"),
    ("death.attack.magic", "was killed by magic", "other"),
    ("death.attack.mob", "was slain by %2$s", "mob"),
    ("death.attack.onFire", "burned to death", "other"),
    ("death.attack.onFire.player", "was burnt to a crisp whilst fighting %2$s", "other"),
    ("death.attack.outOfWorld", "fell out of the world", "other"),
    ("death.attack.player", "was slain by %2$s", "mob"),
    ("death.attack.player.item", "was slain by %2$s using %3$s", "mob"),
    ("death.attack.starve", "starved to death", "other"),
    ("death.attack.thorns", "was killed trying to hurt %2$s", "mob"),
    ("death.attack.thrown", "was pummeled by %2$s", "mob"),
    ("death.attack.thrown.item", "was pummeled by %2$s using %3$s", "mob"),
    ("death.attack.wither", "withered away", "other"),
]

def _compile(key, body, cause):
    """Turn a template body into an anchored regex over the text after the victim's name."""
    parts = re.split(r"(%2\$s|%3\$s)", body)
    out = []
    for p in parts:
        if p == "%2$s":
            out.append(r"(?P<killer>.+?)")
        elif p == "%3$s":
            out.append(r"(?P<item>.+?)")
        else:
            out.append(re.escape(p))
    return key, cause, re.compile(r"^(?P<player>" + NAME + r") " + "".join(out) + r"$")


# More specific templates first, so "was slain by X using Y" is not read as killer "X using Y".
COMPILED = [_compile(*t) for t in sorted(TEMPLATES, key=lambda t: -len(t[1]))]


def parse_message(text):
    """Return (player, killer, cause, key) for a death line, or None."""
    for key, cause, rx in COMPILED:
        m = rx.match(text)
        if m:
            killer = m.groupdict().get("killer")
            return m.group("player"), killer, cause, key
    return None


def classify(parsed, known):
    player, killer, cause, key = parsed
    if killer and killer in known:
        return "player"
    return cause


def open_log(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def file_date(path, override):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", os.path.basename(path))
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if override:
        return override
    return dt.date.fromtimestamp(os.path.getmtime(path))


def scan(paths, override_date, known):
    """Yield one dict per death found, in file order."""
    for path in paths:
        day = file_date(path, override_date)
        last = None
        with open_log(path) as fh:
            for raw in fh:
                line = raw.rstrip("\r\n")
                m = LINE.match(line)
                if not m:
                    continue
                clock, text = m.group(1), m.group(2)
                j = JOIN.match(text)
                if j:
                    known.add(j.group(1))
                    continue
                hh, mm, ss = (int(x) for x in clock.split(":"))
                if last is not None and (hh, mm, ss) < last:
                    day = day + dt.timedelta(days=1)
                last = (hh, mm, ss)
                parsed = parse_message(text)
                if not parsed:
                    continue
                naive = dt.datetime(day.year, day.month, day.day, hh, mm, ss)
                utc = naive.astimezone().astimezone(dt.timezone.utc)
                yield {
                    "time_obj": utc,
                    "player": parsed[0],
                    "killer": parsed[1],
                    "cause": None,
                    "message": text,
                    "_parsed": parsed,
                    "source": os.path.basename(path),
                }


def load_usercache(path):
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {e["name"]: e["uuid"] for e in data if isinstance(e, dict) and "name" in e}


def grave_id(time_iso, player, message):
    return hashlib.sha1(f"{time_iso}|{player}|{message}".encode("utf-8")).hexdigest()[:12]


def load_existing(path):
    if not path or not os.path.exists(path):
        return {"updated": None, "graves": []}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("graves", [])
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="server log files: latest.log and/or rotated *.log.gz")
    ap.add_argument("--out", help="graves JSON to read and update (written in place)")
    ap.add_argument("--usercache", help="usercache.json, to map names to uuids")
    ap.add_argument("--date", help="YYYY-MM-DD for log files whose name carries no date")
    ap.add_argument("--demo", action="store_true", help="print the parsed lines and write nothing")
    args = ap.parse_args(argv)

    override = dt.date.fromisoformat(args.date) if args.date else None
    cache = load_usercache(args.usercache)
    known = set(cache)
    found = list(scan(args.logs, override, known))
    # The first pass learns joins from the same logs, so classify on the second.
    for d in found:
        d["cause"] = classify(d["_parsed"], known)

    if args.demo:
        for d in found:
            print(f"{d['time_obj'].strftime('%Y-%m-%dT%H:%M:%SZ')}  {d['cause']:<9} {d['source']}  {d['message']}")
        print(f"{len(found)} death lines", file=sys.stderr)
        return 0

    if not args.out:
        ap.error("--out is required unless --demo is given")

    data = load_existing(args.out)
    seen = set()
    for g in data["graves"]:
        seen.add((g.get("time"), g.get("player"), g.get("message")))
    added = 0
    for d in found:
        iso = d["time_obj"].strftime("%Y-%m-%dT%H:%M:%SZ")
        key = (iso, d["player"], d["message"])
        if key in seen:
            continue
        seen.add(key)
        data["graves"].append({
            "id": grave_id(iso, d["player"], d["message"]),
            "player": d["player"],
            "uuid": cache.get(d["player"]),
            "time": iso,
            "message": d["message"],
            "killer": d["killer"],
            "cause": d["cause"],
            "dimension": None,
            "pos": None,
            "model": 0,
        })
        added += 1

    data["graves"].sort(key=lambda g: g["time"])
    data["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, args.out)
    print(f"{len(found)} death lines read, {added} new, {len(data['graves'])} graves in {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
