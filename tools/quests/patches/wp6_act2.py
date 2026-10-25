#!/usr/bin/env python3
"""WP-6 of docs/design/questline-audit.md: Act II, "The Old Powers". DRAFT FOR REVIEW.

Act II is the Twilight Forest (the Naga, the Lich, the Minoshroom, the Hydra) and the
witches' overworld (Witchery, all of Ch 4). Today they are two tabs, "Ch 3: Twilight" and
"Ch 4: Witchery". This patch makes them one tab, "II: Old Powers", that ends in a finale,
484 The Old Powers Answer, and rewrites the texts of the act in the house voice (audit 4.7).
The plan is docs/design/quests/act-structure.md; the decisions it builds on are in
docs/design/quests/review-act2-2026-10-25.md.

    py -3.10 -I tools/quests/patches/wp6_act2.py                  # rebuild both drafts
    py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.act2.json
    py -3.10 -I tools/quests/patches/wp6_act2.py --book all       # ONCE APPROVED: both repo books

With no --book, the pack book is copied to drafts/DefaultQuests.wp5.json with the WP-5
patch applied (wp5_prologue.apply), and that draft is copied to drafts/DefaultQuests.act2.json
with this patch applied. The repo books are not touched. Safe to re-run: every helper reports
"already" when its edit is in, so a re-run changes no bytes.

The choices the draft makes, each one a constant or a table row below:
  - Act I's finale 481 First Blood does not exist yet, so 14 Pool at Dusk keeps 6 Diamond
    Gear. Set ACT1_FINALE to 481 once it does; ACT1_FALLBACK is used until then.
  - The Far Twilight bosses 94, 18, 95 and 19 are Act III. They stay in a holding tab,
    "Far Twilight", because the chapter order (qb.py path) reads every numbered tab as a link
    in one chain, and a numbered tab for them would sit between II and Dark Paths. The tab
    gets a number when Act III is built.
  - 56 Enhanced End needs 484 instead of 17 + 105 (REPOINT). That passes qb.py path, because
    484 needs everything 56 needed and more. 43, 44, 45 and 106 (Dark Paths) stay on 105: the
    same repoint on them makes Dark Paths and The End open at the same point, and qb.py path
    fails ("can open before"). They move to 484 with Act III, when the two tabs are one.

What it does (review-act2-2026-10-25.md has the full list and the rewards):
  - adds line 21 "II: Old Powers" at tab 3, UNLOCKED, with the act text;
  - moves 14, 15, 16, 93, 17 (Twilight) and 9, 96, 97, 10, 98, 99, 100, 104, 101, 102, 103,
    105 (Witchery) into it, Twilight in a column at x 0 and Witchery in two at x 144 and 192,
    and adds 487, 488 and 484 (three new quests; 484 is the finale);
  - retires line 2 "Ch 4: Witchery" (now empty) and renames line 3 "Ch 3: Twilight" to
    "Far Twilight", holding 94, 18, 95 and 19;
  - 16 The Lich King needs 488 The Shimmering Scale (a Naga Scale, retrieval) instead of 15;
  - 484 needs 17 The Hydra + 105 The Circle Talisman, one checkbox, and the act's reward;
  - rewrites the texts of all 17 Act II quests and renames 10 (its task is clay jars);
  - 16 loses its Nether Star choice for a Rare loot bag (reward change, review decision 6).

Facts the texts rely on, and where each was checked (the review lists what is only [likely]):
  Twilight names   TwilightForest-2.4.3.jar assets/twilightforest/lang/en_US.lang: entity
                   names (Naga, Twilight Lich, Minoshroom, Hydra), item names (Naga Scale
                   Tunic, Magic Map, Hydra Chop, Shimmering Scale is the achievement name).
  Twilight texts   the same lang file's achievements: "Slay the naga in its forest courtyard";
                   "Obtain a naga scale, allowing you to overcome the barrier magic surrounding
                   the Lich's tower" (Shimmering Scale); "Slay the lich at the top of his
                   tower"; "Acquire all three scepters of power"; "The meat-and-mushroom stew
                   in the labyrinth makes you feel ready to enter the Fire Swamp" (Mighty
                   Stroganoff); "Find the Mazebreaker pick in the secret labyrinth vault";
                   "Chow down on some overpowered hydra meat when your food bar is empty"
                   (Massive Chops).
  Portal           BlockTFPortal.class references Blocks.water; the pool-and-flowers recipe and
                   the diamond are not in any string [likely].
  Witchery names   witchery-1.7.10 jar, assets/witchery/lang/en_US.lang: Altar, Witches Oven,
                   Kettle, Distillery, Poppet Shelf, Taglock Kit, Circle Talisman, Ritual,
                   Infernal and Otherwhere Chalk, Fume Funnel, Filtered Fume Funnel, the
                   seed and herb names.
  Witchery books   the in-game book strings in the same lang file: "Altars provide power" (kettle),
                   "Ensure the distillery is near to an Altar to get power" and "Place the
                   items into the distillery along with the required number of clay jars";
                   "Place Clay Jars into the oven when cooking to collect the fumes"; food and
                   wood give Foul Fume; Oak gives Exhale of the Horned One, Birch Breath of the
                   Goddess, Rowan Whiff of Magic; "Tall grass yields seeds"; "Harvest at night,
                   lest it waken and scream" (Mandrake); "It grows in tilled earth in stages";
                   "The artichoke grows on still water"; the circle sizes 7x7, 11x11, 15x15;
                   "Draw circles ... with a heart glyph at the centre"; "Infernal (red) small
                   and/or medium circles ... significantly reduce altar power costs, but at an
                   increased risk of side-effects"; "Ritual (white) small and/or medium circles
                   ... moderately reduce power costs and eliminate side-effects"; purple chalk for
                   transposition; "Death is almost always assured" (infusions).
  Altar power      witchery javap, BlockAltar$TileEntityAltar: the power sources are saplings
                   (treeSapling), logs (logWood), leaves (treeLeaves), grass, dirt and tall grass.
  Ingredient meta witchery javap, ItemGeneral: clayJar 27, foulFume 28, mutandis 14,
                   mandrakeRoot 22, whiffOfMagic 34, wolfsbane 156 (the same names the book uses).
  Poppet shelf     witchery javap, BlockPoppetShelf: it holds a ForgeChunkManager chunk ticket,
                   so the shelf's chunk stays loaded.
  Poppet types     witchery lang: protectEarth, protectWater, protectStarvation, protectFire,
                   protectTool, protectDeath (the names of the poppet types).
  Hunts            kills by the party count for everyone (WP-4, TaskHunt, verified). Every hunt
                   target is in entities.json.
  Items            every item id is in registry.json (qb.py ids).
  Trophy meta      TwilightForest item.trophy meta 0 = Hydra Trophy: the lang order (hydra first)
                   and 19 Snow Queen using meta 4 [likely]; check in the server trial.
"""
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qb
import wp5_prologue as wp5
from qb import item, retrieval, checkbox, item_reward, choice_reward, add_quest, add_line, \
    move_to_line, set_prereqs, replace_reward, rewrite_text, edit_text, set_visibility, \
    set_pack_version
