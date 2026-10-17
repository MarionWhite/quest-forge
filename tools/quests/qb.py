#!/usr/bin/env python3
"""Quest toolkit for the BetterQuesting 3 book (DefaultQuests.json).

WHY THIS EXISTS. The old scripts in tools/pack-fixes/quests/ hard-code a macOS
PrismLauncher path and cannot be re-run. Every quest edit since then was checked
by hand, which is how the book shipped a quest that needs 64 unstackable swords,
three creative-only rewards and a chain of quests whose rewards complete the next
one. This file is the one place those checks live (docs/design/questline-audit.md,
WP-0).

TWO BOOKS. The repo carries two copies, and they are NOT the same book:
  pack    pack/config/betterquesting/DefaultQuests.json    the shipped book
  server  server/config/betterquesting/DefaultQuests.json  the survey server's
          older book: it still has the HBM quests and no ChocolateQuest ones,
          because that server runs HBM (see server/README.md)
Every edit goes into both. The pack copy is written with \\u escapes, the server
copy with raw UTF-8; save() keeps whichever style the file already had, and
load() refuses to work on a file it cannot write back byte for byte.

Usage (py -3.10 -I tools/quests/qb.py ...):
    check [--book pack|server|all]      lint + ids + cheese + stack + text (exit 1 on error)
    lint | ids | cheese | stack | text  one check at a time
    tally [--book ...]                  reward totals per quest line, ungated totals
    dump [--book ...] [--out FILE]      human-readable dump of the whole book
    show QID [QID ...]                  one quest, raw JSON
    diff                                semantic differences between pack and server
    registry --save LEVEL_DAT           rebuild registry.json from a world's FML ItemData

As a library (edit scripts in tools/quests/patches/ use this):
    import qb
    book = qb.load('pack')          # or a path
    q = book.quest(63)              # the raw quest dict, edit in place
    book.save()
"""
import argparse, collections, gzip, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BOOKS = {
    'pack': os.path.join(REPO, 'pack', 'config', 'betterquesting', 'DefaultQuests.json'),
    'server': os.path.join(REPO, 'server', 'config', 'betterquesting', 'DefaultQuests.json'),
}
# Namespaces a book may use that the pack registry does not have. The survey server
# runs HBM, so its book keeps the HBM chapter; the pack does not ship HBM.
EXTRA_NAMESPACES = {'pack': set(), 'server': {'hbm'}}
REGISTRY = os.path.join(HERE, 'registry.json')
LEVELUP_CFG = os.path.join(REPO, 'pack', 'config', 'levelup.cfg')

# ---------------------------------------------------------------------------
# Blocklist: items no quest may ask for or hand out. Each entry: (pattern, scope, why).
# scope is 'reward', 'task' or 'any'. Patterns are exact ids, or 'ns:*'.
BLOCKLIST = [
    ('TragicMC:swordOfJustice', 'any', "creative-tab debug weapon; its hit code reads isCreativeMode"),
    ('TragicMC:bowOfJustice', 'any', "creative-tab debug weapon, same family as the Sword of Justice"),
    ('witchery:infinityegg', 'any', "creative infinite altar power; no recipe, creative tab only"),
    ('betterquesting:placeholder', 'any', "BQ writes this when an item id failed to resolve"),
    ('minecraft:command_block', 'any', "admin block"),
    ('minecraft:bedrock', 'task', "not obtainable in survival"),
    ('minecraft:mob_spawner', 'task', "not obtainable as an item in survival (Chest Transporter keeps it as a transporter)"),
    ('minecraft:end_portal_frame', 'task', "not obtainable in survival"),
]


def levelup_blocklist():
    """levelup:* is blocked while config/levelup.cfg disables its items: a disabled
    item is not registered, and BQ silently turns it into a placeholder."""
    try:
        txt = open(LEVELUP_CFG, encoding='utf-8', errors='replace').read()
    except OSError:
        return []
    off = [k for k in ('Enable Talisman', 'Enable Unlearning Book')
           if re.search(r'B:"?%s"?=false' % re.escape(k), txt)]
    if off:
        return [('levelup:*', 'any', 'levelup.cfg disables ' + ', '.join(off))]
    return []


