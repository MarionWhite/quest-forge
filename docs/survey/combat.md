# Measuring enchantments in combat

How to produce per-enchantment numbers that describe what actually happens in a
fight in this pack — and why the numbers that existed before this were not that.

This is the combat counterpart to [`README.md`](README.md), and it follows the
same rule the ore survey settled on: **generate the answer with the real game and
the real mod set, then read it.** No modelling, no inference.

---

## Why the previous numbers were not enough

Two documents already describe the enchantments, and neither answers "how does
this perform in a fight".

[`../reference/enchantment-ground-truth.md`](../reference/enchantment-ground-truth.md)
is the constants, transcribed from source with line numbers. It is correct and it
is not a performance figure: knowing Colossus procs at 12% and adds 2.5% of the
target's maximum health does not tell you what it is worth against a boss with a
damage cap, or how it compares to Rupture.

[`../reference/enchantment-tuning.md`](../reference/enchantment-tuning.md) has
performance conclusions, and its own status section says where they came from:

> Outstanding: … a playtest — none of this has been felt in a real fight yet.

The gap between those two was filled by `tools/balance/qfsim.py`, a Python
re-implementation of `EnchantDispatcher` and the 1.7.10 damage pipeline. It is a
careful piece of work and it has a structural problem that no amount of care
fixes: **it is a second copy of rules that live in Java.** It can be exactly right
on the day it is written and quietly wrong one commit later, and its output looks
identical either way. That is why the ground-truth file exists at all, and why
this replaces the simulation as the source of balance numbers rather than
supplementing it.

`qfsim.py` and `qfbench.py` are kept. They are useful for exploring a change
before making it. They are no longer evidence.

## What the combat census does

`/qfcensus combat` fights every combat enchantment in the running game and writes
what happened. Each measurement is a **cell**: one loadout, one mode, one target,
run for a fixed window of real game ticks.

Every cell is **paired against a control** — the identical fight with the same
weapon carrying no custom enchantment — and the reported figure is the
difference. That is what makes results comparable across a pack whose weapons run
from a wooden sword's 4 damage to the Royal Guardian's 747. "+6 damage" means
nothing on its own; "+31% over control" means the same thing at both ends.

Three quantities are recorded, because they answer different questions and
routinely disagree:

| Quantity | What it is for |
|---|---|
| `marginal_pct` | Sustained damage per second against the control. The tuning number. |
| `marginal_ttk_pct` | Time to kill a target allowed to die. The felt number, and where health-scaling effects stop resembling their DPS figure. |
| `observed_proc_pct` | How often the enchantment actually fired, counted at the point of dispatch. |

The third is a check on the **code**, not the balance. If an enchantment
documented at 24% fires at 8%, that is a bug, and tuning the effect will not fix
it. It is written to a separate file for exactly that reason.

## Running it

The dev server has only `qf-content` loaded, so its only targets are vanilla mobs
and its only weapon is a diamond sword. That is enough to prove the harness works
and useless for balancing a pack whose bosses have four thousand health. **Build
in dev, measure in the pack.**

```
/qfcensus calibrate                     # must pass first
/qfcensus combat                        # default targets
/qfcensus combat Zombie mobzilla        # or name them
/qfcensus status
/qfcensus stop
```

The weapon measured is **whatever the operator is holding**, so the pack's real
endgame gear can be measured without naming any of it in code. Hold the Royal
Guardian and run it; hold a diamond sword for a baseline.

Targets are resolved by entity registry name, case-insensitively and by suffix,
and anything not registered is skipped and recorded in the failures file. The
same command therefore works in a bare dev client and in the full pack.

Output lands in `config/`:

| File | Contents |
|---|---|
| `qfcontent-census-combat.tsv` | One row per cell. The balance sheet. |
| `qfcontent-census-combat-procs.tsv` | Observed vs declared proc rate, per enchantment per trigger. |
| `qfcontent-census-combat-failed.tsv` | Cells that could not be measured, and per-slot diagnosis of degenerate ones. |

Then:

```
python tools/balance/qfcombat.py <path-to-config-dir>
```

which ranks by marginal contribution within mode, flags proc-rate mismatches,
checks whether measured power actually increases with rarity, compares stacked
loadouts against the sum of their parts, and proposes loot weights derived from
measurement rather than intent.

