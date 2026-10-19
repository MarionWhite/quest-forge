# Questline audit

Status: **WP-0 to WP-4 done (2026-10-17); see [section 6](#6-implementation-log).** WP-5 onward
are still proposals for the author to review. The audit itself was written 2026-10-16 against
`pack/config/betterquesting/DefaultQuests.json` (SHA-1 `a4ec0775…`). That file is byte-identical
to the live instance's copy and to the friends' server copy (`C:\qfs\friends`), so everything below
describes what players actually see.

Who this is for: the pack author, who decides what the book should feel like, and the agents
who will implement it one work item at a time (section 5).

The goal it is measured against comes from the author: the questline "has decent bones, but needs
a lot of deliberate work to reach the quality of a AAA title". It should stay true to CrazyCraft.
Big leaps in power are fine and fun, but they should never go straight to the top, and the plateau
must not come fast.

---

## How sure each claim is

Every finding carries one of these tags:

| Tag | Meaning |
|---|---|
| **[verified]** | Checked against the live game data: the item registry saved in a world, a mod's own jar (lang file, class, enum order), or a config file. |
| **[likely]** | Strong inference from mod knowledge plus partial evidence. Worth a 30-second in-game check before acting. |
| **[guess]** | Design judgement or mod knowledge that I could not check offline. Treat it as a hypothesis. |

**How item IDs were checked.** Forge writes the full item and block registry into every world's
`level.dat` (`FML → ItemData`). I parsed it from a copy of `saves/Stress Test/level.dat`, saved
2026-10-16 with all 141 mod IDs of the current pack. That gives 9,394 names. Each of the book's
**2,190 item references (732 distinct IDs)** was looked up exactly, with case sensitivity. This is
the same method the old quest-55 repair used, and it catches the prefix trap that README describes.
It checks **names only**. Damage values (metadata) are not in the registry, so each meta-sensitive
finding below was checked separately against the mod's own enum or lang.

---

## 1. Inventory

### 1.1 The book at a glance

| | |
|---|---|
| Quests | **308** in **20** quest lines. Every quest sits in exactly one line. No dangling prerequisites, no cycles. **[verified]** |
| Task types used | `bq_standard:retrieval` ×305, `bq_standard:checkbox` ×3 (quests 0, 430, 431). **Nothing else.** |
| Task types available but unused | hunt (kill), location (dimension/biome/structure), crafting, block break, interact entity/item, meeting, XP, fluid, scoreboard. All of them ship in Standard Expansion 3.0.181. **[verified, class list]** |
| Reward types used | `bq_standard:item` ×240, `bq_standard:choice` ×68 |
| Reward types available but unused | command, XP, scoreboard |
| Retrieval settings | `consume=0` on **all 305** retrieval tasks. Items are only looked at, never taken. |
| Visibility | 301 `ALWAYS`, 7 `COMPLETED` (the Secrets). Every line is also `ALWAYS`, so the whole book, Queen and Red Matter included, is readable on day one. |
| Party/global flags | `party_enable=1` globally. `globalShare=0`, `autoClaim=0`, `repeatTime=-1` and `lockedProgress=0` on every quest. |
| Prerequisite graph | Max depth 17 (Welcome → … → Crystal Armoury). **109 root quests** (Pets 55, Heroes 50, Secrets 3, Welcome 1). **177 leaves.** **Only 2 quests in the whole book have more than one prerequisite** (105 Circle Talisman, 121 Dragon Reborn). |
| Hub | Quest **6 "Diamond Gear"** directly unlocks **15** quests across 9 lines. Quest 4 "Armor Up!" unlocks 13. |

### 1.2 Quest lines (tab order as shown in game)

| Order | Line | Quests | Opens after | Depth | Notes |
|---|---|---|---|---|---|
| 0 | Ch 1: Start | 9 | — | 0–6 | Vanilla wood → diamond kit. 3 checkboxes (0, 430, 431). |
| 1 | Ch 2: Base | 7 | 2 Crafting Station | 3–4 | Storage QoL. |
| 2 | Ch 3: Twilight | 9 | 6 Diamond Gear | 7–15 | Linear boss ladder, Naga → Snow Queen. Best-structured line. |
| 3 | Ch 4: Witchery | 12 | **5** Diamond Dreams | 6–14 | Opens *before* Ch 3, though its own text says "after Twilight on purpose". |
| 4 | Ch 5: Dark Paths | 7 | 105 Circle Talisman | 15–16 | Witchery part 2. |
| 5 | Ch 6: The End | 13 | 6 Diamond Gear | 7–15 | HEE. |
| 6 | Ch 7: OreSpawn | 12 | 6 Diamond Gear | 7–17 | Titans. Feeds ProjectE gating. |
| 7 | Ch 8: TragicMC | 11 | 6 Diamond Gear | 7–15 | Text says "After the titans". Data says after diamond. |
| 8 | Ch 9: ProjectE | 4 | 16 Lich, 22/23/24 titans | 10–16 | Mirrors `crazycraft_gating.zs`. |
| 9 | Railcraft | 9 | 5 Diamond Dreams | 6–10 | |
| 10 | Gadgets | 10 | 4/5/6 | 5–8 | Portal Gun, Gravity Gun, Battlegear, Mutants, MCHeli, Sync. |
| 11 | Exploration | 13 | 4/6 | 5–8 | Backpacks, glider, ships, Soul Shards, SecurityCraft, ChocolateQuest loot. |
| 12 | Workshop | 11 | 2/3/6 | 3–7 | Decoration mods. |
| 13 | Danger Zone | 5 | 4/6 | 5–7 | TARDIS, Weeping Angels, Pandora's Box, Jungle. |
| 14 | War Machines | 2 | 6 | 7–8 | ICBM. |
| 15 | Pets | **55** | — (all roots) | 0 | One quest per Inventory Pet. |
| 16 | Rewards | 5 | 0/6/19/24 | 1–16 | Lucky Block, Loot Bag, Roguelike, TF trophies, **PACK MASTER**. |
| 17 | Beastiary | 6 | 4 Armor Up! | 5–10 | Lycanites → Rahovart. |
| 18 | Heroes | **101** | — (50 roots) | 0–4 | One piece quest plus one full-set quest per suit, for 48 suits, plus Iron Man marks. |
| 19 | Secrets | 7 | various / none | 0–16 | Hidden until done. |

**Where the 308 quests go.** The nine numbered chapters hold **84** quests (27%). Nine side tabs
hold **68** (22%). **Pets and Heroes alone hold 156 (51%)**, and none of those 156 have a gate.
Half the book is collection checklists that open on day one.

### 1.3 Content coverage

55 registry namespaces appear somewhere in the book. These are the most-referenced: legends 824,
minecraft 282, lootbags 210, lucky 165, InventoryPets 129, witchery 95, TragicMC 64, OreSpawn 63,
TwilightForest 60, HEE 52, Railcraft 47.

**Content mods with zero quests** (counted against registry namespaces and `pack/mods.tsv`):

| Mod | Registry entries | Why it matters |
|---|---|---|
| **Quest Forge Content (`qfcontent`)** | 15 | The pack's *own* features have no quests: jukebox, records, Record Case, enchant books, the four consumables, **sealed tomes**, Forge Block/Shard, Tower Speaker. `docs/design/enchantments.md` says tomes are meant to be handed out as quest rewards (`qfcontent:sealed_tome`, meta 0–4) and that this "is authoring work, not code". None are handed out. |
| **Quest Forge Commands (`qfcommands`)** | 1 (`lottery_ticket`) | Tickets unlock `/vault`, `/home` and dimension travel. They are an ideal non-power reward, and none are used. |
| Transformers | 119 | Ships a custom `-qf1` build. No quests. |
| Psychedelicraft | 71 | |
| Ender Utilities | 26 | |
| **Morph** | entity-only | Ships enabled (commit `4f44164`). A signature CrazyCraft toy with no mention anywhere. |
| Lycanites: arctic, desert, freshwater, inferno, jungle, mountain, plains, saltwater, shadow, swamp | ~150 | Only `forestmobs` (Warg Treat) and `demonmobs` (Rahovart) appear. |
| Doomlike Dungeons, Recurrent Complex | structures | Roguelike appears only through quest 80's mossy-cobble proxy. |
| ArchitectureCraft, Wireless Redstone, Hopper Ducts, ChickenChunks, Mob Statues, Killer Pacman, Origin | | Utilities and toys. |
| Custom NPCs | 414 | Two reward references only. It could carry quest-giver NPCs (section 4). |

**Token coverage (1–2 quests)** in mods that are headline features in CrazyCraft: MCHeli (481
items, 2 quests), ICBM (2), TARDIS (1), Portal Gun (1), Gravity Gun (1), Weeping Angels (1),
Mutant Creatures (2), Food Plus + Food Expansion (437 items, 1 quest), ChocolateQuest (5 loot
quests, **0 of its 16 bosses**), Welcome to the Jungle (2, and the Lost World is never reached).
The Legends jar also bundles Star Wars, Kaiju mechs, Horror and Battlebourn content plus
**13 dimensions** (`docs/survey/dimension-names.tsv`). The book touches none of that, only suits.

**Missing vanilla progression:** there is **no Nether quest and no Wither quest**. The Nether
appears only as a ghast tear in Secret 73 and as TragicMC's Nether key.

---

## 2. Defects

Severity: **S1** breaks a quest or the economy · **S2** skips a tier or lets a quest be cheesed ·
**S3** misleading text, wrong proof, cosmetic.

### 2.1 Impossible or broken quests

| Sev | Quest | Problem | Evidence | Fix |
|---|---|---|---|---|
| S1 | **63 ★ PACK MASTER ★** (the book's final quest) | Asks for **64 × `OreSpawn:OreSpawn_Royal`**, the Royal Guardian *Sword*. Swords do not stack, and retrieval with `consume=0` needs all 64 in the inventory at once. There are only 36 slots. **Uncompletable.** | Royal is a sword per `crazycraft_gating.zs` and `docs/survey/combat.md` ("Royal Guardian's 747"). **[verified id / likely stack size]** | Rewrite as the finale convergence (section 4.3). At minimum use ×1. |
| S1 | **80 Dungeon Delver** | Needs `minecraft:mob_spawner` as an item. Survival cannot produce one: Chest Transporter picks spawners up as a *transporter* item (config `pickupSpawners=true`), not as the spawner block. | `config/ChestTransporter.cfg`, jar `Spawner.class` **[likely]** | Use a location/structure task, or loot only Roguelike drops. |
| S1 | **39 Railcraft: Steam Power** | Asks for `Railcraft:machine.alpha` meta 5. That meta is the **Smoker**. The Solid Fueled Firebox the text names is `machine.beta` meta 5. | Enum order read from `EnumMachineAlpha` / `EnumMachineBeta` in `Railcraft.jar` **[verified]** | Change task and icon to `Railcraft:machine.beta@5`. |
| S2 | **431 Pick a Class** | The reward `levelup:xpTalisman` and the icon `levelup:respecBook` are **not registered**: `config/levelup.cfg` has `Enable Talisman=false` and `Enable Unlearning Book=false`. The reward becomes a placeholder. The text also advertises a Book of Unlearning that does not exist. | Registry has no `levelup:*` items; config lines 89/92 **[verified]** | Re-enable the items (an author decision) or swap the reward and rewrite the text. |
| S3 | **300 Hall of Heroes** | Reward `legends:superDex` is not registered, so it becomes a placeholder. | Registry and Legends lang **[verified]** | Drop it or find the real ID. |
| S3 | `tools/pack-fixes/quest-55/README.md` | Says the quest 55 fix is "prepared, NOT applied". It **is** applied (quest 55 uses `weepingangels:Angel's Tear`). Its invariants ("145 quests, 17 quest lines") describe an older book. | **[verified]** | Mark it historical. |
| S3 | Every script in `tools/pack-fixes/quests/` | They hard-code a macOS PrismLauncher path and a `minecraft/config` folder that does not exist in this repo. None of them can be re-run. | **[verified]** | Replace them with one toolkit (WP-0). |

### 2.2 Creative-only or admin items handed out as rewards

| Sev | Quest | Reward | Evidence |
|---|---|---|---|
| S1 | **140 TragicMC: The Doomsday Scroll** (choice) | `TragicMC:swordOfJustice` | Registered to TragicMC's *Creative* tab. Its hit code reads `capabilities.isCreativeMode` and `stackSize`, so in survival it either deletes itself or acts as a debug item. Either way it is not a reward. **[verified class / likely behaviour]** |
| S1 | **144 ★ Doombringer ★** (choice) | `TragicMC:bowOfJustice` | Same family as the sword. **[verified class]** |
| S1 | **141 ★ Witch of the Wild ★** (choice) | `witchery:infinityegg` | Lives in Witchery's creative tab. It has no recipe in this audit, and only the altar's power code refers to it: it is the creative infinite-altar-power block. **[likely]** |

### 2.3 Rewards that skip tiers

| Sev | Quest | What it hands out | Why it is wrong |
|---|---|---|---|
| S1 | **134 TragicMC: The Dimensional Key** | Choice of **Overlord Helm / Plate / Amulet** | The Overlord is TragicMC's final boss, and it lives *inside* the Synapse this key opens. The book hands out the last boss's armour for crafting the door to its house. The chapter opens at Diamond Gear (quest 6). **[verified ids, likely tier]** |
| S1 | **24 OreSpawn: THE QUEEN** | Choice: **64 Queen Scales** | Each Red Matter craft costs one Queen Scale (`crazycraft_gating.zs`). One kill plus this reward unlocks 64 Red Matter, which makes the Red Matter gate meaningless. It also fills a third of Pack Master. **[verified]** |
| S2 | **13 / 34 ProjectE Dark / Red Matter** | 3 Dark Matter, then 4 Red Matter, for crafting the first one | Triples or quadruples the most-gated material in the pack. |
| S2 | **6 Diamond Gear** | Choice includes `ProjectE:item.pe_zero_ring` | A ProjectE item before the Lich, while the ProjectE chapter says it "stays sealed until the story bosses are receipts". |
| S2 | **21 OreSpawn: Ultimate Gear** | Ultimate Pickaxe and Ultimate Bow, for crafting the Ultimate Sword | This is step 2 of the chapter, before Mantis, Basilisk, Scorpion and Kraken. The quest order makes Ultimate the *first* OreSpawn goal, then pays out two more Ultimate pieces. **[likely tier]** |
| S2 | **107 Witchery: The Road to Torment** | Choice includes `witchery:deathsrobe` | Part of the Death set, which normally drops from Witchery's Death boss. **[verified id, likely source]** |
| S2 | **137 TragicMC: Time and Corruption** | Choice includes `TragicMC:titan` ("The Titan") | A top-tier named weapon from a mid-chapter quest. **[likely]** |
| S2 | **Pets (55) + Heroes (101)**, no gates | Together: **554 Lucky Blocks, 6 Legendary + 11 Epic loot bags, 68 golden apples, 32 diamonds, 2 diamond blocks** | All of it is available without passing a single boss. For scale, the nine numbered chapters together give **10 guaranteed loot bags and 0 Lucky Blocks**. The economy is upside down: hobby tabs pay 10–50× more than story bosses. **[verified tally]** |

### 2.4 Cheesable tasks: a reward completes the next quest

Each line reads: the reward of the first quest fully satisfies the task of the quest it unlocks. **[verified]**

- **401 → 402 → 403 → 404** (Bestiary main chain): the Soulgazer reward gives 2 Warg Treats, which completes 402. Its reward gives a Soulstone, which completes 403. That reward gives a Soulkey, which completes 404. Four "main" quests take three clicks.
- **33 → 434**: the helicopter reward includes 1 fuel, which completes "Keep It in the Air".
- **2 → 52**: Crafting Station rewards a BiblioCraft Clipboard, which is exactly what "BiblioCraft Library" asks for.
- **18 → 62**: the Ur-Ghast choice reward includes the Ur-Ghast trophy that the Trophy Collector asks for.
- **118 → 113**: the Spatial Dash Gem reward gives 8 Endium, and "HEE: Endium" asks for 4.
- **303 → 300**: Iron Man Mark 1 gives 9 Electronics, and the Hall of Heroes entry quest asks for 1.

**Structural cheese, everywhere: `consume=0` plus a shared server.** One friend's Royal Guardian
Sword, Dragon Egg or Doomsday Scroll can be handed to every other player and completes the same
quest for each of them. For boss proofs, that turns the book into a relay race. Section 4.6 covers
this.

### 2.5 The task does not prove what the quest says

| Sev | Quest | Problem |
|---|---|---|
| S2 | **14 Twilight Forest: Portal Creation** | The text says to build the portal. The task asks for a **Naga Scale**, so this "portal" quest only completes after the Naga is dead, which duplicates quest 15. Use a location task (dimension 7). **[verified data]** |
| S2 | **19 Twilight: The Snow Queen** | Asks for Alpha Fur, which drops from the **Alpha Yeti**, not the Snow Queen. **[likely]** |
| S2 | **95 Twilight: The Alpha Yeti** | Asks for Arctic Fur, which drops from **ordinary Yetis**. **[likely]** |
| S3 | **18 Twilight: Ur-Ghast** | Asks for Carminite, which also comes from the tower's lesser mobs. The Ur-Ghast-specific drop, Fiery Tears, is in the *reward* instead. **[likely]** |
| S3 | **94 Knight Phantom** | Knightmetal comes from the stronghold goblins' armour shards. **[likely]** |
| S2 | **430 The Name Was Longer**, **431 Pick a Class** | Checkboxes: honour system. 430 could be a hunt task. |
| S3 | **6 Diamond Gear / 4 Armor Up!** | The text says "Wear it". The task only checks the inventory. |
| S3 | **62 Twilight Trophy Collector** | "Collect all Twilight Forest boss trophies", but it omits the Snow Queen trophy (meta 4), even though it unlocks after the Snow Queen. **[likely meta]** |

### 2.6 Text that contradicts the data

- **13 ProjectE: Dark Matter** says "The recipe now requires King Scales". The CraftTweaker recipe uses the **Royal Guardian Sword** (`.reuse()`), and quest 23 correctly says the King has no tidy drop. **[verified]**
- **Ch 4 Witchery** line text says it "sits after Twilight on purpose". It opens at quest 5, before Twilight's quest 6.
- **Ch 8 TragicMC** line text says "After the titans". It opens at quest 6.
- **Ch 6 The End** says "after the craft, before the OreSpawn gods". It is gated only by quest 6.
- **406 Rahovart** says "late-game on purpose". The chain opens at iron armour (quest 4) and self-completes (2.4).
- **49 Hat Collector**: the text says to kill mobs for hats, but the task is crafting a Hat Stand. **57 Master Chef**: the text says Fryer, the task asks for a Grill. **52 BiblioCraft Library**: the text says shelf or stand, the task asks for a Clipboard.
- **300 Hall of Heroes** and the **Pets** line text both say "Workshop tab". They are their own tabs.
- **421 The Book of Scale** promises "The Lost World portal is later". No later quest exists.

### 2.7 Typos, grammar and voice

- Tab name **"Beastiary"** should be **"Bestiary"**, in the line name and in the 401 text. `HardcoreEnderExpansion:schorching_pickaxe` is the mod's own spelling, so leave it.
- The pet template says "Retrieve **a Anvil** / **a Apple** / **a April Fool** / **a Enchanting Table** / **a Ender Chest** / **a Enderman** / **a Illuminati** / **a Iron Golem** / **a Ocelot** Pet". These are quests 46, 47, 64, 90, 91, 92, 194, 195 and 204.
- **Two voices.** 134 quests use the house voice: an italic hook, a short body, an attributed quote and a yellow imperative. **16 quests are still in the old marketing voice**, with exclamation marks and "This mod adds…": 12, 13, 26, 38, 39, 44, 45, 49, 50, 54, 55, 56, 57, 58, 60, 62. Quests 0 and 59 are a mix.
- Recurring tics worth thinning out: "suggestion" ×7, "opinions" ×7, "receipt" ×7, "landlord" ×5, "paperwork" ×4. The text also refers to its own structure ("this page", "side tab", "the spine", "numbered chapters") far more often than to the world.

### 2.8 Things checked and found correct

- No item ID typos beyond the three in 2.1. 729 of 732 distinct IDs resolve exactly, including every TragicMC, OreSpawn, HEE and Witchery endgame ID.
- The quest-55 Weeping Angels fix is in place.
- The Hall of Heroes full-set rewards look shuffled (Supergirl's full set pays out Zod materials, for example), but that is **deliberate**. `tools/branding/hero-art/retarget_fullset_rewards.py` points each full set at a related hero's materials as a nudge toward the next suit.
- Tab order is sane: chapters 1–9 first, Secrets last.

---

## 3. Pacing map

### 3.1 What the quests imply versus what the mods are

The tiers on the left are the usual CrazyCraft power ladder. Exact placement of individual items is
**[guess]** unless marked. `docs/survey/combat.md` gives the one hard number on the scale:
weapons run from a wooden sword's 4 damage to the Royal Guardian's **747**, and Rahovart has
**5,000 HP** (`docs/reference/enchantment-combat-results.md`).

```
TIER                        WHAT THE BOOK ASKS                     WHAT THE BOOK OPENS / GIVES
--------------------------  -------------------------------------  ---------------------------------------------
T0 Vanilla                  Ch1 0-5: logs, table, iron tools,      Day 1, ungated: Pets (55) + Heroes (50 roots)
   (iron -> diamond)        iron armour, 16 diamonds               => 554 Lucky Blocks, 6 Legendary bags   [J4]
                                                                   Q4 iron armour opens Bestiary -> Rahovart
                                                                   summon chain (self-completing)          [J9]
                                                                   Q5 opens Witchery + Railcraft
                            Q6 full diamond kit (~26 more  [S1]    Q6 opens 15 quests in 9 lines AT ONCE   [J1]
                            diamonds) is the ONE big gate          incl. Ch3, Ch6, Ch7, Ch8, ICBM; zero ring [J5]
T1 Early modded             Ch3 Naga/Lich; Ch4 Witchery basics;    Lich -> Philosopher's Stone (good gate)
   (named mobs, first       Railcraft steel; Mutants; CQ loot;
   dungeons)                OreSpawn Mothra (Q20)
                            -> Q21 ULTIMATE SWORD, chapter step 2  + Ultimate pick + bow                   [J2]
T2 Mid                      Ch3 Minoshroom..Snow Queen; Ch6 HEE;   TragicMC Q134 (step 5): OVERLORD ARMOUR [J3]
   (multi-phase bosses,     Ch5 Spirit/Torment; TragicMC synapse   Q137 The Titan; Q107 Death's Robe       [J7]
   new dimensions)          crafting; OreSpawn Mantis..Kraken      Q141 Infinity Egg (creative)            [J8]
T3 Late (titans)            Mobzilla, King, Queen; HEE Dragon;     Queen: 64 Queen Scales -> 64 Red Matter [J6]
                            Rahovart (5,000 HP)                    Dark Matter x3, Red Matter x4
T4 Endgame                  Crystal Dimension + armoury;           Sword/Bow of Justice (creative)
                            Doomsday Scroll; Red Matter            PACK MASTER: impossible (64 swords)     [S3]
                            -> nothing after Red Matter            ProjectE post-gate: no content          [S4]
```

### 3.2 Where the player jumps too far

- **J1: one door opens five chapters.** After quest 6 the "numbered" chapters 3, 6, 7 and 8 open at the same moment. Nothing in the data stops a diamond-armoured player from starting OreSpawn or TragicMC before the Naga. The numbers are advice, not structure, because only 2 quests in the book require two things.
- **J2: OreSpawn front-loads its best craftable gear.** Ultimate comes at step 2, then the minibosses meant to justify it.
- **J3: TragicMC hands out its final-boss armour mid-chapter.** That reward arrives within reach of a fresh diamond player.
- **J4: the Pets/Heroes faucet.** Hundreds of Lucky Blocks and the pack's best loot bags, with no gate. In CrazyCraft a Lucky Block can roll anything. This is the main reason the plateau would come fast.
- **J5–J8:** individual leaks: zero ring, Queen Scales ×64, Death set, Infinity Egg, Justice weapons.
- **J9: Rahovart's summon at iron tier.** This is the reverse problem. The player can summon a 5,000 HP world boss with iron gear. It is a trap, not a leap, but the quest claims it is late game.

### 3.3 Where the player stalls

- **S1: the diamond wall.** About 40 diamonds (16 for quest 5, then a full kit for quest 6) must be found before most of the pack opens. Everything before it is vanilla and the rewards are thin. That is the wrong first hour for CrazyCraft, and the worst possible first hour for a friend joining a server where everyone else is already flying.
- **S2: no mid-game climaxes.** Chapters end in isolation. Twilight's Snow Queen, HEE's dragon and the Witchery finale unlock nothing beyond their own chapter, so there is no "Act II is over" moment. Combined with J1–J4, the player levels past the content rather than through it.
- **S3: no ending.** The capstone (63) cannot be completed, and it only measures OreSpawn anyway.
- **S4: content cliff after Red Matter.** ProjectE gets 4 quests and then nothing: no collectors, condensers, Klein stars or gem armour, even though the zs script gates collectors behind Dark Matter.

---

## 4. What AAA would look like here

The bones are good: a strong house voice, a real gating script, a chronicle framing ("Quest Forge
– Chronicle of Chaos" is already the `pack_name`), hero art, and dungeons and bosses in every
direction. What's missing is **structure that enforces the story, rewards that respect it, and
tasks that prove what they claim.**

### 4.1 Narrative spine: the Chronicle of Chaos

One sentence the whole book hangs on: *the dimensional barriers broke, the old powers
(Twilight, Witchery, the End) woke first, the titans (OreSpawn, TragicMC, Rahovart) came after,
and the Chronicle records the people who walked through all of it.* The existing text already says
this in pieces (the Twilight intro, OreSpawn "First Contact", the Philosopher's Stone). It needs
to be said on purpose, one act at a time.

| Act | Tab name (≤ 14 chars, because GuiHome clips) | Tier | Contents | Finale gate (multi-prerequisite) |
|---|---|---|---|---|
| Prologue | `Arrival` | T0 | Onboarding (4.2) | — |
| I | `I: Broken Sky` | T0→T1 | Iron, **the Nether**, first Mutant, first CQ castle, first tame, Battlegear, backpacks | **"First Blood"**: kill one of Mutant Zombie, a CQ boss or the Wither (OR logic), *and* reach diamond. Opens Act II. |
| II | `II: Old Powers` | T1→T2 | Twilight Naga → Hydra; Witchery to the Talisman; Railcraft steel; Lycanites families | **"The Old Powers Answer"**: Hydra **AND** Circle Talisman. Opens Act III and the End. |
| III | `III: The Veil` | T2 | HEE End; Dark Paths (Spirit, Torment); Twilight Knight Phantom → Snow Queen; TragicMC Nether/End keys and the Collision; OreSpawn sky worlds and minibosses (Mantis → Kraken); **Ultimate gear goes here** | **"Beyond the Veil"**: HEE Dragon **AND** Snow Queen **AND** one TragicMC key. Opens Act IV. |
| IV | `IV: Titans` | T3 | Mobzilla (→ Transmutation), Rahovart, the King (→ Dark Matter), TragicMC Synapse and **the Overlord** (its armour is earned by killing it), the Queen (→ Red Matter) | **"Titanfall"**: Queen **AND** Overlord **AND** Rahovart |
| Epilogue | `Chronicle` | T4 | Crystal Dimension, Doomsday Scroll, ProjectE post-gate (collectors, condensers, gem armour), Legends' far dimensions | **New Pack Master**: the four act finales. Reward is cosmetic and server-wide (4.5, 4.6). |

Keep the current Ch 1–9 quests. Most of them move into an act unchanged. What changes is the
*prerequisites between chapters* and the *visibility*: an act's tab should be `UNLOCKED`/`NORMAL`
rather than `ALWAYS`, so the Queen is a rumour until you've earned her.

The pack already has the art for this. The loading-screen plates in qf-content, the hero art, and
`questforge:dark` as the theme are there. Each act's line can use a `bg_image` from the existing
art.

### 4.2 Onboarding: `Arrival` (8–10 quests, about 20 minutes)

A new friend joining a server mid-campaign is the most common case for this pack. The prologue
has to teach the systems that kill people, not the crafting table.

1. **Welcome to the Chronicle** (checkbox). Covers the keys: `'` for the book, `J` for the map, `L` for Level Up, the party key. Covers server rules.
2. **Join a party** (checkbox). Explains BQ parties and what they share (4.6).
3. **The First Night**: hunt 5 hostile mobs. Reward: bed and torches (moved from quest 0).
4. **Long Names**: kill an Infernal mob (hunt task, if Infernals can be targeted. Otherwise keep the checkbox). Explains nametag affixes.
5. **When You Die Here**: what Gravestones/OpenBlocks graves do, and how to get your things back (checkbox, with the Gravestone in the reward).
6. **Pick a Class**: fixed quest 431.
7. **Things That Are Not Your Fault**: Weeping Angels below Y=40, mutants, roaming titans. "If it is taller than your base, walk away." Checkbox, rewards a Common sealed tome.
8. **A Bag That Remembers**: Adventure Backpack, the existing quest 35 moved here.
9. **Your First Ticket**: a `/home` lottery ticket. This is utility, not power, and it is the single most friend-friendly thing the pack can hand a newcomer.
10. **Into the Chronicle**: unlocks Act I.

Move the diamond wall later and soften it. Act I should put a modded thrill (a mutant, a
helicopter, a portal gun) **before** the full diamond kit, which is how CrazyCraft actually plays.

### 4.3 Milestone boss gates

Use `bq_standard:hunt` for kills and `bq_standard:location` for arrivals. Keep retrieval for
crafting and gathering. The table below lists entity names to try, taken from the mods' lang
keys (`entity.<name>.name`). They are **[likely]**: confirm each one with the entity picker in
BQ edit mode before writing data.

| Boss | Hunt target (try) | Today's proxy |
|---|---|---|
| Naga / Lich / Minoshroom / Hydra | `TwilightForest.Naga`, `TwilightForest.Twilight Lich`, `TwilightForest.Minoshroom`, `TwilightForest.Hydra` | scales, scepter, stroganoff, blood |
| Knight Phantom / Ur-Ghast / Alpha Yeti / Snow Queen | `TwilightForest.Knight Phantom`, `TwilightForest.Tower Boss`, `TwilightForest.Yeti Boss`, `TwilightForest.Snow Queen` | wrong drops (2.5) |
| Rahovart | `demonmobs.rahovart` | Demon Crystal |
| TragicMC bosses | `TragicMC.Apis`, `TragicMC.Kitsune`, `TragicMC.Polaris`, `TragicMC.TimeController`, `TragicMC.Enyvil`, `TragicMC.Claymation`, `TragicMC.Aegar`, `TragicMC.OverlordCore` | none |
| ChocolateQuest bosses | `chocolateQuest.spiderBoss`, `…monking`, `…pirateBoss`, `…necromancer`, `…Lich`, `…greenDragon`, `…minotaurBoss` and others (16 total) | banners only |
| Mutants | `MutantCreatures.MutantZombie`, `…MutantSkeleton`, `…MutantEnderman`, `…MutantCreeper` | drops |
| OreSpawn titans | names not readable offline. Take them from the editor's picker. | scales / sword |

Dimension IDs for location tasks are already catalogued in `docs/survey/dimension-names.tsv`:
Twilight 7, Synapse 3, Collision 2, Crystal 84, Lost World −42, Torment −38, Spirit −39,
Dream −37, Legends 30–66, OreSpawn 80–85. Location tasks can also target a biome or a structure.

### 4.4 Side chapters per major mod

Side chapters hang off the act that makes them sensible. They pay **utility and flavour**, never
the next act's power.

| Side tab | Opens from | Built from |
|---|---|---|
| `Workshop` / `Base` | Prologue | Existing quests, kept |
| `Bestiary` | Act I | Lycanites by family: one hunt per biome group (arctic, desert, inferno…), taming, soulstones. Rahovart moves to Act IV. Fixes 2.4. |
| `Castles` | Act I | ChocolateQuest: banners and loot (existing 440–444) plus its 16 bosses as hunt tasks |
| `Dungeons` | Act I | Roguelike, Doomlike, Recurrent Complex. Location/structure tasks replace quest 80. |
| `Witchery` | Act I | Today's Ch 4/5 grow into the full craft: rituals, Mirror dimension, the Death set **earned from Death** |
| `Heroes` | Act I | **Tiered**: street-level suits (Batman family, Arrow, Daredevil) in Act I; powered suits (Flash family, Spider family, Cap) in Act II; cosmic suits (Superman, Thor, Hulk, Shazam) in Act III. **[guess on suit power; measure it, see WP-8]** Add Legends dimensions as location quests (Speed Force, Wakanda, Quantum Realm…). |
| `Engineering` | Act I | Railcraft (existing), MCHeli expanded (more than 2 airframes), ICBM, Archimedes |
| `Gadgets` | Act I | Portal Gun, Gravity Gun, TARDIS, Sync, **Morph** (checkbox, "Wear their skin"), **Transformers** |
| `Jungle` | Act II | Welcome to the Jungle through the **Lost World portal** (location −42), redeeming quest 421's promise |
| `Pets` | Prologue | Shrink 55 one-pet quests to **about 12 family quests** (farm pets, block pets, nether pets, legendaries), with modest rewards |
| `Quest Forge` | Act I | The pack's own content: craft a jukebox, collect record tiers, open a sealed tome, apply a book, use Magic Dust and Ward Scroll. This teaches the custom enchantment system the pack built and never explains. |
| `Kitchen` | Prologue | Food Plus and Food Expansion: 437 items, currently 1 quest |
| `Secrets` | — | Keep the idea, and keep it last |

### 4.5 Reward design

**Principles:**

1. **Never pay out the next tier.** A reward should be worth less than the effort of the quest, and from the same or a lower tier. Boss gear comes from the boss.
2. **Choice between flavours, not between tiers.** The 68 choice rewards are a strength. Make each option different in *kind* (weapon, armour piece, utility) and equal in *power*. Today many choices are "64 of a material vs a weapon".
3. **Gambles scale with the act, through the systems the pack already has:**
   - Loot bags `lootbags:lootbag` meta 0–4 (Common → Legendary).
   - Sealed tomes `qfcontent:sealed_tome` meta 0–4. The roll happens when the tome is opened, so a quest-given tome is still a gamble (`docs/design/enchantments.md`). Add Magic Dust and Ward Scrolls (`qfcontent:consumable` meta 0/1) as sweeteners.
   - Lucky Blocks: a **budget**, not a confetti cannon.
4. **Utility is the best reward on a friends' server.** Lottery tickets for `/home` and `/vault` (`qfcommands:lottery_ticket`, where the damage value is the position in `Unlockables.java`), Iron Chest upgrades, drawer upgrades, backpack parts, Ender Pouches. Dimension tickets can only come from a quest that proves you *arrived*, matching the ticket design in `Unlockables.java`: "the command can never skip the quest".
5. **Cosmetics and trophies for finales:** statues, hats, records (qfcontent record tiers), banners, named items, a server-wide announcement through a command reward.

**Budget per act, as a starting point** **[guess, tune by playtest]:**

| Act | Loot bags (most valuable) | Sealed tomes | Lucky Blocks across the whole act | Raw diamonds / blocks |
|---|---|---|---|---|
| Prologue | Common | 1 Common | ≤ 5 | 0 |
| I | Uncommon | Common–Uncommon | ≤ 20 | ≤ 16 diamonds |
| II | Rare | Uncommon–Rare | ≤ 30 | ≤ 4 blocks |
| III | Epic | Rare–Epic | ≤ 30 | ≤ 8 blocks |
| IV | Legendary (finales only) | Epic–Legendary | ≤ 40 | free |
| Side tabs | one bag below the act they open from | Common–Uncommon | ≤ 1 per quest | ≤ 4 diamonds per quest |

### 4.6 Multiplayer and party design

What the data does today: parties are enabled. Every quest is personal (`globalShare=0`).
Retrieval never consumes. BQ's party screen offers "Share Lives" and **"Single Reward"** toggles
**[verified, lang]**. The exact sharing semantics of BQ 3.0.328 should be confirmed in a
two-account test (WP-9) before relying on them. **[likely]** Party members share quest
progress, and "Single Reward" decides whether one claim pays everyone or only the claimer.

Recommendations:

- **Default: one party per friend group, with Single Reward OFF.** Everyone in the party gets credit for a boss the group killed, and everyone gets their own reward. Say this in the Prologue so nobody feels carried or cheated.
- **Boss proofs become hunt tasks**, not handed-around items. That closes the relay-race cheese from 2.4. Where an item must stay as proof (the Royal sword for Dark Matter), that is fine: the zs recipe uses it with `.reuse()`.
- **Never require one-per-world items for everyone.** The Dragon Egg (quest 121) exists once per End unless HEE respawns the dragon **[guess]**. Use a hunt task on the dragon instead.
- **A `Chronicle` tab of server-wide firsts** (quest property `GLOBAL`): "The first party to kill Mobzilla", "The first to reach the Synapse". Rewards: a command reward that announces it (`say` with the player-name variable; check the placeholder name in the editor) plus a cosmetic. These are the stories the friends will retell.
- **Catch-up for late joiners:** Act I and the Prologue stay personal and fast. A late friend who joins an existing party inherits the party's progress **[likely, verify]**. Note this in the Prologue.
- **Bump `pack_version`** (currently 5) on every quest release, and run `/bq_admin default load` on the server after installing. BQ only re-imports defaults when told to, or when the version changes **[likely]**.

### 4.7 Tone and writing guidelines

The house voice is already good. Codify it:

1. **Hook:** one italic line, 15 words or fewer, about the world, not the book.
2. **Body:** two or three short paragraphs. What it is, why now, and **one practical tip that actually saves a life** (a Y-level, a key, a weakness).
3. **Quote:** one line, attributed to a role (`- Watch`, `- Quartermaster`). It can be funny. It should not repeat the hook.
4. **Ask:** the last line in `§e`, stating *exactly* what the task checks. Never claim "wear it" or "build it" when the task is retrieval.
5. **No meta-structure in prose.** Avoid "this page", "side tab", "the spine", "numbered chapters". Use the act name or say nothing.
6. **No marketing voice.** No exclamation marks, no "This mod adds".
7. **Parties:** say "you and your party" wherever a fight is group-sized.
8. **Rotate the tics** ("suggestion", "opinions", "receipt", "landlord", "paperwork"). At most one per chapter.

**Three rewritten examples.** The data changes are described in prose. Write them in BQ edit mode
so the typed keys come out right.

**A. Quest 14, "The Pool at Dusk"** (was "Twilight Forest: Portal Creation")
- Task: `bq_standard:location`, dimension 7, anywhere in the dimension. The Naga Scale moves to quest 15, where it belongs.
- Reward: choice of {Twilight magic map | Common sealed tome | 16 torchberries}. Plus a Twilight lottery ticket? **No.** By the ticket design those only drop inside the dimension.
- Text:
  > *§oFour flowers, still water, and one diamond you will never get back.§r*
  >
  > Dig a two-by-two pool in open grass and ring every edge with flowers. Any kind will do. Throw a diamond in and step away from the water. The lightning is the forest checking who you are. It does not check twice.
  >
  > §7"I thought the flash meant it worked. It meant swim."§r §7- Pathfinder§r
  >
  > §eStep through into the Twilight Forest.§r

**B. Quest 134, "A Key to Somewhere Hostile"** (was "TragicMC: The Dimensional Key")
- Task unchanged (`TragicMC:dimensionalKeySynapse`). **Reward changed:** choice of {1 Epic loot bag | 2 Rare sealed tomes | 2 enchanted golden apples}. The Overlord armour moves to a new Act IV quest, "The Overlord", with a hunt task on `TragicMC.OverlordCore` (verify the name) and a statue or trophy reward.
- Text:
  > *§oCore, link, crystal. Turn it once and somewhere else agrees to be here.§r*
  >
  > The Synapse is not a cave with a new sky. It was built to kill people who arrived on purpose, and the thing that runs it is still at home. Go with your party, a way back, and more poppets than seems reasonable.
  >
  > §7"It doesn't unlock anything. It just stops the door pretending."§r §7- Keysmith§r
  >
  > §eCraft the Synapse Dimensional Key.§r

**C. Quest 22, "Mobzilla"** (was "OreSpawn: MOBZILLA!")
- Tasks: hunt the Mobzilla entity ×1 (party credit), **and** retrieval of 5 Mobzilla Scale Blocks with `consume=0`, kept because the Transmutation Table needs them.
- Reward: choice of {Mobzilla Helmet | 1 Legendary sealed tome | 1 Epic loot bag}. Plus a command reward announcing it to the server. **Remove the 32 bonus scale blocks.**
- Text:
  > *§oIt does not hunt. It occupies.§r*
  >
  > You will hear it before the chunk loads. Ultimate gear is the minimum, a horse is a coffin, and fighting near your base is how the base becomes a crater. Pick open ground, spread out, and let whoever has the bow keep its attention.
  >
  > §7"Fifty soldiers. Three came back. None of them wanted to talk about the shadow."§r §7- Archive§r
  >
  > §eKill Mobzilla. Bring five Scale Blocks. The Transmutation Table is listening.§r

---

## 5. Prioritised work plan

Each item can be done in one session. Do them in order: earlier items make later ones safe.

**Global rules for every item:**

- The repo file `pack/config/betterquesting/DefaultQuests.json` is the source.
- Prefer authoring in BQ edit mode (`/bq_admin edit`, then `/bq_admin default save`) and copying the saved file back into the repo, so the typed NBT-JSON keys are exactly what BQ writes.
- Bump `pack_version`.
- Commit each item, staging only your own hunks.
- Install to the live instance only when the user's game is not running.
- If writes to the live `DefaultQuests.json` silently revert, read `tools/pack-fixes/quest-55/README.md` first.

### WP-0: a quest toolkit (prerequisite for everything) — DONE 2026-10-17

- **Scope:** one script, `tools/quests/qb.py`, replacing the dead Mac-path scripts. It should have these subcommands:
  - `registry`: parse `FML/ItemData` out of a save's `level.dat` (gzip NBT; names carry a `\x01` block or `\x02` item prefix) into `tools/quests/registry.json`.
  - `lint`: unique IDs, every prereq exists, every quest in exactly one line, no cycles, unique `order:3` with Secrets last, no raw newlines in strings, balanced `§` codes.
  - `ids`: every `id:8` resolves exactly. Also fail on a **blocklist**: `TragicMC:swordOfJustice`, `TragicMC:bowOfJustice`, `witchery:infinityegg`, `betterquesting:placeholder`, and `levelup:*` while it is disabled in config.
  - `cheese`: a reward that satisfies a successor's task.
  - `stack`: count > 1 on known unstackables (swords, armour, tools, suits).
  - `tally`: reward totals per line and per act against the 4.5 budget.
  - `dump`: the human-readable dump this audit was written from.
- **Files:** new `tools/quests/qb.py`, `tools/quests/README.md`, `tools/quests/registry.json`. A note in `tools/README.md`.
- **Validate:** it reproduces this audit's numbers (308 quests, 2,190 refs / 732 IDs, 3 unresolved, 6 cheese pairs, the 554-Lucky-Block tally). Use `py -3.10 -I`.

### WP-1: hotfixes, no redesign — DONE 2026-10-17

- **Scope:** every S1/S3 data fix that doesn't change design.
  - 63: Royal ×64 → ×1, as a stopgap until WP-6.
  - 80: replace the spawner.
  - 39: `machine.beta@5`.
  - 431: reward and text.
  - 300: `superDex`.
  - 140 and 144: drop the Justice weapons.
  - 141: drop the Infinity Egg.
  - 33/434, 2/52 and 401–404: break the cheese pairs, either by changing the reward or by setting `consume=1` on the successor.
  - 13: text.
  - 14: location task.
  - 19/95/18: proofs. Hunt tasks are better; WP-4 does them properly.
  - The 2.6 text mismatches, "Beastiary" → "Bestiary", and the "a Anvil" grammar.
  - Mark `quest-55/README.md` historical.
- **Files:** `DefaultQuests.json`, `tools/pack-fixes/quest-55/README.md`.
- **Validate:** `qb.py lint ids cheese stack` are clean. Then a slim boot:
  `py -3.10 tools/trial/trial.py build q --bundle quests --bundle inspect railcraft levelup legends tragicmc witchery twilightforest lycanites` (add whatever the touched quests reference). Launch it as a background task when no other client is running. Open the book and confirm no placeholder icons on the touched quests.

### WP-2: stop the tier leaks (reward-only changes) — DONE 2026-10-17

- **Scope:** the 2.3 table.
  - 134: Overlord armour out.
  - 24: Queen Scales 64 → about 4.
  - 13 and 34: one Dark/Red Matter or a non-matter reward.
  - 6: zero ring out.
  - 21: Ultimate pick and bow out.
  - 107: Death's Robe out.
  - 137: The Titan out.
  - Pets and Heroes faucet: cap each quest at 1 Lucky Block and 1 loot bag at least one tier lower. Legendary bags only on the 4 legendary pets, the Costume Closet and the Mark 7.
- **Files:** `DefaultQuests.json`.
- **Validate:** `qb.py tally` shows the ungated Lucky Block total under about 60, and no Legendary bag reachable before Act III, except the legendary pets and the closet, which need rare finds.

### WP-3: put the spine into the data — DONE 2026-10-17

- **Scope:** add cross-chapter prerequisites without rewriting quests:
  - Ch 6 entry (56) needs 17 Hydra.
  - Ch 7 entry (20) needs 114 Endstone Temple, or 121.
  - Move 21 Ultimate after 79 Kraken.
  - Ch 8 entry (58) needs 22 Mobzilla, or at least 121.
  - Ch 4 entry (9) needs 15 Naga.
  - 401 Soulgazer needs 6. Rahovart (406) additionally needs 22.
  - Set the later chapters' quests to `UNLOCKED` visibility.
- **Files:** `DefaultQuests.json`.
- **Validate:** `qb.py lint`. A new `qb.py path` subcommand prints the shortest route to each chapter's first quest, and the order must match the chapter numbers. Slim boot with `--bundle quests`, then confirm in a fresh world that only Ch 1, Ch 2, Workshop and Pets are visible.

### WP-4: boss proofs become hunt and location tasks — DONE 2026-10-17

- **Scope:** Twilight 14–19 and 93–95, 121 Dragon, 22/23/24 titans, 406 Rahovart, plus new Overlord and Mutant quests. Entity names come from the 4.3 table, **confirmed with the BQ editor's entity picker**. Keep a retrieval alongside the hunt only where an item is needed downstream.
- **Files:** `DefaultQuests.json`.
- **Validate:** slim boot with the boss's mod plus `--bundle quests --bundle inspect`. Spawn the boss with an egg in creative and kill it. The hunt task must tick. Then do one co-op check (WP-9).

### WP-5: Prologue `Arrival`

**Drafted 2026-10-19, awaiting review:** `tools/quests/patches/wp5_prologue.py` builds it into
`tools/quests/drafts/DefaultQuests.wp5.json`. The plan for the acts is
[`quests/act-structure.md`](quests/act-structure.md); what needs deciding is in
[`quests/review-2026-10-19.md`](quests/review-2026-10-19.md).

- **Scope:** 8–10 quests per 4.2. Move 0, 430, 431 and 35 into it. Add lottery-ticket and sealed-tome rewards.
- **Files:** `DefaultQuests.json`.
- **Validate:** slim boot `--bundle quests --bundle qf --bundle hud` plus gravestones, levelup, infernalmobs and backpack. Walk it on a fresh world in under 20 minutes.

### WP-6: the Acts restructure

- **Scope:** rename and reorder lines into Prologue, Acts I–IV and Epilogue (4.1). Add the four finale convergence quests. Rewrite Pack Master as the convergence of the act finales. Write act line descriptions and assign `bg_image`. Add the Nether and Wither quests to Act I.
- **Files:** `DefaultQuests.json`. Maybe `pack/config/betterquesting/resources/` for backgrounds.
- **Validate:** `qb.py lint path tally`. Slim boot and screenshot every tab for the author's review.

### WP-7: new side chapters

- **Scope:** in the order the friends will notice them:
  1. `Quest Forge` (own content)
  2. `Castles` (CQ bosses)
  3. `Bestiary` by family
  4. `Jungle` through the Lost World
  5. `Gadgets` plus Morph and Transformers
  6. `Engineering` (MCHeli/ICBM)
  7. `Kitchen`
  8. Legends dimensions
  9. ProjectE post-gate
- One chapter per commit.
- **Validate:** `qb.py ids` against a fresh registry dump (`qb.py registry` from a save loaded with the current mods), then a slim boot with that chapter's mods.

### WP-8: Heroes and Pets consolidation

- **Scope:**
  - Pets: 55 quests → about 12 family quests.
  - Heroes: gate the suit lines by power tier (4.4), and cut the 101 quests to about 40 by dropping the separate piece quest for minor suits.
  - **First measure suit power.** This is the biggest unknown in this audit. Use the combat census (`docs/survey/combat.md`) on a Superman and a Batman loadout to place suits on the same scale as the Royal Guardian.
- **Files:** `DefaultQuests.json`, `tools/branding/hero-art/` (keep its generators in sync, or retire them).
- **Validate:** `qb.py tally`, and census numbers recorded in a short `docs/reference/` note.

### WP-9: multiplayer pass

- **Scope:** decide and document the party model (4.6). Add the `Chronicle` world-firsts tab (GLOBAL quests with command rewards). Audit `consume` on every retrieval task.
- **Files:** `DefaultQuests.json`, `docs/setup/hosting-a-server.md` (one paragraph for the friends).
- **Validate:** a slim **server** trial, `py -3.10 tools/trial/trial.py build bq --server --bundle quests <mods>`, with two client accounts, run one at a time per the one-client rule or with an offline second account on another machine. Check what a partymate sees after a kill, after a claim, and after joining late.

### WP-10: writing pass

- **Scope:** the 16 old-voice quests, the 2.6 mismatches that are left, and the meta-structure phrasing, all per 4.7. Add a `qb.py style` check: flag `!` count above 1, a missing `§e` ask line, and banned phrases.
- **Validate:** `qb.py style` is clean. The author reads one chapter out loud.

### WP-11: playtest protocol

- **Scope:** a written script for two friends: a fresh world, timestamps at each act finale, and notes on where people got bored and where they got too strong. Target pacing **[guess]**: Act I ≈ 2–3 h, II ≈ 5 h, III ≈ 8 h, IV ≈ 10 h+. The plateau (at most one tier below best-in-slot) should not arrive before Act IV.
- **Files:** `docs/design/questline-playtest.md`.

---

## 6. Implementation log

Every edit went into **both** books: `pack/config/…` and `server/config/betterquesting/DefaultQuests.json`.
The server copy is the survey server's older book (it keeps the HBM chapter, 148–155 and
410–415, and lacks ChocolateQuest 440–444); everything else in it was left as it was. Both
are now `pack_version` 8 (they were 5 and 3 before WP-1, 6 after WP-2, 7 after WP-3). The edits are scripts in `tools/quests/patches/`
and can be re-run.

### WP-0 (toolkit)

`tools/quests/qb.py`, documented in `tools/quests/README.md`. It reproduces this audit's numbers:
308 quests, 2,190 refs / 732 ids, 3 unresolved, and 554 Lucky Blocks in Pets + Heroes (765
across the book). Before WP-1 `qb.py check` failed with 27 errors per book. After WP-1 it passes.

### WP-1 (hotfixes)

| Quest | Change | Why |
|---|---|---|
| 63 Pack Master | task: Royal Guardian Sword ×64 → ×1 | Unstackable: 64 cannot fit in 36 slots. Stopgap until WP-6. |
| 80 Dungeon Delver | task: `minecraft:mob_spawner` removed; 64 Mossy Cobblestone stays | No survival path to a spawner item. |
| 39 Steam Power | task and icon: `machine.alpha@5` (Smoker) → `machine.beta@5` (Solid Fueled Firebox) | |
| 14 Portal Creation → "The Pool at Dusk" | task: Naga Scale → Twilight Oak log (`tile.TFLog@0`); text rewritten | The Naga Scale belonged to quest 15. A log proves arrival until WP-4 adds a location task. |
| 94 Knight Phantom | task: 8 Knightmetal → Phantom Helm **or** Phantom Plate (taskLogic OR) | Knightmetal also comes from goblins. The vault chest always holds one of the two (`TFTreasure.stronghold_boss`). |
| 18 Ur-Ghast | task: 8 Carminite → 1 Fiery Tear | Carminite also drops from lesser ghasts. Fiery Tears come only from the boss chest (`darktower_boss`). |
| 95 Alpha Yeti | task: 8 Arctic Fur → 4 Alpha Fur | Arctic Fur is the ordinary Yeti's. The Alpha drops 6–11 Alpha Fur (`EntityTFYetiAlpha`). |
| 19 Snow Queen | task: 4 Alpha Fur → Snow Queen trophy (`item.trophy@4`) | Alpha Fur is the Yeti's. She always drops her trophy (`EntityTFSnowQueen`). |
| 62 Trophy Collector | task: + Snow Queen trophy | "All trophies" skipped meta 4. |
| 52 BiblioCraft Library | task: Clipboard → Shelf (any wood) | Quest 2 hands out the Clipboard, and the text asks for a shelf. |
| 13, 49, 57 | text rewritten to match the task | 13 named King Scales (the recipe uses the Royal sword), 49 a mob hat (task: Hat Stand), 57 a Fryer (task: Grill). |
| 300, Pets tab | "Workshop tab" removed | They are their own tabs. |
| 406 Rahovart, 421 Book of Scale, 431 Pick a Class | text | "Late-game on purpose" (it opens at iron); a Lost World quest that does not exist; a Book of Unlearning that is disabled. |
| Tab 19, quests 4 and 401, tab 0 | "Beastiary" → "Bestiary" for the tab | Lycanites' own GUI really is spelled "Beastiary", so text pointing at that GUI says "Lycanites' Beastiary". |
| 46, 47, 64, 90, 91, 92, 194, 195, 204 | "a Anvil" → "an Anvil", etc. | |

**Rewards replaced in WP-1:**

| Quest | Old | New | Why |
|---|---|---|---|
| 140 Doomsday Scroll | `TragicMC:swordOfJustice` | `TragicMC:celestialAegis` | Creative-tab debug sword. The Celestial Aegis is TragicMC's own endgame blade, registered in its Survival tab (checked in the jar). |
| 144 Doombringer | `TragicMC:bowOfJustice` | `TragicMC:celestialLongbow` | Creative-tab debug bow. The Celestial Longbow is in the Survival tab. |
| 141 Witch of the Wild | `witchery:infinityegg` | Sealed Tome (Epic) | Creative infinite altar power. Epic is the top of the Act III tome band (4.5). |
| 431 Pick a Class | `levelup:xpTalisman` (unregistered) | Sealed Tome (Common) | Disabled in `levelup.cfg`; showed as a placeholder. Icon `levelup:respecBook` → experience bottle. |
| 300 Hall of Heroes | `legends:superDex` (unregistered) | removed | Showed as a placeholder. |
| 18 Ur-Ghast | Ur-Ghast trophy (choice) | Sealed Tome (Rare) | The trophy is already in the boss chest, and it part-filled quest 62. Rare = one per TF boss quest (progression audit §5). |
| 19 Snow Queen | Snow Queen trophy (choice) | Sealed Tome (Rare) | The trophy is now the proof. |
| 33 Take Flight | 1 `mcheli:fuel` | removed (the wrench stays) | Completed 434 "Keep It in the Air". |
| 401 Soulgazer | 2 Warg Treats | 1 Name Tag | Completed 402. |
| 402 Bribery Works | 1 Soulstone | 2 Leads | Completed 403. |
| 403 Soulbound | 1 Soulkey | 8 Bottles o' Enchanting | Completed 404. |

**Left for later, on purpose:** the chapter-order texts (Ch 4 "after Twilight", Ch 6, Ch 8 "after
the titans") describe the order WP-3 will enforce, so they wait for it. "Wear it" in 4 and 6 is
untouched. `tools/pack-fixes/quest-55/README.md` is outside this pass's files; it still needs
its "historical" note. Two cheese warnings remain where the reward completes an *unrelated*
quest, not the next one: 118 → 113 (Endium) and 303 → 300 (Electronics).

### WP-2 (tier leaks)

**Rewards replaced in WP-2:**

| Quest | Old | New | Why |
|---|---|---|---|
| 134 Dimensional Key | choice: Overlord Helm / Overlord Plate / Overlord Amulet | choice: 1 Epic loot bag / 2 Rare Sealed Tomes / 2 enchanted golden apples | The final boss's armour for crafting the key to its house (example B, 4.7). The armour waits for a WP-4 "Overlord" hunt quest. |
| 24 The Queen | 64 Queen Scales (choice) | 4 Queen Scales | One Red Matter per scale. Note: the Queen herself drops **56** scales and a Royal sword per kill (`TheQueen.func_70628_a`), so the kill, not the quest, is the real supply. |
| 22 Mobzilla | 32 Mobzilla Scale Blocks (choice) | 4 | Mobzilla drops 50–79 scales (5–8 blocks) per kill; 32 blocks was four to six kills. |
| 13 Dark Matter | 3 Dark Matter | 1 | Rewarding the first craft with triple the gated material. |
| 34 Red Matter | 4 Red Matter | 1 | Same. |
| 6 Diamond Gear | ProjectE Zero Ring (choice) | Sealed Tome (Uncommon) | A ProjectE item before the Lich. The tome introduces the pack's own enchant system at Act I's band. |
| 21 Ultimate Gear | Ultimate Pickaxe + Ultimate Bow | 1 Rare loot bag + 8 Bottles o' Enchanting | Two more Ultimate pieces at OreSpawn step 2, before Mantis, Basilisk and Kraken. |
| 107 Road to Torment | Death's Robe (choice) | Witches Robes (`witchery:witchrobe`) | Part of the Death set, which Witchery's Death boss drops. |
| 137 Time and Corruption | The Titan (choice) | Sealed Tome (Epic) | A top-tier named weapon at mid-chapter. |
| Pets (55) + Heroes (101) | 2–16 Lucky Blocks per quest, 554 in all | 1 per completion quest (47 hero Full Sets, the 4 legendary pets, Costume Closet, Iron Man Mark 21), 0 elsewhere: **53** | J4. At ~1.5–2% Ultimate-tier per block, 554 ungated blocks were ~10 Ultimate pieces before any boss. |
| Pets + Heroes | 1 loot bag per quest | 1 bag, **one tier lower** (Common stays Common); Legendary only on the 4 legendary pets, the Costume Closet and Mark 7 | 104 bag stacks lowered. Ungated Epic bags in these tabs: 11 → 0. |

**`qb.py tally` after WP-2 (pack):** Lucky Blocks in the whole book 765 → 264; ungated
100 (Heroes 49, Pets 4, and 47 outside these tabs: Secret 73 "Dimensional Traveler" 30,
Exploration 7, Danger Zone 5, Rewards 5). Ungated Legendary bags: only 67, 83, 208, 215,
301, 305. Still ungated and untouched: 68 golden apples, 12 diamonds and 2 diamond blocks in
Pets; Epic bags in 107, 119, 121, 134, 141–144 and 405, which sit behind chapters that WP-3
gates properly.

### Validation, WP-1 and WP-2 (2026-10-17)

`qb.py check` passes on both books. One slim **server** trial (`trial.py build quests --server
--overlay pack` with qfcontent, Twilight, TragicMC, Witchery, OreSpawn, ProjectE, Railcraft,
Lycanites, BiblioCraft, MCHeli, Legends, Inventory Pets, Loot Bags, Lucky Blocks, Hat Stand,
Food Plus, `--bundle quests --bundle inspect`). A server, not a client, because BQ only reads
`DefaultQuests.json` when a world starts; a client at the title screen never parses it. Ready
in 25 s, no ERROR lines in `logs/latest.log`. The saved `world/betterquesting/QuestDatabase.json`
had all 308 quests at `pack_version` 6, and **no item introduced by WP-1/WP-2 became a
placeholder**. The placeholders that remain in edited quests are old items from mods left out of
the trial (Colorful Mobs, Food Expansion, Custom NPCs, Statues, The Jungle) plus `mcheli:bell47g`,
an MCHeli aircraft item that a dedicated trial server does not register.

### WP-3 (chapter order)

`tools/quests/patches/wp3_chapter_order.py`. Quest 6 Diamond Gear used to open Twilight, the
End, OreSpawn, TragicMC and ICBM at once (J1). Now each numbered chapter opens strictly after
the one before it, and `qb.py path` (new, and part of `check`) fails if that stops being true.

**Prerequisites changed:**

| Quest | Old | New | Why |
|---|---|---|---|
| 9 Witchery: The Altar (Ch 4 entry) | 5 Diamond Dreams | 15 Naga | The line text says "after Twilight on purpose"; it opened before Ch 3. |
| 56 HEE: Enhanced End (Ch 6 entry) | 6 | 17 Hydra **and** 105 Circle Talisman | The Act II finale of 4.1: the Old Powers answer, then the End opens. |
| 20 OreSpawn: First Contact (Ch 7 entry) | 6 | 114 Endstone Temple | The audit's first choice. 121 would put the dragon in front of Mothra. |
| 74 Mantis | 21 Ultimate Gear | 20 | Follows from the next row. |
| 21 Ultimate Gear | 20 | 79 Kraken | J2: Ultimate after the minibosses that justify it. Moved to (96,96) in the tab. |
| 22 Mobzilla | 79 | 21 | "Ultimate gear is the minimum." |
| 58 TragicMC: Embrace Doom (Ch 8 entry) | 6 | 22 Mobzilla | Line text "After the titans"; now "after the first titan". |
| 150 ICBM: Pocket Warcrime | 6 | 6 **and** 126 Railcraft Blast Furnace | Off the quest-6 hub. ICBM joins the Engineering line (4.4) at steel. |
| 12 / 13 / 34 ProjectE | 22 / 23 / 24 | + 11 / + 12 / + 13 | Each rung also needs the rung before, as the recipes do. |
| 401 The Soulgazer (Bestiary entry) | 4 Armor Up! | 6 | As proposed. |
| 405 A Box That Should Stay Shut | 404 | 404 **and** 22 Mobzilla | The Rahovart summon (J9) and its Epic bag wait for Mobzilla; 406 inherits it. It sits on 405 rather than 406 so the book does not suggest the summon at iron. |

**Chapter order now** (`qb.py path`, pack book; "first" is how many quests must be done before the entry unlocks):

| Chapter | Opens at | After | First |
|---|---|---|---|
| Ch 1 Start | 0 Welcome | — | 0 |
| Ch 2 Base | 7 / 8 | 2 Crafting Station | 3 (side tab, not in the chain) |
| Ch 3 Twilight | 14 The Pool at Dusk | 6 Diamond Gear | 7 |
| Ch 4 Witchery | 9 The Altar | 15 Naga | 9 |
| Ch 5 Dark Paths | 43 / 44 / 45 / 106 | 105 Circle Talisman | 20 |
| Ch 6 The End | 56 Enhanced End | 17 Hydra + 105 Circle Talisman | 23 |
| Ch 7 OreSpawn | 20 First Contact | 114 Endstone Temple | 28 |
| Ch 8 TragicMC | 58 Embrace Doom | 22 Mobzilla | 35 |
| Ch 9 ProjectE | 11 Philosopher's Stone | 16 Lich | 10 (a ladder; its last rung, Red Matter, needs 40) |

Ch 5 and Ch 6 both hang off the Circle Talisman, as Act III of 4.1 puts Dark Paths beside the
End. Ch 6 does not need Ch 5's last quest.

**Visibility.** The semantics come from BQ 3.0.328 `QuestCache.isQuestShown` and `GuiQuestLines`.
The seven lines Ch 3–9 went from `ALWAYS` to `UNLOCKED`, which hides a tab until one of its
quests is unlocked. Their 68 quests went from `ALWAYS` to `NORMAL`, which shows a quest once it
is unlocked or once all its prerequisites are, so the next step shows one step ahead. Side tabs
stay `ALWAYS`. Only their end-game quests went to `NORMAL`: 62 Trophy Collector, 63 Pack Master,
and 405 and 406 (Rahovart). In a fresh world the visible tabs are Ch 1, Ch 2, every side tab
and the empty Secrets tab.

**Texts:**
- Ch 4: "sits after Twilight" became "opens once the Naga is dead".
- Ch 6: "comes after the craft" now names the Hydra and the Talisman, and says the OreSpawn gods wait for its temple.
- Ch 7: says it opens at the Endstone Temple.
- Ch 8: "After the titans" became "After the first titan: this road opens when Mobzilla is dead".
- 405: says the page waits for Mobzilla.

### WP-4 (boss proofs)

`tools/quests/patches/wp4_boss_hunts.py`. Every hunt target is in `tools/quests/entities.json`
with the class it maps to and where the name came from: the mod's registration call in the jar.
`qb.py hunt` (new, and part of `check`) fails on any other name. Standard Expansion's
`TaskHunt.readFromNBT` only reads the string, so **there is no load-time validation of a hunt
target**. A misspelt one would load without a log line and never complete. The names were
therefore also confirmed at runtime in the server trial below.

A hunt kill counts for every member of the killer's party (`ParticipantInfo.ALL_UUIDS`). Kills
by pets, minions or the environment do not count.

| Quest | Old task (retrieval) | New task | Entity |
|---|---|---|---|
| 14 The Pool at Dusk | Twilight Oak log | **location**: dimension 7, anywhere | — |
| 15 Naga | 5 Naga Scales | kill 1 | `TwilightForest.Naga` |
| 16 Lich King | Lich Scepter | kill 1 | `TwilightForest.Twilight Lich` (his shadow clones take no damage, so they cannot be counted) |
| 93 Minoshroom | Meef Stroganoff | kill 1 | `TwilightForest.Minoshroom` |
| 17 Hydra | 3 Fiery Blood | kill 1 | `TwilightForest.Hydra` (multi-part, but every part passes the player's DamageSource on) |
| 94 Knight Phantom | Phantom Helm OR Plate | kill 6 **OR** Phantom Helm **OR** Phantom Plate | `TwilightForest.Knight Phantom` |
| 18 Ur-Ghast | Fiery Tear | kill 1 | `TwilightForest.Tower Boss` |
| 95 Alpha Yeti | 4 Alpha Fur | kill 1 | `TwilightForest.Yeti Boss` |
| 19 Snow Queen | her trophy | kill 1 | `TwilightForest.Snow Queen` |
| 121 The Dragon Reborn | Dragon Egg + Enderman Head | kill 1 **OR** 1 Dragon Essence (`HardcoreEnderExpansion:essence@0`) | `HardcoreEnderExpansion.Dragon` |
| 22 Mobzilla | 5 Scale Blocks | kill 1 | `Mobzilla` |
| 23 The King | Royal Guardian Sword | kill 1 | `The King` |
| 24 The Queen | Queen Scale | kill 1 | `The Queen` |
| 406 Rahovart | Demon Crystal | kill 1 | `demonmobs.rahovart` |
| 28 Mutant Creatures: The Hunt | Skeleton Part | kill 1 | `MutantCreatures.MutantSkeleton` |
| **450 TragicMC: The Overlord** (new, Ch 8, after 134) | — | kill 1 | `TragicMC.OverlordCore` |
| **451 Mutant Zombie** (new, Gadgets, after 28) | — | kill 1 | `MutantCreatures.MutantZombie` |
| **452 Mutant Creeper** (new, Gadgets, after 28) | — | kill 1 | `MutantCreatures.MutantCreeper` |
| **453 Mutant Enderman** (new, Gadgets, after 28) | — | kill 1 | `MutantCreatures.MutantEnderman` |

**Why the names have these forms:**
- OreSpawn's names are the plain ones because it calls `registerGlobalEntityID` before `registerModEntity`. FML only adds the `modid.name` alias for a class that has no name yet.
- TF's `creatureCompatibility` is declared but never set, so TF registers only `TwilightForest.*` names.
- HEE's End spawns its own `EntityBossDragon` (`BiomeDecoratorHardcoreEnd`), not the vanilla `EnderDragon`.
- `subtypes` is on (BQ's default), so a hunt also credits subclasses. None of these targets has a subclass in the pack. The trap runs the other way: the Ur-Ghast extends `Tower Ghast` and the Minoshroom extends `Minotaur`, so those base names must never be targets.

**Item proofs kept as an OR alternative, and why:**

- **94 Knight Phantom.** The boss is six entities (`TileEntityTFKnightPhantomsSpawner` makes
  6). If one of them dies to anything but a player, the count stops at five for that
  stronghold for good. The vault chest's Helm or Plate still proves the fight.
- **121 HEE Dragon.** There is one dragon per fight, and only the killer's party is credited.
  A friend who was not in the party, or who joins later, could never finish the quest. The
  dying dragon sheds Dragon Essence (`DragonRewardManager`: `ItemStack(essence, n, 0)`), which
  can be shared. The essence replaces the Dragon Egg, which exists only once.

No other quest keeps an item proof:
- The Overlord is repeatable: a Synapse Core block placed in the Synapse summons it again (`BlockSynapseCore`).
- Rahovart is summoned by a cube.
- The OreSpawn titans' head entities pass the player's damage to the body (`KingHead.attackEntityFrom`).

The drops that later quests need still have to be collected. 12 asks for the Transmutation
Table, which needs Mobzilla scales. 13 asks for Dark Matter, which needs the Royal sword; the
King drops it with his armour (`TheKing.func_70628_a`). 34 asks for Red Matter, which needs a
Queen Scale.

**New quests and their rewards:**

| Quest | Reward | Note |
|---|---|---|
| 450 The Overlord | choice: Overlord Helm / Overlord Plate / Overlord Amulet | The armour WP-2 took off 134, now earned by killing the final phase. `NORMAL`, main line. |
| 451 Mutant Zombie | 1 Common loot bag + 8 Bottles o' Enchanting | 29 Hulk Hammer now follows it, because the Zombie drops the hammer. 29 moved to (144,96). |
| 452 Mutant Creeper | choice: Common sealed tome / 8 Bottles o' Enchanting / 1 Common loot bag | Side-tab budget (4.5): one bag tier below Act I. |
| 453 Mutant Enderman | choice: Uncommon sealed tome / 16 Ender Pearls | The hardest of the four. |

**Texts.** Each quest's last (`§e`) line now says what the task checks, for example "Kill the
Naga.", "Kill all six Knight Phantoms, or bring back the Phantom Helm or Plate from the vault
chest." and "Kill the dragon, or bring back Dragon Essence from the fight." Sentences that
described the old proofs were removed:
- 14: "a log is the proof".
- 19: "her trophy is the proof".
- 121: the Enderman Head, and "the egg is yours".
- 23 and 13: the claim that the King drops no souvenir. He drops the Royal sword and the Royal armour.
- 406: the Demon Crystal receipt.

**Not converted, on purpose:** the OreSpawn minibosses (74, 77, 78, 79) and Mothra (20) still
ask for one of their drops. They are outside WP-4's list, and their drops come only from them.
Their names are already verified if a later pass wants hunt tasks there: `Mantis`, `Basilisk`,
`Emperor Scorpion`, `The Kraken` and `Mothra`.

**Server book.** Every WP-3 and WP-4 edit fitted the server copy, so nothing was skipped. It
has all the quests and lines these patches touch. The new IDs 450–453 are free in both books.
The server book now has 316 quests, against 312 in the pack.

### Validation, WP-3 and WP-4 (2026-10-17)

`qb.py check` passes on both books, with the new `hunt` and `path` checks included.

One slim **server** trial, `qbtest`:
- Built with `trial.py build qbtest --server --bundle quests --overlay pack` and qfcontent, Twilight Forest, TragicMC, OreSpawn, HEE, Lycanites, Mutant Creatures, Witchery, ProjectE, Railcraft and Loot Bags.
- Two boots of 3 GB each, 11–14 s to ready. **0 ERROR lines** in either log.
- `fml-server-latest.log` shows `Loaded 312 quests` and `Loaded 20 quest lines`.

**Entity names.** BQ has no load-time check for hunt targets, so the second boot ran
`/qfcensus find` for each mod. It lists the keys of `EntityList.stringToClassMapping`, the map
BQ looks targets up in. All 18 targets were present.

**Round trip.** BQ writes `QuestDatabase.json` only when its database is dirty, so the second
boot also ran `bq_admin default save` before `stop`. That makes BQ write the database it
parsed back over the trial's `DefaultQuests.json`. Compared with the repo book, the written-back
copy had:
- `pack_version` 8, 312 quests and 20 lines;
- identical prerequisites, visibility, task logic, names and texts;
- identical tasks: each hunt target and count, and the location task's dimension 7, as written;
- the new rewards as written.

The only differences were `betterquesting:placeholder` stacks for items from mods left out of
the trial (Storage Drawers, MCHeli, ICBM, Lucky Blocks, Legends and so on). A hunt task whose
keys BQ had not read would have come back targeting `Zombie`, its default.

Not yet done: the in-game kill test WP-4 asks for, which is to spawn each boss from an egg,
kill it and watch the task tick. It needs a client. The co-op check belongs to WP-9.

## Appendix: reproduction notes

- **Registry snapshot:** `saves/Stress Test/level.dat` (2026-10-16, 141 mod IDs) → 9,394 names. The older `Tryhard Run` save still contains HBM and lacks 39 newer mod IDs (Lycanites, ChocolateQuest, OpenBlocks, Sync…), so do not use it as the registry.
- **Scratch scripts** for this audit, possibly wiped with the temp dir:
  `C:\Users\a2dsu\AppData\Local\Temp\claude\c--Users-a2dsu-OneDrive-Desktop-quest-forge\f913a0d1-f36c-4b0f-b8a6-d180f0754584\scratchpad\quests\`
  (`nbtreg.py`, `analyze.py`, `dump.py`, `idcheck.py`, `graph.py`, `rewards.py`, `text.py`). WP-0 should absorb them.
- **Meta-sensitive facts checked against jars:**
  - Railcraft `EnumMachineAlpha`/`Beta` order.
  - TragicMC `WeaponSwordOfJustice` uses the Creative tab.
  - Witchery `BlockInfinityEgg` uses the creative tab and is referenced only by `TileEntityAltar`.
  - `levelup.cfg` item toggles.
  - `ChestTransporter.cfg` spawner pickup.
- **Not checked offline:** Witchery `ingredient` metas (25, 27, 34, 156, 163), TF trophy metas, OreSpawn entity names and recipes, BQ party semantics. Each is flagged where it matters.
