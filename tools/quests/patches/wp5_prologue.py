#!/usr/bin/env python3
"""WP-5 of docs/design/questline-audit.md: the Prologue, "Arrival". DRAFT FOR REVIEW.

A new friend joining the server mid-campaign is this pack's most common player. Today
they get "Welcome", a log, a table and then a 40-diamond wall, and nothing tells them
about graves, Infernal names, Weeping Angels, classes, tomes or the jukebox. Arrival is
the first day and the first night, plus the systems that kill people here. Act I
(today's Ch 1) opens when it is done.

    py -3.10 -I tools/quests/patches/wp5_prologue.py               # build the review draft
    py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.wp5.json
    py -3.10 -I tools/quests/patches/wp5_prologue.py --book all    # ONCE APPROVED: both repo books

With no --book, the pack book is copied to tools/quests/drafts/DefaultQuests.wp5.json and
the patch is applied to the copy; the repo books are not touched. Safe to re-run.

Built to the owner's answers of 2026-10-25 (docs/decisions/0004-prologue-and-act-i.md,
docs/decisions/answers/s001.json):
  - 16 quests in Arrival (act1-06 A was "keep 17"; the 17th was 478 You and Your Party).
  - NO PARTIES (act1-05 note, srv-quests B: "Everyone has their own quests and their own
    rewards"). 478 is not built, 480 needs 473 + 474 only, questSettings.party_enable is 0,
    and no text says "you and your party": the two shipped texts that did (406 Rahovart,
    450 The Overlord) lose that clause and keep the rest. Quest id 478 stays free.
  - THE VOICE IS REJECTED (act1-09 C). The 2026-10-19 draft wrote every new quest, and
    rewrote the nine old Ch 1 quests, in the audit 4.7 house voice (hook, body, quote, ask);
    that text is gone from this patch (it is in git history before 2026-10-25 and quoted in
    docs/design/quests/review-2026-10-19.md). Now: a quest that only moved keeps the shipped
    book's text, word for word; a new quest carries a "[WRITE: ...]" placeholder that lists
    the checked facts its text must carry, and ends with the ask line (in §e) that states
    exactly what the task checks. The writers' brief is docs/design/quests/wp6-writing-brief.md;
    `qb.py text` allows the placeholders in a draft and refuses them in the repo books.
  - wood and the crafting table move into Arrival (act1-07 A), the three reward cuts stand
    (act1-08 A), the /home ticket ends the Prologue (act1-03 A), the jukebox is 476's reward
    and also has a recipe in qf-content (act1-04 A), Zombie Pigmen count toward 473 (act1-10 A).

What it does:
  - adds line 20 "Arrival" as the first tab (every other tab moves one place right);
  - moves 0 Welcome, 1 Punch Some Trees, 2 Crafting Station, 430 The Name Was Longer,
    431 Pick a Class, 35 Adventure Awaits! and 61 Loot Bag Basics into it;
  - adds 470-477 and 480 (9 new quests; 16 in the tab);
  - Ch 1 now opens at 3 Better Tools, after 480 Into the Chronicle;
  - party_enable 0; pack_version 9.

Facts the placeholders rely on, and where each was checked:
  keys       ' quest book, J map, L Level Up, M grave design, B backpack, V record menu:
             key bindings in the live options.txt (40, 36, 38, 50, 48, 47); V is also
             qf-content RecordKeys (KEY_V). R/U are NEI's recipe and usage keys.
  graves     GraveStones (subaraki), not OpenBlocks: pack/config/OpenBlocks.cfg grave=false.
             The grave holds the inventory; only its owner may open it ("This grave
             belongs to someone. I should not do that.", BlockGrave). Its look changes
             every 5 levels (gravestonemod.cfg).
  angels     pack/config/Weeping Angels.cfg: spawn at Y 0-40, light 8 or less; only a
             pickaxe hurts them; 35% teleport, 10% infection.
  classes    Level Up lang: Miner, Warrior, Artisan, Spelunker, Scout, Farmer,
             Archaeologist. levelup.cfg disables the Book of Unlearning.
  jukebox    qf-content ModRecipes: a blank Record is coal (or iron, gold, diamond: the metal
             only changes the look) + string + redstone, shapeless; the jukebox is a vanilla
             jukebox + any blank Record, shapeless (added 2026-10-25, decision act1-04 A).
             Right-click searches, sneak-click plays or stops; local files come from the game
             directory's jukebox/ folder (MusicIndex); a blank record used on the jukebox
             opens the cutter, and a pressed one copies into the holder's library (BlockJukebox).
             476's task checks the black (coal) pressing, damage 0.
  tomes      qf-content ItemSealedTome: right-click opens it into a book; books and Magic
             Dust are applied by dropping them on the target (docs/design/enchantments.md).
  hunts      stock BetterQuesting credits a hunt kill to the killer (and, with parties off,
             to nobody else); kills by pets, minions or the environment do not count (WP-4,
             TaskHunt). qf-content is getting damage-based credit for boss hunts (everyone who
             damaged the boss; the killing blow highlighted in chat); 473's zombies are not
             a boss fight, so it is the killer's count either way.
  /home      qf-commands HomeAccess: /sethome and /home, works across dimensions, not a
             respawn point. Ticket damage value 1 (Unlockables order: vault 0, home 1).
"""
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qb
from qb import item, hunt, retrieval, checkbox, item_reward, add_quest, add_line, move_to_line, \
    set_prereqs, replace_reward, rewrite_text

