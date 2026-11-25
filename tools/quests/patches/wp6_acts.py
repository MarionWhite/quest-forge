#!/usr/bin/env python3
"""WP-6 of docs/design/questline-audit.md: the four-act spine. DRAFT FOR REVIEW.

The plan is docs/design/quests/act-structure.md (sections 1 and 3: what moves where; 4 and
8: the hunt targets; 5: side tabs; 6: multiplayer). The ten Prologue / Act I decisions it
depends on are docs/design/quests/review-2026-10-19.md section 5, asked on the Decisions
page as cards act1-01 .. act1-10 (site/decisions/sheets/s001.json) and answered on
2026-10-25 (docs/decisions/0004-prologue-and-act-i.md, docs/decisions/answers/s001.json);
this patch takes the owner's answers and builds the book they describe. Nothing here is
text for the shipped books: a quest that only moved keeps the shipped book's words, and
every new quest carries a "[WRITE: ...]" placeholder listing the checked facts its text
must carry, then the ask line, for the writers (docs/design/quests/wp6-writing-brief.md).
`qb.py text` allows those in a draft and refuses them in the pack and server books.

    py -3.10 -I tools/quests/patches/wp6_acts.py                       # the review draft, recommended answers
    py -3.10 -I tools/quests/patches/wp6_acts.py --decisions docs/decisions/answers/s001.json
    py -3.10 -I tools/quests/patches/wp6_acts.py --act1-02 B --act1-06 B  # one card at a time
    py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.wp6.json
    py -3.10 -I tools/quests/patches/wp6_acts.py --book all             # ONCE APPROVED, after wp5_prologue.py --book all

With no --book, the WP-5 draft (tools/quests/drafts/DefaultQuests.wp5.json) is copied to
tools/quests/drafts/DefaultQuests.wp6.json and the patch is applied to the copy. The repo
books are not touched. Re-running it on its own output changes nothing (`--book PATH`).

What it does, whatever the answers (act-structure section 3):
  - the finales: 481 First Blood (needs 6 Diamond Gear; OR tasks: a Mutant Skeleton, a
    Mutant Zombie, the Wither or a ChocolateQuest pirate boss), 484 The Old Powers Answer
    (17 + 105), 485 Beyond the Veil (121 + 19 + 21), 486 Titanfall (24 + 450 + 406);
  - 482 The Nether (location, dimension -1, after 5 Diamond Dreams) and 483 The Wither
    (hunt WitherBoss, after 482) in Act I;
  - each finale is the one prerequisite of the next act: 14 needs 481, 56 and the Dark
    Paths entries (43, 44, 45, 106) need 484, 22 needs 485, 122 needs 486;
  - 63 Pack Master needs 480 + 481 + 484 + 485 + 486, its task becomes a checkbox and its
    reward a statue and one Legendary loot bag (audit 4.1: cosmetic);
  - 60 Feeling Lucky? needs 6 (a crafted Lucky Block costs 2 diamonds and 2 emeralds);
  - 405 and 406 Rahovart move out of the Bestiary into Act IV;
  - "Ch 2: Base" becomes "Base" and "Ch 9: ProjectE" becomes "ProjectE" (side and ladder
    tabs, by name, in qb.py);
  - act tabs are UNLOCKED and their quests NORMAL (WP-3's rule), so an act is a rumour
    until its first quest is unlocked; pack_version 10.

Two answers are not cards this patch toggles; they are built in, always:
  no parties     The owner (act1-05 note; srv-quests B): "I don't want any quest sharing.
                 Everyone has their own quests and their own rewards." So: 478 You and Your
                 Party is not in the book (wp5_prologue.py no longer builds it; this patch
                 removes it from an older base), 480 needs 473 + 474, questSettings
                 party_enable is 0, and the two shipped texts that said "your party" (406,
                 450) lose that clause. `--no-parties` names this on the command line and
                 is accepted for the record; there is no `--parties`. An answers file whose
                 srv-quests is A (parties) stops the patch. Hunt credit: stock BetterQuesting
                 credits the killer only; qf-content is getting damage-based credit for boss
                 hunts (everyone who damaged the boss), which is code, not book data.
  no house voice act1-09 C: "completely rethink the voice ... something that doesn't take
                 itself so seriously." The W() placeholder has no hook or quote slot; the
                 writers sample a new voice first (the brief, section 1).

What depends on an answer (defaults are the review's recommendations):
  act1-01 act boundaries   A as planned. B/C cannot be built from this table (a TragicMC
                           reorder); the patch stops and says so.
  act1-02 tab layout       A one tab per act: I: Broken Sky, II: Old Powers, III: The Veil,
                           IV: Titans, Chronicle; the emptied Witchery, Dark Paths and TragicMC
                           tabs are removed. B act-prefixed mod tabs: today's tabs renamed
                           (II: Twilight, II: Witchery, III: The End, III: Dark Arts,
                           III: OreSpawn, IV: TragicMC) plus III: Twilight (the far Twilight),
                           IV: OreSpawn (the titans, Rahovart) and Chronicle.
  act1-03 /home ticket     A the ticket stays on 480. B a Common loot bag, and a note for the
                           writers to drop the ticket paragraph.
  act1-04 jukebox          A the jukebox stays 476's reward and its placeholder says it also
                           has a recipe (qf-content ModRecipes: a vanilla jukebox and a blank
                           Record, shapeless, added 2026-10-25). B reward only, no note.
                           C the reward becomes a Common loot bag, with a note.
  act1-06 Prologue length  A the 16 quests of the WP-5 draft (17 minus 478). B lean 12 minus
                           one: 472, 476, 477 to Workshop, 475 to Danger Zone, 61 back to
                           Rewards (Kitchen and Quest Forge are WP-7 tabs).
  act1-07 Act I at iron    A as drafted. B (wood and table back in Act I) breaks the Prologue
                           quests that need 2; the patch stops and says so.
  act1-08 reward cuts      A the WP-5 cuts stand. B 430 and 61 get their old rewards back and
                           0 its bed (471 keeps the bed it was given).
  act1-09 the voice        no data (see above): A/B would have meant WP-10 spreads the voice;
                           C, the answer, means no text is written until the samples are picked.
  act1-10 pigmen           A subtypes stay on. B subtypes:1 = 0 on 473's hunt.
"""
import argparse, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import qb
from wp5_prologue import TICKET_SENTENCE, JUKEBOX_SENTENCE, PARTY_TEXTS
from qb import item, hunt, location, checkbox, item_reward, add_quest, add_line, move_to_line, \
    set_prereqs, set_tasks, set_visibility, replace_reward, add_reward_stack, rewrite_text, \
    edit_text, rename_line, remove_line, remove_quest, set_tab_order, set_task_field, line_by_name

