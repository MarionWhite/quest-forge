# WP-6 writing brief: the act spine

**For:** the writers (the Mac side). **From:** the PC side, which did the data.
**Status:** amended 2026-10-25 to the owner's answers
([decision 0004](../../decisions/0004-prologue-and-act-i.md), `docs/decisions/answers/s001.json`).
The books this describes are `tools/quests/drafts/DefaultQuests.wp5.json` (the Prologue, built
by `tools/quests/patches/wp5_prologue.py`) and `tools/quests/drafts/DefaultQuests.wp6.json` (the
acts, built on it by `tools/quests/patches/wp6_acts.py --decisions docs/decisions/answers/s001.json`).
Nothing is in the shipped books.

Two of the owner's answers change this brief from the ground up:

- **The voice is rejected** (card act1-09, answer C): "I think we need to completely rethink
  the voice because this just reads as a random jumble of words. This isn't a compelling or
  interesting story, and I'd rather do something that doesn't take itself so seriously." The
  audit 4.7 house voice (italic hook, true paragraph, attributed quote, yellow ask) does not
  spread. Everything written in it was taken out of the drafts: a quest that only moved keeps
  the shipped book's words, and every new quest carries a `[WRITE: ...]` placeholder that
  lists the checked facts its text must carry, then the ask line. **The first job is samples
  of a new voice (section 1), not quest text.**
- **There are no parties** (card act1-05 note, and srv-quests = personal progression): "I don't
  want any quest sharing. Everyone has their own quests and their own rewards." Quest 478 You
  and Your Party is gone, nothing says "you and your party", and the credit rule for a shared
  boss fight is in section 4.

Every placeholder says what its text must say. Replace the placeholder; keep the last line (the
ask) unless the task changes, because it states exactly what the task checks. `qb.py text`
lists what is still unwritten
(`py -3.10 -I tools/quests/qb.py text --book tools/quests/drafts/DefaultQuests.wp6.json`), and
refuses a `[WRITE:` in the pack or server book, so nothing unwritten can ship.

## 1. First: three (or four) samples of a voice

The owner wants to see what the writers come up with: "I would like to see what it comes up
with for voice. I want to stay open minded." So this brief does not prescribe a tone. It asks
for samples the owner can choose between on the next Decisions sheet, and nothing is written at
scale until one is chosen.

**Write the same three quests in three different registers**, one register per sample set:

| Quest | What the text has to carry (true facts) | Ask line (what the task checks) |
|---|---|---|
| **1 Punch Some Trees** (Arrival) | Wood is where tools, the table and the door before dark come from. The grave is GraveStones' (the shipped text says OpenBlocks; wrong, that mod's graves are off in this pack). The reward machete is for leaves and vines. | *Have 16 logs.* |
| **473 The First Night** (Arrival) | Zombies come in numbers and walk through an open door; fight from the doorway, step inside under half health. Zombie Pigmen count too. The count is your own (personal progression; say nothing about pets or about who else hit it, section 4). | *Kill 5 zombies.* |
| **481 First Blood** (I: Broken Sky, the Act I finale) | Act I ends on a kill with a name, not a craft. Any one of four counts: a Mutant Skeleton or Mutant Zombie (they roam the overworld), the Wither (three wither skeleton skulls and soul sand from a Nether fortress), or the pirate boss of a ChocolateQuest pirate dungeon. It may speak to friends who fought together (section 4 has the credit rule). Point forward to the Twilight pool: one diamond thrown into water ringed with flowers. | *Kill one of these: a Mutant Skeleton, a Mutant Zombie, the Wither, or the pirate boss of a ChocolateQuest dungeon.* |

Each sample is **3 to 5 sentences** plus the ask line. The three registers below are examples
of how far apart the samples could sit, not a shortlist; take them, swap any, or replace them:

- light and irreverent;
- warm adventure-serial;
- deadpan survival log.

**A fourth sample set in a register of the writers' own choosing is invited**, and the owner
has asked to be surprised. The only things every sample must do: the facts in the table are
true and nothing else is claimed; the ask line is the last line and says what the task checks;
no "you and your party", no "this page", "chapter", "tab" or "Act I" in the prose (the player
sees tab names, not the plan). Colour codes are optional (`§e...§r` for the ask is the book's
convention; the rest is yours).

Hand the samples back as `docs/design/quests/voice-samples.md`, one heading per register, the
three quests under each, with one line per set saying what the register is for and what it
would sound like at Act IV. The PC side puts them on Decisions sheet 2 as one card per set, with
the owner's own words from act1-09 at the top. The owner picks; then section 5 is the work.

