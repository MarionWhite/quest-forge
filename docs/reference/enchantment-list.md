# Enchantment master list

Working list. Architecture lives in `DESIGN-enchantments.md`.

## Build status

**Built and registering: 81 — every approved enchantment.** Framework, dispatcher,
ID pinning, the book, the drag-and-drop coremod, the client layer, and the
enchantments across every category.

The last five were the ones that needed rendering or bytecode rather than an
event handler. All are now in:

| Enchantment | How it ended up being done |
|---|---|
| **Reach** | Half ASM, half API. `ReachTransformer` patches `PlayerControllerMP.getBlockReachDistance` so the *client* aims further, and the `36.0D` entity check in `NetHandlerPlayServer` so the *server* believes an attack. The server's *block* reach needed no bytecode at all — Forge already routes it through a settable `getBlockReachDistance`, so `ReachUpkeep` sets it from the player tick |
| **Tracker** | `TrackerFX`. Wireframe boxes with the depth test off, drawn at `RenderWorldLastEvent`. Red for hostiles, blue for players, green for the rest |
| **Prospector** | `ProspectorHUD`. Ore is identified through the **ore dictionary**, not a hardcoded list, so every modded ore in the pack is found for free. Scans every 2s, results cached per block+meta |
| **Jammer** | `JammerFX`. A genuine downsample in fixed-function GL: copy the world render to a texture, draw it small with `LINEAR`, copy *that* back and blow it up with `NEAREST`. Runs before the HUD, so the victim loses their aim but keeps their health bar |
| **Torchlight** | `BlockEnchantLight` + `TorchlightUpkeep`. An invisible, replaceable, collision-free light block kept at head height, moved every 5 ticks and cleaned up on logout — plus a random-tick self-destruct as a backstop for orphans |

**Four of the five need no packets at all.** A client already holds its own
player's inventory NBT and its own loaded chunks, so Tracker, Prospector and Reach
read what they need locally. Only Jammer crosses the network, because its effect
happens on somebody else's screen.

Two respecs were applied where 1.7.10 could not express the original idea:
**Rage** grants Strength rather than swing speed, and **Cripple** applies
Slowness plus a damage debuff. **Ferocious** was merged into **Momentum**.

**Feasibility** is effort *after* the framework exists, and is my honest estimate,
not a promise:

- **Easy** — a handful of lines in an event handler
- **Med** — real logic, state tracking, or entity manipulation
- **Hard** — rendering, packets to other clients, or fighting another mod
- **Blocked** — needs a 1.7.10 mechanic that does not exist; must be redefined

Counts: **41 approved** from the original menu, **43 proposed** by you, minus
collisions and merges below.

---

## Settled decisions

| Question | Decision |
|---|---|
| **Reach** / **Demon Forged** duplicate TragicMC effects | **Keep both.** They duplicate TragicMC's *effects*, never its IDs — we allocate our own, so there is no crash risk. Players will see two similarly-named enchants; that was accepted |
| **Rage** (no attack speed in 1.7.10) | Temporary **Strength** buff on proc |
| **Cripple** (no attack speed in 1.7.10) | **Slowness + reduced attack damage** via attribute modifier |
| **Ferocious** (duplicates Momentum) | **Merged into Momentum** |
| **Multi Strike** | **In.** Framework built around a central dispatcher from the start |
| **Turtle** | Capped at **80%** total reduction |
| **Killing Blow** | **Sets target health to 0**, bypassing damage math and boss damage caps |
| **Accelerant** | **Amplifies and extends** all negative effects on the target |
| **Fortune V** | **Rare.** **Fortune X** added as **Epic** |
| **#39 Fallout Ward** | **Cut** — radiation is being disabled in the pack |
| **#18 Kiln** | **Cut** — TragicMC's Combustion likely covers it |
| **Jammer** | **In**, and accepted as expensive. Every hit downsamples the victim's screen |

Still open: **#43 needs a name** (it is no longer an EMC siphon), and **Sacrifice**
and **Tracker** need building from scratch since totems (1.11) and the glowing
effect (1.9) postdate 1.7.10 — both confirmed doable, just not free.

---

## Approved — original menu