DRAFT = os.path.join(qb.DRAFTS, 'DefaultQuests.wp5.json')
ARRIVAL = 20          # new line id; free in both books
CH1 = 0
BAG = 'lootbags:lootbag'
TOME = 'qfcontent:sealed_tome'
PACK_VERSION = 9


def P(must_say, ask):
    """A placeholder description for the writers: what the text must say (the checked
    facts, no tone), then the ask line, which states exactly what the task checks and is
    written here because the task is this patch's doing. No house voice: decision 0004."""
    return '[WRITE: %s]\n\n§e%s§r' % (must_say, ask)


ARRIVAL_DESC = P(
    'the Arrival tab text. Story spine (tone open): you arrive with nothing, an hour before '
    'dark, on a continent where the sky has cracked. One day and one night teach what this '
    'world does differently: graves, Level Up classes, sealed tomes, the jukebox, Infernal '
    'names and the Weeping Angels under Y 40. It ends when you have walls, food and a way home.',
    'Start with Welcome.')

CH1_DESC = P(
    'the Ch 1 tab text now that Ch 1 opens at iron: iron tools, iron armour, 16 diamonds, '
    'then the diamond kit. Wood, the table, the Infernal lesson and the class choice moved '
    'to Arrival. (WP-6 replaces this tab with "I: Broken Sky" and its own placeholder.)',
    'Start with Better Tools.')

# This sentence of 480 is what wp6_acts.py swaps under decision act1-03 B; keep it verbatim.
TICKET_SENTENCE = ('The reward is the /home ticket: right-click it and /sethome and /home are yours for '
                   'good (one place, reachable from anywhere, even another dimension; it does not move '
                   'where you wake after dying).')
# This sentence of 476 is what wp6_acts.py extends under act1-04 A and rewrites under C.
JUKEBOX_SENTENCE = 'The jukebox is the reward.'