**It runs in real game ticks and takes tens of minutes.** That is not a
performance bug to be optimised away — potion durations, bleed intervals,
cooldowns and invulnerability frames are all counted in ticks by the code being
measured, and running the loop faster than the world would measure a different
game.

## Calibration, and why there are two

`calibrate` has a known answer and the census refuses to run if it fails. This is
the same discipline as the mob census, for the same reason: a broken probe fails
silently and produces well-formed output.

The combat census adds a **second** calibration, because it has a second silent
failure mode. Forge's `FakePlayer` overrides `onUpdate()` to do nothing, and the
probe is never added to the world's entity list, so nothing ever ticks it. Three
things then never happen, and all three fail in the direction of a plausible
number:

- **`ticksExisted` stays 0 forever.** Every piece of combat memory in the mod
  compares against it. `Cooldowns.isReady` asks `ticksExisted >= readyAt`, false
  for all time at tick zero — Crushing Blow and Get Off Me fire once each and
  then look like enchantments that decline to proc. `CombatState.recordHit` asks
  whether `now - lastTick` exceeds the window; at a frozen zero it never does, so
  Momentum's streak never resets. `wasHurtRecently` is true forever, so Riposte's
  conditional bonus becomes unconditional. Two of those inflate and one deflates.
- **Potion effects never expire.** Strength from Rage or Excalibur is applied when
  added and then never removed — a four-second buff measured as permanent.
- **Invulnerability never lapses**, so a defensive measurement records the first
  hit of a fight and ignores every one after.

`CensusProbe.pumpTick` fixes this by calling the real `onEntityUpdate` and posting
a real `PlayerTickEvent` to the bus the bridge is registered on — driving the
shipping code rather than a copy of it. `calibrateTick` proves it did: it puts
Excalibur on a sword, pumps a full 40-tick cycle, and requires the probe to come
out with Strength on it. If the tick dispatch is not reaching the probe it reports
a failure instead of a file of zeroes.

## The chunk trap

This one cost the most to find and is worth writing down, because it produced
data that looked entirely reasonable.

`World.updateEntityWithOptionalForce` (World.java:2266-2290) only ticks an entity
when `checkChunksExist` is true for a **32-block radius** around it. A census has
no real players, so once the spawn region prepared at startup drifts out of
memory — about a minute in — the chunks neighbouring the arena unload. The
arena's own chunk survives, because spawn chunks are protected, so
`spawnEntityInWorld` still succeeds and the target is still in `loadedEntityList`.
It simply never ticks again. The repair that would re-register it with its chunk
lives inside the same `canUpdate` branch, so it never recovers either.

A target that never ticks never loses its invulnerability frames. Vanilla's
`attackEntityFrom` discards any hit that is not larger than the last one, so
**exactly one swing of a fight lands and every subsequent swing is silently
dropped.** The cell still runs its full window, still reports forty swings, and
writes a tidy row saying the enchantment is worth −97%.

Symptom to recognise: every offensive cell after the first minute reporting
`damage_dealt` equal to exactly one hit, and a suspiciously uniform `marginal_pct`
across unrelated enchantments.

The fix uses the escape hatch vanilla already has. The same method opens with
`isForced = getPersistentChunks().containsKey(...)` and then
`b0 = isForced ? 0 : 32` — a chunk force-loaded through Forge's
`ForgeChunkManager` shrinks the required radius to zero. The census requests a
ticket for the arena on start and releases it on stop. Note that `loadChunk`
alone is **not** sufficient: it keeps chunks resident but does nothing about the
32-block test.

Forge refuses a ticket to a mod with no loading callback registered, so one is
registered on first use. It is deliberately empty — a ticket held by a
measurement run has no meaning after a restart, and re-forcing those chunks would
leave a finished census pinning part of a world forever.

## Reading the output honestly

**Against weak targets the damage figures quantise.** A diamond sword kills a
20-health zombie in three hits, so a 400-tick window is dominated by the
kill-and-respawn cadence rather than by sustained output, and enchantments that
differ genuinely can both report exactly `13 kills / 260 damage`. Damage is
counted as health actually lost, so overkill is discarded. Use the pack's bosses
for anything you intend to tune on; a vanilla zombie is a harness test, not a
measurement.

