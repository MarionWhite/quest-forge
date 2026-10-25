# Installing the Angelica client

The Angelica client is the same Quest Forge pack with a different renderer:
[Angelica](https://github.com/GTNewHorizons/Angelica) (Celeritas chunk
rendering plus a backport of the Iris shader loader) instead of OptiFine E7.
With shaders it measured 1.7 to 3.9 times E7's frame rate, and it runs
Complementary Unbound, which E7 cannot. Why the pack moved and what it costs:
[`../design/angelica-decision.md`](../design/angelica-decision.md).

**The OptiFine E7 client stays supported.** Use it on a PC whose graphics
cannot do OpenGL 3.3, which Angelica requires: Intel HD 2000/3000 (2011) and
older. Both clients can play on the same server (see below).

## What is different from the E7 client

| | E7 client | Angelica client |
|---|---|---|
| Forge | 10.13.4.1558, hand-patched jar | 10.13.4.1614, stock jar |
| Renderer mods | OptiFine E7, FastCraft, BetterFps | Angelica 2.2.33, UniMixins 0.3.2, GTNHLib 0.11.54 |
| CodeChicken | GTNH CodeChickenCore 1.4.22 (CCL merged in), since 2026-10-18 | the same |
| Loading screen and splash music | from the patched Forge jar | from QuestForgeTweaks (`SplashTransformer`); looks and sounds the same |
| Shader packs | Sildur's Vibrant, Enhanced Default | the same, plus Complementary Unbound |
| Zoom | C | C |
| Shader keys | Options -> Video Settings -> Shaders | F4 toggle, F8 pick a pack, F9 reload |
| Lost | | Better Snow, OptiFine's Smooth FPS, Fast Render, Fast Math |
| Not used | | Hodgepodge, ArchaicFix (never add them; see below) |

The jar list, with hashes and download links, is
[`tools/angelica-client/manifest.json`](../../tools/angelica-client/manifest.json).
The pack's own three jars (QuestForgeTweaks, QuestForgeContent, TransformersMod)
are the same builds for both clients.

## Install on Windows (pack folder layout, like TEST-LAUNCH.bat)

You need a working E7 install first (the client-instance release; see
[`transfer-from-windows.md`](transfer-from-windows.md)). The script copies it
into a new folder and changes only the new copy.

1. Download the three jars in `manifest.json` (`mods_add`) and the Forge 1614
   universal jar (`forge.add`) into one folder, e.g. `C:\QuestForge-downloads`.
   The script checks each SHA-1 and refuses a jar that differs.
2. Optionally download Complementary Unbound
   (`https://modrinth.com/shader/complementary-unbound`, r5.9.3 was tested).
3. Run, with Python 3.10 (`py -3.10 -I`):

   ```
   py -3.10 -I tools\angelica-client\build_angelica_client.py ^
       --from "%APPDATA%\.crazycraft4" --to "%APPDATA%\.qf-angelica" ^
       --jars C:\QuestForge-downloads ^
       --add-shaderpack C:\QuestForge-downloads\ComplementaryUnbound_r5.9.3.zip
   ```

   `--from` must already run GTNH CodeChickenCore 1.4.22 (any E7 install updated
   on or after 2026-10-18; `source_must_have` in the manifest). The script
   refuses one that still has stock `CodeChickenCore.jar` or CodeChickenLib.
   `--from` is only read. Add `--with-saves` to copy your worlds,
   `--pack-jars DIR` to use freshly built pack jars, `--shader off` to start
   with shaders off. On one drive the big files (assets, mods, resources) are
   hard links, so the copy costs little disk.
4. Start `%APPDATA%\.qf-angelica\LAUNCH-ANGELICA.bat`. It picks the heap from
   your RAM (3 GB on 8 GB, up to 7 GB on 32 GB; `set QF_XMX=6144M` overrides)
   and refuses to start if OptiFine or the 1558 Forge jar is still there.