# ---------------------------------------------------------------------------
# The new quests. (qid, x, y, size, name, desc, icon, tasks, rewards, prereqs, main)
NEW = [
    (470, 0, 48, 24, 'Where You Woke',
     P('if the server showed a map of starting points, each was marked with an honest '
       'difficulty; if it did not, you woke where everyone wakes (true today and after the '
       'spawn picker ships). Learn the ground around you before looking for worse. F3 shows '
       'your coordinates: write them down, beds break and maps get lost. J opens the JourneyMap '
       'map, which remembers everywhere you have walked.',
       'Check the box once you know where you are.'),
     item('minecraft:compass'), [checkbox()],
     [item_reward(item('minecraft:compass'), item('minecraft:map'))], [0], 1),

    (471, 0, 192, 24, 'Four Walls and a Door',
     P('the first night is about walls, not fighting. Dig into a hill or stack a box of planks; '
       'what it looks like does not matter, only that nothing walks in. Hostile mobs spawn in '
       'the dark, so torches are walls too: light the inside and the ground around the door.',
       'Have a wooden door and 8 torches.'),
     item('minecraft:wooden_door'),
     [retrieval(item('minecraft:wooden_door'), item('minecraft:torch', 8))],
     [item_reward(item('minecraft:bed'))], [2], 1),

    (472, 48, 144, 24, 'Something Hot',
     P('hunger is slower than zombies and never stops. Plant the seeds the grass drops and '
       'bake bread before the meat runs out. Food Plus and Food Expansion add hundreds of '
       'dishes: hold any food and press U to see what it goes into, R to see how it is made.',
       'Have 10 bread.'),
     item('minecraft:bread'), [retrieval(item('minecraft:bread', 10))],
     [item_reward(item('minecraft:carrot', 4), item('minecraft:potato', 4), item('minecraft:pumpkin_pie', 4))],
     [2], 0),

    (473, 0, 240, 24, 'The First Night',
     P('zombies come in numbers and walk straight through an open door. Fight from the '
       'doorway, never in the open field, and step back inside when health drops below half. '
       'Zombie Pigmen count too (the task counts subtypes). The count is your own: kills by '
       'pets, golems or the environment do not count.',
       'Kill 5 zombies.'),
     item('minecraft:rotten_flesh'), [hunt('Zombie', 5)],
     [item_reward(item('battlegear2:shield.wood'), item(BAG))], [471], 1),

    (474, 48, 240, 24, 'When You Die Here',
     P('everything you carry goes into a gravestone where you fall, and only you can open it. '
       'Walk back, open it, take it all. You wake at your last bed, not at the grave, so sleep '
       'in one before any trip you might not come back from. JourneyMap marks where you died. '
       'M chooses the stone they bury you under; better designs unlock every five levels.',
       'Check the box when you know where you will wake up.'),
     item('gravestonemod:graveStone'), [checkbox()],
     [item_reward(item('gravestonemod:graveStone'))], [473], 0),

    (475, 96, 240, 24, 'Taller Than Your House',
     P('below Y 40, in the dark, Weeping Angels spawn: they move only while nobody is looking, '
       'they can throw you somewhere else, and only a pickaxe hurts them. Light your mines and '
       'keep a pickaxe in the hotbar. Mutants, Lycanites and the biggest OreSpawn creatures walk '
       'the overworld too, and none of them is a fair fight on day one.',
       'Check the box. Then stay out of the dark below Y 40 until you have iron.'),
     item('weepingangels:Plinth'), [checkbox()],
     [item_reward(item('minecraft:torch', 16), item(BAG))], [473], 0),

    (476, 96, 144, 24, 'Bring Your Own Music',
     P('a blank Record is coal, string and redstone (iron, gold or diamond instead of coal only '
       'change its look). Right-click the jukebox to search for music; sneak and right-click to '
       'play or stop. Your own mp3 or ogg files go in the jukebox folder of the game directory. '
       'Use a blank Record on the jukebox to cut a song onto it; hand the record to a friend and '
       'it plays for them and goes into their library. Hover a record and press V for its menu. '
       + JUKEBOX_SENTENCE,
       'Have a blank black Record (the coal pressing).'),
     item('qfcontent:qf_jukebox'), [retrieval(item('qfcontent:record'))],
     [item_reward(item('qfcontent:qf_jukebox'))], [2], 0),

    (477, 96, 48, 24, 'Break the Seal',
     P('a Sealed Tome holds one enchantment; right-click it and it opens into a book. Pick the '
       'book up and drop it onto the item you want it on. The tooltip gives the chance it takes '
       'and the chance it destroys the item, so read it first. Magic Dust dropped on a book adds '
       'five points to its chance.',
       'Open a Sealed Tome and hold the book it gives you.'),
     item(TOME), [retrieval(item('qfcontent:enchant_book'), ignore_nbt=1)],
     [item_reward(item('qfcontent:consumable', 2, 0))], [431], 0),

    (480, 0, 288, 32, 'Into the Chronicle',
     P('the first night is behind you: walls, food, and a fair idea of what kills people here. '
       'Next comes iron, then diamonds, then the doors onto other worlds, the Twilight Forest '
       'first. ' + TICKET_SENTENCE,
       'Check the box. The climb starts with iron.'),
     item('minecraft:written_book'), [checkbox()],
     [item_reward(item('qfcommands:lottery_ticket', 1, 1))], [473, 474], 1),
]

# Existing quests that move into Arrival: (qid, x, y, size). Their texts are the shipped
# book's, untouched (decision 0004: the voice is rejected; the writers get them as rows).
MOVES = [(0, 0, 0, 32), (61, 48, 0, 24), (1, 0, 96, 24), (2, 0, 144, 24), (431, 48, 48, 24),
         (35, 144, 144, 24), (430, 144, 240, 24)]
