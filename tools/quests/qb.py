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
    check [--book pack|server|all|PATH] lint + ids + cheese + stack + text + hunt + path (exit 1 on error)
    lint | ids | cheese | stack | text | hunt   one check at a time
    path [--book ...]                   the chapter order: what opens each numbered chapter
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
# Drafts for review: copies of the pack book with a proposed work package applied.
# Every command takes one with --book PATH; nothing installs them.
DRAFTS = os.path.join(HERE, 'drafts')
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
    406: 'Rahovart', 121: 'HEE Dragon', 450: 'The Overlord',
}
# Items only a boss drops. A quest that asks for one is gated even with no prerequisites
# (the Secrets: "carry every OreSpawn sword" needs the Royal). Since WP-4 most boss quests
# prove the kill with a hunt task, so their tasks no longer list these items.
BOSS_DROPS = {
    ('TwilightForest:item.nagaScale', 0), ('TwilightForest:item.scepterZombie', 0),
    ('TwilightForest:item.scepterTwilight', 0), ('TwilightForest:item.scepterLifeDrain', 0),
    ('TwilightForest:item.meefStroganoff', 0), ('TwilightForest:item.fieryBlood', 0),
    ('TwilightForest:item.fieryTears', 0), ('TwilightForest:item.alphaFur', 0),
    ('TwilightForest:item.phantomHelm', 0), ('TwilightForest:item.phantomPlate', 0),
    ('TwilightForest:item.trophy', 4),
    ('OreSpawn:OreSpawn_BlockMobzillaScaleBlock', 0), ('OreSpawn:OreSpawn_Royal', 0),
    ('OreSpawn:OreSpawn_QueenScale', 0), ('demonmobs:demoncrystal', 0),
    ('HardcoreEnderExpansion:essence', 0), ('minecraft:dragon_egg', 0),
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


# -- task and reward builders ---------------------------------------------------
# Keys and defaults read from Standard Expansion 3.0.181 (TaskHunt / TaskLocation
# writeToNBT and constructors). index:3 is set by set_tasks().

def retrieval(*stacks, ignore_nbt=0):
    t = {'partialMatch:1': 1, 'autoConsume:1': 0, 'groupDetect:1': 0, 'ignoreNBT:1': ignore_nbt,
         'index:3': 0, 'consume:1': 0, 'requiredItems:9': {}, 'taskID:8': 'bq_standard:retrieval'}
    set_stacks(t, 'requiredItems:9', list(stacks))
    return t


def hunt(target, required=1):
    """Kill `required` of the entity whose EntityList name is `target`. BQ looks the name
    up in EntityList.stringToClassMapping and, with subtypes on (its default), credits a
    kill of that class or a subclass. A kill counts for every member of the killer's
    party. Nothing checks the name at load time, so `qb.py hunt` checks it against
    entities.json."""
    return {'index:3': 0, 'target:8': target, 'required:3': required, 'subtypes:1': 1,
            'ignoreNBT:1': 1, 'targetNBT:10': {}, 'damageType:8': '', 'taskID:8': 'bq_standard:hunt'}


def location(name, dim):
    """Be anywhere in dimension `dim` (range -1 = no distance check, biome -1 = any)."""
    return {'index:3': 0, 'name:8': name, 'posX:3': 0, 'posY:3': 0, 'posZ:3': 0, 'dimension:3': dim,
            'biome:3': -1, 'structure:8': '', 'range:3': -1, 'visible:1': 0, 'hideInfo:1': 0,
            'invert:1': 0, 'taxiCabDist:1': 0, 'taskID:8': 'bq_standard:location'}


def checkbox():
    """The player ticks it. Honour system: use it only where no task type can see the
    thing (reading a page, choosing a Level Up class, joining a party)."""
    return {'index:3': 0, 'taskID:8': 'bq_standard:checkbox'}


def item_reward(*stacks):
    r = {'rewardID:8': 'bq_standard:item', 'index:3': 0, 'rewards:9': {}}
    set_stacks(r, 'rewards:9', list(stacks))
    return r


def choice_reward(*stacks):
    r = {'rewardID:8': 'bq_standard:choice', 'index:3': 0, 'choices:9': {}}
    set_stacks(r, 'choices:9', list(stacks))
    return r


def task_key(t):
    """A comparable summary of a task, for 'is this edit already in?' checks."""
    tid = t['taskID:8']
    if tid == 'bq_standard:hunt':
        return (tid, t['target:8'], t['required:3'])
    if tid == 'bq_standard:location':
        return (tid, t['dimension:3'], t.get('biome:3', -1), t.get('structure:8', ''))
    return (tid,) + tuple((s['id:8'], s.get('Damage:2', 0), s.get('Count:3', 1)) for s in stacks_of(t))


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


def edit_text(log, holder, field, old, new, where, superseded_by=None):
    """Replace one exact substring of a name/desc. `holder` is a quest or a line.
    `superseded_by` is the text a later patch put in place of `new`, so re-running an
    earlier patch on a later book is still a no-op."""
    p = holder['properties:10']['betterquesting:10']
    s = p[field]
    if superseded_by and superseded_by in s and old not in s:
        log('%s %s: already edited (superseded since)' % (where, field))
        return
    # `new` may contain `old` (an edit that appends) or be part of it (one that cuts), so
    # "already done" is: `new` is there, and `old` is either gone or only there inside `new`.
    if old in s and not (old in new and new in s):
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
    # A later patch may have edited the rewritten text again (WP-4 changed the ask lines of
    # texts WP-1 rewrote). Its first paragraph, the hook, is what identifies it.
    hook = new.split('\n\n')[0]
    if p[field] == new:
        log('%s %s: already rewritten' % (where, field))
    elif must_contain in p[field]:
        p[field] = new
        log('%s %s: rewritten (%r...)' % (where, field, strip(new)[:50]))
    elif len(strip(hook)) >= 12 and p[field].startswith(hook):
        log('%s %s: already rewritten (edited since)' % (where, field))
    else:
        raise SystemExit('%s %s: expected text not found: %r' % (where, field, must_contain))


def set_prereqs(log, q, old, new):
    """Replace a quest's prerequisites, but only from the list we expect (`old`)."""
    qid, cur = q['questID:3'], q['preRequisites:11']
    if sorted(cur) == sorted(new):
        log('q%d prereqs: already %s' % (qid, sorted(new)))
    elif sorted(cur) == sorted(old):
        q['preRequisites:11'] = list(new)
        log('q%d prereqs: %s -> %s' % (qid, sorted(old), list(new)))
    else:
        raise SystemExit('q%d prereqs: expected %s, found %s' % (qid, sorted(old), cur))


def set_visibility(log, holder, vis, where):
    """`holder` is a quest or a quest line."""
    p = holder['properties:10']['betterquesting:10']
    if p.get('visibility:8') != vis:
        log('%s visibility: %s -> %s' % (where, p.get('visibility:8'), vis))
        p['visibility:8'] = vis


def set_tasks(log, q, old_keys, new_tasks, logic='AND'):
    """Replace all tasks of a quest. `old_keys` is the task_key() list we expect to find;
    anything else (a hand edit since) stops the patch."""
    qid = q['questID:3']
    cur = [task_key(t) for t in tasks(q)]
    want = [task_key(t) for t in new_tasks]
    sep = ' %s ' % logic
    if cur == want and props(q)['taskLogic:8'] == logic:
        log('q%d tasks: already %s' % (qid, sep.join(describe_task(k) for k in want)))
        return
    if cur != [tuple(k) for k in old_keys]:
        raise SystemExit('q%d tasks: expected %s, found %s' % (qid, old_keys, cur))
    for i, t in enumerate(new_tasks):
        t['index:3'] = i
    q['tasks:9'] = {'%d:10' % i: t for i, t in enumerate(new_tasks)}
    old_logic = props(q)['taskLogic:8']
    props(q)['taskLogic:8'] = logic
    log('q%d tasks: %s -> %s' % (qid, (' %s ' % old_logic).join(describe_task(k) for k in cur),
                                 sep.join(describe_task(k) for k in want)))


def describe_task(k):
    if k[0] == 'bq_standard:hunt':
        return 'kill %s x%d' % (k[1], k[2])
    if k[0] == 'bq_standard:location':
        return 'be in dim %d' % k[1]
    if k[0] == 'bq_standard:retrieval':
        return 'have ' + ', '.join('%s@%d x%d' % s for s in k[1:])
    return k[0]


def add_quest(log, book, qid, line_id, x, y, name_, desc, icon, task_list, reward_list, pre,
              main=0, vis='ALWAYS', logic='AND', template=0):
    """Add a new quest (or report that it is there). Copies every property BQ writes from
    an existing quest, so new quests carry the same keys in the same order."""
    if book.has(qid):
        q = book.quest(qid)
        if strip(props(q)['name:8']) != strip(name_):
            raise SystemExit('q%d exists as %r, not %r' % (qid, name(q), strip(name_)))
        log('q%d %s: already added' % (qid, strip(name_)))
        return q
    import copy
    q = copy.deepcopy(book.quest(template))
    b = props(q)
    b.update({'name:8': name_, 'desc:8': desc, 'icon:10': icon, 'isMain:1': main, 'visibility:8': vis,
              'taskLogic:8': logic, 'questLogic:8': 'AND'})
    q['questID:3'] = qid
    q['preRequisites:11'] = list(pre)
    for i, t in enumerate(task_list):
        t['index:3'] = i
    q['tasks:9'] = {'%d:10' % i: t for i, t in enumerate(task_list)}
    for i, rw in enumerate(reward_list):
        rw['index:3'] = i
    q['rewards:9'] = {'%d:10' % i: rw for i, rw in enumerate(reward_list)}
    book.qdb['%d:10' % qid] = q
    entries = book.line(line_id)['quests:9']
    entries['%d:10' % len(entries)] = {'sizeX:3': 24, 'x:3': x, 'y:3': y, 'id:3': qid, 'sizeY:3': 24}
    log('q%d %s: added to line %d at (%d,%d), prereqs %s' % (qid, strip(name_), line_id, x, y, list(pre)))
    return q


def move_in_line(log, book, line_id, qid, x, y):
    for e in book.line(line_id)['quests:9'].values():
        if e['id:3'] == qid:
            if (e['x:3'], e['y:3']) != (x, y):
                log('q%d position: (%d,%d) -> (%d,%d)' % (qid, e['x:3'], e['y:3'], x, y))
                e['x:3'], e['y:3'] = x, y
            return
    raise SystemExit('q%d is not in line %d' % (qid, line_id))


def add_line(log, book, line_id, order, name_, desc, icon, vis='ALWAYS', template=0):
    """Add an empty quest line (or report that it is there) at tab position `order`.
    Every other line at `order` or later moves one place right, so Secrets stays last.
    Copies the property keys from line `template`."""
    import copy
    if any(l['lineID:3'] == line_id for l in book.lines):
        l = book.line(line_id)
        if strip(l['properties:10']['betterquesting:10']['name:8']) != strip(name_):
            raise SystemExit('line %d exists as %r, not %r' % (line_id, strip(book.line_name(line_id)), strip(name_)))
        log('line %d %s: already added' % (line_id, strip(name_)))
        return l
    l = copy.deepcopy(book.line(template))
    l['lineID:3'] = line_id
    l['quests:9'] = {}
    l['properties:10']['betterquesting:10'].update(
        {'name:8': name_, 'desc:8': desc, 'icon:10': icon, 'visibility:8': vis, 'bg_image:8': ''})
    for other in book.data['questLines:9'].values():
        if other['order:3'] >= order:
            other['order:3'] += 1
    l['order:3'] = order
    book.data['questLines:9']['%d:10' % line_id] = l
    log('line %d %s: added at tab %d' % (line_id, strip(name_), order))
    return l


def move_to_line(log, book, qid, line_id, x, y, size=24):
    """Move a quest from whatever line holds it into `line_id` at (x, y)."""
    entries = book.line(line_id)['quests:9']
    for e in entries.values():
        if e['id:3'] == qid:
            if (e['x:3'], e['y:3']) != (x, y):
                log('q%d position in line %d: (%d,%d) -> (%d,%d)' % (qid, line_id, e['x:3'], e['y:3'], x, y))
                e['x:3'], e['y:3'] = x, y
            else:
                log('q%d: already in line %d' % (qid, line_id))
            return
    old = None
    for l in book.lines:
        es = l['quests:9']
        keep = [e for e in es.values() if e['id:3'] != qid]
        if len(keep) != len(es):
            old = l['lineID:3']
            l['quests:9'] = {'%d:10' % i: e for i, e in enumerate(keep)}
    if old is None:
        raise SystemExit('q%d is in no line' % qid)
    entries['%d:10' % len(entries)] = {'sizeX:3': size, 'x:3': x, 'y:3': y, 'id:3': qid, 'sizeY:3': size}
    log('q%d: line %d -> line %d at (%d,%d)' % (qid, old, line_id, x, y))


def set_pack_version(log, book, version):
    s = book.settings
    if s['pack_version:3'] >= version:
        log('pack_version: already %d' % s['pack_version:3'])
    else:
        log('pack_version: %d -> %d' % (s['pack_version:3'], version))
        s['pack_version:3'] = version


def load(which):
    """'pack', 'server', or the path of a book file (a draft under drafts/)."""
    path = BOOKS.get(which, which)
    if which not in BOOKS and not os.path.isfile(path):
        raise SystemExit('no book %r: use pack, server, all or the path of a DefaultQuests.json' % which)
    if which in BOOKS:
        return Book(path, which)
    try:
        label = os.path.relpath(path, REPO).replace('\\', '/')
    except ValueError:  # another drive
        label = path
    return Book(path, label)


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
            if t['taskID:8'] == 'bq_standard:hunt' and (not t.get('target:8') or t.get('required:3', 0) < 1):
                r.err('quest %d: hunt task without a target or with required < 1' % qid)
            if t['taskID:8'] == 'bq_standard:location' and 'dimension:3' not in t:
                r.err('quest %d: location task without a dimension' % qid)
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


ENTITIES = os.path.join(HERE, 'entities.json')


def load_entities():
    if not os.path.exists(ENTITIES):
        return {'entities': {}, 'dimensions': {}}
    return json.load(open(ENTITIES, encoding='utf-8'))


def check_hunt(book):
    """Hunt targets and location dimensions. BQ does not check a hunt target when the book
    loads: a wrong name is a quest nobody can finish, and the log never says so. So every
    target must be a name in entities.json, which records where each was verified."""
    r = Report('hunt %s' % book.label)
    ents = load_entities()
    known, dims = ents['entities'], ents['dimensions']
    n = 0
    for qid, q in sorted(book.quests.items()):
        for t in tasks(q):
            if t['taskID:8'] == 'bq_standard:hunt':
                n += 1
                if t['target:8'] not in known:
                    r.err('quest %d: hunt target %r is not in entities.json' % (qid, t['target:8']))
            elif t['taskID:8'] == 'bq_standard:location':
                n += 1
                if str(t['dimension:3']) not in dims:
                    r.err('quest %d: location dimension %d is not in entities.json' % (qid, t['dimension:3']))
            elif t['taskID:8'] not in ('bq_standard:retrieval', 'bq_standard:checkbox'):
                r.warn('quest %d: task type %s is not checked by qb.py' % (qid, t['taskID:8']))
    r.note('%d hunt/location tasks checked against %d known entities' % (n, len(known)))
    return r


# ---------------------------------------------------------------------------
# path: the chapter order

# A numbered tab is `Ch N: name` (today's chapters) or `<roman>: name` (the act tabs, WP-6:
# `II: Old Powers` is act 2). Keys below are the tab's label ('Ch 2', 'II'), not its number:
# Ch 2 Base and act II are both number 2.
CHAPTER_RE = re.compile(r'^(?:Ch (\d+)|(I|II|III|IV|V|VI|VII|VIII|IX|X)):')
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}


