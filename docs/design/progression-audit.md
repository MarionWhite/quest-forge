# Progression audit

Status: **audit 2026-10-16. Config fixes F2–F5, F8, F9a, F10 and F14 applied 2026-10-17 (see §6); F6/F7 are quest edits, tracked separately.** This document
proposes changes. Each one still needs a slim boot to validate it, and none has
been booted yet.

**The question:** where can a player in this pack jump straight to the top, and
what would stop it without betraying CrazyCraft?

**The rule being measured against** is the user's: players can make big leaps in
power, but not straight to the top, and the plateau must not arrive fast.
Additions are welcome only if they cost no performance.

**How to read the claims.** Every claim carries one of these tags:

| Tag | Meaning |
|---|---|
| **[E]** | Evidence: a file, a config key, a bytecode constant or a census row that I read. The path is given. |
| **[R]** | Recall: general knowledge of these mod versions. I did not check it here. |
| **[G]** | Guess: an estimate, with its reasoning shown. |

**Sources:**
- Live instance: `%APPDATA%\.crazycraft4` (written `L\` below). Its configs match `pack/config` apart from line endings and auto-added entries.
- Live `minetweaker.log`: the gating script loads cleanly and every remove/add fires.
- Recipes were recovered by walking the bytecode of `OreSpawnMain`, `ObjHandler` (ProjectE) and `InventoryPets.class`. The scratch scripts are in the session scratchpad. No game was launched.

---

## 0. The five things that matter most

1. **Bountiful duplicates storage blocks without limit.** This is our own code. **[E]**
   - Place a diamond block, break it, then place it in a *new* spot.
   - At 33% that compounds without bound, because the guard only remembers positions.
   - It feeds every other shortcut below: crafted lucky blocks, Philosopher's Stone conversions, beacons, and EMC.
2. **Lucky Blocks drop every gate item.**
   - The drops include the Royal Guardian Sword (the Dark Matter key), Queen Scales (the Red Matter key), Mobzilla scales and scale blocks (the Transmutation Table key), and full Ultimate sets.
   - There is also a Sharpness-1000 diamond sword. A ProjectE Repair Talisman, craftable on day one, makes it permanent.
   - The quest book hands out **~765** lucky blocks. **[E]**
3. **Loot bags plus spawner farms make Legendary enchant tomes and Binding Scrolls effectively unlimited.**
   - Legendary bags pull only chest entries of weight ≤ 5, which is exactly where `EnchantLoot` puts Legendary, Epic and Rare tomes and the 100%-success Binding Scroll.
   - SoulShards has an empty blacklist and no player check. **[E]**
4. **Creative-only items are quest rewards:** TragicMC's Sword and Bow of Justice, and Witchery's Infinity Egg. **[E]**
5. **The ×1–4 damage scaler turns the weapon ladder upside down.**
   - KillerPacman's `WeaponScaler` multiplies every non-OreSpawn melee hit.
   - A diamond sword (8 → ~20) outhits an OreSpawn Ruby sword (16, unscaled). TragicMC's Titan outhits the Ultimate Sword.
   - The T3 and T4 OreSpawn weapons get no boost. **[E]**

The top five fixes are in §6. All but one are config or script edits. Each costs
no performance, and each can be undone.

---

## 1. Tier ladder

Each row is what a player holds at that stage, how they get it, and a rough time
from a fresh server **[G]**.

The times assume a small group of two to four friends playing focused sessions
without exploits. They are calibrated from three things:
- the ore survey (`pack/reports/ore-rates.txt`);
- the census boss pools and kill times (`C:\qfs\{c1,c2,combat}\config\qfcontent-census-combat.tsv`, read-only);
- the quest order in `config/betterquesting/DefaultQuests.json`.

### Weapons and damage (as dealt, not as listed)

`WeaponScaler` multiplies a held non-OreSpawn item's hit by 1 + 3·rand, an average
of ×2.5. **[E]**
- Its constant pool is in `L\mods\KillerPacman.jar` `fiskfille/pacman/WeaponScaler.class`: `LivingHurtEvent`, `getClass().toString().contains("orespawn")`, `nextFloat`.
- The diagnostic is noted in `CombatCensus.walkHurtListeners`.

| Tier | Weapon | Listed | Effective per hit | Source and route | Time [G] |
|---|---|---:|---:|---|---|
| T0 | iron sword | 6 | ~15 | crafted | <1 h |
| T1 | diamond sword | 8 | **~20** (census: 20.0 per hit vs Naga) [E] | diamonds (~6 per chunk in the overworld [E]) plus quest rewards (q3, q6, q20, q28 give 4–8 each [E]) | 2–5 h |
| T1 (side) | OreSpawn emerald / ruby | 16 (ruby) | **16, unscaled** | emerald / ruby ore | 3–8 h |
| T2 | TF fiery sword, Witchery, TragicMC (Titan 26 listed in `qfbench.py`) | 26 | **~65** | Hydra quest; TragicMC q137 offers Titan as a choice [E] | 10–25 h |
| T3 | OreSpawn Ultimate Sword | 36 | **36** | 1 titanium ingot + 1 uranium ingot + 1 iron (ore → nugget → 9 nuggets per ingot [E]), so **9 titanium ore + 9 uranium ore**. No boss needed. | 4–10 h of strip-mining |
| T3+ | Battle Axe 46, Chainsaw 56, Attitude Adjuster 82 | 46–82 | unscaled | Ultimate Sword + Ultimate Axe + green goo; Ultimate Axe + 8 redstone blocks; 2 Ultimate Swords + Big Hammer + goo [E] | +1–3 h after T3 |
| T3.5 | Big Bertha / Slice | 496 | unscaled | handle, guard and blade need about 14 mid-boss parts (Kraken, Basilisk, Mothra, Emperor Scorpion, Nightmare, T-Rex, Caterkiller, Sea Viper, Vortex …) plus an Ultimate Sword [E] | 25–50 h |
| T4 | Royal Guardian Sword | 746 | unscaled | dropped by **The King and also The Queen** (both class constant pools reference `MyRoyal` [E]) | 40–80 h |
| T4 | Queen Scale Battle Axe | 662 | unscaled | Queen scales [E] | after the Queen |
| T5 | ProjectE Dark / Red Matter tools, Katar | 12–16 listed, but radius and death-aura abilities (`katarDeathAura=1000` [E]) | ~30–40 scaled | gated by the Royal sword and the Queen scale (§1.3) | 60–120 h |

Two consequences of the scaler. **[E for the mechanism, G for the feel]**
- A diamond sword beats every OreSpawn weapon below the Ultimate Sword.
- TragicMC and Twilight weapons beat the Ultimate Sword.

The measured fights show the scale:

| Fight (census) | Damage per hit | Time to kill |
|---|---|---|
| Diamond sword vs the Naga (1,565 HP) | 20 | 39 s |
| Royal Guardian vs Mobzilla (17,818 HP) | **120**, every hit | 148 s |

A 746-damage sword landing exactly 120 against Mobzilla means its damage is
clamped. Against Mobzilla, anything above ~120 per hit is therefore the same
weapon. **[E]** That is a plateau marker; see §3.

### Armour

The numbers come from `docs/reference/enchantment-tuning.md` D2/D3, run on the
real pipeline. **[E]**

| Tier | Set | Points / durability | Survives (s, one hit per second) vs Mobzilla / Queen / King | Route |
|---|---|---|---|---|
| T1 | diamond | 20 / 33 | one-shot by all three | diamonds |
| T2 | TF fiery, TragicMC overlord | ~24 / 35 | one-shot | Hydra; Synapse key (q134 [E]) |
| T2+ | OreSpawn ruby | 25 / 90 | 3 / 1 / 1 | ruby ore (0.21 per chunk — scarce [E]) |
| T3 | **OreSpawn Ultimate** (Protection V built in) | 34 / 200 | 43 / 29 / 11 | 9 titanium + 9 uranium **ingots** = 81 + 81 ore [E] |
| T4 | Mobzilla scale | 38 / 1000 | 416 / 317 / 195 | 24 scales; the Mobzilla quest offers **32 scale blocks** [E] |
| T4 | Royal | 42 / 2000 | 860 / 665 / 422 | The King's drop (+ q23 choice [E]) |
| T4 | Queen | 48 / 1500 | 428 / 331 / 206 | Queen scales (q24 offers **64** [E]) |
| T5 | ProjectE Gem armour | — | flight, plus regen/void | Red Matter + Klein Star Omega + SWRG ×2, etc. [E] |

**Getting Ultimate armour [G].** Titanium is the bottleneck: 1.63 ore per chunk
in the overworld, Y 2–17. A full set plus a sword needs ~90 titanium ore, the
entire titanium of ~55 chunks. Branch mining that band takes roughly 10–20
minutes per chunk, so **8–15 hours solo, 3–6 hours for a group.** That is a
healthy mid-game grind. The OreSpawn mining dimension (dim 81) is no richer in
titanium (1.81 per chunk). **[E]**

### Mobility, healing, automation and "skip" items

| Category | Item | Route | Time [G] | Note |
|---|---|---|---|---|
| Flight | **Morph** into a bat, chicken, ghast … | kill one mob | **day 1** | `abilities=1`, `disableEarlyGameFlight=0` [E] |
| Flight | MCHeli helicopters | iron blocks (e.g. AH-64 `"X X"," X ","X X"`, X = iron_block [E]) | day 1–2 | `DamageVsLiving=0.2` softens its guns [E] |
| Flight | Archimedes airships | wool balloons; q36 gives 8 [E] | day 1–2 | `mandatory_engines=false` [E] |
| Glide | OpenBlocks hang glider; Royal glide (`RoyalGlideEnable=1`) | iron and leather; Royal armour | day 1; T4 | |
| Flight | ProjectE SWRG; TragicMC Wings of Liberation (q139 choice) | Dark Matter + Iron Band [E]; TragicMC endgame | T5; T2+ | |
| Teleport | `/home`, dimension tickets (qf-commands) | tickets: 1/5000 per kill, 1/10 per boss kill [E] | slow | no /fly, /give or keepInventory [E] |
| Teleport | Ender Utilities porters, lasso, ender bow | ender pearls | day 2–5 | teleport blacklist covers only the dragon and the Wither [E] |
| Healing | Golden apples (~80 from quests [E]), Magic Apple | quests; 8 redstone blocks + apple [E] | early | |
| Death insurance | Sync shells (`overrideDeathIfThereAreAvailableShells=1` [E]), `/pv` vault | mid | mid | |
| Repair | **ProjectE Repair Talisman** | covalence dust (cobble + charcoal, iron + redstone, diamond + coal), string and paper, **no Philosopher's Stone** [E] | **day 1–2** | see §2.2 |
| Automation | SoulShards cages (q38 offers 2 [E]) | Soul Stealer kills | early–mid | empty blacklist; T5 cooldown 5 s × 4 spawns, no player/light/world checks [E] |
| Automation | ProjectE collectors and condensers | Dark Matter (gated) [E] | T5 | MK2/MK3 and relays upgrade from MK1, so they inherit the gate [E] |
| EMC | Philosopher's Stone conversions (8 iron → 1 gold, 4 gold → 1 diamond, 2 diamond → 1 emerald) [E] | after the Lich | T2 | CC-faithful; dangerous only combined with Bountiful |

### 1.3 The intended boss gates, and whether each holds

`pack/scripts/crazycraft_gating.zs` loads cleanly (see `L\minetweaker.log`). **[E]**

| Gate | Key item | Holds against crafting? | Holds against drops? |
|---|---|---|---|
| Philosopher's Stone | TF Zombie Scepter (one of three random Lich scepters [E]; the Lich quest also offers a **Nether Star** [E]) | yes (both original recipes removed [E]) | Illuminati pet (§2.5) |
| Transmutation Table | 4 Mobzilla scale blocks (36 scales) | yes | **no**: Lucky Blocks drop 8–16 Godzilla scales (L227) and a column of 9 scale blocks (L466) [E] |
| Dark Matter | Royal Guardian Sword, **reused** (not consumed) | yes | **no**: Lucky Block L104 group drops `OreSpawn_Royal` [E]. Also, the Queen drops it, so the "King gate" is really "King **or** Queen". |
| Red Matter | Queen Scale (consumed) | yes | **no**: Lucky L177 / L227 drop 8–20 Queen scales [E]. The Queen quest also offers 64 [E]. |
| Collector / Condenser | Dark Matter | yes | — |

**Open questions** that only an in-game check can answer:
- Does the EMC mapper give Dark Matter a value now that its recipe contains a no-EMC item (the Royal sword)? If it does, one learned Dark Matter makes the Royal gate meaningless for anyone with a Transmutation Table. Check the EMC tooltip with NEI. **[G]**
- Does the King's "charade" ending (`FullPowerKingEnable=1`) still run his drop code?

---

## 2. Shortcuts that skip to the top, ranked

Rank = how far up the ladder it jumps × how cheap and repeatable it is.

### 2.1 Bountiful block duplication — our own code — CRITICAL [E]

> **Status: fixed in `dc165b0`** (2026-10-16). Bountiful now skips any drop that is
> the block's own item, so the place-and-rebreak loop below no longer pays. It is
> live only once the jar is installed with `trial.py install`.
>
> **Leftover, accepted:** crafting cycles. A block that breaks into ingredients that
> craft back into the block still nets about +33% per cycle at level III. Examples
> are clay (4 balls), snow (4 balls) and glowstone (dust; 4 dust make a block).
> All of these are cheap, so they were left alone on purpose. Re-check if a mod adds
> a valuable block that drops its own crafting ingredients.

Where it lives: `mods/qf-content/src/main/java/com/questforge/content/ench/enchants/ToolEnchants.java`, class `Bountiful`.

How it works:
- On any block with no tile entity and no drop NBT, broken by a tool without Fortune, it doubles the drops with 11 / 22 / 33% chance.
- The only guard is `DuplicationMemory.claim(dim, x, y, z)`: one payout per *position*, expiring after 6000 ticks, at most 8,192 entries.

The exploit:
1. Place a diamond block (or iron, emerald, gold, OreSpawn ruby, titanium, uranium or Mobzilla scale block).
2. Break it.
3. Place it one block over and repeat.

The expected yield is 1.33 blocks per break, compounding.
- **[G]** At about one break per second, one diamond block becomes hundreds per hour.
- Bountiful is UNCOMMON, so it turns up early.

It feeds:
- crafted lucky blocks at maximum luck (`diamond_block=100` luck [E]);
- beacons;
- after the Lich, every Philosopher's Stone conversion;
- after the table, unlimited EMC.

The tuning doc's claim that it "cannot be farmed by replacing and rebreaking" is
true only for the *same* spot.

### 2.2 Lucky Blocks — CRITICAL [E]

Config: `L\config\lucky\LuckyBlockProperties.txt`, about 308 drop lines, CrazyCraft-customised.

How players get them:
- **Crafted:** 2 diamonds, 2 emeralds, 2 gold, 2 redstone and a dropper.
- **Luck can be raised** by crafting items in: `diamond=12`, `diamond_block=100`, `nether_star=100`.
- **World generation:** `spawnrate=100`, i.e. one per 100 chunks.
- **Quests:** ~765 handed out. The Pets line (55 quests, 246 blocks) and the Heroes line (101 quests, 226 blocks) give 2–8 for each pet or suit crafted. [E, my count]

Top-tier drops:

| Line | Drop | Weight |
|---|---|---|
| L104 | one of Ultimate Sword, Nightmare, Attitude Adjuster, **Big Bertha**, Slice, **Royal Guardian**, Battle Axe, Queen Battle Axe, Chainsaw | `@luck=4` |
| L92 / L120 | one Ultimate armour piece | `@luck=2` |
| L121 | one Ultimate tool | `@luck=2` |
| L227 | 8–16 each of Godzilla scale, Queen scale, titanium ingot and uranium ingot | `@chance=0.5@luck=4` |
| L466 | a falling column of 9 Mobzilla scale blocks (the whole Transmutation Table gate, twice over) | `@chance=0.1@luck=-4` |
| L1 | **"1 hit KO"**: diamond sword, Sharpness 1000, 1 durability from breaking, `RepairCost=1000` | `@luck=1` |
| L130, L156, L504 / L521 | dragon egg, nether star, beacon, 10 end portal frames | |
| L509 | "sky temple" with 250 diamonds | `@chance=0.5` |
| L299 / L463 / L466 | Mobzilla, King spawner, Queen spawner (dangers rather than rewards) | |

**Rough odds [G].** Weighting maths are not visible statically. At neutral luck,
about 5 of ~308 lines give Ultimate, Royal or Queen-tier gear, so ~1.5–2% per
block. Inside L104 the Royal is 1 of 9, so ~1 in 2,500–3,000 per block at
neutral luck, and better at +100 luck.
- Across the quest book's 765 blocks, expect **~10 Ultimate pieces**.
- Expect a **coin-flip's chance of a Royal Guardian Sword**.
- Expect a good chance of a Queen-scale stack and of the scale-block column.

With Bountiful-fed crafted blocks at luck 100, the Royal sword becomes a matter of
hours. The Ultimate set, the Transmutation Table and Red Matter's key follow.

**The repair combo [E].** The "1 hit KO" sword deals 1,250 extra damage (1.25
per Sharpness level in 1.7.10 [R]), before the ×2.5 scaler. Its three hits look
self-limiting, and the anvil is locked by `RepairCost`. But the ProjectE Repair
Talisman is uncraft-gated (recipe `LMH/SPS/HML` of covalence dust, string and
paper [E]; covalence needs no Philosopher's Stone [E]), and it repairs carried
items over time [R]. The sword then becomes a permanent five-figure hit. It is
blunted only by per-hit caps (Mobzilla ~120, TragicMC `bossDamageCap=25`). It
one-shots the whole Twilight ladder and every uncapped boss.

### 2.3 Loot bags × spawner farms × sealed tomes — HIGH, and it flattens the enchant curve [E]

How the bags are built (`L\config\Lootbags_BagConfig.cfg`):
- Every bag uses `$USEGENERALLOOTSOURCES:true`.
- The maximum entry weight drops tier by tier: Common unlimited, Uncommon 20, Rare 15, Epic 10, **Legendary 5**.
- Bags combine upward (`$CRAFTEDFROM`).
- The recycler is on, turning junk into Common bags.

Drop rate (`L\config\lootbags.cfg`): about 21% per hostile kill, about 38% per boss
kill, `Valid Kill Methods=All`.

The interaction with our loot code:
- `EnchantLoot` injects tomes at weights 12/8/4/2/1 and the Binding Scroll at 1.
- So a Legendary bag (max weight 5) draws almost only from Rare, Epic and Legendary tomes, Binding Scrolls, Ward Scrolls (3) and Solvent (4), plus vanilla's rarest entries.
- The same filter also catches Pandora's Boxes and **Lucky Eggs** (both inject into chests [E]), and PortalGuns (`lootRarityPortalGun=2` [E]).

The farm (`L\config\SSTOW`): the blacklist is empty, and every tier has `Check Player=false`, `Check Light=false` and `Checks World=false`. A Tier-5 cage spawns 4 mobs every 5 s.

**[G]** A cage killed by a player with a sweeping weapon yields ~2,900 kills per
hour. That is ~30 Legendary and ~70 Epic bags per hour straight from drops,
before any combining. **A player owns every Legendary enchant with a Binding
Scroll (100% success, 0% destroy) inside a weekend.** The rarity and
risk design in `docs/design/enchantments.md` stops existing.

### 2.4 Creative-only items as quest rewards — HIGH, but late [E]

| Quest | Choice includes | Evidence |
|---|---|---|
| q140 Doomsday Scroll | **Sword of Justice** (also a dragon egg) | `WeaponSwordOfJustice.class` registers in TragicMC's `Creative` tab and checks `isCreativeMode`; [R] it kills anything in one hit |
| q144 Doombringer | **Bow of Justice**, 32 diamond blocks | same class family |
| q141 Witch of the Wild | **Witchery Infinity Egg** | [R] creative-only; gives unlimited altar power |

These sit at the end of the TragicMC and Witchery lines, so they are not
day-one skips. They do skip *everything after them*: the OreSpawn T4 bosses are
then a click away (bar the Mobzilla cap).

### 2.5 Inventory Pets: the Illuminati pet — MEDIUM-HIGH, a slow drip [E]

- **Recipe:** 7 emerald nuggets, a diamond and a **nether star** (`OOO/ODO/OGO`, recovered from `InventoryPets.class`). The nether star is a Lich-quest choice and a Lucky Block drop.
- **Config:** `Disable Illuminati Give Random Items=false`, `Illuminati Cooldown=2` (minutes), `Spawns Only Craftable Items=true`. The blacklist covers only dirt, command blocks, BiblioCraft, the April Fool pet and gift.
- **What it does:** "craftable" means any `CraftingManager` output, and CraftTweaker's gated recipes *are* such outputs. The pool therefore includes the Philosopher's Stone, the Transmutation Table, Dark and Red Matter and every DM/RM tool. **[E for the config, G for the pool]**
- **Rate [G]:** about 30 rolls an hour against a pool of thousands. Expect a gate item every ~10–20 hours carried. A slow, unconditional leak around every boss gate.

### 2.6 Boss spawn eggs and spawners in loose circulation — MEDIUM [E]

The sources:
- Lucky Eggs (chest-only; the boss pool includes `TheKing`, `TheQueen`, `Godzilla`, `Kraken` …);
- OreSpawn's dungeon loot and Easter Bunny drops (both reference `GodzillaEgg`, `TheKingEgg` and `TheQueenEgg`);
- spawn-egg ore (`SpawnOres_rate=28`);
- Lucky drops of the King and Queen spawners.

This is not loot in itself. It lets a player choose the arena, and the arena is the
cheese.
- **Mobzilla** has no `inWall` or explosion filter in its constant pool, so pits, TNT and ICBM work. [E for missing checks, G for the effect]
- **The King and Queen** filter suffocation (noClip), and the Queen likely filters explosions.

The Royal sword is reused, so **a single kill by any means unlocks Dark Matter
for the whole server**: one player can craft every Dark Matter item and hand
them out.

### 2.7 Day-one flight — MEDIUM, a shape problem rather than a power one [E]

Morph flight from a bat or chicken (`disableEarlyGameFlight=0`), MCHeli and
Archimedes all give flight on day one or two. Flight erases terrain as an
obstacle and makes mining, structures and Twilight towers trivial.

This *is* CrazyCraft, though. CC4 players flew helicopters early. Only Morph's
free flight is worth gating.

### 2.8 Smaller leaks

**Quest rewards ahead of their tier [E]:**
- q6 Diamond Gear offers a ProjectE **Zero Ring**, a ProjectE item before the Lich.
- q22 Mobzilla offers **32 scale blocks**: eight Transmutation Tables, or Mobzilla armour for the whole server.
- q24 Queen offers **64 Queen Scales**: 64 Red Matter keys.
- q75, q144 and q24 offer 8, 32 and 16 diamond blocks.
- q63 offers Mjolnir and 64 lucky blocks.

The late ones are fine as celebrations. The gate-material multiples are the leak:
one kill buys the whole server's supply.

**Smaller sources:**
- **Doomlike Dungeons** level-8 chests: nether star, 1–12 diamond and emerald blocks, a beacon, and up to **8 wither skulls** (`L\config\DLDungeonsJBG\chests.cfg`). [E]
- **OreSpawn worldgen:** diamond and emerald *blocks* generate as ore (`BlockDiamond_rate=2`, `BlockEmerald_rate=2`). [E] With Bountiful this is a seed stock.
- **Twilight uncrafting table** is live (`DisableUncrafting=false` [E]). [R] It breaks enchanted or lucky-drop gear back into materials, e.g. Ultimate armour into titanium and uranium ingots. It is not a duplicator by itself in vanilla recipes.
- **Ender Utilities** can teleport OreSpawn, TF and TragicMC bosses into a trap (blacklist: dragon and Wither only [E]).
- **Pandora's Box** is cheap (gold, redstone, ender pearl, planks [E]) and vanilla-only. Its upside is diamonds and emerald blocks; its downside is a spawned Wither. Low.
- **OpenBlocks** auto-enchanter plus XP drain plus spawner XP gives endless level-30 vanilla enchants [R]. Low: vanilla enchants are a small slice of power here.
- **Villager trades:** none added by pack code [E]. Vanilla 1.7.10 librarians do not sell books [R]. Not a vector.

---

## 3. Plateau

### Where power stops rising

**1. Per-hit damage caps cap offence long before the weapon list does.**

| Cap | Value | Source |
|---|---|---|
| TragicMC bosses | `bossDamageCap=25` | config [E] |
| Mobzilla | landed exactly **120.0 every hit** from a 746-damage sword | census, control rows [E] |
| Infernal-mob hits on you | `maxOneShotDamage=10` | config [E] |
| Lycanites bosses | clamp per hit | `enchantment-tuning.md` [E] |

Past ~120 per hit, a bigger number on the sword buys nothing against the bosses
that matter. **[G]** The practical offensive plateau is therefore the Attitude
Adjuster or Big Bertha tier, not the Royal Guardian.

What still scales past the caps:
- the enchant layer, which adds damage outside the base hit (Executioner raised Royal-vs-Mobzilla DPS from 119.6 to 162.6; Multi Strike + Colossus + Executioner to 210.5 [E]);
- attack *rate*.

**2. Defence plateaus on durability, not points.** Royal is the top (2,000
durability, Protection X and Unbreaking V). Nothing survives one ×8-enraged King
swing. **[E]**

**3. Resources plateau at ProjectE collectors and condensers**, which are gated
behind Dark Matter.

### How early a determined player gets there

| Route | Time to the plateau [G] |
|---|---|
| Intended route (Ultimate → mid-bosses → Mobzilla → King/Queen → DM/RM) | **60–120 h** of group play. Healthy. |
| With Lucky Blocks alone (quest blocks plus some crafted) | Ultimate gear in the first **5–10 h**, and a decent chance of the Royal sword or Queen scales before any T4 boss. A **2–5× compression** of the middle. |
| With Bountiful + crafted max-luck Lucky Blocks | Royal sword, Ultimate set, table and RM keys in **one to two evenings**. That flattens the whole curve. |
| With a SoulShards T5 cage + loot bags | the enchant ceiling (every Legendary, risk-free) in **~10–20 h**, independent of gear. |

### What keeps the late game interesting

- **The OreSpawn T4 trio.** Mobzilla takes 148 s of perfect swinging with the Royal sword. The King's enrage makes him a skill fight.
- **Dimensions:**
  - Twilight, with eight bosses in order;
  - TragicMC Collision and Synapse;
  - Witchery's Torment and Spirit World;
  - OreSpawn's Crystal, Chaos and Islands;
  - HEE's End;
  - Legends' many dimensions.
- **The custom enchant layer**, *if* tomes stay scarce. It is the only power that keeps growing past the damage caps, which makes it the right place for a long tail.
- **Collection quests** (Heroes, Pets, Full Arsenal, PACK MASTER).

---

## 4. Interventions

Columns:
- **Curve:** what the fix does to the curve.
- **Perf:** runtime cost.
- **CC:** fidelity to CrazyCraft's spirit, from 1 (alien) to 5 (pure CC).
- **Type:** reversible config or script, or invasive code.

| # | Problem | Fix | Curve | Perf | CC | Type |
|---|---|---|---|---|---|---|
| F1 | Bountiful duplication | In `Bountiful.onHarvest`, skip any block whose drop is the block itself (`Item.getItemFromBlock(block) == drop.getItem()`). That leaves only "ore-like" blocks that drop something else, which is what Fortune-ignored blocks were meant to be. Optionally also skip an oredict `block*` list. | removes the unbounded source | zero (one comparison per harvest) | 5 (players never notice) | qf-content code, small, one class; revert by reverting the commit |
| F2 | Lucky gate items | In `LuckyBlockProperties.txt`: (a) strip `OreSpawn_Royal`, `OreSpawn_QueenBattleAxe`, `OreSpawn_Bertha` and `OreSpawn_Slice` from L104; (b) drop the Queen scale and Godzilla scale from L227 and L177, keeping titanium and uranium; (c) replace L466's Mobzilla-scale column with Ultimate ore blocks; (d) delete L1 "1 hit KO", or set its sharpness to ~10. Keep the Ultimate gear lines: they *are* CC4's signature jackpot and they top out at T3. | keeps the jackpot feel, removes the jumps to T4 and T5 | zero | 4 | reversible config |
| F3 | Lucky farming | Raise the cost of crafted luck: `diamond=12`→`4`, `diamond_block=100`→`36`, `nether_star=100`→`40`. Optionally add a CraftTweaker recipe swap so a lucky block needs one Twilight item, e.g. `TwilightForest:item.nagaScale`. | crafted blocks stay a gamble, not a vending machine | zero | 4 | reversible config / zs |
| F4 | Tomes and Binding Scrolls through bags | In `Lootbags_BagConfig.cfg`, add `qfcontent:sealed_tome` and `qfcontent:consumable` to each bag's `$STARTBLACKLIST`. Then *explicitly* whitelist tomes per bag at controlled weights (§5). In `lootbags.cfg`, set `Valid Kill Methods` to player-only. | restores scarcity; hands the enchant curve to §5's design | zero | 5 | reversible config |
| F5 | SoulShards spawner farm | `SSTOW/BlackList.cfg`: blacklist every OreSpawn boss and mini-boss (Mobzilla, The_King, The_Queen, The_Kraken, Basilisk, Nightmare, Mothra, EmperorScorpion …), TF bosses and Lycanites bosses. Set T4/T5 `Check Player=true`. | farms still work, but need a player nearby | slightly *negative* (fewer AFK spawns) | 5 | reversible config |
| F6 | Creative rewards | `DefaultQuests.json` choices: q140 Sword of Justice → TragicMC Celestial set or 8 diamond blocks; q144 Bow of Justice → `TragicMC:celestialLongbow`; q141 Infinity Egg → `witchery:brewbottle` stack or a Legendary sealed tome. | removes the post-TragicMC "win button" | zero | 5 (CC4 never handed these out) | reversible data |
| F7 | Gate-material multiples in quests | q22: 32 scale blocks → 4. q24: 64 Queen scales → 4 (or a Queen Battle Axe only). q6: drop the Zero Ring option and leave the diamonds, emeralds and bags. | one kill = one player's key, not the server's | zero | 5 | reversible data |
| F8 | Illuminati pet | `InventoryPets.cfg`: `Disable Illuminati Give Random Items=true` (it keeps its other gags). Alternatively add `ProjectE` and `OreSpawn` to `InventoryPets_illuminati_blacklist.json` (check whether the reader accepts mod IDs or only item IDs; the shipped list contains `bibliocraft` [E], which suggests mod IDs work). | closes the drip | zero | 4 | reversible config |
| F9 | Weapon inversion (scaler) | Two options. **(a) Preferred:** keep `WeaponScaler`, because it is a CC4 artefact that makes modded weapons viable, and lift the T1/T2 OreSpawn weapons instead: `OreSpawn.cfg` `Ruby_damage`, `Emerald_damage` and `Amethyst_damage` ×2–2.5 so they sit at diamond×2.5 or above. Raise `Ultimate_damage` 36 → **60** so T3 beats scaled T2 (~65 average, but 60 always, versus a rolled 26–104). Leave Bertha and Royal alone, since the caps make them plateau anyway. **(b)** Patch `WeaponScaler` in the jar to a flat ×2.5 (removes variance). | restores monotone tiers; Ultimate feels like a leap again | zero | 4 (a) / 3 (b) | (a) reversible config; (b) invasive (jar patch) |
| F10 | Morph free flight | `Morph.cfg`: `disableEarlyGameFlight=1`, `disableEarlyGameFlightMode=1` (flight unlocks after the End; check the mode semantics in game [R]). | flight becomes a reward, not a day-one default | zero | 4 (helicopters remain the CC4 early-flight fantasy) | reversible config |
| F11 | Royal sword "reuse" makes one kill serve the server | Option A: consume the Royal sword but make the recipe give 4 Dark Matter. Option B: keep reuse, accept it, and rely on F2/F7. Prefer B: reuse plus the quest is CC4's design and is fine once drops stop leaking. | minor | zero | 5 | reversible zs |
| F12 | Dark Matter EMC after learning | If the in-game check shows Dark Matter has EMC, set it to 0 in `config/ProjectE/custom_emc.cfg` (`ProjectE:item.pe_matter|0=0`, ditto `|1`), so the gate cannot be bypassed by transmutation. | closes a conditional leak | zero | 4 | reversible config |
| F13 | Repair Talisman on day one | CraftTweaker: add `TwilightForest:item.fieryBlood` or `item.scepterZombie` (reuse) to the Repair Talisman recipe. | removes free durability (which *is* defence at T4 scale) before T2 | zero | 4 | reversible zs |
| F14 | Boss teleport traps | `enderutilities.cfg` `teleporting.EntityBlackList`: add the OreSpawn and TF boss classes. | small | zero | 5 | reversible config |
| F15 | Doomlike level-8 wither skulls / beacon | `DLDungeonsJBG/chests.cfg`: skulls 1–8 → 1–3, keep the beacon. | small | zero | 5 | reversible config |

**Not recommended:**
- Removing Lucky Blocks, Pandora's Box, MCHeli or Morph. These are CrazyCraft's identity.
- Raising boss health further. MobProperties already applies ×2–5 to OreSpawn bosses and ×3–9 to Twilight [E].
- Disabling the uncrafting table. It is low-yield, and CC players know it.

---

## 5. Loot and distribution: a design for `EnchantLoot`

**What exists now:**
- Tomes go into eight vanilla chest categories at 12/8/4/2/1 by *declared* rarity.
- Consumables go in alongside them.
- That is the only source; BetterQuesting hands out none yet.

**What the census showed** (`docs/reference/enchantment-combat-results.md`) [E]:
- Declared rarity does not track power.
- Momentum (UNCOMMON) is the strongest weapon enchant.
- Excalibur (LEGENDARY) measures RARE.
- Bulwark and Cockroach measure LEGENDARY.

A table keyed on today's colours hands out power at random.

### Principles

1. **Re-tier first, then distribute.** Move each enchant to its measured band, as the census checklist says.
   - Promote: Momentum, Colossus, Berserk, Bulwark and Cockroach to LEGENDARY; Roulette, Piercing and Tank to EPIC.
   - Demote: Excalibur and Homing to RARE.
   - The Cultist + Berserk + Riposte combination needs Cultist priced *as if* it were Legendary, or Berserk and Riposte kept apart.
2. **Place tiers on the ladder, not in vanilla chests only.** Each tier's main source is a step of the §1 ladder, so a tome is a reward for reaching that step.
3. **Keep the risk.** Binding Scrolls are rarer than Legendary tomes. A Legendary tome is wasted without one, which is the gamble the design wants.
4. **No source scales with AFK time.** No tomes from spawner mobs or loot bags; all of these sources are once-per-structure or once-per-boss-kill.

### Proposed placement

| Tier | Main sources | Weight / chance | Ladder step |
|---|---|---|---|
| COMMON | vanilla dungeon and mineshaft chests (as now); Ch1–2 quests | chest weight 12 | T0–T1 |
| UNCOMMON | vanilla chests; Roguelike / Doomlike low levels; Twilight hedge mazes and hollow hills | 8 | T1 |
| RARE | Twilight boss chests (Naga courtyard, Lich tower, Labyrinth); stronghold library; Chocolate Quest dungeon bosses; quest rewards for each TF boss | 4 in TF chests; 1 guaranteed per TF boss quest | T2 |
| EPIC | **boss drops**: TF Hydra / Knight Phantom / Ur-Ghast / Snow Queen, TragicMC bosses, Witchery bosses, OreSpawn mid-bosses (Mantis, Basilisk, Kraken, Emperor Scorpion); about 25% per boss kill | `LivingDropsEvent`, only when `source.getEntity()` is a real `EntityPlayer` (not a FakePlayer) and the mob was *not* spawner-spawned | T2–T3 |
| LEGENDARY | Mobzilla / King / Queen / Rahovart kills (guaranteed 1); 1 in each OreSpawn Chaos / Crystal dimension structure chest; PACK MASTER-line quests | guaranteed per T4 boss kill | T4 |
| Binding Scroll | T4 boss kills only (50%); the end-of-line "★" quests (one each) | — | T4 |
| Ward Scroll | Epic sources at 1 in 4 | — | T3 |
| Magic Dust | as now (common) | — | all |

### Why this suits the census

- The measured LEGENDARY set (Momentum, Colossus, Berserk, Bulwark, Cockroach, Turtle) is exactly what lets a player push past the per-hit caps (§3). Putting it behind T4 kills makes the late game the place where power keeps growing.
- Colossus's cap (`max(20, hit×4)`) means it scales with the weapon. On a T3 weapon (36–82) it is already strong against killable targets, which is a reason for Epic-at-T3 if it is left uncapped. Decide the cap first (checklist item 2).
- Momentum + Assassinate saturate each other (−57 points). Rewarding both at the same step wastes a reward. Spread them across tiers.

### Implementation sketch (qf-content, about 80 lines; performance about zero)

- `EnchantLoot.registerChestLoot()`:
  - keep the vanilla categories for COMMON and UNCOMMON;
  - drop Epic and Legendary from vanilla chests entirely;
  - drop the Binding Scroll from chests.
- Add `EnchantLoot.onBossDrops(LivingDropsEvent)`:
  - **The gate:** `!(e.entityLiving instanceof EntityPlayer)`, a real player killer, and a name in a small static `Map<String, Rarity>` of boss entity names (the same names `run_campaign.py` uses).
  - **The cost:** one map lookup per mob death.
  - **Skip spawner mobs:** SoulShards tags its mobs [R]. Check `getEntityData().getBoolean("SSTOW")` or the equivalent in game, and skip those.
- Quest tomes are authoring only: `qfcontent:sealed_tome` with meta 0–4.
- Validation:
  - `/qfcensus` already counts procs;
  - add a dry-run command that rolls 10,000 boss drops and prints the tier histogram (no world needed).

---

## 6. Prioritised work list

Each item lists how to validate it. Run boots with the trial harness and keep to
one client at a time.

1. **F1: the Bountiful self-drop guard** (qf-content).
   - **Validate:** `py -3.10 tools/trial/trial.py build bountiful qfcontent`, then in game place and break a diamond block in fresh spots with a Bountiful III pickaxe, 200 times. The diamond-block count must stay flat while ores (coal or quartz from silk-less blocks) still double. Commit with the census row unchanged.
2. **F2 + F3: Lucky Block config.**
   - **Status: done in `199ae38`.** Removed: the "1 hit KO" sword; Royal, Queen Battle Axe, Bertha and Slice from the weapon jackpot; Queen and Godzilla scales from both scale groups. The Queen's pole became titanium/uranium blocks and ores; the gem tower's Mobzilla block became an emerald block. KING BOB keeps his Queen kit but drops none of it (`DropChances` 0). L100 fixed. Crafted luck is now about ⅓ of the old values on every positive item, not only the three named in F3. The in-game 200-block open is still to do. Slim boot 2026-10-17 (luckyblocks lootbags soulshards enderutilities orespawn inventorypets qfcontent morph hee, `--overlay pack`): title screen in 12 s, no config errors in `latest.log`.
   - **Validate:** `trial.py build lucky lucky orespawn twilightforest projecte crafttweaker`. Use the mod's own log on boot for parse errors on the edited lines (L100 is already malformed: `ID=OreSpawn:ID=...`, so fix it in the same pass). Open 200 max-luck blocks as op; no `OreSpawn_Royal`, `QueenScale` or `GodzillaScale` may appear.
3. **F4: loot-bag blacklist and player-only kills.**
   - **Status: done in `a38ed17`.** `qfcontent` is in the Global Blacklist and `Valid Kill Methods=Real`. No per-bag tome whitelist was added, because §5 wants no tomes from bags. The in-game bag count is still to do.
   - **Validate:** `trial.py build bags lootbags qfcontent sstow`. Kill 300 zombies from a spawner cage, then open every bag; zero `qfcontent:sealed_tome`. Check the fake-player kill path with a cage plus a blaze or a vanilla dispenser.
4. **F6 + F7: quest reward edits** (`DefaultQuests.json`; note `server/config/betterquesting/DefaultQuests.json` differs from the pack copy and needs the same edit).
   - **Validate:** `trial.py build quests betterquesting standardexpansion tragicmc witchery orespawn`. Open each edited quest in the book; no "missing item" placeholders.
5. **F5 + F14: SoulShards and Ender Utilities blacklists.**
   - **Status: done in `852b36f` (35 SSTOW entries, `Check Player=true` on every tier) and `529b174` (53 EU class names).** SSTOW already demands a real-player kill in code, and already skips IBossDisplayData mobs. Not yet tried in game.
   - **Validate:** `trial.py build farms sstow enderutilities orespawn twilightforest`. Try to bind a soul shard to a spawned Mothra and a Kraken; it must be refused.
6. **F9a: OreSpawn T1–T3 damage** (`OreSpawn.cfg`).
   - **Status: done in `b90f80b`.** A hit is 5 + config (ItemSword + player base). Emerald 6→16, Amethyst 11→20, Ruby 16→30, Ultimate 36→60 (65 per hit). Battle Axe 46→70, Chainsaw 56→80 and Attitude 82→110 were raised too, so they stay above Ultimate. The census re-run is still to do.
   - **Validate:** re-run the census controls with the Ruby and Ultimate swords against the Naga, using the campaign's T1 rows (`/qfcensus combat OreSpawn:OreSpawn_UltimateSword` …) on a *free* `C:\qfs` node after the running campaign ends. Per-hit damage must order Ruby ≥ diamond (20) and Ultimate ≥ Titan (65).
7. **F8: the Illuminati pet.**
   - **Status: done in `d7d6b33`** (`Disable Illuminati Give Random Items=true`).
   - **Validate:** `trial.py build pets inventorypets`. Carry the pet for 10 cooldowns as op; no items appear.
8. **Check F12** (Dark Matter EMC) and **F13** (Repair Talisman gate).
   - **Validate:** `trial.py build pe projecte crafttweaker orespawn twilightforest`. NEI on Dark Matter shows the EMC value; NEI shows the talisman recipe now needs fiery blood.
9. **F10: Morph flight gating.**
   - **Status: done in `ede7341`.** Morph has no End option, so it uses `disableEarlyGameFlight=2` with `customMobToKillForFlight=chylex.hee.entity.boss.EntityBossDragon`, in server-wide mode 0. The boot log confirms the class mapped. The in-game kill is still to verify.
   - **Validate:** `trial.py build morph morph`. Kill a bat in the overworld and confirm flight is withheld until the configured milestone. Remember the OptiFine E7 Morph fixes (`31da143`); test on the full client before the friends' server.
10. **§5 loot redesign** (qf-content), after the census re-tier.
    - **Validate:** a dry-run histogram command, then `trial.py build loot qfcontent twilightforest orespawn`. Kill the Naga as a player: 1 RARE tome in the quest and 0 Epic or Legendary in chests over 50 dungeon chests.
11. **F15, F11** (optional), and update `docs/reference/enchantment-tuning.md`'s Bountiful row.

**Apply every config change to three places:** the repo `pack/config`, the live
`%APPDATA%\.crazycraft4\config` (when the user says to), and the play server
`C:\qfs\friends` via `tools/server/build_play_server.py`. Never apply them to the
census nodes.

---

## Appendix: evidence that was hard to get

- **OreSpawn recipes.** These were recovered by walking `OreSpawnMain.make_some_more_things` bytecode, so they are approximate. Key results:
  - **Ultimate Sword:** `" T "/" U "/" I "`, with T = titanium ingot, U = uranium ingot, I = iron ingot.
  - **Ultimate Body:** `"I I"/"TTT"/"UUU"`.
  - **Ingots:** `"UUU"×3` from nuggets. The ores smelt to nuggets.
  - **Attitude Adjuster** (`MyHammy`): 2 Ultimate Swords + Big Hammer + Green Goo.
  - **Battle Axe:** Ultimate Sword + Ultimate Axe + Green Goo.
  - **Chainsaw:** Ultimate Axe + 8 redstone blocks.
  - **Big Bertha:** handle + guard + blade, from 14 boss parts and an Ultimate Sword.
  - **Slice:** Bertha + iron.
  - **Royal Guardian Sword:** no crafting recipe.
- **ProjectE recipes,** from `ObjHandler` bytecode:
  - Covalence dust needs no Philosopher's Stone.
  - Repair Talisman = covalence ×6 + string ×2 + paper.
  - SWRG = Dark Matter ×4 + feathers ×4 + Iron Band.
  - Collector MK2/MK3 and Relay MK2/MK3 upgrade from MK1. **Relay MK1 is ungated** (obsidian, glass, diamond block); it is useless without a collector.
  - The Philosopher's Stone conversions are present.
- **Census.** Live campaign files `C:\qfs\c2\config\qfcontent-census-combat.tsv` (Royal vs Mobzilla) and `C:\qfs\combat\config\…` (diamond vs the Naga) were read, not touched. Median boss pools from `census-run.log`: Naga 1,430–1,565, Mantis 528–592, Mobzilla 17,818.
- **What cannot be determined statically:**
  - Lucky Block weighting maths;
  - the loot-bag combine count;
  - which items OreSpawn injects into chest tables;
  - Pandora's Box effect weights;
  - Illuminati per-roll odds;
  - Dark Matter's EMC under the replaced recipe;
  - whether the King's full-power ending drops loot.