## 2. What stays true whatever the voice

These are not tone. They come from the data and the checks, and `qb.py check` enforces the
ones it can.

1. **True facts only.** Every mechanic named is checked in a jar, config or the book. The
   patch docstrings (`wp5_prologue.py`, `wp6_acts.py`) list where each Prologue and Act I fact
   was checked; do the same in the commit message for anything new.
2. **The ask is the last line and states exactly what the task checks.** A hunt task is "Kill
   X"; a checkbox is "Check the box"; a location task is "Enter the Nether"; a retrieval task
   is "Have N X" (it checks the inventory, so never "wear it", "build it" or "craft it" for a
   retrieval). The placeholders carry the right ask already.
3. **No party language.** Not "you and your party", not "your party shares it". "Friends" is
   fine where friends are meant (450 The Overlord now says "Bring friends, a way home, and more
   poppets than seems reasonable").
4. **The finales may speak to friends who fought together.** There is no group mechanic behind
   the word; what the book credits is in section 4.
5. **Meta-structure stays out of the prose**: no "this page", "side tab", "chapter", "the
   spine", and no "Act III" (the finales may name the next act's places: the End, the Knight
   Stronghold). This is inherited from the audit and the owner can overturn it; until then it
   stands because the tab names already carry the numbering.
6. **Tab names are 14 characters or fewer** (GuiHome clips them; `qb.py lint` warns).
7. Paragraphs are blank lines (`\n\n`); `qb.py text` rejects "a" before a vowel, "Beastiary"
   for the tab, double full stops and placeholder words (TODO, TBD).

## 3. The beats: the story spine, tone open