**The first start needs internet.** Angelica's library loader (FalsePatternLib)
downloads about 26 MB of libraries (fastutil, JOML, Brigadier, the
jvmdowngrader stubs) into `falsepattern\` and logs `FalsePatternLib is
downloading dependencies`. After that it starts offline. To set up a PC with no
internet, copy `falsepattern\` from a client that has started once. Its one
"problem reading the entry module-info.class ... joml" error at start-up is
harmless (FML scanning a Java 9 file in that jar).

Like `TEST-LAUNCH.bat`, `LAUNCH-ANGELICA.bat` starts the game offline: fine for
singleplayer and LAN, not for the online-mode friends' server.

What the script changes in the copy:

- `bin\lib`: Forge 1558 out, Forge 1614 in.
- `mods`: OptiFine, FastCraft and BetterFps out; Angelica, UniMixins and GTNHLib
  in. Hodgepodge and ArchaicFix are removed if present. CodeChickenCore is not
  touched: the E7 pack already runs GTNH CodeChickenCore 1.4.22.
- `config\angelica-options.json`: `vsync_mode: OFF`, so Angelica does not pace
  frames to the monitor (E7 ran with vsync off too; `maxFps` in Options still
  caps it).
- `config\angelica-modules.cfg`: `showSplashMemoryBar=false`, so Angelica's
  memory bar does not cover the loading screen.
- `config\splash.properties`: `enabled=true`.
- `options.txt`: Angelica's zoom on C; Iris toggle/pick/reload on F4/F8/F9.
  Angelica ships all four unbound. C is also `key.prev` in this pack, the same
  overlap the E7 client has with OptiFine's zoom.
- `config\shaders.properties`: the shader pack the E7 copy used (Angelica
  ignores `optionsshaders.txt`).

## Install in Prism Launcher (the friends' server)

1. Right-click the Quest Forge instance -> **Copy Instance**, call it
   "Quest Forge (Angelica)". Keep the E7 instance as the fallback.
2. In the copy: **Edit -> Version**, select Forge, **Change version**, pick
   **10.13.4.1614**. This replaces the patched 1558 jar with stock 1614; the
   loading screen and music still work because QuestForgeTweaks carries them.
3. **Edit -> Mods**: disable or delete `OptiFine_1.7.10_HD_U_E7.jar`,
   `fastcraft-1.25.jar` and `BetterFps-1.0.1.jar`. Add the three jars from
   `manifest.json` (`mods_add`). The instance must already have
   `CodeChickenCore-1.4.22.jar` and no `CodeChickenCore.jar` or
   `1.7.10/CodeChickenLib-*.jar`. If it has them, it predates 2026-10-18: make
   that swap in the E7 instance first.
4. Open the instance folder (`.minecraft`) and copy in
   `tools/angelica-client/overlay/config/angelica-options.json` and
   `angelica-modules.cfg` (into `config\`; if Angelica already wrote them, set
   just those keys). Set the keys in `tools/angelica-client/overlay/options-keys.txt`
   in `options.txt`, or bind zoom and the Iris keys in Controls.
5. Java settings stay as in [`jvm-args.md`](jvm-args.md) (Java 8, 64-bit).

## Playing on the server

- The server must **not** run Hodgepodge, ArchaicFix or GTNHLib. With them,
  only clients that also run them can join, and an E7 client cannot run GTNHLib
  at all. An Angelica client with Hodgepodge in its own mods is kicked by a
  server without it (`packet 53` mismatch).
- Everyone, server included, runs **GTNH CodeChickenCore 1.4.22** instead of
  stock CodeChickenCore + CodeChickenLib, since 2026-10-18. With a mismatch,
  NEI's packets differ and the client is kicked 5 s after login. E7 clients run
  the same jar and keep OptiFine. (`docs/setup/hosting-a-server.md`,
  "CodeChickenCore", covers it.)
- The friends' server is in **online mode**: join from a launcher that signs in
  with a real account (Prism). `LAUNCH-ANGELICA.bat` is offline and is refused
  there (hosting guide, "Online mode").
- The server's pack check compares the versions of mods both sides have
  (QuestForgeTweaks, QuestForgeContent, qf-commands...). Use the pack jars the
  server was built from; Angelica's own jars are client-only and ignored.

## Settings

- **Shaders.** F8 opens the shader-pack screen; F4 turns the current pack on
  and off. Complementary Unbound is the recommended pack. Sildur's Vibrant and
  Enhanced Default also work.
- **Frame rate.** Vsync is off, so the game runs above the monitor's refresh
  rate unless Options -> Video Settings -> Max Framerate caps it. The log line
  `Frame pacing: vsync off` confirms it; `vsync 240Hz` means something turned
  vsync back on (Video Settings -> VSync, or `vsync_mode` in
  `config\angelica-options.json`). Menus run at 30 fps, as in vanilla.
- **Weaker PCs.** `tools/lite-client/apply-profile.ps1 -Profile lite|potato`
  applies the Angelica-era profile: Celeritas settings, the QuestForge pack's
  Low or Potato preset, client-only jars set aside, and the heap for the PC's
  RAM ([`performance-tuning.md`](performance-tuning.md),
  [`../../tools/lite-client/README.md`](../../tools/lite-client/README.md)).

## Checking that it worked

In `logs\latest.log`:

```
[QuestForgeTweaks] Transform applied: cpw.mods.fml.client.SplashProgress$3: full-screen mural; frame hook; textured bars; 2 text colour(s);
[QFSplash] first splash frame at ... textured bars on, chant PLAYING ...
[QFSplash] 4000 ms after the splash: chant none, menu PLAYING ...
Frame pacing: vsync off
[QuestForge] shader pack ON (Angelica/Iris): record case and jukebox take the shader-safe path
```

The last line appears the first time a jukebox or record case is drawn with a
pack on. `textured bars OFF (plain Forge boxes)` means `resources\` is missing
from the game folder.

## Known gaps

- Psychedelicraft's drug-vision overlays do not compile under Angelica
  ("Error creating shader" twice per boot), so drugs have no screen effect.
  Undecided whether to fix (2-4 h) or accept.
- A few things only a person can check: portals, transforming, MCHeli rotors,
  door swings, Morph by hand. See [`angelica-hand-test.md`](angelica-hand-test.md).
