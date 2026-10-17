# Combat-census singles: anomaly diagnosis (2026-10-17)

A read-only diagnosis of the suspicious cells in the singles campaign
(`C:\qfs\campaign\*-singles\`, 28 jobs, all finished). Nothing here was re-run.
Every claim below comes from the job TSVs and `census.log`s, the census source as
of `1e8bb5b`, the qf-content enchant source, and decompiled boss classes taken from
the live instance's jars (`orespawn.zip`, `TragicMC.jar`,
`HardcoreEnderExpansionMCv.jar`, `Witchery.jar`, `KillerPacman.jar`, Lycanites).
Line numbers for decompiled classes are Fernflower output lines and only locate
the code. For the census and enchant code they are real source lines.

The report regenerated from all 28 TSVs is identical to the one under review.

## Summary

| # | Boss / cells | Cause | Census-only or real | Data verdict | Blocks pairs? |
|---|---|---|---|---|---|
| 1a | Kitsune | Immune to everything except reflected fireballs (`kitsunakumaFireballExempt=true`). Enchants that add flat damage leak through the zeroed hit. | Immunity is real. The leak is a **real qf-content bug**. | Offence invalid; defence OK | Yes: drop Kitsune from offensive phases |
| 1b | Enyvil | Its main body refuses every hit whose attacker is a player. Players have to strike an `EntityPart`, and the probe strikes the main entity. The census also skips `onSpawnWithEgg`, so Enyvil has no Dark Crystal. | **Census-only** | Melee invalid; bow and defence partly | Yes: fix the probe, then re-run |
| 2 | EnderDemon | A ticking-entity NPE on the probe's null connection makes Forge (`removeErroringEntities=true`) delete the boss. The census counts a removal as a kill and books its remaining health as damage. | **Census-only** | Offence invalid; defence meaningless | Yes |
| 3 | Apis | 160-tick reflect phase / 160-tick vulnerable phase. Bands are also 160 ticks, so whole bands land on the reflect phase. | Phase is real; the noise is **census-only** | Invalid; re-run | Yes |
| 4a | Rupture/Venomous/Poisonous vs Mobzilla, Kraken, Basilisk, Emperor Scorpion | OreSpawn's private `hurt_timer` gate (20/30 ticks). Each DoT tick re-arms it and the next melee swings are refused. `TickedEffects` clears only vanilla's i-frames. | **Real gameplay bug** | Real for current code. Re-run those cells after the fix | Yes, for pairs containing a DoT on those 4 bosses |
| 4b | Bastion vs Baba Yaga, monking, Huntsman, Lich, Mantis | Iron golem hits take the boss's vanilla i-frames. A player swing inside the window lands only its raw excess over the golem hit, and WeaponScaler (x1-4) and the qf multipliers scale only that excess. Baba Yaga's 15-raw cap makes it worse. | **Real** | Trustworthy as gameplay | No |
| 4c | Feast vs Apis | Feast only heals on kill. -57% is Apis noise. | Artifact (of #3) | Discard with Apis | No |
| 5a | OreSpawn "+58.3%" columns | Not copies. OreSpawn weapons skip WeaponScaler, so every hit is deterministic and Excalibur is an exact x2.3976 on each one. | Real | Trustworthy | No |
| 5b | Mobzilla ~0 for every damage enchant | Godzilla caps each hit at 750 raw, and the T4 Royal sword already swings for 751. | **Real balance problem** | Trustworthy | No (but no damage enchant can show anything on Mobzilla) |
| 5c | DeathReaper (nearly everything +30..60%), Berserk generally | The probe's health is not held: boss AI melee wears it down between scheduled hits. Skultar puts its full armour on (x3) while its target is at 25% health or less. | **Census-only** | DeathReaper invalid; Berserk/Cultist/Feast/Mending partly | Yes |
| 5d | Lord of Torment (TTK) | At or below 50% health in the Overworld it teleports the fight to the Torment dimension and `setDead()`s. Bands 50/25/10 then read as instant kills. | Mechanic real; TTK **census artifact** | Bands 1-2 valid; TTK invalid. Fixable in the report | Partly |
| 5e | Rahovart | `damageMax = 25` per hit, so every multiplier reads 0. | Real | Trustworthy | No |

Two cross-cutting census faults explain #2, #5c and #5d, and they also distort
cells nobody flagged:

- **A target removed while alive is counted as killed.** `CombatCensus.advanceOffense`
  lines 1335-1348 treat `mob.isDead` as a kill. `accumulateDamage` (1812) books the
  target's whole remaining health as damage dealt (`now = mob.isDead ? 0 : health`).
- **The wielder's health is not controlled.** `hp_fraction=1.0` is set once per band
  (line 1326). Damage the boss's own AI deals to the probe is never undone, apart
  from the clamp at 1 HP (line 1431).

---

## 1a. TragicMC.Kitsune: "never", 45 of 53 melee cells degenerate

**Cause.** `EntityKitsune.attackEntityFrom` (decompiled lines 314-343):

```java
if (source.getEntity() instanceof EntityKurayami) return super.attackEntityFrom(src, dmg * 0.145F);
else if (!TragicConfig.kitsunakumaFireballExempt) return super.attackEntityFrom(src, dmg);
else if (!src.getDamageType().equals("fireball") && !justiceWeapon)
    return super.attackEntityFrom(src, 0.0F);          // <- every probe swing
else { ... dmg = 10 or 20; teleportToEntity(attacker); return super(...); }
```

`C:\qfs\c1\config\TragicMC.cfg:1090` has `B:kitsunakumaFireballExempt=true`, the same
as the live `.crazycraft4` config (diffed: identical). Every swing goes into vanilla's
pipeline at 0 damage. It still sets 20 ticks of i-frames, which matches the log:
`Kitsune stopped taking hits at cell tick 50: health 410.6398/410.6398, hurtResist 20`,
and every control's first swing reads `dealt 0.0000`. This is not teleporting, a
broken leash or healing. The boss is immune by design.

**Would a real player be stuck too?** Yes, with The Titan or any other weapon. A real
player kills Kitsune by knocking its fireballs back into it (10 or 20 per hit, then
100 ticks of hurt time), or with the Sword/Bow of Justice. Weapon enchants have no
legitimate effect on that fight.

**But 8 melee cells did deal damage, and that is a real qf-content bug.** The 8
non-degenerate cells are the ones whose enchants add **flat** damage in
`LivingHurtEvent`: Excalibur (`WeaponEnchants2.java:419`, `ctx.damage += 4.0F`),
Momentum (`CombatEnchants.java:350`), Riposte (`CombatEnchants.java:376`), Colossus
(`CombatEnchants.java:49`, floored at `MIN_CAP`). Kitsune hands vanilla a 0-damage
hit, `EnchantEventBridge.onLivingHurt` dispatches ATTACK on it anyway, and the flat
add turns it into real damage. Excalibur's row shows `hit=80 dmg=320` (exactly 4 per
hit). Momentum deals 798. **A player with these enchants can melee a boss the pack
configured as fireball-only.**

**Fixes.**
- qf-content (real bug): `EnchantEventBridge.java`, in `onLivingHurt` straight after the
  Cripple multiplier (after line 55), add
  `if (event.ammount <= 0F) { applyArmour(event, attacker); return; }`.
  A hit the target has already zeroed keeps no on-hit enchantment. That covers the
  arrow path (lines 59-71) and the melee path (lines 79-87). The same leak also
  lets flat adds past caps applied *before* the event (Lord of Torment's 5, Baba
  Yaga's 15, EnderDemon's 5). That case is a design question, not this bug, and is
  noted under 5d.
- Census: nothing to fix in the probe. Remove Kitsune from the MELEE and BOW modes of
  every later phase (`modes=DEFENSE` in its campaign job) and mark it "immune by design"
  in `docs/survey/combat.md`. If the pack *wants* a melee Kitsune, the lever is
  `kitsunakumaFireballExempt=false`, which is a design decision.

**Verdict.** Melee and bow: **discard**. Bow controls trickle 1.25 dps through a route
that was not traced, and three of the five controls read "never". Defence (11 damage
per 60 hits): **trustworthy**.

## 1b. TragicMC.Enyvil: "never", 53 of 53 melee cells degenerate

**Cause.** `EntityEnyvil.attackEntityFrom` (decompiled line 738):

```java
return src.getEntity() != null && !(src.getEntity() instanceof EntityPlayer)
       ? attackEntityFromPart(getDefaultPart(), src, dmg) : false;
```

The body refuses every player-sourced hit outright, before the vanilla pipeline
runs, so no LivingHurtEvent fires and nothing leaks. Players are meant to strike its
`EntityPart`s. `EntityPart.attackEntityFrom` hands the hit to
`main.attackEntityFromPart(part, ...)` (EntityPart.java:32), which gives the eye full
damage and every other part `dmg/6 + 1` (lines 758-767). Damage is halved again while
Enyvil has no Dark Crystal (line 755). The census probe swings at the main entity.
`CensusProbe.swing` (lines 363-388) calls
`target.attackEntityFrom(causePlayerDamage(probe), ...)` in this pack, because Legends
cancels `AttackEntityEvent` and the census falls back to that direct path. Every
first swing logs `dealt 0.0000`.

A real player hits the parts. `WorldServer.onEntityAdded` registers every
`getParts()` entity id, so a client's click resolves to the part. Arrows collide with
parts too, which is why the Enyvil **bow** cells do measure something (controls 23-62
damage per cell, ±32%).

**Second census fault.** The census spawns bosses with `ctor.newInstance(world)` +
`spawnEntityInWorld` (`CombatCensus.java:2026-2038`, sampling at 1078-1083) and never
calls `onSpawnWithEgg(null)`. Natural spawns, spawn eggs and summoning items all call
it. Enyvil builds its Dark Crystal there (`func_110161_a`, line 281-286). With no
crystal and `enyvilDarkCrystals=true`, every hit is halved and the laser and the other
crystal abilities are off. DeathReaper (`isBomb`/reaper type) and Polaris (daytime)
also initialise there.

**Real player?** Yes, they can kill it. The bow data even suggests a slow fight.

**Fixes (census).**
- `CensusProbe.swing`, before line 386: resolve the hitbox the way a click does.
  If `target.getParts()` is non-empty, deliver the hit to a part:
  `Entity hitbox = partFor(target); hitbox.attackEntityFrom(DamageSource.causePlayerDamage(probe), base + bonus);`.
  `partFor` takes a census option `part=<name>` (default: the part whose bounding
  box is nearest the probe's eye) and logs the chosen part once per cell. For Enyvil
  run `part=enyvilEye`. The eye is the intended weak point, and a shell hit is
  `dmg/6+1`, about 6x less. Keep `swing`'s return value as the health lost on the
  main entity.
- `CombatCensus.spawnOne` (after line 2035) and `startSampling` (after 1082): when the
  mob is an `EntityLiving`, call `((EntityLiving) mob).onSpawnWithEgg(null)` before
  `spawnEntityInWorld`, as natural spawning does.
- qf-content (real, secondary, non-blocking): `TickedEffects.hurtThroughInvulnerability`
  (`TickedEffects.java:115`) calls `victim.attackEntityFrom` on the main entity, so
  Rupture's bleed and Venom are refused by Enyvil, as Arc's chains are by any
  multipart boss. When that call returns false and `victim.getParts()` is non-empty,
  retry on the part returned by `getDefaultPart()` (found by reflection), falling
  back to `parts[0]`.

**Verdict.** Melee: **re-run**. Bow and defence: **partly trustworthy**. Every Enyvil
cell fought a crystal-less, half-damage Enyvil with its abilities off, so re-run
those modes too once `onSpawnWithEgg` is in.

## 2. HardcoreEnderExpansion.EnderDemon: control TTK 1 s, every enchant +0.0%

**What the data says.** Every melee cell (controls included) has `kills=80` for 80
swings, and every band's dps is exactly two band-healths per second
(`5531.48 4148.61 2765.74 1382.87 553.15` = 2765.74 x {1, .75, .5, .25, .1} x 2/s). In
other words every swing "kills". Even 2-damage bow arrows "kill" 39 of 40 times.
The boss cannot actually take that much. `EntityBossEnderDemon.attackEntityFrom`
(decompiled line 219-220) caps every non-void hit at `min(5, amount * 0.45)` before
the vanilla pipeline, and the logged first swings deal 11.8-18.3 (5 x WeaponScaler's
U(1,4)).

**Cause.** After the first hit, `lastAttacker` is the probe (line 222-224 stores any
`EntityPlayerMP`, which `FakePlayer` is). On the boss's next tick,
`updateEntityActionState` (line 69) evaluates
`lastAttacker.playerNetServerHandler.netManager.isChannelOpen()`. The probe's
`playerNetServerHandler` is null (`CensusProbe.ProbePlayer` only works around the
null connection for potion, mount and teleport calls), so the boss's tick throws a
NullPointerException. All three configs (c1, c2, the live instance) have
`forge.cfg: B:removeErroringEntities=true`, so instead of crashing, Forge logs the
report and removes the boss. The census then:

- counts the removal as a kill (`advanceOffense`, line 1337:
  `if (mob == null || !mob.isDead && mob.getHealth() > 0F) continue;` treats `isDead`
  with health left as a death);
- books the boss's whole remaining health as damage (`accumulateDamage`, line 1812:
  `double now = mob.isDead ? 0.0D : mob.getHealth();`).

So each band "deals" its full health per swing. The node's fml-server log for that
run (05:24-06:31 on c1) has already rotated out, so the ticking-entity reports
themselves are gone. The code path, the config and the impossible damage line up
without them.

**Real player?** No. A real player's channel is open. The real fight is a 5-raw cap
per hit (then WeaponScaler and qf multipliers in LivingHurtEvent), +1 HP every 10
ticks of regen (line 75-76), and lightning on the last attacker: roughly 2 minutes
with The Titan, not 1 second. One real side effect is worth knowing: any FakePlayer
from another mod (automated sword, turtle, deployer) that hits the EnderDemon
deletes it the same way.

**Fixes (census, both needed).**
- Stop counting removals as kills. `CombatCensus.advanceOffense`, lines 1335-1348:
  record a kill only when `mob.getHealth() <= 0F || mob.deathTime > 0`. For
  `mob.isDead && mob.getHealth() > 0F`, increment a new `Result.removedAlive`, append
  `[target removed while alive N time(s)]` to the note, and still respawn. In
  `accumulateDamage` (line 1812) use `now = mob.isDead && mob.getHealth() > 0F ?
  lastHealth[i] : (mob.isDead ? 0 : mob.getHealth())`, so a removal deals nothing.
  In `tools/balance/qfcampaign.py:degenerate()` (lines 62-65) also exclude notes
  containing `removed while alive`.
- Give the probe a connection that answers "closed". In
  `CensusProbe.ProbePlayer`'s constructor (line 52-55), give it a
  `NetHandlerPlayServer` over a `NetworkManager(false)` with no channel.
  `isChannelOpen()` then returns false, and the EnderDemon drops `lastAttacker` as it
  would for a logged-off player. *Caution:* every `playerNetServerHandler != null`
  branch in `ProbePlayer` (lines 105-171) then takes the `super` path and queues
  packets on a closed manager. Change those guards to test a probe-local
  `hasConnection` flag instead. The narrower alternative is to clear the boss's
  `lastAttacker` field by reflection each tick in `keepPinned`, like `dropShields`.
  It fixes this boss only and changes its lightning targeting, so prefer the
  connection.

**Verdict.** Melee and bow: **invalid; re-run**. Defence: the EnderDemon has no melee
(`attackDamage NaN`, first defensive hit `20.0 -> 20.0`) and its lightning targets
`lastAttacker`, so the armour table's "immune" means "never attacked". Drop it from
the armour table.

## 3. TragicMC.Apis: noise ±92%, control 476 s

**What the data says.** Controls land 48 or 33 of 80 swings, and in every control
bands 1, 3 and 5 deal about 1 dps while bands 2 and 4 deal 13-18:

```
(control) hit=48 bands=[1.58 15.41 1.17 13.53 14.59]
(control) hit=33 bands=[0.57 14.38 1.02 14.59 1.51]
```

The log's `stopped taking hits` lines fall at cell ticks 60, 380 and 700, which is
inside bands 1, 3 and 5, with `hurtResist 0`. So these are not i-frames.

**Cause.** `EntityApis` reflects. While `isReflecting()` it returns `true` without
taking the hit and throws `dmg/2 + 1` back at the attacker (decompiled lines
358-369). Reflection lasts 160 ticks (`setReflectionTicks(160)`, line 352). Then
`reflectionBuffer = 160` vulnerable ticks (lines 225, 239-240), and it restarts on
the next `ticksExisted % 20 == 0` once it has a target. The period is 320-339 ticks
and the duty cycle is 50%. The census's `BAND_TICKS = 160` (`CombatCensus.java:150`)
exactly matches the half-period. The cycle starts at the first hit, just after
warm-up, so whether a given band sits wholly in a reflect window, wholly in a
vulnerable one or straddles both is a phase lottery. A band near 0 dps blows up its
term of the TTK integral (`ttkSeconds`, line 367-375). Hence 293-786 s controls and
±92%. Melee also takes `x0.425` (line 386), which is real.

**Real player?** The phase is real. A player waits out the 8-second reflect, or eats
half their damage back. The real fight is roughly 2x the vulnerable-phase TTK. The
noise is the census's own.

**Fix (census).** Hold the reflection down the way the Lich's shields are held
(`dropShields`, line 1644), and measure the vulnerable phase. In `keepPinned`
(line 1475) add `dropReflection(mob)`: if the class declares a private
`setReflectionTicks(int)`, invoke it with 0 and set the `reflectionBuffer` int field
to 160 every tick, and note `[reflection held down: the vulnerable phase is
measured]`. Report Apis's TTK as 2x the measured figure. (The alternative,
`BAND_TICKS = 320` for Apis, still leaves ±3-6% phase slop because the period
varies by up to 19 ticks, and it doubles the job's length.)

**Verdict.** **Invalid; re-run.** Every Apis cell is a phase sample, including blind
+79.7%, cultist -70.4%, feast -57% and reach -29.7%.

## 4. DoT enchants and Bastion slowing kills

### 4a. Rupture / Venomous (and Poisonous) vs Mobzilla, Kraken, Basilisk, Emperor Scorpion

**What the data says.** Hits landed collapse exactly where the speed-up turns
negative:

| Boss | control hits / 80 | rupture:3 | venomous:3 | poisonous:3 |
|---|---:|---:|---:|---:|
| Mobzilla | 40 | **9** (-140%) | 29 (-10%) | 35 (-0.7%) |
| The Kraken | 27 | 17 (-52%) | 17 (-53%) | 24 (-7%) |
| Basilisk | 27 | 15 (-43%) | 19 (-29%) | 25 (-4%) |
| Emperor Scorpion | 27 | 20 (-21%) | 20 (-18%) | 27 (0%) |
| Mantis (control case) | 80 | 80 (+11%) | 80 (+12%) | 80 (+9%) |
| Mothra (control case) | 80 | 80 (+10%) | 80 (+11%) | 80 (+8%) |

**Cause.** Four of these OreSpawn bosses carry their own hit gate, a private
`int hurt_timer` checked before vanilla's damage path:

- `Godzilla.attackEntityFrom` (decompiled 717-746): `if (hurt_timer > 0) return false;`,
  then caps the hit at 750, calls `super`, and sets `hurt_timer = 20` whether or not
  `super` landed. It is decremented once a tick in `updateAITasks` (lines 268-270).
- `Kraken` (1261-1264) and `Basilisk` (373-376) do `if (hurt_timer > 0) return false;
  hurt_timer = 30;` before `super`. `EmperorScorpion` (412-417) sets 30 after `super`.
- Mantis and Mothra have no such gate (their `attackEntityFrom` calls `super`
  directly). That is why the same enchants are positive on them.

This gate is also why the controls land 40 of 80 swings on Mobzilla (one per 20
ticks) and 27 of 80 on the others (one per 30).

`TickedEffects.hurtThroughInvulnerability` (`TickedEffects.java:102-123`) was written
to let a DoT tick through *vanilla's* i-frames without costing the wielder's next
swing. It zeroes `hurtResistantTime` for the call and restores it afterwards. It
cannot see `hurt_timer`. So each bleed tick (every 20 ticks, `BLEED_INTERVAL`, line 29)
and each venom tick (every 12 ticks at poison amplifier 1, `venomInterval`,
line 211-217) that lands *re-arms the boss's gate*, and the player's next swings are
refused for 20-30 ticks. Each lost swing on Mobzilla is 120 after armour. The bleed
tick that displaced it is a few dozen. Rupture's 20-tick bleed lines up with
Godzilla's 20-tick gate almost perfectly (9 hits left of 80).

Rejected hypotheses: OreSpawn bosses do not heal from DoT sources (no heal path in
any of the four `attackEntityFrom`s). The report computes these cells correctly
(the TSV's own `marginal_ttk_est_pct` agrees: -140.3, -52.5, -43.1, -21.1).
WeaponScaler is not involved, because OreSpawn weapons are exempt
(`WeaponScaler.onDamage` skips any held item whose class name contains "orespawn").

**Real player?** **Yes, this is a qf-content balance bug.** The gate belongs to the
boss and applies to a real player's swings in exactly the same way. A player with
Rupture on Mobzilla gets most of their swings refused.

**Fix (qf-content, `TickedEffects.java:102-123`).** Treat a mod's private hurt gate the
way vanilla's is already treated: save, zero, call, restore.

```java
// next to savedInvulnerability (line 106)
java.lang.reflect.Field gate = HurtGate.of(victim.getClass());   // int "hurt_timer" on the class
                                                                  // hierarchy, cached per class, null if absent
int savedGate = 0;
try { if (gate != null) { savedGate = gate.getInt(victim); gate.setInt(victim, 0); } } catch (Exception ignored) {}
...
finally {
    ...existing restores...
    try { if (gate != null) gate.setInt(victim, savedGate); } catch (Exception ignored) {}
}
```

The DoT tick then lands, and the gate is exactly as the wielder's last real hit left
it, so melee cadence is unchanged. **Expect a large swing in the other direction.**
On Mobzilla, Rupture's per-stack bleed is 4% of a 750 hit (30/s, up to 4 stacks,
armour-bypassing), so Rupture would go from -140% to well over +50%. If that is
judged too strong, the conservative alternative is the reverse rule: skip the DoT
tick (and keep its damage banked onto the next tick) while `hurt_timer > 0`. DoT
then costs nothing and adds little against gated bosses. Choose deliberately. Either
fixes the inverted sign.

**Verdict.** The four bosses' rupture/venomous/poisonous cells and the stacks
containing them (`arc+rupture+feast`, `multistrike+rupture+accelerant`,
`venomous+poisonous+accelerant`) correctly describe *the current code*. They are not
census faults. **Re-run those cells after the fix.** Every other cell on these bosses
is trustworthy.

### 4b. Bastion vs Baba Yaga (-237%), monking (-43%), Huntsman (-24%), Lich (-14%), Mantis (-15%)

**What the data says.** Hits landed drop: Baba Yaga 19/80, monking 71, Huntsman 69,
Lich 68 (Mantis keeps 80/80 but deals 12% less). Alpha (wolves) and Necromancer
(zombies/skeletons) stay near 0.

**Cause.** Bastion (`WeaponEnchants2.java:513-528`) summons iron golems: 9% per swing
at level 3, each lasting 1,000 ticks (`SummonEnchant.onAttack`, line 475), so several
build up over a cell. A golem swings for 7-21 raw (`EntityIronGolem.attackEntityAsMob`).
A golem hit opens the boss's vanilla i-frame window and sets `lastDamage = G`. A player
swing inside that window lands only `S - G` raw (`EntityLivingBase.attackEntityFrom`).
The multipliers that make up most of a player's hit in this pack come *after* that
subtraction, in `LivingHurtEvent`: KillerPacman's `WeaponScaler`
(`amount += amount * U(0,1) * 3`, about x2.5 on average for non-OreSpawn weapons)
and qf's ATTACK dispatch. So a golem hit replaces a big multiplied player hit with a
small unmultiplied one. Baba Yaga makes it far worse: `EntityBabaYaga.attackEntityFrom`
(line 335) caps *every* hit at 15 raw before vanilla, so The Titan's 21 becomes 15,
and any golem roll of 15 or more (7 in 15) leaves the next swing nothing at all.
Hence 61 of 80 swings refused. Zombies and wolves hit for 3-4 raw, which is why
Necromancer and Alpha do not show the effect. The Mantis loss (12% with an OreSpawn
weapon, so no WeaponScaler) is not fully explained by the i-frame arithmetic. Golem
knock-up (`motionY += 0.4`) on a flier is the likely remainder. It was not isolated
from these logs.

**Real player?** **Yes.** Golems attacking the same boss take its i-frames in play as
well. Bastion is a net loss against any boss where the player's hit is mostly
post-i-frame multiplier, or capped to near a golem's hit.

**Fix (qf-content, a design choice, non-blocking).** Options, in order of how much
they change: (a) summons ignore the wielder's current target while the wielder hit
it within the last 20 ticks (`TickedEffects.keepPointedAtTheEnemy`, line 455), so
golems fight adds rather than the boss; (b) move Bastion's value from the golem's
damage to its tanking (taunt, so the boss hits the golem); (c) accept it and document
"Bastion is an add-clearing enchant". No census change.

**Verdict.** **Trustworthy** as a description of current gameplay.

### 4c. Feast -57% vs Apis

Feast (`CombatEnchants.java:59-72`) only heals the wielder on a kill. In a banded
cell nothing dies, so it can do nothing. -57% (TSV: -96%) is Apis's phase noise
(#3). Feast's other cells are all within noise. **Discard with Apis.**

## 5. Other cells that do not make sense

### 5a. The identical OreSpawn columns (Excalibur +58.3% on five bosses)

**Not copies.** The absolute numbers differ per boss (control / Excalibur damage:
Basilisk 442.8 / 1061.6, Kraken 664.2 / 1592.5, Scorpion 221.4 / 530.8, Mantis
1967 / 4718). Every ratio is 2.3976. OreSpawn weapons are exempt from WeaponScaler,
the probe always swings for the same attribute, and these bosses have no damage
randomness, so a pure per-hit multiplier gives the same speed-up everywhere
(1 - 1/2.3976 = 58.29%). The controls repeat to the hundredth, so the noise band sits
at qfcampaign's 2% floor (`_stats`, line 110). That is also why so many OreSpawn
cells read a bold small value or exactly +0.0%. **Trustworthy.**

The real outlier is how strong Excalibur is (the Strength it grants is a
multiplicative +130% on the attack attribute in 1.7.10). That is a tuning
observation, not an anomaly.

### 5b. Mobzilla: every damage enchant ~0

`Godzilla.attackEntityFrom` caps each hit at 750 raw before armour (line 723-724).
The T4 Royal Guardian sword swings for 751 (`first swing ... attack 751.0000 ...
dealt 120.0000`), so it is already over the cap, and every multiplier or flat add
applied to the raw hit is discarded. Excalibur +0.5%, Rage/Colossus within the
floor. Only hit cadence (the 20-tick gate) and DoT matter against it. **Real balance
problem**: the T4 weapon outgrows the T4 boss's cap, so no damage enchant has a
measurable effect on Mobzilla. **Trustworthy** (apart from 4a).

### 5c. DeathReaper: almost every enchant +30..60%, including ones that do nothing

**What the data says.** Band dps is bimodal, at about 85 or about 22 (a 4x step).
Controls are high in band 1 and mostly low in bands 2-4. Enchanted cells with no
plausible effect read Tracker +34%, Sunder +55%, Alpha +52%, Decapitate +30%.

**Cause.** `EntityDeathReaper.getTotalArmorValue` (decompiled 508-510) is the full
`skultarStats[5]` while `isBeingAggressive()` (demeanor > 0) and a third of it
otherwise. Demeanor is forced to 5 every tick while **its target is at 25% health or
less** (lines 274-276), or after 100 ticks unhit, or at random (line 245). The census
does not hold the probe's health. `advanceOffense` sets it once per band (line 1326).
Hits the boss's *own AI* lands on the probe (the probe becomes its revenge target
once hit) are never undone, apart from the 1-HP floor at line 1431. So within a band
the probe drifts to 1 HP, Skultar armours up, and the cell's damage drops 4x until the
next band resets the probe to 20. Enchants that change how fast the probe is worn
down (Cripple +55%, Blind +60%, Reach +54%, Riposte, Rage) shift the armour state and
read as huge gains. Noise from that hidden state does the rest. The 5 controls happen
to agree (±8.7%) and understate it.

**The same drift shows up on other bosses through Berserk.** Berserk scales with the
*wielder's* missing health (`EnchantBerserk.java:41`). In a run at `hp_fraction=1.0` it
should attribute exactly 0. It attributes 741 (Minoshroom), 824 (Naga), 525 (Lich),
368 (Snow Queen), 1,352 (Death), 522 (Huntsman), 1,531 (TimeController) and 2,114
(DeathReaper). Those are the bosses whose AI melee reaches the probe. Berserk's
+19..+49% there, and the readings for every enchant keyed to the wielder's health
(Cultist, Feast, Mending, Riposte's "hurt recently"), describe the census's drift.
They do not describe a player at the health the run claims.

**Real player?** Skultar's armour mechanic is real. A player at low HP faces the
armoured reaper. The *rate* at which the probe reaches low HP (no regen, no food, no
potions, a 1-HP floor, plus `absorbHit`'s scheduled hit on top of the AI's) is the
census's own.

**Fix (census).** Make the boss's AI damage on the probe follow the run's health
control, as `absorbHit` already does for the scheduled hit. Register a
`LivingAttackEvent` listener in the census (cancelled only while a census cell is
running) that cancels any attack on the probe whose `source.getEntity()` is a cell
target or one of its summons, *unless* a new `CombatCensus.inAbsorbHit` flag is set
(set and cleared around line 1766 `attackEntityAsMob`). Cultist's self-damage
(`BLOOD_PRICE`, `CombatEnchants.java:294`) is not from the target, so it still
accumulates as designed. Also add a TSV column `probe_hp_min` (minimum probe health
seen per cell), so drift can never hide again.

**Verdict.** DeathReaper: **invalid; re-run**. Berserk, Cultist, Feast, Mending on
Minoshroom, Naga, Lich, Snow Queen, Death, Huntsman, TimeController: **partly**. The
direction is right, the size is not. Other enchants on those bosses: trustworthy (the
drift hits control and treatment alike).

### 5d. Lord of Torment: TTK built from three instant bands

`EntityLordOfTorment.attackEntityFrom` (decompiled 189-232) caps every hit at 5 raw
(8 for demonic damage). Then, outside the Torment dimension, once health is at or
below 50% it marks every nearby player and attacker for the Torment dimension and
calls `setDead()`. The census puts it at 50%, 25% and 10% for bands 3-5. It vanishes
on the first hit, gets counted as a kill with its whole band-health as damage (the
removed-while-alive fault from #2), and respawns. Bands 3-5 read
`3982.1 1991.1 796.4` dps in every cell (2,789 "kills" in the job). The 12 bow rows
excluded as degenerate are the same thing: the boss is still respawning
(`max health 500 at cell end: pin did not hold`).

**Real player?** The real Overworld fight *ends* at 50% and continues in the Torment
dimension, which the census cannot fight.

**Fix.** Census: the removed-while-alive fix (#2) turns these bands into honest
"cannot be measured" rows. Report (no re-run needed): in `qfcampaign.py` add a
per-boss phase limit (`PHASE_END = {"witchery.lordoftorment": 0.5}`) and compute that
boss's TTK from bands 1-2 only, over 50% of its health. Those two bands are valid in
the existing TSV (20-48 dps). Note that the 5-raw cap makes flat adds (Excalibur's +4,
Momentum, Riposte) disproportionately strong here. That is the same leak as 1a, and
whether flat adds should pass a pre-event cap is a design call.

**Verdict.** Bands 1-2 **trustworthy**. TTK column and speed-ups **invalid until the
report fix**. No re-run needed.

### 5e. Rahovart: controls identical to the decimal, Rage +0.0%

Every control hit deals exactly 25.0. Lycanites' `EntityCreatureBase` clamps damage
to `damageMax` in its armour step (decompiled 1819-1822), and `EntityRahovart` sets
`damageMax = 25` (line 80), so multipliers on the raw hit (Rage, Berserk) read
exactly 0. A few enchants still get past the 25 (Excalibur 29/hit, Executioner's
bands rise to 84 dps). The route they take was not traced. **Real; trustworthy.**

### 5f. Report artifacts (qfcampaign.py)

- The **Mean** column and the rarity-outlier medians include EnderDemon's all-zero
  column, Apis's phase noise and Mobzilla's capped zeros. Until those bosses are
  re-run, exclude them in `report()` (an `INVALID = {...}` set next to
  `RARITY_ORDER`, line 32), or the means and the "2.5 sd outlier" lines move for the
  wrong reasons.
- The "Pairs: synergy" table is built from the curated 2-enchant stack
  `excalibur + multistrike` (`collect`, lines 144-145, any `stacked` row with two
  names). The pairs phase has not run yet. Label it "curated pair" until it has.
- The noise floor of 2% is correct for deterministic bosses, but it turns every
  ±2.1% OreSpawn cell bold. Consider showing "deterministic" in the noise column
  when the control MAD is 0.

---

## What blocks the pairs phase

Fix before spending pairs time:

1. **Removed-while-alive counted as kills** (`CombatCensus.java:1335-1348, 1812`), plus
   the qfcampaign exclusion. Without it, EnderDemon and Lord of Torment pairs are
   garbage, and any other boss that despawns, teleports away or errors does the same
   silently.
2. **Probe connection** (`CensusProbe.ProbePlayer`), or EnderDemon cannot be measured at all.
3. **Probe health held against boss AI hits** (LivingAttackEvent guard + `probe_hp_min`),
   or DeathReaper is noise and every pair with Berserk, Cultist, Riposte, Feast or Mending
   inherits the drift.
4. **Apis reflection held down** (`keepPinned` -> `dropReflection`).
5. **Multipart swing + `onSpawnWithEgg`** (`CensusProbe.swing`, `CombatCensus.spawnOne`),
   for Enyvil.
6. **Kitsune out of the offensive modes.**
7. **qf-content DoT vs `hurt_timer`** (`TickedEffects.java:102-123`): blocks only pairs
   containing rupture/venomous/poisonous on Mobzilla, Kraken, Basilisk and Emperor
   Scorpion. Every pair with a DoT there would otherwise re-measure a known bug.

Not blocking: the `ammount <= 0` guard in `EnchantEventBridge` (a real bug, but it only
changes Kitsune, which leaves the offensive phases anyway), Bastion's design, the
Mobzilla 750 cap, Rahovart's 25 cap, and the qfcampaign phase limit for Lord of Torment
(a report change, applicable to existing data).

Re-run after the fixes: EnderDemon, Apis, Enyvil, DeathReaper singles in full. The DoT
cells on the four gated OreSpawn bosses. The wielder-health enchants (Berserk, Cultist,
Feast, Mending, Riposte) on Minoshroom, Naga, Lich, Snow Queen, Death, Huntsman and
TimeController. Everything else in the singles stands.
