"""Build the item browser's data (site/items/data/) from an ItemDump.

    py -3.10 -I tools/items/build_site.py --dump <dir written by -Dqf.itemdump>

The dump comes from qf-content's debug ItemDump (see README.md here). This
script joins it with three things the game does not know:

- the mod catalog (tools/modlist/catalog.json): each mod's category and blurb,
  matched by jar file name, so the browser groups mods the way the mod list does;
- the quest book (pack/config/betterquesting/DefaultQuests.json, via
  tools/quests/qb.py): which quests ask for, hand out or show each item;
- the icon sheets, re-encoded smaller.

It writes items.json, recipes.json and icons-N.png into site/items/data/. The page
itself, site/items/index.html, is hand-written and reads only those files.
"""
import argparse, datetime, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'tools', 'quests'))
import qb  # noqa: E402

CATALOG = os.path.join(REPO, 'tools', 'modlist', 'catalog.json')
OUT = os.path.join(REPO, 'site', 'items', 'data')
COLOR = re.compile('§.')
KINDS = ['block', 'item', 'weapon', 'bow', 'tool', 'armor', 'food']

# ChestGenHooks' category keys, as a player would name the chest.
CHEST_NAMES = {
    'bonusChest': 'Spawn bonus chest', 'dungeonChest': 'Dungeon', 'mineshaftCorridor': 'Mineshaft',
    'pyramidDesertyChest': 'Desert temple', 'pyramidJungleChest': 'Jungle temple',
    'pyramidJungleDispenser': 'Jungle temple dispenser', 'strongholdCorridor': 'Stronghold corridor',
    'strongholdCrossing': 'Stronghold crossing', 'strongholdLibrary': 'Stronghold library',
    'villageBlacksmith': 'Village blacksmith', 'railcraft:workshop': 'Railcraft workshop',
}

