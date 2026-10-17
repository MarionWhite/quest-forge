"""Merge researched item descriptions into tools/items/descriptions.json.

    py -3.10 -I tools/items/merge_descriptions.py <dir of {mod}.json files>

Each input file is {key: {"d": text, "get": how to obtain, "src": "wiki" | "jar" | "wiki+jar" | "inferred"}},
written from export_for_writing.py's sheets. Keys are "modid:name" (every variant) or
"modid:name@meta" (one variant).

descriptions.json keeps only the text, so it stays easy to edit by hand: a plain string is a
description, and {"d": ..., "get": ...} adds a "how to get it" line.
descriptions-sources.json records where each researched entry came from. An entry in
descriptions.json that has no source record was written by hand, and a merge never
overwrites it. Run tools/items/build_site.py afterwards to publish.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESC = os.path.join(HERE, 'descriptions.json')
SRCS = os.path.join(HERE, 'descriptions-sources.json')


def load(p, default):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    desc, srcs = load(DESC, {}), load(SRCS, {})
    hand = {k for k in desc if not k.startswith('_') and k not in srcs}
    added = kept = 0
    for f in sorted(os.listdir(sys.argv[1])):
        if not f.endswith('.json'):
            continue
        for k, v in json.load(open(os.path.join(sys.argv[1], f), encoding='utf-8')).items():
            text = (v.get('d') if isinstance(v, dict) else v or '').strip()
            get = (v.get('get') or '').strip() if isinstance(v, dict) else ''
            if not text and not get:
                continue
            if k in hand:
                kept += 1
                continue
            desc[k] = {'d': text, 'get': get} if get else text
            srcs[k] = v.get('src', '') if isinstance(v, dict) else ''
            added += 1
    doc = {k: desc[k] for k in desc if k.startswith('_')}
    body = {k: desc[k] for k in sorted(desc, key=str.lower) if not k.startswith('_')}
    with open(DESC, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({**doc, **body}, f, ensure_ascii=False, indent=1)
        f.write('\n')
    with open(SRCS, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({k: srcs[k] for k in sorted(srcs, key=str.lower)}, f, ensure_ascii=False, indent=0)
        f.write('\n')
    inferred = sum(1 for v in srcs.values() if v == 'inferred')
    print('%d merged, %d hand-written kept; %d entries, %d inferred' % (added, kept, len(body), inferred))


if __name__ == '__main__':
    main()