### Combat
| # | Name | Effect | Tier | Feas. |
|---|---|---|---|---|
| 1 | Executioner | Damage scales with target's missing health | Rare | Easy |
| 2 | Colossus | Damage scales with target's max health — **probability-based proc, not flat** | Epic | Easy |
| 3 | Rupture | Stacking bleed over time | Rare | Med |
| 4 | Momentum | Consecutive hits on same target ramp up (absorbs Ferocious) | Uncommon | Med |
| 5 | Riposte | Next hit within 3s of being hit is amplified | **Uncommon** | Med |
| 6 | Arc | Chance to chain damage to nearby mobs | Epic | Med |
| 7 | Disarm | Chance to knock a mob's weapon out | Uncommon | Med |
| 8 | Decapitate | Chance at mob head drop | Uncommon | Easy |
| 9 | Frostbite | Slow/freeze on hit | **Rare** | Easy |
| 10 | Blind | Blindness on hit | **Rare** | Easy |
| 11 | Feast | Heal on kill | Rare | Easy |
| 12 | Piercing | Ignore % of target armor — **bows/ranged only** | Rare | Med |
| 13 | Sunder | Temporarily strip target armor | Rare | Med |
| 14 | Berserk | Your damage rises as your health falls | Epic | Easy |
| 15 | Assassinate | Bonus damage vs unaware targets / from sneak | Rare | Med |

**On #10 Blind:** your instinct was right. `Potion.blindness` exists and applying
it is trivial, but mob AI in 1.7.10 does not meaningfully use vision — blinding a
zombie barely changes its behaviour. Against **players** it is devastating. So
this is effectively a PvP enchant. Rare is right; consider making it player-only.

### Bows
| # | Name | Effect | Tier | Feas. |
|---|---|---|---|---|
| 16 | Penetrating | Arrows pass through targets | Rare | Med |
| 17 | Ricochet | Arrows bounce to a second target | Epic | Med |

### Tools
| # | Name | Effect | Tier | Feas. |
|---|---|---|---|---|
| 19 | Excavate | Break a connected vein | **Uncommon** | Med |
| 20 | Timber | Fell a whole tree | Uncommon | Med |
| 21 | Magnetize | Drops go to inventory | Common | Easy |
| 22 | Tunneler | Area mining — **radius grows with level** | Epic | Med |
| 23 | Prospector | Reports nearby valuables — **non-invasive HUD readout** | Rare | Med |
| 24 | Sieve | Bonus drops from stone/dirt | **Common** | Easy |
| 25 | **Mending** | Repair durability from XP (renamed) | Epic | Med |
| 26 | Bountiful | Fortune applies to non-ore blocks | **Uncommon** | Easy |
| 27 | Torchlight | **Pickaxe emits light like a held torch; brightness scales with level** | Uncommon | Med |

### Armor
| # | Name | Effect | Tier | Feas. |
|---|---|---|---|---|
| 28 | Bulwark | Damage reduction grows as health falls | Rare | Easy |
| 29 | Nightsight | Night vision in darkness | Common | Easy |
| 30 | Cleansing | **Chance to clear a negative effect when hit** | Rare | Easy |
| 31 | Stonehide | Cuts fall and explosion damage | Uncommon | Easy |
| 32 | Rebound | Negates knockback, chance to reflect | Uncommon | Easy |
| 33 | Soulbound | See expanded spec below | **Legendary** | Hard |
| 34 | Swiftswim | Swim speed (no Depth Strider in 1.7.10) | Uncommon | Easy |
| 35 | Frostpath | Freeze water underfoot (no Frost Walker in 1.7.10) | Rare | Med |
| 36 | Vigor | Bonus max health | Epic | Easy |
| 37 | Regrowth | Regen out of combat | Rare | Easy |
| 38 | Camouflage | Reduced mob aggro range | Rare | Med |

**#33 Soulbound, expanded per your spec** — three separate behaviours:
1. Item is kept through death — **and removed from the pool Gravestones collects.**
   Requires running at a higher event priority than Gravestones and pulling the
   stack before it sees it. This is the fiddly part and the reason it's Hard.
2. Never dropped from an inventory on death.
3. If it would ever despawn or burn, it returns to the owner instead.
   `ItemExpireEvent` and `ItemTossEvent` both exist in 1.7.10, so the despawn case
   is clean; lava/fire needs a check on the `EntityItem`.

Legendary is right — it's three systems, not one.

### Pack-specific
| # | Name | Effect | Tier | Feas. |
|---|---|---|---|---|
| 40 | Beast Bane | Bonus damage vs Lycanites families | Rare | Med |
| 41 | Infernal Hunter | Bonus damage/drops vs Infernal Mobs | Epic | Med |
| 42 | Angelic Ward | Resists Weeping Angel teleports | Rare | Med |
| 43 | **(rename needed)** | **Chance to drop a random ore on any ore break** | Epic | Easy |