from wp5_prologue import D

DRAFT_WP5 = wp5.DRAFT
DRAFT_ACT2 = os.path.join(qb.DRAFTS, 'DefaultQuests.act2.json')
PACK_VERSION = 10
BAG = 'lootbags:lootbag'

# -- the act -----------------------------------------------------------------------------
ACT_LINE = 21           # new line id; free in both books
ACT_ORDER = 3           # takes the tab slot of "Ch 3: Twilight"
ACT_NAME = 'II: Old Powers'
FAR_LINE = 3            # "Ch 3: Twilight" becomes "Far Twilight" (Act III bosses, held)
RETIRED_LINE = 2        # "Ch 4: Witchery": empty after the move, removed

# The finale of Act I: 14 needs it once it exists. Until then the entry stays at 6.
ACT1_FINALE = 481
ACT1_FALLBACK = 6

# Repoints to 484 that keep qb.py path passing: 56 The End. Dark Paths (43, 44, 45, 106)
# would open with The End and fail the path check, so they wait for Act III. Rows are
# (qid, old prereqs, new prereqs).
REPOINT = [
    (56, [17, 105], [484]),
]

ACT_DESC = (
    '§o"The oldest powers answer first."§r\n\n'
    'Through a pool ringed with flowers lies the Twilight Forest, where a Naga, a lich and a '
    'hydra stand between you and the deeper dark. In the overworld the witches teach altars, '
    'chalk and poppets. The act ends when the Hydra is dead and the Circle Talisman is made.')

