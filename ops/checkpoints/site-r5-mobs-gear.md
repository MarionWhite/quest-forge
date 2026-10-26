# site-r5-mobs-gear (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: `site/lib/mc/*`, `tools/site/gen_vanilla_models.py`, `tools/site/gen_orespawn_models.py`.
Previous state: `ops/checkpoints/site-mobs.md`.

## Owner's words (2026-10-26)
- "King bob doesn't have armor, I'm not sure if that is intentional." It is not: drop 179 equips
  OreSpawn Queen armor and the Queen Battle Axe, and the Bob family wear enchanted diamond armor
  with diamond swords.
- On the Krypt Silverfish scare: "the silverfish textures weren't properly loaded." The scares
  agent also found the library Silverfish rendering as tan slabs.

## STATUS: done (2026-10-26). Sheet: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/r5/mobs-gear/final/sheet.png

## Done means
- [x] **Equipment:** `makeMob(id, { equipment })` accepts the drop's `equipment` array, using the
  same format as the `actions[].equipment` field in `site/lucky/data/lucky.json`. It renders:
  - Armour: the 1.7.10 armour layers (the `models/armor/*_layer_1/2.png` textures, the
    ModelBiped scaled 1.0 and 0.5, as RenderBiped does) on every biped-style mob. That covers
    zombie, pigman, skeleton, giant and Steve.
  - Enchanted pieces: the enchantment glint.
  - OreSpawn armour: its own textures from the jar, e.g. Queen armour.
  - Held items: the 1.7.10 third-person transform from `RenderBiped`, for swords, axes and the
    Queen Battle Axe.
  Feature-detectable: export `MOB_FEATURES.equipment = true`.
- [x] **Silverfish:** the 1.7.10 silverfish model and texture, with its segments animated,
  correct in the lineup and at small scale.
- [x] Lineup frame: Zombie, Giant (scaled) and Skeleton in diamond armour, King Bob in Queen
  armour with the axe, and Silverfish front and 3/4.
- [x] `python3 -I tools/site/check_sounds.py` exits 0.

## Done
- Equipment API committed (milestone 1): `makeMob(id, { equipment, enchanted })`, `MOB_FEATURES.equipment`,
  `EQUIP_PRESETS`, `parseEquipment`. New `site/lib/mc/equipment.js`; textures in `tex/armor`, `tex/items`, `tex/misc`.
  `equipment` = the drop's `actions[].equipment` array. Plain strings: glint on for `minecraft:` ids (every vanilla
  piece in the drops is enchanted), off for OreSpawn; pass `{id, ench:false}` to override or `enchanted: false`.
  Applies to Zombie, Giant, PigZombie, ZombieVillager, Skeleton, WitherSkeleton, Steve (others ignore it).
  `m.equipment = {applied, slots, held}`.
- Lineup: `?ids=Zombie@diamond,Zombie@queen,Zombie@queenarmor`.
- Facts: vanilla 1.7.10 RenderGiantZombie draws NO armour or held item (done anyway, per the owner's list).
  Queen Battle Axe model renders at scale 1.0 (blocks), x0.35: about 7 blocks long in hand, per the bytecode.
- Silverfish: model and texture are exact (wing dots are sparse by design); anim speed fixed (was 0.3x).
  Krypt swarm uses its own box mesh in `site/graves/scares/cuts1.js` (see Requests).

## Requests
- scares / krypt-more: `site/graves/scares/cuts1.js` `silverfishMesh()` builds grey boxes; use the library
  model instead (`makeMob('Silverfish')`) for real texture and segment wiggle.
- lucky-accuracy: pass `equipment: action.equipment` to `makeMob` (fx.js spawnMob, reel.js) and guard with `MOB_FEATURES.equipment`.
