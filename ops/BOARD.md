# Board

Updated 2026-10-25 22:15. Keep each row current: rewrite it, don't append. History goes in `journal/`.

| Track | Status | Next step | Blocker | Detail |
|---|---|---|---|---|
| **shaders** | Round 8 in progress; work in progress in `shaders/QuestForge` (uncommitted) | finish the r008 loops, then the critic, then publish | none | `tracks/shaders.md` |
| **textures** | QF Textures v1 in progress (cc3230e); r008 texture scenes not handed over yet | finish v1 renders, write `r008/texture_scenes.json` + TEXTURES-READY | none | `tracks/textures.md` |
| **render loop** | done: renderq live; scheduled task "QuestForge renderq"; night mode 22:15–08:00 (shot jobs only, 30 fps) | report night power/fans from `C:\qfb\renderq\power.csv` on 10-26 | none | `tools/renderq/README.md` |
| **quests** | WP-5/WP-6 drafts rebuilt to decision 0004 (no parties, no house voice) (6acae6e); act-structure and wp6 brief edits uncommitted | owner review of the drafts | owner | `docs/design/quests/` |
| **balance** | P6–P9 applied (ad7f9f4, 20eef31, 823f683, 53a6284) | retest after the changes (the owner asked that everything be retested) | none | `docs/reference/enchantment-combat-results.md` |
| **world** | plan r13/r14: difficulty layer, rated spawns, tree generator, illustrated map | owner's WorldPainter trial | owner | `docs/design/world/` |
| **server** | the owner's rules applied (decision 0007); Opis, world border, backups and restore | "Who's online" waits on DECISIONS | owner | `docs/setup/hosting-a-server.md` |
| **performance** | win #8 (Decocraft lazy models) live; client profiles full/lite/potato | tune the profiles together with the shader's Low/Potato presets | none | `docs/design/performance-plan.md` |
| **distribution** | Prism instance builder drafted (issue #9) | wait until the pack is finalised | owner | issue #9 |

## Loose ends
- `mods/qf-content/.../debug/AutoShot.java` and `net/QFNetwork.java` have been modified and uncommitted since about 10-23, owner unknown. Commit or revert once the owner is identified.
- `C:\dev\qf-loop` still holds 2 jars locked by a Gradle daemon. Delete the folder later.
