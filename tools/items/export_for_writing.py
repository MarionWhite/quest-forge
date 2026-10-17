"""One research sheet per mod, for writing the item index's descriptions.

    py -3.10 -I tools/items/export_for_writing.py --out <dir> [--mod OreSpawn ...]

Reads the built site data (site/items/data/) and writes <dir>/<mod id>.tsv: one row per
registry id, variants folded together, with everything the dump knows that hints at what
the item is: names, kind, tab, ore names, tooltip, what it's made from, what it goes into,
and how quests use it. A writer (or an agent) researches from this plus the mod's own jar
and wiki, and returns {key: {"d": text, "src": ...}} for merge_descriptions.py.
"""
import argparse, collections, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, 'site', 'items', 'data')
COLOR = re.compile('§.')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mod', action='append', default=[], help='mod id(s); default all')
    a = ap.parse_args()
    d = json.load(open(os.path.join(DATA, 'items.json'), encoding='utf-8'))
    r = json.load(open(os.path.join(DATA, 'recipes.json'), encoding='utf-8'))
    items, mods, kinds = d['items'], d['mods'], d['kinds']
    base = lambda k: k.split('#')[0]
    id_of = lambda k: base(k)[:base(k).rfind('@')]
    first_name = {}
    for it in items:
        first_name.setdefault(base(it['k']), it['n'])
        first_name.setdefault(id_of(it['k']), it['n'])
    def name(ref):
        if ref is None: return None
        if isinstance(ref, list): return name(ref[0]) if ref else None
        if ref.startswith('ore:'): return 'any ' + ref[4:]
        return first_name.get(ref) or first_name.get(ref.rsplit('@', 1)[0]) or ref
    made_from, goes_into = collections.defaultdict(set), collections.defaultdict(set)
    for rec in r['crafting'] + r['smelting']:
        out = rec.get('out')
        if not out: continue
        oid = out.rsplit('@', 1)[0]
        for x in rec.get('in', []):
            n = name(x)
            if n: made_from[oid].add(('smelt:' if rec['type'] == 'smelting' else '') + n)
            for ref in (x if isinstance(x, list) else [x]):
                if ref and not ref.startswith('ore:'):
                    # Name the exact output: spawn eggs and the like share one id across metas.
                    goes_into[ref.rsplit('@', 1)[0]].add(first_name.get(out) or first_name.get(oid, oid))
        if rec['type'] == 'special':
            made_from[oid].add('special recipe ' + rec.get('class', '').split('.')[-1])
    groups = collections.OrderedDict()
    for i, it in enumerate(items):
        if it.get('u'): continue
        groups.setdefault(id_of(it['k']), []).append(i)
    os.makedirs(a.out, exist_ok=True)
    per_mod = collections.defaultdict(list)
    for iid, idxs in groups.items():
        it0 = items[idxs[0]]
        m = mods[it0['m']]
        if a.mod and m['id'] not in a.mod: continue
        names = list(dict.fromkeys(items[i]['n'] for i in idxs))
        tips = list(dict.fromkeys(COLOR.sub('', t) for i in idxs for t in items[i].get('tt', [])))
        ores = sorted({o for i in idxs for o in items[i].get('o', [])})
        quests = sorted({'%s:%s' % (role, d['quests'].get(str(q), [q])[0])
                         for i in idxs for q, role in d['qrefs'].get(str(i), [])})
        stats = []
        if 'a' in it0: stats.append('attack +%s' % it0['a'])
        if 'ar' in it0: stats.append('armour %s %s' % (it0['ar'], it0.get('sl', '')))
        if 'd' in it0: stats.append('durability %s' % it0['d'])
        if 'f' in it0: stats.append('food %s' % it0['f'])
        row = [iid, str(len(idxs)), ' | '.join(names[:12]) + (' | ...' if len(names) > 12 else ''),
               kinds[it0['c']], d['tabs'][it0['t']] if 't' in it0 else '', ', '.join(stats),
               ', '.join(ores[:8]), ' / '.join(tips[:4]),
               ', '.join(sorted(made_from.get(iid, []))[:8]),
               ', '.join(sorted(goes_into.get(iid, []))[:8]), '; '.join(quests[:4]),
               it0.get('ul', '')]
        per_mod[m['id']].append([c.replace('\t', ' ').replace('\n', ' ') for c in row])
    head = ['id', 'variants', 'names', 'kind', 'tab', 'stats', 'ore_names', 'tooltip',
            'made_from', 'goes_into', 'quests', 'unlocalized']
    for mid, rows in per_mod.items():
        with open(os.path.join(a.out, re.sub(r'[^A-Za-z0-9_.-]', '_', mid) + '.tsv'), 'w', encoding='utf-8') as f:
            f.write('\t'.join(head) + '\n')
            for row in rows:
                f.write('\t'.join(row) + '\n')
    print('%d mods, %d ids -> %s' % (len(per_mod), sum(map(len, per_mod.values())), a.out))


if __name__ == '__main__':
    main()