# Unstackable items: a retrieval task with Count > 1 on one of these needs that many
# inventory slots at once (consume=0), and a reward with Count > 1 is dubious.
UNSTACKABLE_IDS = {
    'OreSpawn:OreSpawn_Royal', 'OreSpawn:OreSpawn_Bertha', 'OreSpawn:OreSpawn_Slice',
    'OreSpawn:OreSpawn_QueenBattleAxe', 'OreSpawn:OreSpawn_BattleAxe', 'OreSpawn:OreSpawn_Chainsaw',
    'OreSpawn:OreSpawn_Nightmare', 'OreSpawn:OreSpawn_AttitudeAdjuster', 'legends:mjolnir',
    'TragicMC:doomsdayScroll',
}
UNSTACKABLE_RE = re.compile(
    r'(sword|pickaxe|_axe|axe$|shovel|spade|_hoe|hoe$|bow$|bow_|longbow|helm|helmet|chestplate|'
    r'plate$|leggings|legs$|boots|robe|hat$|amulet|talisman|_ring|(?-i:[a-z]Ring$)|scythe|hammer|blade$|dagger|'
    r'katana|mace|staff|wand|rifle|launcher|backpack|saddle|chestpiece|cowl|mask$|cape$)',
    re.I)
STACKABLE_HINT = re.compile(r'(ingot|nugget|scale|shard|block|dust|plate[A-Z_]?.*ingot|titaniumPlate|ironPlate|'
                            r'fabric|essence|gem$|ore$|bucket|_part|part\.)', re.I)


def unstackable(item_id):
    if item_id in UNSTACKABLE_IDS:
        return True
    tail = item_id.split(':', 1)[-1]
    if STACKABLE_HINT.search(tail):
        return False
    return bool(UNSTACKABLE_RE.search(tail))


# Quests that prove a boss kill (or a boss-tier craft). A quest is "ungated" when
# neither it nor any of its ancestors is one of these. Used by `tally`.
BOSS_QUESTS = {
    15: 'Naga', 16: 'Lich', 17: 'Hydra', 93: 'Minoshroom', 94: 'Knight Phantom', 18: 'Ur-Ghast',
    95: 'Alpha Yeti', 19: 'Snow Queen', 22: 'Mobzilla', 23: 'The King', 24: 'The Queen',
    406: 'Rahovart',
}

# Text checks: (regex on colour-stripped text, why). Errors.
TEXT_RULES = [
    (re.compile(r'\b[Aa] (?=[AEIOU][a-z])(?!Uni|Use|Usu|Ura|Uto|Eur|One)'), 'article: "a" before a vowel'),
    (re.compile(r"(?<!Lycanites' )Beastiary"), "spelling: Bestiary (the Lycanites GUI itself is \"Lycanites' Beastiary\")"),
    (re.compile(r'\b(TODO|TBD|FIXME|lorem ipsum|XXX)\b', re.I), 'placeholder text'),
    (re.compile(r'(?<!\.)\.\.(?!\.)'), 'double full stop'),
]

# ---------------------------------------------------------------------------
COLOR = re.compile('§.')


def strip(s):
    return COLOR.sub('', s or '')


class Book:
    def __init__(self, path, label=None):
        self.path = path
        self.label = label or path
        raw = open(path, 'rb').read()
        self.data = json.loads(raw.decode('utf-8'))
        self.ascii = max(raw) < 128 if raw else True
        if self._dumps() != raw:
            raise SystemExit('%s: does not round-trip byte for byte; refusing to edit it' % path)

    def _dumps(self):
        return (json.dumps(self.data, indent=2, ensure_ascii=self.ascii) + '\n').encode('utf-8')

    def save(self):
        out = self._dumps()
        json.loads(out.decode('utf-8'))
        with open(self.path, 'wb') as f:
            f.write(out)

    # -- structure ------------------------------------------------------
    @property
    def qdb(self):
        return self.data['questDatabase:9']

    @property
    def quests(self):
        return {q['questID:3']: q for q in self.qdb.values()}

    def quest(self, qid):
        for q in self.qdb.values():
            if q['questID:3'] == qid:
                return q
        raise KeyError('quest %s not in %s' % (qid, self.label))

    def has(self, qid):
        return any(q['questID:3'] == qid for q in self.qdb.values())

    @property
    def lines(self):
        return sorted(self.data['questLines:9'].values(), key=lambda l: l['lineID:3'])

    def line(self, lid):
        for l in self.data['questLines:9'].values():
            if l['lineID:3'] == lid:
                return l
        raise KeyError(lid)

    def line_of(self):
        out = collections.defaultdict(list)
        for l in self.lines:
            for e in l['quests:9'].values():
                out[e['id:3']].append(l['lineID:3'])
        return out

    def line_name(self, lid):
        return self.line(lid)['properties:10']['betterquesting:10']['name:8']

    @property
    def settings(self):
        return self.data['questSettings:10']['betterquesting:10']


def props(q):
    return q['properties:10']['betterquesting:10']


def name(q):
    return strip(props(q)['name:8'])


def stacks_of(container):
    """The item stacks inside a task or reward."""
    for key in ('requiredItems:9', 'rewards:9', 'choices:9'):
        for s in container.get(key, {}).values():
            yield s