**#43** — your redefinition drops the ProjectE dependency entirely, which makes it
simpler and removes a soft-dep. It's no longer "Transmuter"; wants a new name.

---

## Approved — your proposals

### Weapons
| Name | Effect | Tier | Feas. |
|---|---|---|---|
| Poisonous | Chance of vanilla poison | Uncommon | Easy |
| Venomous | Stronger Poisonous | Rare | Easy |
| Suplex | Throw mob into the air for fall damage | Rare | Easy |
| Killing Blow | Sub-1% chance of lethal damage | Epic | Easy |
| Crushing Blow | Cooldown: crouch+hit for big damage | Epic | Med |
| **Get Off Me** | Cooldown: hold right-click + attack for massive knockback and launch | Epic | Med |
| Accelerant | Negative effects on target tick faster | Rare | Med |
| Rally | Battle music in combat | Common | Easy |
| Necromancer | Chance to summon temporary zombies/skeletons | Rare | Med |
| Alpha | Chance to summon temporary wolves | Rare | Med |
| Bastion | Chance to summon temporary iron golems | Epic | Med |
| Excalibur | Permanent Strength/Resistance/Speed + bonus base damage | Legendary | Med |
| Lich | Temporary bonus max health on kill | Epic | Easy |
| Daze | Chance to spin target 180° | Uncommon | Easy |
| Roulette | 50/50 half or double damage | Uncommon | Easy |
| Cultist | Chance to take weapon damage yourself for double on target | Rare | Easy |
| Multi Strike | All custom enchant procs fire twice | Legendary | **See below** |

**Accelerant** needs its mechanic pinned down — potion effects in 1.7.10 have a
duration and an amplifier but no tick-rate. "Faster" can mean either *higher
amplifier* (poison hurts harder/more often) or *shorter duration* (which is worse
for you, not better). I'd read your intent as the former. Confirm.

### Bows
| Name | Effect | Tier | Feas. |
|---|---|---|---|
| Instant Transmission | Teleport to where your arrow lands | Epic | Med |
| Soul Entwine | Swap positions with the target you hit | Rare | Easy |
| Bola | Inflict slowness | Rare | Easy |
| Homing | Arrows track targets | Legendary | Med |

### Tools
| Name | Effect | Tier | Feas. |
|---|---|---|---|
| Haste | Permanent Haste | Epic | Easy |
| Eco-Friendly | Partial resources back when the tool breaks | Common | Easy |
| Bold | Doubles Fortune's effect | Epic | Easy |
| Fortune V | Higher Fortune; mutually exclusive with vanilla Fortune | — | Med |
| Old Reliable | Mining XP rises as durability falls | Uncommon | Easy |

**Fortune V** — `canApplyTogether(Enchantment)` handles the mutual exclusion
natively, so "can't add vanilla Fortune if this is present" is one method. The
"replaces vanilla Fortune if already on the item" half is custom logic in our
apply step, which is also fine. Needs a tier.

### Armor
| Name | Effect | Tier | Feas. |
|---|---|---|---|
| Turtle | Damage reduction per piece, no weapon held — **see balance note** | Legendary | Easy |
| Frog | Permanent jump boost | Rare | Easy |
| Deft | Permanent speed | Epic | Easy |
| Affliction | Chance to inflict every negative effect on attackers | Legendary | Easy |
| Reflect | Knockback attackers, no damage | Epic | Easy |
| Tank | Permanent slowness for permanent resistance | Rare | Easy |
| Cockroach | Resistance at half a heart or lower | Epic | Easy |

### PvP
| Name | Effect | Tier | Feas. |
|---|---|---|---|
| Polarize | 0.01% stacking chance to strip all enchants off attacker's gear | Legendary | Med |
| Trade | Chance to swap held items with your enemy | Rare | Easy |
| Jammer | Consecutive hits degrade the enemy's screen resolution | Legendary | **Hard** |

---

## The Multi Strike consequence

Multi Strike — "proc all custom enchants twice" — only works if every enchant's
effect is invoked through a single dispatcher rather than each one hooking events
directly. That is a better architecture anyway: it gives one place for proc
chance, cooldowns, level scaling and the Multi Strike multiplier.

But it has to be built that way from the first enchant. Retrofitting 80 enchants
that each registered their own handler is a rewrite.

So: **decide now whether Multi Strike is in.** If it is, the framework changes
shape before enchant #1 gets written. It costs very little today and a great deal
later.
