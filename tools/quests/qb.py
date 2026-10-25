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
    481: 'First Blood (a Mutant, a ChocolateQuest boss or the Wither)', 483: 'The Wither',  # WP-6
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
# A writing placeholder left by a data patch for the writers (docs/design/quests/
# wp6-writing-brief.md): "[WRITE: what the text must say]". Allowed in a draft, an error in
# the pack and server books.
WRITE_RE = re.compile(r'\[WRITE:')

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


def add_reward_stack(log, q, stack):
    """Append `stack` to the quest's first item reward (made if there is none), unless a
    stack of that id and damage is already handed out."""
    qid = q['questID:3']
    if any(_match(s, stack['id:8'], stack['Damage:2']) for rw in rewards(q) for s in stacks_of(rw)):
        log('q%d: reward %s@%d already there' % (qid, stack['id:8'], stack['Damage:2']))
        return
    for rw in rewards(q):
        if rw['rewardID:8'] == 'bq_standard:item':
            stacks = list(rw['rewards:9'].values()) + [stack]
            set_stacks(rw, 'rewards:9', stacks)
            break
    else:
        rw = item_reward(stack)
        rw['index:3'] = len(rewards(q))
        q.setdefault('rewards:9', {})['%d:10' % rw['index:3']] = rw
    log('q%d reward: + %s@%d x%d' % (qid, stack['id:8'], stack['Damage:2'], stack['Count:3']))


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
            elif e['sizeX:3'] != size:
                log('q%d size in line %d: %d -> %d' % (qid, line_id, e['sizeX:3'], size))
            else:
                log('q%d: already in line %d' % (qid, line_id))
            e['sizeX:3'] = e['sizeY:3'] = size
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


def line_by_name(book, name_):
    """The line whose (colour-stripped) name is `name_`, or None."""
    for l in book.lines:
        if strip(book.line_name(l['lineID:3'])).strip() == strip(name_).strip():
            return l
    return None


def rename_line(log, book, old, new, desc=None, icon=None):
    """Rename a tab (found by its old or its new name). `desc`/`icon` replace the line's text
    and icon when given; the rename alone is reported as already done when only the name
    matches."""
    l = line_by_name(book, old)
    if l is None:
        l = line_by_name(book, new)
        if l is None:
            raise SystemExit('no line named %r (nor %r)' % (strip(old), strip(new)))
        log('line %d %s: already renamed' % (l['lineID:3'], strip(new)))
    else:
        if line_by_name(book, new) is not None:
            raise SystemExit('cannot rename %r: a line named %r exists' % (strip(old), strip(new)))
        l['properties:10']['betterquesting:10']['name:8'] = new
        log('line %d: renamed %r -> %r' % (l['lineID:3'], strip(old), strip(new)))
    p = l['properties:10']['betterquesting:10']
    if desc is not None and p.get('desc:8') != desc:
        log('line %d %s: desc rewritten (%r...)' % (l['lineID:3'], strip(new), strip(desc)[:40]))
        p['desc:8'] = desc
    if icon is not None and (p['icon:10']['id:8'], p['icon:10'].get('Damage:2', 0)) != (icon['id:8'], icon['Damage:2']):
        log('line %d %s: icon -> %s' % (l['lineID:3'], strip(new), icon['id:8']))
        p['icon:10'] = icon
    return l


def remove_line(log, book, name_):
    """Delete an EMPTY tab by name (or report it gone). Later tabs move one place left."""
    l = line_by_name(book, name_)
    if l is None:
        log('line %s: already removed' % strip(name_))
        return
    if l['quests:9']:
        raise SystemExit('line %d %s still holds %d quests; move them first' % (
            l['lineID:3'], strip(name_), len(l['quests:9'])))
    order = l['order:3']
    for key, other in list(book.data['questLines:9'].items()):
        if other is l:
            del book.data['questLines:9'][key]
        elif other['order:3'] > order:
            other['order:3'] -= 1
    log('line %d %s: removed (was tab %d)' % (l['lineID:3'], strip(name_), order))


