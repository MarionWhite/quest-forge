# Board

Updated 2026-10-25 22:40. Keep each row current: rewrite it, don't append. History goes in `journal/`.

| Track | Status | Next step | Blocker | Detail |
|---|---|---|---|---|
| **shaders** | Round 8 in progress; work in progress in `shaders/QuestForge` (uncommitted) | finish the r008 loops, then the critic, then publish | none | `tracks/shaders.md` |
| **textures** | QF Textures v1 in progress (cc3230e); r008 texture scenes not handed over yet | finish v1 renders, write `r008/texture_scenes.json` + TEXTURES-READY | none | `tracks/textures.md` |
| **render loop** | done: renderq live; scheduled task "QuestForge renderq"; night mode 22:15–08:00 (shot jobs only, 30 fps) | report night power/fans from `C:\qfb\renderq\power.csv` on 10-26 | none | `tools/renderq/README.md` |
| **quests** | WP-5/WP-6 drafts to decision 0004 (6acae6e); jukebox recipe (1e836c4); brief and act-structure edits uncommitted | finish brief + §6, build jukebox jar, `ops/checkpoints/quests-wp6.md`; damage-based hunt credit in qf-content, `ops/checkpoints/quests-hunt-credit.md`; then the writers' voice samples (Mac) | voice samples: Mac | `docs/design/quests/` |
| **balance** | P1–P9 + P6 config applied on main (00fba6b…ad7f9f4), not built, not installed | build, targeted census re-test, §9 results: `ops/checkpoints/balance-retest.md`; effects table + rarity plan + fight-duration study: `ops/checkpoints/balance-effects-table.md` | owner check-in before install | `docs/decisions/0005-enchant-census-proposals.md` |
| **world** | plan r13/r14: difficulty layer, rated spawns, tree generator, illustrated map | owner's WorldPainter trial | owner | `docs/design/world/` |
| **server** | rules applied and rebuilt (ba3ec94, decision 0007); /tpa committed (df53b43); MCHeli assets + Decocraft jar on the server | verify rules on disk, boot a copy, rules post, loaders explainer, hub proposal, /tpa jar: `ops/checkpoints/server-rules-docs.md` | gist token + firewall rule + port forward: owner | `docs/setup/hosting-a-server.md` |
| **performance** | win #8 (Decocraft lazy models) live; client profiles full/lite/potato | tune the profiles together with the shader's Low/Potato presets | none | `docs/design/performance-plan.md` |
| **distribution** | Prism instance builder drafted (issue #9) | wait until the pack is finalised | owner | issue #9 |

## Loose ends
- Two texture lines ran today: the harness's QF Textures v1 (Faithful 64x, own art, VNR PBR) and the modded-block pipeline (`tools/textures/rank_modded_blocks.py`, `build_modded_textures.py`, `build_ship.py`: 70 ores on Faithful stone, 90 backports, modded CTM, emissive; `docs/design/textures/modded-blocks.md`). texture-dev folds the modded output into the v1 shipping build; the release builder expects one `C:\qfb	extures\QFTextures.zip`.
- `mods/qf-content/.../debug/AutoShot.java` and `net/QFNetwork.java` have been modified and uncommitted since about 10-23, owner unknown. Commit or revert once the owner is identified.
- `C:\dev\qf-loop` still holds 2 jars locked by a Gradle daemon. Delete the folder later.
