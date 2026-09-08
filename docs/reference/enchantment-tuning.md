# Enchantment tuning pass

Every number currently in the code, extracted from the implementations so we can
go through them together. Nothing here is a proposal unless it says **⚠** — the
tables are the ground truth of what is live right now.

Mark up whatever you want changed. `ENCHANT-LIST.md` stays the roster;
`DESIGN-enchantments.md` stays the architecture; this is the balance sheet.

---

## Status

**All 81 reviewed and applied** across armor, weapons, tools and bows. The tables
below record what shipped, not what was proposed.

Outstanding: Rally's battle music, which needs an audio file before it is worth
writing. And a playtest — none of this has been felt in a real fight yet.

## The three structural questions, answered

**1. Armor enchantments fire once per equipped piece.** Decided case by case
rather than by rule. Flavour and stat enchantments are slot-locked so they cannot
stack at all; defensive and retaliatory ones stay per-piece and are balanced for a
full set. Anything per-piece that sets a value rather than adding one — Reflect —
assigns it, so four calls agree on one answer instead of compounding.

**2. Max level.** Decided per enchant, no house rule.

**3. Item targeting.** Slot-precise categories added: `SWORD`, `AXE`, `PICKAXE`,
`SHOVEL`, `DIGGER`, `HELMET`, `CHESTPLATE`, `LEGGINGS`, `BOOTS`, alongside the
broad buckets. Modded gear is matched two ways — `instanceof` for anything built
on the vanilla classes, and Forge's `getToolClasses` for tools that extend
`ItemTool` directly and would otherwise be invisible. Armor slots come from
`ItemArmor.armorType`, which modded sets fill in correctly because rendering
depends on it.

## Weapons — SETTLED

All 38 reviewed and applied. `WEAPON` means swords and axes, including modded
ones. Damage bonuses are multipliers wherever the value is large, because this
pack's weapons run from a wooden sword's 4 to well over 30 and a flat number
cannot be balanced against both.

