# Open decisions for the owner

Newest first. Each entry has options and a recommendation. The owner answers on the Decisions
page: entries here are carried into a sheet (`tools/decisions/sheet.py`; draft
`tools/decisions/drafts/s002.json`), published when its supporting documents exist. When
answered, record the answer in `docs/decisions/` (lasting calls) or the track journal, and
delete the entry here. Sheet 1 (30 cards) was answered 2026-10-25 → decisions 0004–0007.

## Balance (cards once the re-test and the effects table land)
- **Enchant rarity distribution and new enchantments** (`docs/design/enchant-rarity-plan.md`,
  pending). The owner wants the comprehensive effects table first; no loot placement before it.
- **Fight-duration target bands per tier** (`docs/design/fight-duration-study.md`, pending).
  "Check back in before making any other changes in this capacity."

## Quests
- **The voice.** Three or four samples in different registers on the same three quests (Mac
  writers; `docs/design/quests/wp6-writing-brief.md`). "I want to stay open minded." A card when
  the samples exist.
- **WP-6 finale and Pack Master rewards** (bag + tome per finale; statue + Legendary bag), the Act
  III diamond overage (78 vs 72), and whether Act III's tab waits for the Act II finale. In s002.

## Textures
- **F32 Modded Edition 1.7.10** (README-only permission, no licence file): use it for Railcraft,
  Twilight, Witchery, Chisel, drawers, iron chests and BoP at 32x, or reference only.
  *Recommend: use, README quoted.* In s002.
- **Netherrack and end stone hosts** (Faithful so the Nether and End ores can follow the stone-ore
  path) and **four uncertain backports** (soul fire ×2, silver concrete, blast furnace bottom). In s002.
- **Shipping third-party PBR maps** (Vanilla Normals Renewed: README allows redistribution, unsold,
  with a link). Confirm before they go in the shipped zip.

## Shader
- **Rule 10 counted in full-screen equivalents** so clouds, light shafts, bloom and AO can each use
  a sub-resolution buffer. *Recommend: yes.* In s002.

## Server
- **RCON over Tailscale** for remote admin. *Recommend: yes.* In s002.
- **"Who's online" publishing** shows friends' Minecraft names on the public site. *Recommend: ask
  the friends first; off until then.* Needs a gist-scoped token either way.
- **The loaders bundle, item by item** (`docs/design/server-loaders-explainer.md`, pending): applied
  as decided; the owner asked for each item's effect, with a revert card per item.
- **The hub** (`docs/design/hub-proposal.md`, pending): a lobby with the spawn picker, information,
  a protected trade station; which trade mechanism.

## Site
- **Publish route for the Mac's site work** (`ops/tracks/site.md`). After round 4: merge
  origin/main into the Mac's main (6 conflicts; the PC's `/online/` page, fed by the supervisor,
  replaces the Mac's), then push either as a `mac/site` PR or straight to main (deploys at once).
  *Recommend: `mac/site` PR, so the PC sees the merge before it goes live.*
- **Game assets on the public site.** The Lucky Block and Krypt pages ship vanilla 1.7.10
  textures, and round 4 adds the game's sounds plus OreSpawn's (Mojang's and OreSpawn's,
  all rights reserved). CLAUDE.md says only Faithful-licensed or redistribution-permitting art
  ships. Options: (a) keep them, credited, as most fan sites do; (b) swap textures to QF
  Textures / Faithful (licensed) and sounds to our own synthesized set; (c) keep textures, swap
  sounds. *Recommend: (b) for textures, since QF Textures is the pack's look anyway; decide sounds
  after hearing the round.*

## Harness / PC
- **The last ~10 ms of focus risk.** LWJGL calls SetForegroundWindow once per test-client launch,
  and the guard hands focus back within 10 ms. Removing it fully needs a qf-tweaks transformer,
  which means a live-jar install. *Recommend: yes, low risk.*
