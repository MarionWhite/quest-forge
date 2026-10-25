#!/usr/bin/env python3
"""Build site/players/data/players.json from a play server's folder.

Player cards and the First Kills board for the Players page (site/players/).
Python 3, standard library only. On the PC: py -3.10 -I tools/server/player_cards.py ...

Usage:
    player_cards.py --server SERVER_DIR [--world world] [--quests PATH]
                    [--out site/players/data/players.json] [--demo]

    --server   the server folder: holds usercache.json and the world folder.
    --world    the world folder inside --server (default: world).
    --quests   DefaultQuests.json for the boss list (default: the pack's copy,
               pack/config/betterquesting/DefaultQuests.json, found from this file).
    --out      write the result there. Without --out the result is printed.
    --demo     print the result and write nothing, even when --out is given.

Inputs, read from SERVER_DIR:
    usercache.json                      uuid -> name (vanilla)
    WORLD/stats/<uuid>.json             vanilla 1.7.10 stats, flat "stat.deaths" keys, values
                                        in the stat's unit (playOneMinute is in ticks)
    WORLD/betterquesting/QuestProgress.json   BetterQuesting 3 progress, typed keys
    WORLD/playerdata/<uuid>.dat         gzip NBT, read for the Level Up class and the level

Output (players.json), times in epoch milliseconds:
    {"updated": ms, "players": [...], "firsts": [...]}
    player: uuid, name, firstSeen, lastSeen, playMinutes, deaths, mobKills,
            playerKills, questsDone, questsTotal, class (or null), level (or null),
            dimension (always null for now), bossKills {boss label: count}
    first:  boss (label), quest {id, name}, player, uuid, time. One entry per boss
            quest, in climb order (quest depth in the chain, then quest id). A boss
            nobody has finished has player, uuid and time null: "still standing".

WHAT IS CONFIRMED AGAINST REAL DATA (checked on the repo's files, 2026-10):
  - QuestProgress.json has the typed-key shape: "questProgress:9" is a map of
    "N:10" entries, each with "questID:3", "completed:9", "tasks:9"; tasks have
    "index:3", "taskID:8", "completeUsers:9", "userProgress:9". The example file
    (server/runtime/survey/betterquesting/QuestProgress.json) has 308 quests and
    NO completions, so the shape of a completed entry is NOT confirmed.
  - The boss list is read from pack DefaultQuests.json: every quest with a
    "bq_standard:hunt" task (18 quests in the pack's book when this was written).
    Names and prerequisites come from "properties:10" -> "betterquesting:10"
    -> "name:8" and "preRequisites:11".
  - usercache.json and stats/<uuid>.json are read as vanilla writes them (the
    stat keys are the 1.7.10 StatList names). The stats sample is a fake file
    written by hand for the test, not a real save.
  - LevelUp (LevelUp.jar, PlayerExtendedProperties.class, read with javap):
    the class is a byte "Class" in a compound saved under the identifier
    "LevelUpSkills" (SKILL_ID in ClassBonus). ClassBonus.from(byte) maps the byte
    to the CLASSES enum by ordinal: 0 NONE, 1 MINER, 2 WARRIOR, 3 ARTISAN,
    4 SPELUNKER, 5 SCOUT, 6 FARMER, 7 ARCHAEOLOGIST, 8 ASSASSIN, 9 LUMBERJACK,
    10 HERMIT, 11 ZEALOT, 12 FISHERMAN, 13 FREELANCE.

UNCONFIRMED, AWAIT A REAL SAVE:
  - Where Forge writes the extended-properties compound in playerdata. The
    reader looks for "LevelUpSkills" at the root and under "ForgeData".
  - The entry shape of "completed:9" (expected: a list of {"uuid:8", "timestamp:4"},
    timestamp in epoch ms). Both a list and a map keyed by uuid are accepted.
  - The level. The reader uses vanilla "XpLevel" from the playerdata root. Level Up
    may keep its own level; this is unverified.
  - firstSeen with no previous output is the earliest quest completion, and
    lastSeen is the newest of the stats/playerdata mtimes and completions. These
    are approximations; a second run keeps firstSeen from the previous --out file.
  - bossKills: the count is stat.killEntity.<entity> when that stat matches the
    hunt target, else 1 for a completed boss quest. The stat names for boss mobs
    are not confirmed (vanilla only records mobs with spawn eggs).
"""
import argparse, gzip, json, os, re, struct, sys, time, uuid as uuidlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_QUESTS = os.path.join(REPO, 'pack', 'config', 'betterquesting', 'DefaultQuests.json')
DEFAULT_OUT = os.path.join(REPO, 'site', 'players', 'data', 'players.json')