FAR_DESC = (
    '§o"The far Twilight opens one door at a time."§r\n\n'
    'The Knight Stronghold, the Ur-Ghast\'s Dark Tower and the Alpha Yeti\'s glacier, in that '
    'order. Each one opens after the one before it, and the first opens after the Hydra.')

# Positions in the act tab. Twilight is the column at x 0; Witchery is two columns at x 144
# and 192; the finale sits between the two roads.
MOVES = [  # (qid, x, y, size): quests already in the book, moved in
    (14, 0, 0, 24), (15, 0, 48, 24), (16, 0, 144, 24), (93, 0, 192, 24), (17, 0, 240, 24),
    (9, 144, 0, 24), (96, 192, 0, 24), (97, 144, 48, 24), (10, 192, 48, 24),
    (98, 144, 96, 24), (99, 192, 96, 24), (100, 144, 144, 24), (104, 192, 144, 24),
    (101, 144, 192, 24), (102, 192, 192, 24), (103, 144, 240, 24), (105, 192, 240, 24),
]

# Quests the act adds. (qid, x, y, size, name, desc, icon, tasks, rewards, prereqs, main)
NEW = [
    (488, 0, 96, 24, 'Twilight: The Shimmering Scale',
     D('The Lich\'s tower is wrapped in barrier magic. One scale gets you through.',
       'Carry a Naga Scale and the barrier around the Lich\'s tower lets you through. Keep one '
       'in your hotbar on the way up, and a spare in your pack for the next trip.',
       'It shimmers like a bad idea, and then it lets you in.',
       'Tower Notes',
       'Have a Naga Scale in your inventory.'),
     item('TwilightForest:item.nagaScale'), [retrieval(item('TwilightForest:item.nagaScale'))],
     [item_reward(item('minecraft:cooked_beef', 8))], [15], 1),

    (487, 240, 0, 24, 'Witchery: Mandrake at Night',
     D('Pull it at night. Pulled in daylight, it screams.',
       'A mandrake grows from seed in tilled soil, in stages like any crop. Its root wakes when '
       'it is pulled, and the Witchery book is clear that the time to pull it is at night, while '
       'it is still asleep. Pull it with nobody next to you.',
       'It looked like my uncle. We did not discuss it.',
       'Hedge Witch',
       'Have one Mandrake Root.'),
     item('witchery:ingredient', 1, 22), [retrieval(item('witchery:ingredient', 1, 22))],
     [item_reward(item('witchery:ingredient', 4, 14))], [96], 0),

    (484, 96, 288, 32, 'The Old Powers Answer',
     D('The Hydra is dead, the circle is bound, and the forest is listening.',
       'The Hydra and the Circle Talisman were the two things this act was built around: the '
       'forest\'s oldest guard, and the coven\'s last ordinary craft. With both in your pack, '
       'the roads ahead are the End and the dark paths the coven warned you about.\n\n'
       'The reward is a choice: the Hydra Trophy for the wall, three Rare loot bags, or two Rare '
       'sealed tomes.',
       'Turn the page. The next one has more teeth.',
       'Chronicler',
       'Check the box. The Hydra and the Circle Talisman quests above it do the checking.'),
     item('TwilightForest:item.trophy', 1, 0), [checkbox()],
     [choice_reward(item('TwilightForest:item.trophy', 1, 0), item(BAG, 3, 2),
                    item('qfcontent:sealed_tome', 2, 2))],
     [17, 105], 1),
]

