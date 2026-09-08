# Emblem icons (2026-09-04, Mac)

Source: the live skull-on-anvil `emblem_corner.png` (336x357 px of usable emblem), padded onto a transparent
1024 canvas with a soft drop shadow (`make_icons.py` output in `out/`).

Installed:
- Prism instance icon: `~/Library/Application Support/PrismLauncher/icons/questforge.png` (512 px). Prism may need
  a restart to show it.
- Resource pack icon: `pack.png` inside the live `resourcepacks/QuestForge.zip` (256 px).
- CustomMenu window icon (Windows taskbar via `Display.setIcon`): `icon16/32/64.png` + `icon.icns` inside the live
  `mods/CustomMenu.jar`.
- macOS dock icon for the fallback launcher: `-Xdock:icon=~/.questforge/QuestForge.icns -Xdock:name="Quest Forge"`
  added to `launch-questforge-mac.command`.

NOT done automatically (Prism was running and rewrites instance.cfg itself): the same dock flags for Prism launches.
Add in Prism: Edit Instance -> Settings -> Java arguments, append
`-Xdock:icon=/Users/suaz/.questforge/QuestForge.icns -Xdock:name=QuestForge`

Backups of the replaced files are in `backup-before/`.
