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

## Done means
- [ ] **Equipment:** `makeMob(id, { equipment })` accepts the drop's `equipment` array, using the
  same format as the `actions[].equipment` field in `site/lucky/data/lucky.json`. It renders:
  - Armour: the 1.7.10 armour layers (the `models/armor/*_layer_1/2.png` textures, the
    ModelBiped scaled 1.0 and 0.5, as RenderBiped does) on every biped-style mob. That covers
    zombie, pigman, skeleton, giant and Steve.
  - Enchanted pieces: the enchantment glint.
  - OreSpawn armour: its own textures from the jar, e.g. Queen armour.
  - Held items: the 1.7.10 third-person transform from `RenderBiped`, for swords, axes and the
    Queen Battle Axe.
  Feature-detectable: export `MOB_FEATURES.equipment = true`.
- [ ] **Silverfish:** the 1.7.10 silverfish model and texture, with its segments animated,
  correct in the lineup and at small scale.
- [ ] Lineup frame: Zombie, Giant (scaled) and Skeleton in diamond armour, King Bob in Queen
  armour with the axe, and Silverfish front and 3/4.
- [ ] `python3 -I tools/site/check_sounds.py` exits 0.

## Done
(nothing yet)