PREREQS = [  # (qid, expected, new): 14 is handled through ACT1 below
    (16, [15], [488]),     # the Lich's tower is past the barrier, and the scale is the key
]

# Reward changes on quests that stay: (qid, old id, old damage, new stack or None, count)
REWARDS = [
    (16, 'minecraft:nether_star', 0, item(BAG, 1, 2), None),   # Wither's drop out of Act II
]

# Texts. (qid, field, must_contain, new). `must_contain` is a phrase of the text the patch
# expects to find; once rewritten, the hook identifies it on a re-run.
TEXTS = [
    (14, 'desc:8', 'Four flowers, still water',
     D('Flowers, still water, and one diamond you will not get back.',
       'Dig a pool of water in open grass and ring its edge with flowers. Throw a diamond into '
       'the water and step back. The lightning is the forest checking who you are. It does not '
       'check twice, so stay out of the water until it has gone.',
       'I thought the flash meant it worked. It meant swim.',
       'Pathfinder',
       'Be in the Twilight Forest. The task checks the dimension, nothing else.')),
    (15, 'desc:8', 'The Naga guards the threshold',
     D('The Naga waits in its forest courtyard, and it is the first real fight.',
       'Fight it with your party, out in the open, and keep your health above half before you go '
       'in. Naga Scales drop from it, and the scale is the key to the Lich\'s tower.',
       'The courtyard walls aren\'t to keep the Naga in. They are to keep the fight fair. Outside '
       'those walls, it is just faster.',
       'Hunter\'s Warning',
       'Kill one Naga. A kill by anyone in your party counts for all of you.')),
    (16, 'desc:8', 'Once a mortal wizard',
     D('He wanted to live forever, and the forest took him at his word.',
       'The Twilight Lich lives at the top of his tower, behind the barrier a Naga Scale gets you '
       'past. He summons minions, so clear them at the foot of the stairs with your '
       'party, then climb.\n\n'
       'Three scepters of power exist, and the reward lets you take one. Choose the one you will '
       'use.',
       'The Lich doesn\'t fight fair - why should you?',
       'Tower Raider',
       'Kill the Twilight Lich. A kill by anyone in your party counts for all of you.')),
    (93, 'desc:8', 'Beneath the Labyrinth',
     D('The labyrinth has a centre, and the thing in it is half minotaur.',
       'The Minoshroom waits at the centre of the Labyrinth, behind corridors long enough to wear '
       'a party down before it arrives. The stew in the labyrinth is the meal that makes you ready '
       'for the Fire Swamp.\n\n'
       'The labyrinth has a secret vault, and the Mazebreaker pick is inside it.',
       'Everyone maps the maze on the way in. Nobody remembers the map on the way out.',
       'Labyrinth Cartographer',
       'Kill the Minoshroom. A kill by anyone in your party counts for all of you.')),
    (17, 'desc:8', 'The Hydra predates',
     D('Three heads, one lair, and a meal you will want afterwards.',
       'The Hydra sleeps in its lair beneath the forest. It has three heads, and it does '
       'not fight one at a time. Fight it with your party, so someone can always take the hits.\n\n'
       'Hydra Chop is overpowered food when your food bar is empty. The reward has eight of them, '
       'so keep the spare for a hard night.',
       'You cannot kill all three heads at once. Be patient, and be methodical.',
       'Sole Survivor',
       'Kill the Hydra. A kill by anyone in your party counts for all of you.')),
    (9, 'desc:8', 'When the barriers fell',
     D('The witches were waiting. They want to know what you grow.',
       'An altar takes its power from living things around it: saplings, logs, leaves, grass and '
       'tall grass all feed it. Put it among trees and fields, not on bare stone. The kettle, the '
       'distillery and the circles all draw on that power, and most of the craft starts here.\n\n'
       'The Witches Oven keeps the smoke as well as the food. Build the three together before you '
       'go any further.',
       'The altar does not create power. It channels it.',
       'Coven Elder',
       'Have an Altar, a Cauldron and a Witches Oven in your inventory.')),
    (96, 'desc:8', 'Every brew starts in the dirt',
     D('Every brew starts in the dirt, and most of the dirt is weeds.',
       'Witchery hides its two starter herbs in tall grass. Break enough of it and Belladonna Seeds '
       'and Mandrake Seeds turn up. Plant them on tilled soil; they grow in stages.\n\n'
       'The Witchery book says to harvest Mandrake at night, because a root pulled up in daylight '
       'wakes and screams.',
       'Two weeds from a field of weeds. That is the whole beginning.',
       'Hedge Witch',
       'Have 4 Belladonna Seeds and 4 Mandrake Seeds.')),
    (97, 'desc:8', 'The altar gives you power',
     D('The altar gives you power. Chalk tells it where to spend it.',
       'A circle starts with a heart glyph in its centre and grows outward, 7 by 7, 11 by 11 or 15 '
       'by 15 blocks. Ritual chalk is the white one, for everyday rites. Small and medium white '
       'circles cut the power a rite costs and stop its side effects.\n\n'
       'Keep the ground inside the circle clear of blocks, or the centre will not take. An altar is '
       'often needed for power, so draw the circle within its reach.',
       'People think the hard part is the ritual. The hard part is finding nine flat blocks in a '
       'hilly world.',
       'Circle Drawer',
       'Have one Ritual Chalk.')),
    (10, 'desc:8', 'Mutandis is how the garden starts lying',
     D('The oven keeps its smoke, if you give it somewhere to put it.',
       'Put Clay Jars in the Witches Oven while it cooks. Food and wood make Foul Fume, and the jars '
       'hold it. Cook a sapling and the smoke is stranger: Rowan gives Whiff of Magic, Oak gives '
       'Exhale of the Horned One.\n\n'
       'The oven cooks a little faster than a furnace, but it cannot smelt ore.',
       'It smelled like a mistake. It grew like a plan.',
       'Coven Ledger',
       'Have 4 Clay Jars.')),
    (98, 'desc:8', 'A cauldron is a serious commitment',
     D('A cauldron is a commitment. A kettle is a question.',
       'A kettle needs water inside it and heat underneath. Throw the ingredients in and watch the '
       'brew. When a brew needs power, an altar nearby supplies it.\n\n'
       'Fill the finished brew into an empty glass bottle. The Witchery book is blunt about '
       'infusions: death is almost always assured if you get them wrong.',
       'Small pot, small mistakes. That is the entire argument for starting here.',
       'Kitchen Coven',
       'Have a Kettle.')),
    (99, 'desc:8', 'An ordinary furnace burns things',
     D('An ordinary furnace burns things. This one keeps the smoke.',
       'Cook food or wood in the Witches Oven and it leaves a residue: Foul Fume, or the sapling '
       'fumes the book lists by tree. Fume Funnels stacked on top of the oven catch the smoke, and '
       'a Filtered Fume Funnel catches more.\n\n'
       'The residues are what the rest of the craft spends, so set up the funnels before you start '
       'the rites.',
       'I ran that oven for a week before someone told me about the chimney. A week of good smoke, '
       'straight out the window.',
       'Apprentice, furious',
       'Have 2 Fume Funnels and 1 Filtered Fume Funnel.')),
    (100, 'desc:8', 'The oven breaks things down by burning',
     D('The oven breaks things down. The distillery takes its time.',
       'A distillery needs power from an altar nearby. Put the items in with the clay jars it asks '
       'for, then wait: distilling takes time, and it works while you are doing something else.\n\n'
       'The result is a set of distillates, the finer parts of what you fed it. Build it beside the '
       'oven.',
       'Everything in this craft is just taking one thing apart carefully enough to find two things '
       'inside it.',
       'Still Keeper',
       'Have a Distillery.')),
    (104, 'desc:8', 'Belladonna and Mandrake grow in any field',
     D('Mutandis argues with reality, and reality sometimes loses.',
       'Sprinkle Mutandis on a plant and it can become another species. Mutandis Extremis does the '
       'same job harder, and on grass it makes mycelium. Snowbell grows in tilled earth; the Water '
       'Artichoke grows on still water. Both start from tall grass seeds.\n\n'
       'Four seeds are the whole task: Wormwood, Wolfsbane, Snowbell and Water Artichoke. Expect to '
       'waste some powder getting them.',
       'Throw it at a dandelion enough times and eventually the dandelion gives up and becomes '
       'something useful.',
       'Field Notes of a Frustrated Botanist',
       'Have one seed each of Wormwood, Wolfsbane, Snowbell and Water Artichoke.')),
    (101, 'desc:8', 'A poppet is a little cloth figure',
     D('A poppet is a cloth figure with your name in it.',
       'Take a taglock with a Taglock Kit, and a poppet is bound to you. Each poppet guards '
       'against a different harm: earth, water, hunger, fire, tools and death each have their own. '
       'When the harm comes, the poppet takes it and breaks.\n\n'
       'A Poppet Shelf keeps poppets together, and its chunk stays loaded while you are away, so the '
       'poppets on it keep working.',
       'I have died eleven times since Tuesday. The shelf has died eleven times since Tuesday. I have '
       'died zero times since Tuesday.',
       'Cautious Witch',
       'Have a Taglock Kit, a Poppet and a Poppet Shelf.')),
    (102, 'desc:8', 'Two knives and a cup',
     D('Two knives and a cup. Every tradition ends up here eventually.',
       'The Arthana is the ritual blade: a working tool, and a poor weapon in a fight. The '
       'Boline is its curved companion, for plants. The Chalice holds liquid at the heart of a circle, '
       'and several rites will not start without one.\n\n'
       'The Circle Talisman needs a finished ritual, so craft all three before you go on.',
       'The blade is not for the goat. The blade is for the rope holding the goat. Please stop asking '
       'about the goat.',
       'Coven Elder',
       'Have an Arthana, a Boline and a Chalice.')),
    (103, 'desc:8', 'Ritual Chalk handles the polite rites',
     D('These two chalks cost more, and they ask less politely.',
       'Infernal chalk is red. Small and medium red circles cut the altar power a rite costs, at the '
       'price of a higher risk of side effects. Otherwhere chalk is purple, and the transposing rites '
       'use it to reach a bound waystone.\n\n'
       'Mixing colours is allowed. A white and a red circle together let you choose how much power to '
       'spend and how much risk to take.',
       'Ritual chalk asks. Infernal chalk demands. Otherwhere chalk simply opens the door and steps back.',
       'Margery of the Long Silence',
       'Have one Infernal Chalk and one Otherwhere Chalk.')),
    (105, 'desc:8', 'The great weakness of circle magic',
     D('Circles do not travel. This talisman lets them.',
       'Perform the Rite of Binding over a finished circle and it is pulled into the talisman. The '
       'talisman comes in small, medium or large to match the circle, and ritual, otherwhere and '
       'infernal circles can all be bound.\n\n'
       'This is the last ordinary craft this act asks for.',
       'She drew it once, in a barn, in 1604. She has been redrawing that same barn ever since.',
       'On the Talisman',
       'Have a Circle Talisman.')),
]

