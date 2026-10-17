# Platform decision: stay on 1.7.10, or port to a newer Minecraft?

> **Decided 2026-10-17 by the user: stay on 1.7.10.** The reasoning below was accepted.
> The ore and structure survey is **deferred until just before the pack goes to a real server**:
> worldgen will keep changing until then, so a survey now would be stale.

Written 2026-10-17, before the 15–25 hours of Angelica and Java 25 work in
[`angelica-decision.md`](angelica-decision.md). The question was: will we
regret building on 1.7.10, after all the quest, shader, balance and server work
to come?

How this was researched: the CurseForge, Modrinth and GitHub listings for every
identity mod were checked on 2026-10-17, through the Modrinth API and a
CurseForge file mirror (api.cfwidget.com), because CurseForge blocks direct
fetching. The size of our own code was measured in the repo. The 1.7.10
numbers come from our own benches. Nothing was installed or launched. Where
evidence is thin, the text says **unverified**.

## Recommendation

**Stay on 1.7.10 and adopt the GTNH stack. Confidence: high, about 85%.**

Two facts decide it:

1. **The mods that make this CrazyCraft exist only on 1.7.10.**
   - OreSpawn and TragicMC 2 never left 1.7.10. Newer versions have nothing
     beyond alpha fan remakes, or a pack of OreSpawn's bosses on 1.12.2.
   - Fisk's Transformers and the original Chocolate Quest have no equivalent
     on any newer version.
   - Witchery and MCHeli survive on newer versions only as remakes or alphas.
   - On 1.20.1, the best modern target, 7 of the 17 identity mods have no
     faithful version. That includes the two most iconic, OreSpawn and
     TragicMC. A port would build a different pack that shares a name with
     this one.
2. **The 1.7.10 platform is more alive in 2026 than it has been for years.**
   - Angelica had seven releases between 4 and 17 October 2026, and it has 100
     or more contributors.
   - lwjgl3ify (Java 25) had seven releases in five weeks.
   - Hodgepodge had ten releases in three weeks.
   - The GT New Horizons pack ships nightly builds.
   - Angelica's shaders are now marked "Generally Available".
   - Even if all of that stopped tomorrow, a finished 1.7.10 pack keeps
     working: we hold the jars, and Minecraft 1.7.10 does not change under us.

A third fact backs this up for the friends' weaker PCs. The whole pack
measured **1.3 GB of live heap** in a loaded world, and it fits a 3 GB heap
on an 8 GB machine
([`performance-plan.md`](performance-plan.md)). Large modern packs recommend
8–12 GB (ATM9, ATM10), and none of them came close to 1.3 GB.

**What we give up by staying:** modern vanilla content. That means 1.13+
water and swimming, the Nether update, Caves & Cliffs, newer mobs and blocks,
and the Create ecosystem. It also means the pool of mods we can add is fixed:
no one writes new content mods for 1.7.10. That is the real cost of staying.
It only matters if those things are what the group wants.

**The conditions that would flip this:**

- **A faithful, maintained OreSpawn and TragicMC appear on 1.20.1 or 1.21.**
  The closest today is Craziness Awakened (1.20.1, alpha, 60+ mobs; whether it
  has Mobzilla, the King or the Queen is unverified). If it reaches a full
  release with the bosses, and Lycanites "Incursion" leaves alpha, 1.20.1
  becomes worth re-pricing.
- **The group decides it wants modern vanilla more than OreSpawn, TragicMC
  and Transformers.** Then the answer is 1.20.1 Forge, and the right move is
  to build on an existing modern CrazyCraft pack (option F), not to port ours.
- **Something breaks 1.7.10 from outside:** Microsoft login stops working on
  old versions, or an unpatchable security hole appears. There is no sign of
  either. Login works through current launchers, and our server already
  removes the Log4Shell class
  ([`../setup/hosting-a-server.md`](../setup/hosting-a-server.md)).
- **Not a flip condition:** friends' GPUs that lack OpenGL 3.3. Modern
  versions need OpenGL 3.2–3.3 too, and Sodium officially wants 4.5. Those PCs
  are better served by our OptiFine E7 fallback than by any newer version.