def item(id_, count=1, damage=0):
    """A new BQ item stack in the key order BQ writes."""
    return {'id:8': id_, 'Count:3': count, 'Damage:2': damage, 'OreDict:8': ''}


def set_stacks(container, key, stacks):
    container[key] = {'%d:10' % i: s for i, s in enumerate(stacks)}


def tasks(q):
    return list(q.get('tasks:9', {}).values())


def rewards(q):
    return list(q.get('rewards:9', {}).values())


# -- edit helpers (used by patches/) ---------------------------------------
# Each helper checks the state it expects and says so when it is already applied,
# so a patch can be re-run on a book that has it and stays a no-op.

class Log:
    def __init__(self, book):
        self.book, self.lines = book, []

    def __call__(self, msg):
        self.lines.append(msg)
        print('  %-6s %s' % (self.book.label, msg))


def _match(s, id_, damage):
    return s['id:8'] == id_ and (damage is None or s.get('Damage:2', 0) == damage)


def replace_reward(log, q, old_id, new, old_damage=None, count=None):
    """Swap one reward stack (item or choice option) for `new` (a stack, or None to
    drop it). With `count`, only change the count."""
    qid = q['questID:3']
    for rw in rewards(q):
        key = 'choices:9' if 'choices:9' in rw else 'rewards:9'
        stacks = list(rw.get(key, {}).values())
        for i, s in enumerate(stacks):
            if _match(s, old_id, old_damage):
                if count is not None:
                    if s['Count:3'] == count:
                        log('q%d: %s already x%d' % (qid, old_id, count))
                        return
                    log('q%d reward: %s x%d -> x%d' % (qid, old_id, s['Count:3'], count))
                    s['Count:3'] = count
                    return
                if new is None:
                    stacks.pop(i)
                    log('q%d reward: %s x%d removed' % (qid, old_id, s['Count:3']))
                else:
                    stacks[i] = new
                    log('q%d reward: %s x%d -> %s@%d x%d' % (qid, old_id, s['Count:3'], new['id:8'],
                                                           new['Damage:2'], new['Count:3']))
                set_stacks(rw, key, stacks)
                return
    if new is not None and any(_match(s, new['id:8'], new['Damage:2']) for rw in rewards(q) for s in stacks_of(rw)):
        log('q%d: %s already replaced' % (qid, old_id))
        return
    if new is None:
        log('q%d: %s already gone' % (qid, old_id))
        return
    raise SystemExit('q%d: no reward %s to replace' % (qid, old_id))


def replace_task_item(log, q, old_id, new, old_damage=None):
    qid = q['questID:3']
    for t in tasks(q):
        stacks = list(t.get('requiredItems:9', {}).values())
        for i, s in enumerate(stacks):
            if _match(s, old_id, old_damage):
                if new is None:
                    stacks.pop(i)
                    log('q%d task: %s x%d removed' % (qid, old_id, s['Count:3']))
                else:
                    stacks[i] = new
                    log('q%d task: %s@%d x%d -> %s@%d x%d' % (qid, old_id, s.get('Damage:2', 0), s['Count:3'],
                                                            new['id:8'], new['Damage:2'], new['Count:3']))
                set_stacks(t, 'requiredItems:9', stacks)
                return
    log('q%d: task item %s already changed' % (qid, old_id))


def set_icon(log, q, new):
    ic = props(q)['icon:10']
    if (ic['id:8'], ic.get('Damage:2', 0)) != (new['id:8'], new['Damage:2']):
        log('q%d icon: %s@%d -> %s@%d' % (q['questID:3'], ic['id:8'], ic.get('Damage:2', 0), new['id:8'], new['Damage:2']))
        props(q)['icon:10'] = new


def edit_text(log, holder, field, old, new, where):
    """Replace one exact substring of a name/desc. `holder` is a quest or a line."""
    p = holder['properties:10']['betterquesting:10']
    s = p[field]
    if old in s:
        if s.count(old) != 1:
            raise SystemExit('%s %s: %r occurs %d times' % (where, field, old, s.count(old)))
        p[field] = s.replace(old, new)
        log('%s %s: %r -> %r' % (where, field, strip(old)[:60], strip(new)[:60]))
    elif new in s:
        log('%s %s: already edited' % (where, field))
    else:
        raise SystemExit('%s %s: expected text not found: %r' % (where, field, old))


def rewrite_text(log, holder, field, must_contain, new, where):
    """Replace a whole name/desc, but only if it still contains `must_contain` (so a
    re-run, or a hand edit made since, is never overwritten)."""
    p = holder['properties:10']['betterquesting:10']
    if p[field] == new:
        log('%s %s: already rewritten' % (where, field))
    elif must_contain in p[field]:
        p[field] = new
        log('%s %s: rewritten (%r...)' % (where, field, strip(new)[:50]))
    else:
        raise SystemExit('%s %s: expected text not found: %r' % (where, field, must_contain))