Each act tab's description in the draft is a `[WRITE: ...]` placeholder carrying its beat from
[act-structure section 2](act-structure.md#2-the-beat-of-each-act). The beats are the order
of events and the places, which the data fixes; how they are told is the voice.

| Act | Tab | Beat |
|---|---|---|
| Prologue | `Arrival` | You arrive with nothing, an hour before dark, on a continent where the sky has cracked. One day and one night teach what this world does differently: graves, Level Up classes, sealed tomes, the jukebox, Infernal names, the Weeping Angels under Y 40. It ends when you have walls, food and a way home. |
| I | `I: Broken Sky` | The overworld is no longer only the overworld. Mutants walk the forests, ChocolateQuest's castles hold the ridges, the Nether still burns under all of it. Iron to diamond, then prove you can kill something with a name. |
| II | `II: Old Powers` | The oldest powers answer first. The Twilight Forest (Naga, Lich, Minoshroom, Hydra) and the witches (altars, poppets, circles). Ends when the Hydra is dead and the Circle Talisman is made. The Philosopher's Stone at the Lich is the first taste of ProjectE. |
| III | `III: The Veil` | The walls between worlds thin. HEE's End and its dragon; the far Twilight (Knight Stronghold, Dark Tower, Alpha Yeti, Aurora Palace); Witchery's Spirit World, Dream and Torment; OreSpawn's first contact and the four minibosses before Ultimate gear. |
| IV | `IV: Titans` | The things CrazyCraft is remembered for. Mobzilla, The King, The Queen; the Synapse and the Overlord; Rahovart from the Demonic Soulcube. The Transmutation Table and Dark Matter each behind the titan its recipe needs. |
| Epilogue | `Chronicle` | No new tier, only the edge of the map: the Crystal Dimension, Red Matter, the far Legends worlds, the outskirts past the sea. Pack Master asks for the four act finales. |

## 4. Facts you can rely on (checked in the data)

- **Who a hunt credits.** Stock BetterQuesting credits a kill to the killer, and with parties
  off to nobody else; kills by pets, minions or the environment never count (WP-4, Standard
  Expansion `TaskHunt`). **qf-content is getting damage-based credit**, built by another agent
  on the owner's call of 2026-10-25 (`ops/checkpoints/quests-hunt-credit.md`): everyone who
  damaged the boss gets the hunt credit (a pet's or minion's damage counts for its owner), and
  the killing blow is highlighted in chat. Write the boss texts to that rule ("everyone who
  fought it gets the page", in whatever words), say nothing about who landed the blow, and
  never say that pet kills do not count; the PC side confirms the rule in a trial before any
  boss text ships.
- `WitherBoss` is vanilla's name for the Wither. Wither skeletons are not a subclass (they are
  `Skeleton` with skeletonType 1), so they never count toward 483.
- `chocolateQuest.pirateBoss` is the boss the pirate mob type spawns (`MobPirate.getBoss`); the
  pack's dungeon configs use `mob = pirate` twice. Castles with the default mob type pick a
  boss at random from the big ones (`monking`, `spiderBoss`, `greenDragon`, `giantZombie`,
  `bull`, `slimeBoss`, `turtleBoss`), so 481 names the pirate boss, which is deterministic.
- The Nether is dimension −1; a location task with range −1 completes anywhere in it.
- Fire Resistance potion: `minecraft:potion` damage 8195 (3:00).
- The HEE dragon sheds Dragon Essence for everyone present; 121 accepts the essence or the kill.
- **The jukebox** (qf-content): a blank Record is coal, string and redstone, shapeless (iron,
  gold or diamond in place of coal only change its look); since 2026-10-25 the jukebox itself is
  a vanilla jukebox plus any blank Record, shapeless (`ModRecipes.jukebox()`), as well as 476's
  reward. Right-click searches, sneak-click plays or stops; local files come from the game
  directory's `jukebox/` folder; a blank record used on the jukebox opens the cutter; a pressed
  record handed to a friend plays for them and goes into their library; V opens a record's menu.
- Graves are GraveStones (subaraki), not OpenBlocks (`OpenBlocks.cfg grave=false`). Only the
  owner opens a grave; the look changes every 5 levels; M chooses the design.
- Weeping Angels (`Weeping Angels.cfg`): spawn at Y 0–40, light 8 or less; only a pickaxe
  hurts them; 35% teleport, 10% infection.
- Level Up classes: Miner, Warrior, Artisan, Spelunker, Scout, Farmer, Archaeologist; no Book
  of Unlearning on this server (`levelup.cfg`). L opens it.
- Sealed tomes: right-click opens one into a book; books and Magic Dust are applied by dropping
  them on the target (Magic Dust adds five points to a book's chance).
- The `/home` ticket (qf-commands `HomeAccess`): right-click it and `/sethome` and `/home` are
  yours for good, across dimensions; it does not move the respawn point.
- Keys in the live `options.txt`: `'` quest book, J map, L Level Up, M grave design, B
  backpack, V record menu; R and U are NEI's recipe and usage keys.
- `qb.py tally` by act, best case: Act III hands out 78 diamond-equivalents against a budget of
  72 (8 blocks); every other act is inside its band. Not a writing matter; noted for the owner.

## 5. The quests that need text

Rewards marked **proposal** are new, inside the audit 4.5 band of their act, and wait for the
owner's approval like any balance change. Prerequisites are quest ids. "Must say" is the
placeholder's content: facts, not phrasing.

### 5.1 The Prologue's new quests (WP-5 draft, all placeholders now)

| ID | Teaches | Task | Reward | Prereqs | Must say | Ask |
|---|---|---|---|---|---|---|
| **470 Where You Woke** | where you are; the spawn picker, truthfully in both worlds | checkbox | compass + map | 0 | If the server showed a map of starting points, each was marked with an honest difficulty; otherwise you woke where everyone wakes. Learn the ground before looking for worse. F3 shows coordinates (write them down); J opens the JourneyMap map, which remembers where you walked. | *Check the box once you know where you are.* |
| **471 Four Walls and a Door** | the first night is about walls | have a wooden door + 8 torches | bed | 2 | Dig in or build a box; only "nothing walks in" matters. Mobs spawn in the dark: light the inside and the ground around the door. | *Have a wooden door and 8 torches.* |
| **472 Something Hot** | food | have 10 bread | 4 carrots, 4 potatoes, 4 pumpkin pies | 2 | Plant the seeds grass drops; bake bread before the meat runs out. Food Plus and Food Expansion add hundreds of dishes; U shows what a food goes into, R how it is made. | *Have 10 bread.* |
| **473 The First Night** | the first fight | kill 5 zombies (subtypes on) | wooden shield + Common bag | 471 | Section 1's facts. | *Kill 5 zombies.* |
| **474 When You Die Here** | graves | checkbox | a gravestone block | 473 | Everything goes into a gravestone where you fall; only you can open it; walk back and take it all. You wake at your last bed, not at the grave. JourneyMap marks the death. M picks the design; better ones every five levels. | *Check the box when you know where you will wake up.* |
| **475 Taller Than Your House** | the things not to fight on day one | checkbox | 16 torches + Common bag | 473 | Weeping Angels below Y 40 in the dark: move only unobserved, can teleport you, only a pickaxe hurts them; light mines, keep a pickaxe in the hotbar. Mutants, Lycanites and big OreSpawn creatures walk the overworld; none is a fair fight on day one. | *Check the box. Then stay out of the dark below Y 40 until you have iron.* |
| **476 Bring Your Own Music** | the jukebox | have a blank black Record (coal pressing, damage 0) | 1 QF Jukebox | 2 | Section 4's jukebox facts. Say the jukebox is the reward and also has a recipe (a vanilla jukebox and a blank Record), so a second one is a craft. | *Have a blank black Record (the coal pressing).* |
| **477 Break the Seal** | sealed tomes | hold an enchant book (any NBT) | 2 Magic Dust | 431 | Right-click a tome: a book. Drop the book onto the item. The tooltip gives the chance it takes and the chance it destroys the item: read it first. Magic Dust on a book adds five points. | *Open a Sealed Tome and hold the book it gives you.* |
| **480 Into the Chronicle** | the Prologue ends; the `/home` ticket | checkbox | `/home` lottery ticket | 473 + 474 | Walls, food and a fair idea of what kills people here; next iron, then diamonds, then the Twilight Forest. The ticket (section 4). | *Check the box. The climb starts with iron.* |

The Arrival tab (line 20) and the Ch 1 tab (line 0, which WP-6 renames) are placeholders too.

### 5.2 The acts' new quests (WP-6)

| ID | Tab | Teaches | Task | Reward | Prereqs | Must say | Ask |
|---|---|---|---|---|---|---|---|
| **481 First Blood** | I: Broken Sky | Act I ends on a kill with a name | OR: Mutant Skeleton, Mutant Zombie, `WitherBoss`, `chocolateQuest.pirateBoss` | 1 Uncommon bag + 1 Uncommon tome *(proposal)* | 6 | Section 1's facts. | *Kill one of these: a Mutant Skeleton, a Mutant Zombie, the Wither, or the pirate boss of a ChocolateQuest dungeon.* |
| **482 The Nether** | I: Broken Sky | the first other dimension | be in dimension −1 | 2 Fire Resistance (3:00) + 1 Common bag *(proposal)* | 5 | Portal: 10 obsidian (diamond pickaxe, or cast it in place with lava and water buckets), flint and steel. Fire resistance; do not hit the zombie pigmen. Blaze rods, glowstone, fortresses, and the Wither are why. | *Enter the Nether.* |
| **483 The Wither** | I: Broken Sky | the first vanilla boss | kill `WitherBoss` | 1 Uncommon bag + 8 Bottles o' Enchanting *(proposal)* | 482 | Four soul sand in a T, three wither skeleton skulls on top (wither skeletons walk the fortresses). Spawn it underground or far from the base: it explodes when it wakes and it flies; its skulls wither you. It drops a Nether Star, which a beacon needs. Friends who fight together; section 4's credit rule. | *Kill the Wither.* |
| **484 The Old Powers Answer** | II: Old Powers | the Act II finale | checkbox | 1 Rare bag + 1 Rare tome *(proposal)* | 17 + 105 | The Hydra is dead and the Circle Talisman made. No new task: the kill was counted at 17, the craft at 105. Point forward: the End, the Knight Stronghold, the Dark Tower, the Aurora Palace, the Spirit World, Torment. | *Check the box. The Hydra and the Circle Talisman were the proof.* |
| **485 Beyond the Veil** | III: The Veil | the Act III finale | checkbox | 1 Epic bag + 1 Epic tome *(proposal)* | 121 + 19 + 21 | The dragon, the Snow Queen, the Ultimate Sword. Point forward to the titans: Mobzilla, The King, The Queen, the Synapse and its Overlord, Rahovart. Nothing below Ultimate gear survives what comes next. | *Check the box. The dragon, the Snow Queen and the Ultimate Sword were the proof.* |
| **486 Titanfall** | IV: Titans | the Act IV finale | checkbox | 1 Legendary bag + 1 Legendary tome *(proposal; "Legendary, finales only")* | 24 + 450 + 406 | The Queen, the Overlord's core and Rahovart are dead. What is left: the Crystal Dimension and its armoury, Red Matter, the far Legends worlds, the outskirts past the sea, Pack Master. | *Check the box. The Queen, the Overlord and Rahovart were the proof.* |

### 5.3 Rewritten quests

| ID | Tab | Task | Reward | Prereqs | Must say | Ask |
|---|---|---|---|---|---|---|
| **63 ★ PACK MASTER ★** | Chronicle | checkbox (was 64 Mobzilla Scale Blocks + a Royal sword + 64 Queen Scales) | statue + 1 Legendary bag (was Mjolnir + 64 Lucky Blocks + 64 Epic bags) *(proposal: cosmetic, audit 4.1)* | 480 + 481 + 484 + 485 + 486 | Nothing to bring; the kills were counted. The reward is a trophy, not power. The shipped line "The chronicle is a list. You are the last line." may stay if the voice allows. Keep the `✦ THE CLIMB, FILED` header. | *Check the box. The four act finales were the proof.* |

### 5.4 Tab texts (all placeholders)

| Line | Tab | Must say |
|---|---|---|
| 20 | `Arrival` | the Prologue beat (section 3) |
| 0 | `I: Broken Sky` | the Act I beat |
| 3 | `II: Old Powers` | the Act II beat |
| 14 | `III: The Veil` | the Act III beat |
| 4 | `IV: Titans` | the Act IV beat |
| 21 | `Chronicle` | the Epilogue beat |

### 5.5 Moved quests whose shipped text is stale or wrong

The patches did not touch these words (decision 0004: nothing is rewritten until the voice is
chosen). Once it is, they are the first pass after the new quests, because several state a
fact the pack does not have or an ask the task does not check.

| ID | Now in | Needs | What is wrong or stale |
|---|---|---|---|
| 0 Welcome to Quest Forge | Arrival | — | "Main chapters are the climb. Side pages are hobbies." is meta-structure; it no longer holds the bed (471 does). |
| 1 Punch Some Trees | Arrival | 470 (was 0) | "a grave from OpenBlocks": wrong mod (GraveStones). The task is a retrieval of 16 logs of any wood: *Have 16 logs.* |
| 2 Crafting Station | Arrival | — | "Craft a Crafting Table" but the task is a retrieval: *Have a Crafting Table.* |
| 35 Adventure Awaits! | Arrival | 2 (was 4) | "Tanks and a hose are the next page": meta. The task is a retrieval: *Have an Adventure Backpack.* |
| 61 Loot Bag Basics | Arrival | — | "Open a Loot Bag" but the task checks for a Common bag in the inventory: *Have a Common Loot Bag.* Reward is now 2 Common bags. |
| 430 The Name Was Longer | Arrival | 473 (was 4) | Fine; reward is now 1 golden apple + 1 Common bag. |
| 431 Pick a Class | Arrival | 470 (was 4) | Fine ("pay rent" is the old voice). |
| 3 Better Tools | I: Broken Sky | 480 (was 2) | "Wear the time they buy": the task checks the inventory for an iron pickaxe, sword and axe. "what the book means when it says you have started": meta. |
| 4 Armor Up! | I: Broken Sky | — | "Wear it": retrieval, the task checks the inventory. |
| 5 Diamond Dreams | I: Broken Sky | — | "Below Y-16 the ores change": not something this pack does. |
| 6 Diamond Gear | I: Broken Sky | — | "Then open the next chapter": meta, and wrong: 481 First Blood now stands between diamond and the Twilight pool. Worth one clause. |
| 14 The Pool at Dusk | II: Old Powers | 481 (was 6) | Fine as written. |
| 56 Enhanced End | III: The Veil | 484 (was 17 + 105) | Old marketing voice ("completely overhauls The End!"). |
| 43, 44, 45, 106 (Dark Paths) | III: The Veil | 484 (was 105) | 43: "Finish the Old Ways first. This chapter is still mid-book.": meta. |
| 94, 18, 95, 19 (far Twilight) | III: The Veil | unchanged | 19: "the last of the numbered Twilight lords on this page": meta. |
| 22 Mobzilla | IV: Titans | 485 (was 21) | Fine. |
| 405, 406 Rahovart | IV: Titans (from Bestiary) | unchanged | 405: "The book keeps this page shut until Mobzilla is dead": meta. 406 lost "and your party shares it"; a credit sentence (section 4) can go there once damage credit ships. |
| 450 The Overlord | IV: Titans | unchanged | Now "Bring friends, a way home, and more poppets than seems reasonable." Same credit note as 406. |
| 122, 123 Crystal Dimension | Chronicle | 486 (was 24) | Fine ("designed for players who had already killed the Queen"). |
| 60 Feeling Lucky? | Rewards | 6 (was 0) | Old voice; fine. |

## 6. How to hand text back

Add a `TEXTS` table to the patch that owns the quest (`wp5_prologue.py` for 470–477, 480 and
the Arrival tab; `wp6_acts.py` for 481–486, 63 and the act tabs) in the shape
`(qid, 'desc:8', must_contain, new)` with `rewrite_text`, where `must_contain` is a phrase of
the placeholder, so the draft rebuilds from the decisions and a re-run changes nothing. Editing
the draft's `desc:8` fields by hand works too, but the next rebuild loses it. Then
`py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.wp6.json` must
pass with no `[WRITE:` warning left, and the commit message names where each fact was checked.
