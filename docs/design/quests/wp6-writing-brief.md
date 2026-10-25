# WP-6 writing brief: the act spine

**For:** the writers (the Mac side). **From:** the PC side, which did the data.
**Status:** draft, 2026-10-25. The book this describes is
`tools/quests/drafts/DefaultQuests.wp6.json`, built by `tools/quests/patches/wp6_acts.py`
from the WP-5 draft. Nothing is in the shipped books.

Every quest below carries a `[WRITE: ...]` placeholder in the draft saying what its text must
say. Replace the placeholder; keep the last line (the ask) unless the task changes, because it
states exactly what the task checks. `qb.py text` lists what is still unwritten
(`py -3.10 -I tools/quests/qb.py text --book tools/quests/drafts/DefaultQuests.wp6.json`), and
refuses a `[WRITE:` in the pack or server book, so nothing unwritten can ship.

## 1. The rules (audit 4.7, the review's section 4)

1. **Hook:** one italic line, **15 words or fewer**, about the world, not the book.
2. **Body:** two or three short paragraphs. What it is, why now, and one practical tip that
   saves a life (a Y-level, a key, a weakness). **True facts only**: every mechanic named must
   be checked in a jar, config or the book. The WP-5 patch docstring lists where the Prologue's
   facts were checked; do the same in the commit message.
3. **Quote:** one line, attributed to a role (`- Watch`, `- Keeper`). It can be funny. It does
   not repeat the hook.
4. **Ask:** the last line, in `§e`, **stating exactly what the task checks.** A hunt task is
   "Kill X"; a checkbox is "Check the box"; a location task is "Enter the Nether". Never
   "wear it" or "build it" for a retrieval task.
5. **No meta-structure in prose.** No "this page", "side tab", "the spine", "chapter". Use
   the act's name or say nothing. The finales may name the next act's places (the End, the
   Knight Stronghold), never "Act III".
6. **No marketing voice.** No exclamation marks, no "This mod adds".
7. **"You and your party"** in any text about a group-sized fight (481, 483, 484, 485, 486).
8. Rotate the tics ("suggestion", "opinions", "receipt", "landlord", "paperwork"): at most one
   per tab.

Colour codes: hook `§o...§r`, quote `§7"..." - Role§r`, ask `§e...§r`. Paragraphs are blank
lines (`\n\n`). The draft's placeholders are already laid out in that shape.

## 2. The beats (act-structure section 2): the voice of each act

Each act tab's description in the draft is its beat under a `[WRITE: tab hook]`. Write the
hook, and polish the beat if it reads like a plan rather than a place.

| Act | Tab | Beat |
|---|---|---|
| Prologue | `Arrival` | You arrive with nothing, an hour before dark, on a continent where the sky has cracked. One day and one night teach what this world does differently. It ends when you have walls, food and a party. *(written in WP-5)* |
| I | `I: Broken Sky` | The overworld is no longer only the overworld. Mutants walk the forests, ChocolateQuest's castles hold the ridges, the Nether still burns under all of it. Iron to diamond, then prove you can kill something with a name. |
| II | `II: Old Powers` | The oldest powers answer first. The Twilight Forest (Naga, Lich, Minoshroom, Hydra) and the witches (altars, poppets, circles). Ends when the Hydra is dead and the Circle Talisman is made. The Philosopher's Stone at the Lich is the first taste of ProjectE. |
| III | `III: The Veil` | The walls between worlds thin. HEE's End and its dragon; the far Twilight (Knight Stronghold, Dark Tower, Alpha Yeti, Aurora Palace); Witchery's Spirit World, Dream and Torment; OreSpawn's first contact and the four minibosses before Ultimate gear. |
| IV | `IV: Titans` | The things CrazyCraft is remembered for. Mobzilla, The King, The Queen; the Synapse and the Overlord; Rahovart from the Demonic Soulcube. The Transmutation Table and Dark Matter each behind the titan its recipe needs. |
| Epilogue | `Chronicle` | No new tier, only the edge of the map: the Crystal Dimension, Red Matter, the far Legends worlds, the outskirts past the sea. Pack Master asks for the four act finales. |

Tab names are capped at 14 characters (GuiHome clips them; `qb.py lint` warns).

## 3. The quests that need text

Rewards marked **proposal** are new, inside the audit 4.5 band of their act, and wait for the
owner's approval like any balance change. Prerequisites are quest ids. Decisions are the
Decisions page cards `act1-01` .. `act1-10` (review section 5); a row with no decision column
entry is the same under every answer.

### 3.1 New quests