NAMES = [  # (qid, field, old, new)
    (10, 'name:8', 'Witchery: First Brews', 'Witchery: Jars for the Oven'),
]


def retire_line(log, book, lid):
    """Remove a quest line that holds no quests any more."""
    key = '%d:10' % lid
    lines = book.data['questLines:9']
    if key not in lines:
        log('line %d: already retired' % lid)
        return
    if lines[key]['quests:9']:
        raise SystemExit('line %d still holds %d quests; not retiring it' % (lid, len(lines[key]['quests:9'])))
    log('line %d %s: retired (empty)' % (lid, qb.strip(book.line_name(lid))))
    del lines[key]


def set_size(log, book, line_id, qid, size):
    for e in book.line(line_id)['quests:9'].values():
        if e['id:3'] == qid and e['sizeX:3'] != size:
            log('q%d size: %d -> %d' % (qid, e['sizeX:3'], size))
            e['sizeX:3'] = e['sizeY:3'] = size


def apply(book, voice=True):
    """WP-5 (the Prologue) and then the act: what a repo book gets with --book."""
    wp5.apply(book, voice=voice)
    return apply_act2(book)


def apply_act2(book):
    """The act only; the book must already carry WP-5."""
    log = qb.Log(book)
    Q = book.quest
    add_line(log, book, ACT_LINE, ACT_ORDER, ACT_NAME, ACT_DESC, item('witchery:circletalisman'),
             vis='UNLOCKED', template=FAR_LINE)
    for qid, x, y, size, name_, desc, icon, task_list, reward_list, pre, main in NEW:
        add_quest(log, book, qid, ACT_LINE, x, y, name_, desc, icon, task_list, reward_list, pre,
                  main=main, vis='NORMAL', template=15)
        set_size(log, book, ACT_LINE, qid, size)
    for qid, x, y, size in MOVES:
        move_to_line(log, book, qid, ACT_LINE, x, y, size)
    retire_line(log, book, RETIRED_LINE)
    far = book.line(FAR_LINE)
    edit_text(log, far, 'name:8', 'Ch 3: Twilight', 'Far Twilight', 'line %d' % FAR_LINE)
    rewrite_text(log, far, 'desc:8', 'The Twilight Forest predates our world.', FAR_DESC,
                 'line %d' % FAR_LINE)
    set_visibility(log, far, 'UNLOCKED', 'line %d' % FAR_LINE)
    if book.has(ACT1_FINALE):
        entry = [ACT1_FINALE]
    else:
        entry = [ACT1_FALLBACK]
        log('q14: Act I finale %d is not in the book; entry stays at %d' % (ACT1_FINALE, ACT1_FALLBACK))
    set_prereqs(log, Q(14), [ACT1_FALLBACK], entry)
    for qid, old, new in PREREQS:
        set_prereqs(log, Q(qid), old, new)
    for qid, old, new in REPOINT:
        set_prereqs(log, Q(qid), old, new)
    for qid, old_id, dmg, new, count in REWARDS:
        replace_reward(log, Q(qid), old_id, new, old_damage=dmg, count=count)
    for qid, field, old, new in NAMES:
        edit_text(log, Q(qid), field, old, new, 'q%d' % qid)
    for qid, field, must, new in TEXTS:
        rewrite_text(log, Q(qid), field, must, new, 'q%d' % qid)
    set_pack_version(log, book, PACK_VERSION)
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--book', help='pack, server or all: apply WP-5 and WP-6 to the repo books '
                                   '(only once approved). Default: rebuild both drafts from the pack book.')
    ap.add_argument('--dry-run', action='store_true', help='print the log; write nothing')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if a.book:
        for book in qb.books_for(a.book):
            print('==', book.label)
            apply(book)
            if not a.dry_run:
                book.save()
                print('wrote', book.path)
        return
    os.makedirs(qb.DRAFTS, exist_ok=True)
    # The WP-5 draft is rebuilt from the pack book, then the act is built on a copy of it.
    src = qb.BOOKS['pack']
    if not a.dry_run:
        shutil.copyfile(src, DRAFT_WP5)
    w5 = qb.load(DRAFT_WP5 if not a.dry_run else 'pack')
    print('== WP-5 draft')
    wp5.apply(w5, voice=True)
    if not a.dry_run:
        w5.save()
        print('wrote', DRAFT_WP5)
        shutil.copyfile(DRAFT_WP5, DRAFT_ACT2)
        act = qb.load(DRAFT_ACT2)
    else:
        act = w5
    print('== act II draft')
    apply_act2(act)
    if not a.dry_run:
        act.save()
        print('wrote', DRAFT_ACT2)


if __name__ == '__main__':
    main()