def remove_quest(log, book, qid):
    """Delete a quest and its line entry (or report it gone). Stops if anything needs it."""
    if not book.has(qid):
        log('q%d: already removed' % qid)
        return
    users = sorted(o for o, q in book.quests.items() if qid in q['preRequisites:11'])
    if users:
        raise SystemExit('q%d is a prerequisite of %s; change those first' % (qid, users))
    q = book.quest(qid)
    for key, other in list(book.qdb.items()):
        if other is q:
            del book.qdb[key]
    for l in book.lines:
        es = l['quests:9']
        keep = [e for e in es.values() if e['id:3'] != qid]
        if len(keep) != len(es):
            l['quests:9'] = {'%d:10' % i: e for i, e in enumerate(keep)}
    log('q%d %s: removed' % (qid, name(q)))


def set_tab_order(log, book, leading):
    """Put the tabs named in `leading` first, in that order; every other tab keeps its
    relative order after them, and Secrets stays last."""
    lines = book.lines
    lead = []
    for nm in leading:
        l = line_by_name(book, nm)
        if l is None:
            raise SystemExit('set_tab_order: no line named %r' % nm)
        lead.append(l)
    rest = sorted((l for l in lines if l not in lead), key=lambda l: l['order:3'])
    secrets = [l for l in rest if strip(book.line_name(l['lineID:3'])).strip().lower() == 'secrets']
    rest = [l for l in rest if l not in secrets]
    changed = 0
    for i, l in enumerate(lead + rest + secrets):
        if l['order:3'] != i:
            l['order:3'] = i
            changed += 1
    log('tab order: %s' % ('already as asked' if not changed else '%d tabs moved' % changed))


def set_task_field(log, q, index, field, value):
    """Set one key of one task (for example subtypes:1 on a hunt), or report it already set."""
    t = tasks(q)[index]
    if t.get(field) == value:
        log('q%d task %d: %s already %r' % (q['questID:3'], index, field, value))
    else:
        log('q%d task %d: %s %r -> %r' % (q['questID:3'], index, field, t.get(field), value))
        t[field] = value


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
    unwritten = []
    for where, s in fields:
        plain = strip(s)
        for rx, why in TEXT_RULES:
            for m in rx.finditer(plain):
                ctx = plain[max(0, m.start() - 20):m.end() + 20].replace('\n', ' / ')
                r.err('%s: %s: ...%s...' % (where, why, ctx))
        if WRITE_RE.search(plain):
            unwritten.append(where)
    if unwritten:
        # A draft may carry writing placeholders for the Mac writers; a shipped book may not.
        msg = '%d text(s) still hold a [WRITE: ...] placeholder: %s' % (len(unwritten), ', '.join(unwritten))
        (r.err if book.label in BOOKS else r.warn)(msg)
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

# A tab is a link in the chain when its name is numbered. Two spellings, one scale:
#   "Ch N: ..."            the pre-WP-6 book: N
#   "Arrival"              the Prologue (act-structure.md section 1): 0
#   "I: ..." .. "IV: ..."  the acts: 1-4. Several tabs may share an act (decision act1-02 B,
#                          "II: Twilight" beside "II: Witchery"); they are checked as one act.
#   "Chronicle"            the Epilogue: 5
CHAPTER_RE = re.compile(r'^Ch (\d+):')
ACT_RE = re.compile(r'^(I|II|III|IV):')
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
ACT_TABS = {'Arrival': 0, 'Chronicle': 5}
ACT_NAMES = {0: 'Prologue', 1: 'Act I', 2: 'Act II', 3: 'Act III', 4: 'Act IV', 5: 'Epilogue'}
TAB_NAME_MAX = 14   # GuiHome clips longer names (lint warns)