| # | Enchant | Rarity | Lvl | Proc | What it does |
|---|---|---|---|---|---|
| 1 | Executioner | Rare | 3 | always | Damage ×`1 + 0.25 × level × target's missing health`. Up to **×1.75** against something on its last sliver; nothing at full health. Not doubled by Multi Strike |
| 2 | Berserk | Epic | 3 | always | The mirror, scaling off **your** missing health. Up to **×1.90** at level 3. Not doubled by Multi Strike |
| 3 | Frostbite | Rare | 3 | 20/30/40% | Slowness I–III (−15/−30/−45% speed) for **1.5 / 2.0 / 2.5s**. Short on purpose: at a 40% proc rate a long one is a lockdown |
| 4 | Colossus | Epic | 3 | 6/9/12% | **+2.5% of the target's maximum health per level, capped at 4× the hit that triggered it** (never less than +20). Uncapped it was 0.9% of max health per swing whatever the weapon, a ~55 s ceiling on Mobzilla with a diamond sword |
| 5 | Feast | Rare | 3 | on kill | Heals 1 / 2 / 3 hearts |
| 6 | Poisonous | Uncommon | 3 | 10/20/30% | Real Poison I for 4 / 5 / 6s — particles, milk, curing and undead immunity all behave normally — carrying **venom worth 4% of the applying hit per level, per second**. Vanilla deals poison damage from inside `Potion.performEffect`, where the invulnerability window swallows it; the venom rides alongside and actually lands. Unlike vanilla poison it **can** finish a target. The figure is a **rate**, not a per-tick amount: Accelerant drives poison to amplifier VIII where vanilla's cadence collapses to one tick, and a fixed per-tick amount there made Poisonous plus Accelerant worth **2.36×**, beating the strongest Epic in the mod from an Uncommon and a Rare. Worth **1.04×**, or 1.06× with Accelerant |
| 7 | Venomous | Rare | 3 | 8/16/24% | The same at Poison II for 7 / 9 / 11s, venom at **5.8% of the hit per level per second**, plus a **10% damage cut for 4s**. Worth **1.09×** |
| 8 | Blind | Rare | 3 | 8/16/24% | Blindness for 4 / 5 / 6s. Near-inert on mobs — 1.7.10 AI ignores sight — and brutal on players |
| 9 | Suplex | Rare | 3 | 10/15/20% | Throws them **4.5 / 6.3 / 8.3 blocks** up. Fall distance is not reset, so the landing is the damage |
| 10 | Daze | Uncommon | 3 | 10/20/30% | Spins the target 180°. Camera flip for a player; cosmetic on a mob |
| 11 | Roulette | Uncommon | 1 | always | 50/50 **×2.0 or ×0.5**. Expected value ×1.25. Not doubled by Multi Strike |
| 12 | Cultist | Rare | 3 | 8/16/24% | Damage ×2.0, and **you take 10% of your max health per level** (or 75% of the hit if that is less) as **ordinary physical damage — armor applies in full**, and armor durability is spent paying it. Never takes you below one health. The raw price at level 3 is 6.0: three hearts unarmoured, 0.24 in enchanted diamond, so what you wear decides what this costs. The old 75%-of-hit killed the wielder in every simulated fight, because this pack's weapons swing for more than a player has health. Not doubled by Multi Strike |
| 13 | Killing Blow | Epic | 3 | **0.1/0.2/0.3%** | Sets target health to 0. Set rather than dealt, because several bosses here clamp incoming damage |
| 14 | Momentum | Uncommon | 3 | always | +0.5 × level flat per consecutive hit on one target, 8 stacks, 2s window. Fully stacked: +3.5 / +7.0 / +10.5. Not doubled by Multi Strike |
| 15 | Riposte | Uncommon | 3 | always, if hurt in 3s | +1.5 / +3.0 / +4.5 flat. Not doubled by Multi Strike |
| 16 | Rupture | Rare | 3 | 25/35/45% | Bleed **4% of the applying hit per stack per second** (never less than 0.5), **ignoring armor**, for 5 / 6 / 7s. Stacks to level+1. Ticks land **past the target's invulnerability window** (see the note on `hurtThroughInvulnerability`) — before that they were discarded wholesale while you kept swinging, 148 blocked and 0 landed per 150 s. Bleed ticks do **not** count as new hits: they used to re-roll every on-hit enchantment every second, forever, with the player standing still. Worth **1.08×** sustained damage |
| 17 | Arc | Epic | 3 | 15/20/25% | 35% of the hit leaps to 1 / 2 / 3 others within 5 blocks. Chained hits do not re-roll procs, and never land on players (unless PvP is on), tamed animals, NPCs or summons |
| 18 | Disarm | Uncommon | 3 | 4/8/12% mobs, **2/4/6% players** | Knocks the held item to the floor with a 1s pickup delay. Players only when PvP is on; never CustomNPCs, tamed animals or summons |
| 19 | Assassinate | Rare | 3 | when unaware | ×1.25 / 1.50 / 1.75, **only if the target is not already targeting you**. An opener, not a passive. In a group this is a standing bonus for whoever is not being tanked. Not doubled by Multi Strike |
| 20 | Sunder | Uncommon | 3 | 10/20/30% | Cuts their damage **8 / 16 / 24%** and applies Mining Fatigue I–III, for 4 / 5 / 6s |
| 21 | Rage | Epic | 3 | 5/10/15% | **Strength I for 4 / 6 / 8s.** Fixed at I: 1.7.10 Strength is multiplicative (`1.3 × (amplifier+1)` on the total), so I is already ×2.3 and III would be ×4.9. Level buys duration |
| 22 | Cripple | Rare | 3 | 10/20/30% | Cuts the target's outgoing damage **20 / 30 / 40%** for 6 / 8 / 10s. **No slow.** Tracked ourselves, because vanilla Weakness is a flat −0.5 |
| 23 | Accelerant | Rare | 3 | **12% flat** | Every negative effect on the target gains `+level` amplifier and +2s per level, up to a ceiling of **IV / VI / VIII**. **Wither stops at IV** at every level: wither V is 10 damage a second and VI and up is 20 a second, armor-ignoring and lethal. Poison keeps the full ceiling (it stops at half a heart; undead are immune). Slowness VII is a full freeze; worth watching, since Frostbite and Bola supply the slowness it amplifies |
| 24 | Lich | Epic | 3 | on kill | Absorption I–III (4 / 8 / 12 shield health) for 20 / 25 / 30s |
| 25 | Excalibur | Legendary | 1 | always | **+4 flat damage**, and while held: permanent Strength I (×2.3 damage), Resistance I and Speed I. Left deliberately enormous |
| 26 | Necromancer | Rare | 3 | 3/6/9% | Summons a zombie or skeleton for 30 / 40 / 50s, **target-locked to your enemy and never to you** |
| 27 | Alpha | Rare | 3 | 3/6/9% | Summons a wolf tamed to you, same duration |
| 28 | Bastion | Epic | 3 | 3/6/9% | Summons an iron golem, same duration. **Will attack players**, because its target is assigned outright rather than left to golem AI |
| 29 | Trade | Rare | 3 | 2/4/6% | Swaps your selected hotbar slot with theirs. Players only |
| 30 | Decapitate | Common | 3 | **15/30/40%** | Drops the head. Vanilla skulls only: skeleton, wither skeleton, zombie, creeper, player |
| 31 | Crushing Blow | Epic | 3 | while sneaking, 10s cooldown | ×1.6 / 2.2 / 2.8 plus a knock-up |
| 32 | Get The Fuck Off Me | Epic | 3 | while right-click held, **10 minute cooldown** | Launch velocity 4 / 5 / 6 with 1 up, fall distance zeroed: roughly **40 / 50 / 60 blocks** of travel. Deliberately the far version, and the cooldown is what it costs |
| 33 | Rally | Common | 1 | opening blow of a fight | Plays a flourish. **Battle music pending** — see below |
| 34 | Reach | Epic | 3 | passive | **+1 block of range per level**, mining and melee both. Survival base is 4.5, so level 3 is 7.5 |
| 35 | Tracker | Common | 3 | passive | Outlines living things through walls within 16 / 32 / 48 blocks |
| 36 | Jammer | Legendary | 3 | always, vs players | Downsamples their screen, factor `3 + 2×(hits−1) + (level−1)` capped at 16, for 5 / 7 / 9s. **Seven consecutive hits reaches the cap** |
| 37 | Multi Strike | Legendary | 1 | — | Every other custom enchantment on the item rolls twice, independently |
| 38 | Demon Forged | Legendary | 1 | passive | Sets the vanilla `Unbreakable` tag — and **removes it again** if the enchantment ever goes, which it previously did not |

### Two 1.7.10 mechanics that shaped the above