BASE = os.path.join(qb.DRAFTS, 'DefaultQuests.wp5.json')
DRAFT = os.path.join(qb.DRAFTS, 'DefaultQuests.wp6.json')
PACK_VERSION = 10
BAG = 'lootbags:lootbag'
TOME = 'qfcontent:sealed_tome'
CHRONICLE, FAR_TWILIGHT, TITANS_B = 21, 22, 23   # new line ids; 0-20 are taken in both books

# ---------------------------------------------------------------------------
# The decisions: card id -> (recommended answer, {answer: what it means}).
DECISIONS = {
    'act1-01': ('A', {'A': 'acts split as planned', 'B': 'follow the audit: TragicMC keys in Act III',
                      'C': 'something else (see the note)'}),
    'act1-02': ('A', {'A': 'one tab per act', 'B': 'act-prefixed mod tabs'}),
    'act1-03': ('A', {'A': 'the /home ticket ends the Prologue', 'B': 'a Common loot bag instead'}),
    'act1-04': ('A', {'A': 'jukebox: quest reward plus a recipe', 'B': 'quest reward only', 'C': 'recipe only'}),
    # act1-05 (parties and late friends) is not here: the owner's note removed parties (docstring).
    'act1-06': ('A', {'A': 'keep the Prologue whole (16 quests)', 'B': 'lean 11'}),
    'act1-07': ('A', {'A': 'Act I starts at iron', 'B': 'wood and the table stay in Act I'}),
    'act1-08': ('A', {'A': 'cut the moved rewards', 'B': 'keep them as they were'}),
    'act1-09': ('C', {'A': 'approve the voice', 'B': 'approve with changes', 'C': 'not yet: rejected 2026-10-25'}),
    'act1-10': ('A', {'A': 'Zombie Pigmen count', 'B': 'vanilla Zombies only (subtypes off)'}),
}
# Answered outside the cards: parties are out (decision 0004). Shown with the decisions.
PARTIES = 'none: personal progression, no 478, party_enable 0 (decision 0004; act1-05 note, srv-quests B)'
NOT_DATA = {
    ('act1-01', 'B'): 'moving the TragicMC keys into Act III reorders five TragicMC quests (act-structure section 3, '
                      '"Why TragicMC stays whole in Act IV"); redesign the chapter first, then extend LAYOUTS',
    ('act1-01', 'C'): 'read the note on the card and redesign act-structure section 1 before building',
    ('act1-07', 'B'): 'moving 1 and 2 back into Act I would put 472, 476, 35 and 471 (Prologue quests that need 2) '
                      'behind Act I; redesign the Prologue (review section 2) first',
}


