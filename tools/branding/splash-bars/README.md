# Textured splash bars + HD splash font (installed 2026-09-04 21:11, Mac)

## What runs
- `qf/splash/QFBars.class` was added to the patched Forge jar and `SplashProgress$3.drawBar` was rewritten
  (ASM, `java/PatchSplash.java`): its three `drawBox` calls go to `QFBars.drawBox`, and the first `glScalef`
  goes to `QFBars.beginBar`. Everything else in the jar (buffer patch, emblem pulse) is untouched.
- `QFBars` draws: a soft plaque behind title+bar, a tapered stone trough, a scrolling magma fill with a glowing
  head, and a rim overlay; the title is drawn 2.6x instead of 2x and nudged up. On any error it falls back to
  Forge's plain boxes.
- Textures: `<instance>/resources/assets/minecraft/textures/gui/title/splash/{trough,rim,magma,head,plaque}.png`
- Font: `<instance>/resources/assets/minecraft/textures/font/ascii.png` (Georgia Bold, baked outline+shadow),
  `config/splash.properties` `font=0xFFE2B0`.
- Installed into BOTH live Forge copies: Prism `instances/Quest Forge/libraries/forge-...universal.jar` and the
  fallback `minecraft/bin/lib/forge-...universal.jar` (2,966,699 bytes each).

## Regenerate / preview / reinstall
```
python3 make_bar_textures.py                      # -> out/*.png, out/ascii.png
javac -cp lwjgl.jar:launchwrapper.jar:asm-all.jar -d build java/qf/splash/QFBars.java java/PatchSplash.java java/BarHarness.java
java -cp build:... BarHarness <gameDir-with-textures> <mural.png> out/ascii.png out/preview_splash.png 0xFFE2B0 1280 720
java -cp build:asm-all.jar PatchSplash <backup forge.jar> out/forge-patched.jar build/qf/splash/QFBars.class
```
(see the shell history in this session for the exact classpaths under Prism's `libraries/`).

## Revert
Copy `backup-before-<stamp>/forge-prism.jar` back to Prism's `libraries/forge-1.7.10-10.13.4.1558-1.7.10-universal.jar`
and `forge-binlib.jar` to `minecraft/bin/lib/…`, restore `splash.properties`, delete the `splash/` texture folder and
`textures/font/ascii.png` in `resources/`.
