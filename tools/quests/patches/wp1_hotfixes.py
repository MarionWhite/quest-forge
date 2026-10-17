#!/usr/bin/env python3
"""WP-1 of docs/design/questline-audit.md: hotfixes that do not change the design.

Applies to both books (pack and server). Safe to re-run: every step checks the
state it expects and reports "already" when the edit is in.

    py -3.10 -I tools/quests/patches/wp1_hotfixes.py [--book pack|server|all] [--dry-run]
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qb
from qb import item, replace_reward, replace_task_item, set_icon, edit_text, rewrite_text

PACK_VERSION = 6
TOME = 'qfcontent:sealed_tome'   # meta 0-4 = Common..Legendary (ench/Rarity.java)


def apply(book):
    log = qb.Log(book)
    Q = book.quest

    # -- broken quests ---------------------------------------------------
    # 63 PACK MASTER: 64 Royal Guardian Swords cannot be carried (unstackable, 36 slots).
    for t in qb.tasks(Q(63)):
        for s in qb.stacks_of(t):
            if s['id:8'] == 'OreSpawn:OreSpawn_Royal' and s['Count:3'] != 1:
                log('q63 task: OreSpawn:OreSpawn_Royal x%d -> x1' % s['Count:3'])
                s['Count:3'] = 1
    edit_text(log, Q(63), 'desc:8',
              'Bring stacks of Mobzilla scale blocks, Royal Guardian proof, and Queen Scales.',
              'Bring a stack of Mobzilla Scale Blocks, a stack of Queen Scales, and one Royal Guardian Sword.',
              'q63')

    # 80 Dungeon Delver: a mob spawner cannot be picked up as an item in survival.
    replace_task_item(log, Q(80), 'minecraft:mob_spawner', None)
    edit_text(log, Q(80), 'desc:8', 'Gather dungeon loot as proof of your delve!',
              'Bring back 64 Mossy Cobblestone from the dungeon walls.', 'q80')

    # 39 Steam Power: machine.alpha@5 is the Smoker; the Solid Fueled Firebox is machine.beta@5.
    replace_task_item(log, Q(39), 'Railcraft:machine.alpha', item('Railcraft:machine.beta', 1, 5), old_damage=5)
    set_icon(log, Q(39), item('Railcraft:machine.beta', 1, 5))

    # 431 Pick a Class: levelup.cfg disables the Talisman and the Unlearning Book, so both
    # ids are unregistered and BQ shows placeholders.
    replace_reward(log, Q(431), 'levelup:xpTalisman', item(TOME, 1, 0))
    set_icon(log, Q(431), item('minecraft:experience_bottle'))
    edit_text(log, Q(431), 'desc:8',
              'The Book of Unlearning is there if you hate the first choice.',
              'This build has no Book of Unlearning, so pick the class you will still like next week.',
              'q431')

    # 300 Hall of Heroes: legends:superDex is not registered.
    replace_reward(log, Q(300), 'legends:superDex', None)

    # -- creative-only rewards ---------------------------------------------
    replace_reward(log, Q(140), 'TragicMC:swordOfJustice', item('TragicMC:celestialAegis'))
    replace_reward(log, Q(144), 'TragicMC:bowOfJustice', item('TragicMC:celestialLongbow'))
    replace_reward(log, Q(141), 'witchery:infinityegg', item(TOME, 1, 3))

    # -- Twilight boss proofs (retrieval of the boss's own drop; WP-4 makes them hunts) --
    # 14: the portal quest asked for a Naga Scale, i.e. the next quest's proof.
    q = Q(14)
    replace_task_item(log, q, 'TwilightForest:item.nagaScale', item('TwilightForest:tile.TFLog', 1, 0))
    set_icon(log, q, item('TwilightForest:tile.TFLog', 1, 0))
    edit_text(log, q, 'name:8', 'Twilight Forest: Portal Creation', 'Twilight: The Pool at Dusk', 'q14')
    rewrite_text(log, q, 'desc:8', 'Dig a 2x2 water pool',
              '§d✦ THE TWILIGHT REALM ✦§r\n\n'
              '§oFour flowers, still water, and one diamond you will never get back.§r\n\n'
              'Dig a two-by-two pool in open grass and ring every edge with flowers. Any kind will do. '
              'Throw a diamond in and step away from the water. The lightning is the forest checking who '
              'you are. It does not check twice.\n\n'
              'Twilight Oak grows only on the other side, so a log of it is the proof you went through.\n\n'
              '§7"I thought the flash meant it worked. It meant swim." - Pathfinder§r\n\n'
              '§eStep through into the Twilight Forest. Cut a Twilight Oak log.§r', 'q14')

    # 94 Knight Phantom: Knightmetal also comes from the goblins outside. The vault chest
    # the last phantom leaves always holds a Phantom Helm or Plate (TFTreasure.stronghold_boss).
    q = Q(94)
    ts = qb.tasks(q)
    if len(ts) == 1 and any(s['id:8'] == 'TwilightForest:item.knightMetal' for s in qb.stacks_of(ts[0])):
        helm = ts[0]
        plate = dict(helm)
        qb.set_stacks(helm, 'requiredItems:9', [item('TwilightForest:item.phantomHelm')])
        qb.set_stacks(plate, 'requiredItems:9', [item('TwilightForest:item.phantomPlate')])
        plate['index:3'] = 1
        q['tasks:9'] = {'0:10': helm, '1:10': plate}
        qb.props(q)['taskLogic:8'] = 'OR'
        log('q94 tasks: knightMetal x8 -> phantomHelm OR phantomPlate')
    else:
        log('q94 tasks: already edited')
    set_icon(log, q, item('TwilightForest:item.phantomHelm'))
    edit_text(log, q, 'desc:8', 'Claim eight Knightmetal Ingots from the stronghold.',
              'Bring back the Phantom Helm or the Phantom Plate from the vault chest.', 'q94',
              superseded_by='Kill all six Knight Phantoms, or bring back')  # WP-4

    # 18 Ur-Ghast: Carminite also drops from the tower's lesser ghasts. Fiery Tears come
    # only from the Ur-Ghast's own treasure chest (TFTreasure.darktower_boss).
    q = Q(18)
    replace_task_item(log, q, 'TwilightForest:item.carminite', item('TwilightForest:item.fieryTears', 1, 0))
    set_icon(log, q, item('TwilightForest:item.fieryTears'))
    # The trophy option is already in that chest and part-fills Trophy Collector (62).
    replace_reward(log, q, 'TwilightForest:item.trophy', item(TOME, 1, 2), old_damage=3)
    edit_text(log, q, 'desc:8', 'Kill the Ur-Ghast. Bring back what it drops.',
              'Kill the Ur-Ghast. Bring back a Fiery Tear from the chest it leaves.', 'q18',
              superseded_by='§eKill the Ur-Ghast.§r')  # WP-4

    # 95 Alpha Yeti asked for Arctic Fur (ordinary Yetis). The Alpha drops 6-11 Alpha Fur.
    q = Q(95)
    replace_task_item(log, q, 'TwilightForest:item.arcticFur', item('TwilightForest:item.alphaFur', 4, 0))
    set_icon(log, q, item('TwilightForest:item.alphaFur'))
    edit_text(log, q, 'desc:8', 'Strip eight Arctic Furs from the beast.',
              'Strip four Alpha Furs from the beast.', 'q95',
              superseded_by='§eKill the Alpha Yeti.§r')  # WP-4

    # 19 Snow Queen asked for Alpha Fur (the Yeti's). She always drops her trophy (meta 4).
    q = Q(19)
    replace_task_item(log, q, 'TwilightForest:item.alphaFur', item('TwilightForest:item.trophy', 1, 4))
    set_icon(log, q, item('TwilightForest:item.trophy', 1, 4))
    replace_reward(log, q, 'TwilightForest:item.trophy', item(TOME, 1, 2), old_damage=4)
    edit_text(log, q, 'desc:8', 'Alpha Yeti Fur is the proof.', 'Her trophy is the proof.', 'q19',
              superseded_by='Her trophy is for the wall.')  # WP-4
    edit_text(log, q, 'desc:8', '§eDefeat the Snow Queen.§r',
              '§eDefeat the Snow Queen. Bring back her trophy.§r', 'q19',
              superseded_by='§eKill the Snow Queen.§r')  # WP-4

    # 62 Trophy Collector: "all trophies", but it skipped the Snow Queen's.
    q = Q(62)
    t = qb.tasks(q)[0]
    have = list(qb.stacks_of(t))
    if not any(s['id:8'] == 'TwilightForest:item.trophy' and s['Damage:2'] == 4 for s in have):
        qb.set_stacks(t, 'requiredItems:9', have + [item('TwilightForest:item.trophy', 1, 4)])
        log('q62 task: + TwilightForest:item.trophy@4 (Snow Queen)')

    # -- rewards that complete the next quest -----------------------------
    replace_reward(log, Q(33), 'mcheli:fuel', None)                      # -> 434 asks for fuel
    replace_reward(log, Q(401), 'forestmobs:wargtreat', item('minecraft:name_tag'))      # -> 402
    replace_reward(log, Q(402), 'lycanitesmobs:soulstone', item('minecraft:lead', 2))    # -> 403
    replace_reward(log, Q(403), 'lycanitesmobs:soulkey', item('minecraft:experience_bottle', 8))  # -> 404
    # 52 asked for the Clipboard that Crafting Station (2) hands out; its text asks for a shelf.
    q = Q(52)
    replace_task_item(log, q, 'BiblioCraft:item.BiblioClipboard', item('BiblioCraft:BiblioShelf', 1, 32767))
    set_icon(log, q, item('BiblioCraft:BiblioShelf'))
    edit_text(log, q, 'desc:8', 'Craft a BiblioCraft shelf or stand.', 'Craft a BiblioCraft Shelf, any wood.', 'q52')

    # -- text that contradicts the data -----------------------------------
    rewrite_text(log, Q(13), 'desc:8', 'requires King Scales',
              '§5[UNLOCKED BY DEFEATING THE KING]§r\n\n'
              '§oThe King leaves no tidy souvenir. His guardian\'s sword is the key.§r\n\n'
              'The Dark Matter recipe asks for the Royal Guardian Sword and hands it back. '
              'One kill opens the recipe for good; the sword is never spent. Everything above this line '
              'of alchemy is built from Dark Matter, so spend it like it cost a titan.\n\n'
              '§7"Heavier than it looks. It looks heavy." - Alchemist§r\n\n'
              '§eCraft Dark Matter.§r', 'q13')
    rewrite_text(log, Q(49), 'desc:8', 'Kill a mob and collect its hat item',
              '§oEvery mob out there is wearing something. You can keep it.§r\n\n'
              'Kill a mob and its hat joins your collection. Press H to open the hat menu and wear one. '
              'A Hat Stand is where the good ones wait while you are wearing something sensible.\n\n'
              '§7"He kept the creeper hat on the stand. Nobody stood near it." - Haberdasher§r\n\n'
              '§eCraft a Hat Stand.§r', 'q49')
    rewrite_text(log, Q(57), 'desc:8', 'Craft a Fryer',
              '§oA grill is the first argument for cooking anything twice.§r\n\n'
              'Food Plus and Food Expansion add hundreds of dishes, and most of them start on a grill. '
              'Better food is more saturation, and saturation is what keeps you standing in a long fight.\n\n'
              '§7"I came for the sushi. The burgers kept me alive." - Mess Hall§r\n\n'
              '§eCraft a Grill.§r', 'q57')
    edit_text(log, Q(300), 'desc:8', '§oWorkshop tab. Capes are optional.', '§oCapes are optional.', 'q300')
    edit_text(log, Q(406), 'desc:8',
              'He is late-game on purpose — diamond is the admission ticket, not the loadout.',
              'Nothing stops you summoning him early. That is the trap: diamond is the admission ticket, '
              'not the loadout.', 'q406',
              superseded_by='Nothing stops you crafting the cube before Mobzilla.')  # WP-4
    edit_text(log, Q(421), 'desc:8',
              'The Lost World portal is later, and it wants the ceremonial kit — this page is only the reading.',
              'The Lost World portal wants the ceremonial kit, and nobody in the Chronicle has filed that '
              'trip yet. This is only the reading.', 'q421')
    pets = [l for l in book.lines if qb.strip(l['properties:10']['betterquesting:10']['name:8']) == 'Pets'][0]
    edit_text(log, pets, 'desc:8', '§oWorkshop tab. Pocket creatures', '§oPocket creatures', 'line Pets')

    # -- typos ------------------------------------------------------------------
    # The tab is the Bestiary. Lycanites' own GUI really is spelled "Beastiary", so text
    # that points at that GUI says "Lycanites' Beastiary".
    beasts = book.line(19)
    edit_text(log, beasts, 'name:8', 'Beastiary', 'Bestiary', 'line 19')
    edit_text(log, beasts, 'desc:8', 'Open the Beastiary from Controls. Bind the key.',
              "Lycanites' Beastiary has its own key. Bind it in Controls.", 'line 19')
    edit_text(log, book.line(0), 'desc:8', 'The Beastiary is not a hobby.', 'The Bestiary is not a hobby.', 'line 0')
    edit_text(log, Q(4), 'desc:8', 'The Beastiary and the jungle', 'The Bestiary and the jungle', 'q4')
    edit_text(log, Q(401), 'desc:8', 'then open the Beastiary (the key',
              "then open Lycanites' Beastiary (the key", 'q401')
    for qid in (46, 47, 64, 90, 91, 92, 194, 195, 204):
        q = Q(qid)
        d = qb.props(q)['desc:8']
        m = re.search(r'Retrieve a ([AEIOU])', d)
        if m:
            edit_text(log, q, 'desc:8', m.group(0), 'Retrieve an ' + m.group(1), 'q%d' % qid)

    # -- version ------------------------------------------------------------
    s = book.settings
    if s['pack_version:3'] < PACK_VERSION:
        log('pack_version %d -> %d' % (s['pack_version:3'], PACK_VERSION))
        s['pack_version:3'] = PACK_VERSION
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
