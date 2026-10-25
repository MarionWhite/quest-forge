# The four-act spine

Status: **draft for the author's review, 2026-10-19.** Nothing here is in the shipped book.
The Prologue (WP-5) exists as a draft book, `tools/quests/drafts/DefaultQuests.wp5.json`. The
acts (WP-6) are built as a draft on top of it, `tools/quests/drafts/DefaultQuests.wp6.json`, by
`tools/quests/patches/wp6_acts.py` (2026-10-25), parameterised by the decisions in
[review-2026-10-19.md](review-2026-10-19.md); its texts are placeholders for the writers
([wp6-writing-brief.md](wp6-writing-brief.md)).

This turns section 4.1 of the [questline audit](../questline-audit.md) into a plan that matches
the book as WP-3 and WP-4 left it. Quest IDs are kept; quests move between tabs and gain
prerequisites, and a handful of new quests join chapters together. Tags follow the audit:
**[verified]** checked in a jar, config or the book; **[likely]**; **[guess]**.

---

## 1. The spine at a glance

| Act | Tab (14 chars max) | Tier | Where it happens | Built from | Opens at | Finale (the gate to the next act) | Target time **[guess]** |
|---|---|---|---|---|---|---|---|
| Prologue | `Arrival` | T0 | The overworld around your spawn point | New, plus 0, 1, 2, 430, 431, 35, 61 | first login | **480 Into the Chronicle**: 473 First Night + 474 graves + 478 party | 20–30 min |
| I | `I: Broken Sky` | T0→T1 | Overworld, the Nether | Ch 1 (3, 4, 5, 6), new Nether and Wither quests | 480 | **481 First Blood**: 6 Diamond Gear, then one kill from a list (Mutant, ChocolateQuest boss, the Wither) | 2–3 h |
| II | `II: Old Powers` | T1→T2 | Twilight Forest (dim 7), the witches' overworld | Ch 3 up to the Hydra, all of Ch 4 Witchery | 481 | **484 The Old Powers Answer**: 17 Hydra + 105 Circle Talisman | ≈5 h |
| III | `III: The Veil` | T2 | The End (HEE, dim 1), Witchery's Spirit World, Dream and Torment (−39, −37, −38), the far Twilight biomes, OreSpawn's first dimensions | Ch 6 The End, Ch 5 Dark Paths, the rest of Ch 3, Ch 7 up to Ultimate Gear | 484 | **485 Beyond the Veil**: 121 HEE Dragon + 19 Snow Queen + 21 Ultimate Gear | ≈8 h |
| IV | `IV: Titans` | T3 | Wherever the titans stand; TragicMC's Synapse (3) and Collision (2) | Ch 7 from Mobzilla, all of Ch 8 TragicMC, 405/406 Rahovart | 485 | **486 Titanfall**: 24 The Queen + 450 The Overlord + 406 Rahovart | 10 h+ |
| Epilogue | `Chronicle` | T4 | The Crystal Dimension (84), Legends' far worlds, the outskirts beyond the sea | 122, 123, 34 Red Matter, 63 Pack Master (rewritten), ProjectE post-gate (WP-7) | 486 | **63 Pack Master**: the four act finales | open-ended |

The order is the one WP-3 already enforces (`qb.py path`): Twilight, then Witchery, then the
End and Dark Paths, then OreSpawn, then TragicMC. The acts add three things the data lacks:
a **finale quest per act that needs more than one thing** (today only 56 and 105 do), a
**Prologue** before the diamond wall, and a **name and a beat** for each stage, so a player
always knows which story they are in.

### How the finales are built

BetterQuesting 3.0.328 has one logic setting for a quest's prerequisites (AND or OR) and one
for its tasks. A finale like "diamond gear, *and* any one of three kills" therefore puts the
AND in the prerequisites and the OR in the tasks:

- **481 First Blood**: prerequisite 6 Diamond Gear; tasks (OR): hunt `MutantCreatures.MutantSkeleton`,
  `MutantCreatures.MutantZombie` [verified, `entities.json`], `WitherBoss`, or a ChocolateQuest
  boss [both to be checked with `/qfcensus find`, as WP-4 did].
- **484, 485, 486**: AND prerequisites on the boss quests, one checkbox task ("Turn the page"),
  and the act's best reward. The kill was already counted by the boss quest's hunt task, which
  credits the whole party [verified, WP-4].

Each finale then becomes the only prerequisite that opens the next act:
14 Pool at Dusk needs 481 (not 6); 56 Enhanced End and the Dark Paths entries need 484 (not
17 + 105); 22 Mobzilla needs 485 (not 21). That is four `set_prereqs` calls, not a rewrite.