## Comparison

"Identity" counts the 17 identity mods that have a faithful, usable version:
the original mod or a close port, maintained, alpha or abandoned-but-working.
A different mod that only covers the same theme doesn't count. Effort is solo
hours with Claude's help, to reach today's feature parity. The estimates are
explained under "Porting our own code" below.

| | A. 1.7.10 + GTNH | B. 1.12.2 (Forge / Cleanroom) | C. 1.16.5 Forge | D. 1.20.1 Forge | E. 1.21.1 NeoForge | F. Base on a modern CC pack |
|---|---|---|---|---|---|---|
| Identity mods kept | **17 / 17** | 13 / 17, plus OreSpawn's bosses only | 9 / 17, mostly abandoned builds | 10 / 17 (Lycanites alpha; Furniture as its successor, Refurbished) | about 9 / 17 (several alpha; split across NeoForge and Fabric) | What the pack ships (Chaos Awakens or Craziness Awakened instead of OreSpawn) |
| Effort to parity | **15–25 h** (already at parity; this is the upgrade) | 250–400 h | 450–700 h | 450–750 h | 550–900 h | 300–550 h to re-add our own content; the pack itself is free |
| Renderer / shaders | Angelica (Celeritas + Iris backport), shaders GA; measured 1.7–3.9× OptiFine's fps with shaders | OptiFine; Celeritas only as unofficial builds; Cleanroom alpha | Rubidium/Oculus, old and unmaintained | Embeddium + Oculus, mature | Sodium + Iris, best-maintained | as D or C |
| RAM for this pack size | 1.3 GB live heap measured; 3 GB heap enough | more than 1.7.10, unmeasured | 6–8 GB heap (estimate) | 6–8 GB heap (estimate); ATM9 recommends about 8 GB | 6–10 GB (estimate); ATM10 recommends 8–12 GB | as D |
| Java | 25 via lwjgl3ify (server benched); 8 still works | 25 via Cleanroom (alpha) | 8–11 | 17 | 21 | as D |
| Platform maintenance | Very active (GTNH); Forge itself frozen | Cleanroom active but labelled alpha, with breaking changes this month | Abandoned by most authors | Forge's long-term version; largest modern mod pool (25,245 Forge mods on Modrinth) | Most active; but 26.1 is expected to replace 1.21.1 as the next stable version | as D |
| What we gain | Fps, shaders, GC stalls fixed, Java 25 | Chocolate Quest Repoured, a fuller Lycanites, maintained MCHeli CE, Witchery: Resurrected | Little | Modern vanilla, Create, Simple Voice Chat, a big mod pool | as D, newest | as D, plus a tested mod list |
| What we lose | Modern vanilla; no new mods | Full OreSpawn, TragicMC 2, Legends, Transformers; stays old anyway | Most of the identity, and it is a dead version | OreSpawn, TragicMC, Witchery, MCHeli, Transformers, Chocolate Quest, iChun's Morph; the quest book, enchant balance and census have to be redone | as D, plus Legends; Pandora's Box is Fabric-only and Lucky Block NeoForge-only | as D, plus everything we have built is set aside |

### B, 1.12.2: the runner-up, and why it still loses

1.12.2 keeps more of the identity than any other move.

- **Faithful versions:**
  - Lycanites: its most complete version.
  - Witchery: Resurrected, described as "mostly finished content-wise".
  - Chocolate Quest Repoured: a better Chocolate Quest.
  - McHeli: Community Edition, maintained (August 2026).
  - Twilight Forest, Morph, Lucky Block, Pandora's Box, Decocraft, CustomNPCs,
    Inventory Pets, MrCrayfish's Furniture and ProjectE all have official
    1.12.2 builds.
  - The quest book can stay on Better Questing: BetterQuesting Unofficial was
    updated in May 2026.
- **What it loses:**
  - OreSpawn: only its bosses survive (the King, the Queen and Mobzilla, in
    "Legacy of Utopia"). The rest of the mod is gone.
  - TragicMC: TragicMC 3 is an alpha the author has abandoned.
  - Legends: none. HeroesExpansion was discontinued in 2019.
  - Transformers: none.
