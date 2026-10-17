#!/usr/bin/env python3
"""WP-2 of docs/design/questline-audit.md: rewards that hand out the next tier.

Reward-only changes, applied to both books (pack and server). Safe to re-run.

    py -3.10 -I tools/quests/patches/wp2_tier_leaks.py [--book pack|server|all] [--dry-run]

The faucet rule for Pets and Heroes (the 156 quests with no gate):
  - Lucky Blocks: 1 on each completion quest (a hero's Full Set, the four legendary
    pets, the Costume Closet, the last Iron Man mark); none on single pieces or
    ordinary pets. That is 53 blocks, down from 554.
  - Loot bags: at most 1 per quest, one tier lower than before (Common stays
    Common). Legendary stays only on the four legendary pets, the Costume Closet and
    the Mark 7, which need rare finds.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qb
from qb import item, replace_reward

TOME = 'qfcontent:sealed_tome'
LEGENDARY_KEEP = {67, 83, 208, 215, 301, 305}   # 4 legendary pets, Costume Closet, Mark 7
LUCKY_ONE = {67, 83, 208, 215, 301, 306}        # ...and the Mark 21 ends the Iron Man line
BAG = 'lootbags:lootbag'
LUCKY = 'lucky:lucky_block'


def faucet(book, log):
    names = {qb.strip(l['properties:10']['betterquesting:10']['name:8']): l for l in book.lines}
    qids = sorted(e['id:3'] for n in ('Pets', 'Heroes') for e in names[n]['quests:9'].values())
    before = after = 0
    changed = 0
    for qid in qids:
        q = book.quest(qid)
        full_set = qb.strip(qb.props(q)['name:8']).endswith('Full Set')
        lucky_target = 1 if (full_set or qid in LUCKY_ONE) else 0
        lucky_seen = False
        new_rewards = []
        for rw in qb.rewards(q):
            key = 'choices:9' if 'choices:9' in rw else 'rewards:9'
            stacks = []
            for s in rw.get(key, {}).values():
                if s['id:8'] == LUCKY:
                    before += s['Count:3']
                    if lucky_target and not lucky_seen:
                        lucky_seen = True
                        if s['Count:3'] != lucky_target:
                            log('q%d reward: %s x%d -> x%d' % (qid, LUCKY, s['Count:3'], lucky_target))
                            s['Count:3'] = lucky_target
                            changed += 1
                        after += 1
                        stacks.append(s)
                    else:
                        log('q%d reward: %s x%d removed' % (qid, LUCKY, s['Count:3']))
                        changed += 1
                    continue
                if s['id:8'] == BAG:
                    tier = s.get('Damage:2', 0)
                    keep_legendary = qid in LEGENDARY_KEEP and tier == 4
                    new_tier = tier if keep_legendary else max(0, tier - 1)
                    if s['Count:3'] != 1 or new_tier != tier:
                        log('q%d reward: bag %s x%d -> %s x1' % (qid, qb.BAG_NAMES[tier], s['Count:3'],
                                                              qb.BAG_NAMES[new_tier]))
                        s['Count:3'], s['Damage:2'] = 1, new_tier
                        changed += 1
                stacks.append(s)
            if stacks:
                qb.set_stacks(rw, key, stacks)
                new_rewards.append(rw)
        for i, rw in enumerate(new_rewards):
            rw['index:3'] = i
        q['rewards:9'] = {'%d:10' % i: rw for i, rw in enumerate(new_rewards)}
    return before, after, changed


def apply(book):
    log = qb.Log(book)
    Q = book.quest

    # 134: the Overlord's armour for crafting the key to its house (audit example B).
    q = Q(134)
    replace_reward(log, q, 'TragicMC:overlordHelm', item(BAG, 1, 3))
    replace_reward(log, q, 'TragicMC:overlordPlate', item(TOME, 2, 2))
    replace_reward(log, q, 'TragicMC:overlordAmulet', item('minecraft:golden_apple', 2, 1))

    # Gate-material multiples (progression audit F7): one kill = one player's key.
    replace_reward(log, Q(24), 'OreSpawn:OreSpawn_QueenScale', None, count=4)
    replace_reward(log, Q(22), 'OreSpawn:OreSpawn_BlockMobzillaScaleBlock', None, count=4)
    replace_reward(log, Q(13), 'ProjectE:item.pe_matter', None, old_damage=0, count=1)
    replace_reward(log, Q(34), 'ProjectE:item.pe_matter', None, old_damage=1, count=1)

    # 6: a ProjectE ring before the Lich.
    replace_reward(log, Q(6), 'ProjectE:item.pe_zero_ring', item(TOME, 1, 1))

    # 21: OreSpawn step 2 paid out two more Ultimate pieces for crafting the first.
    q = Q(21)
    replace_reward(log, q, 'OreSpawn:OreSpawn_UltimatePickaxe', item(BAG, 1, 2))
    replace_reward(log, q, 'OreSpawn:OreSpawn_UltimateBow', item('minecraft:experience_bottle', 8))

    # 107: part of the Death set, which Witchery's Death boss drops.
    replace_reward(log, Q(107), 'witchery:deathsrobe', item('witchery:witchrobe'))
    # 137: a top-tier named weapon from a mid-chapter quest.
    replace_reward(log, Q(137), 'TragicMC:titan', item(TOME, 1, 3))

    # Pets and Heroes faucet. Only run once per book: the tier drop is not idempotent,
    # so the marker is the Lucky total (554 before; at most 53 after).
    lucky = sum(s['Count:3'] for n in ('Pets', 'Heroes')
                for l in book.lines if qb.strip(l['properties:10']['betterquesting:10']['name:8']) == n
                for e in l['quests:9'].values()
                for rw in qb.rewards(book.quest(e['id:3'])) for s in qb.stacks_of(rw) if s['id:8'] == LUCKY)
    if lucky > 60:
        before, after, changed = faucet(book, log)
        log('Pets+Heroes: Lucky Blocks %d -> %d, %d reward stacks changed' % (before, after, changed))
    else:
        log('Pets+Heroes faucet: already capped (%d Lucky Blocks)' % lucky)
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', choices=['pack', 'server', 'all'], default='all')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for book in qb.books_for(a.book):
        print('==', book.label)
        apply(book)
        if not a.dry_run:
            book.save()


if __name__ == '__main__':
    main()