---

## 2. The beat of each act

**Prologue: Arrival.** You arrive with nothing, an hour before dark, somewhere on a continent
where the sky has cracked. One day and one night teach what this world does differently:
gravestones, parties, Level Up classes, sealed tomes, Infernal names and the Weeping Angels
under Y 40. It ends when you have walls, food and a party.

**Act I: Broken Sky.** The overworld is no longer only the overworld. Mutant Creatures walk
the forests, ChocolateQuest's castles hold the ridges, and the Nether still burns under all
of it. You climb from iron to diamond and prove you can kill something with a name.

**Act II: Old Powers.** The oldest powers answer first. Through a flower-ringed pool lies the
Twilight Forest, where the Naga, the Twilight Lich, the Minoshroom and the Hydra guard the
way deeper. In the overworld the witches teach altars, poppets and circles, and the act ends
when the Hydra is dead and the Circle Talisman is made. The Philosopher's Stone, at the Lich,
is the first taste of ProjectE.

**Act III: The Veil.** The walls between worlds thin. Hardcore Ender Expansion's End, its
Endstone Temple and a dragon far harder than vanilla's. The far Twilight: the Knight Stronghold,
the Ur-Ghast's Dark Tower, the Alpha Yeti and the Snow Queen's Aurora Palace. Witchery's
Spirit World, Dream and Torment. OreSpawn makes first contact, and the Mantis, Basilisk,
Emperor Scorpion and Kraken stand between you and Ultimate gear.

**Act IV: Titans.** The things CrazyCraft is remembered for. Mobzilla, The King and The Queen
from OreSpawn; TragicMC's Synapse and the Overlord at its core; Rahovart, summoned with
Lycanites' Demonic Soulcube. The Transmutation Table and Dark Matter come on the way, each
behind the titan its recipe needs (`crazycraft_gating.zs`).

**Epilogue: Chronicle.** No new tier, only the edge of the map: the Crystal Dimension and its
armoury, Red Matter, the far Legends worlds (Speed Force, Wakanda, Quantum Realm, Tatooine
and the rest of `docs/survey/dimension-names.tsv`), and the outskirts past the sea, which
[decision 0003](../../decisions/0003-designed-world.md) makes the hardest content in the game.
Pack Master asks for the four act finales.

---

## 3. What moves where

Every quest keeps its ID. "Prereq change" lists only the edges that change.

| From (today) | Quests | To | Prereq change |
|---|---|---|---|
| Ch 1 Start | 0, 1, 2, 430, 431 | **Arrival** (done in the WP-5 draft) | 1: 0 → 470. 430: 4 → 473. 431: 4 → 470 |
| Ch 1 Start | 3, 4, 5, 6 | **I: Broken Sky** | 3: 2 → 480 (in the WP-5 draft) |
| Exploration | 35 Adventure Backpack | **Arrival** (WP-5 draft) | 4 → 2 |
| Rewards | 61 Loot Bag Basics | **Arrival** (WP-5 draft) | none |
| — | 482 The Nether (new, location dim −1), 483 The Wither (new, hunt), 481 First Blood (new) | **I** | 481 needs 6 |
| Ch 3 Twilight | 14, 15, 16, 93, 17 | **II: Old Powers** | 14: 6 → 481 |
| Ch 4 Witchery | 9, 96, 97, 10, 98, 99, 100, 104, 101, 102, 103, 105 | **II** | none (9 stays at 15 Naga) |
| — | 484 The Old Powers Answer (new) | **II** | needs 17 + 105 |
| Ch 6 The End | 56, 110–121 | **III: The Veil** | 56: 17 + 105 → 484 |
| Ch 5 Dark Paths | 43, 109, 44, 45, 108, 106, 107 | **III** | 43, 44, 45, 106: 105 → 484 |
| Ch 3 Twilight | 94, 18, 95, 19 | **III** | none (94 stays at 17) |
| Ch 7 OreSpawn | 20, 433, 74, 77, 78, 79, 21 | **III** | none (20 stays at 114 Endstone Temple) |
| — | 485 Beyond the Veil (new) | **III** | needs 121 + 19 + 21 |
| Ch 7 OreSpawn | 22, 23, 24 | **IV: Titans** | 22: 21 → 485 |
| Ch 8 TragicMC | 58, 131–140, 450 | **IV** | none (58 stays at 22 Mobzilla) |
| Bestiary | 405, 406 Rahovart | **IV** | none (405 already needs 22) |
| — | 486 Titanfall (new) | **IV** | needs 24 + 450 + 406 |
| Ch 7 OreSpawn | 122, 123 Crystal Dimension and Armoury | **Chronicle** | 122: 24 → 486 |
| Rewards | 63 Pack Master | **Chronicle** | 24 → 480 + 481 + 484 + 485 + 486; task and reward rewritten (audit 4.3) |
| Ch 9 ProjectE | 11, 12, 13, 34 | stays a **ladder** tab, `ProjectE` | none: each rung already opens at its boss |
| Rewards | 60 Feeling Lucky?, 80 Dungeon Delver, 62 Trophy Collector | side tabs (section 5) | 60: 0 → 6 (a crafted Lucky Block costs 2 diamonds and 2 emeralds [verified, progression audit 2.2]) |