**`hits_landed` is melee-only.** An arrow damages on impact rather than at the
moment it is fired, so bow cells legitimately report zero and their damage shows
up in `damage_dealt`.

**`attributed_damage` is not the whole contribution.** It records the change an
enchantment made to the hit in flight, which is the whole story for Executioner
or Colossus and only part of it for Rupture, Arc or Venomous, whose damage
arrives later or lands on somebody else. Those appear in `damage_dealt` and not
in that column. The two must not be added together.

**The swing cadence is an assumption.** One swing every ten ticks against
vanilla's twenty-tick invulnerability window. It cancels out of every marginal
figure because control and treatment use the same value, and it is recorded in
the file header.

**Prefer the per-trigger proc file over the combat file's proc columns.**
`qfcontent-census-combat.tsv` carries one aggregate `observed_proc_pct` per cell;
`qfcontent-census-combat-procs.tsv` is keyed by enchantment *and* trigger. When
the two disagree the second is right, and the disagreement is worth reading — it
is how the arrow contamination below was found.

**A cell in the failures file is not balanced**, whatever the tuning document
says about it.

## A false bug report, and how it was caught

Worth recording because the failure looked exactly like a real finding.

An early run reported Poisonous firing at **98%** against a declared 30%, and
Rupture at 97% against 45%. Both are weapon enchantments with a damage-over-time
effect, so the obvious reading was that their DoT ticks were re-entering the
dispatcher and re-rolling — a plausible and serious bug.

It was not. The per-trigger file, which has always been keyed by enchantment,
showed Poisonous at 29.4% on TICK and 40% on ATTACK — correct, within noise. The
inflated number came from the census itself: the per-cell aggregate summed *every*
counter in the tap, and a bow cell looses an arrow every ten ticks, some of which
never hit anything. Those arrows outlived the cell that fired them, went on
dispatching `ARROW_TICK` for their own bow's enchantments once per arrow per tick,
and their rolls landed in whatever cell happened to be running.

Two things were wrong and both are fixed: the aggregate now counts only the
enchantments the cell is measuring, and arrows still in flight are removed
between cells. The general lesson is the one the ore survey already learned — a
measurement that aggregates across everything in the world will eventually
measure something else, and the only defence is to key every counter to the thing
it is about.

## Controls the harness imposes

These exist so the arena cannot be what kills the target, and each is a thing
that produced a wrong number before it was added:

- Targets are spawned on ground resolved **per slot**, because one shared height
  drops a mob into a hillside where it suffocates.
- Burning targets are extinguished every tick, so a cell run after the census
  world reaches daylight measures the enchantment rather than the sunlight.
- Three targets per cell, so cleave effects — Arc above all — have somewhere to
  land. A single-target census records Arc as contributing nothing.
- One incoming hit every two seconds during offensive cells. Mob AI never engages
  the probe, because it is not in the world's player list, which would leave
  Riposte and Bulwark permanently untriggered and measured at zero.
- Per-entity combat memory is cleared between cells. The probe is reused, so a
  Momentum streak or a Crushing Blow cooldown earned in one cell would otherwise
  still be there at the start of the next, and a contaminated result is
  indistinguishable from a clean one.

## Bosses the census fights differently

- **TragicMC Kitsune is immune by design.** With the pack's
  `kitsunakumaFireballExempt=true` it takes damage only from its own fireballs
  knocked back into it (or the Sword/Bow of Justice); every weapon hit is zeroed.
  No weapon enchantment can act on that fight, so its campaign jobs run
  `modes=defense` only and it is left out of every offensive phase.
- **TragicMC Enyvil is struck through its parts** (`part=enyvilEye`), as a
  player's click resolves to one; its main body refuses player hits.
- **Lord of Torment's fight ends at 50%**, where it leaves for the Torment
  dimension. qfcampaign integrates its TTK over the bands above 50% only.
- **Apis and the Twilight Lich are measured in their vulnerable phase**: the
  census holds Apis's reflection and the Lich's shields down. A real Apis fight
  is about twice as long, waiting out the reflect.