def chapter_number(tab_name):
    """The chain position of a tab, or None for a side tab."""
    nm = strip(tab_name).strip()
    m = CHAPTER_RE.match(nm)
    if m:
        return int(m.group(1))
    m = ACT_RE.match(nm)
    if m:
        return ROMAN[m.group(1)]
    return ACT_TABS.get(nm)


# Numbered tabs that are not links in the chain, keyed by tab name, and why. Every other
# numbered chapter must open strictly after the one before it.
SIDE_CHAPTERS = {
    'Ch 2: Base': 'Base is storage QoL, a Prologue side tab (audit 4.4); it opens at quest 2 Crafting Station',
}
# Ladder tabs, keyed by tab name: (the chapter/act number whose opening the last rung must
# come after, why). A ladder's rungs each open at the boss their recipe needs, so only its
# last rung is checked. An unnumbered ladder tab ("ProjectE" after WP-6) is still checked.
LADDER_CHAPTERS = {
    'Ch 9: ProjectE': (8, 'ProjectE is a ladder: each rung opens at the boss its recipe needs (crazycraft_gating.zs), '
                          'so its first rung opens at the Lich; its last rung must come after Ch 8 opens'),
    'ProjectE': (4, 'ProjectE is a ladder: each rung opens at the boss its recipe needs (crazycraft_gating.zs), '
                    'so its first rung opens at the Lich; its last rung must come after Act IV opens'),
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


def tab_table(book, req, line):
    """(name, entries, opening entry, open set, quest ids) for one tab. An entry is a quest
    with no prerequisite inside the tab; the opening entry is the cheapest."""
    qs = book.quests
    ids = {e['id:3'] for e in line['quests:9'].values() if e['id:3'] in qs}
    entries = sorted(qid for qid in ids if not any(p in ids for p in qs[qid]['preRequisites:11']))
    if not entries:
        return None
    first = min(entries, key=lambda e: (len(req[e]), e))
    return (strip(book.line_name(line['lineID:3'])), entries, first, req[first] - {first}, ids)


def chapter_table(book, req):
    """{chapter number: [tab rows]} for the numbered tabs, in chain order. One act may hold
    several tabs (decision act1-02 B); a ladder or side tab is listed under its number too,
    and check_path treats it by name."""
    out = collections.defaultdict(list)
    for l in book.lines:
        num = chapter_number(l['properties:10']['betterquesting:10']['name:8'])
        if num is None:
            continue
        row = tab_table(book, req, l)
        if row:
            out[num].append(row)
    return collections.OrderedDict(sorted(out.items()))


def chain_label(num, tabs):
    """How to name chain position `num` in a message: the tab's name when it is one tab,
    otherwise 'Act II' (act-style names) or 'Ch 2' (the pre-WP-6 numbering). `tabs` is a
    list of tab rows or of tab names."""
    names = [t[0] if isinstance(t, tuple) else t for t in tabs]
    if len(names) == 1:
        return names[0]
    if all(CHAPTER_RE.match(n) for n in names):
        return 'Ch %d' % num
    return ACT_NAMES.get(num, 'Ch %d' % num)


def check_path(book):
    """Every act (or numbered chapter) opens strictly after the one before: each entry of each
    of its tabs needs everything the previous act's opening entry needs, and more. Side and
    ladder tabs (by name) are exempt; a ladder's last rung must still follow its act."""
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

    def describe(lname, first, opened):
        gates = qs[first]['preRequisites:11']
        r.note('%-18s opens at %d %s, after %s; %d quests first (%s)' % (
            lname, first, name(qs[first]),
            ' + '.join('%d %s' % (g, name(qs[g])) for g in gates) or 'nothing',
            len(opened), where(opened) or '-'))

    chapters = chapter_table(book, req)
    # The chain: per number, the tabs that are links (not side or ladder tabs), the act's
    # opening set (its cheapest tab's) and every quest id in the act.
    chain = collections.OrderedDict()
    for num, rows in chapters.items():
        links = [row for row in rows if row[0] not in SIDE_CHAPTERS and row[0] not in LADDER_CHAPTERS]
        if links:
            opened = min((row[3] for row in links), key=len)
            chain[num] = (links, opened, set().union(*(row[4] for row in links)))
    prev = None
    for num, rows in chapters.items():
        for lname, entries, first, opened, ids in rows:
            describe(lname, first, opened)
            if lname in SIDE_CHAPTERS:
                r.note('%-18s side chapter, not in the chain: %s' % ('', SIDE_CHAPTERS[lname]))
            elif lname in LADDER_CHAPTERS:
                pass  # checked below with the unnumbered ladders
            elif prev is not None:
                pnum, popened = prev
                pname = chain_label(pnum, chain[pnum][0])
                for e in entries:
                    if not (req[e] - {e}) > popened:
                        r.err('%s: entry %d %s does not need everything %s needs, so it can open before (or with) it'
                              % (lname, e, name(qs[e]), pname))
        if num in chain:
            links = chain[num][0]
            if len(links) > 1:
                r.note('%-18s %s: %d tabs, opens at %d' % ('', chain_label(num, links), len(links),
                                                            min((row[2] for row in links), key=lambda e: (len(req[e]), e))))
            prev = (num, chain[num][1])
    # no backwards edge: an earlier act must not need a later act's quests
    nums = list(chain)
    for i, num in enumerate(nums):
        for later in nums[i + 1:]:
            hit = chain[num][1] & chain[later][2]
            if hit:
                r.err('%s needs %s from later %s' % (chain_label(num, chain[num][0]), sorted(hit),
                                                      chain_label(later, chain[later][0])))
    # ladders: the last rung comes after the named chapter opens
    for l in book.lines:
        lname = strip(book.line_name(l['lineID:3']))
        if lname not in LADDER_CHAPTERS:
            continue
        after, why = LADDER_CHAPTERS[lname]
        row = tab_table(book, req, l)
        if row is None:
            continue
        if chapter_number(lname) is None:
            describe(lname, row[2], row[3])
        ids = row[4]
        cap = max(ids, key=lambda i: (len(req[i]), i))
        r.note('%-18s ladder; last rung %d %s needs %d quests' % ('', cap, name(qs[cap]), len(req[cap]) - 1))
        if after not in chain:
            r.warn('%s: ladder should follow chapter %s, which this book does not have' % (lname, after))
        elif not (req[cap] - {cap}) > chain[after][1]:
            r.err('%s: last rung %d does not come after %s opens' % (lname, cap, chain_label(after, chain[after][0])))
    r.note('%d quests, all reachable' % len(qs) if not r.errors else '%d quests' % len(qs))
    return r


# ---------------------------------------------------------------------------
# obtain: can a player actually get what a task asks for?

CENSUS = os.path.join(REPO, 'docs', 'reference', 'dead-items.json')
# The census is research, not a test, so by default `obtain` warns and `check` still passes.
# Two things turn a finding into an error: `--strict` (every finding), or the quest being in
# OBTAIN_VERIFIED_BAD, which lists quests whose ask someone has confirmed impossible in game:
# {quest id: 'who confirmed what, when'}. Empty today: the nine quests `obtain` flags
# (tools/quests/README.md) have not been tried in game.
OBTAIN_VERIFIED_BAD = {}
# The opposite table: quests a human has verified obtainable in game, so the census verdict is
# dropped for them: {quest id: {item id, ...}} or {quest id: '*'}. Say who verified what and when.
OBTAIN_ALLOW = {}
STRICT = False  # set by --strict on `check` and `obtain`


def load_census():
    """docs/reference/dead-items.json, written by tools/items/dead_items.py: every item's
    status ('ok' means some recipe, loot table, drop, worldgen, trade or mod craft gives it;
    'creative', 'technical', 'hidden', 'no-source', 'disabled', 'quest-only' mean none does)."""
    if not os.path.exists(CENSUS):
        return None
    return json.load(open(CENSUS, encoding='utf-8'))


def check_obtain(book):
    """A retrieval task should ask for an item the dead-item census calls `ok`: `ids` only proves
    the id is registered, and a registered item can still be creative-only, a technical block,
    or without any source in the pack. An item the dump never listed is flagged too (the dump
    client did not register it, or it is not in the pack). Findings are warnings, so the nine
    known ones stay visible on every run without failing `check`; they are errors with --strict
    or for a quest in OBTAIN_VERIFIED_BAD. Rewards of creative or technical items are always
    warnings. OBTAIN_ALLOW drops a verdict a human has tested in game."""
    r = Report('obtain %s' % book.label)
    census = load_census()
    if census is None:
        r.warn('no %s: run `py -3.10 -I tools/items/dead_items.py`; nothing checked' % os.path.relpath(CENSUS, REPO))
        return r
    items = census['items']
    extra = EXTRA_NAMESPACES.get(book.label, set())
    n = skipped = 0

    def allowed(qid, iid):
        a = OBTAIN_ALLOW.get(qid)
        return a == '*' or (a is not None and iid in a)

    def flag(qid, msg):
        if STRICT or qid in OBTAIN_VERIFIED_BAD:
            r.err(msg + (' [confirmed in game: %s]' % OBTAIN_VERIFIED_BAD[qid] if qid in OBTAIN_VERIFIED_BAD else ''))
        else:
            r.warn(msg + ' [unverified: --strict makes this an error]')

    for qid, q in sorted(book.quests.items()):
        for t in tasks(q):
            if t['taskID:8'] != 'bq_standard:retrieval':
                continue
            for s in stacks_of(t):
                iid = s['id:8']
                if iid.split(':')[0] in extra:
                    skipped += 1
                    continue
                n += 1
                if allowed(qid, iid):
                    continue
                it = items.get(iid)
                if it is None:
                    flag(qid, 'quest %d %s: task asks for %s, which the item dump never listed (registered but not '
                              'loaded on the dump client, or not in the pack); see dead-items.md' % (qid, name(q), iid))
                elif it['status'] != 'ok':
                    why = it.get('get') or ', '.join(f for f in it['flags'] if f != 'registered')
                    flag(qid, 'quest %d %s: task asks for %s, which the census calls "%s" (%s)'
                              % (qid, name(q), iid, it['status'], why[:90]))
        for rw in rewards(q):
            kind = 'reward' if rw['rewardID:8'] == 'bq_standard:item' else 'choice'
            for s in stacks_of(rw):
                iid = s['id:8']
                it = items.get(iid)
                if it and it['status'] in ('creative', 'technical', 'hidden') and not allowed(qid, iid):
                    r.warn('quest %d %s: %s hands out %s, which the census calls "%s"'
                           % (qid, name(q), kind, iid, it['status']))
    r.note('%d task items checked against the census of %s (built %s from the %s item dump); %s'
           % (n, os.path.relpath(CENSUS, REPO), census.get('built'), census.get('dump'),
              'strict: every finding is an error' if STRICT else
              'findings are warnings until confirmed in game (OBTAIN_VERIFIED_BAD) or run with --strict'))
    if skipped:
        r.note('%d task items in namespaces %s not checked (not in the pack)' % (skipped, sorted(extra)))
    return r


CHECKS = {'lint': check_lint, 'ids': check_ids, 'cheese': check_cheese, 'stack': check_stack,
          'text': check_text, 'hunt': check_hunt, 'path': check_path, 'obtain': check_obtain}


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

# Reward budget per act, audit 4.5 ("a starting point [guess, tune by playtest]"), compared
# against the best case: bag = most valuable loot bag tier allowed, tome = most valuable
# sealed tome tier, lucky = Lucky Blocks across the act, diamonds = raw diamonds plus
# 9 per diamond block. None = free. The Epilogue has no budget in the audit.
ACT_BUDGET = {
    0: {'bag': 0, 'tome': 0, 'lucky': 5, 'diamonds': 0},
    1: {'bag': 1, 'tome': 1, 'lucky': 20, 'diamonds': 16},
    2: {'bag': 2, 'tome': 2, 'lucky': 30, 'diamonds': 4 * 9},
    3: {'bag': 3, 'tome': 3, 'lucky': 30, 'diamonds': 8 * 9},
    4: {'bag': 4, 'tome': 4, 'lucky': 40, 'diamonds': None},
    5: {'bag': None, 'tome': None, 'lucky': None, 'diamonds': None},
}


def act_tally(book, per_line):
    """{act number: (tab names, guaranteed Counter, best Counter)} from the per-line totals,
    for the tabs chapter_number() places in the chain (side tabs are not an act's budget)."""
    acts = collections.OrderedDict()
    for lid, (g, b) in per_line.items():
        nm = strip(book.line_name(lid))
        num = chapter_number(nm)
        if num is None or nm in SIDE_CHAPTERS or nm in LADDER_CHAPTERS:
            continue
        names, ag, ab = acts.setdefault(num, ([], collections.Counter(), collections.Counter()))
        names.append(nm)
        ag.update(g)
        ab.update(b)
    return collections.OrderedDict(sorted(acts.items()))


def act_budget_lines(book, per_line):
    """Printable rows: one per act, with the best-case figure for each budget column and an
    'OVER' mark where it passes audit 4.5."""
    rows = []
    free = {'bag': None, 'tome': None, 'lucky': None, 'diamonds': None}
    for num, (names, g, b) in act_tally(book, per_line).items():
        act_style = not all(CHAPTER_RE.match(n) for n in names)
        bud = ACT_BUDGET.get(num, ACT_BUDGET[5]) if act_style else free
        top_bag = max([i for i in range(5) if b['bag%d' % i]] or [-1])
        top_tome = max([i for i in range(5) if b['tome%d' % i]] or [-1])
        diamonds = b['diamond'] + 9 * b['dblock']

        def cell(val, limit, show):
            over = limit is not None and val > limit
            return '%s%s' % (show, ' OVER' if over else '')
        rows.append('%-9s %-28s bag %-14s tome %-14s lucky %-9s diamonds %-10s' % (
            (ACT_NAMES.get(num, 'Ch %d' % num) if act_style else 'Ch %d' % num), ', '.join(names)[:28],
            cell(top_bag, bud['bag'], BAG_NAMES[top_bag] if top_bag >= 0 else '-'),
            cell(top_tome, bud['tome'], BAG_NAMES[top_tome] if top_tome >= 0 else '-'),
            cell(b['lucky'], bud['lucky'], '%d/%s' % (b['lucky'], bud['lucky'] if bud['lucky'] is not None else 'free')),
            cell(diamonds, bud['diamonds'], '%d/%s' % (diamonds, bud['diamonds'] if bud['diamonds'] is not None else 'free'))))
    return rows


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
        rows = act_budget_lines(book, per_line)
        if rows:
            print('by act, best case, against the audit 4.5 budget (bag and tome: most valuable tier; '
                  'diamonds count 9 per block; "Ch N" tabs have no act budget):')
            for row in rows:
                print('  ' + row)
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
        if n in ('check', 'obtain'):
            p.add_argument('--strict', action='store_true',
                           help="every `obtain` finding is an error, not a warning (the census is research; "
                                "by default only quests in OBTAIN_VERIFIED_BAD fail)")
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
    global STRICT
    STRICT = bool(getattr(a, 'strict', False))
    if a.cmd == 'check':
        sys.exit(0 if run_checks(list(CHECKS), a.book, a.verbose) else 1)
    if a.cmd in CHECKS:
        sys.exit(0 if run_checks([a.cmd], a.book, a.verbose or a.cmd == 'path') else 1)
    {'tally': cmd_tally, 'dump': cmd_dump, 'show': cmd_show, 'diff': cmd_diff,
     'registry': cmd_registry}[a.cmd](a)


if __name__ == '__main__':
    main()