def chapter_of(name):
    """(label, number) for a numbered tab, else None: 'Ch 4: Witchery' -> ('Ch 4', 4),
    'II: Old Powers' -> ('II', 2)."""
    m = CHAPTER_RE.match(name)
    if not m:
        return None
    if m.group(1):
        return 'Ch %s' % m.group(1), int(m.group(1))
    return m.group(2), ROMAN[m.group(2)]


# Numbered tabs that are not links in the chain, and why. Every other numbered chapter
# must open strictly after the one before it.
SIDE_CHAPTERS = {
    'Ch 2': 'Base is storage QoL, a Prologue side tab (audit 4.4); it opens at quest 2 Crafting Station',
}
LADDER_CHAPTERS = {
    'Ch 9': 'ProjectE is a ladder: each rung opens at the boss its recipe needs (crazycraft_gating.zs), '
       'so its first rung opens at the Lich; its last rung must come after Ch 8 opens',
}


def required_sets(book):
    """For each quest, the cheapest set of quests that must be complete before it can be
    (itself included). AND prerequisites add up; OR takes the cheapest branch."""
    qs = book.quests
    memo = {}

    def req(qid, stack=()):
        if qid in memo:
            return memo[qid]
        if qid in stack:
            raise ValueError('cycle through %d' % qid)
        q = qs[qid]
        pres = [p for p in q['preRequisites:11'] if p in qs]
        logic = props(q).get('questLogic:8', 'AND')
        out = {qid}
        if pres:
            subs = [req(p, stack + (qid,)) for p in pres]
            if logic == 'OR':
                out |= min(subs, key=len)
            else:
                for s in subs:
                    out |= s
        memo[qid] = frozenset(out)
        return memo[qid]
    sys.setrecursionlimit(10000)
    for qid in qs:
        req(qid)
    return memo