**Strength is multiplicative.** `PotionAttackDamage.func_111183_a` returns
`1.3 × (amplifier + 1)` against an operation-2 attribute modifier, so Strength I
is ×2.3 melee damage, II is ×3.6 and III is ×4.9. This is not the additive
Strength of later versions. It is why Rage is pinned at level I.

**Weakness is a flat −0.5 damage per level**, not a percentage. Against a modded
weapon swinging for 25 that is a 2% debuff, so every enchantment that wanted a
real damage debuff — Cripple, Sunder, Venomous — routes through our own
percentage tracker in `TickedEffects` instead.

## Tools — SETTLED

| # | Enchant | Rarity | Lvl | Applies to | Proc | What it does |
|---|---|---|---|---|---|---|
| 1 | Magnetize | Common | 1 | any tool | always | Drops go to your inventory; anything that will not fit falls normally |
| 2 | Haste | Epic | 3 | any tool | passive | Permanent Haste I–III: +20 / +40 / +60% dig speed |
| 3 | Excavate | Uncommon | 3 | **pickaxe** | always | Breaks a connected vein of up to 8 / 16 / 24 blocks. **Ores only.** Sneak to disable. 1 durability per block |
| 4 | Timber | Uncommon | 1 | **axe** | always | Fells up to 128 logs, searching upward. Sneak to disable |
| 5 | Tunneler | Epic | 3 | **pickaxe** | always | 3×3 / 5×5 / 7×7 slab perpendicular to your facing. 7×7 costs 48 durability per swing |
| 6 | Sieve | Common | 3 | **pickaxe + shovel** | 2/4/6% | On stone, dirt, gravel, sand or cobble: one of flint, coal, gold nugget, clay. Vanilla blocks only |
| 7 | Bountiful | Uncommon | 3 | any tool | **11/22/33%** | Doubles the block's drops when the tool has no Fortune of any kind (vanilla, V, X or Bold). **One payout per block position**, so it cannot be farmed by replacing and rebreaking. **Never a block with a tile entity, never a drop carrying NBT**: a placed backpack or a compact machine copied with its contents is a duplicator |
| 8 | Transmuter | Epic | 3 | **pickaxe** | 3/6/9% | Breaking an ore adds a second ore drawn from a **weighted distribution**, never more than one harvest tier above what you broke |
| 9 | Old Reliable | Uncommon | 3 | any tool | always | Mining XP × `(1 + wear × level)`. A fully worn tool at L3 gives 4× XP |
| 10 | Eco-Friendly | Common | 3 | any tool | on break | Refunds `min(level, 3)` of the repair material. **Now works on modded tools** |
| 11 | Mending | Epic | 1 | **any gear** | always | 2 durability per XP point collected, consuming the XP |
| 12 | Fortune V | Rare | 1 | **pickaxe** | always | Ores drop 0–4 extra copies (×3 on average). Cannot coexist with vanilla Fortune, Silk Touch, Fortune X or Bold |
| 13 | Fortune X | Epic | 1 | **pickaxe** | always | Ores drop 0–9 extra copies (×5.5 on average). Same exclusions |
| 14 | Bold | Epic | 1 | **pickaxe** | always | Doubles what **vanilla** Fortune is doing. Cannot coexist with Fortune V or X: stacked on Fortune X it multiplied to **30 ores per block**, forty with Bountiful |
| 15 | Prospector | Rare | 3 | **pickaxe** | passive | Client-side scan every 2s, radius 12 / 16 / 20 and ±8 vertical, listing nearby ore |
| 16 | Torchlight | Uncommon | 3 | **pickaxe** | passive | Invisible light block at head height, level 9 / 12 / 15 |

### How Transmuter's distribution works

There is no cross-mod ore *rarity* API in 1.7.10 — nothing reports how often a
block generates. The numbers exist (vanilla places 20 veins of coal per chunk and
1 of diamond) but they are arguments to method calls inside each mod's generator,
not data attached to a block. Unqueryable — but perfectly **measurable**.

`OreDistribution` builds its pool at postInit from whatever the ore dictionary
contains, and weights it from one of two sources:

1. **A survey**, once one exists (≥ 200 chunks). Real measured abundance.
2. **Harvest tier**, as a fallback: `240 / (1 + harvestLevel × 5 + hardness)`.
   A proxy for *tier*, not rarity — coal and iron share a tier but differ
   threefold in abundance — which is exactly why the survey is worth running.

Either way a roll is restricted to ores at most **one harvest tier above** the
block that was broken. No mod is named anywhere; adding or removing one changes
the pool by itself.

### Running an ore survey

`/qfsurvey start [chunks] [budgetMs]` (op only). **No player, no flying, no client**
— chunk generation is server-side and can be driven directly: the survey generates
terrain itself, counts what came out, and throws it away. Then `/qfsurvey show [n]`,
and `/qfsurvey stop` to end early. Results persist in
`config/qfcontent-oresurvey.txt`, keyed on registry name rather than block id so
they survive a mod being added.

Sample size is the thing that matters. The interesting ores are the rare ones, and
rare ores are exactly what a small sample gets wrong — at one vein per few hundred
chunks, a thousand-chunk survey is measuring noise. Default is 5,000 chunks; the
ceiling is a million. It logs progress and rewrites the file every 10,000 chunks,
so a multi-hour run can be left alone and survives a crash.

Two things make it correct rather than merely fast:

