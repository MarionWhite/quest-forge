# Fight-duration study (DRAFT)

**Status:** DRAFT, proposal only, paused 2026-10-25 at the owner's request. Nothing is changed.
Written for decision [0005](../decisions/0005-enchant-census-proposals.md) P6: "take into
consideration how long other fights are averaging ... research modern modpacks that do a good job of
balancing fight duration ... **Check back in before making any other changes in this capacity.**"
Section 3 (external evidence) is thin and says so; section 5 lists what is still open.

Tags: **[V]** verified on the page named; **[U]** unverified, from memory or a search summary only.

## 1. Our fights today

Control time to kill (no custom enchantment, the census probe's standard weapon for the tier, bands
integrated to full health), from [enchant-effects](../reference/enchant-effects.md). Apis and
Leonard are excluded for biased controls; Lord of Torment runs to 50 % health only.

| Tier | Bosses | Range | Median |
|---|---|---|---|
| T1 | 7 | 13 s (Knight Phantom) to 97 s (Tower Boss) | 34 s (Naga, Yeti) |
| T2 | 11 trusted | 12 s (Polaris) to 132 s (Ender Demon) | 40-51 s |
| T3 | 5 | 12 s (Mantis, Mothra) to 284 s (Emperor Scorpion) | 77 s |
| T4 | Mobzilla 135 s, The Queen 240 s, The King 295 s (all 750-per-hit capped); Godzilla 8 s | | 240 s |
| Rahovart | 845 s with the old max-health boost (25 per hit cap) | | P6 cuts the boost, expected about 13,500 HP and a fight of about 270 s (results doc section on P6; re-test pending) |

These are probe times: a stationary wielder hitting every swing with tier gear, so a real player's
fight is longer by dodging and healing. The pattern worth noting: the fights are not
tier-ordered. T1 Tower Boss (97 s) outlasts T2 Polaris (12 s) and T3 Mantis (12 s); the T3 median is
above the T2 median only because of the Scorpion, Kraken and Basilisk. Godzilla at 8 s is the
only boss that dies faster than a T1 mini-boss to its tier weapon.

## 2. What the owner's note implies

P6 shortened exactly one fight (Rahovart, 845 s to about 280 s) and asks for a band informed by
other packs. This draft proposes the band in section 4 for the owner to accept or change.

## 3. What others aim for (evidence found)

The searches turned up little that is quantitative. Honest summary:

- **RLCraft, Rahovart.** Health 3000 (6000 variants), defence 4, armour 0, three phases with a
  wipe-your-buffs mechanic; "sufficient damage lets you kill him before Hellfire walls clear your
  effects". The wiki gives no fight duration. [V] https://rlcraft.wiki.gg/wiki/Rahovart. Useful
  contrast: 3000 HP against our 42,249 HP at Rahovart's old setting (13,500 after P6).
  RLCraft's Bosses page is marked incomplete and lists no health or lengths [V]
  https://rlcraft.wiki.gg/wiki/Bosses
- **Prominence II.** Bosses carry levels (10 to 60) and fighting below a boss's level reduces your
  damage; the changelog tunes bosses with HP multipliers (Conjunctivius 3.5 to 6, Fallen Icon 550 to
  650, "Chaos monarch is tankier", "all bosses Weakness resistant for any cheesing"). No durations.
  [V] https://www.curseforge.com/minecraft/modpacks/prominence-2-hasturian-era/files/7688228 ;
  level claim [U] (search summary of https://www.minecraft-guides.com/modpacks/prominence-ii-hasturian-era/).
  Lesson: they tune by HP multiplier and plug cheeses, and revisit after release.
- **DawnCraft.** Marketing text only: bosses with at least 10 unique attacks. [U]
  https://www.modpackindex.com/mod/42722/dawncraft-mobs . No numbers.
- **Better Minecraft, GTNH-style packs.** Nothing usable found. [U] Not claimed.
- **Vanilla reference.** Ender Dragon 200 HP, takes about 75 % less damage except to the head
  (effective 800), crystals heal 1 HP per 0.5 s. No stated duration. [V]
  https://minecraft.wiki/w/Ender_Dragon
- **General design.** A boss should take about as long as the stage around it; an expert beating it
  in half the expected time is fine, a novice should not need four times as long. [V]
  https://www.gamedeveloper.com/design/video-game-boss-design-for-shmups . Players complain at
  ten minutes (Path of Exile thread), with replies blaming gear rather than design. [V]
  https://www.pathofexile.com/forum/view-thread/3756532 . Indie targets of 3 to 10 minutes for a
  standard boss, with a note that movement makes real fights much longer than the HP maths. [U]
  (search summary of itch.io devlogs).

Not found: any pack publishing a target in seconds. The usable principle is the shmups ratio
(expert at half the design time, novice at up to double or so) plus the "ten minutes is too long"
complaint line.

## 4. Proposed band per tier (a proposal for the owner)

Probe time, one unenchanted wielder in tier gear. A real fight is roughly 1.5 to 2.5 times
longer once dodging, healing and phases are counted, so the player-facing numbers are in brackets.

| Tier | Probe band | Player-facing | Notes |
|---|---|---|---|
| T1 | 20-60 s | 30 s-2 min | Knight Phantom (13 s) is short; Tower Boss (97 s) is long |
| T2 | 30-90 s | 1-3 min | Polaris, DeathReaper, Enyvil (12-21 s) read short; Ender Demon (132 s) long |
| T3 | 60-180 s | 2-6 min | Mantis, Mothra (12 s) are short; Scorpion and Kraken (240-284 s) are long |
| T4 | 120-300 s | 4-10 min | Mobzilla, Queen, King fit; Godzilla (8 s) is far short |
| Final (Rahovart) | up to 300 s | up to 12 min | after P6 the expected 270 s fits |

The top of each band stays under about ten minutes player-facing, matching the one fairly firm
complaint line in the evidence. Outliers below: Godzilla; the 12-13 s T2/T3 bosses. Outliers above:
Tower Boss, Emperor Scorpion, Kraken, Ender Demon. These are listed for the owner, not changed.

Reminder from the census: the strongest single enchantment shortens a fight about 40 %, and an
Epic-plus-Legendary pair about 50 %, so a fight a stacked player finishes in half its probe time
must still clear the band's floor. The floors above assume that.

## 5. Still open (draft ends here)

1. Bastion-like summon enchants elsewhere (P8's "how others do this"): the searches found nothing
   verifiable on Factions golem-summon enchants. AdvancedEnchantments' wiki index
   (https://ae.advancedplugins.net/enchantments) links Default (250+) and Custom (60+) pages
   that were not read. [U] until read.
2. Better evidence for RLCraft/Prominence/DawnCraft durations: video timings, or community
   kill-time posts. Not found in text.
3. Pack-by-pack numbers for GTNH-style bosses.
4. Decide the band (section 4) and whether to touch any outlier. Any change needs a re-census.

## 6. For the owner

Do you accept the section 4 band as the working target? No fight is changed until you say so.