| ID | Tab | Teaches | Task | Reward | Prerequisites | Must say | Depends on |
|---|---|---|---|---|---|---|---|
| **481 First Blood** | I: Broken Sky | Act I ends on a kill with a name, not a craft | OR: kill a Mutant Skeleton, a Mutant Zombie, the Wither, or a ChocolateQuest pirate boss (`chocolateQuest.pirateBoss`, the boss of the pirate dungeons) | 1 Uncommon loot bag + 1 Uncommon sealed tome *(proposal)* | 6 Diamond Gear | Any one of the four counts; Mutants roam the overworld; the Wither needs three wither skeleton skulls and soul sand from a Nether fortress; the pirate boss sits in ChocolateQuest's pirate dungeons. "You and your party": a kill by any member counts for all. Point forward to the Twilight pool (one diamond, flowers, water). Ask: *Kill one of these: a Mutant Skeleton, a Mutant Zombie, the Wither, or the pirate boss of a ChocolateQuest dungeon.* | — |
| **482 The Nether** | I: Broken Sky | the first other dimension; it is a location task | be anywhere in dimension −1 | 2 Fire Resistance potions (3:00) + 1 Common loot bag *(proposal)* | 5 Diamond Dreams | Portal: 10 obsidian (diamond pickaxe, or cast it in place with lava and water buckets), flint and steel. Tip: fire resistance, and do not hit the zombie pigmen. Why go: blaze rods, glowstone, fortresses, and the Wither. Ask: *Enter the Nether.* | — |
| **483 The Wither** | I: Broken Sky | the first vanilla boss; group fight | kill `WitherBoss` ×1 | 1 Uncommon loot bag + 8 Bottles o' Enchanting *(proposal)* | 482 | Four soul sand in a T, three wither skeleton skulls on top (wither skeletons walk the Nether fortresses). Spawn it underground or far from the base: it explodes when it wakes and it flies; its skulls wither you. It drops a Nether Star, which a beacon needs. "You and your party." Ask: *Kill the Wither.* | — |
| **484 The Old Powers Answer** | II: Old Powers | the Act II finale; no new task | checkbox | 1 Rare loot bag + 1 Rare sealed tome *(proposal)* | 17 Hydra + 105 Circle Talisman | The Hydra is dead and the Circle Talisman made: the oldest powers have answered. The kill was counted at 17 (a hunt credits the whole party) and the craft at 105. Point forward to what thins next: the End, the Knight Stronghold, the Dark Tower, the Aurora Palace, the Spirit World, Torment. Ask: *Check the box. The Hydra and the Circle Talisman were the proof.* | — |
| **485 Beyond the Veil** | III: The Veil | the Act III finale | checkbox | 1 Epic loot bag + 1 Epic sealed tome *(proposal)* | 121 HEE Dragon + 19 Snow Queen + 21 Ultimate Gear | The dragon, the Snow Queen and the Ultimate Sword. Point forward to the titans: Mobzilla, The King, The Queen, the Synapse and its Overlord, Rahovart. Nothing below Ultimate gear survives what comes next. Ask: *Check the box. The dragon, the Snow Queen and the Ultimate Sword were the proof.* | — |
| **486 Titanfall** | IV: Titans | the Act IV finale | checkbox | 1 Legendary loot bag + 1 Legendary sealed tome *(proposal; "Legendary, finales only")* | 24 The Queen + 450 The Overlord + 406 Rahovart | The Queen, the Overlord's core and Rahovart are dead. Point to what is left: the Crystal Dimension and its armoury, Red Matter, the far Legends worlds, the outskirts past the sea, Pack Master. Ask: *Check the box. The Queen, the Overlord and Rahovart were the proof.* | — |

### 3.2 Rewritten quests