# Forge, FML and vanilla register as mods but ship no jar of their own.
BUILTIN = {'minecraft': ('Minecraft', 'Vanilla'), 'FML': ('Forge Mod Loader', 'Vanilla'),
           'Forge': ('Minecraft Forge', 'Vanilla'), 'mcp': ('Minecraft Coder Pack', 'Vanilla')}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def untranslated(e):
    n = e.get('name') or ''
    return (not n or n == e.get('unloc') or n.endswith('.name') or n.startswith(('item.', 'tile.'))
            or n.startswith('null'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dump', required=True, help='directory ItemDump wrote')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    items = load(os.path.join(a.dump, 'items.json'))
    recipes = load(os.path.join(a.dump, 'recipes.json'))
    mods = load(os.path.join(a.dump, 'mods.json'))
    summary = load(os.path.join(a.dump, 'summary.json'))
    catalog = load(CATALOG)

    # Catalog files can carry a subfolder ("1.7.10/ForgeMultipart-...jar"); match on the name.
    by_file = {os.path.basename(m['file']).lower(): m for m in catalog['mods']}
    cats = [{'key': c[0], 'label': c[1].replace('&amp;', '&'), 'note': c[2]} for c in catalog['cats']]
    cats.insert(0, {'key': 'Vanilla', 'label': 'Minecraft & Forge', 'note': 'The base game.'})

    # -- mods: every mod id that owns at least one item -----------------------------
    counts = {}
    for e in items:
        counts[e['mod']] = counts.get(e['mod'], 0) + 1
    lower = {k.lower(): k for k in mods}
    mod_rows, mod_index = [], {}
    shared = {}
    for mid in counts:
        f = (mods.get(mid) or {}).get('file', '').lower()
        if f in by_file:
            shared[id(by_file[f])] = shared.get(id(by_file[f]), 0) + 1
    for mid in sorted(counts, key=lambda m: m.lower()):
        info = mods.get(mid) or mods.get(lower.get(mid.lower(), ''), {})
        jar = (info.get('file') or '').lower()
        cat_entry = by_file.get(jar)
        if cat_entry is None and jar.startswith('questforge'):
            # The pack's own jars share one entry's category (qf-commands is newer than the catalog).
            own = by_file.get('questforgecontent-1.0.0.jar', {})
            cat_entry = {'cat': own.get('cat', 'Other'), 'name': info.get('name'), 'desc': ''}
        if mid in BUILTIN:
            name, cat = BUILTIN[mid]
            desc = ''
        else:
            name = (cat_entry or {}).get('name') or info.get('name') or mid
            cat = (cat_entry or {}).get('cat') or 'Other'
            desc = (cat_entry or {}).get('desc', '')
        if shared.get(id(cat_entry), 0) > 1 and info.get('name'):
            name = info['name']  # Lycanites' sub-mods share one jar's entry; keep them apart
        mod_index[mid] = len(mod_rows)
        mod_rows.append({'id': mid, 'name': name, 'ver': info.get('version', ''),
                         'file': info.get('file', ''), 'cat': cat, 'desc': desc, 'count': counts[mid]})
    if any(m['cat'] == 'Other' for m in mod_rows):
        cats.append({'key': 'Other', 'label': 'Other', 'note': 'Mods the catalog does not list.'})

    # -- items -------------------------------------------------------------------
    tabs, tab_index = [], {}
    rows, key_index, by_id = [], {}, {}
    for e in items:
        t = e.get('tab')
        if t and t.startswith('itemGroup.'):
            # Vanilla tabs come back as their language key; I18n isn't applied to them here.
            t = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', t[len('itemGroup.'):]).replace('_', ' ').title()
        if t is not None and t not in tab_index:
            tab_index[t] = len(tabs)
            tabs.append(t)
        r = {'k': e['key'], 'n': COLOR.sub('', e.get('name') or ''), 'm': mod_index[e['mod']],
             'c': KINDS.index(e['kind']) if e['kind'] in KINDS else 1, 'i': e['icon']}
        if t is not None: r['t'] = tab_index[t]
        if e.get('name') and COLOR.search(e['name']): r['nc'] = e['name']
        if e.get('blank') or e.get('renderFailed'): r['b'] = 1
        if untranslated(e): r['u'] = 1
        for src, dst in (('attack', 'a'), ('armor', 'ar'), ('slot', 'sl'), ('durability', 'd'),
                         ('food', 'f'), ('ores', 'o'), ('tooltip', 'tt'), ('nbt', 'nbt'), ('unloc', 'ul')):
            if e.get(src) not in (None, '', []): r[dst] = e[src]
        if e.get('stack', 64) != 64: r['s'] = e['stack']
        if 'a' in r:
            r['a'] = round(r['a'] - 1, 2)  # the dump adds the player's base 1; show the tooltip's "+N"
        if e.get('rarity') not in (None, 'Common'): r['r'] = e['rarity']
        key_index[e['key']] = len(rows)
        by_id.setdefault(e['id'], []).append(len(rows))
        rows.append(r)

    # -- chest loot (ChestGenHooks), when the dump has it ------------------------------
    # The chance an item turns up in one chest: each of the chest's rolls picks an entry by
    # weight, so P = 1 - (1 - w/W)^rolls, with rolls the middle of the chest's range.
    loot_cats, loot_path = [], os.path.join(a.dump, 'loot.json')
    if os.path.exists(loot_path):
        for cat, info in sorted(load(loot_path).items()):
            total = sum(e[1] for e in info['items'])
            if not total:
                continue
            rolls = (info['rollsMin'] + info['rollsMax']) / 2
            label = CHEST_NAMES.get(cat) or re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', cat.split(':')[-1]).replace('_', ' ').strip().capitalize()
            ci = len(loot_cats)
            loot_cats.append(label)
            for ref, weight, lo, hi in info['items']:
                pct = 100 * (1 - (1 - weight / total) ** rolls)
                idxs = by_id.get(ref[:-2], []) if ref.endswith('@*') else (
                    [key_index[ref]] if ref in key_index else by_id.get(ref.rsplit('@', 1)[0], [])[:1])
                for idx in idxs:
                    rows[idx].setdefault('lt', []).append([ci, round(pct, 1 if pct < 10 else 0), lo, hi])

    # -- quests ------------------------------------------------------------------
    book = qb.load('pack')
    line_of = book.line_of()
    quests = {}
    for qid, q in book.quests.items():
        lines = [book.line_name(l) for l in line_of.get(qid, [])]
        quests[qid] = [qb.name(q), COLOR.sub('', lines[0]) if lines else '']
    qrefs, unresolved = {}, {}
    for where, kind, s in qb.refs(book):
        if not isinstance(where, int):
            continue
        key = '%s@%s' % (s['id:8'], s.get('Damage:2', 0))
        idx = key_index.get(key)
        if idx is None and by_id.get(s['id:8']):
            idx = by_id[s['id:8']][0]  # meta not in the creative list (e.g. a damaged tool)
        if idx is None:
            unresolved.setdefault(key, []).append(where)
            continue
        refs = qrefs.setdefault(idx, [])
        if [where, kind] not in refs:
            refs.append([where, kind])

    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        if f.startswith('icons-') and f.endswith('.png'):
            os.remove(os.path.join(a.out, f))
    sheets = summary['sheets']
    for n in range(sheets):
        src, dst = os.path.join(a.dump, 'icons-%d.png' % n), os.path.join(a.out, 'icons-%d.png' % n)
        shutil.copy(src, dst)
        try:
            # Java's encoder is fair; keep a re-encode only when it is actually smaller.
            from PIL import Image
            tmp = dst + '.tmp.png'
            Image.open(src).save(tmp, optimize=True)
            if os.path.getsize(tmp) < os.path.getsize(dst):
                os.replace(tmp, dst)
            else:
                os.remove(tmp)
        except ImportError:
            pass

    out = {
        'built': datetime.date.today().isoformat(),
        'cell': summary['cell'], 'side': summary['side'], 'sheets': sheets,
        'cats': cats, 'mods': mod_rows, 'tabs': tabs, 'kinds': KINDS, 'lootCats': loot_cats,
        'items': rows,
        'quests': quests, 'qrefs': {str(k): v for k, v in qrefs.items()},
        'unresolvedQuestRefs': unresolved,
    }
    with open(os.path.join(a.out, 'items.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    rec = {'crafting': recipes['crafting'], 'smelting': recipes['smelting'], 'ores': recipes['ores'],
           'unreadable': recipes.get('unreadable', 0)}
    with open(os.path.join(a.out, 'recipes.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, separators=(',', ':'))

    # Hand-written descriptions ride along as they are; the page reads them by item key or id.
    lore = load(os.path.join(HERE, 'descriptions.json')) if os.path.exists(os.path.join(HERE, 'descriptions.json')) else {}
    lore = {k: v for k, v in lore.items() if not k.startswith('_')}
    with open(os.path.join(a.out, 'descriptions.json'), 'w', encoding='utf-8') as f:
        json.dump(lore, f, ensure_ascii=False, indent=0)
    used = sum(1 for i in range(len(rows)) if i in qrefs)
    # A few numbers for the homepage's card, so it need not fetch the whole index.
    with open(os.path.join(a.out, 'stats.json'), 'w', encoding='utf-8') as f:
        json.dump({'built': out['built'], 'items': len(rows), 'mods': len(mod_rows), 'inQuest': used,
                   'recipes': len(rec['crafting']) + len(rec['smelting'])}, f)
    print('%d stacks from %d mods, %d tabs; %d in a quest, %d quest refs unresolved'
          % (len(rows), len(mod_rows), len(tabs), used, sum(len(v) for v in unresolved.values())))
    print('%d crafting + %d smelting recipes (%d unreadable); %d sheets; dump: %s'
          % (len(rec['crafting']), len(rec['smelting']), rec['unreadable'], sheets,
             {k: summary[k] for k in ('renderFailures', 'subItemFailures', 'metaFailures', 'blankIcons')}))
    other = [m['id'] for m in mod_rows if m['cat'] == 'Other']
    if other:
        print('not in tools/modlist/catalog.json (filed under Other):', ', '.join(other))


if __name__ == '__main__':
    main()