def resolve_decisions(path, flags):
    """{card: answer}: the recommendation, overridden by the answers file, overridden by flags."""
    chosen = {k: v[0] for k, v in DECISIONS.items()}
    source = {k: 'recommended' for k in DECISIONS}
    if path:
        doc = json.load(open(path, encoding='utf-8'))
        resolved = doc.get('resolved') or {}
        for cid, a in resolved.items():
            c = (a or {}).get('choice')
            if cid in DECISIONS and c and c != 'later':
                if c not in DECISIONS[cid][1]:
                    raise SystemExit('%s: answer %r is not one of %s' % (cid, c, sorted(DECISIONS[cid][1])))
                chosen[cid], source[cid] = c, 'answers file'
        if (resolved.get('srv-quests') or {}).get('choice') == 'A':
            raise SystemExit('srv-quests = A (parties): decision 0004 removed BetterQuesting parties from the '
                             'design and this patch builds personal progression only; reopen the decision first')
    for cid, c in flags.items():
        if c:
            chosen[cid], source[cid] = c, 'flag'
    for cid, c in chosen.items():
        if (cid, c) in NOT_DATA:
            raise SystemExit('%s = %s (%s) cannot be built by this patch: %s' % (
                cid, c, DECISIONS[cid][1][c], NOT_DATA[(cid, c)]))
    return chosen, source


# ---------------------------------------------------------------------------
# Text placeholders. W() is a whole description left to the writers: what the text must say
# (the checked facts, no tone: the house voice was rejected, decision 0004), then the ask
# line, written here because it must state exactly what the task checks and the task is
# this patch's doing. Same shape as wp5_prologue.P().

def W(must_say, ask, header=''):
    return header + '[WRITE: %s]\n\n§e%s§r' % (must_say, ask)


def tab_desc(beat):
    """An act tab's text, all of it to write; the beat from act-structure section 2 is the
    story spine, and the tone is open."""
    return '[WRITE: the tab text. Story spine (tone open): %s]' % beat


BEATS = {
    1: 'The overworld is no longer only the overworld. Mutant Creatures walk the forests, ChocolateQuest\'s '
       'castles hold the ridges, and the Nether still burns under all of it. You climb from iron to diamond '
       'and prove you can kill something with a name.',
    2: 'The oldest powers answer first. Through a flower-ringed pool lies the Twilight Forest, where the Naga, '
       'the Twilight Lich, the Minoshroom and the Hydra guard the way deeper. In the overworld the witches '
       'teach altars, poppets and circles, and the act ends when the Hydra is dead and the Circle Talisman is '
       'made. The Philosopher\'s Stone, at the Lich, is the first taste of ProjectE.',
    3: 'The walls between worlds thin. Hardcore Ender Expansion\'s End, its Endstone Temple and a dragon far '
       'harder than vanilla\'s. The far Twilight: the Knight Stronghold, the Ur-Ghast\'s Dark Tower, the Alpha '
       'Yeti and the Snow Queen\'s Aurora Palace. Witchery\'s Spirit World, Dream and Torment. OreSpawn makes '
       'first contact, and the Mantis, Basilisk, Emperor Scorpion and Kraken stand between you and Ultimate gear.',
    4: 'The things CrazyCraft is remembered for. Mobzilla, The King and The Queen from OreSpawn; TragicMC\'s '
       'Synapse and the Overlord at its core; Rahovart, summoned with Lycanites\' Demonic Soulcube. The '
       'Transmutation Table and Dark Matter come on the way, each behind the titan its recipe needs.',
    5: 'No new tier, only the edge of the map: the Crystal Dimension and its armoury, Red Matter, the far '
       'Legends worlds, and the outskirts past the sea. Pack Master asks for the four act finales.',
}