- **Why it still loses:**
  - It isn't newer in any way the group would notice. The vanilla is still
    old, and most of its mods were abandoned years ago, like ours.
  - Its modern-Java loader (Cleanroom) is still labelled alpha. Version 0.7.0
    of 13 October 2026 was a "major overhaul" with breaking config changes.
  - Its shader story is worse than Angelica's.
  - It costs 250–400 h to trade a few identity mods for others. It only makes
    sense if Chocolate Quest Repoured and Witchery: Resurrected matter more
    than OreSpawn, TragicMC, Legends and Transformers.

### F, building on an existing modern CrazyCraft

These packs already exist:

| Pack | Version | Status | Size | OreSpawn content |
|---|---|---|---|---|
| Crazy Craft Updated | 1.16.5 | Updated 2026-09-20, about 4.2 M downloads | 250+ mods | Chaos Awakens |
| Crazy Craft Even More Updated | 1.20.1 | Updated 2026-10-10 | — | an OreSpawn remake |
| Crazy Craft Chaos | 1.20.1 | Updated 2026-08-15 | — | an OreSpawn remake |

None of them is made by the original CrazyCraft authors. The original CrazyCraft
4.0 has been frozen since 29 February 2020. If the group ever wants modern
CrazyCraft, starting from one of these is cheaper than porting our pack. But
they are not what Quest Forge is: the custom enchants, the quest book, the
balance work and the jukebox would all have to be rebuilt on top of one.

## The identity mods, per version

Key:

- **OFF**: an official build.
- **fork**: an unofficial port or fork.
- **repl**: a different mod covering the same idea.
- **—**: nothing found.
- **maint**: updated in 2026.
- **aband**: no update for two years or more.

Dates are the newest file for that version.