def load(which):
    path = BOOKS.get(which, which)
    return Book(path, which if which in BOOKS else None)


def books_for(arg):
    names = list(BOOKS) if arg in (None, 'all') else [arg]
    return [load(n) for n in names]


def refs(book):
    """Every item reference: (where, kind, stack)."""
    out = []
    for qid, q in sorted(book.quests.items()):
        out.append((qid, 'icon', props(q)['icon:10']))
        for t in tasks(q):
            for s in stacks_of(t):
                out.append((qid, 'task', s))
        for r in rewards(q):
            for s in stacks_of(r):
                out.append((qid, 'reward', s))
    for l in book.lines:
        ic = l['properties:10']['betterquesting:10'].get('icon:10')
        if ic:
            out.append(('line%d' % l['lineID:3'], 'icon', ic))
    return out


class Report:
    def __init__(self, title):
        self.title, self.errors, self.warnings, self.info = title, [], [], []

    def err(self, m):
        self.errors.append(m)

    def warn(self, m):
        self.warnings.append(m)

    def note(self, m):
        self.info.append(m)

    def print(self, verbose=False):
        status = 'FAIL' if self.errors else 'ok'
        print('[%s] %s: %d error(s), %d warning(s)' % (status, self.title, len(self.errors), len(self.warnings)))
        for m in self.errors:
            print('   ERROR', m)
        for m in self.warnings:
            print('   warn ', m)
        if verbose:
            for m in self.info:
                print('   info ', m)
        return not self.errors


# ---------------------------------------------------------------------------
# checks

def check_lint(book):
    r = Report('lint %s' % book.label)
    ids = [q['questID:3'] for q in book.qdb.values()]
    dup = [i for i, c in collections.Counter(ids).items() if c > 1]
    if dup:
        r.err('duplicate quest ids %s' % dup)
    for k, q in book.qdb.items():
        if k != '%d:10' % q['questID:3']:
            r.warn('quest %d stored under key %s' % (q['questID:3'], k))
    qs = book.quests
    for qid, q in qs.items():
        for p in q['preRequisites:11']:
            if p not in qs:
                r.err('quest %d: prerequisite %d does not exist' % (qid, p))
            if p == qid:
                r.err('quest %d requires itself' % qid)
        for i, t in enumerate(tasks(q)):
            if t.get('index:3', i) != i:
                r.warn('quest %d: task index %s at position %d' % (qid, t.get('index:3'), i))
            if t['taskID:8'] == 'bq_standard:retrieval' and not list(stacks_of(t)):
                r.err('quest %d: retrieval task with no items' % qid)
        for i, rw in enumerate(rewards(q)):
            if not list(stacks_of(rw)):
                r.err('quest %d: reward %d has no items' % (qid, i))
        if not tasks(q):
            r.err('quest %d: no tasks' % qid)
        b = props(q)
        if b.get('taskLogic:8') not in ('AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR'):
            r.err('quest %d: taskLogic %r' % (qid, b.get('taskLogic:8')))
    # cycles
    pre = {qid: [p for p in q['preRequisites:11'] if p in qs] for qid, q in qs.items()}
    state = {}

    def visit(u, path):
        state[u] = 1
        for v in pre[u]:
            if state.get(v) == 1:
                r.err('prerequisite cycle: %s' % ' -> '.join(map(str, path + [v])))
            elif not state.get(v):
                visit(v, path + [v])
        state[u] = 2
    sys.setrecursionlimit(10000)
    for q in qs:
        if not state.get(q):
            visit(q, [q])
    # lines
    lo = book.line_of()
    for qid in qs:
        if len(lo.get(qid, [])) != 1:
            r.err('quest %d (%s) is in %d quest lines' % (qid, name(qs[qid]), len(lo.get(qid, []))))
    for qid in lo:
        if qid not in qs:
            r.err('a quest line lists missing quest %d' % qid)
    orders = {}
    for l in book.lines:
        o = l.get('order:3')
        if o is None:
            r.err('line %d has no order:3' % l['lineID:3'])
            continue
        if o in orders:
            r.err('lines %d and %d share order %d' % (orders[o], l['lineID:3'], o))
        orders[o] = l['lineID:3']
    if orders:
        last = orders[max(orders)]
        if strip(book.line_name(last)).strip().lower() != 'secrets':
            r.err('the last tab is %r, not Secrets' % strip(book.line_name(last)))
    # text: raw newlines are fine in JSON-decoded strings; check section codes
    def text_fields():
        for qid, q in qs.items():
            b = props(q)
            yield 'quest %d name' % qid, b['name:8']
            yield 'quest %d desc' % qid, b['desc:8']
        for l in book.lines:
            p = l['properties:10']['betterquesting:10']
            yield 'line %d name' % l['lineID:3'], p['name:8']
            yield 'line %d desc' % l['lineID:3'], p.get('desc:8', '')
    for where, s in text_fields():
        if s.endswith('§'):
            r.err('%s ends with a bare section sign' % where)
        bad = re.findall('§([^0-9a-fk-orA-FK-OR])', s)
        if bad:
            r.err('%s: unknown formatting code(s) %s' % (where, bad))
        if '\r' in s or '\t' in s:
            r.err('%s: raw CR or tab' % where)
    for l in book.lines:
        nm = strip(l['properties:10']['betterquesting:10']['name:8'])
        if len(nm) > 14:
            r.warn('line %d name %r is longer than 14 characters (GuiHome clips it)' % (l['lineID:3'], nm))
    r.note('%d quests in %d lines' % (len(qs), len(book.lines)))
    return r