# ---------------------------------------------------------------------------
# New quests: (qid, name, desc, icon, tasks, task logic, rewards, prereqs). Positions are in
# LAYOUTS. Rewards are proposals inside the audit 4.5 band of their act, for the owner's
# approval (the brief lists them).
NEW = [
    (481, 'First Blood',
     W('Act I ends on a kill with a name, not on a craft. Any one of these counts: a Mutant Skeleton or a '
       'Mutant Zombie (they roam the overworld), the Wither (three wither skeleton skulls and soul sand from '
       'a Nether fortress), or the pirate boss of a ChocolateQuest pirate dungeon. It may speak to friends who '
       'fight together (no group mechanic exists; the credit rule is in the brief, section 4). Point forward to '
       'the Twilight pool.',
       'Kill one of these: a Mutant Skeleton, a Mutant Zombie, the Wither, or the pirate boss of a ChocolateQuest dungeon.'),
     item('minecraft:skull', 1, 1),
     [hunt('MutantCreatures.MutantSkeleton'), hunt('MutantCreatures.MutantZombie'), hunt('WitherBoss'),
      hunt('chocolateQuest.pirateBoss')], 'OR',
     [item_reward(item(BAG, 1, 1), item(TOME, 1, 1))], [6]),

    (482, 'The Nether',
     W('The Nether: build a portal from 10 obsidian (mine it with a diamond pickaxe, or cast it in place with '
       'lava and water buckets) and light it with flint and steel. One practical tip that saves a life: bring '
       'fire resistance, and do not hit the zombie pigmen. Blaze rods, glowstone and the fortresses are why you '
       'go, and the Wither waits there. The task is a location task: standing anywhere in the Nether completes it.',
       'Enter the Nether.'),
     item('minecraft:netherrack'),
     [location('The Nether', -1)], 'AND',
     [item_reward(item('minecraft:potion', 2, 8195), item(BAG))], [5]),

    (483, 'The Wither',
     W('The Wither: four soul sand in a T, three wither skeleton skulls on top (wither skeletons walk the '
       'Nether fortresses). Spawn it underground or far from the base; it explodes when it wakes, and it '
       'flies. Its skulls wither you. It drops a Nether Star, which a beacon needs. Friends who fight together, '
       'no group mechanic (brief, section 4).',
       'Kill the Wither.'),
     item('minecraft:nether_star'),
     [hunt('WitherBoss')], 'AND',
     [item_reward(item(BAG, 1, 1), item('minecraft:experience_bottle', 8))], [482]),

    (484, 'The Old Powers Answer',
     W('Act II ends: the Hydra is dead and the Circle Talisman is made, and the oldest powers have answered. '
       'No new task; the kill was counted at 17 and the craft at 105. Point '
       'forward to what thins next: the End, the Knight Stronghold, the Dark Tower, the Aurora Palace, the '
       'Spirit World and Torment.',
       'Check the box. The Hydra and the Circle Talisman were the proof.'),
     item('TwilightForest:item.trophy', 1, 0),
     [checkbox()], 'AND',
     [item_reward(item(BAG, 1, 2), item(TOME, 1, 2))], [17, 105]),

    (485, 'Beyond the Veil',
     W('Act III ends: the HEE dragon, the Snow Queen and the Ultimate Sword. No new task; the kills were counted '
       'at 121 and 19 and the craft at 21. Point forward to the titans: Mobzilla, The King and The Queen, the '
       'Synapse and its Overlord, Rahovart. Say that nothing below Ultimate gear survives what comes next.',
       'Check the box. The dragon, the Snow Queen and the Ultimate Sword were the proof.'),
     item('HardcoreEnderExpansion:essence'),
     [checkbox()], 'AND',
     [item_reward(item(BAG, 1, 3), item(TOME, 1, 3))], [121, 19, 21]),

    (486, 'Titanfall',
     W('Act IV ends: The Queen, the Overlord\'s core and Rahovart are dead. No new task; the kills were counted '
       'at 24, 450 and 406. Point to what is left: the Crystal Dimension and its armoury, Red Matter, the far '
       'Legends worlds, the outskirts past the sea, and Pack Master.',
       'Check the box. The Queen, the Overlord and Rahovart were the proof.'),
     item('minecraft:beacon'),
     [checkbox()], 'AND',
     [item_reward(item(BAG, 1, 4), item(TOME, 1, 4))], [24, 450, 406]),
]

