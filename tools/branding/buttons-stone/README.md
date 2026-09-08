# Stone buttons + 4K menu background (2026-09-04 evening, Mac)

Installed into the live Prism instance
(`~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/`),
both `resourcepacks/QuestForge.zip` and `mods/CustomMenu.jar`:

1. `assets/custommenu/background.jpg` — 3840x2160 LANCZOS upscale of the shipped 1920x1080
   (same picture, no new detail) plus `background.jpg.mcmeta` `{"texture":{"blur":true,"clamp":true}}`
   so the menu draws it bilinear instead of nearest-neighbour. Script: `../_bg-4k-20260904/install_bg4k.py`.
2. Twelve button plates from `make_buttons.py` (procedural dark stone, rugged alpha edges, deep fissures
   dark when idle, amber-lit `*over.png` hover state, Georgia Bold label baked in), 1800x240 big /
   900x240 small, each with a `.mcmeta` blur flag.

Why the labels are baked in: CustomMenu draws its background quad *after* `GuiMainMenu.drawScreen`,
so the vanilla button plates and labels are covered; only the plate textures drawn afterwards are visible.

Smoke test: scripted launch via `launch-questforge-mac.command` at 20:39 with the 4K background installed
reached the title screen (JourneyMap palette generated 20:44:16), no texture errors, exit code 0, no crash
report. The buttons were installed after that launch and have not yet been seen in-game.

## Revert

```
cp backup-before-20260904-204606/QuestForge.zip "$INST/resourcepacks/"   # buttons only
cp backup-before-20260904-204606/CustomMenu.jar "$INST/mods/"
cp ../_bg-4k-20260904/backup-before/QuestForge.zip "$INST/resourcepacks/"  # back to 1920 bg + old buttons
cp ../_bg-4k-20260904/backup-before/CustomMenu.jar "$INST/mods/"
```

Re-render / tweak: edit `make_buttons.py`, run `python3 make_buttons.py` (preview in `out/preview_menu_crop.png`),
then `python3 make_buttons.py --install`.