| Mod | 1.7.10 (what we run) | 1.12.2 | 1.16.5 | 1.20.1 | 1.21.x |
|---|---|---|---|---|---|
| **OreSpawn** | OFF, aband (author stopped here) | fork, bosses only: "The King and The Queen – Legacy of Utopia", maint 2026-09-27 | repl: Chaos Awakens, aband (2022–24) | repl: Craziness Awakened, **alpha**, 2025-07 (60+ mobs; bosses unverified) | — |
| **TragicMC 2** | OFF, aband (2016) | TragicMC 3, alpha rewrite, author quit 2022 | — | — | — |
| **Lycanites Mobs** | OFF, aband | OFF, the most complete, 2024-09 | OFF, 2025-12 | OFF "Incursion", **alpha**, 2026-08 | fork "Reloaded", alpha, one upload 2026-05 |
| **Witchery** | OFF, aband (2015); WitcheryPatch 2023 | fork: Witchery: Resurrected, faithful; Companion maint 2026-06 | repl: Enchanted, aband 2022 | repl: Enchanted 2026-06; Bewitchment (Fabric) 2024 | repl: Just Another Witchery Remake ("1:0.9 remake"), maint 2026-10-16, v0.5, breaks worlds between versions |
| **Twilight Forest** | OFF, 2023-07 | OFF, aband 2020 | OFF beta, aband 2021 | OFF, 2024-06 | **OFF, maint**, 2026-03 (NeoForge 1.21.1) |
| **MCHeli** | OFF aband; fork Mcheli-O/Overdrive, maint 2026-10-14 | fork: McHeli Community Edition, maint 2026-08 | repl: Immersive Aircraft | repl: Immersive Aircraft, Superb Warfare | fork: MCHeli Modern Port, **alpha**, 2026-08 (112 vehicles, creative-only spawning) |
| **Legends** (superheroes) | OFF (Superheroes Unlimited) | — (repl: HeroesExpansion, aband 2019) | — | **OFF, maint**, 2026-10-12 (roster vs 1.7.10 unverified) | — |
| **Morph** (iChun) | OFF, aband 2016 | OFF, aband 2020 | OFF, aband 2023 | repl: ReMorphed / Woodwalkers, maint | repl: ReMorphed / Woodwalkers, maint 2026-10 |
| **Transformers** (Fisk) | OFF, aband; our patched fork | — (another author's G1 mod, discontinued 2018) | — | repl: Craftformers Prime / Symformers, early, few robots | — (a tech demo) |
| **Chocolate Quest** | OFF, aband | **CQ Repoured**, maint (2.8.0B, 2025-11 / 2026-03) | unreleased branch | unreleased branch (2025-02); repl: When Dungeons Arise (structures only) | unreleased pre-alpha branch, 2026-08 |
| **Lucky Block** | OFF, aband | OFF, aband | OFF, aband | OFF, frozen 2023-10 | OFF, NeoForge 1.21.6–1.21.8 only, 2025-12 (no 1.21.1 seen) |
| **Pandora's Box** | OFF, aband 2014 | OFF, aband 2017 | OFF, 2024-03 | OFF, maint 2026-02 | OFF, maint 2026-05, **Fabric only** |
| **Decocraft** | OFF, aband | OFF, aband | OFF, perpetual beta | OFF 3.x, maint 2025-12 | OFF, maint 2026-04 |
| **CustomNPCs** | fork: CustomNPC+, **maint** 2026-03 (repo active 2026-10) | OFF, aband 2020 | OFF, aband 2022 | fork: CustomNPCs-Unofficial, maint 2026-07 | fork: same, 1.21.1 only, 2026-05 |
| **Inventory Pets** | OFF, aband | OFF, aband | OFF, aband | OFF, maint 2026-08 | OFF, maint 2026-08 |
| **MrCrayfish's Furniture** | OFF, aband 2014 | OFF, aband 2022 | prerelease, aband | successor Refurbished Furniture (different, modern item set) | Refurbished, maint 2026 |
| **ProjectE** | OFF, aband 2016 | OFF, aband 2019 | OFF, 2022 | OFF, stable 2023 | OFF, 2025-06, still getting commits in 2026-07 |

Two traps found while checking:

- "MMD OreSpawn" is an unrelated ore library.
- Vazkii's "Morph-o-Tool" is a wrench, not a morph mod.

Also, luckyblockmod.com is now a casino site. Download Lucky Block only from
CurseForge.

## The rest of the pack, per version

Condensed. These mods matter less, because most have a good modern
replacement. **Bold** marks the ones with no equivalent outside 1.7.10.

| Mod | 1.12.2 | 1.20.1 | 1.21.x |
|---|---|---|---|
| **Hardcore Ender Expansion** | — | — | — |
| **Welcome to the Jungle** | — (unverified) | — | — |
| Recurrent Complex | OFF ("seeking maintainer") | — | — |
| Doomlike / Roguelike Dungeons | OFF | OFF / Dungeon Crawl | Dungeon Crawl (unverified) |
| Mutant Creatures | Mutant Beasts | Mutant Monsters | Mutant Monsters |
| Infernal Mobs | OFF | OFF 2026-02 | OFF 2026-02 |
| Just Another Spawner | In Control! | In Control! | In Control! |
| Psychedelicraft | fork, 2026-10 | small Fabric remake (unverified) | NeoForge port, 1.21.8 |
| TARDIS | New Tardis Mod | Tardis Mod / TARDIS Refined | TARDIS (eccentric) |
| Weeping Angels | OFF | OFF 2026-09 | OFF 2026-09 |
| **PortalGun, Gravity Gun (iChun)** | OFF 2019 | — | — |
| Archimedes' Ships | Valkyrien Skies 1 | VS2 + Eureka | Create: Aeronautics |
| **ICBM Classic** | OFF 2026-05 | — | — |
| SecurityCraft, Storage Drawers, JourneyMap, Iron Chests | OFF | OFF | OFF |
| Railcraft | OFF | Railcraft Reborn | Railcraft Reborn |
| Carpenter's Blocks | — | FramedBlocks | FramedBlocks |
| Chisel | OFF 2020 | Rechiseled / Chipped | Rechiseled |
| BiblioCraft | OFF 2022 | — | Bibliocraft Legacy |
| **Malisis' Doors** | OFF 2018 | — | — |
| Hats (iChun) | OFF 2020 | — | — |
| Sync (iChun) | OFF 2019 | Fabric fork (unverified) | — |
| Battlegear 2 | — | Better Combat / Epic Fight (different) | same |
| Adventure Backpack | — | Traveler's / Sophisticated Backpacks | same |
| Little Maid Mob | littleMaidMobX 2019 | Touhou Little Maid | Touhou Little Maid |
| Compact Machines | OFF | OFF 2024 | OFF 2026-02 |
| **Mob Dismemberment / Amputation** | Amputation (unverified) | — | — |
| Level Up! | Level Up! Reloaded | Project MMO | Project MMO |
| Damage Indicators, Waila, NEI | Neat, Hwyla, JEI | Neat/Jade, JEI/EMI | Jade, JEI/EMI |
| GraveStones | Corail Tombstone | Corail / GraveStone | Corail / GraveStone |
| **Ender Utilities, OpenBlocks, Loot Bags, Wireless Redstone** | OFF 2019–20 | — | — |
| Baubles | OFF | Curios | Curios |
| Custom Menu | OFF 2020 | FancyMenu | FancyMenu |
| Sound Filters | OFF | Sound Physics Remastered | Sound Physics Remastered |
| CraftTweaker | OFF | CraftTweaker / KubeJS | CraftTweaker / KubeJS |
| Chunk Pregenerator | OFF | Chunky | OFF / Chunky |
| **Quest book** | Better Questing (BQ Unofficial, maint 2026-05); FTB Quests Importer converts BQ to FTBQ on 1.12.2 | FTB Quests 2026-05; Heracles 2024 | FTB Quests 2026-09; Odyssey 2026-10 |
| Voice chat | Simple Voice Chat | Simple Voice Chat, Plasmo | Simple Voice Chat, Plasmo |

## Porting our own code

What we have, measured 2026-10-17:

| Piece | Size | What it is |
|---|---|---|
| qf-content | 187 files, 39,839 lines | Enchants 8,524; jukebox 16,104; census 4,795; net 2,188; survey 2,012; voice 1,947; client 1,205 |
| qf-tweaks | 15 files, 1,580 lines | ASM coremod patches |
| qf-commands | 17 files, 2,147 lines | Server commands |
| Quest book | 312 quests in 9 chapters, an 873 KB `DefaultQuests.json` | Better Questing |
| Configs | 127 entries under `pack/config` | Plus three CraftTweaker scripts |
| Transformers fork | 70,698 lines | Fisk's code, not ours, so we can't port it |

Estimates per target. These are judgement calls, not measurements. The ranges
are wide because nobody has ported a 40,000-line mod like this one. The one
documented comparison is Balkon's WeaponMod. That is a single moderate content
mod, and porting it from 1.7.10 to modern versions took "a bit more than 4
months" part-time (started 2024-02-17).

| Work | 1.12.2 | 1.16.5 / 1.20.1 | 1.21.x |
|---|---|---|---|
| **qf-content.** Most of the jukebox's audio, library and codec logic is plain Java and moves cheaply. The parts that touch Minecraft have to be rewritten: blocks, tile entities, GUIs, rendering, the network layer and the enchant hooks. | 80–140 h: the same FML event model, but block states and registry events | 180–300 h: the 1.13 "flattening" ended numeric IDs and metadata; rendering was rewritten in 1.15 and 1.17 | 220–360 h: as 1.20.1, plus **enchantments became data files in 1.21**, so all 81 have to be redesigned as data plus custom effect types, not ported class by class |
| **qf-tweaks.** Coremods don't carry over; mixins replace them. But most of these patches fix 1.7.10 mods (GraveStones, Lucky Block, LittleMaid, Morph, OptiFine) that would be replaced anyway. | 5–15 h | 5–15 h | 5–15 h |
| **qf-commands** | 5–10 h | 10–20 h | 10–20 h |
| **Quest book.** Every quest points at item IDs that change, and many point at mods that would be gone. | 40–70 h: BQ still exists; the 1.7.10 → 1.12 file format is unverified | 80–150 h: rebuilt by hand in FTB Quests; no converter from a 1.7.10 file found | same |
| **Balance.** Progression audit, gating scripts, enchant tuning, combat census rerun, ore survey. The census code is in qf-content; the data has to be measured again. | 40–80 h | 60–120 h: a different mob and gear ladder | same |
| **Shaders.** Our pack's own shader work targets the OptiFine/Iris format, so it is the cheapest piece. | 5–10 h on OptiFine | 10–20 h on Oculus/Iris | 10–20 h |
| **Pack assembly, configs, server, client testing, lite client** | 60–100 h | 100–150 h | 120–180 h |
| **Total** | **250–400 h** (with Cleanroom's alpha risk on top) | **450–750 h** | **550–900 h** |

On 1.20.1 and later, our voice chat (1,947 lines) could be dropped for Simple
Voice Chat. That saves its port but loses our in-band design.

Licensing: OreSpawn, TragicMC and the other abandoned mods are "All Rights
Reserved". Porting one ourselves for a private friends' server is a grey area,
and it would cost far more than the table above. It is not counted.

## Performance and stability

**Client.**

- **1.7.10 + Angelica:** our benches measured 1.7–3.9 times OptiFine E7's fps
  with shaders on, and better 1% lows and worst frames at a 3 GB heap
  ([`angelica-decision.md`](angelica-decision.md)).
- **Modern renderers:** Sodium/Embeddium and Iris/Oculus are mature and fast.
  But Minecraft from 1.18 on draws far more world (a taller world, new terrain
  generation), so a fair comparison isn't "Sodium vs Angelica". It is "a
  modern pack's total load vs ours". No primary source puts numbers on that,
  so it is **unverified**.
- **GPU floor:**
  - Vanilla from 1.17 needs OpenGL 3.2–3.3.
  - Sodium's official support starts at OpenGL 4.5 (Intel HD 500 and later,
    GeForce 400 and later).
  - Angelica needs OpenGL 3.3, and 1.7.10 with OptiFine runs on older still.
  - 1.7.10 is the most forgiving option.

**Memory.**

- Our measured live heap is 1.3 GB, about 1 GB of it from Decocraft, MCHeli
  and Legends.
- The GTNH wiki recommends 4–6 GB for single player on Java 17–25.
- ATM10's recommended heap is 8–12 GB, and ATM9's is about 8 GB for 1–3
  players. Those figures come from host and wiki pages.
- A modern pack of our size would probably need a 6–8 GB heap. That is
  **inferred** from the figures above, not measured, but the direction is
  consistent across every source found.
- On an 8 GB PC that is the difference between fitting comfortably and not.

**Server.**

- Our Java 25 bench cut total GC pause time by 68% and the worst stall from
  about 1.1 s to about 0.26 s.
- Modern servers have good tuning mods (Lithium, ModernFix, FerriteCore,
  C2ME), but worldgen after 1.18 is widely said to be costlier. That is
  **unverified** here.
- For a server of 15 friends, both are adequate. 1.7.10's tick times
  measured 0.4 ms idle and with 320 mobs, far under the 50 ms budget.

## Longevity

- **GTNH 1.7.10 stack: very active.**
  - Angelica 2.2.28–2.2.34 shipped 4–17 October 2026.
  - lwjgl3ify had seven releases from 2026-09-07 to 2026-10-14.
  - Hodgepodge had ten releases from 2026-09-15 to 2026-10-05.
  - The GTNH pack ships nightlies.
  - The GTNH wiki now calls Java 8 "not recommended" and Java 25 "the most
    optimized". The community is moving the old version forward, not
    abandoning it.
  - The risk is that GTNH-specific fixes target GTNH's mods, not ours. That
    is why we needed our own patches (Lucky Block, LittleMaid,
    Recurrent Complex).
- **Forge for 1.7.10** gets security fixes only. That doesn't matter much,
  because the stack above patches around it.
- **Cleanroom (1.12.2):** active, but every release is still tagged alpha.
- **Forge 1.20.1:** Forge's long-term version, with the largest pool of
  modern mods.
- **NeoForge 1.21.1:** its "most popular" version, with over 16,000 mods.
  But NeoForge expects Minecraft **26.1** (Java 25, no obfuscation) to replace
  it as the next stable modding version. A 1.21.1 port could itself be one
  version behind within a year or two.
- **Java:** free Java 8 builds (Temurin, Corretto, Zulu) are supported to
  2030-12-31, so the Java 8 fallback is safe. Java 25 removes the question
  altogether.
- **Logins:** Microsoft accounts work on 1.7.10 through current launchers.
  Skins on old versions need a patch mod such as Lumy Skin Patch, which was
  updated after Mojang's January 2024 API change.

## Where the evidence is thin

- **The feature completeness of the remakes is unverified:** Craziness
  Awakened (does it have Mobzilla, the King and the Queen?), Lycanites
  Incursion, Just Another Witchery Remake, and the 1.20.1 Legends roster
  compared with 1.7.10. These are exactly the facts that would flip the
  decision. Check them again in 6–12 months.
- **The porting hours are estimates,** anchored on code size and one public
  example. Treat them as order-of-magnitude: hundreds of hours against tens.
- **Modern RAM and fps for a pack like ours are inferred** from public packs
  and host pages, not benched. A slim 1.20.1 trial (Embeddium, Oculus, the
  ten surviving identity mods) would settle it in an afternoon if the
  question ever reopens.
- **Several CurseForge dates came through a mirror.** Some Modrinth dates are
  re-uploads of old files, and were marked so where spotted.

## Sources (all accessed 2026-10-17 unless dated)

1.7.10 stack:

- Angelica releases and README: https://api.github.com/repos/GTNewHorizons/Angelica/releases, https://github.com/GTNewHorizons/Angelica
- lwjgl3ify releases: https://api.github.com/repos/GTNewHorizons/lwjgl3ify/releases
- Hodgepodge releases: https://api.github.com/repos/GTNewHorizons/Hodgepodge/releases
- GTNH modpack repo: https://api.github.com/repos/GTNewHorizons/GT-New-Horizons-Modpack
- GTNH Java and RAM guidance: https://wiki.gtnewhorizons.com/wiki/Installing_and_Migrating
- Celeritas: https://git.taumc.org/embeddedt/celeritas

1.12.2:

- Cleanroom releases (0.7.0-alpha 2026-10-13 to 0.7.8-alpha 2026-10-17): https://api.github.com/repos/CleanroomMC/Cleanroom/releases
- Cleanroom wiki: https://cleanroommc.com/wiki/end-user-guide/introduction
- Fugue: https://www.curseforge.com/minecraft/mc-mods/fugue

Forge, NeoForge and mod counts:

- NeoForge 2025 retrospective (2026-01-01): https://neoforged.net/news/2025-retrospection/
- NeoForge 26.1 post (2026-03-24): https://neoforged.net/news/26.1release/
- Forge supported versions: https://forums.minecraftforge.net/topic/91712-supported-version-directory/
- Forge 47.4.0 for 1.20.1: https://forums.minecraftforge.net/topic/154387-forge-474-minecraft-1201/
- Mod counts per version: Modrinth search API (`total_hits`)

Performance and RAM:

- Sodium (GPU requirements): https://modrinth.com/mod/sodium
- Embeddium: https://modrinth.com/mod/embeddium
- ATM10 RAM: https://wiki.siriusmc.net/books/modpack-guides-and-tutorials/page/introduction-atm10/revisions/992, https://space-node.net/minecraft/all-the-mods-10
- ATM9 RAM: https://www.minecraft-hosting.pro/all-the-mods-9-server-hosting

Porting:

- 1.21 data-driven enchantments: https://fabricmc.net/2024/05/31/121.html (2024-05-31), https://docs.fabricmc.net/1.21.1/develop/items/custom-enchantment-effects
- WeaponMod port example: https://github.com/ThexXTURBOXx/Balkons-WeaponMod-Legacy

Security, Java and logins:

- Log4Shell advisory (Dec 2021): https://www.minecraft.net/it-it/article/important-message--security-vulnerability-java-edition
- Java 8 support dates (secondary): https://www.herodevs.com/blog-posts/java-8-11-17-eol-dates-by-openjdk-vendor-temurin-to-red-hat
- Lumy Skin Patch: https://www.curseforge.com/minecraft/mc-mods/lumy-skin-patch/files/3787022

Identity mods (Modrinth API `api.modrinth.com/v2/project/<slug>`, CurseForge via `api.cfwidget.com/minecraft/mc-mods/<slug>`):

- OreSpawn line:
  - legacy-of-utopia (2026-09-27)
  - craziness-awakened-orespawn-remake (2025-07-14)
  - chaos awakens
  - https://forums.minecraftforge.net/topic/82401-orespawn
- TragicMC: tragicmc2 (2017-09-01), tragicmc3 (2022-05-16), https://moddex.gg/mod/tragicmc3
- Lycanites: lycanites-mobs (2026-08-01), lycanites-mobs-reloaded (2026-05-28)
- Witchery line:
  - witchery (2015-04-16)
  - witchery-companion (2026-06-12)
  - just-another-witchery-remake (2026-10-16)
  - enchanted-witchcraft (2026-06-19)
  - bewitchment (2025-04-02 / 2024-10-17)
- Twilight Forest: the-twilight-forest (2026-10-17)
- MCHeli line:
  - mchce (2026-08-29)
  - mcheli-modern-port (2026-08-27)
  - Modrinth "mcheli" search (Mcheli-O 2026-10-14)
  - immersive-aircraft, superb-warfare
- Legends and superheroes: legends-mod-core and legends-superheroes-unlimited (2026-10-12), fiskheroes (2024-09-19), heroesexpansion (2019-08-15)
- Morph line: morph (2023-02-15), remorphed and woodwalkers (2026-10-13), identity (2023-08-07)
- Transformers: https://www.curseforge.com/minecraft/mc-mods/the-transformers-mod (2018-10-18), craftformers-prime (2025-11-01)
- Chocolate Quest: https://github.com/TeamChocoQuest/ChocolateQuestRepoured (branches to 2026-10-11), chocolate-quest-repoured (2026-03-29)
- Lucky Block: https://www.curseforge.com/minecraft/mc-mods/lucky-block (2025-12-26), https://github.com/alexsocha/luckyblock
- Pandora's Box: https://www.curseforge.com/minecraft/mc-mods/pandoras-box (2026-05-02)
- Decocraft: https://www.curseforge.com/minecraft/mc-mods/decocraft (2026-04-09)
- CustomNPCs line:
  - https://www.kodevelopment.nl/minecraft/customnpcs/downloads (2022-05-15)
  - https://www.curseforge.com/minecraft/mc-mods/customnpcs-unofficial (2026-07-11)
  - https://github.com/KAMKEEL/CustomNPC-Plus (2026-10-06)
- Inventory Pets: https://www.curseforge.com/minecraft/mc-mods/inventory-pets (2026-08-26)
- Furniture: https://www.curseforge.com/minecraft/mc-mods/mrcrayfish-furniture-mod/files/all (2023-06-22), https://www.curseforge.com/minecraft/mc-mods/refurbished-furniture (2026-07-10)
- ProjectE: https://www.curseforge.com/minecraft/mc-mods/projecte/files/all (2025-06-03), https://github.com/sinkillerj/ProjectE

Modpacks:

- https://www.curseforge.com/minecraft/modpacks/crazy-craft-updated (2026-09-20)
- https://www.curseforge.com/minecraft/modpacks/crazy-craft-even-more-updated (2026-10-10)
- https://modrinth.com/modpack/chaos-crazy-craft (2026-08-15)
- https://voidswrath.com/ (CrazyCraft 4.0, 2020-02-29)

Quest books and other mods:

- FTB Quests Importer: https://www.curseforge.com/minecraft/mc-mods/ftb-quests-importer
- The other mods: CurseForge project pages and Modrinth's batch project API (`api.modrinth.com/v2/projects`), as listed in the per-mod tables.