def load_registry():
    if not os.path.exists(REGISTRY):
        raise SystemExit('no %s: run `qb.py registry --save <level.dat>` first' % REGISTRY)
    return json.load(open(REGISTRY, encoding='utf-8'))


def blocked(item_id, kind):
    for pat, scope, why in BLOCKLIST + levelup_blocklist():
        hit = item_id == pat or (pat.endswith(':*') and item_id.split(':')[0] == pat[:-2])
        if hit and (scope == 'any' or scope == kind or (scope == 'task' and kind == 'icon')):
            return why
    return None


def check_ids(book):
    r = Report('ids %s' % book.label)
    reg = load_registry()
    names = set(reg['items']) | set(reg['blocks'])
    low = {n.lower(): n for n in names}
    extra = EXTRA_NAMESPACES.get(book.label, set())
    allrefs = refs(book)
    distinct = set()
    skipped = 0
    for where, kind, s in allrefs:
        iid = s['id:8']
        distinct.add(iid)
        why = blocked(iid, kind)
        if why:
            r.err('%s %s: %s is blocklisted (%s)' % (where, kind, iid, why))
        if iid in names:
            continue
        if iid.split(':')[0] in extra:
            skipped += 1
            continue
        hint = (' (case: %s)' % low[iid.lower()]) if iid.lower() in low else ''
        (r.err if kind != 'icon' else r.warn)('%s %s: %s is not registered%s' % (where, kind, iid, hint))
    r.note('%d refs, %d distinct ids; registry %d names from %s' % (
        len(allrefs), len(distinct), len(names), reg.get('source', '?')))
    if skipped:
        r.note('%d refs in namespaces %s not checked (not in the pack)' % (skipped, sorted(extra)))
    return r


def stack_matches(have, need):
    """Does a reward stack satisfy a retrieval stack (ignoring NBT)?"""
    if have['id:8'] != need['id:8']:
        return False
    nd = need.get('Damage:2', 0)
    return nd == 32767 or nd == have.get('Damage:2', 0)


def reward_options(q):
    """Every distinct bundle of items one claim of this quest can hand out: all item
    rewards together, plus one option from each choice reward."""
    fixed = [s for rw in rewards(q) if rw['rewardID:8'] != 'bq_standard:choice' for s in stacks_of(rw)]
    bundles = [fixed]
    for rw in rewards(q):
        if rw['rewardID:8'] == 'bq_standard:choice':
            opts = list(stacks_of(rw)) or [None]
            bundles = [b + ([o] if o else []) for b in bundles for o in opts]
    return bundles


def task_satisfied(task, bundle):
    if task['taskID:8'] != 'bq_standard:retrieval':
        return False
    for need in stacks_of(task):
        got = sum(s['Count:3'] for s in bundle if stack_matches(s, need))
        if got < need.get('Count:3', 1):
            return False
    return True


def quest_satisfied(q, bundle):
    ts = tasks(q)
    if not ts:
        return False
    results = [task_satisfied(t, bundle) for t in ts]
    logic = props(q).get('taskLogic:8', 'AND')
    return all(results) if logic == 'AND' else any(results) if logic == 'OR' else False


# Reward currencies. A quest whose task asks only for these is a tutorial on using
# rewards, so a reward elsewhere completing it is intended.
CURRENCY = {'lucky:lucky_block', 'lootbags:lootbag', 'qfcontent:sealed_tome'}


