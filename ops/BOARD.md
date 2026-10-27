# Board

Updated 2026-10-25 22:55 (project paused by the owner). Keep each row current: rewrite it, don't append. History goes in `journal/`.

## Pick-up list (paused 2026-10-25, 22:55)

Start here when the project resumes. Each item names its checkpoint or document; a fresh agent can take any of them.

1. **Balance re-test results** (`ops/checkpoints/balance-retest.md`): the census ran detached on node C:\qfs\c4 from 22:37 (results in `C:\qfs\campaign-v3\R-*`, driver log `driver-v3.log`). Triage whether it finished, restore the node's rahovart.json overlay, write §9 of `docs/reference/enchantment-combat-results.md`, then **ask the owner** whether the jar (1.1.0+20261025.20eef315) goes live via `trial.py install` on client and server. Nothing is installed until then.
2. **Fight-duration study** (`ops/checkpoints/balance-effects-table.md`): `docs/design/fight-duration-study.md` is a DRAFT with thin web evidence; the Bastion/factions summon comparison is open. The owner asked for a check-in before any further fight-length change.
3. **Damage-based boss credit** (`ops/checkpoints/quests-hunt-credit.md`): decided, not started. Worktree C:\qfb\hunt-credit\wt.
4. **Server** (`ops/checkpoints/server-rules-docs.md`): slim boot of the /tpa jar (built, not installed), board/track housekeeping, and the sheet-2 cards from the hub proposal and the loaders explainer. Owner actions: op his real account before day one (spawn protection is inert with an empty ops list), gist token for Who's online, firewall rule for 25565, router port forward.
5. **Decisions sheet 2**: `tools/decisions/drafts/s002.json` plus everything in `ops/DECISIONS.md` (rarity plan, fight bands, hub cards, loaders revert cards, voice samples once the Mac writers deliver them, F32 Modded licence, PBR-map licence, rule 10, RCON). Publish with `tools/decisions/sheet.py publish`; the site deploys on push.
6. **Quests (Mac):** voice samples on quests 1, 473, 481 in three or four registers (`docs/design/quests/wp6-writing-brief.md`), then the `[WRITE:]` placeholders in `tools/quests/drafts/DefaultQuests.wp6.json`. Drafts are not applied to `pack/config` until the texts exist.
7. **Textures:** fold the modded-block pipeline (`build_modded_textures.py`, `build_ship.py`, `docs/design/textures/modded-blocks.md`) into the harness's v1 line (`ops/tracks/textures.md`); the release builder expects one `C:\qfb\textures\QFTextures.zip`. Render requests for modded_wall/modded_close and the pane row are in modded-blocks.md §6.
8. **Shader round 8** continues on its own track (`ops/tracks/shaders.md`, renderq); the technique briefs and the reference-photo set are in `docs/design/shaders/research/briefs/`.
9. **Pending measurements that need the client slot** (through renderq when free): full-pack heap after the Decocraft install (`trial.py heap`, expected about 850 MB vs 1,321), `tools/lite-client/measure_profiles.py lite potato`, the Angelica raw TEXTURE_3D probe, the shader cost-isolation round.
10. **Housekeeping:** `C:\qfb\decocraft-lazy\wt` and `C:\dev\qf-loop` hold jars locked by Gradle daemons (delete after `gradlew --stop`); C:\dev\quest-forge-onedrive-retired and the emptied OneDrive folder can be deleted; the relay token expires around 2026-11-22; worktrees C:\qfb\wt-enchant, wt-jukebox, wt-silent can go once their jars are installed or superseded.

| Track | Status | Next step | Blocker | Detail |
|---|---|---|---|---|
| **shaders** | r009 live 2026-10-27, waiting on the owner (ab4ada7 pushed, rounds/r009.json 200; High worst 3.29 ms (r8 4.58), Low 0.86, Potato 0.29; critic 6.5, "not yet: motes in the beam") | the owner's r009 feedback (Edge screenshot not taken) | owner feedback; 4 calls in DECISIONS (Shaders) | `tracks/shaders.md` |
| **textures** | QF Textures v1 in progress (cc3230e); r008 texture scenes not handed over yet | finish v1 renders, write `r008/texture_scenes.json` + TEXTURES-READY | none | `tracks/textures.md` |
| **render loop** | done: renderq live; scheduled task "QuestForge renderq"; night mode 22:15–08:00 (shot jobs only, 30 fps) | report night power/fans from `C:\qfb\renderq\power.csv` on 10-26 | none | `tools/renderq/README.md` |
| **quests** | WP-5/WP-6 drafts to decision 0004 (no parties, no house voice; 6acae6e, 8b29c67); jukebox recipe + jar built (1e836c4), not installed; dead-item census and `qb.py obtain` | Mac writers: voice samples, then the `[WRITE:]` texts; PC: damage-based hunt credit (`ops/checkpoints/quests-hunt-credit.md`) | voice samples: Mac | `ops/tracks/quests.md` |
| **balance** | P1–P9 + P6 on main; jar 1.1.0+20261025.20eef315 built, NOT installed; census re-test running detached since 22:37; effects table + rarity plan committed; fight study DRAFT | §9 results, then the owner's install decision (`ops/checkpoints/balance-retest.md`); finish the fight study (`balance-effects-table.md`) | owner check-in before install | `docs/decisions/0005-enchant-census-proposals.md` |
| **world** | plan r13/r14: difficulty layer, rated spawns, tree generator, illustrated map | owner's WorldPainter trial | owner | `docs/design/world/` |
| **server** | decision 0007 applied and verified on C:\qfs\friends (ba3ec94); rules post, loaders explainer, hub proposal committed; /tpa jar built, not installed; MCHeli assets + Decocraft jar on the server; no world, stopped | slim boot of the /tpa jar; sheet-2 cards (`ops/checkpoints/server-rules-docs.md`) | owner: op real account, gist token, firewall, port forward | `ops/tracks/server.md` |
| **performance** | win #8 (Decocraft lazy models) live; client profiles full/lite/potato | tune the profiles together with the shader's Low/Potato presets | none | `docs/design/performance-plan.md` |
| **distribution** | Prism instance builder drafted (issue #9) | wait until the pack is finalised | owner | issue #9 |

## Loose ends
- Two texture lines ran today: the harness's QF Textures v1 (Faithful 64x, own art, VNR PBR) and the modded-block pipeline (`tools/textures/rank_modded_blocks.py`, `build_modded_textures.py`, `build_ship.py`: 70 ores on Faithful stone, 90 backports, modded CTM, emissive; `docs/design/textures/modded-blocks.md`). texture-dev folds the modded output into the v1 shipping build; the release builder expects one `C:\qfb	extures\QFTextures.zip`.
- `mods/qf-content/.../debug/AutoShot.java` and `net/QFNetwork.java` have been modified and uncommitted since about 10-23, owner unknown. Commit or revert once the owner is identified.
- `C:\dev\qf-loop` still holds 2 jars locked by a Gradle daemon. Delete the folder later.