TICKS_PER_MINUTE = 20 * 60
HUNT = 'bq_standard:hunt'
# CLASSES order is the enum declaration order in ClassBonus$CLASSES (javap).
CLASSES = ['NONE', 'MINER', 'WARRIOR', 'ARTISAN', 'SPELUNKER', 'SCOUT', 'FARMER',
           'ARCHAEOLOGIST', 'ASSASSIN', 'LUMBERJACK', 'HERMIT', 'ZEALOT', 'FISHERMAN', 'FREELANCE']
UUID_RE = re.compile(r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$', re.I)


def warn(msg):
    print('player_cards: ' + msg, file=sys.stderr)


def norm_uuid(s):
    """Dashed lowercase uuid, or None if s is not a uuid."""
    if not isinstance(s, str) or not UUID_RE.match(s):
        return None
    return str(uuidlib.UUID(s))


def base(key):
    """'questID:3' -> 'questID'. Keys in BetterQuesting JSON are 'name:typeid'."""
    return key.rsplit(':', 1)[0] if ':' in key else key


def field(d, name):
    if not isinstance(d, dict):
        return None
    for k, v in d.items():
        if base(k) == name:
            return v
    return None


def ms_of_mtime(path):
    return int(os.path.getmtime(path) * 1000)


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---- NBT (1.7.10: big-endian, gzip) ------------------------------------------

_FMT = {2: '>h', 3: '>i', 4: '>q', 5: '>f', 6: '>d'}


def _read_str(buf, pos):
    (n,) = struct.unpack_from('>H', buf, pos)
    pos += 2
    return buf[pos:pos + n].decode('utf-8', 'replace'), pos + n


def _read_payload(buf, pos, t):
    if t == 1:
        return struct.unpack_from('>b', buf, pos)[0], pos + 1
    if t in _FMT:
        size = struct.calcsize(_FMT[t])
        return struct.unpack_from(_FMT[t], buf, pos)[0], pos + size
    if t == 7:
        (n,) = struct.unpack_from('>i', buf, pos)
        pos += 4
        return list(buf[pos:pos + n]), pos + n
    if t == 8:
        return _read_str(buf, pos)
    if t == 9:
        et = buf[pos]
        (n,) = struct.unpack_from('>i', buf, pos + 1)
        pos += 5
        out = []
        for _ in range(n):
            v, pos = _read_payload(buf, pos, et)
            out.append(v)
        return out, pos
    if t == 10:
        d = {}
        while True:
            tt = buf[pos]
            pos += 1
            if tt == 0:
                return d, pos
            name, pos = _read_str(buf, pos)
            d[name], pos = _read_payload(buf, pos, tt)
    if t == 11:
        (n,) = struct.unpack_from('>i', buf, pos)
        pos += 4
        return list(struct.unpack_from('>%di' % n, buf, pos)), pos + 4 * n
    raise ValueError('unknown NBT tag type %d' % t)


def read_nbt(path):
    """Root compound of a gzip NBT file as nested dicts and lists."""
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass  # not gzipped: take it as raw NBT
    if not raw or raw[0] != 10:
        raise ValueError('not a compound NBT file')
    _name, pos = _read_str(raw, 1)
    root, _ = _read_payload(raw, pos, 10)
    return root


def levelup_class(root):
    """Level Up class name from the playerdata root, or None."""
    tag = root.get('LevelUpSkills')
    if not isinstance(tag, dict) and isinstance(root.get('ForgeData'), dict):
        tag = root['ForgeData'].get('LevelUpSkills')
    if not isinstance(tag, dict):
        return None
    b = tag.get('Class')
    if not isinstance(b, int) or b <= 0 or b >= len(CLASSES):
        return None
    return CLASSES[b].capitalize()


def read_playerdata(path):
    """(class, level) from a player .dat; (None, None) if the file cannot be read."""
    try:
        root = read_nbt(path)
    except (OSError, ValueError, struct.error, IndexError) as e:
        warn('cannot read %s: %s' % (path, e))
        return None, None
    lvl = root.get('XpLevel')
    return levelup_class(root), (lvl if isinstance(lvl, int) else None)


# ---- the quest book and progress ---------------------------------------------

def boss_label(name):
    """'Twilight: Defeat the Naga' -> 'Naga'; 'OreSpawn: MOBZILLA!' -> 'MOBZILLA!'."""
    s = re.sub(r'^[^:]+: ', '', name or '', count=1)
    s = re.sub(r'^Defeat the ', '', s)
    return s


def load_book(path):
    """(names, prereqs, bosses) from a DefaultQuests.json. bosses is climb-ordered:
    each is {'id', 'name', 'label', 'targets'} for a quest with a hunt task."""
    book = load_json(path)['questDatabase:9']
    names, prereqs, hunts = {}, {}, {}
    for entry in book.values():
        qid = field(entry, 'questID')
        if not isinstance(qid, int):
            continue
        props = field(entry, 'properties') or {}
        names[qid] = field(field(props, 'betterquesting') or {}, 'name') or ('quest %d' % qid)
        pre = field(entry, 'preRequisites')
        prereqs[qid] = [p for p in pre if isinstance(p, int)] if isinstance(pre, list) else []
        for task in (field(entry, 'tasks') or {}).values():
            if field(task, 'taskID') == HUNT:
                hunts.setdefault(qid, []).append(field(task, 'target') or '')
    depth_memo = {}

    def depth(q, seen=()):
        if q in depth_memo:
            return depth_memo[q]
        if q in seen:
            return 0
        d = 0
        for p in prereqs.get(q, []):
            d = max(d, 1 + depth(p, seen + (q,)))
        depth_memo[q] = d
        return d

    bosses = [{'id': q, 'name': names[q], 'label': boss_label(names[q]), 'targets': hunts[q]}
              for q in sorted(hunts, key=lambda q: (depth(q), q))]
    return names, bosses


def load_progress(path):
    """({questID: {uuid: timestamp or None}}, number of quest entries)."""
    if not os.path.exists(path):
        warn('no QuestProgress at %s' % path)
        return {}, 0
    qp = field(load_json(path), 'questProgress') or {}
    done, total = {}, 0
    for entry in qp.values():
        qid = field(entry, 'questID')
        if not isinstance(qid, int):
            continue
        total += 1
        comp = done.setdefault(qid, {})
        completed = field(entry, 'completed') or {}
        if isinstance(completed, dict):
            elements = list(completed.items())
        else:
            elements = list(enumerate(completed))
        for key, el in elements:
            if isinstance(el, dict):
                u = norm_uuid(field(el, 'uuid'))
                ts = field(el, 'timestamp')
            else:  # a map keyed by uuid: value is a timestamp or a compound with one
                u = norm_uuid(key if isinstance(key, str) else base(str(key)))
                ts = el if isinstance(el, int) else None
            if u:
                prev = comp.get(u)
                if prev is None or (ts is not None and ts < prev):
                    comp[u] = ts if isinstance(ts, int) else None
    return done, total


def load_stats(path):
    """Flat {'stat.deaths': n, ...} from a vanilla stats file."""
    flat = {}

    def walk(prefix, v):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(prefix + '.' + k if prefix else k, x)
        else:
            flat[prefix] = v
    walk('', load_json(path))
    return flat


def stat_int(flat, key):
    v = flat.get(key, 0)
    return int(v) if isinstance(v, (int, float)) else 0


def kills_of(flat, entity):
    """Kills of one entity from stat.killEntity.<entity>, matching the full name or its tail."""
    best = 0
    for k, v in flat.items():
        if not k.startswith('stat.killEntity.'):
            continue
        ent = k[len('stat.killEntity.'):]
        if ent in entity or entity.endswith('.' + ent) or ent.endswith(entity):
            if isinstance(v, (int, float)):
                best = max(best, int(v))
    return best


# ---- build -------------------------------------------------------------------

def build(server, world, quests_path, prev):
    names = {}
    uc = os.path.join(server, 'usercache.json')
    if os.path.exists(uc):
        for e in load_json(uc):
            u = norm_uuid(e.get('uuid'))
            if u and e.get('name'):
                names[u] = e['name']
    else:
        warn('no usercache.json in %s; names will be uuids' % server)

    wdir = os.path.join(server, world)
    book_names, bosses = load_book(quests_path)
    done, total = load_progress(os.path.join(wdir, 'betterquesting', 'QuestProgress.json'))

    stats_dir = os.path.join(wdir, 'stats')
    stat_files = {}
    if os.path.isdir(stats_dir):
        for fn in os.listdir(stats_dir):
            u = norm_uuid(os.path.splitext(fn)[0]) if fn.endswith('.json') else None
            if u:
                stat_files[u] = os.path.join(stats_dir, fn)
    else:
        warn('no stats folder at %s' % stats_dir)

    completions = {}  # uuid -> {qid: ts}
    for qid, comp in done.items():
        for u, ts in comp.items():
            completions.setdefault(u, {})[qid] = ts

    everyone = set(names) | set(stat_files) | set(completions)
    players = []
    for u in everyone:
        flat = load_stats(stat_files[u]) if u in stat_files else {}
        pd = os.path.join(wdir, 'playerdata', u + '.dat')
        cls, level = read_playerdata(pd) if os.path.exists(pd) else (None, None)
        stamps = [ms_of_mtime(p) for p in (stat_files.get(u), pd if os.path.exists(pd) else None) if p]
        stamps += [t for t in completions.get(u, {}).values() if t is not None]
        last = max(stamps) if stamps else None
        old = prev.get(u, {})
        first = old.get('firstSeen')
        if first is None:
            ct = [t for t in completions.get(u, {}).values() if t is not None]
            first = min(ct) if ct else last
        kills = {}
        for b in bosses:
            if u not in done.get(b['id'], {}):
                continue
            n = max([kills_of(flat, t) for t in b['targets']] + [1])
            kills[b['label']] = n
        players.append({
            'uuid': u,
            'name': names.get(u, u),
            'firstSeen': first,
            'lastSeen': last,
            'playMinutes': stat_int(flat, 'stat.playOneMinute') // TICKS_PER_MINUTE,
            'deaths': stat_int(flat, 'stat.deaths'),
            'mobKills': stat_int(flat, 'stat.mobKills'),
            'playerKills': stat_int(flat, 'stat.playerKills'),
            'questsDone': len(completions.get(u, {})),
            'questsTotal': total,
            'class': cls,
            'level': level,
            'dimension': None,
            'bossKills': kills,
        })
    players.sort(key=lambda p: p['name'].lower())

    firsts = []
    for b in bosses:
        comp = done.get(b['id'], {})
        best = None
        for u, ts in comp.items():
            key = (ts is None, ts or 0, u)
            if best is None or key < best[0]:
                best = (key, u, ts)
        firsts.append({
            'boss': b['label'],
            'quest': {'id': b['id'], 'name': b['name']},
            'player': names.get(best[1], best[1]) if best else None,
            'uuid': best[1] if best else None,
            'time': best[2] if best else None,
        })
    return {'updated': int(time.time() * 1000), 'players': players, 'firsts': firsts}


def previous(out_path):
    """firstSeen by uuid from an earlier output, so it survives reruns."""
    try:
        return {p['uuid']: p for p in load_json(out_path).get('players', [])}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--server', required=True)
    ap.add_argument('--world', default='world')
    ap.add_argument('--quests', default=DEFAULT_QUESTS)
    ap.add_argument('--out')
    ap.add_argument('--demo', action='store_true', help='print only; write nothing')
    a = ap.parse_args(argv)

    prev = previous(a.out) if a.out and not a.demo else {}
    result = build(a.server, a.world, a.quests, prev)
    text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if a.out and not a.demo:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text)
        print('wrote %s (%d players, %d bosses)' % (a.out, len(result['players']), len(result['firsts'])),
              file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
