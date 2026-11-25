# Checkpoint: site-publish (Mac site work -> merge with origin/main, no push)

Worktree: /Users/suaz/Desktop/QuestForge-wt/site-publish, branch mac/site-publish (cut from main 0fc1a0d).
Scratch: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/publish/
Merge base with origin/main: 1fdb110. origin/main merged: 61060a2. DO NOT PUSH; the coordinator pushes.

## Done (all steps)
- [x] fetch, worktree created
- [x] merge committed: bb0f77e (parents 0fc1a0d, 61060a2); 26 conflicts resolved, see its message
  - ops/: the Mac's copy was the PC's e0a1ca4 snapshot; 17 untouched files take the PC's version,
    BOARD/DECISIONS 3-way merged on e0a1ca4, quests-wp6.md stays deleted (PC closed it)
  - home: Mac page + PC's live online card/script + Decisions card (13-tython plate); Shader Lab card left off
    (owner: shader progress private); site/online/ = PC's exactly
- [x] mobs-local in git ls-files: 0, and in no commit of origin/main..HEAD
- [x] secrets/PII scan of every Mac commit's patch (git log -p origin/main..HEAD): no tokens/keys/passwords, no emails,
  no phone numbers; demo graves/players names are invented (301f8fc says so); /Users/suaz paths were already public
- [x] pages.yml copies every site dir once (decisions, online, first-night, lucky, graves, players, lib, ...)
- [x] homepage: every href/src resolves (34), no shaders/ link; every page's nav strip resolves
- [x] check_sounds.py: 94 files, 190 names, 0 missing. check_krypt_plan.mjs: OK (3 min; support OK)
- [x] nav_check.py lucky/?idle=60000 + --bosses (15): 0 violations, feet 0, world 0
- [x] dump_frames.py (as briefed) -> scratch publish/publish/sheet.png: graves + 2 scares dumped; home, lucky/,
  first-night, online, shaders have no ?dump hook by design (NO DUMP)
- [x] console pass (scratch tools/dumpcheck.py, one Chrome at a time; shots for non-hook pages, lucky/?idle=4000 for
  the Lucky frame): 10 frames, no console errors; warnings only (three.js empty texture, headless autoplay,
  Shader Lab relay CORS from 127.0.0.1). Sheet: scratch publish/console/sheet.png; card grid crop publish/tall/cards-crop.png
- [x] board site row + journal entry

## Blocks publishing (owner)
- Game-asset licence (DECISIONS.md, Site) is still open: site/lib/sfx (vanilla + 307 OreSpawn sounds), site/lib/mc/tex,
  site/lucky/tex, site/graves/tex hold Mojang/OreSpawn ARR assets; CLAUDE.md says only Faithful/redistribution-permitting art ships.
- Shader Lab card is off the homepage (owner's privacy rule) though the coordinator asked to keep Shader Lab links: confirm.
