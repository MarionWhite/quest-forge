# 0008 — Game assets on the public site, and publishing the Mac's site work

**Date:** 2026-11-24
**Status:** accepted (asked in the Mac session; the owner's answers below).
Source: `ops/DECISIONS.md` (Site), `ops/tracks/site.md`.

## Decisions

| Question | Decision |
|---|---|
| Game assets on the public site | **Publish as-is, credited.** The Lucky Block, Krypt and First night pages keep Minecraft 1.7.10's textures and sounds and OreSpawn's sounds, with a plain credit line at the bottom of each page and on the sound credits page. |
| Publish route | **Merge and push now.** `mac/site-publish` merged origin/main (the PC's `/online/` page wins) and went to main. |

## What this changes
- CLAUDE.md's licence rule ("only Faithful-licensed or redistribution-permitting art ships") is relaxed for the
  website's vanilla 1.7.10 and OreSpawn assets only. Everything else keeps the rule: the modpack's own releases,
  QF Textures, and all other art.
- The Patrix mob skins stay local-only (gitignored `site/graves/tex/mobs-local/`); the public Krypt shows vanilla skins.
- Screams stay CC0 / CC BY with credits (`site/lib/sfx/credits.html`).

## Why
Most Minecraft fan sites show the game's own art with credit; swapping every texture and sound first would have held
the pages back by days. The risk is a takedown request, in which case option (b) of the original entry applies: QF
Textures / Faithful textures and our own sounds.