- **Patches, not scattered chunks.** Ore is placed during *populate*, and
  `Chunk.populateChunk` refuses to populate until a chunk's `+1/+1` neighbours
  exist. Isolated chunks come out as bare terrain with zero ore in them. So each
  sample generates a 10×10 patch and counts only the middle 7×7 — the chunks whose
  whole 3×3 neighbourhood has been populated, since a vein can spill across a
  boundary. 49 chunks measured per 100 generated.
- **A tick budget, not a chunk count.** A fixed count cannot suit both vanilla and a
  113-mod pack where a single chunk can cost hundreds of milliseconds; a time budget
  self-throttles to whatever the pack actually costs. It takes 20 ms of each 50 ms
  tick with players online and 45 ms with nobody on, because a dedicated box
  generating a large sample has nothing to stay out of the way of. Pass `budgetMs`
  to force it.

Counts accumulate across runs and across dimensions, so **run it once per
dimension** — an overworld-only survey leaves nether ores like quartz unmeasured,
and they fall back to weight 1.

Verified on a headless dedicated server: 343 chunks measured from 700 generated in
5.5 s with no tick overruns. The result checks against vanilla's own generator —
every ore lands on the same ~0.45–0.55 ratio of measured blocks to nominal
`veins × size`, which is the shortfall `WorldGenMinable` produces through overlap:

| Ore | Vanilla call | Nominal /chunk | Measured | Ratio |
|---|---|---|---|---|
| Coal | 20 × 16 | 320 | 140.7 | 0.44 |
| Iron | 20 × 8 | 160 | 76.3 | 0.48 |
| Redstone | 8 × 7 | 56 | 25.9 | 0.46 |
| Gold | 2 × 8 | 16 | 8.9 | 0.56 |
| Lapis | 1 × 6 | 6 | 3.5 | 0.58 |
| Diamond | 1 × 7 | 7 | 3.3 | 0.47 |

Emerald came in at 0.02/chunk — it only generates in extreme hills. The heuristic
would have rated it alongside iron.

### How Eco-Friendly finds a repair material

It used to read the vanilla `ToolMaterial` enum, which only covers gear built on
one of the five vanilla materials — a small minority here. It now asks the item
itself through Forge's `Item.getIsRepairable(ItemStack, ItemStack)`, which every
modded tool implements because the anvil depends on it, testing against every
`ingot*`, `gem*`, `nugget*` and `plate*` in the ore dictionary plus a few vanilla
staples. Cached per item type, so the scan runs once per tool rather than once per
break.

## Bows — SETTLED

Arrows do not remember which bow fired them, so `ArrowTracker` tags each arrow
with the bow's enchantments at launch and everything here reads that tag.

| # | Enchant | Rarity | Lvl | Proc | What it does |
|---|---|---|---|---|---|
| 1 | Piercing | Rare | **3** | always | ×1.15 / 1.30 / 1.45 damage. A stand-in for armor penetration, since armor is applied after the event we hook. Not doubled by Multi Strike |
| 2 | Penetrating | Rare | 3 | always | The arrow continues through up to `level` targets at ×0.85 speed and ×0.8 damage each. **Now spawns one block further along its heading**, so it cannot immediately re-hit what it just passed through |
| 3 | Ricochet | Epic | 3 | always | Spawns a second arrow at the nearest **valid** target within 8 blocks, ×0.75 damage, up to `level` bounces |
| 4 | Bola | Rare | 3 | always | Slowness I–III for 6 / 8 / 10s. The only slow in the mod with no proc roll, which a bow's slower rate of fire earns |
| 5 | Instant Transmission | Epic | 1 | always, **3s cooldown** | Teleports you to the arrow when it lands, fall distance zeroed |
| 6 | Soul Entwine | Rare | 1 | always, **5s cooldown** | Swaps your position with whatever you hit |
| 7 | Homing | Legendary | 3 | always | Steers toward the nearest **valid** target within 9 / 12 / 15 blocks, blending heading by 10 / 20 / 30% per tick |

**Valid target** means not the shooter and not a tamed animal — so a guided arrow
no longer curves into your own wolves, and a ricochet no longer bounces off a mob
into the villager behind it. Shared by Ricochet and Homing.

## Armor — SETTLED

These twenty are applied and in the build. Slot-locked ones can only ever be on
one piece; per-piece ones are balanced for a full set.