# Pack Master, rewritten as the convergence of the act finales (act-structure section 3,
# audit 4.1): a checkbox, a cosmetic reward, the old bulk-receipt task gone.
PACK_MASTER_TASKS_BEFORE = [('bq_standard:retrieval', ('OreSpawn:OreSpawn_BlockMobzillaScaleBlock', 0, 64),
                             ('OreSpawn:OreSpawn_Royal', 0, 1), ('OreSpawn:OreSpawn_QueenScale', 0, 64))]
PACK_MASTER_DESC = W(
    'Pack Master is the last page: the Prologue\'s 480 and the four act finales 481, 484, 485 and 486 are its '
    'prerequisites, and there is nothing to bring. The reward is a trophy, not power: a statue and one Legendary '
    'loot bag. The shipped page\'s line "The chronicle is a list. You are the last line." may stay if the new '
    'voice allows it.',
    'Check the box. The four act finales were the proof.',
    header='§6✦ THE CLIMB, FILED §r\n\n')

# Prerequisite changes, both layouts: (qid, before, after). Each finale is the one door
# into the next act (act-structure section 1, "How the finales are built").
PREREQS = [
    (14, [6], [481]),             # the Twilight pool opens at First Blood, not at Diamond Gear
    (56, [17, 105], [484]),       # the End opens at the Act II finale (the same two quests, one door)
    (43, [105], [484]),           # Dark Paths entries likewise
    (44, [105], [484]),
    (45, [105], [484]),
    (106, [105], [484]),
    (22, [21], [485]),            # Mobzilla opens Act IV at the Act III finale
    (122, [24], [486]),           # the Crystal Dimension is the Epilogue
    (63, [24], [480, 481, 484, 485, 486]),
    (60, [0], [6]),               # a crafted Lucky Block costs 2 diamonds and 2 emeralds
]

# ---------------------------------------------------------------------------
# Tab layouts per act1-02. renames: old tab -> new tab (both looked up by name, so a
# re-run finds the new one). new_lines: (id, name, desc, icon). place: tab -> (qid, x, y[, size]):
# quests moved into the tab or re-laid inside it; a quest not listed stays where it is.
# remove: tabs that must be empty afterwards. order: the leading tabs; the rest follow.

def col(quests, dx=0, dy=0):
    """Shift a block of (qid, x, y[, size]) entries."""
    return [(e[0], e[1] + dx, e[2] + dy) + tuple(e[3:]) for e in quests]


ACT1 = [(3, 0, 0), (4, 0, 48), (5, 0, 96), (6, 0, 144), (482, 48, 96), (483, 48, 144), (481, 0, 192, 32)]
TWILIGHT_NEAR = [(14, 0, 0), (15, 0, 48), (16, 0, 96), (93, 0, 144), (17, 0, 192)]
TWILIGHT_FAR = [(94, 0, 0), (18, 0, 48), (95, 0, 96), (19, 0, 144)]
WITCHERY = [(9, 0, 0), (96, 48, 0), (97, 0, 48), (10, 48, 48), (98, 0, 96), (99, 48, 96), (100, 0, 144),
            (104, 48, 144), (101, 0, 192), (102, 48, 192), (103, 0, 240), (105, 48, 240)]
DARK_PATHS = [(43, 0, 0), (109, 48, 0), (44, 0, 48), (45, 48, 48), (108, 0, 96), (106, 48, 96), (107, 0, 144)]
ORESPAWN_VEIL = [(20, 0, 0), (433, 96, 0), (74, 0, 48), (77, 48, 48), (78, 0, 96), (79, 48, 96), (21, 96, 96)]
TITANS = [(22, 0, 0), (23, 0, 48), (24, 0, 96)]
TRAGIC = [(58, 0, 0), (131, 48, 0), (132, 0, 48), (133, 48, 48), (134, 0, 96), (135, 48, 96), (450, 96, 96),
          (136, 0, 144), (137, 48, 144), (138, 0, 192), (139, 48, 192), (140, 0, 240)]
RAHOVART = [(405, 0, 0), (406, 0, 48, 32)]
CHRONICLE_Q = [(122, 0, 0), (123, 0, 48), (63, 0, 96, 32)]

