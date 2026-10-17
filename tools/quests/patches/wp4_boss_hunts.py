#!/usr/bin/env python3
"""WP-4 of docs/design/questline-audit.md: boss proofs become hunt and location tasks.

"Bring this drop" proved nothing on a shared server: retrieval never consumes, so one
friend's Naga Scale or Royal Guardian Sword completes the quest for everyone it is
handed to, and several proofs were drops of lesser mobs. A bq_standard:hunt task counts
the kill itself, for every member of the killer's party. Applied to both books (pack and
server). Safe to re-run.

    py -3.10 -I tools/quests/patches/wp4_boss_hunts.py [--book pack|server|all] [--dry-run]

Every hunt target is in tools/quests/entities.json, read from the mod's own registration
code and checked with /summon in a server trial (`qb.py hunt` enforces it).

Kept as an alternative item proof (taskLogic OR), and why:
  94 Knight Phantom: the boss is six separate entities. If one of them dies to anything
     but a player (a pet, a minion, the stronghold), the count stops at five for that
     stronghold for good. The vault chest's Phantom Helm or Plate still proves the fight.
  121 HEE Dragon: one dragon per End fight, and only the killer's party is credited. A
     friend who was not partied, or joins later, could never finish the quest. The fight
     sheds Dragon Essence (HardcoreEnderExpansion:essence@0, DragonRewardManager), which
     can be shared. It replaces the Dragon Egg, of which there is only one.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qb
from qb import item, hunt, location, retrieval, item_reward, choice_reward, set_tasks, edit_text, \
    set_prereqs, add_quest, move_in_line

TF = 'TwilightForest:'
TOME = 'qfcontent:sealed_tome'
BAG = 'lootbags:lootbag'


def R(*stacks):
    """task_key() of a retrieval task: ('bq_standard:retrieval', (id, damage, count), ...)"""
    return ('bq_standard:retrieval',) + tuple(stacks)


# (quest, tasks before (task_key form), tasks after, task logic)
TASKS = [
    (14, [R((TF + 'tile.TFLog', 0, 1))], [location('Twilight Forest', 7)], 'AND'),
    (15, [R((TF + 'item.nagaScale', 0, 5))], [hunt('TwilightForest.Naga')], 'AND'),
    (16, [R((TF + 'item.scepterZombie', 0, 1))], [hunt('TwilightForest.Twilight Lich')], 'AND'),
    (93, [R((TF + 'item.meefStroganoff', 0, 1))], [hunt('TwilightForest.Minoshroom')], 'AND'),
    (17, [R((TF + 'item.fieryBlood', 0, 3))], [hunt('TwilightForest.Hydra')], 'AND'),
    (94, [R((TF + 'item.phantomHelm', 0, 1)), R((TF + 'item.phantomPlate', 0, 1))],
         [hunt('TwilightForest.Knight Phantom', 6),
          retrieval(item(TF + 'item.phantomHelm')), retrieval(item(TF + 'item.phantomPlate'))], 'OR'),
    (18, [R((TF + 'item.fieryTears', 0, 1))], [hunt('TwilightForest.Tower Boss')], 'AND'),
    (95, [R((TF + 'item.alphaFur', 0, 4))], [hunt('TwilightForest.Yeti Boss')], 'AND'),
    (19, [R((TF + 'item.trophy', 4, 1))], [hunt('TwilightForest.Snow Queen')], 'AND'),
    (121, [R(('minecraft:dragon_egg', 0, 1), ('HardcoreEnderExpansion:enderman_head', 0, 1))],
          [hunt('HardcoreEnderExpansion.Dragon'), retrieval(item('HardcoreEnderExpansion:essence'))], 'OR'),
    (22, [R(('OreSpawn:OreSpawn_BlockMobzillaScaleBlock', 0, 5))], [hunt('Mobzilla')], 'AND'),
    (23, [R(('OreSpawn:OreSpawn_Royal', 0, 1))], [hunt('The King')], 'AND'),
    (24, [R(('OreSpawn:OreSpawn_QueenScale', 0, 1))], [hunt('The Queen')], 'AND'),
    (406, [R(('demonmobs:demoncrystal', 0, 1))], [hunt('demonmobs.rahovart')], 'AND'),
    (28, [R(('MutantCreatures:item.skeletonPart', 0, 1))], [hunt('MutantCreatures.MutantSkeleton')], 'AND'),
]

# The "ask" line (and any sentence that described the old proof) must say what the task checks.
TEXTS = [  # (quest, old, new)
    (14, '\n\nTwilight Oak grows only on the other side, so a log of it is the proof you went through.', ''),
    (14, '§eStep through into the Twilight Forest. Cut a Twilight Oak log.§r', '§eStep through into the Twilight Forest.§r'),
    (15, '§eDefeat the Naga and claim its scales as proof of your victory.§r', '§eKill the Naga.§r'),
    (16, '§eDestroy his shields, then strike true.§r', '§eBreak his shields, then kill the Twilight Lich.§r'),
    (93, '§eBring back its Meef Stroganoff - proof you reached the centre and walked out again.§r',
         '§eKill the Minoshroom at the centre of the Labyrinth.§r'),
    (17, '§eClaim its Fiery Blood - liquid flame that never cools.§r', '§eKill the Hydra.§r'),
    (94, '§eBring back the Phantom Helm or the Phantom Plate from the vault chest.§r',
         '§eKill all six Knight Phantoms, or bring back the Phantom Helm or Plate from the vault chest.§r'),
    (18, '§eKill the Ur-Ghast. Bring back a Fiery Tear from the chest it leaves.§r', '§eKill the Ur-Ghast.§r'),
    (95, '§eStrip four Alpha Furs from the beast.§r', '§eKill the Alpha Yeti.§r'),
    (19, 'Her trophy is the proof.', 'Her trophy is for the wall.'),
    (19, '§eDefeat the Snow Queen. Bring back her trophy.§r', '§eKill the Snow Queen.§r'),
    (121, ' And bring an Enderman Head, because you should not be arriving here without having learned that '
          'lesson first.\n\nWhen it falls, the egg is yours.§r',
          '\n\nAs it dies it sheds Dragon Essence, enough for everyone who was there.§r'),
    (121, '§eClaim the Dragon Egg and an Enderman Head.§r',
          '§eKill the dragon, or bring back Dragon Essence from the fight.§r'),
    (22, '§eKill Mobzilla. Bring the scales. The Transmutation Table is listening.§r',
         '§eKill Mobzilla. Keep the scales: the Transmutation Table is listening.§r'),
    (23, 'The Royal Guardian Sword is the proof this pack uses, because the King himself does not drop a tidy '
         'souvenir.',
         'He drops the Royal Guardian Sword with his armour. Keep it: Dark Matter asks for it.'),
    (23, '§eSurvive The King. Hold the Royal Guardian Sword.§r', '§eKill The King.§r'),
    (13, "The King leaves no tidy souvenir. His guardian's sword is the key.",
         "The King drops the Royal Guardian Sword. The sword is the key."),
    (24, '§eKill The Queen. Bring a Queen Scale.§r', '§eKill The Queen.§r'),
    (406, 'Kill him. Bring back a Demon Crystal. That is the receipt. Nothing stops you summoning him early. '
          'That is the trap: diamond is the admission ticket, not the loadout.',
          'Kill him; the kill is the receipt, and your party shares it. Nothing stops you crafting the cube '
          'before Mobzilla. That is the trap: the cube does not check your gear.'),
    (406, '§eRetrieve a Demon Crystal. That means he is down.§r', '§eKill Rahovart.§r'),
    (28, '§eBring back what it drops.§r', '§eKill a Mutant Skeleton.§r'),
]

OVERLORD_DESC = (
    '§oThe Synapse was built around something, and it is still at home.§r\n\n'
    'Place a Synapse Core inside the Synapse and the Overlord wakes. It fights three times: a cocoon, '
    'a body, and the core that ran both. Only the core counts. Bring your party, a way home, and more '
    'poppets than seems reasonable.\n\n'
    '§7"We cracked the shell and cheered. The shell let us." - Keysmith§r\n\n'
    "§eKill the Overlord's core in the Synapse.§r")

MUTANTS = [  # (qid, name, entity, x, y, icon, rewards, desc)
    (451, 'Mutant Creatures: Mutant Zombie', 'MutantCreatures.MutantZombie', 96, 96, item('minecraft:skull', 1, 2),
     [item_reward(item(BAG), item('minecraft:experience_bottle', 8))],
     '§oIt hits the ground and the ground files a complaint.§r\n\n'
     'A Mutant Zombie slams the ground hard enough to throw you, and it brings the dead up with it. Keep '
     'moving sideways, and do not fight it next to anything you built. It is also where the Hulk Hammer '
     'comes from.\n\n'
     '§7"We kept backing up. It kept being closer." - Range Report§r\n\n'
     '§eKill a Mutant Zombie.§r'),
    (452, 'Mutant Creatures: Mutant Creeper', 'MutantCreatures.MutantCreeper', 96, 144,
     item('MutantCreatures:item.creeperShard'),
     [choice_reward(item(TOME), item('minecraft:experience_bottle', 8), item(BAG))],
     '§oA creeper that stopped being polite about it.§r\n\n'
     'It jumps, it charges, and it does not need to reach you to go off. Fight it from range, and pick '
     'ground you do not mind losing.\n\n'
     '§7"It did not hiss. That was worse." - Demolition Survey§r\n\n'
     '§eKill a Mutant Creeper.§r'),
    (453, 'Mutant Creatures: Mutant Enderman', 'MutantCreatures.MutantEnderman', 96, 192,
     item('MutantCreatures:item.endersoulHand'),
     [choice_reward(item(TOME, 1, 1), item('minecraft:ender_pearl', 16))],
     '§oFour arms, and every one of them is holding part of your house.§r\n\n'
     'A Mutant Enderman throws blocks, splits into clones to spoil your count, and is the hardest of the '
     'four. Keep your back to a wall, and do not trust the first one you see.\n\n'
     '§7"It threw the bridge at us. Then it threw the other half." - Survey Crew§r\n\n'
     '§eKill a Mutant Enderman.§r'),
]


def apply(book):
    log = qb.Log(book)
    Q = book.quest
    for qid, old, new, logic in TASKS:
        set_tasks(log, Q(qid), old, new, logic)
    for qid, old, new in TEXTS:
        edit_text(log, Q(qid), 'desc:8', old, new, 'q%d' % qid)

    # The Overlord: the armour WP-2 took off quest 134 (the key to its house) is earned
    # by killing it. Ch 8, after the Synapse key.
    add_quest(log, book, 450, 16, 96, 96, 'TragicMC: The Overlord', OVERLORD_DESC,
              item('TragicMC:overlordHelm'), [hunt('TragicMC.OverlordCore')],
              [choice_reward(item('TragicMC:overlordHelm'), item('TragicMC:overlordPlate'),
                             item('TragicMC:overlordAmulet'))],
              pre=[134], main=1, vis='NORMAL', template=134)

    # Mutants (Gadgets): 28 is now the Mutant Skeleton hunt; the other three branch off it,
    # and the Hulk Hammer follows the Mutant Zombie that drops it.
    for qid, name_, ent, x, y, icon, rw, desc in MUTANTS:
        add_quest(log, book, qid, 5, x, y, name_, desc, icon, [hunt(ent)], rw, pre=[28], template=28)
    set_prereqs(log, Q(29), [28], [451])
    move_in_line(log, book, 5, 29, 144, 96)

    qb.set_pack_version(log, book, 8)
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