| Enchant | Rarity | Lvl | Slot | Proc | What it does |
|---|---|---|---|---|---|
| Nightsight | Common | 1 | helmet | passive | Night vision whenever you are somewhere at light level 8 or below. Lapses on its own in daylight |
| Frog | Rare | 3 | boots | passive | Permanent Jump Boost I / II / III |
| Deft | Epic | 2 | boots | passive | Permanent Speed I / II (+20% / +40% movement) |
| Tank | Rare | 3 | chestplate | passive | Permanent Slowness I, and you take **11% / 22% / 33%** less damage. Applied directly rather than as Resistance, because Resistance only comes in 20% steps and 33% is not expressible as one |
| Cockroach | Epic | 3 | chestplate | a hit that leaves you **alive** at ≤ 1 heart, once a minute | **Resistance II / III / IV for 5 / 6 / 7s** — a second wind, long enough to run or to take the fight back. It does **not** blunt the triggering hit; you are meant to feel that one. **60 s cooldown.** The qualifying test asks `Mitigation.predict`, not the raw event damage: LivingHurtEvent fires before armor, so comparing the raw figure to health made this fire on nearly every boss swing and read as a permanent 80% reduction that made a player unkillable. Never amplifier 4, which is total immunity. Runs in the PROC phase, after Tank, Bulwark, Turtle and Stonehide |
| Regrowth | Rare | 3 | leggings | 10s out of combat | Regeneration I / II / III. Stops the instant anything hits you |
| Bulwark | Rare | 3 | chestplate | always | Damage reduction that grows as health falls: nothing at full health, up to **10% / 20% / 30%** at death's door. Not doubled by Multi Strike |
| Cleansing | Rare | 3 | leggings | 10 / 20 / 30% | Strips one negative potion effect when something hits you. **If what it strips is Tank's slowness, Tank stays off for 20 seconds** rather than re-applying |
| Camouflage | Rare | 3 | leggings | 10 / 20 / 30% | A mob that targets you immediately forgets you. Stops fights starting; does not end one already underway |
| Flippers | Uncommon | 3 | boots | passive | Depth Strider. Closes the swim-speed gap in thirds, so level 3 swims at walking pace. Hard-capped at land sprint speed so it cannot overshoot into rubber-banding. **Applied on the client** for the local player: movement is client-owned, and the server-side version moved nobody |
| Vigor | Epic | 3 | chestplate | passive | **+4 maximum health per level** — up to 6 extra hearts at level 3 |
| Stonehide | Uncommon | 3 | **per piece** | always | 3% per piece per level against falls and explosions only. Full set at L3: about **31%**. Not doubled by Multi Strike |
| Turtle | Legendary | 1 | **per piece** | while not holding **any weapon** (sword, axe, bow, or a whitelisted modded weapon) | **33% per piece.** Reductions multiply, so a full set lands on exactly **80%** — 33 / 55 / 70 / 80% for one to four pieces. Not doubled by Multi Strike (it was 55% per piece, 96% for a set). Checking only swords made a Turtle archer the strongest build in the mod. **A hit always delivers at least half a health point** while Turtle is active: the full set on enchanted diamond took a 40-damage swing to 0.22, under the 0.25-per-second regeneration floor, and the wearer simply could not be killed by anything in the pack. The floor is the smaller of half a point and what the hit would have done without Turtle, so wearing it can never make a hit worse — in the pack's best armor a swing already lands for less than that. A full defensive set now dies to The King in about **420 s** instead of never |
| Rebound | **Common** | 3 | **per piece** | 2 / 4 / 6% per piece | Shoves the attacker back with **1.0 / 1.25 / 1.5 of push and 0.42 of lift**, roughly 4 blocks. A full set works out at roughly 8 / 16 / 23% per hit. The old 0.6–1.2 push with 0.3 of lift was recovered inside a single attack interval and measured as doing nothing at all; distance comes from airtime as much as from speed, so the lift went up with it. Dropped to Common to match what it is |
| Reflect | Epic | 3 | **per piece** | 8 / 12 / 16% per piece | Launches the attacker **2 blocks back and 1 block up per piece worn** — a full set throws them 8 blocks away and 4 into the air. Sets velocity rather than adding it, so the four per-piece calls agree on one launch instead of compounding |
| Affliction | Legendary | **4** | **per piece** | see below | Seven debuffs on the attacker at once: poison, wither, blindness, nausea, weakness, slowness, mining fatigue, all at the enchantment's level. **The chance falls as the level rises** — a full set of Affliction I procs ~3.8% of hits for level I debuffs; a full set of Affliction IV procs ~1% for level IV |
| Polarize | Legendary | 3 | **per piece** | 0.01% per level per piece | Wipes every enchantment off the attacker's armor and held item, permanently. See the note below on how rare this actually is |
| Frostpath | Rare | 3 | boots | passive | Freezes still source water under you, radius 1 / 2 / 3. **Thaws back to water after 20 s**, like Frost Walker; left permanent it paved oceans and broke other players' water sources |
| Sacrifice | Rare | 1 | **per piece** | on lethal damage | Survive at half health: effects cleared, Regen II and Resistance II for 10s, Fire Resistance for 20s. Destroys the piece, and the slot is cleared at once rather than left holding a zero-count ghost. A full set is four saves. Runs from `DeathHandler`, ahead of GraveStones |
| Soulbound | Legendary | 1 | any gear | on death | Never dropped, pulled from the inventory ahead of GraveStones, stashed in the player's persisted NBT (survives a restart) and returned on respawn. A dropped copy is now **watched from the moment it hits the ground**: its Forge lifespan is set to never expire, and once a tick anything burning is put out and anything in lava or below the world is handed back to its owner, or lifted to the surface if the owner is away. None of those paths fires a cancellable event, and `Entity.isImmuneToFire` is protected while `Entity.invulnerable` is private, so neither can be set without reflection — watching works instead because lava deals 4 damage a tick against an item's 5 health, leaving exactly one tick to act. **Explosions are still not covered**: they delete an item entity in a single hit |

**Affliction's per-piece chances** are the fourth root of the intended full-set
figure, since four pieces each roll independently: 0.97% / 0.73% / 0.49% / 0.25%
per piece, giving 3.8% / 2.9% / 1.9% / 1.0% for a full set. The roll is done
inside the enchantment rather than through `getProcChance`, which only speaks in
whole percent.


---

## Balance pass, 2026-09-06

Findings from a source review plus simulation against the pack as configured
(MobProperties ×4–10 health, OreSpawn weapons to 746, Lycanites and TragicMC
damage caps, GraveStones, InfernalMobs, LootBags). The simulation is in
`tools/balance-sim/qfsim.py`; the per-enchant changes are recorded in the rows
above. Three structural changes:

