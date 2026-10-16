# The combat census server

How to build a headless server that can run `/qfcensus combat` against the pack's
real mobs, and the three things about this pack that stop it working out of the
box.

This is the combat equivalent of the ore survey's Step 2, and it uses the same
script — [`tools/survey/build_server.py`](../../tools/survey/build_server.py) —
for the same reason: a server maintained by hand drifts from the pack, and every
number it produces then describes a mod set nobody plays.

---

## Why a server rather than the client instance

The client instance has the mods but cannot be driven without a person clicking.
`/qfcensus combat` needs to run for an hour and be told what to fight, so it runs
on a dedicated server assembled from that same instance. Nothing about the
measurement is client-side: the dispatcher, the mobs and the damage pipeline are
all server code.

## Building it

```bash
# 1. Forge's installer produces the vanilla server jar and a maven libraries/
#    tree. The client's bin/lib is a flat directory and will not substitute.
V=1.7.10-10.13.4.1558-1.7.10
curl -O "https://maven.minecraftforge.net/net/minecraftforge/forge/$V/forge-$V-installer.jar"
java -jar "forge-$V-installer.jar" --installServer

# 2. Assemble from the live instance. Keep the path short -- see the ore
#    survey's note about WinError 206.
py -3.10 tools/survey/build_server.py \
    --instance "$APPDATA/.crazycraft4" \
    --out      /c/qfs/combat \
    --forge    forge-$V-universal.jar \
    --vanilla  minecraft_server.1.7.10.jar \
    --libraries libraries \
    --level combat --port 25599

# 3. The census measures the mod you are testing, so install your build.
cp mods/qf-content/build/libs/QuestForgeContent-1.0.0.jar /c/qfs/combat/mods/

# 4. Normal difficulty. Mob damage is difficulty-scaled, and the default is Easy.
echo "difficulty=2" >> /c/qfs/combat/server.properties
```

Run it with `-Dfml.queryResult=confirm`, or FML stops at a console prompt the
first time the mod set changes and waits forever.

## The removal rule

The ore survey removes a mod only if it *cannot place a block*. The combat census
needs its own version of that rule, and it is stricter:

> A mod is removed only if it cannot affect a fight — it provides no mob, no
> weapon, no armour and no damage-modifying effect. Anything that spawns
> something, scales something, or changes a damage number stays in, whatever it
> costs to boot.

`build_server.py` already drops ten client-only mods (renderers, HUDs,
cosmetics). One more has to go for a combat run:

| Mod | Why |
|---|---|
| `Saintscore.jar` | NullPointerException in `mod_Saintscore.preInit` on a dedicated server, which leaves FML in ERRORED and the world never loads. It is a content loader for the SaintsPack cosmetic/gun pack, declares no dependents, and provides no mob or damage effect, so it passes the rule above. |

Everything else in the pack stays, including Battlegear2, The Legends Mod,
Lycanites and Twilight Forest.

## Three things that surprise you

### 1. Something cancels the probe's attacks

`EntityPlayer.attackTargetEntityWithCurrentItem` opens by posting
`AttackEntityEvent`, and in this pack
`com.tihyo.legends.handlers.LegendsCommonEventHandler.onAttack` cancels it for
the census probe — The Legends Mod takes over player melee and has no data for a
player that never logged in. Every swing then returns having done nothing.

This is exactly the failure the calibration exists to catch, and originally it
did not: the first pack run reported `OK` while `diamond sword swing lands
0.0000`, because the check tested that the mob *could* be hurt and that the probe
*could* be hurt but never that a swing worked. It does now, and it names the gate
that stopped it — the event, the item's `onLeftClickEntity`, `canAttackWithItem`
or `hitByEntity` — plus every listener registered on the event, so the mod
responsible can be named without bisecting a hundred jars.

`CensusProbe.swing` falls back to delivering the same damage as
`causePlayerDamage` directly. `LivingHurtEvent` still fires, so every custom
enchantment, every armour calculation and every other mod's damage modifier still
applies; what is skipped is knockback, crits and item wear, none of which a
stationary probe produces anyway. **Which path a run used is recorded in the TSV
header**, because it is a fact about the measurement rather than about the
enchantments.

### 2. Mobs are not the mobs in the jar

`config/MobProperties.json` applies a global modifier to everything that spawns:

| Attribute | Modifier |
|---|---|
| `generic.maxHealth` | `× (1 + U(3.0, 9.0))` |
| `generic.attackDamage` | `× (1 + U(0.5, 2.0))` |

So a "20 health" zombie has 80–200, and the spread is per-spawn. That is the
pack as played, and it is also a source of variance the census cannot remove —
every cell fights freshly rolled mobs. Read marginal percentages, which are
paired against a control fighting the same distribution; do not read a single
cell's absolute damage as precise.

### 3. Vanilla numbers do not hold

The calibration reports a zombie dealing **2.25** to an unarmoured player on
Normal where vanilla deals 3.0, and player-source damage landing well above the
raw amount passed in. Something in the pack scales both directions. This is not a
census bug — it is the reason a census exists, and it is why
`ENCHANT-GROUND-TRUTH.md`'s two "confirmed by measurement" vanilla facts should
be re-confirmed against the pack rather than against a dev client.

## Running it

```
/qfcensus find <text>            # registry names for targets and weapons
/qfcensus combat Zombie TwilightForest.Hydra demonmobs.rahovart
/qfcensus combat chocolateQuest:swordMonking Zombie   # a colon means a weapon
/qfcensus status
```

An argument containing a colon is an item registry name and becomes the weapon;
everything else is a target entity. That matters on a server, which has no hands
— without it every headless run silently measures a diamond sword.

Budget roughly **20–30 seconds per cell**: 77 cells for one target, 231 for
three, so about an hour and a half. It runs in real game ticks on purpose.