# What is left of Ch 1, moved up to fill the gap.
CH1_LAYOUT = [(3, 0, 0, 24), (4, 0, 48, 24), (5, 0, 96, 24), (6, 0, 144, 24)]

PREREQS = [  # (qid, expected, new)
    (1, [0], [470]),       # the main column runs through Where You Woke
    (3, [2], [480]),       # Act I opens when the Prologue is done
    (430, [4], [473]),     # Infernal names are a first-night lesson, not an iron-armour one
    (431, [4], [470]),     # choose a class on day one
    (35, [4], [2]),        # the backpack is a day-one craft
]

# Reward changes on moved quests (act1-08 A): (qid, old id, old damage, new stack or None, count)
REWARDS = [
    (0, 'minecraft:bed', 0, None, None),                         # the bed moves to 471
    (430, 'minecraft:golden_apple', 0, None, 1),                 # 2 -> 1 golden apple
    (430, BAG, 1, item(BAG), None),                              # Uncommon bag -> Common
    (61, BAG, 1, None, None),                                    # 3 Common + 1 Uncommon ...
    (61, BAG, 0, None, 2),                                       # ... -> 2 Common
]

TEXTS = [  # (qid or 'lineN', field, must_contain, new): only the tab whose contents changed
    ('line0', 'desc:8', 'The numbered chapters are the climb.', CH1_DESC),
]

# Shipped texts that said "your party" (decision 0004): the clause goes, the rest stays as it
# was. (qid, old, new) for edit_text; wp6_acts.py applies the same list to an older base.
PARTY_TEXTS = [
    (406, 'Kill him; the kill is the receipt, and your party shares it.', 'Kill him; the kill is the receipt.'),
    (450, 'Bring your party, a way home, and more poppets than seems reasonable.',
     'Bring friends, a way home, and more poppets than seems reasonable.'),
]


def holder(book, key):
    if isinstance(key, str) and key.startswith('line'):
        return book.line(int(key[4:])), key
    return book.quest(key), 'q%d' % key


def apply(book):
    log = qb.Log(book)
    Q = book.quest
    add_line(log, book, ARRIVAL, 0, 'Arrival', ARRIVAL_DESC, item('minecraft:bed'), vis='ALWAYS', template=CH1)
    for qid, x, y, size in MOVES:
        move_to_line(log, book, qid, ARRIVAL, x, y, size)
    for qid, x, y, size in CH1_LAYOUT:
        move_to_line(log, book, qid, CH1, x, y, size)
    for qid, x, y, size, name_, desc, icon, task_list, reward_list, pre, main in NEW:
        add_quest(log, book, qid, ARRIVAL, x, y, name_, desc, icon, task_list, reward_list, pre,
                  main=main, vis='ALWAYS', template=0)
        if size != 24:
            move_to_line(log, book, qid, ARRIVAL, x, y, size)
            for e in book.line(ARRIVAL)['quests:9'].values():
                if e['id:3'] == qid:
                    e['sizeX:3'] = e['sizeY:3'] = size
    if book.has(478):   # an older draft of this patch built You and Your Party
        set_prereqs(log, Q(480), [473, 474, 478], [473, 474])
        qb.remove_quest(log, book, 478)
    for qid, old, new in PREREQS:
        set_prereqs(log, Q(qid), old, new)
    for qid, old_id, dmg, new, count in REWARDS:
        replace_reward(log, Q(qid), old_id, new, old_damage=dmg, count=count)
    for key, field, must, new in TEXTS:
        h, where = holder(book, key)
        rewrite_text(log, h, field, must, new, where)
    for qid, old, new in PARTY_TEXTS:
        qb.edit_text(log, Q(qid), 'desc:8', old, new, 'q%d' % qid)
    qb.set_setting(log, book, 'party_enable:1', 0)
    qb.set_pack_version(log, book, PACK_VERSION)
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--book', help='pack, server or all: apply to the repo books (only once approved). '
                                   'Default: rebuild the review draft from the pack book.')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if a.book:
        books = qb.books_for(a.book)
    else:
        os.makedirs(qb.DRAFTS, exist_ok=True)
        if not a.dry_run:
            shutil.copyfile(qb.BOOKS['pack'], DRAFT)
            books = [qb.load(DRAFT)]
        else:
            books = [qb.load('pack')]
    for book in books:
        print('==', book.label)
        apply(book)
        if not a.dry_run:
            book.save()
            print('wrote', book.path)


if __name__ == '__main__':
    main()