def chapter_table(book, req):
    """[(number, line, entries, opening entry, open set, quest ids, label)] for numbered tabs."""
    qs = book.quests
    out = []
    for l in book.lines:
        c = chapter_of(strip(l['properties:10']['betterquesting:10']['name:8']))
        if not c:
            continue
        label, num = c
        ids = {e['id:3'] for e in l['quests:9'].values() if e['id:3'] in qs}
        entries = sorted(qid for qid in ids if not any(p in ids for p in qs[qid]['preRequisites:11']))
        first = min(entries, key=lambda e: (len(req[e]), e))
        out.append((num, l, entries, first, req[first] - {first}, ids, label))
    return sorted(out, key=lambda c: (c[0], c[6]))


def check_path(book):
    r = Report('path %s' % book.label)
    qs = book.quests
    try:
        req = required_sets(book)
    except ValueError as e:
        r.err('prerequisite %s' % e)
        return r
    # reachability: every prerequisite exists (lint), no cycles (above), and nothing a
    # player must finish is HIDDEN.
    for qid in sorted(qs):
        for p in sorted(req[qid] - {qid}):
            if props(qs[p]).get('visibility:8') == 'HIDDEN':
                r.err('quest %d needs %d, which is HIDDEN' % (qid, p))
    lo = book.line_of()

    def where(ids):
        c = collections.Counter(strip(book.line_name(lo[i][0])) for i in ids)
        return ', '.join('%s %d' % kv for kv in sorted(c.items(), key=lambda kv: -kv[1]))
    chapters = chapter_table(book, req)
    prev = None
    for num, l, entries, first, opened, ids, label in chapters:
        lname = strip(book.line_name(l['lineID:3']))
        gates = [p for p in qs[first]['preRequisites:11']]
        r.note('%-18s opens at %d %s, after %s; %d quests first (%s)' % (
            lname, first, name(qs[first]),
            ' + '.join('%d %s' % (g, name(qs[g])) for g in gates) or 'nothing',
            len(opened), where(opened) or '-'))
        if label in SIDE_CHAPTERS:
            r.note('%-18s side chapter, not in the chain: %s' % ('', SIDE_CHAPTERS[label]))
            continue
        if prev is not None:
            pnum, pname, popened, pids = prev
            if label in LADDER_CHAPTERS:
                cap = max(ids, key=lambda i: (len(req[i]), i))
                ok = (req[cap] - {cap}) > popened
                r.note('%-18s ladder; last rung %d %s needs %d quests' % ('', cap, name(qs[cap]), len(req[cap]) - 1))
                if not ok:
                    r.err('%s: last rung %d does not come after %s opens' % (lname, cap, pname))
            else:
                if not (opened > popened):
                    r.err('%s can open before (or with) %s: its entry %d does not need everything %s needs'
                          % (lname, pname, first, pname))
                for e in entries:
                    if e != first and not (req[e] - {e}) > popened:
                        r.err('%s: entry %d %s opens no later than %s' % (lname, e, name(qs[e]), pname))
        # no backwards edge: an earlier chapter must not need this chapter's quests
        for onum, ol, oent, ofirst, oopened, oids, olabel in chapters:
            if onum < num and olabel not in SIDE_CHAPTERS and (oopened & ids):
                r.err('%s needs %s from later %s' % (strip(book.line_name(ol['lineID:3'])),
                                                      sorted(oopened & ids), lname))
        prev = (num, lname, opened, ids)
    r.note('%d quests, all reachable' % len(qs) if not r.errors else '%d quests' % len(qs))
    return r