- **Dispatch runs in phases.** Flat adds, then multipliers, then procs, whatever
  order the books were applied in. Before, the same sword did 11% more or less
  damage depending on which tome came first.
- **Multi Strike doubles procs, not passives.** Anything with a 100% chance whose
  effect is a multiplier or a flat add now returns false from `isMultipliable`:
  "twice" for those meant squaring the multiplier (Executioner ×1.75 became
  ×3.06; a Turtle set went from 80% to 96%). It still doubles Colossus, Killing
  Blow, Arc, Rupture, Rage and the summons, which is where the fun is.
- **Our own damage is not a new swing.** Rupture's bleed, Arc's chains and
  Cultist's self-damage all set a reentrancy flag, and the bridge skips the
  weapon dispatch while it is set.

Decided and deliberately **not** changed: no per-item cap on custom enchants
(accumulation is to be governed by the loot pool and by the per-rarity success
ranges, which are the next pass); summons may attack other players (only the
summoner, tamed animals, NPCs and other summons are excluded); Assassinate keeps
its group behaviour.

Death handling moved to `DeathHandler`, registered in **preInit** with the mod
declared `before:gravestonemod`, because GraveStones empties the inventory on
`LivingDeathEvent` at HIGHEST priority from its own preInit. Sacrifice runs first
and can veto; the Soulbound sweep runs only if the death stands and keepInventory
is off.

The pack's `config/qfcontent.cfg` is the source of truth for IDs and has to be
shipped to the server and every client. Its numbering differs from the dev
workspace's (Railcraft, BiblioCraft and OpenBlocks own 190–192, 196–197 and
211–213 in the pack).

## Benchmark pass, 2026-09-07

`tools/balance-sim/qfbench.py` (output `bench_output-2026-09-07.txt`) benchmarks
combinations rather than single enchantments, and simulates the defensive half
instead of multiplying it out on paper. Two code changes came out of it, both
recorded in the rows above: Cultist's price became physical damage, and Cockroach
learned to ask what a hit will actually cost.

What the numbers say, for the loot pass:

- **Damage-over-time did nothing while you were attacking — now fixed.** Rupture,
  Poisonous and Venomous all measured exactly 1.00×, because their ticks landed
  inside the target's own invulnerability window from your last swing and were
  discarded: 148 bleed ticks blocked and 0 landed in a 150-second fight. That is
  vanilla's `hurtResistantTime` rule, not a dispatcher bug.
  `TickedEffects.hurtThroughInvulnerability` zeroes the timer for the duration of
  the call and puts it back, so ticks land while the wielder's next swing is
  untouched; the target's motion is restored too, because the path it forces also
  applies knockback and a once-a-second shove would push a boss around the arena.
  Poison's damage is dealt inside `Potion.performEffect` and cannot be reached, so
  Poisonous and Venomous now carry their own venom alongside the real poison
  effect, following its cadence. They are worth 1.04× and 1.09×.
- **Against a damage-capped boss every multiplier is worth nothing.** Lycanites
  and TragicMC clamp incoming damage per hit, so all the multiplier enchantments
  measure 1.00× against Rahovart. Damage caps are the pack's real ceiling.
  Since the fix, the damage-over-time enchantments are the **only** ones that beat
  a cap — 1.08× / 1.06× / 1.04× — because a cap limits the size of a hit, not how
  many arrive. That gives those three a clear job that nothing else in the set
  can do.
- **Rage is the strongest single offensive enchantment** at roughly 2.1×, because
  vanilla Strength is ×2.3 and it keeps it up permanently. Colossus with Multi
  Strike is the only strongly superlinear pair, at 1.5× over the two parts.
- **Accumulation is gentle in the middle and steep at the top.** Four random
  offensive enchantments give a median 2.0×; eight give a median 3.9× but a
  worst case of 8.9×. The tail, not the median, is what a loot table has to price.
- **0.25 health per second is the line between tough and unkillable**, because
  natural regeneration is one health every four seconds. Any loadout that pushes
  an attacker below it can never be killed by that attacker. Only a full Turtle
  set crosses it, and only with the weapon put away. Cockroach used to cross it
  against everything tested; rebuilt as a cooldown ability it no longer moves a
  build across the line at all, and the full non-Turtle defensive stack went from
  surviving indefinitely to dying in about five minutes.
- **Turtle is worth 5× survivability and costs you your weapon.** That is the
  right shape for a Legendary and needs no change.
- **Rebound is nearly inert** (2.5 blocks of knockback is recovered inside one
  attack interval) and **Reflect's value collapses against fast bosses**: it
  removes 85% of attack uptime from a slow mob and 40% from a flying one.

## Gear pass, 2026-09-07

Everything above was measured in vanilla diamond with a diamond-tier weapon,
which nobody is wearing by the time they meet these bosses. Armour totals were
read out of the mod jars with `javap` — `EnumHelper.addArmorMaterial` takes its
numbers as bytecode constants, so no decompiler is needed, which matters because
fernflower produced nothing for OreSpawn — and out of `OreSpawn.cfg`, which is
config-driven. The extractor is `tools/balance-sim/geardig.py`, its raw output
`geardig_raw.txt`, and the benchmarks are section D of `qfbench.py`.

### Retracted: the "invulnerable armour" finding

An earlier version of this section claimed the pack had armour that made players
literally invulnerable, on the grounds that 1.7.10's `applyArmorCalculations`
does `(25 - points) / 25` with no clamp. **That was wrong**, and it was wrong in
the way that matters: it described a code path players never take.

