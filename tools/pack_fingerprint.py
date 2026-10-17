"""The Quest Forge pack fingerprint, computed from a config folder.

The same algorithm as qf-content's PackFingerprint.java: a client and a server
compare it at login, and a client whose ID-bearing configs differ from the server's
is refused with a message saying which side is out of date. This script lets you
read the fingerprint of a folder without booting the game -- pack/config before a
release, a friend's config folder, or the play server's.

    py -3.10 -I tools/pack_fingerprint.py                      pack/config's fingerprint
    py -3.10 -I tools/pack_fingerprint.py --config C:\\qfs\\friends\\config
    py -3.10 -I tools/pack_fingerprint.py --files               ...and each file's digest
    py -3.10 -I tools/pack_fingerprint.py --show witchery.cfg   the entries that count
    py -3.10 -I tools/pack_fingerprint.py --diff OTHER_CONFIG   which files differ
    py -3.10 -I tools/pack_fingerprint.py --scan                configs with ID entries
                                                               missing from the list
    py -3.10 -I tools/pack_fingerprint.py --stamp               set packDate to today

The file list lives in mods/qf-content/src/main/resources/qfcontent-packcheck.txt,
which ships inside the qf-content jar so both sides use the same one.

KEEP IN STEP WITH PackFingerprint.java. If the two disagree, every client is refused.
The game's `/qfpack` prints the fingerprint it computed; it must equal this script's
output on the same folder.
"""
import argparse
import datetime
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LIST = os.path.join(REPO, "mods", "qf-content", "src", "main", "resources", "qfcontent-packcheck.txt")
DEFAULT_CONFIG = os.path.join(REPO, "pack", "config")

VERSION_TAG = "qfpack-1"

# re.ASCII everywhere: Java's \s, \d and (?i) are ASCII-only, Python's are not.
A = re.ASCII
ENTRY = re.compile(r'^(?:[A-Za-z]:)?(?:"([^"]*)"|([^=]+?))\s*=(.*)$', A)
COLON = re.compile(r'^([^:=]+):([A-Za-z]):(.*)$', A)
INT = re.compile(r'^-?\d+$', A)
ID_TOKEN = re.compile(r'(?<![A-Za-z])[Ii][Dd][Ss]?(?![a-z])|(?<=[a-z0-9])(?:ID|Id)[Ss]?(?![a-z])', A)
KIND = re.compile(r'potion|biome|enchant|dimension|villager|profession|provider', A | re.I)
CTRL = "".join(chr(i) for i in range(33))  # Java's String.trim(): every char <= ' '


def trim(s):
    return s.strip(CTRL)


def read_list(path=LIST):
    files, reviewed = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = trim(line)
            if not t or t.startswith("#"):
                continue
            if t.startswith("-"):
                # "-path   reason": the path ends at the first run of 2+ spaces or a tab
                reviewed.append(re.split(r"\t| {2,}", t[1:])[0])
            else:
                files.append(t)
    return files, reviewed


def entries(raw):
    """The ID-bearing entries of one config file, canonical and sorted."""
    text = raw.decode("latin-1")         # 1 byte = 1 char: no decoder can disagree
    if text.startswith("\u00ef\u00bb\u00bf"):
        text = text[3:]                  # a UTF-8 BOM, as Latin-1
    out, stack, in_list = [], [], False
    for line in re.split(r"\r\n|\r|\n", text):
        t = trim(line)
        if in_list:
            if t.endswith(">"):
                in_list = False
            continue
        if not t or t.startswith("#") or t.startswith("//"):
            continue
        if t.endswith("<"):
            in_list = True               # S:list < ... >: lists never hold IDs here
            continue
        if t == "}":
            if stack:
                stack.pop()
            continue
        if t.endswith("{") and "=" not in t:
            name = trim(t[:-1])
            if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
                name = name[1:-1]
            stack.append(name)
            continue
        m = ENTRY.match(t)
        if m:
            key = m.group(1) if m.group(1) is not None else m.group(2)
            value = m.group(3)
        else:
            m = COLON.match(t)
            if not m:
                continue
            key, value = m.group(1), m.group(3)
        key, value = trim(key), trim(value)
        if not INT.match(value):
            continue
        path = "/".join(stack)
        if "client" in path.lower():
            continue
        if ID_TOKEN.search(key) or KIND.search(key) or KIND.search(path):
            out.append(path + "|" + key + "=" + value)
    out.sort()
    return out