LAYOUTS = {
    'A': {
        'renames': {'Ch 1: Start': 'I: Broken Sky', 'Ch 3: Twilight': 'II: Old Powers',
                    'Ch 6: The End': 'III: The Veil', 'Ch 7: OreSpawn': 'IV: Titans',
                    'Ch 2: Base': 'Base', 'Ch 9: ProjectE': 'ProjectE'},
        'descs': {'I: Broken Sky': (tab_desc(BEATS[1]), item('minecraft:iron_pickaxe')),
                  'II: Old Powers': (tab_desc(BEATS[2]), None),
                  'III: The Veil': (tab_desc(BEATS[3]), None),
                  'IV: Titans': (tab_desc(BEATS[4]), None)},
        'new_lines': [(CHRONICLE, 'Chronicle', tab_desc(BEATS[5]), item('minecraft:written_book'))],
        'place': {
            'I: Broken Sky': ACT1,
            'II: Old Powers': TWILIGHT_NEAR + col(WITCHERY, 96) + [(484, 0, 240, 32)],
            'III: The Veil': col(DARK_PATHS, 96) + col(TWILIGHT_FAR, 192) + col(ORESPAWN_VEIL, 240) + [(485, 0, 336, 32)],
            'IV: Titans': TITANS + col(TRAGIC, 96) + col(RAHOVART, 240) + [(486, 0, 144, 32)],
            'Chronicle': CHRONICLE_Q,
        },
        'remove': ['Ch 4: Witchery', 'Ch 5: Dark Paths', 'Ch 8: TragicMC'],
        'acts': ['I: Broken Sky', 'II: Old Powers', 'III: The Veil', 'IV: Titans', 'Chronicle'],
        'order': ['Arrival', 'I: Broken Sky', 'II: Old Powers', 'III: The Veil', 'IV: Titans', 'Chronicle',
                  'Base', 'ProjectE'],
    },
    'B': {
        'renames': {'Ch 1: Start': 'I: Broken Sky', 'Ch 3: Twilight': 'II: Twilight',
                    'Ch 4: Witchery': 'II: Witchery', 'Ch 5: Dark Paths': 'III: Dark Arts',
                    'Ch 6: The End': 'III: The End', 'Ch 7: OreSpawn': 'III: OreSpawn',
                    'Ch 8: TragicMC': 'IV: TragicMC', 'Ch 2: Base': 'Base', 'Ch 9: ProjectE': 'ProjectE'},
        'descs': {'I: Broken Sky': (tab_desc(BEATS[1]), item('minecraft:iron_pickaxe'))},
        'new_lines': [
            (FAR_TWILIGHT, 'III: Twilight',
             tab_desc('[WRITE: the far Twilight: the Knight Stronghold, the Ur-Ghast\'s Dark Tower, the Alpha '
                      'Yeti and the Snow Queen\'s Aurora Palace. It opens once the Hydra is dead.]'),
             item('TwilightForest:item.trophy', 1, 4)),
            (TITANS_B, 'IV: OreSpawn',
             tab_desc('[WRITE: the titans: Mobzilla, The King and The Queen, and Rahovart summoned with the '
                      'Demonic Soulcube. It opens at Beyond the Veil.]'),
             item('OreSpawn:OreSpawn_QueenScale')),
            (CHRONICLE, 'Chronicle', tab_desc(BEATS[5]), item('minecraft:written_book'))],
        'place': {
            'I: Broken Sky': ACT1,
            'II: Twilight': TWILIGHT_NEAR,
            'II: Witchery': [(484, 0, 288, 32)],
            'III: Twilight': TWILIGHT_FAR,
            'III: OreSpawn': ORESPAWN_VEIL + [(485, 0, 144, 32)],
            'IV: OreSpawn': TITANS + col(RAHOVART, 48) + [(486, 0, 144, 32)],
            'Chronicle': CHRONICLE_Q,
        },
        'remove': [],
        'acts': ['I: Broken Sky', 'II: Twilight', 'II: Witchery', 'III: Twilight', 'III: The End', 'III: Dark Arts',
                 'III: OreSpawn', 'IV: OreSpawn', 'IV: TragicMC', 'Chronicle'],
        'order': ['Arrival', 'I: Broken Sky', 'II: Twilight', 'II: Witchery', 'III: Twilight', 'III: The End',
                  'III: Dark Arts', 'III: OreSpawn', 'IV: OreSpawn', 'IV: TragicMC', 'Chronicle', 'Base', 'ProjectE'],
    },
}