`EntityLivingBase.damageEntity` calls `applyArmorCalculations`. **`EntityPlayer`
overrides `damageEntity` and calls `ISpecialArmor.ArmorProperties.ApplyArmor`
instead** — Forge replaces the vanilla formula outright for players. Mobs use the
vanilla one; players do not. Below 25 points with ordinary armour the two agree
exactly, which is why the substitution went unnoticed for as long as it did.

`ApplyArmor` sums a per-piece absorption ratio of `damageReduceAmount / 25`, and
then does the thing the vanilla formula has no equivalent of: it caps each
piece's absorption at that piece's **remaining durability**, with damage scaled
up by 25 inside the comparison. So a piece absorbs at most
`remaining_durability / 25` damage from any one hit, whatever its armour rating.
A full undamaged vanilla diamond set holds 1819 durability between its four
pieces, which is 72.8 damage of absorption in total. Against a 350-damage swing
it stops 73 and passes 277.

This inverts the finding. Armour points stop predicting anything once hits get
large, and the pack's hits are very large. Boss damage, from the mob block of
`OreSpawn.cfg` — and `MobProperties` scales these bosses' *health* by 3–6× while
leaving their damage alone, so these stand as written:

| Boss | Attack | Health after MobProperties |
| --- | --- | --- |
| OreSpawn The King | 350 | 21,000–42,000 |
| OreSpawn The Queen | 225 | 18,000–36,000 |
| OreSpawn Mobzilla | 175 | 12,000–24,000 |
| OreSpawn Kraken | 40 | 3,000–6,000 |

A separate error rode along with the first one: the benchmarks above labelled a
40-damage hit "The King". 40 is the Kraken. The King hits nearly nine times
harder.

Damage reaching a 20 HP health bar from one swing on a fresh set, built-in
enchantments included (section D2):

| Set | Pts | Durability | Kraken 40 | Mobzilla 175 | Queen 225 | King 350 |
| --- | --- | --- | --- | --- | --- | --- |
| vanilla diamond | 20 | 33 | 8.0 | 102 † | 152 † | 277 † |
| OreSpawn amethyst | 22 | 100 | 4.8 | 21.0 † | 37.9 † | 140 † |
| TragicMC overlord | 24 | 35 | 1.6 | 97.8 † | 148 † | 273 † |
| OreSpawn ruby | 25 | 90 | 0.0 | 7.3 | 41.3 † | 152 † |
| OreSpawn ultimate | 34 | 200 | 0.0 | 0.0 | 0.0 | 0.0 |
| OreSpawn mobzilla | 38 | 1000 | 0.0 | 0.0 | 0.0 | 0.0 |
| OreSpawn royal | 42 | 2000 | 0.0 | 0.0 | 0.0 | 0.0 |
| OreSpawn queen | 48 | 1500 | 0.0 | 0.0 | 0.0 | 0.0 |

† one-shot kill from full health.

Ruby is a strong set that shrugs off a Kraken and is killed outright by one
swing from The Queen — which is what the pack's actual play reports, and what my
earlier claim of invulnerability contradicted.

The four extreme sets do take zero from a fresh swing, and only durability ends
that. Section D3, seconds survived at one landing hit a second with natural
regeneration:

| Set | Pts | Durability | Built-ins | Kraken | Mobzilla | Queen | King |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OreSpawn ruby | 25 | 90 | — | 88 | 3 | 1 | 1 |
| OreSpawn ultimate | 34 | 200 | Prot V | 251 | 43 | 29 | 11 |
| OreSpawn mobzilla | 38 | 1000 | Prot X, Unb V | >1800 | 416 | 317 | 195 |
| OreSpawn queen | 48 | 1500 | — | >1800 | 428 | 331 | 206 |
| OreSpawn royal | 42 | 2000 | Prot X, Unb V | >1800 | 860 | 665 | 422 |

Queen has the most armour points in the pack and dies faster than Royal, which
has six fewer points but twice the durability plus Protection X and Unbreaking V
built into the config. That ordering is the whole argument: **durability, not
points, is what decides a fight at this scale.**

Nothing is invulnerable, and no config edit is needed. The `orespawnarmor` block
was checked against the jar's compiled defaults and matches exactly, so the pack
has not been altered.

### Verified by running the game's own code, not by reading it

The armour claim above was disputed, and a transcription is only as good as the
person who read the source. `tools/armor-probe/` calls
`ISpecialArmor.ArmorProperties.ApplyArmor` and
`EntityLivingBase.applyPotionDamageCalculations` **directly**, on real
`ItemStack`s built by `EnumHelper.addArmorMaterial`, out of the deobfuscated Forge
jar in `build/rfg`. It runs on Java 8 because `EnumHelper` uses
`sun.reflect.ReflectionFactory` internals that changed afterwards.

The decisive experiment holds armour points fixed at 25 and changes only the
durability factor:

| 25-point set | Durability | hit 10 | hit 40 | hit 175 | hit 350 |
| --- | --- | --- | --- | --- | --- |
| identical reductions | 5 | 0.52 | 28.84 | 163.84 | 338.84 |
| identical reductions | 15 | 0.00 | 8.52 | 141.84 | 316.84 |
| identical reductions | 33 | 0.00 | 0.00 | 102.24 | 277.24 |
| identical reductions | 90 | 0.00 | 0.00 | 7.32 | 151.84 |
| identical reductions | 300 | 0.00 | 0.00 | 0.00 | 0.00 |

