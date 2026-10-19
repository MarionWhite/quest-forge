#!/usr/bin/env python3
"""WP-5 of docs/design/questline-audit.md: the Prologue, "Arrival". DRAFT FOR REVIEW.

A new friend joining the server mid-campaign is this pack's most common player. Today
they get "Welcome", a log, a table and then a 40-diamond wall, and nothing tells them
about graves, parties, Infernal names, Weeping Angels, classes, tomes or the jukebox.
Arrival is the first day and the first night, plus the systems that kill people here.
Act I (today's Ch 1) opens when it is done.

    py -3.10 -I tools/quests/patches/wp5_prologue.py               # build the review draft
    py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.wp5.json
    py -3.10 -I tools/quests/patches/wp5_prologue.py --book all    # ONCE APPROVED: both repo books

With no --book, the pack book is copied to tools/quests/drafts/DefaultQuests.wp5.json and
the patch is applied to the copy; the repo books are not touched. --skip-voice leaves out
part B (the WP-10 writing-pass sample on the nine original Ch 1 quests). Safe to re-run.

What it does (docs/design/quests/review-2026-10-19.md has the full list and the rewards):
  - adds line 20 "Arrival" as the first tab (every other tab moves one place right);
  - moves 0 Welcome, 1 Punch Some Trees, 2 Crafting Station, 430 The Name Was Longer,
    431 Pick a Class, 35 Adventure Awaits! and 61 Loot Bag Basics into it;
  - adds 470-478 and 480 (10 new quests; 17 in the tab);
  - Ch 1 now opens at 3 Better Tools, after 480 Into the Chronicle;
  - part B rewrites the texts of 0, 1, 2, 3, 4, 430, 5, 431, 6 in the 4.7 voice.

Facts the texts rely on, and where each was checked:
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
  jukebox    qf-content: no recipe registers the jukebox (ModRecipes), so this reward is
             its first survival source. A blank Record is coal + string + redstone; right-
             click searches, sneak-click plays or stops; local files come from the game
             directory's jukebox/ folder (MusicIndex); a blank record used on the jukebox
             opens the cutter, and a pressed one copies into the holder's library (BlockJukebox).
  tomes      qf-content ItemSealedTome: right-click opens it into a book; books and Magic
             Dust are applied by dropping them on the target (docs/design/enchantments.md).
  hunts      a hunt kill counts for every member of the killer's party (WP-4, TaskHunt).
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

ARRIVAL_DESC = (
    '§o"Everyone arrives the same way: with nothing, an hour before dark."§r\n\n'
    'The first day and the first night, and the things this world does differently: graves, '
    'parties, classes, sealed tomes, the jukebox, and mobs with long names. The climb starts '
    'once you have walls, food and a party.')

CH1_DESC = (
    '§o"Iron first. Then diamonds. Then the doors start opening."§r\n\n'
    'Iron tools, iron armour, sixteen diamonds, then the full diamond kit that the Twilight '
    'Forest and the witches expect. Every step down is louder than the last.')


def D(hook, body, quote, role, ask):
    """One description in the house voice (audit 4.7): italic hook, body, attributed
    quote, and a yellow ask that says exactly what the task checks."""
    return '§o%s§r\n\n%s\n\n§7"%s" - %s§r\n\n§e%s§r' % (hook, body, quote, role, ask)


# ---------------------------------------------------------------------------
# Part A: the new quests. (qid, x, y, size, name, desc, icon, tasks, rewards, prereqs, main)
NEW = [
    (470, 0, 48, 24, 'Where You Woke',
     D('Nobody chooses the first night. You can choose where to spend it.',
       'If the server showed you a map of starting points, each one was marked with how hard it '
       'is, and the marks were honest. If it did not, you woke where everyone wakes. Either way, '
       'learn the ground around you before you go looking for worse.\n\n'
       'Press F3 and write down where you are standing. Beds break and maps get lost; numbers do '
       'not. Press J for the map, which remembers everywhere you have walked.',
       'I picked the hard start to impress them. They found my grave on day two. It was impressive.',
       'Pathfinder',
       'Check the box once you know where you are.'),
     item('minecraft:compass'), [checkbox()],
     [item_reward(item('minecraft:compass'), item('minecraft:map'))], [0], 1),

    (471, 0, 192, 24, 'Four Walls and a Door',
     D('The first night is not a fight. It is a test of walls.',
       'Dig into a hill or stack a box of planks. It does not matter what it looks like, only '
       'that nothing walks in. Hostile mobs spawn in the dark, so a torch is a wall too: light '
       'the inside and the ground around the door.',
       'I built a beautiful house and forgot the door. It was beautiful for about a minute.',
       'Mason',
       'Have a wooden door and 8 torches.'),
     item('minecraft:wooden_door'),
     [retrieval(item('minecraft:wooden_door'), item('minecraft:torch', 8))],
     [item_reward(item('minecraft:bed'))], [2], 1),

    (472, 48, 144, 24, 'Something Hot',
     D('Hunger is slower than zombies, and it never stops.',
       'Plant the seeds the grass gives you and bake bread before the meat runs out. Food Plus '
       'and Food Expansion add hundreds of dishes. Hold any food and press U to see everything '
       'it goes into, or R to see how it is made.',
       'We ate the horse on day three. On day four we needed a horse.',
       'Cook',
       'Have 10 bread.'),
     item('minecraft:bread'), [retrieval(item('minecraft:bread', 10))],
     [item_reward(item('minecraft:carrot', 4), item('minecraft:potato', 4), item('minecraft:pumpkin_pie', 4))],
     [2], 0),

    (473, 0, 240, 24, 'The First Night',
     D('The sun goes down. The ground starts to move.',
       'Zombies come in numbers, and they walk straight through a door left open. Fight from '
       'the doorway, never in the open field, and step back inside when your health drops '
       'below half. You and your party share the count: a kill by any of you counts for all.',
       'Five is a good night. Six is when you learn to count.',
       'Gate Log',
       'Kill 5 zombies.'),
     item('minecraft:rotten_flesh'), [hunt('Zombie', 5)],
     [item_reward(item('battlegear2:shield.wood'), item(BAG))], [471], 1),

    (474, 48, 240, 24, 'When You Die Here',
     D('You will die. The question is what you lose.',
       'Everything you carry goes into a gravestone where you fall, and only you can open it. '
       'Walk back, open it, take it all. You wake at your last bed, not at the grave, so sleep '
       'in one before any trip you might not come back from.\n\n'
       'JourneyMap marks where you died. Press M to choose the stone they will bury you under; '
       'better designs unlock every five levels.',
       'We found the grave. Then we found the creeper that made it. In that order.',
       'Recovery Team',
       'Check the box when you know where you will wake up.'),
     item('gravestonemod:graveStone'), [checkbox()],
     [item_reward(item('gravestonemod:graveStone'))], [473], 0),

    (475, 96, 240, 24, 'Taller Than Your House',
     D('Some of what came through is not a fight. It is weather.',
       'Below Y 40, in the dark, Weeping Angels spawn. They move only while nobody is looking, '
       'they can throw you somewhere else, and only a pickaxe hurts them. Light your mines and '
       'keep a pickaxe in the hotbar.\n\n'
       'Mutants, Lycanites and the biggest OreSpawn creatures walk the overworld too. None of '
       'them is a fair fight on day one. If it is taller than your house, walk away.',
       'It was not chasing us. It was just going the same way. So, briefly, were we.',
       'Survey Crew',
       'Check the box. Then stay out of the dark below Y 40 until you have iron.'),
     item('weepingangels:Plinth'), [checkbox()],
     [item_reward(item('minecraft:torch', 16), item(BAG))], [473], 0),

    (476, 96, 144, 24, 'Bring Your Own Music',
     D('The one machine in this world that plays what you like.',
       'Craft a blank Record from coal, string and redstone, and the jukebox is yours. '
       'Right-click it to search for music; sneak and right-click to play or stop. Drop your '
       'own mp3 or ogg files into the jukebox folder of the game directory and they show up too.\n\n'
       'Use a blank Record on the jukebox to cut a song onto it. Hand the record to a friend: '
       'it plays for them, and the song goes into their library. Hover a record and press V '
       'for its menu.',
       'We argued about the playlist for an hour. The Hydra waited.',
       'Night Watch',
       'Have a blank Record.'),
     item('qfcontent:qf_jukebox'), [retrieval(item('qfcontent:record'))],
     [item_reward(item('qfcontent:qf_jukebox'))], [2], 0),

    (477, 96, 48, 24, 'Break the Seal',
     D('A tome holds one enchantment. You learn which when the seal breaks.',
       'Right-click a Sealed Tome and it opens into a book. Pick the book up and drop it onto '
       'the item you want it on. The tooltip gives the chance it takes and the chance it '
       'breaks the item, so read it first. Magic Dust dropped on a book adds five points to '
       'its chance.',
       'It said twelve percent to destroy. I rounded down.',
       'Binder',
       'Open a Sealed Tome and hold the book it gives you.'),
     item(TOME), [retrieval(item('qfcontent:enchant_book'), ignore_nbt=1)],
     [item_reward(item('qfcontent:consumable', 2, 0))], [431], 0),

    (478, 48, 0, 24, 'You and Your Party',
     D('Alone, the Chronicle is a list. With friends it is a story.',
       'Open the quest book and choose Party to start one, then invite your friends by name. '
       'A kill counts for everyone in the party, so a boss you fought together is done for all '
       'of you. One party for the whole group is the easy way to play here.',
       'Three of us hit it. All three of us got the page. Nobody argued, which was a first.',
       'Hall Steward',
       'Check the box once you are in a party, or once you have chosen to walk alone.'),
     item('minecraft:cake'), [checkbox()],
     [item_reward(item('minecraft:cake'))], [0], 0),

    (480, 0, 288, 32, 'Into the Chronicle',
     D('The first night is behind you. The rest of the world is not.',
       'You have walls, food, a party and a fair idea of what kills people here. Next comes '
       'iron, then diamonds, and then the doors that open onto other worlds, the Twilight '
       'Forest first.\n\n'
       'The reward is a ticket. Right-click it and /sethome and /home are yours for good: mark '
       'one place, and walk back to it from anywhere, even from another dimension. It does not '
       'move where you wake after dying.',
       'Everyone starts on the same page. Not everyone turns it.',
       'Keeper',
       'Check the box. The climb starts with iron.'),
     item('minecraft:written_book'), [checkbox()],
     [item_reward(item('qfcommands:lottery_ticket', 1, 1))], [473, 474, 478], 1),
]

# Existing quests that move into Arrival: (qid, x, y, size)
MOVES = [(0, 0, 0, 32), (1, 0, 96, 24), (2, 0, 144, 24), (431, 48, 48, 24), (35, 144, 144, 24),
         (430, 144, 240, 24), (61, 96, 0, 24)]
# What is left of Ch 1, moved up to fill the gap.
CH1_LAYOUT = [(3, 0, 0, 24), (4, 0, 48, 24), (5, 0, 96, 24), (6, 0, 144, 24)]

PREREQS = [  # (qid, expected, new)
    (1, [0], [470]),       # the main column runs through Where You Woke
    (3, [2], [480]),       # Act I opens when the Prologue is done
    (430, [4], [473]),     # Infernal names are a first-night lesson, not an iron-armour one
    (431, [4], [470]),     # choose a class on day one
    (35, [4], [2]),        # the backpack is a day-one craft
]

# Reward changes on moved quests: (qid, old id, old damage, new stack or None, count)
REWARDS = [
    (0, 'minecraft:bed', 0, None, None),                         # the bed moves to 471
    (430, 'minecraft:golden_apple', 0, None, 1),                 # 2 -> 1 golden apple
    (430, BAG, 1, item(BAG), None),                              # Uncommon bag -> Common
    (61, BAG, 1, None, None),                                    # 3 Common + 1 Uncommon ...
    (61, BAG, 0, None, 2),                                       # ... -> 2 Common
]

TEXTS_A = [  # (qid or 'lineN', field, must_contain, new)
    (35, 'desc:8', 'A chest you wear, with opinions.', D(
        'A chest you wear, with plumbing.',
        'An Adventure Backpack holds a chest of items and two tanks of fluid, and you open it on '
        'the move with B. Some skins do extra work: a Bat backpack sees in the dark, a Squid '
        'backpack breathes underwater.',
        'He put lava in the left tank. We stopped lending him backpacks.',
        'Outfitter',
        'Have an Adventure Backpack.')),
    (35, 'name:8', 'Adventure Awaits!', 'A Bag That Remembers'),
    (61, 'desc:8', 'Mobs drop bags.', D(
        'Mobs drop bags. Bags drop excuses to keep fighting.',
        'About one kill in five drops a Loot Bag. Common, Uncommon, Rare, Epic, Legendary: the '
        'colour tells you which. Right-click to open one. Bosses drop them more often, and the '
        'rare colours are worth the detour.',
        'I opened a Common. I got string. I opened another Common. I got hope.',
        'Auditor',
        'Have a Common Loot Bag.')),
    ('line0', 'desc:8', 'The numbered chapters are the climb.', CH1_DESC),
]

# ---------------------------------------------------------------------------
# Part B: the WP-10 writing-pass sample. The nine quests that were Ch 1 at the time of
# the audit, rewritten in the 4.7 voice. Facts fixed on the way: 1 named OpenBlocks
# graves (disabled in this pack); 4 and 6 said "wear it" (the task only checks the
# inventory); 5's "below Y-16 the ores change" is not something the pack does; 6 told
# the player to "open the next chapter".
TEXTS_B = [
    (0, 'desc:8', 'The old chronicle called this CrazyCraft.',
     '§6✦ QUEST FORGE ✦§r\n\n' + D(
         'The sky cracked, and everything on the other side came through.',
         'This is CrazyCraft, rebuilt for a few friends on one server: titans that flatten '
         'forests, heroes\' suits, witches, and a Twilight Forest with a lich in it. The book '
         'keeps the order you should meet them in. Press \' (apostrophe) to open it.\n\n'
         'The climb opens one step at a time, as you earn it. The tabs beside it pay in comfort '
         'and toys, not power. Claim a reward whenever you like; it waits for you.',
         'We wrote it down in the order it tried to kill us.',
         'Chronicler',
         'Claim this to begin.')),
    (1, 'desc:8', 'Wood is the first argument',
     D('Wood is the last argument the forest still loses.',
       'Everything starts as a log: the table, the first tools, the door you will want before '
       'dark. Take more than you think you need. The machete in the reward is for leaves and '
       'vines, not for fights.',
       'He said stone was good enough. A Mutant Zombie filed the rebuttal.',
       'Camp Log',
       'Have 16 logs of any wood.')),
    (2, 'desc:8', 'A table is not furniture.',
     D('The first machine anyone builds. The rest are this, with ambitions.',
       'Presses, altars and reactors all start as a recipe at this table, and nobody memorises '
       'a hundred mods. Hold any item and press R to see how it is made, or U to see what it '
       'makes.',
       'Fifty years and the same four logs. The table outlived the theories.',
       'Workshop',
       'Craft a Crafting Table.')),
    (3, 'desc:8', 'Iron is the first metal',
     D('Iron is the first metal that bites back.',
       'Stone chips and wood splinters. Iron holds an edge long enough to dig for diamonds, and '
       'half the early modded recipes quietly ask for it. You will replace these tools. You '
       'cannot skip them.',
       'Survivor steel. Not special. Just required.',
       'Smith',
       'Have an iron pickaxe, an iron sword and an iron axe.')),
    (4, 'name:8', 'Armor Up!', 'Armor Up'),
    (4, 'desc:8', 'Leather is a suggestion.',
     D('Leather is a suggestion. Iron is a policy.',
       'Infernal mobs and mutants hit through cloth as if it were paper. Put iron in all four '
       'slots before you go underground, and before your first walk through a forest at night.',
       'She said she would run past them. We buried the boots.',
       'Watch',
       'Have a full set of iron armour: helmet, chestplate, leggings and boots.')),
    (430, 'desc:8', 'Some of them come with extra adjectives.',
     D('Some of them come with extra adjectives.',
       'A mob whose nametag reads like a list is an Infernal: more health, extra powers, and '
       'loot worth the swing. The longer the name, the worse the fight. Read it before you '
       'swing, and if it is longer than your arm, come back with friends.',
       "It said '1UP Regenerating Ghastly.' I said no.",
       'Night Watch',
       'Kill an Infernal mob, then check the box. The book takes your word for it.')),
    (5, 'desc:8', 'Diamonds are still the key.',
     D('Diamonds are still the key. The basement just got louder.',
       'Enchanting, the Twilight portal and a dozen recipes you have not met yet all ask for '
       'the same crystal. Deep caves are where the lava is, so carry a water bucket and pour it '
       'before you step: it turns a lake of fire into a floor.',
       'The glow was new. The teeth were not.',
       'Last Survey',
       'Have 16 diamonds.')),
    (431, 'desc:8', 'Level Up! is a second skill tree',
     D('A second skill tree, and nobody hands you the map.',
       'Press L to open Level Up and choose a class: Miner, Warrior, Scout, Farmer and more. '
       'Each one pays back every level you put into it. There is no Book of Unlearning on this '
       'server, so choose the one you will still like in a month.',
       'He picked Freelancer for the points. He still could not punch a Warg.',
       'Trainer',
       'Choose a class, then check the box.')),
    (6, 'desc:8', 'This is the admission ticket.',
     D('The price of admission. Not the ending.',
       'The Twilight Forest, the witches and everything with a proper name expect you in '
       'diamond. Below it you are loot. Keep one diamond back when you craft the set: the '
       'Twilight portal takes one, thrown into a pool ringed with flowers.',
       'Diamond is how the world knows you are serious.',
       'Quartermaster',
       'Have a full set of diamond armour and a diamond sword.')),
]


def holder(book, key):
    if isinstance(key, str) and key.startswith('line'):
        return book.line(int(key[4:])), key
    return book.quest(key), 'q%d' % key


def apply(book, voice=True):
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
    for qid, old, new in PREREQS:
        set_prereqs(log, Q(qid), old, new)
    for qid, old_id, dmg, new, count in REWARDS:
        replace_reward(log, Q(qid), old_id, new, old_damage=dmg, count=count)
    for key, field, must, new in TEXTS_A + (TEXTS_B if voice else []):
        h, where = holder(book, key)
        rewrite_text(log, h, field, must, new, where)
    qb.set_pack_version(log, book, PACK_VERSION)
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--book', help='pack, server or all: apply to the repo books (only once approved). '
                                   'Default: rebuild the review draft from the pack book.')
    ap.add_argument('--skip-voice', action='store_true', help='leave out part B (the Ch 1 writing sample)')
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
        apply(book, voice=not a.skip_voice)
        if not a.dry_run:
            book.save()
            print('wrote', book.path)


if __name__ == '__main__':
    main()