def file_digest(config, rel):
    p = os.path.join(config, *rel.split("/"))
    if not os.path.isfile(p):
        return "missing"
    with open(p, "rb") as f:
        canon = "".join(e + "\n" for e in entries(f.read()))
    return hashlib.sha256(canon.encode("latin-1")).hexdigest()[:16]


def fingerprint(config, files):
    digests = [(rel, file_digest(config, rel)) for rel in files]
    body = VERSION_TAG + "\n" + "".join(f"{rel}\t{d}\n" for rel, d in digests)
    return hashlib.sha256(body.encode("latin-1")).hexdigest()[:12], digests


def pack_date(config):
    p = os.path.join(config, "qfcontent.cfg")
    try:
        with open(p, encoding="latin-1") as f:
            m = re.search(r'^\s*S:packDate=(.*)$', f.read(), re.M)
            return trim(m.group(1)) if m else ""
    except OSError:
        return ""


def scan(config, files, reviewed):
    known = set(files) | set(reviewed)
    new = []
    for dp, dn, fn in os.walk(config):
        dn.sort()
        for f in sorted(fn):
            if not re.search(r"\.(cfg|ini|prop|properties)$", f):
                continue
            rel = os.path.relpath(os.path.join(dp, f), config).replace(os.sep, "/")
            with open(os.path.join(dp, f), "rb") as fh:
                e = entries(fh.read())
            if e and rel not in known:
                new.append((rel, e))
    return new


def stamp(config):
    p = os.path.join(config, "qfcontent.cfg")
    today = datetime.date.today().isoformat()
    with open(p, "rb") as f:
        s = f.read().decode("latin-1")
    s2, n = re.subn(r'(?m)^(\s*S:packDate=).*?(\r?)$', lambda m: m.group(1) + today + m.group(2), s)
    if not n:
        sys.exit(f"{p} has no S:packDate line; add the packcheck section first")
    with open(p, "wb") as f:
        f.write(s2.encode("latin-1"))
    print(f"packDate = {today} in {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="config folder (default: pack/config)")
    ap.add_argument("--files", action="store_true", help="print each file's digest")
    ap.add_argument("--show", metavar="FILE", help="print the entries that count for FILE")
    ap.add_argument("--diff", metavar="OTHER", help="another config folder to compare with")
    ap.add_argument("--scan", action="store_true", help="list configs with ID entries not in the list")
    ap.add_argument("--stamp", action="store_true", help="set packcheck.packDate to today")
    a = ap.parse_args()
    files, reviewed = read_list()

    if a.stamp:
        return stamp(a.config)
    if a.show:
        p = os.path.join(a.config, *a.show.split("/"))
        with open(p, "rb") as f:
            for e in entries(f.read()):
                print(e)
        return
    if a.scan:
        new = scan(a.config, files, reviewed)
        for rel, e in new:
            print(f"{len(e):4d}  {rel}   e.g. {e[0]}")
        print(f"{len(new)} config(s) with ID entries are neither fingerprinted nor reviewed"
              if new else "every config with ID entries is fingerprinted or reviewed")
        sys.exit(1 if new else 0)

    fp, digests = fingerprint(a.config, files)
    print(f"{fp}  pack {pack_date(a.config) or '?'}  ({a.config})")
    if a.files:
        for rel, d in digests:
            print(f"  {d:16}  {rel}")
    if a.diff:
        fp2, d2 = fingerprint(a.diff, files)
        print(f"{fp2}  pack {pack_date(a.diff) or '?'}  ({a.diff})")
        diff = [rel for (rel, x), (_, y) in zip(digests, d2) if x != y]
        print("differ: " + (", ".join(diff) if diff else "nothing"))


if __name__ == "__main__":
    main()