def check_cheese(book):
    """A reward that completes the quest it unlocks (error), or any quest that is not
    already behind it (warning)."""
    r = Report('cheese %s' % book.label)
    qs = book.quests
    succ = collections.defaultdict(list)
    for qid, q in qs.items():
        for p in q['preRequisites:11']:
            succ[p].append(qid)

    def ancestors(qid, seen=None):
        seen = set() if seen is None else seen
        for p in qs[qid]['preRequisites:11']:
            if p in qs and p not in seen:
                seen.add(p)
                ancestors(p, seen)
        return seen
    anc = {qid: ancestors(qid) for qid in qs}
    pairs = 0
    for qid, q in sorted(qs.items()):
        bundles = reward_options(q)
        for other_id, other in sorted(qs.items()):
            if other_id == qid or other_id in anc[qid]:
                continue
            hits = [b for b in bundles if quest_satisfied(other, b)]
            if not hits:
                continue
            if other_id not in succ[qid] and all(
                    s['id:8'] in CURRENCY for t in tasks(other) for s in stacks_of(t)):
                continue  # "open your first Lucky Block" tutorials are meant to be fed by rewards
            what = '; '.join('%s x%d' % (s['id:8'], s['Count:3']) for s in hits[0][:6])
            msg = '%d %s -> %d %s: one claim (%s) completes it' % (qid, name(q), other_id, name(other), what)
            if other_id in succ[qid]:
                pairs += 1
                r.err(msg)
            else:
                r.warn(msg + ' [not downstream]')
    return r


def check_stack(book):
    r = Report('stack %s' % book.label)
    for where, kind, s in refs(book):
        if kind == 'icon' or s.get('Count:3', 1) <= 1 or not unstackable(s['id:8']):
            continue
        msg = '%s %s: %s x%d is unstackable' % (where, kind, s['id:8'], s['Count:3'])
        (r.err if kind == 'task' else r.warn)(msg)
    return r


def check_text(book):
    r = Report('text %s' % book.label)
    fields = []
    for qid, q in sorted(book.quests.items()):
        fields.append(('quest %d' % qid, props(q)['name:8'] + '\n' + props(q)['desc:8']))
    for l in book.lines:
        p = l['properties:10']['betterquesting:10']
        fields.append(('line %d' % l['lineID:3'], p['name:8'] + '\n' + p.get('desc:8', '')))
    for where, s in fields:
        plain = strip(s)
        for rx, why in TEXT_RULES:
            for m in rx.finditer(plain):
                ctx = plain[max(0, m.start() - 20):m.end() + 20].replace('\n', ' / ')
                r.err('%s: %s: ...%s...' % (where, why, ctx))
    return r


CHECKS = {'lint': check_lint, 'ids': check_ids, 'cheese': check_cheese, 'stack': check_stack,
          'text': check_text}


def run_checks(names, book_arg, verbose):
    ok = True
    for book in books_for(book_arg):
        for n in names:
            ok &= CHECKS[n](book).print(verbose)
    return ok


# ---------------------------------------------------------------------------
# tally

TALLY_KEYS = [
    ('lucky', lambda s: s['id:8'] == 'lucky:lucky_block'),
] + [('bag%d' % i, (lambda i: lambda s: s['id:8'] == 'lootbags:lootbag' and s.get('Damage:2', 0) == i)(i))
     for i in range(5)] + [
    ('tome%d' % i, (lambda i: lambda s: s['id:8'] == 'qfcontent:sealed_tome' and s.get('Damage:2', 0) == i)(i))
    for i in range(5)] + [
    ('diamond', lambda s: s['id:8'] == 'minecraft:diamond'),
    ('dblock', lambda s: s['id:8'] == 'minecraft:diamond_block'),
    ('gapple', lambda s: s['id:8'] == 'minecraft:golden_apple'),
    ('star', lambda s: s['id:8'] == 'minecraft:nether_star'),
]
BAG_NAMES = ['Common', 'Uncommon', 'Rare', 'Epic', 'Legendary']


