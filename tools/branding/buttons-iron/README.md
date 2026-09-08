# Forged-iron animated main-menu buttons (installed 2026-09-04, Mac)

Replaces the stone plates with chamfered blackened-iron lettering that heats to amber on hover,
blooms, and throws floating embers. The hover animation is real per-frame rendering, not a texture swap.

## Pieces
- `make_iron_buttons.py` -> `out/`
  - `<name>.png` / `<name>over.png` (identical) — the idle plate: iron letters, lavender top rim,
    ember under-light, baked ground shadow. 1800x240 big / 900x240 small.
  - `out/qf/<name>_heat.png` — emissive amber letters (additive, alpha = letter mask)
  - `out/qf/<name>_glow.png` — amber bloom around the letters (additive)
  - `out/qf/<name>_mask.png` — letter mask, used to pick ember spawn points
  - `out/preview_idle.png` — composite over the real background
- `java/qf/menu/QFButtons.java` — the runtime. Per plate it tracks an eased hover value, draws the heat
  layer with a front that rises from the bottom of the letters, adds the bloom, and simulates embers
  (spawn rate 0.35/s idle, +55/s hovered) that drift up, wobble, cool from amber to red and fade.
  On any Throwable it disables itself and the plain plates keep drawing.
- `java/PatchMenu.java` — ASM. In `mainmenuserver.MainMenuFix.func_73863_a` (drawScreen) the mod draws
  the plates twice; only the second pass is visible (the first is covered by its full-screen background
  quad). The 4th and 5th `drawTexturedModalRect(IIII)` calls — the two in the second loop, at offsets
  568 and 593 — become `QFButtons.drawButton(MainMenuFix,IIIII)`, with `ILOAD 11` pushed first so the
  helper receives the mod's own `buttonTextures` index. That index, not geometry, identifies the button:
  the array is `{publicserverover, publicserver, singleover, single, multiplayerover, multiplayer,
  modsover, mods, null, null, optionsover, options, quitover, quit}` (indices 8–9 skip the
  language button), so name = NAMES[j/2] with a hole: publicserver, single, multiplayer, mods,
  null, options, quit.
- `java/MenuHarness.java` — stand-alone LWJGL preview (`out/preview_anim_f*.png`), hovers Multiplayer
  then Quit via the `QFButtons.debugMouse` test hook.
- `java/stubs/` — compile-time stubs for `Gui`, `GuiScreen`, `MainMenuFix`.

## Build / preview / install
```
python3 make_iron_buttons.py
JH=/Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home   # must be JDK 8: ByteBuffer.flip()
"$JH/bin/javac" -cp lwjgl.jar:asm-all-5.0.3.jar -d build java/stubs/**/*.java java/qf/menu/QFButtons.java java/PatchMenu.java java/MenuHarness.java
"$JH/bin/java" -Djava.library.path=<instance>/bin/natives -cp build:<assets>:lwjgl.jar:lwjgl_util.jar MenuHarness out <background.jpg> out/preview_anim
"$JH/bin/java" -cp build:asm-all-5.0.3.jar PatchMenu <backup CustomMenu.jar> out/CustomMenu-patched.jar build/qf/menu/QFButtons.class \
    assets/custommenu/single.png=out/single.png ... assets/custommenu/qf/single_heat.png=out/qf/single_heat.png ...
```
PatchMenu asserts it saw exactly 5 plate draws and redirected 2; it fails loudly if CustomMenu changes.

## Installed
- `<instance>/mods/CustomMenu.jar` — patched class + `qf/menu/QFButtons.class` + all 12 plate PNGs + 18 `qf/` layers.
- `<instance>/resourcepacks/QuestForge.zip` — the 12 plate PNGs (the pack overrides the jar, so both must match).
  The `.png.mcmeta` blur/clamp entries were left in place.

## Revert
Copy `backup-before-20260904-213020/CustomMenu.jar` and `QuestForge.zip` back over the live files.
