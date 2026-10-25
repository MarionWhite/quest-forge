#!/usr/bin/env python3
"""Describe the pack as the site shows it: its config fingerprint, packDate and commit.

    py -3.10 -I tools/site/pack_json.py                   print the JSON
    py -3.10 -I tools/site/pack_json.py --out F.json      write it to F.json

    {"fingerprint":"3f7f089e6508","packDate":"2026-10-17","version":"pack 2026-10-17 - 3f7f089e6508",
     "commit":"5e3bae0","generated":"2026-10-25"}

The fingerprint and packDate come from tools/pack_fingerprint.py over pack/config, the same
values the game's /qfpack shows. The deploy writes this to _site/play/pack.json so the play
page can say which pack it describes. commit is $GITHUB_SHA (short) when set, else
`git rev-parse --short HEAD`, else "unknown".
"""
import argparse, datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import pack_fingerprint as pf  # noqa: E402


def commit():
    sha = os.environ.get('GITHUB_SHA', '').strip()
    if sha:
        return sha[:7]
    try:
        out = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'],
                             capture_output=True, text=True, check=True).stdout.strip()
        return out or 'unknown'
    except (OSError, subprocess.CalledProcessError):
        return 'unknown'


def describe(config=pf.DEFAULT_CONFIG):
    files, _ = pf.read_list()
    fp, _ = pf.fingerprint(config, files)
    date = pf.pack_date(config) or '?'
    return {
        'fingerprint': fp,
        'packDate': date if date != '?' else None,
        'version': 'pack %s - %s' % (date, fp),
        'commit': commit(),
        'generated': datetime.date.today().isoformat(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default=pf.DEFAULT_CONFIG, help='config folder (default: pack/config)')
    ap.add_argument('--out', metavar='PATH', help='write the JSON to PATH instead of printing it')
    a = ap.parse_args()
    text = json.dumps(describe(a.config), separators=(',', ':'))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    else:
        print(text)


if __name__ == '__main__':
    main()
