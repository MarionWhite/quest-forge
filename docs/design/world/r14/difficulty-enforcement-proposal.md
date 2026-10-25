# r14 — Making the game as hard as the difficulty map: a proposal

**Status:** proposal for the author's approval. Nothing in the pack changes until the author says yes
(balance and gameplay changes need the author's explicit yes).
**Date:** 2026-10-25
**Inputs:** [`difficulty.md`](difficulty.md) and [`difficulty.yaml`](difficulty.yaml) (tiers, hot zones,
spawns), `C:\qf-world\renders\r14-difficulty.png`, the [progression audit](../../progression-audit.md),
the [questline audit](../../questline-audit.md), decision [0003](../../../decisions/0003-designed-world.md),
the pack's spawn and mob configs under `pack/config` (read-only), and the mob census
`C:\qfs\c1\config\qfcontent-census-mobs.tsv` (16 Oct, 564 entities).

> **Every number in this document is a proposal**, unless it is marked **[E]** (read from a
> config file or measured by the census). The proposed numbers are starting points for the
> measurements in §7. None should go into the pack before those measurements and the author's yes.

## The author's decisions (2026-10-25)

The mechanism (hybrid: biome spawn tables plus a position hook) is **approved**, and these
decisions override the rest of this document:

1. **No T1.** The tiers are T2 to T6. Spawn pockets use the **T2** numbers. They stay **small** and
   are only easy enough for the very early game, while players get their bearings and their
   starter kit online.
2. **The T2 to T6 numbers are accepted as starting points, but they must be tested**, armour-ignoring
   damage above all. Hard constraints for that tuning:
   - In **Royal Guardian** gear, a player should die only to the strongest enemies in the pack.
   - **Ultimate** gear should feel like a big boost in defence, not invincibility.
   - **Player damage is part of the equation.** If Ultimate one-shots everything, mob damage stops
     mattering. Offence and defence are tuned together (with the enchant census and the combat
     campaign).
3. **Spawners** use the tier of the place they stand in. **Player-made spawners** (Soul Shards cages
   and similar) are **always T3**.
4. **Lycanites world events** are suppressed inside the spawn pockets.
5. **No ward blocks.** Players cannot lower the tier around their base.
6. The other defaults are accepted:
   - today's pack is the T3 baseline;
   - caves count one tier harder;
   - only T6 mobs are faster;
   - part of T6 damage ignores armour (subject to point 2);
   - the outskirts get harder with distance;
   - enchant-tome odds follow the enchant census;
   - the mechanism ships first with every multiplier at 1.0, and the numbers are tuned after the
     census.

---

## 0. Summary

- **Recommendation: a hybrid (option c).** The biome decides *what kind* of mob spawns, and the map
  position decides *how dangerous* it is.
  - **Biome → family.** The JustAnotherSpawner (JAS) tables stay keyed by biome. They have to be
    rebuilt anyway for the BoP biome names, and they give each region its flavour: Lycanites desert
    mobs in deserts, arctic mobs on the ice.
  - **Position → tier.** A small, server-only qf-content module, `DifficultyGrid`, reads a baked
    tier grid (one byte per chunk) and does four things. It filters which mobs may spawn at that
    tier. It thins spawns in low tiers. It scales health and damage. It sets InfernalMobs elite odds.
- **T3 is today's game.** Most of the land is T3, and it keeps the pack's current tuning
  unchanged: MobProperties ×4–10 health and ×1.5–3 damage on ordinary mobs, and elites at 1 in 15
  **[E]**. T1 and T2 sit *below* today, and T4–T6 sit above it. The census numbers therefore remain
  the truth for 45% of the land, and nothing is inflated across the board.
- **One trap shapes the high tiers.** In 1.7.10, 25 armour points stop all normal melee and
  projectile damage. Ultimate armour (34) and Royal (42) are therefore immune to ordinary hits
  **[E]**. A damage multiplier alone cannot make T5 and T6 hard for late-game players. Those tiers
  have to get their danger from damage that ignores armour: Lycanites piercing and effects, magic,
  fire, wither and poison, and InfernalMobs modifiers. Faster armour wear also helps.

---

## 1. What the pack does today

| Tool | What it controls | Keyed by | Today's setting **[E]** |
|---|---|---|---|
| **JustAnotherSpawner 0.17.8** | Which mobs spawn, by weight and pack size; caps per creature type | biome name, per dimension profile | Vanilla spawn lists emptied, vanilla chunk spawning off. MONSTER cap 70, spawn distance 6 chunks. 141 biome keys, **none of them `biomesoplenty.*`**: the live pack has no BoP yet. Spawn and despawn **tags** are MVEL expressions that can read `posX`/`posY`/`posZ`. JAS calls Forge's `canEntitySpawn`, so `LivingSpawnEvent.CheckSpawn` fires for its spawns. |
| **Lycanites Mobs 1.13.0.5** | Its own spawners (fire, storm, darkness, lunar, underground, …) plus biome spawns through JAS; world events; subspecies | biome tags, dimension, light, block type | Difficulty multipliers only per *world difficulty* (Hard ×1.1). Subspecies uncommon 20/400 with ×4 health. **No level scaling exists in this version.** Mob events from day 0 (some from day 10). |
| **MobProperties** | Health and damage modifiers, drops, NBT, per entity, via JSON | entity; conditions include `in_biome_`, `in_dimension_`, `below_` (y), `beyond_` (distance from the *single* world spawn), `check_nbt_` | **Every ordinary mob gets ×(1 + 3~9) health and ×(1 + 0.5~2) damage** (operator 1); bosses get ×(1 + 2~5) health. That covers 312 and 292 files. It applies from a queue a few ticks after spawn. |
| **InfernalMobs** | Elite, ultra and infernal promotions with modifiers (Wither, Rust, Lifesteal, Vengeance, …) | global; whitelist per entity | `eliteRarity=15`; ultra 1 in 7 elites; infernal 1 in 7 ultras. `maxOneShotDamage=10`, anti-farm on. Rolls on `EntityJoinWorldEvent`. No per-dimension or per-position setting. |
| **KillerPacman WeaponScaler** | Player melee ×U(1,4) on non-OreSpawn weapons | global | Kept (author). It makes player damage noisy, so TTK targets need medians. |
| **LevelUp** | Player skills | — | ×1.5 XP per level, 5 skill points lost on death. XP from kills feeds it, so an XP multiplier by tier is also a LevelUp multiplier. |

**What this means for today's balance.** From the census **[E]**, median health is: vanilla Creeper
132, Skeleton 149, Spider 106 (vanilla value 20 or 16), Lycanites mobs median 119, TragicMC mobs
median 213, Mutant Creatures 551–1,474. The pack is already *uniformly hard*. Today, the first night
at spawn is as dangerous as the far north. The map wants the opposite gradient.

## 2. The core problem, and the three options

Difficulty is a map layer (`difficulty.png`, one tier per 32-block plan pixel). Every spawning and
scaling tool above is keyed by biome, dimension, light or the one world spawn point.

| | (a) Tiers onto biomes | (b) Position hook only | **(c) Hybrid (recommended)** |
|---|---|---|---|
| **How** | Give each tier its own biome set; JAS and MobProperties `in_biome_` do the rest | qf-content reads a tier grid, and decides spawn, stats and elites from it | JAS biome tables pick the family; the grid hook picks the rank, stats, density and elites |
| **Covers T1/T2 spawn pockets** | **No.** The pockets are radial (750 and 1,550 blocks) and cross several biomes. | Yes | Yes |
| **Covers hot zones** | Partly. The Volcano and the corrupted core are their own biomes, but the **high crests** are height-based, the **deep desert** is depth-based (1,600 blocks inside the biome), and the falloffs blend over 500–1,400 blocks. | Yes | Yes |
| **Biome IDs** | Needs "hard" copies of biomes, and the IDs are already one short (108 free, 109 needed) | none | none |
| **Regional flavour** | Yes | Must be rebuilt in code | Yes, from JAS |
| **Effort** | Large, and it can't express the map | Medium (≈400–600 lines plus the bake) | Medium: the hook in (b), plus the JAS rebuild that decision 0003 already requires |
| **Server cost** | none | one array read per spawn | same as (b) |
| **Author edits** | config | code for every change | config for families (JAS) and one `difficulty-tiers.json` for the numbers |

Option (a) fails on the map's two defining features: the safe pockets and the smooth falloffs.
Option (b) throws away JAS's biome flavour, which RLCraft-style regions depend on. **Option (c)
keeps each tool doing what it is good at.**

## 3. Recommended mechanism

### 3.1 The baked grid

- `tools/world/difficulty.py` gains `--bake OUT.bin`. It writes the **continuous** difficulty `D`
  (before rounding to a tier; range 1.0–6.0) at **one byte per chunk** (`round(D × 40)`). For the
  ±24,576-block plan that is 3,072 × 3,072 = **9.4 MB**. At plan resolution (32 blocks) it would be
  2.4 MB.
  - A small header holds the magic number, the version, the origin, the cell size, the
    dimensions, the plan id, and the sha256 of `difficulty.yaml`.
- The file lives **in the world folder** (`world/data/qf-difficulty.bin`), not in the pack. It
  belongs to that world's map, so test worlds without it are unaffected.
  - **No file means the hook is off.** The census nodes, the trial worlds and today's test worlds
    are unaffected.
- Outside the grid (the RWG outskirts beyond the plan), **D = 6**. An optional ramp could raise it
  further with distance; see open question Q6.
- **Overworld only.** Other dimensions keep today's behaviour. Twilight, TragicMC and OreSpawn
  dimensions already have their own ladder.
- The hook loads the file at server start and keeps it as a `byte[]` (9.4 MB of heap). Each lookup
  is `grid[(z>>4 - z0) * w + (x>>4 - x0)]`, and **nothing is sent to clients**. A weak client pays
  nothing; only the spawn picker UI ships its own image.

### 3.2 The hook (qf-content, `world/DifficultyGrid` + `world/TierRules`)

One table (`config/qfcontent-difficulty.json`) gives the numbers per tier, so tuning never needs
a rebuild. Each event does a small job:

| Event | Priority | Job |
|---|---|---|
| `LivingSpawnEvent.CheckSpawn` (fires for JAS spawns **[E]**, and for vanilla and Lycanites spawns that use it) | HIGH | **Rank filter**: `DENY` if the mob's rank is above the tier's maximum. **Density**: `DENY` with probability `1 − density(tier)`. **Pocket rule**: `DENY` hostile spawns in the hearth (§5). |
| `EntityJoinWorldEvent` (every spawn path: JAS, Lycanites' own spawners, events, dungeon spawners, OreSpawn, eggs) | HIGHEST | If the mob has no `ForgeData.qfTier` yet, stamp it (tier and `D` at the spawn position). Then apply the safety net: cancel a natural spawn the rank filter would have denied, for spawners that skip `CheckSpawn`. |
| same, LOWEST, or one tick later | — | **Stats**: add two attribute modifiers with fixed UUIDs, **operator 2 (multiply total)**, so they compose *after* MobProperties' operator-1 boost rather than being added into it. **Elites**: adjust InfernalMobs per tier (§3.4). |
| `LivingDropsEvent` | NORMAL | Loot and XP by tier (§4.4). Only for kills by a real player, never by a FakePlayer, and never on SoulShards-cage or spawner mobs, so that no reward scales with AFK time (progression audit, principle 4). |

**Exclusions.** These are never scaled or filtered:
- **bosses**, using the same name list as `run_campaign.py` and `EnchantLoot`;
- tamed mobs and pets (Lycanites, Inventory Pets, Little Maids);
- player summons (`TickedEffects`);
- CustomNPCs;
- mobs marked by the census.

**Why exclude bosses.** They are the gates of the power ladder. Their difficulty is measured, and
it should not depend on where someone summons them. Their per-hit caps (Mobzilla 120, TragicMC 25)
would also mute any health scaling.

**Idempotence.** The stamp and the fixed-UUID modifiers persist in NBT, so a reloaded chunk never
scales a mob twice.

**Mob rank.** `pack/config/qfcontent-mob-ranks.json` gives every hostile entity a rank from 1 to 6,
meaning the lowest tier where it may spawn naturally.
- It is generated from the census as `health_med × dealt_mean`, with special cases flagged: ranged,
  flying, piercing, griefing, armour-ignoring.
- The author then edits it by hand.
- It is the one new data file the author tunes besides the tier table.

### 3.3 Density

JAS caps are global per creature type, so position cannot raise them locally. The scheme:
- Set JAS's MONSTER cap to the **T5 level**.
- Deny a share of spawns in every lower tier, so that T3 lands on today's density.
- Proposal: MONSTER cap 70 → **84** (×1.2). `density(tier)` is then the kept share: T1 0.25,
  T2 0.55, T3 0.83 (= 70/84, today), T4 1.0, T5 1.0, T6 1.0.
- T4 to T6 differ by **rank, pack size and elites**, not by mob count. More mobs costs server TPS,
  and the friends' server and weak clients set the ceiling (pack vision: friends' weaker PCs must run it).

### 3.4 InfernalMobs by tier

InfernalMobs rolls one global rate on `EntityJoinWorldEvent` **[E]**. Two routes are possible.
Which one works must be verified against the jar:
1. **Lower the global rate to the T2 value, and top it up by tier.** Call
   `InfernalMobsCore.processEntitySpawn` again, or `addEntityModifiersByString`, for an extra roll
   in T4–T6. This is the preferred route, because it changes no InfernalMobs code.
2. **Keep 1 in 15, and strip elites in T1** after the roll, through the core's rare-mob map.

Ultra and infernal shares rise with tier (see §4). `maxOneShotDamage=10` stays.

### 3.5 How it interacts with the combat balance work

- **The census is unaffected.** Bosses are excluded, census worlds have no grid, and T3 = today.
- **Predictions are cheap.** Ordinary-mob TTK at tier t ≈ TTK(T3) × health multiplier(t). Damage
  taken ≈ (damage(T3) × multiplier(t)), minus armour, so it is 0 at 25 or more armour points.
- **The open-world numbers wait for the census.** Damage, health and loot by tier are balance
  changes. Under the balance rule (gear and combat numbers wait for the enchant census), the tier table waits for the
  enchant census to wrap up, as gear does. The *mechanism* (grid, bake, hook with every
  multiplier at 1.0 and only the T1/T2 relief switched on) can land earlier. It changes nothing
  in T3 and above.

## 4. Per-tier targets (all proposed)

How the map's tiers line up with the gear ladder (progression audit §1, questline audit §3.1):

| Map tier | Gear the tier is built for | Rough hours of group play [G] |
|---|---|---|
| T1 | nothing to iron | 0–2 |
| T2 | iron, first diamonds | 1–5 |
| T3 | diamond (×WeaponScaler); first Twilight bosses | 4–20 |
| T4 | diamond plus TF fiery or TragicMC overlord, ruby; the Ultimate set coming | 15–40 |
| T5 | OreSpawn Ultimate (34 points, so melee-immune) and enchants | 30–80 |
| T6 | Mobzilla, Royal or Queen armour; Legendary enchants | 60–120+ |

"Leaps without a fast plateau": each tier asks for the next step of the ladder, and T6 stays
dangerous after the plateau, because its danger is mostly armour-ignoring.

### 4.1 Spawning

| Tier | Max mob rank | Families, by example (the biome still chooses among these) | Kept share of spawns | Pack size |
|---|---|---|---|---|
| **T1** Safe | 1 | Vanilla zombies, skeletons and spiders only at night; passive and ambient as normal. No creepers within the hearth (§5). No Lycanites custom-spawner mobs, no OreSpawn hostiles, no TragicMC, no Mutants, no Witchery night spawns. | 0.25 | JAS minimum |
| **T2** Apron | 2 | T1 plus vanilla creepers and witches. Low-rank Lycanites by biome (Plains Maka-grade animals, Swamp Remobra, Desert Clink). OreSpawn small mobs. | 0.55 | today |
| **T3** Quite difficult | 3 | **Today's tables for the biome**: Lycanites up to Jabberwock and Geken-class, TragicMC common mobs (Jabba, Tox, Minotaur), Witchery night mobs, OreSpawn mid mobs. | 0.83 (today) | today |
| **T4** Hard | 4 | T3 plus Mutant Creatures (Mutant Zombie, Mutant Skeleton), Lycanites demon and inferno mobs where the biome allows (Cacodemon, Lobber), TragicMC greater mobs (Greater Stin, Avris), OreSpawn heavies (Mantis-class as rare natural spawns). | 1.0 | +1 |
| **T5** Very difficult | 5 | T4, and the biome's top family is weighted up. Flyers and rangers count double here: Lycanites Roc and Cacodemon, OreSpawn Brutalfly. Lycanites subspecies uncommon odds ×2. | 1.0 | +2 |
| **T6** Beyond | 6 | Everything the biome allows. Rare named mini-bosses become natural spawns (OreSpawn Emperor Scorpion, Mantis; Witchery Nightmare). Subspecies ×3. | 1.0 | +2 |

### 4.2 Health and damage

These are multipliers **on top of today's** values, which already include MobProperties.

| Tier | Health × | Damage × | Resulting vanilla Creeper median HP [from 132 **E**] | Notes |
|---|---|---|---|---|
| T1 | 0.4 | 0.6 | ~53 | close to MobProperties' minimum ×4, i.e. vanilla ×2.6 |
| T2 | 0.7 | 0.8 | ~92 | |
| T3 | **1.0** | **1.0** | 132 | today, unchanged |
| T4 | 1.5 | 1.3 | ~198 | |
| T5 | 2.2 | 1.7 | ~290 | |
| T6 | 3.0 | 2.2 | ~396 | |

Speed and follow range stay out of the first pass. They are the cheapest way to make a mob harder,
and also the easiest way to make it unfair. Measure first (Q4).

### 4.3 Elites and armour-ignoring pressure

| Tier | Elite chance (today 6.7%) | Ultra share of elites | Infernal share of elites | Armour-ignoring extras |
|---|---|---|---|---|
| T1 | 0% | — | — | none |
| T2 | 3% | 1/10 | 0 | none |
| T3 | 6.7% (1 in 15, today) | 1/7 (today) | 1/49 (today) | today |
| T4 | 10% | 1/5 | 1/25 | — |
| T5 | 15% | 1/4 | 1/12 | Wither, Poisonous, Rust, Lifesteal and Fiery weighted ×2 in modifier rolls (Rust wears armour down) |
| T6 | 22% | 1/3 | 1/8 | as T5. Natural spawns also take armour-piercing modifiers: Lycanites `Pierce` raised by +2 through its stat path, if the hook can reach it (Q5). |

Damage multipliers also wear armour faster, since durability loss ≈ damage/4 per hit. In 1.7.10
this is the one way normal mobs can still touch a melee-immune player. Ultimate armour has 200
durability **[E]**.

### 4.4 Loot quality

Every row applies only to real-player kills of naturally spawned mobs (§3.2).

| Tier | XP × (feeds LevelUp) | Extra drop roll | Loot bags (Lootbags) | Enchant tomes |
|---|---|---|---|---|
| T1 | 0.5 | none | none | none |
| T2 | 0.8 | none | none | none |
| T3 | 1.0 | today | today | today (vanilla chests, by the EnchantLoot plan) |
| T4 | 1.5 | +1 roll of the mob's own drops at 25% | ×1.5 | none extra |
| T5 | 2.0 | +1 roll at 50% | ×2, uncommon or better | elite kills: 2% UNCOMMON, 0.5% RARE |
| T6 | 3.0 | +1 roll at 100% | ×3, rare or better | elite kills: 3% RARE, 0.5% EPIC; **never** LEGENDARY or Binding Scrolls (those stay boss-gated, progression audit §5) |

Structure loot (Roguelike, Doomlike, ChocolateQuest, Recurrent Complex) cannot be keyed by position
from config. A later step could add a `LootTierHook` that adds rolls to chests opened for the
first time in T4–T6. It is out of scope here (Q7).

## 5. Safe pockets around the spawns

Each spawn has a **hearth** (0–150 blocks), then T1 (to 750), then T2 (to 1,550), then a ramp of
1,200 blocks back to the region's tier ([difficulty.md](difficulty.md)).

- **Hearth (proposed 150 blocks):** no natural hostile spawns at all, by day or night. This is the
  only place a new player can stand in the open on night one. Mobs from spawners and events are
  still filtered by rank, and nothing is cancelled outright. The hearth is the ring where players
  arrive when the picker places them.
- **T1:** rank 1, 25% density, no elites, ×0.4 health. Lycanites **mob events** (Arachnophobia,
  Boulder Dash, …) are suppressed when their target player stands in T1. Players can still go out
  to meet them.
- **T2:** low ranks, a few elites, enough to teach the systems (Lycanites, InfernalMobs) without
  killing.
- **Mobs keep the tier they spawned with.** A T4 mob that chases a player into T1 stays a T4 mob,
  so a pocket is not a magic barrier. Proposed: a hostile mob of rank 3 or more that is still in
  the hearth with no player within 32 blocks despawns. That stops wanderers from piling up at the
  hearth.
- **Underground** shares the surface tier in this first pass. A "deep below y 30 counts as +1
  tier" rule is easy to add later (Q3).
- **Player bases outside the pockets** stay at their tier. Whether players can push a tier down
  locally (a crafted ward, a cleared-region mechanic in the style of Valheim) is open question Q2.

## 6. Effort, reliability and performance

| Piece | Effort | Risk | Server cost |
|---|---|---|---|
| `difficulty.py --bake` | small (≈60 lines) | low; the grid comes from the same arrays as the render | offline |
| `DifficultyGrid` load + lookup | small | low; a missing file means off | 9.4 MB heap, O(1) |
| `CheckSpawn` filter + density | medium | medium: some spawners may skip `CheckSpawn`, so the join-event safety net covers them | one lookup and one map read per attempt |
| Stats + stamp on join | small | **ordering with MobProperties' delayed queue and InfernalMobs' health rewrite**: must be verified on a slim trial | two modifiers per spawn |
| InfernalMobs per tier | small–medium | the API route must be checked against the jar | none |
| Mob-rank file from the census | medium (script + the author's pass) | judgement, not code | none |
| JAS rebuild for BoP and RWG names | **large; required by 0003 anyway** | the renamed keys (`biomesoplenty.Plains`, …) | none |
| Drops and XP | small | the FakePlayer and spawner gates must hold | none |

No client mod and no packets are needed. Nothing ticks, apart from the optional hearth
despawn sweep (once every 10 s per loaded hearth chunk).

## 7. What to measure before tuning numbers

1. **Today's T3 baseline in a real world, not a probe.**
   - Hostile mobs per player at night and in the day, in three biomes.
   - Elite share.
   - TPS with 1 and 4 players. Use the friends-server build on Java 25 and a pregenerated test world.
2. **The cap cost.** TPS and entity count at MONSTER cap 70 versus 84 versus 100, with 4 players
   spread across tiers. This sets the T4–T6 density ceiling.
3. **Damage and armour per rank.**
   - What each rank deals to diamond (20), ruby (25), Ultimate (34) and Royal (42) armour, using the
     census probe with armour.
   - Armour durability loss per minute in T3 to T6.
   - Which families get through 25 or more points (piercing, magic, wither), and by how much.
4. **Order of operations.** On one mob, the health before and after MobProperties' queue,
   InfernalMobs' rewrite and the tier modifier. Confirm the multiplier composes as operator 2 on
   the final value.
5. **TTK by tier** for the median mob of each rank with the ladder weapons. WeaponScaler is
   included, so report medians. Target: a T-tier mob takes about the same number of hits with
   T-tier gear at every tier.
6. **The mob-rank table**: the census `health × dealt` score per entity, and its quantiles cut
   into ranks 1–6. The 16 Oct mob census lacks `dealt_*` for most rows; re-run it with damage
   probing.
7. **Survival tests**: one night in each spawn's T1 with no gear; a trip across T3 with iron; a
   visit to a T5 hot zone with Ultimate. Success means no deaths, a few deaths, and a real fight,
   in that order.
8. **The picker ratings again** once the numbers exist. A spawn's label should reflect the
   *measured* danger of its 3,000-block circle, not only its mean tier.

## 8. Open questions for the author

- **Q1. T3 = today?** Is today's pack the "quite difficult" baseline, with spawns made gentler and
  hot zones harder? The alternative is to raise everything. This proposal assumes today = T3,
  following "never inflate the pack".
- **Q2. Player-made safety.** Should players be able to lower the tier around a base (a crafted
  ward, Valheim-style clearing, or killing a region's mini-boss)? Or does the map stay fixed?
- **Q3. Depth.** Should caves and the mining band (where titanium sits, y 2–17) count as one tier
  harder?
- **Q4. Speed and follow range.** Should mobs in T5 and T6 also get faster and more aware, or only
  tougher?
- **Q5. Armour-immune players.** Is it right that T5 and T6 threaten melee-immune armour mainly
  through armour-ignoring damage and durability wear? Or should the pack add an armour-piercing
  share to tier damage, for example 20% of tier damage as `DamageSource.magic` in T6?
- **Q6. Outskirts.** Should the RWG outskirts beyond the grid be flat T6, or keep rising with
  distance (a "T7+" endless frontier) for the long tail?
- **Q7. Loot.** Are the tome odds in §4.4 acceptable, given that EnchantLoot keeps Epic and
  Legendary boss-gated? Should structure chests in T4–T6 get extra rolls?
- **Q8. Spawner and cage mobs.** Should SoulShards cages and dungeon spawners take the tier of
  their position (a T5 farm is harder *and* richer), or stay at T3 regardless?
- **Q9. Lycanites events.** Suppress them in T1 only, or in T1 and T2?
- **Q10. When to apply it.** Should the mechanism land now with every multiplier at 1.0 (only
  T1/T2 relief active), and the T4–T6 numbers after the enchant census? Or should all of it wait?
