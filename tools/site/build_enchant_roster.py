"""Rebuild the enchantment roster inlined in site/enchantments/index.html.

    python3 -I tools/site/build_enchant_roster.py

Reads the item index's data (site/items/data/items.json and descriptions.json),
takes every qf-content enchantment book the game hands out, and rewrites the one
line in the page that starts `const ENCH = ` so the roster describes exactly the
books that ship. Run it after tools/items/build_site.py has refreshed the data.

Each entry: the enchantment's config key, display name (level stripped), highest
level, rarity, what it applies to, the description under `enchant:<key>` in
descriptions.json, and the book's item key, which the card links to in the index.

Refuses to write when a book has no description or the count is not what the mod
registers (81), because a silent gap in the roster is worse than a failed build.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, 'site', 'items', 'data')
PAGE = os.path.join(REPO, 'site', 'enchantments', 'index.html')
EXPECTED = 81
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'X': 10}


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def roster():
    items = load('items.json')['items']
    desc = load('descriptions.json')
    out, missing = [], []
    for it in items:
        if not (it['k'].startswith('qfcontent:enchant_book@') and it.get('en')):
            continue
        shown = re.sub(r'^§.', '', it['nc'])
        m = re.match(r'^(.*?)(?:\s+(I|II|III|IV|V|X))?$', shown)
        name, level = m.group(1), ROMAN[m.group(2)] if m.group(2) else 1
        tooltip = it['tt']
        rarity = re.sub(r'^§.', '', tooltip[0])
        applies = tooltip[1].replace('§7Applies to: ', '')
        d = desc.get('enchant:' + it['en'])
        d = d if isinstance(d, str) else (d or {}).get('d')
        if not d:
            missing.append(it['en'])
        out.append({'key': it['en'], 'name': name, 'max': level, 'rarity': rarity,
                    'applies': applies, 'desc': d, 'k': it['k']})
    if missing:
        sys.exit('no description for: ' + ', '.join(missing))
    if len(out) != EXPECTED:
        sys.exit('found %d enchantment books, expected %d' % (len(out), EXPECTED))
    return out


def main():
    data = json.dumps(roster(), ensure_ascii=False, separators=(',', ':'))
    with open(PAGE, encoding='utf-8', newline='') as f:
        page = f.read()
    new, n = re.subn(r'^const ENCH = .*;$', lambda _: 'const ENCH = ' + data + ';', page, flags=re.M)
    if n != 1:
        sys.exit('expected exactly one "const ENCH = ...;" line in %s, found %d' % (PAGE, n))
    if new == page:
        print('roster unchanged (%d enchantments)' % EXPECTED)
        return
    with open(PAGE, 'w', encoding='utf-8', newline='') as f:
        f.write(new)
    print('wrote %d enchantments into %s' % (EXPECTED, os.path.relpath(PAGE, REPO)))


if __name__ == '__main__':
    main()
