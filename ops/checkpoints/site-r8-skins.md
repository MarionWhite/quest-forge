# site-r8-skins (checkpoint, started 2026-10-27, Mac)

Agent: researcher (sonnet). Read only; writes this checkpoint and files in the scratchpad `r8/skins/`.

## Owner's words (2026-10-27, round 8)
- "I think we should use the mob skins from the Patrix 32x texture packs for the animations to make the mobs
  scarier unless there is an even more terrifying texture pack for them. Leave the actual environmental blocks the
  same vanilla texture, but lets make these mobs scary as fuck."

## The constraint
CLAUDE.md: only Faithful-licensed or redistribution-permitting art ships; all-rights-reserved packs are studied,
never copied, traced or recoloured. The site and repo are public. Patrix is reported as All Rights Reserved.

## Done means
- [ ] Patrix's actual licence, from its own pages (patrixtextures.com, its Modrinth and CurseForge listings, its
  Discord or FAQ terms if public). Quote it with links. Does Patrix grant permission on request, and how?
- [ ] Scary mob texture packs whose licence permits redistribution with or without credit (CC0, CC BY, MIT,
  Faithful-style, or explicit written terms). Search Modrinth (it shows each project's licence), CurseForge,
  Planet Minecraft, GitHub. Mobs needed: zombie, skeleton, wither skeleton, spider, cave spider, creeper,
  enderman, witch, slime, magma cube, blaze, ghast, silverfish, zombie pigman. For each pack: link, licence
  quote, which mobs it covers, resolution, and whether its textures fit the 1.7.10 vanilla models (a pack made
  for a model mod like Fresh Animations will not).
- [ ] Save small preview images of the best 3 packs' mobs to `r8/skins/` (untrusted downloads: each in its own new
  empty directory, read with python3 -I; do not unzip into the repo).
- [ ] Report in five lines: Patrix's licence, the best open option, and the paths.

## Progress
2026-10-27 research done (Mac). Previews (UV sheets, upscaled) in
/private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/r8/skins/
(wsz_zombie.png, cc_creeper.png, be_enderman.png, be_enderman_eyes.png). Downloads in scratchpad dl_wsz, dl_cc, dl_be (outside repo).

### Patrix (patrixcraft, Modrinth team: patrixcraft owner, FreshLX pack developer)
- Modrinth API https://api.modrinth.com/v2/project/patrix-32x : licence id `LicenseRef-All-Rights-Reserved`, name empty, no licence URL, no source, no Discord.
  Page: https://modrinth.com/resourcepack/patrix-32x . Body text has NO permission, redistribution or credit terms.
- No permission grant found. patrixtextures.com does not resolve (unverified that any official site exists); CurseForge and Discord not checked (unverified).
  Contact route: Patreon https://www.patreon.com/patrix (page text shows no licence terms; /about unverified).
- Body: "The pack also features custom mob animation from FreshLX ... with additional tweaks to fit the models better." So the scary mobs
  are Fresh Animations / OptiFine custom entity models (CEM), not vanilla 1.7.10 models: they would not fit 1.7.10 anyway, and
  FreshLX's work is a second rights holder. Verdict: cannot ship without written permission from patrixcraft AND FreshLX; do not copy.
- Other Patrix-derived ARR: Patrix Uncreepifier, Tax' Creepy Mob (424k dl, glowing eyes), Vivian's Horror Spectacular, Blood RP, Halloween Pack: all ARR.

### Open options (Modrinth licence ids from API; Modrinth is the holder's own listing; licence text itself not shown there)
| Pack | Licence | Mob | Res | Fit 1.7.10 vanilla model |
| WU_SHUANGCB's Zombie Skin https://modrinth.com/resourcepack/wu_shuangcbs-zombie-skin | CC-BY-4.0 | zombie (+husk, drowned) | 64x64 | v1.0 targets 1.7.2+; plain skin, zombie.png; _e emissive via OptiFine, random/ variants |
| Creepingly Creeper https://modrinth.com/resourcepack/creepingly-creeper | CC-BY-4.0 | creeper (red eyes, camo) | 64x32 | yes, v1.0 supports 1.0+; plain skin |
| Better Enderman https://modrinth.com/resourcepack/betterenderman | MIT | enderman + eyes | 64x32 | yes, 1.6.1+ |
| Enderman into Slenderman https://modrinth.com/resourcepack/enderman-into-slenderman | MIT | enderman | | 1.11+ and replaces model: no |
| Scary Spider https://modrinth.com/resourcepack/scary-spider | MIT | spider legs | | model change (OptiFine CEM), 1.11+: no |
| Freshly Creepers (MIT), Enhanced Evil x FA (MIT, 1.20+) | | | | Fresh Animations models: no |
Not covered by any open pack found: skeleton, wither skeleton, cave spider, witch, slime, magma cube, blaze, ghast, silverfish, zombie pigman (Modrinth-only search; CurseForge, Planet Minecraft, GitHub not searched).
Modrinth hosts almost nothing for 1.7.10; most scary packs are ARR. Gap: commission or paint our own (QF Textures) for the rest.
CC BY needs credit on the site (author, licence, link).

