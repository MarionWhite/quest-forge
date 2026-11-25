# Hub proposal: the lobby, the boards, the trade station

A proposal for Decisions sheet 2. Nothing here is built. Marks: **[V]** verified
in a jar, a config, a source file or this repo; **[U]** not verified (mod
knowledge, web listings, estimates).

## What the owner asked for (decision 0007, srv-hub)

"a pre-game area like custom maps where you move around before loading into the
actual world … a well designed hub with a bunch of information, but no portals or
anything that can be used for utility … a protected trading station if people
want to exchange gear somewhere PvP is not enabled, and where they can preview
what is going into a trade before confirming … open to recommendations."

## 1. The hub is where you pick your spawn

[Decision 0003](../decisions/0003-designed-world.md) gives the world an
Ark-style spawn picker: a map of ten spawn points, each rated Gentle, Hard,
Brutal or Deadly (r14) [V]. The picker is qf-content code that does not exist
yet [V, decision 0003]. The owner's "pre-game area, before loading into the
actual world" is the same thing seen from the player's side, so one place does
both jobs.

Proposed flow:

1. **First login: you appear in the hub, not in the overworld.** You walk past
   the boards, read the rules, open the quest book. The Prologue's "Where You
   Woke" already says the server showed you a map of starting points, if it
   did [V, `quests/act-structure.md` §7].
2. **The map table is the picker.** Pick a spawn; you are placed there, and
   that spot is your respawn until you sleep in a bed [U: one line of
   qf-content code to set the player's spawn point when it places them].
3. **Later visits: `/hub` from anywhere, free for everyone.** Not a ticket:
   the hub holds nothing that skips the game. Leaving, a "Return" plate puts
   you back where you typed it, the same teleport code `/home` uses today
   [V that the code exists in qf-commands; U the plate].
4. **No re-picking.** After the first choice the table shows the map but
   places nobody: a spawn is a start, not a travel network [recommendation].

Why the hub cannot simply be "spawn" in the overworld: the ten spawns are at
least 8,688 blocks apart [V, `world/r14/difficulty.md`], so a hub at the
world's centre is thousands of blocks from everyone; and `spawn-protection`
applies to one point in the overworld only [V, `DedicatedServer.isBlockProtected`:
`dimensionId != 0` returns false].

## 2. What the hub holds

Information, nothing useful. No portals, no Ender Chests, no crafting, no
beds, no storage.

| Board | What it shows | How |
|---|---|---|
| **The rules post** | `docs/setup/server-rules.md`, eleven rules | BiblioCraft is in the pack [V jar]; its signs and clipboards hold text [U: features not checked here]. Or a qf-content "board" block whose text is the file, so the post updates with the pack [U, small]. |
| **Start here** | What the Prologue is (17 quests, decision 0004 [V]), how to open the quest book, where the first ticket comes from (the `/home` ticket ends the Prologue [V, decision 0004]) | Same board block. |
| **The map table** | The spawn picker: the ten spawns with ratings and the score beside the label [V, r14] | qf-content picker UI, planned [V]. |
| **Gallery** | The pack's dimensions and bosses: the loading-plate art qf-content already has, ordered as in `Unlockables.java` [V that the plates exist] | A qf-content "poster" block that draws a plate texture [U, small]; or BiblioCraft display cases with a souvenir item each [U]. |
| **Who's online / last seen** | Names, dimension, last login | The supervisor already writes `status.json` and can publish it to a Gist for the site [V, commit 078b205; publishing waits on a token and the friends' consent, `ops/DECISIONS.md`]. In game, a qf-content board reading the server's player list [U, small]. |
| **Server firsts** | The GLOBAL tab's "first to …" events (WP-9) [V, `act-structure.md`] | Same board block, fed by qf-content's hunt-credit code when it exists [U]. |
| **The trading station** | Section 4 | |

## 3. Protection without a claims mod

### What `spawn-protection=16` does [V, read from the 1.7.10 server source]

- Overworld only.
- **Nothing at all while the server has no ops** (an empty ops list returns
  "not protected"). `ops.json` holds only `Dev`'s offline UUID; in online mode
  the owner has to `op` his real account, or the hub is unprotected.
- Ops are exempt.
- A square, 33x33 blocks (|dx| ≤ 16 and |dz| ≤ 16 from the spawn point), the
  full height of the world.
- It blocks block breaking (`processPlayerDigging`) **and every right-click on
  a block** (`processPlayerBlockPlacement` gates `activateBlockOrUseItem`): a
  non-op inside the square cannot place, break, open a chest, press a button
  or open a sign's GUI. So boards inside the square are readable only if they
  show their text without a click, or sit outside the 33x33.
- It does not cover explosions (ICBM, MCHeli, OreSpawn bosses, Lucky Blocks),
  fire, fluids, vehicles, mobs, entity interactions (item frames, NPCs), PvP,
  or Excavate and Timber, which ignore protection [V, `hosting-a-server.md`,
  "Known and accepted"].

### Option A: the hub in the overworld, at the spawn point

- Pros: no code for the place itself; the spawn chunks (every chunk within
  128 blocks of spawn, about 17x17) are always loaded anyway [V,
  `ChunkProviderServer.unloadChunksIfNotNearSpawn`]; it is part of the world;
  the picker becomes a map room at the continent's centre.
- Cons: everything the list above does not cover needs code anyway (a
  qf-content hook cancelling player-on-player damage by position, an
  explosion hook, mob spawning kept out); mobs spawn there at night unless it
  is lit and walled; it is thousands of blocks from every spawn, so `/hub` is
  needed regardless; and a hub that ticks forever in the always-loaded chunks
  (fine for decor, never for farms).