# act1-06 B: the five quests that leave Arrival, and where the remaining eleven sit.
LEAN_MOVES = {'Workshop': [472, 476, 477], 'Danger Zone': [475], 'Rewards': [61]}
LEAN_ARRIVAL = [(0, 0, 0, 32), (470, 0, 48), (431, 48, 48), (1, 0, 96), (2, 0, 144), (35, 48, 144),
                (471, 0, 192), (473, 0, 240), (474, 48, 240), (430, 96, 240), (480, 0, 288, 32)]


def place(log, book, tab, entries):
    lid = line_by_name(book, tab)
    if lid is None:
        raise SystemExit('no tab named %r' % tab)
    for e in entries:
        qid, x, y = e[:3]
        size = e[3] if len(e) > 3 else 24
        if not book.has(qid):
            log('q%d: not in this book, not placed' % qid)
            continue
        move_to_line(log, book, qid, lid['lineID:3'], x, y, size)


def below(book, tab, n):
    """n free slots at the bottom of a tab, 48 apart, in a row."""
    l = line_by_name(book, tab)
    ys = [e['y:3'] for e in l['quests:9'].values()] or [-48]
    return [(48 * i, max(ys) + 48) for i in range(n)]


def apply(book, chosen):
    log = qb.Log(book)
    Q = book.quest
    if line_by_name(book, 'Arrival') is None or not book.has(480):
        raise SystemExit('%s has no Prologue: apply wp5_prologue.py first' % book.label)
    lay = LAYOUTS[chosen['act1-02']]

    # 1. Tabs: rename, create, and the act texts.
    for old, new in lay['renames'].items():
        desc, icon = lay['descs'].get(new, (None, None))
        rename_line(log, book, old, new, desc=desc, icon=icon)
    tail = max(l['order:3'] for l in book.lines)   # before Secrets; set_tab_order fixes it below
    for lid, nm, desc, icon in lay['new_lines']:
        add_line(log, book, lid, tail, nm, desc, icon, vis='UNLOCKED', template=line_by_name(book, 'Arrival')['lineID:3'])
        tail += 1

    # 2. New quests, then every move. add_quest puts a quest at its tab's end; place() lays it out.
    first_act = line_by_name(book, 'I: Broken Sky')['lineID:3']
    for qid, nm, desc, icon, task_list, logic, reward_list, pre in NEW:
        add_quest(log, book, qid, first_act, 0, 0, nm, desc, icon, task_list, reward_list, pre,
                  main=1, vis='NORMAL', logic=logic, template=6)
    for tab, entries in lay['place'].items():
        place(log, book, tab, entries)
    for tab in lay['remove']:
        remove_line(log, book, tab)

    # 3. The doors between acts.
    for qid, old, new in PREREQS:
        set_prereqs(log, Q(qid), old, new)

    # 4. Pack Master: the convergence, not a closet.
    pm = Q(63)
    set_tasks(log, pm, PACK_MASTER_TASKS_BEFORE, [checkbox()], 'AND')
    replace_reward(log, pm, 'legends:mjolnir', item('statues:statues.statue'))
    replace_reward(log, pm, 'lucky:lucky_block', None)
    replace_reward(log, pm, BAG, item(BAG, 1, 4), old_damage=3)
    rewrite_text(log, pm, 'desc:8', 'This page only wants the three OreSpawn receipts in bulk.', PACK_MASTER_DESC, 'q63')

    # 5. No parties (decision 0004): nothing is shared. The WP-5 draft no longer builds 478
    #    You and Your Party; an older base still might, so take it out here too (and the
    #    rest of WP-5's no-parties step, which is a no-op on the current base).
    if book.has(478):
        set_prereqs(log, Q(480), [473, 474, 478], [473, 474])
    remove_quest(log, book, 478)
    qb.set_setting(log, book, 'party_enable:1', 0)
    for qid, old, new in PARTY_TEXTS:
        edit_text(log, Q(qid), 'desc:8', old, new, 'q%d' % qid)

    # 6. The decisions that are data.
    if chosen['act1-03'] == 'B':
        replace_reward(log, Q(480), 'qfcommands:lottery_ticket', item(BAG))
        edit_text(log, Q(480), 'desc:8', TICKET_SENTENCE,
                  'The reward is a Common loot bag (decision act1-03 B): there is no ticket.', 'q480')
    if chosen['act1-04'] == 'A':
        edit_text(log, Q(476), 'desc:8', JUKEBOX_SENTENCE,
                  'The jukebox is the reward, and it also has a recipe: a vanilla jukebox and a blank Record, '
                  'shapeless (qf-content ModRecipes), so a second one is a craft, not a quest.', 'q476')
    elif chosen['act1-04'] == 'C':
        replace_reward(log, Q(476), 'qfcontent:qf_jukebox', item(BAG))
        edit_text(log, Q(476), 'desc:8', JUKEBOX_SENTENCE,
                  'The reward is a Common loot bag (decision act1-04 C): the jukebox is crafted, a vanilla '
                  'jukebox and a blank Record, shapeless, and never given.', 'q476')
    if chosen['act1-06'] == 'B':
        for tab, qids in LEAN_MOVES.items():
            lid = line_by_name(book, tab)['lineID:3']
            lo = book.line_of()
            todo = [q for q in qids if lo[q][0] != lid]
            slots = below(book, tab, len(todo))
            for q, (x, y) in zip(todo, slots):
                move_to_line(log, book, q, lid, x, y)
            for q in qids:
                if q not in todo:
                    log('q%d: already in %s' % (q, tab))
        place(log, book, 'Arrival', LEAN_ARRIVAL)
    if chosen['act1-08'] == 'B':
        replace_reward(log, Q(430), 'minecraft:golden_apple', None, count=2)
        replace_reward(log, Q(430), BAG, item(BAG, 1, 1), old_damage=0)
        replace_reward(log, Q(61), BAG, None, old_damage=0, count=3)
        add_reward_stack(log, Q(61), item(BAG, 1, 1))
        add_reward_stack(log, Q(0), item('minecraft:bed'))
    if chosen['act1-10'] == 'B':
        set_task_field(log, Q(473), 0, 'subtypes:1', 0)

    # 7. Visibility: act tabs UNLOCKED, their quests NORMAL (WP-3's rule, act-structure section 5).
    for tab in lay['acts']:
        l = line_by_name(book, tab)
        set_visibility(log, l, 'UNLOCKED', 'line %d %s' % (l['lineID:3'], tab))
        for e in sorted(l['quests:9'].values(), key=lambda e: e['id:3']):
            q = Q(e['id:3'])
            if qb.props(q)['visibility:8'] == 'ALWAYS':
                set_visibility(log, q, 'NORMAL', 'q%d' % e['id:3'])
    set_tab_order(log, book, lay['order'])
    qb.set_pack_version(log, book, PACK_VERSION)
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--book', help='pack, server, all, or a book path (apply to the repo books only once approved). '
                                   'Default: build the review draft from the WP-5 draft.')
    ap.add_argument('--decisions', help='docs/decisions/answers/s001.json from tools/decisions/fetch_answers.py')
    for cid, (rec, opts) in DECISIONS.items():
        ap.add_argument('--' + cid, choices=sorted(opts), metavar='|'.join(sorted(opts)),
                        help='; '.join('%s: %s' % kv for kv in sorted(opts.items())) + ' (recommended %s)' % rec)
    ap.add_argument('--no-parties', action='store_true', default=True,
                    help='personal progression: no 478, party_enable 0, no party text. Always on since decision '
                         '0004 (2026-10-25); the flag is accepted so a command line that names it keeps working')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    chosen, source = resolve_decisions(a.decisions, {cid: getattr(a, cid.replace('-', '_')) for cid in DECISIONS})
    print('decisions:')
    for cid in DECISIONS:
        print('  %s = %s  %-45s (%s)' % (cid, chosen[cid], DECISIONS[cid][1][chosen[cid]], source[cid]))
    print('  parties: %s' % PARTIES)
    if a.book:
        books = qb.books_for(a.book)
    else:
        os.makedirs(qb.DRAFTS, exist_ok=True)
        if not os.path.isfile(BASE):
            raise SystemExit('no %s: run wp5_prologue.py first' % BASE)
        if not a.dry_run:
            shutil.copyfile(BASE, DRAFT)
            books = [qb.load(DRAFT)]
        else:
            books = [qb.load(BASE)]
    for book in books:
        print('==', book.label)
        apply(book, chosen)
        if not a.dry_run:
            book.save()
            print('wrote', book.path)


if __name__ == '__main__':
    main()
