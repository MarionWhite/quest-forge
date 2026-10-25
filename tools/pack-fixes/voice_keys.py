#!/usr/bin/env python3
"""Move the voice chat keys off B and N in an existing options.txt.

    py -3.10 -I tools/pack-fixes/voice_keys.py                 the live instance (%APPDATA%\\.crazycraft4)
    py -3.10 -I tools/pack-fixes/voice_keys.py --options PATH  any options.txt (a trial, a friend's, the Mac)
    py -3.10 -I tools/pack-fixes/voice_keys.py --check         report only, change nothing

qf-content's defaults became Tab (push to talk) and U (mute) on 2026-10-25, because B
opened the Adventure Backpack and aimed a Transformer, and N switched the backpack's hose
(see VoiceKeys.java). A default only applies to a key that options.txt has never
recorded, and Minecraft records every registered key on its first save, so every
existing install, and the client release (tools/release/build_client_release.py copies
the live options.txt), keeps B and N until these two lines change:

    key_key.qfcontent.voice_ptt:48   ->  key_key.qfcontent.voice_ptt:15
    key_key.qfcontent.voice_mute:49  ->  key_key.qfcontent.voice_mute:22

Only a line still on the old default is rewritten; a key the player chose is left
alone, and a line that is missing is added so the next launch does not fall back to
the jar's default on a jar that may be older. A backup is written beside the file.
Run it on the live instance before the next client release.
"""
import argparse
import os
import shutil
import sys

# LWJGL key codes, as options.txt stores them.
OLD = {"key_key.qfcontent.voice_ptt": 48, "key_key.qfcontent.voice_mute": 49}   # B, N
NEW = {"key_key.qfcontent.voice_ptt": 15, "key_key.qfcontent.voice_mute": 22}   # Tab, U
NAMES = {15: "Tab", 22: "U", 48: "B", 49: "N"}


def default_options():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
    return os.path.join(appdata, ".crazycraft4", "options.txt")


def plan(lines):
    """(new lines, [(key, old code or None, new code or None, action)])."""
    out, seen, changes = [], set(), []
    for line in lines:
        body = line.rstrip("\r\n")
        key, sep, val = body.partition(":")
        if sep and key in NEW:
            seen.add(key)
            try:
                code = int(val.strip())
            except ValueError:
                code = None
            if code == OLD[key]:
                out.append("%s:%d%s" % (key, NEW[key], line[len(body):]))
                changes.append((key, code, NEW[key], "moved"))
            else:
                out.append(line)
                changes.append((key, code, code, "kept: the player chose it" if code != NEW[key] else "already moved"))
        else:
            out.append(line)
    nl = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    for key in NEW:
        if key not in seen:
            if out and not out[-1].endswith(("\n", "\r\n")):
                out[-1] += nl
            out.append("%s:%d%s" % (key, NEW[key], nl))
            changes.append((key, None, NEW[key], "added"))
    return out, changes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--options", default=default_options(), help="options.txt to fix (default: the live instance's)")
    ap.add_argument("--check", action="store_true", help="report what would change; write nothing")
    a = ap.parse_args()

    if not os.path.isfile(a.options):
        sys.exit("no such file: %s" % a.options)
    with open(a.options, encoding="utf-8", newline="") as f:
        lines = f.readlines()
    out, changes = plan(lines)
    for key, old, new, action in changes:
        short = key[len("key_key.qfcontent."):]
        print("%-12s %-4s -> %-4s %s" % (short, NAMES.get(old, old if old is not None else "-"),
                                       NAMES.get(new, new), action))
    if out == lines:
        print("nothing to change in %s" % a.options)
        return
    if a.check:
        print("(--check: nothing written)")
        return
    backup = a.options + ".bak-voicekeys"
    shutil.copy2(a.options, backup)
    with open(a.options, "w", encoding="utf-8", newline="") as f:
        f.writelines(out)
    print("wrote %s (backup: %s)" % (a.options, backup))


if __name__ == "__main__":
    main()