| ID | Tab | Teaches | Task | Reward | Prerequisites | Must say | Depends on |
|---|---|---|---|---|---|---|---|
| **63 ★ PACK MASTER ★** | Chronicle | the last page: the four finales converge | checkbox (was: 64 Mobzilla Scale Blocks + a Royal sword + 64 Queen Scales) | 1 statue (`statues:statues.statue`) + 1 Legendary loot bag (was: Mjolnir + 64 Lucky Blocks + 64 Epic bags) *(proposal: cosmetic, audit 4.1)* | 480 + 481 + 484 + 485 + 486 | Nothing to bring; the kills were counted. The reward is a trophy, not power. The Keeper's old quote still fits: "The chronicle is a list. You are the last line." Keep the `✦ THE CLIMB, FILED` header. Ask: *Check the box. The four act finales were the proof.* | — |
| **478 You and Your Party** | Arrival | BQ parties | checkbox | 1 cake | 0 | **One added sentence** at the end of the body: tell a newcomer to finish Arrival before joining a party (a party's completed quests are likely copied to a member who joins; WP-9 confirms). The rest of the text is WP-5's and stays. | `act1-05` A (the draft). B: no change. C: 478 is removed and **480** gets the placeholder instead: teach parties there (open the book, choose Party, invite by name; a kill counts for everyone; one party per friend group, Single Reward off). |
| **480 Into the Chronicle** | Arrival | the climb starts; the `/home` ticket | checkbox | `/home` lottery ticket | 473 + 474 + 478 | Nothing under the recommendation. | `act1-03` B: the reward is a Common loot bag; replace or drop the ticket paragraph (the draft marks it). |
| **476 Bring Your Own Music** | Arrival | the jukebox | have a blank Record | 1 Jukebox | 2 | Nothing under A or B (the recipe is qf-content code, not the book). | `act1-04` C: the reward is a Common loot bag; say in one clause that the jukebox is crafted, not given (the draft marks the sentence). |

### 3.3 Tab texts

| Line | Tab | Must say | Depends on |
|---|---|---|---|
| 0 | `I: Broken Sky` | hook + the Act I beat (in the draft) | — |
| 3 | `II: Old Powers` | hook + the Act II beat | `act1-02` A. Under B the tab is `II: Twilight` and keeps today's Twilight text; `II: Witchery` keeps the Witchery text. |
| 14 | `III: The Veil` | hook + the Act III beat | `act1-02` A. Under B: `III: The End`, `III: Dark Arts` (Dark Paths, renamed to fit 14 characters), `III: OreSpawn` keep their texts; **`III: Twilight` is new**: the far Twilight (Knight Stronghold, Dark Tower, Alpha Yeti, Aurora Palace), opens once the Hydra is dead. |
| 4 | `IV: Titans` | hook + the Act IV beat | `act1-02` A. Under B: `IV: TragicMC` keeps its text; **`IV: OreSpawn` is new**: Mobzilla, The King, The Queen, Rahovart; opens at Beyond the Veil. |
| 21 | `Chronicle` | hook + the Epilogue beat | — |

### 3.4 Moved quests whose text may now be stale (optional pass)

Their words were not changed by the patch; read them once in their new place.

| ID | Now in | Needs | Note |
|---|---|---|---|
| 14 The Pool at Dusk | II: Old Powers | 481 (was 6) | Fine as written. 6 Diamond Gear still says the Twilight portal is next; one named kill now stands between diamond and the pool. Worth one clause in 6 or 481. |
| 56 Enhanced End | III: The Veil | 484 (was 17 + 105) | Old voice ("completely overhauls The End!"); a WP-10 row. The condition is the same two quests through one door. |
| 43, 44, 45, 106 (Dark Paths) | III: The Veil | 484 (was 105) | 43 says "Finish the Old Ways first. This chapter is still mid-book.": meta-structure, a WP-10 row. |
| 94, 18, 95, 19 (far Twilight) | III: The Veil | unchanged (94 needs 17) | 19 says "the last of the numbered Twilight lords on this page": meta-structure. |
| 22 Mobzilla | IV: Titans | 485 (was 21) | Fine. |
| 405, 406 Rahovart | IV: Titans (from Bestiary) | unchanged | 405 says "The book keeps this page shut until Mobzilla is dead": still true, still meta. |
| 122, 123 Crystal Dimension | Chronicle | 486 (was 24) | Fine ("designed for players who had already killed the Queen"). |
| 60 Feeling Lucky? | Rewards | 6 (was 0) | Old voice; fine. |
| 472, 475, 476, 477, 61 | Workshop / Danger Zone / Rewards | unchanged | Only under `act1-06` B (lean 12). Their texts still read as Prologue lessons; 475 in Danger Zone fits, 472 and 477 in Workshop are placeholders for the WP-7 Kitchen and Quest Forge tabs. |

## 4. Facts you can rely on (checked in the data)

- A hunt kill counts for every member of the killer's party; kills by pets, minions or the
  environment do not count (WP-4, Standard Expansion `TaskHunt`).
- `WitherBoss` is vanilla's name for the Wither. Wither skeletons are not a subclass (they are
  `Skeleton` with skeletonType 1), so they never count toward 483.
- `chocolateQuest.pirateBoss` is the boss the pirate mob type spawns (`MobPirate.getBoss`); the
  pack's dungeon configs use `mob = pirate` twice. Castles with the default mob type pick a
  boss at random from the big ones (`monking`, `spiderBoss`, `greenDragon`, `giantZombie`,
  `bull`, `slimeBoss`, `turtleBoss`), so 481 names the pirate boss, which is deterministic.
  WP-7 Castles can add the others; all are in `tools/quests/entities.json`.
- The Nether is dimension −1; a location task with range −1 completes anywhere in it.
- Fire Resistance potion: `minecraft:potion` damage 8195 (3:00).
- The HEE dragon sheds Dragon Essence for everyone present; 121 accepts the essence or the kill.
- `qb.py tally` by act, best case: Act III hands out 78 diamond-equivalents against a budget of
  72 (8 blocks); every other act is inside its band. Not a writing matter; noted for the owner.

## 5. How to hand text back

Edit the draft's `desc:8` fields, or (better) add a `TEXTS` table to
`tools/quests/patches/wp6_acts.py` in the shape WP-5's `TEXTS_B` uses
(`(qid, 'desc:8', must_contain, new)` with `rewrite_text`), so the draft rebuilds from the
decisions. Then `py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.wp6.json`
must pass with no `[WRITE:` warning left.