def tally(book):
    """Per line: guaranteed totals (item rewards) and best-case totals (item rewards plus
    the largest choice option of each kind)."""
    qs = book.quests
    lo = book.line_of()
    gated = {}
    # A quest that asks for a boss quest's proof item is gated too, even with no
    # prerequisites (the Secrets: "carry every OreSpawn sword" needs the Royal).
    boss_items = {(s['id:8'], s.get('Damage:2', 0)) for b in BOSS_QUESTS if b in qs
                  for t in tasks(qs[b]) for s in stacks_of(t)}

    def is_gated(qid):
        if qid in gated:
            return gated[qid]
        g = (qid in BOSS_QUESTS
             or any((s['id:8'], s.get('Damage:2', 0)) in boss_items for t in tasks(qs[qid]) for s in stacks_of(t))
             or any(is_gated(p) for p in qs[qid]['preRequisites:11'] if p in qs))
        gated[qid] = g
        return g
    per_line = collections.OrderedDict()
    ungated = collections.Counter()
    ungated_q = collections.defaultdict(list)
    ungated_line = collections.Counter()
    for l in book.lines:
        per_line[l['lineID:3']] = (collections.Counter(), collections.Counter())
    for qid, q in qs.items():
        guar, best = per_line[lo[qid][0]]
        g = collections.Counter()
        bmax = collections.Counter()
        for rw in rewards(q):
            choice = rw['rewardID:8'] == 'bq_standard:choice'
            for s in stacks_of(rw):
                for k, f in TALLY_KEYS:
                    if f(s):
                        if choice:
                            bmax[k] = max(bmax[k], s['Count:3'])
                        else:
                            g[k] += s['Count:3']
        guar.update(g)
        best.update(g + bmax)
        if not is_gated(qid):
            ungated.update(g + bmax)
            ungated_line[strip(book.line_name(lo[qid][0]))] += (g + bmax)['lucky']
            for k in ('lucky', 'bag3', 'bag4'):
                if (g + bmax)[k]:
                    ungated_q[k].append(qid)
    return per_line, ungated, ungated_q, ungated_line


def cmd_tally(a):
    keys = [k for k, _ in TALLY_KEYS]
    for book in books_for(a.book):
        per_line, ungated, ungated_q, ungated_line = tally(book)
        print('== %s  (guaranteed / best case incl. choice options)' % book.label)
        print('%-18s ' % 'line' + ' '.join('%9s' % k for k in keys))
        tot = (collections.Counter(), collections.Counter())
        for lid, (g, b) in per_line.items():
            print('%-18s ' % strip(book.line_name(lid))[:18] + ' '.join(
                '%9s' % ('%d/%d' % (g[k], b[k]) if b[k] else '.') for k in keys))
            tot[0].update(g)
            tot[1].update(b)
        print('%-18s ' % 'TOTAL' + ' '.join('%9s' % ('%d/%d' % (tot[0][k], tot[1][k])) for k in keys))
        print('ungated (no boss quest upstream), best case: ' + ', '.join(
            '%s=%d' % (k, ungated[k]) for k in keys if ungated[k]))
        print('  ungated Lucky Blocks by line: ' + ', '.join(
            '%s %d' % kv for kv in ungated_line.most_common() if kv[1]))
        for k in ('bag3', 'bag4'):
            if ungated_q[k]:
                print('  ungated %s bags in quests %s' % (BAG_NAMES[int(k[-1])], ungated_q[k]))
        print()


# ---------------------------------------------------------------------------
# dump / show / diff

def fmt_stack(s):
    return '%s x%d@%d%s%s' % (s.get('id:8'), s.get('Count:3', 1), s.get('Damage:2', 0),
                             (' OD=' + s['OreDict:8']) if s.get('OreDict:8') else '',
                             ' NBT' if 'tag:10' in s else '')


def dump(book, out):
    qs = book.quests
    for l in book.lines:
        p = l['properties:10']['betterquesting:10']
        out.write('\n########## LINE %d (order %s) %s\n%s\n' % (
            l['lineID:3'], l.get('order:3'), strip(p['name:8']), strip(p.get('desc:8', ''))))
        for e in sorted(l['quests:9'].values(), key=lambda e: (e['y:3'], e['x:3'])):
            q = qs.get(e['id:3'])
            if q is None:
                out.write('\n[%d] MISSING\n' % e['id:3'])
                continue
            b = props(q)
            out.write('\n[%d] %s  (x%d,y%d) main=%d vis=%s pre=%s logic=%s/%s\n' % (
                q['questID:3'], name(q), e['x:3'], e['y:3'], b['isMain:1'], b['visibility:8'],
                q['preRequisites:11'], b['questLogic:8'], b['taskLogic:8']))
            out.write('  icon ' + fmt_stack(b['icon:10']) + '\n')
            out.write('  DESC: ' + strip(b['desc:8']).replace('\n', ' / ') + '\n')
            for t in tasks(q):
                out.write('  TASK %s consume=%s ignoreNBT=%s partial=%s : %s\n' % (
                    t['taskID:8'], t.get('consume:1'), t.get('ignoreNBT:1'), t.get('partialMatch:1'),
                    '; '.join(fmt_stack(s) for s in stacks_of(t))))
            for rw in rewards(q):
                out.write('  REW %s : %s\n' % (rw['rewardID:8'], '; '.join(fmt_stack(s) for s in stacks_of(rw))))
    out.write('\nSETTINGS ' + json.dumps(book.data['questSettings:10']) + '\n')


def cmd_dump(a):
    for book in books_for(a.book):
        if a.out:
            path = a.out if a.book not in (None, 'all') else a.out.replace('.txt', '-%s.txt' % book.label)
            with open(path, 'w', encoding='utf-8') as f:
                dump(book, f)
            print('wrote', path)
        else:
            dump(book, sys.stdout)