### Option B: a lobby dimension, built by qf-content

A small dimension: void, with the hub structure placed from a schematic at
0,0 [U: Forge 1.7.10 registers custom dimensions through `DimensionManager`;
dimension IDs are not the scarce resource that biome IDs are, V decision
0003's note is about biomes]. In that dimension qf-content cancels:
`BlockEvent.BreakEvent` and `PlaceEvent`, `PlayerInteractEvent` except on
whitelisted blocks (boards, the map table, the trading post),
`LivingAttackEvent` between players, `ExplosionEvent`, and
`EntityJoinWorldEvent` for mobs, vehicles and projectiles. All five events
exist in Forge 1614 [V, the decompiled sources]. Ops bypass. The dimension is
loaded only while someone is in it [V: Forge unloads a dimension with no
players unless something keeps it; `server-readiness.md` 4e says the same of
TARDIS dimensions, "churns the disk but is otherwise cheap"].

- Pros: exactly "a pre-game area before loading into the actual world"; total
  control; the trading station is PvP-free by construction; no claims mod; no
  effect on the overworld; `spawn-protection=16` becomes a harmless extra.
- Cons: code [estimate 10-20 h: dimension, protection hooks, `/hub` and
  Return, placement from the map table; the picker UI is its own job]; the hub
  build itself is the same work in either option; clients must update
  (qf-content's version is in the handshake [V, `version.gradle.kts`]), which
  the picker needs anyway.

### Recommendation: B, a lobby dimension

It is what the owner described, it makes the trading station safe without a
second mechanism, and the picker has to be code in any case. Build the hub
structure once in a creative test world, export it, and let qf-content place
it, so the design iterates like the world does: renders, not hand painting.
Keep `spawn-protection=16` on the overworld spawn regardless; it costs nothing.

## 4. The trading station

Two requirements from the owner: PvP off there, and "preview what is going into
a trade before confirming".

### What exists for 1.7.10

| Option | What it is | Preview before confirm | Live player-to-player | Effort | Risk |
|---|---|---|---|---|---|
| **Trade Booth** (Forge, 1.7.10 listing dated 2018, author not named) [V listing, U everything else] | Two blocks: an owner-locked storage block and a booth on top with 8 price/item pairs; customers left-click a pair; works while the owner is offline | Yes: the pair is the preview | No: it is a shop, not an exchange | Trial on a scratch server (2 h), then a pack release: it adds blocks, so every client needs it | Abandoned, source unknown, never run on Forge 1614 / Java 25 / our 108 mods |
| **Vending Block** (AUTOMATIC_MAIDEN, 1.7.10 port exists) [V listing, U the rest] | Three vending blocks: sell X for Y from a stock, only the placer can remove | Yes | No: a shop | Same as above | Same as above; the "revived" versions target modern Minecraft [V listing] |
| **CustomNPCs trader** (in the pack, `OpsOnly=true` [V config]) | An op-made NPC that trades fixed offers | Yes | No: player-to-NPC; an op is the middleman for any consignment | None in code; op time per listing | Low (already in the pack) [U: the 1.7.10 trader role's details were not confirmed] |
| **EnderStorage / vault pattern** (both in the pack [V]) | Colour-coded shared chests as drop boxes; `/vault` for private storage | You see the chest | No atomic swap: the first to grab takes both sides | None | Scams; honour-based, which the owner accepts for graves, but it does not meet "preview before confirming" |
| **In-house "Trading Post"** (qf-content) | A block in the hub; two players open one shared screen: your offer on the left, theirs on the right, both confirm, a short countdown, then a server-side atomic swap | Yes, with tooltips | Yes | [estimate] 8-16 h: container, GUI, packets, edge cases, a two-player headless test | Dupe bugs, the 1.7.10 container classic; mitigated below |

qf-content already has the pieces: a packet layer with twenty-odd packets
(`net/QFNetwork.java`) [V] and container GUIs (the vault in qf-commands,
`GuiVault`/`VaultContainer`) [V].

### Recommendation: the in-house Trading Post

Design for the card:

- A **Trading Post** block, placeable by ops, in the hub only. Two players
  right-click it (or `/trade <player>` while both are in the hub). Only the
  hub has one, so every trade happens where PvP is off.
- One screen, two halves: 12 offer slots each. You can only edit your side;
  you see theirs with full tooltips (enchantments, NBT).
- **Confirm** on each side. Any change to either side clears both confirms.
  After both confirm, a 3-second countdown with both offers locked, so a
  last-second swap cannot fool anyone (the trick the modern Secure Trade mod
  uses [V, its CurseForge page]).
- The swap is one server-side operation: items never exist in two places,
  and the server owns both inventories for the whole trade. On close,
  disconnect or server stop, everything goes back to its owner; if a bag is
  full, it drops at that player's feet in the hub.
- Tested headlessly with two scripted players on a slim server trial before
  it ships [U: the probe harness exists for one client, `questforge-unattended-
  client-probe`; a second needs the queue's one-client rule relaxed for
  servers, which it does not cover].

Trade Booth stays a possible later addition for offline shops, after a scratch
trial, if the friends ask for one.

## 5. Cards for sheet 2

1. **hub-where**: lobby dimension (recommended) or the overworld spawn.
2. **hub-access**: `/hub` free for everyone plus Return (recommended), or
   walking only.
3. **hub-respawn**: the picker sets your respawn point until your first bed
   (recommended), or beds only.
4. **hub-boards**: which boards: rules, start here, gallery, who's online,
   firsts. Who's online in game is separate from publishing names on the site
   (already an open decision).
5. **hub-trade**: the in-house Trading Post (recommended), a Trade Booth trial,
   or nothing beyond the honour system.