Same points, same reductions, same hit; damage from 338.84 to zero. The
`AbsorbMax` comparison that does it is present in the pack's own
`forge-1.7.10-10.13.4.1558-1.7.10-universal.jar`, disassembled and checked, not
just in the workspace copy.

**The cap only binds when a hit is large relative to remaining durability.** For a
fresh diamond chestplate that is above roughly 66 raw damage. Below it armour
behaves exactly as the point total predicts and durability is irrelevant — which
is every ordinary fight in Minecraft, and why this is invisible in normal play and
decisive against this pack's bosses.

### Correction: Protection is rolled per hit, and is half as strong as assumed

`EnchantmentHelper.getEnchantmentModifierDamage` does not return the summed level.
It returns `(k + 1 >> 1) + rand.nextInt((k >> 1) + 1)`. Four pieces of Protection
IV give `k = 20`, so the modifier lands uniformly in **10 to 20**, and the
reduction is between 60% and 20%, **averaging 40%** — not the flat 80% the cap
suggests. It is re-rolled on every hit.

The simulation had used the flat reading and so made Protection twice as good as
it is. `Mitigation.java` was never affected: it calls the real method. Corrected
figures, averaged over 4000 rolls of the real pipeline:

| Set | Prot | hit 40 | hit 175 | hit 225 | hit 350 |
| --- | --- | --- | --- | --- | --- |
| vanilla diamond | IV | 3.20 | 41.16 | 60.76 | 111.00 |
| OreSpawn ruby | IV | 0.00 | 2.90 | 16.53 | 60.96 |
| OreSpawn ultimate | V (built in) | 0.00 | 0.00 | 0.00 | 0.00 |

### The King enrages, up to sixteen times

`TheKing.attackEntityAsMob` deals a field called `attdam`, not the config value.
`attdam` starts at `TheKing_attack` (350) and `onUpdate` multiplies it by 2, 4, 8
or 16 as his health falls below 2/3, 1/2, 1/4 and 1/8 of `mygetMaxHealth()`.

Two things defuse it in an ordinary fight. Every branch is gated on
`player_hit_count < 10`, and that counter increments in `attackEntityFrom` on
**every hit a player lands**, so it passes ten almost immediately and the enrage
stops arming. And `mygetMaxHealth()` returns the *config* health, 7000 — not the
MobProperties-scaled pool — so the first threshold is 4,666 health out of a real
maximum of 21,000 to 42,000, the last 11–22% of the bar. The counter is reset to
zero once when he says "Prepare to die!", which re-arms it for ten more hits.

Seconds survived at each enrage tier, real pipeline:

| Set | ×1 = 350 | ×2 = 700 | ×4 = 1400 | ×8 = 2800 | ×16 = 5600 |
| --- | --- | --- | --- | --- | --- |
| vanilla diamond | 1 | 1 | 1 | 1 | 1 |
| OreSpawn ruby | 1 | 1 | 1 | 1 | 1 |
| OreSpawn ultimate | 11 | 1 | 1 | 1 | 1 |
| OreSpawn mobzilla | 196 | 83 | 24 | 1 | 1 |
| OreSpawn royal | 424 | 196 | 83 | 23 | 1 |

Nothing in the pack survives a single enraged swing past ×8.

The built-in enchantments were also missing from the earlier pass entirely. Every
OreSpawn set carries configured Protection, Unbreaking, blast/fire/projectile
protection and feather falling, applied as real NBT on creation
(`ItemOreSpawnArmor.onCreated`). Mobzilla and Royal carry **Protection X and
Unbreaking V**. Four pieces of Protection IV already reach the cap of 20 in
`applyPotionDamageCalculations` (5 per piece × 4), so Protection X is worth
exactly as much as Protection IV and not a point more — all six levels above IV
are dead weight. Unbreaking V is a real 1.50× on durability (measured: armour
rolls a 60% chance of no protection at all before the `nextInt(level+1) > 0`
check, so Unbreaking III is 1.43× and V only 1.50×), and at this scale
durability is worth more than points. Full table in `tools/balance-sim/orespawn_armour.json`.

Two smaller findings from the same pass:

- **Offensive enchantments hold their value across weapon tiers**, because almost
  all of them are multipliers. The exception is Colossus, which falls from 1.47×
  on a diamond sword to 1.25× on the Royal Guardian, since its bonus is capped at
  four times the triggering hit. Executioner runs the other way, 1.05× to 1.33×,
  because a faster kill means more time spent against a hurt target.
- **The accumulation ceiling is worst on weak weapons.** Every offensive
  enchantment at once is worth 40× on a diamond sword and 6× on the Royal
  Guardian, because the big weapons already have the damage. A player who gets
  lucky early is proportionally far further ahead than one who gets lucky late,
  which is an argument for the success-range approach rather than against it.

## Still open

**Rally's battle music.** Rally would replace the ambient track with combat music
when a fight opens. The plumbing is buildable — register a sound event, suppress
`MusicTicker` client-side, play ours, hand control back when the fight ends — but
it needs an audio file, and there is none in the workspace. Two decisions first:

- Where the track comes from: composed, sourced, or one of the prototypes from
  the earlier music work.
- Whether it interrupts only ambient music, or also whatever the pack's own music
  system is playing.

Everything else in all four categories is reviewed and applied. What has NOT
happened is a playtest: whether the odds feel right, and whether any given effect
is fun, are questions the code cannot answer.
