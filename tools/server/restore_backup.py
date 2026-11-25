#!/usr/bin/env python3
"""Restore a supervisor backup into a stopped play server.

    restore_backup.py --server C:\\qfs\\friends --backup C:\\qfs\\friends\\backups\\daily\\world-20261025-050000.zip
    restore_backup.py --server DIR --backup ZIP --check-only        # compare, change nothing
    restore_backup.py --server DIR --backup ZIP --with-player-lists  # also ops, whitelist, bans

What it does, in order (docs/setup/hosting-a-server.md, "Restoring a backup"):

1. Refuses while the server is up (the same checks as the builder's --force).
2. Reads MANIFEST.sha256 out of the zip and compares it with the server's jars
   and configs as they are now. The world is only valid with the jar set it was
   saved under (Transformers assigns material IDs at first load; a missing mod
   deletes its items), so a jar difference is refused unless --accept-jar-changes.
   Config differences are listed and allowed: the server rewrites several configs
   at boot, and none of them is an ID entry.
3. Moves the current world/ to world.before-restore-<time>/ (nothing is deleted).
4. Extracts world/ from the zip. --with-player-lists also restores ops.json,
   whitelist.json and the ban lists from the zip; server.properties is never
   restored (it is the live record of port, online mode and so on).

Then start the server with start-supervised.bat. The drill of 2026-10-25
(scratch server, hosting guide) is what this script replaces: unzipping a backup
over the server folder also overwrote server.properties and MANIFEST.sha256,
and nothing checked the jar set.
"""
import argparse, hashlib, os, shutil, sys, time, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_play_server import read_properties, refuse_if_running  # noqa: E402

PLAYER_LISTS = ["ops.json", "whitelist.json", "banned-players.json", "banned-ips.json"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(text):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if line and " " in line:
            digest, name = line.split(" ", 1)
            out[name.lstrip("*").strip()] = digest
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", required=True, help="the server folder (holds world/, mods/, MANIFEST.sha256)")
    ap.add_argument("--backup", required=True, help="a backups/*/world-<time>.zip from the supervisor")
    ap.add_argument("--check-only", action="store_true", help="compare the manifest and stop")
    ap.add_argument("--with-player-lists", action="store_true",
                    help="also restore ops.json, whitelist.json and the ban lists from the zip")
    ap.add_argument("--accept-jar-changes", action="store_true",
                    help="restore even though the jar set differs from the backup's manifest")
    args = ap.parse_args()
    server = os.path.abspath(args.server)
    backup = os.path.abspath(args.backup)
    if not os.path.isfile(backup):
        sys.exit("%s is not a file" % backup)
    if not os.path.isdir(os.path.join(server, "mods")):
        sys.exit("%s has no mods/; is it a server folder?" % server)
    level = read_properties(os.path.join(server, "server.properties")).get("level-name") or "world"

    try:
        refuse_if_running(server)
    except SystemExit as e:
        sys.exit(str(e).replace("refusing to rebuild", "refusing to restore into"))

    with zipfile.ZipFile(backup) as z:
        names = z.namelist()
        world_entries = [n for n in names if n.startswith(level + "/")]
        if not world_entries:
            sys.exit("%s holds no %s/ (entries start with: %s)" % (
                backup, level, ", ".join(sorted({n.split('/')[0] for n in names})[:8])))
        if "MANIFEST.sha256" not in names:
            print("WARNING: the backup carries no MANIFEST.sha256; the jar set cannot be checked")
            saved = None
        else:
            saved = parse_manifest(z.read("MANIFEST.sha256").decode("utf-8"))
        if "%s/level.dat" % level not in names:
            sys.exit("%s/level.dat is not in the zip; this is not a whole world" % level)

        # --- the jar set the world needs vs. what the server runs now ---------
        if saved:
            current = {}
            tops = [f for f in os.listdir(server) if f.endswith(".jar")] + ["mods", "config"]
            for top in tops:
                p = os.path.join(server, top)
                files = [p] if os.path.isfile(p) else [
                    os.path.join(r, f) for r, _, fs in os.walk(p) for f in fs]
                for f in files:
                    current[os.path.relpath(f, server).replace(os.sep, "/")] = sha256_file(f)
            is_jar = lambda n: n.endswith(".jar") and not n.startswith("config/")
            jar_diff = sorted(n for n in set(saved) | set(current)
                              if is_jar(n) and saved.get(n) != current.get(n))
            cfg_diff = sorted(n for n in set(saved) | set(current)
                              if not is_jar(n) and saved.get(n) != current.get(n))
            print("manifest: %d files in the backup, %d on the server now" % (len(saved), len(current)))
            for n in jar_diff:
                state = "missing now" if n not in current else "not in the backup" if n not in saved else "changed"
                print("  JAR %-14s %s" % (state + ":", n))
            for n in cfg_diff:
                state = "missing now" if n not in current else "not in the backup" if n not in saved else "changed"
                print("  cfg %-14s %s" % (state + ":", n))
            if jar_diff and not args.accept_jar_changes:
                sys.exit("%d jar(s) differ from the set this world was saved under. Rebuild the server "
                         "to that set first (BUILT-FROM.txt in the zip says how it was built), or pass "
                         "--accept-jar-changes if the change is known to be safe (a server-only addition "
                         "such as Opis, Morpheus or WorldBorder is)." % len(jar_diff))
            if not jar_diff and not cfg_diff:
                print("manifest: the server's jars and configs are exactly the backup's")
            elif not jar_diff:
                print("manifest: jars match; %d config file(s) differ (listed above, allowed)" % len(cfg_diff))
        if args.check_only:
            print("check only: nothing changed")
            return

        # --- swap the world --------------------------------------------------------
        world = os.path.join(server, level)
        if os.path.isdir(world):
            aside = world + ".before-restore-" + time.strftime("%Y%m%d-%H%M%S")
            os.rename(world, aside)
            print("moved the current %s/ to %s" % (level, aside))
        extracted = 0
        for n in world_entries:
            if n.endswith("/"):
                continue
            z.extract(n, server)
            extracted += 1
        print("restored %s/ from %s (%d files)" % (level, os.path.basename(backup), extracted))
        if args.with_player_lists:
            for n in PLAYER_LISTS:
                if n in names:
                    z.extract(n, server)
                    print("restored %s" % n)
        if "session.lock" in {os.path.basename(n) for n in world_entries}:
            try:
                os.remove(os.path.join(world, "session.lock"))
            except OSError:
                pass
    print("\nDone. Start the server with start-supervised.bat. The world it replaced is still "
          "next to it; delete it once the restored one has booted and someone has logged in.")


if __name__ == "__main__":
    main()