**Why TragicMC stays whole in Act IV.** Audit 4.1 put TragicMC's Nether and End keys in
Act III. In the data, 135 Keys of Nether and End comes *after* 134, the Synapse key, and WP-3
opened the chapter at Mobzilla on purpose ("after the first titan"). Splitting it would mean
reordering five quests to save one; the Act III finale uses Ultimate Gear instead.

**New IDs.** 470–478 and 480 are the Prologue (in the draft). 479 is kept free next to them.
481–486 are reserved for the act gates above; 487–499 for whatever WP-6 needs next. All are
free in both books.

---

## 4. The boss gates, act by act

| Act | Bosses that gate the act | Task today | Still to do |
|---|---|---|---|
| Prologue | none (5 zombies on the first night) | hunt `Zombie` (new, in the draft) | confirm `Zombie` with `/qfcensus find` (vanilla name, not yet run in a trial) |
| I | Mutant Skeleton or Zombie, a ChocolateQuest boss, the Wither | 28, 451 are hunts [verified] | `WitherBoss` and one CQ boss name, checked the WP-4 way; the Nether needs dim −1 in `entities.json` |
| II | Naga, Twilight Lich, Minoshroom, Hydra | hunts since WP-4 [verified] | none |
| III | Knight Phantom, Ur-Ghast, Alpha Yeti, Snow Queen; HEE Dragon; Mantis, Basilisk, Emperor Scorpion, Kraken | TF and the dragon are hunts; the OreSpawn minibosses still ask for a drop | hunts for 74, 77, 78, 79 (names already verified, WP-4 notes) |
| IV | Mobzilla, The King, The Queen, the Overlord, Rahovart | all hunts [verified] | none |
| Epilogue | none new; the Crystal Dimension's own mobs | retrieval | location task on dim 84 for 122 |

---

## 5. Side chapters

Side tabs hang off the act that makes them sensible, and pay in **utility and flavour, never
the next act's power** (audit 4.5). "Opens at" is the quest that unlocks the tab's first entry.

| Side tab | Hangs off | Opens at | Built from | Work package |
|---|---|---|---|---|
| `Base` | Prologue | 2 Crafting Station | Ch 2 as it is (drops the "Ch 2:" number) | WP-6 |
| `Workshop` | Prologue | 2 / 3 / 6 | as it is | — |
| `Pets` | Prologue | roots | 55 → about 12 family quests | WP-8 |
| `Kitchen` | Prologue | 472 Something Hot | Food Plus and Food Expansion (437 items, one quest today) | WP-7 |
| `Gadgets` | Act I | 4 Armor Up | as it is; Mutants (28, 451–453) also feed 481 First Blood; add Morph and Transformers | WP-7 |
| `Castles` | Act I | 4 | ChocolateQuest 440–444 out of Exploration, plus its bosses as hunts | WP-7 |
| `Dungeons` | Act I | 6 | 80 Dungeon Delver; Roguelike and Doomlike by unique loot (the location task cannot see mod structures [verified, world research]) | WP-7 |
| `Exploration` | Act I | 4 / 6 | what remains: ships, Soul Shards, SecurityCraft, the hang glider | — |
| `Engineering` | Act I | 5 Diamond Dreams | Railcraft and War Machines merged, MCHeli expanded | WP-7 |
| `Quest Forge` | Act I | 476 Bring Your Own Music | the pack's own content past the Prologue: record tiers, Record Case, JBL, Tower Speaker, Ward Scroll, Forge Block | WP-7 |
| `Heroes` | Act I | roots, then tiered | Legends suits by power: street-level in Act I, powered in Act II, cosmic in Act III **[guess on suit power: WP-8 measures it first]**; Legends worlds as location quests | WP-8 |
| `Bestiary` | Act I | 6 | Lycanites by family (arctic, desert, inferno, jungle, mountain, plains, shadow, swamp, freshwater, saltwater), taming, soulstones. 405/406 Rahovart move to Act IV | WP-7 |
| `Jungle` | Act II | 484 | Welcome to the Jungle through the Lost World (dim −42), which 421 promises | WP-7 |
| `Danger Zone` | Act II | 6 | TARDIS, Weeping Angels, Pandora's Box | — |
| `ProjectE` | ladder | 16 Lich | as it is, plus the post-gate collectors and condensers | WP-7 |
| `Discovery` | none (hidden) | roots, `COMPLETED` | arrivals in dimensions and biomes (`docs/survey/biome-ids.tsv`) | WP-D1 |
| `Server Firsts` | none | roots, `GLOBAL` | "the first party to kill Mobzilla", with a server-wide announcement | WP-9 |
| `Secrets` | none | as it is | stays the last tab (`qb.py lint` enforces it) | — |

