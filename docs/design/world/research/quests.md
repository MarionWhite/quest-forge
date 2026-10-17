# Support beyond the quest book: research for an RLCraft-style light questline

Date 2026-10-17. Research only; nothing installed, launched or edited.
Tags follow the audit: **[verified]** = checked in a jar, config or source; **[likely]** = strong
inference; **[unverified]** = from web listings or memory, check before relying on it.

Jars inspected: `%APPDATA%\.crazycraft4\mods\` (BetterQuesting 3.0.328, StandardExpansion 3.0.181,
CustomNpcs.jar "1.7.10", RecurrentComplex 0.9.7.1.1, CraftTweaker 3.1.0, JourneyMap 5.1.4p2).

---

## 1. What exists

### 1.1 BetterQuesting features already in the pack (no new mod)

| Feature | Status | Notes |
|---|---|---|
| Hidden quests | **[verified]** `EnumQuestVisibility`: HIDDEN, UNLOCKED, NORMAL, COMPLETED, CHAIN, ALWAYS | `COMPLETED` = invisible until done (what Secrets uses). A root quest with no prereqs and `COMPLETED` visibility is a silent "discovery" that pops when earned. |
| Location task: dimension | **[verified]** fields `dim`, `posX/Y/Z`, `range`, `biome`, `structure`, `visible`, `invert`, `taxiCab`, `hideInfo` | `range <= 0` = anywhere in the dimension. Already used by WP-4 (`qb.py location()`). |
| Location task: biome | **[verified, GTNH source; same fields in 3.0.181]** | Matches the numeric biome ID under the player. Needs `dim` set too (dimension is always checked). One biome per task; use taskLogic OR for families. The repo has no biome-ID catalogue yet. |
| Location task: structure | **Broken for this purpose [verified in GTNH source; 3.0.181 calls the same `func_147416_a`]** | It passes when `findClosestStructure(name)` returns *anything*, i.e. as soon as one exists in the dimension, not when you are inside it. Vanilla 1.7.10 only answers "Stronghold" in the overworld **[likely]**. Mod structures (CQ castles, Roguelike, RC, Battle Towers) are invisible to it. Do not build Discovery on it. |
| Meeting task | **[verified]** entity id + optional NBT match (`targetNBT`, `ignoreNBT`), default `Villager` | Can target `customnpcs.CustomNpc`; matching one named NPC via NBT is **[likely, test]**. |
| Scoreboard task / reward, command reward | **[verified]** | The bridge for anything BQ can't see: another system sets a score, BQ reads it. 1.7.10 scoreboard criteria `achievement.<id>` / `stat.<id>` exist **[likely]**, so achievements (incl. Twilight's) can drive BQ. |
| Per-quest sounds, silent quests | **[verified]** `snd_complete`, `snd_unlock`, `snd_update`, `isSilent` | A distinct discovery chime (qfcontent already has sound assets). |
| Popup notices | **[verified]** `betterquesting.cfg` "Quest Notices"=true; `QuestNotification` class | Already on. This *is* RLCraft's "toast" feel. |
| Repeatable quests | **[verified]** `repeatTime` | A BQ-only bounty board is possible (repeatable hunt quests on a timer). |

**GTNH fork:** `GTNewHorizons/BetterQuesting` 3.8.92-GTNH, released 2026-10-12, maintained
([repo](https://github.com/GTNewHorizons/BetterQuesting),
[release](https://github.com/GTNewHorizons/BetterQuesting/releases)). It merges Standard Expansion
and adds `TaskOptionalRetrieval` and `RewardQuestCompletion`. Its `TaskLocation` has the **same
structure bug** (source lines 146–170). `@Mod dependencies = "after:gtnhlib@[0.10.7,)"`; GTNHLib
is compile-only, but the build declares GTNH NotEnoughItems as `implementation`, so it likely
expects GTNH NEI **[unverified]**. Per `docs/design/angelica-decision.md`, GTNHLib on a server
forces it onto every client and crashes OptiFine E7. Nothing in this report needs the GTNH fork;
stay on 3.0.328 until the E7 clients are gone.

### 1.2 Custom NPCs (installed, original Noppes 1.7.10)

**[verified from class and enum names in the jar]**:
- **Quests:** types Item, Dialog, Kill, AreaKill, Location (named Waypoint blocks). Completion is Instant or Npc. Repeats via `EnumQuestRepeat` (repeatable/daily/weekly **[likely]**).
- **Dialogs** with availability gates (other dialogs/quests read or finished, faction stance, day/night, min player level).
- **Factions** with points and stance.
- **Roles:** Trader, Bank, Transporter, Follower, Companion, Postman. **Jobs:** Guard, Healer, ItemGiver, Spawner, Bard, Conversation, ChunkLoader, Puppet.
- **Transporter = built-in fast travel.** `TransportLocation` has name/dim/xyz/type. `RoleTransporter` unlocks a location when the player comes in range (`transporter.unlock`), so it works like Waystones: discover a post, then travel between discovered posts.
- **Natural spawning:** `SpawnController` / `SpawnData` with biome lists and weights. Cloned NPCs can spawn naturally in chosen biomes (wandering traders, hermits, quest-givers).
- **Commands (op):** `/noppes clone spawn <name> <tab> [[world:]x,y,z] [newname]`, `/noppes quest start|finish <player> <id>`, `/noppes dialog read|unread`, `/noppes faction <player> <id> add|set …`. The clone parser uses vanilla's relative-coordinate helper, so `~` probably works **[likely]**.
- **Scripting:** per-NPC scripts (events INIT, TICK, INTERACT, DIALOG, DIALOG_OPTION, DAMAGED, KILLED, ATTACK, TARGET, COLLIDE, KILLS).
- Config: `OpsOnly=true` (good). `NpcUseOpCommands=false`, so a dialog's command option can't run op commands (e.g. `scoreboard`, `bq_admin`). Turning it on is safe while only ops can edit NPCs.
- Angelica: renders fine (`angelica-decision.md`, the `/summon customnpcs.CustomNpc` test).

**Placing NPCs in generated structures:** CNPC has no worldgen of its own. Two working routes:
1. **Recurrent Complex** (installed) has `BlockSpawnCommand` (runs a command when the structure generates) and `VanillaStructureGenerationInfo` (adds an RC structure as a **village component**, `baseVillageSpawnWeight=10` in `reccomplex.cfg`) **[verified classes and config]**. One RC village house with a spawn-command block running `/noppes clone spawn …` gives NPCs in villages. That the end-to-end chain works is **[likely, needs a trial]**.
2. CNPC natural spawns by biome (no structure needed).

**Maintained fork:** [KAMKEEL/CustomNPC-Plus](https://github.com/KAMKEEL/CustomNPC-Plus), pushed 2026-10-06. It adds party quests, profiles, many more script hooks and an economy. It replaces CNPC rather than adding to it, and world-data compatibility and Angelica/Java 25 behaviour are **[unverified]**. Not needed for the work below. `docs/design/platform-decision.md` already tracks it.

### 1.3 Landmark structures

| Mod | 1.7.10? | Notes |
|---|---|---|
| Recurrent Complex (installed) | yes | 106 bundled structures, maze dungeons, village components, spawn-command blocks, inventory generators, and **poems** (`structures/active/poems/*.rcpt`). Known Java 25 issue: 4 inventory generators fail under lwjgl3ify's Gson 2.10 (`angelica-decision.md`, 2–3 h fix). |
| ChocolateQuest, Roguelike, Doomlike (installed) | yes | Already the landmark layer. GTNH maintains Roguelike: [GTNewHorizons/Roguelike-Dungeons](https://github.com/GTNewHorizons/Roguelike-Dungeons) (pushed 2026-10-12). |
| AtomicStryker Battle Towers / Ruins | **jars exist**: `BattleTowers-1.7.10.zip`, `Ruins-1.7.10.zip` in the archived [atomicstrykers-files](https://github.com/kevinvanrijn/atomicstrykers-files/tree/master/files/1.7.10) (read-only since 2022) | Unmaintained; not in the GTNH org. Battle Towers adds a visible landmark with a golem boss, a good RLCraft-style beacon. Angelica/Java 25 untested. Ruins overlaps RC. Not needed: RC + CQ already cover landmarks. |
| VillageNames (GTNH fork) | yes, [GTNewHorizons/VillageNames](https://github.com/GTNewHorizons/VillageNames), upstream active | Named villages and villagers; villagers write books with hints toward strongholds and temples. A good fit for flavour. Sides and deps **[unverified]**; it changes villager skins and trades. |

### 1.4 Fast travel

- **Waystones-X**: an unofficial 1.7.10 fork, Forge, client+server, **requires UniMixins**, with configurable XP cost, cooldown and village worldgen rules ([Modrinth](https://modrinth.com/mod/waystones-x), source [AngelicIndustries/WaystonesFork](https://github.com/AngelicIndustries/WaystonesFork)). 1.0.15, June 2026 **[unverified, from listings]**. Not in the GTNH org.
- **Already installed, no new mod:** CNPC Transporter (above). qf-commands `/home` and dimension **lottery tickets** (`Unlockables.java`: "the command can never skip the quest"). Ender Utilities porters. Witchery waystones and teleport rites.
- **Conflict to decide:** the pack's travel design is *earned and scarce* (tickets). Free waystone networks undercut it. The CNPC Transporter fits better because ops choose where the posts are.

### 1.5 Bounty boards

No 1.7.10 bounty-board mod found. ("Bountiful" is 1.12+ **[unverified]**.) Equivalents in the pack:
- CNPC repeatable Kill/AreaKill quests from a "Bounty Clerk" NPC (or a CNPC Big Sign/board next to it).
- BQ repeatable hunt quests with `repeatTime`.

### 1.6 Lore books in loot

- **CraftTweaker 3.1.0:** `vanilla.loot.addChestLoot` / `removeChestLoot` **[verified, `ILootRegistry` in the jar]**. Written books with NBT go into ChestGenHooks categories (dungeonChest, strongholdCorridor, villageBlacksmith, pyramid…). It only reaches chests filled through ChestGenHooks. Twilight uses its own `TFTreasure`; Roguelike and CQ use their own tables **[likely]**.
- **Recurrent Complex:** `customBookChance` / `customBookTag` in `reccomplex.cfg` (both off), plus poem files **[verified that the keys exist; the semantics, "inject tagged books into vanilla chests", are likely]**. This path is exposed to the Gson bug under Java 25.
- A BQ retrieval task can require a specific lore book (NBT-matched retrieval) **[likely]**, turning a found page into a hidden quest.

### 1.7 Achievements

- Vanilla and mod achievements exist (Twilight has its own page). BQ has no achievement task, but a scoreboard objective with an `achievement.<id>` criterion plus a `bq_standard:scoreboard` task bridges them **[likely]**.
- GTNH: [Amazing-Trophies](https://github.com/GTNewHorizons/Amazing-Trophies) (config-defined achievements and trophies) and [BetterAchievements](https://github.com/GTNewHorizons/BetterAchievements). Triggers, sides and deps are **[unverified]**. Low value next to BQ.

### 1.8 JourneyMap

- Installed 5.1.4p2. GTNH maintains a fork, [journeymap-legacy](https://github.com/GTNewHorizons/journeymap-legacy) (tags like 5.1.4p8), and [Navigator](https://github.com/GTNewHorizons/Navigator) (a map-layer API for JM/Xaero).
- Share-Where-I-am ([repo](https://github.com/GTNewHorizons/Share-Where-I-am)) shares waypoints in chat. Deps **[unverified]**.
- No server-pushed waypoints in 5.1.4 found **[unverified]**. A quest can't drop a waypoint.
- Practical integration: quest text gives coordinates or directions; rewards hand out the Twilight magic map or vanilla maps.
- The performance plan drops JM only in the potato profile.

---

## 2. Fit with the audit plan, and proposed work packages

### What fits without conflict

- **Hidden Discovery quests** are the Secrets mechanism (`COMPLETED` visibility) applied to places. They fit 4.1's "the Queen is a rumour" and 4.5's ticket rule: dimension tickets "only from a quest that proves you *arrived*". A location quest is exactly that proof.
- **CNPC quest-givers** are already suggested in audit 1.3 ("could carry quest-giver NPCs") and in `server-readiness.md` (a CNPC greeter at the hub, an optional trader).
- **Lore books** extend the 4.7 voice (hooks, role-attributed quotes) into the world.
- **Not recommended now:** the GTNH BQ fork (GTNHLib/NEI lock-in versus E7 clients), Waystones-X (undercuts tickets; a new both-sides mod), Battle Towers/Ruins (unmaintained, untested, redundant with RC/CQ).

**Conflicts to respect**
- `qb.py lint` requires Secrets to stay the last tab, so a new Discovery tab goes before it.
- Structure Discovery can't use the location task's structure field (1.1). Use proxies: the boss hunt (CQ, already in WP-7 Castles), a structure-unique loot item, or a scoreboard set by a spawn-command block.
- Rewards must follow the 4.5 budgets. Discovery pays utility or flavour, never power.

### Proposed work packages (small, in order)

**WP-D0: biome and dimension ID catalogue (≈1 h).** Discovery biome tasks need numeric IDs, and the repo has none (`docs/survey/dimension-names.tsv` covers dimensions only). Dump `BiomeGenBase.biomeList` from a slim server trial: extend the untracked `qf-content` `debug/ItemDump`, or add a `qb.py biomes` parser for its output. Output: `docs/survey/biome-ids.tsv`. These IDs are config-dependent (OreSpawn and TragicMC biome IDs were changed in 699e27e), so regenerate after config changes.

**WP-D1: `Discovery` hidden tab (≈10–14 quests, one session).**
- Root quests, visibility `COMPLETED`, no prereqs, one `bq_standard:location` task each, a distinct `snd_complete`.
- Arrivals:
  - Nether (−1). This also covers the missing Nether quest from audit 1.3.
  - The End (1), Twilight (7), Lost World (−42), one OreSpawn dimension, two or three Legends dimensions (IDs from `dimension-names.tsv`).
  - 4–5 biome families via taskLogic OR: mushroom island, mesa, ice spikes, a Twilight biome such as Dark Forest or Snow, one Lycanites-relevant biome group.
- Rewards: the matching dimension lottery ticket where `Unlockables.java` defines one, else a Common or Uncommon loot bag, a map or a Common sealed tome.
- Text: one-line hook plus a rumour pointing at what lives there, per 4.7.
- Validate: `qb.py check`, then a slim server trial: `/tp` into each dimension and biome and confirm the popup. Uses the existing `location()` helper.

**WP-D2: lore pages (≈2–3 h, after D1).**
- 6–8 written books in the Chronicle voice, each hinting at one act's boss or dimension.
- Inject through CraftTweaker `vanilla.loot.addChestLoot` into `dungeonChest`, `strongholdCorridor`, `pyramidDesertyChest` and `villageBlacksmith` at low weight. Not RC, because of the Java 25 Gson bug.
- Optional: one hidden BQ retrieval quest "The Chronicle Has Pages" (find any 3).
- Validate: `/give` a book and confirm the NBT retrieval match; a slim trial to confirm loot appears.

**WP-N1: the Chronicler and the bounty clerk at the hub (≈half a day, server-side data).**
- Op-built CNPC NPCs at spawn (the hub from `server-readiness.md`):
  - A **Chronicler** with a dialog tree that explains the Acts (helps WP-5 onboarding without adding book quests).
  - A **Bounty Clerk** with 3–5 repeatable Kill/AreaKill quests (zombies at night, a Lycanites family, an Infernal mob) that pay lottery tickets or Common bags. This is the bounty board.
- BQ bridge: one BQ quest with a `meeting` task on the Chronicler (Prologue "Into the Chronicle"), or a token item the NPC gives that BQ retrieves. Don't rely on dialog commands unless `NpcUseOpCommands` is turned on.
- Deliverable: the CNPC data from the world's `customnpcs/` folder (dialogs, quests, factions, clones) checked into the server template that `tools/server/build_play_server.py` copies.
- Validate on a slim server trial.

**WP-N2: NPCs in villages (≈half a day, after N1; trial first).**
- One small RC village component ("Waystation") with a spawn-command block running `/noppes clone spawn Pathfinder QF ~,~1,~`.
- The clone is a CNPC **Transporter** (posts unlock when you walk past) plus a couple of "rumour" dialogs that point at nearby landmarks.
- Gives RLCraft-style travel between discovered villages without a new mod. Keep it overworld-only so the dimension tickets keep their value. Final call is the author's (balance needs approval).
- Risks: clone storage must ship with the server template; whether relative coordinates work in `clone spawn` is unverified; RC structure files are fine, but check the Gson issue under Java 25.

**WP-D3 (optional): structure discoveries via proxies.** Fold into WP-7 Castles/Dungeons. Use hunt tasks on CQ bosses, Roguelike/Doomlike unique loot, or a spawn-command block that sets a scoreboard for a `bq_standard:scoreboard` task. Do not use the location task's structure field.

**Deferred:** GTNH BetterQuesting (revisit once no E7 clients remain); Waystones-X (only if the author wants free travel); Battle Towers (only after a slim Angelica + Java 25 trial).