def cmd_show(a):
    book = load(a.book or 'pack')
    for qid in a.qid:
        q = book.quest(qid)
        print(json.dumps(q, indent=2, ensure_ascii=False))


def cmd_diff(a):
    pa, se = load('pack'), load('server')

    def walk(x, y, path):
        if type(x) != type(y):
            print('TYPE', path)
        elif isinstance(x, dict):
            for k in list(x) + [k for k in y if k not in x]:
                if k not in y:
                    print('only pack  ', path + '/' + k)
                elif k not in x:
                    print('only server', path + '/' + k)
                else:
                    walk(x[k], y[k], path + '/' + k)
        elif x != y:
            print('differs    ', path, '|', repr(x)[:80], '|', repr(y)[:80])
    walk(pa.data, se.data, '')


# ---------------------------------------------------------------------------
# registry

def _nbt(f, t):
    if t == 1: return struct.unpack('>b', f.read(1))[0]
    if t == 2: return struct.unpack('>h', f.read(2))[0]
    if t == 3: return struct.unpack('>i', f.read(4))[0]
    if t == 4: return struct.unpack('>q', f.read(8))[0]
    if t == 5: return struct.unpack('>f', f.read(4))[0]
    if t == 6: return struct.unpack('>d', f.read(8))[0]
    if t == 7:
        n = struct.unpack('>i', f.read(4))[0]
        return f.read(n)
    if t == 8:
        n = struct.unpack('>H', f.read(2))[0]
        return f.read(n).decode('utf-8', 'replace')
    if t == 9:
        et = f.read(1)[0]
        n = struct.unpack('>i', f.read(4))[0]
        return [_nbt(f, et) for _ in range(n)]
    if t == 10:
        d = {}
        while True:
            et = f.read(1)[0]
            if et == 0:
                return d
            nl = struct.unpack('>H', f.read(2))[0]
            key = f.read(nl).decode('utf-8', 'replace')  # before the value: d[k] = v evaluates v first
            d[key] = _nbt(f, et)
    if t == 11:
        n = struct.unpack('>i', f.read(4))[0]
        return list(struct.unpack('>%di' % n, f.read(4 * n)))
    raise ValueError('NBT tag %d' % t)


def cmd_registry(a):
    """Forge writes the whole item/block registry into level.dat (FML -> ItemData).
    Names carry a \\x01 (block) or \\x02 (item) prefix. Read-only on the save."""
    with gzip.open(a.save) as f:
        t = f.read(1)[0]
        f.read(struct.unpack('>H', f.read(2))[0])
        root = _nbt(f, t)
    fml = root['FML']
    blocks = sorted(e['K'][1:] for e in fml['ItemData'] if e['K'].startswith('\x01'))
    items = sorted(e['K'][1:] for e in fml['ItemData'] if e['K'].startswith('\x02'))
    mods = sorted((m.get('ModId'), m.get('ModVersion')) for m in fml.get('ModList', []))
    out = {'source': a.save.replace('\\', '/').split('/saves/')[-1], 'mods': mods,
           'blocks': blocks, 'items': items}
    with open(REGISTRY, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=0, ensure_ascii=False)
        f.write('\n')
    print('%s: %d blocks, %d items, %d mods' % (REGISTRY, len(blocks), len(items), len(mods)))


# ---------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for n in ['check'] + list(CHECKS):
        p = sub.add_parser(n)
        p.add_argument('--book', choices=['pack', 'server', 'all'], default='all')
        p.add_argument('-v', '--verbose', action='store_true')
    p = sub.add_parser('tally')
    p.add_argument('--book', choices=['pack', 'server', 'all'], default='pack')
    p = sub.add_parser('dump')
    p.add_argument('--book', choices=['pack', 'server', 'all'], default='pack')
    p.add_argument('--out')
    p = sub.add_parser('show')
    p.add_argument('qid', type=int, nargs='+')
    p.add_argument('--book', choices=['pack', 'server'], default='pack')
    sub.add_parser('diff')
    p = sub.add_parser('registry')
    p.add_argument('--save', required=True, help='a world level.dat (read only)')
    a = ap.parse_args()
    if a.cmd == 'check':
        sys.exit(0 if run_checks(list(CHECKS), a.book, a.verbose) else 1)
    if a.cmd in CHECKS:
        sys.exit(0 if run_checks([a.cmd], a.book, a.verbose) else 1)
    {'tally': cmd_tally, 'dump': cmd_dump, 'show': cmd_show, 'diff': cmd_diff,
     'registry': cmd_registry}[a.cmd](a)


if __name__ == '__main__':
    main()