CHECKS = {'lint': check_lint, 'ids': check_ids, 'cheese': check_cheese, 'stack': check_stack,
          'text': check_text, 'hunt': check_hunt, 'path': check_path}


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
                  for t in tasks(qs[b]) for s in stacks_of(t)} | BOSS_DROPS

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
                if t['taskID:8'] in ('bq_standard:hunt', 'bq_standard:location'):
                    out.write('  TASK %s : %s\n' % (t['taskID:8'], describe_task(task_key(t))))
                    continue
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

BOOK_HELP = 'pack, server, all, or the path of a book file such as tools/quests/drafts/DefaultQuests.wp5.json'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for n in ['check'] + list(CHECKS):
        p = sub.add_parser(n)
        p.add_argument('--book', default='all', help=BOOK_HELP)
        p.add_argument('-v', '--verbose', action='store_true')
    p = sub.add_parser('tally')
    p.add_argument('--book', default='pack', help=BOOK_HELP)
    p = sub.add_parser('dump')
    p.add_argument('--book', default='pack', help=BOOK_HELP)
    p.add_argument('--out')
    p = sub.add_parser('show')
    p.add_argument('qid', type=int, nargs='+')
    p.add_argument('--book', default='pack', help=BOOK_HELP)
    sub.add_parser('diff')
    p = sub.add_parser('registry')
    p.add_argument('--save', required=True, help='a world level.dat (read only)')
    a = ap.parse_args()
    if a.cmd == 'check':
        sys.exit(0 if run_checks(list(CHECKS), a.book, a.verbose) else 1)
    if a.cmd in CHECKS:
        sys.exit(0 if run_checks([a.cmd], a.book, a.verbose or a.cmd == 'path') else 1)
    {'tally': cmd_tally, 'dump': cmd_dump, 'show': cmd_show, 'diff': cmd_diff,
     'registry': cmd_registry}[a.cmd](a)


if __name__ == '__main__':
    main()