Line visibility follows WP-3: side tabs `ALWAYS`, each act's tab `UNLOCKED`, so an act is a
rumour until its first quest is unlocked.

---

## 6. Parties and multiplayer

The pack is for a few friends on one online-mode server, and the most common new player is a
friend who joins mid-campaign. What the book can rely on, and what it still has to check:

| | Status |
|---|---|
| A hunt kill counts for every member of the killer's party | **[verified]** Standard Expansion `TaskHunt`, `ParticipantInfo.ALL_UUIDS` (WP-4) |
| Kills by pets, minions or the environment do not count | **[verified]** WP-4 |
| Retrieval never consumes (`consume=0` everywhere), so one item proof can be handed round | **[verified]**; why WP-4 moved boss proofs to hunts |
| Party members share quest completion | **[likely]**; WP-9 two-account test |
| "Single Reward" off means each member claims their own reward | **[likely]**; WP-9 |
| A friend who joins a party inherits its completed quests | **[likely]**; WP-9. **This matters for the Prologue** (review doc, decision 5) |

Design rules:

1. **The Prologue and Act I are personal and fast.** They teach systems and carry no kill that
   needs a group. A late friend can be caught up in an evening.
2. **Every act finale is a convergence of hunts**, so a boss the party fought together opens
   the next act for all of it. No finale asks for an item that exists once per world (the
   Dragon Egg problem, already fixed in 121 with Dragon Essence as the shared proof).
3. **Say "you and your party"** in any text about a group-sized fight (audit 4.7).
4. **One party per friend group, Single Reward off**, taught in 478 You and Your Party.
5. **Server-wide firsts** are their own `GLOBAL` tab (WP-9), with a command reward announcing
   the party that did it. These are the stories friends retell.
6. **Travel is earned.** The `/home` ticket at the end of the Prologue (review doc, decision 3)
   is the one shortcut handed out; dimension tickets stay inside their dimensions
   (`Unlockables.java`: "the command can never skip the quest").

---

## 7. How it fits the world plan

[Decision 0003](../../decisions/0003-designed-world.md) gives the overworld a hand-designed,
pregenerated continent, an Ark-style spawn picker with a difficulty per spawn point, and RWG
outskirts past the sea that are the hardest content. The continent draft v4
(`docs/design/world/continent-v4.yaml`) has tier 1 and tier 2 spawn points and "a T3 zone in
sight of every T1 spawn".

- **Prologue**: written for both worlds. 470 Where You Woke says that a map of starting points,
  if the server showed one, marked each with an honest difficulty, and otherwise you woke where
  everyone wakes. It is true today and after the picker ships.
- **Acts I and II** live in the tier 1 and tier 2 regions and their dimensions.
- **Act III and IV** send the party to the tier 3 zones and across the sea.
- **Discovery** (WP-D1) is how the painted biomes earn quests, by biome ID, once the continent
  is fixed. No quest names a region: they name the biome and the structure (Knight Stronghold,
  Aurora Palace), never an invented place name.

---

## 8. What WP-6 has to change in the tooling

- `qb.py path` finds chapters by the name pattern `Ch N:`. Act tabs (`I: Broken Sky`) need
  the pattern to accept a roman numeral, with Arrival as act 0 and Chronicle after IV.
  `SIDE_CHAPTERS` and `LADDER_CHAPTERS` move to tab names.
- `qb.py tally` should total by act, against the budget in audit 4.5.
- Tab names stay at 14 characters or fewer (`lint` warns; GuiHome clips them).
- `entities.json` gains `WitherBoss`, one ChocolateQuest boss and dimension −1, each checked
  in a server trial with `/qfcensus find` before any quest uses it. **Done 2026-10-25**, all of
  the above: `WitherBoss`, the twelve `chocolateQuest.*` bosses (481 uses `pirateBoss`, the
  deterministic one) and dimension −1 are in `entities.json`, checked in the WP-6 trial.
