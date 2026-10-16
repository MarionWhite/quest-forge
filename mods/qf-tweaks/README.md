# QuestForgeTweaks

A Forge 1.7.10 coremod that makes **every BetterQuesting quest readable at any
time, while prerequisites still gate completion**.

Status: **source complete, not yet compiled.** No JDK exists on this machine —
see "Building" below.

---

## The problem

In BetterQuesting 3.0.328, clicking a locked quest does nothing, so players
cannot read ahead to see what a quest will ask of them.

The cause is in
`betterquesting/api2/client/gui/controls/PanelButtonQuest` (12,221 bytes, class
major version 52). The final statement of the constructor is:

```java
this.setActive(QuestingAPI.getAPI(ApiReference.SETTINGS).canUserEdit(this.player) || !lock);
```

`lock` is true when `quest.getState(uuid)` returns `EnumQuestState.LOCKED`.
`PanelButton.onMouseRelease` only broadcasts a `PEventButton` when `isActive()`
is true, so `GuiQuestLines.onButtonPress` — which constructs `new GuiQuest(...)`,
the detail screen — never runs for a locked quest. The click is swallowed one
layer below the code that would show the description.

## The fix

Force that call to `setActive(true)`.

Rather than matching the exact instruction pattern that computes the boolean,
the transformer rewrites the **argument at the call site**. Immediately before
the `INVOKEVIRTUAL setActive(Z)V` in `<init>` it inserts:

```
POP        ; discard whatever boolean was computed
ICONST_1   ; push true
```

The stack at the call is `[..., this, boolean]`; `POP` + `ICONST_1` restores it
to `[..., this, 1]`. This is independent of how the boolean was produced, so it
survives recompiles and minor BetterQuesting updates much better than matching a
specific opcode sequence would.

Frames are recomputed with `ClassWriter.COMPUTE_FRAMES`. `getCommonSuperClass`
is overridden to fall back to `java/lang/Object` rather than loading classes
through the transforming classloader, which is a classic source of
`ClassNotFoundException` and deadlocks during coremod startup.

## Why gating still holds

`GuiQuest`, the detail screen, has **no lock check at all** — it renders name,
description, tasks and rewards unconditionally. Enforcement is entirely
server-side and is untouched by this coremod:

- `QuestInstance.detect()` re-tests `isUnlocked(playerID)` before allowing any
  task progress, so a locked quest's Detect/Submit button looks pressable but
  does nothing.
- `NetQuestAction.claimQuest` re-checks `canClaim` server-side, and `canClaim`
  requires an existing completion record.
- `EventHandler.onLivingUpdate`'s polling loop skips active quests failing
  `isUnlocked`.

The transformer touches **only** `PanelButtonQuest`'s constructor. It does not
modify `QuestInstance`, `NetQuestAction`, `GuiQuest`, `QuestCache` or
`QuestSettings`, and every other class passes through untouched.

Do **not** "fix" this instead by setting `questSettings.editMode: 1` or
`lockedProgress: 1` on quests. `editMode: 1` makes `QuestInstance.detect`
auto-complete any quest whose tasks pass; `lockedProgress: 1` exposes locked
quests to the Submit Station and lets them accept hand-ins. Both break gating.
All 145 quests must stay at `lockedProgress: 0` and `questSettings.editMode`
must stay `0`.

## It is deliberately invisible

`PanelButtonQuest` calls `setTextures(btnTx, btnTx, btnTx)` with the same
texture for all three states, already chosen from the locked preset, so
activating the button does not change its appearance. Locked quests keep their
greyed frame. That is intended — don't "improve" it.

---

## GraveStones beam under shaders

`GraveBeamTransformer` puts `if (ShaderState.active()) return;` at the head of
`TileEntitySpecialRendererGrave.renderBeam` in GraveStones.

A grave that still holds items draws a 256-block column around itself with
texturing off, no UVs, depth writes off and additive blending at 11% alpha.
Without shaders that is a faint glow. Sildur's Vibrant is deferred and its
G-buffer cannot blend, so the same quads come out as an opaque column sampling
whatever texture is bound. You see a dark, noisy pillar that blacks out the scene
behind the gravestone. None of the beam can be drawn correctly in a G-buffer, so
it is skipped while a pack is active and left alone otherwise. `ShaderState`
asks OptiFine's `Config.isShaders()` reflectively on every call, so switching
packs in-game takes effect immediately.

Look for `Transform applied: GraveStones renderBeam skips while a shader pack is
active` in `latest.log`.

## GraveStones and Baubles on a server

`GraveBaublesTransformer` fixes a loop bound in GraveStones'
`GravestoneEventHandler`. When a player dies, GraveStones moves their four
Baubles into the grave and then resyncs slots 0 to 6, a loop copied from its
seven-slot RPG Inventory code. Baubles sends every player a sync for "slot 4",
and each client throws `ArrayIndexOutOfBoundsException` in the packet handler
and is disconnected. On a dedicated server, one death kicks everyone.
Singleplayer never shows it, because Baubles skips the send when client and
server share a process. The patch turns the `BIPUSH 7` after the
`"syncSlotToClients"` lookup into a 4.

This is the one patch here that runs on the server, so the dedicated server
must carry QuestForgeTweaks too. Look for `Transform applied: GraveStones now
resyncs 4 Baubles slots` in the server log.

## Morph under OptiFine E7

`MorphOptifineTransformer` makes the stock `Morph-Beta-0.9.3.jar` usable with
OptiFine E7 and shaders. Install the stock jar. The hand-patched copies in
`mods_disabled\` and the September work folder are superseded. There are two
client bugs:

- **Killing a new mob kicked you** with "critical exception handling a packet
  on channel Morph". To force a model recompile, Morph calls
  `GLAllocation.deleteDisplayLists` on lists that are not in GLAllocation's map
  under OptiFine. That throws a NullPointerException. All three calls
  (`ModelHelper` twice, `ModelMorph` once) now go to
  `MorphFix.deleteDisplayList`. It keeps vanilla's behaviour when that works,
  and otherwise frees the one list with `glDeleteLists`.
- **Morphing froze the game.** Morph's `RenderHandEvent` handler cancels the
  event and calls `EntityRenderer.renderHand` itself to draw the mob's arm.
  OptiFine's `renderHand` posts `RenderHandEvent` again, so the handler
  re-entered itself until it overflowed the stack. OptiFine caught that and
  logged a thousand-line trace every frame, which pinned the game near 0 fps and
  never produced a crash report. In singleplayer this looks like the server
  dying. The handler is now renamed and wrapped. A re-entrant call returns
  without cancelling, so OptiFine's inner `renderHand` draws the arm Morph
  swapped in. The guard is cleared in a `finally`.

Diagnosed on 2026-10-16 with `jstack` on a frozen scripted client. With this
patch, a scripted run on the full pack with Sildur's Vibrant passes all of these
steps: kill, acquire, morph, F5, inventory, pause menu, a second species, and
demorph. Look for three `Transform applied: morph.` lines in `latest.log`. A
dedicated server logs none, because FML strips the client handler first; that
is expected.

---

## Building

**Requires a JDK.** The instance's `C:\Program Files\Java\jre1.8.0_241` is a
runtime only and has no `javac`. As of the last check there was **no JDK
anywhere on this system** — no `javac.exe`, no `tools.jar`, no Gradle, no
Eclipse compiler, and `JAVA_HOME` was unset.

Install a JDK 8 (Adoptium Temurin 8 is the usual choice), then:

```
build.bat
```

`build.bat` locates a JDK via `JAVA_HOME` or the usual install paths, compiles,
packages, verifies the manifest, and installs into `%APPDATA%\.crazycraft4\mods\`.

The underlying commands are:

```
javac -source 1.7 -target 1.7 -nowarn ^
  -bootclasspath "<JDK>\jre\lib\rt.jar" ^
  -cp "%APPDATA%\.crazycraft4\bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar;^
       %APPDATA%\.crazycraft4\bin\lib\launchwrapper-1.11.jar;^
       %APPDATA%\.crazycraft4\bin\lib\asm-all-5.0.3.jar;^
       %APPDATA%\.crazycraft4\bin\lib\log4j-api-2.0-beta9.jar;^
       %APPDATA%\.crazycraft4\bin\minecraft.jar" ^
  -d build src\com\questforge\*.java

jar cfm QuestForgeTweaks-1.0.jar manifest.txt -C build .
```

Targeting 1.7 bytecode is the safest option here; `TEST-LAUNCH.bat` passes
`-XX:+UseSplitVerifier` and `-XX:+FailOverToOldVerifier`, so older-version
bytecode is fine.

Everything compiled against is already in the instance — Forge 10.13.4.1558
bundles ASM under `org.objectweb.asm`, so there is no external dependency to
fetch.

## Manifest

```
Manifest-Version: 1.0
FMLCorePlugin: com.questforge.QuestForgeCore
```

`FMLCorePluginContainsFMLMod` is **deliberately absent** — there is no `@Mod`
class in this jar, and the mere presence of that attribute makes FML scan the
jar as a mod container. There is direct precedent for getting this wrong in this
pack: `ColorfulMobsMC.jar` carried a stale `FMLCorePlugin` line for a class it
did not contain, which produced a `ClassNotFoundException` at startup.
`build.bat` verifies `com/questforge/QuestForgeCore.class` is actually present
in the jar before installing.

## Verifying it works

After launching, `logs\latest.log` should contain exactly one line like:

```
[QuestForgeTweaks] Transform applied: PanelButtonQuest.<init> now calls setActive(true); locked quests are readable (12221 -> NNNNN bytes).
```

If the expected pattern is ever missing (e.g. after a BetterQuesting update),
the transformer logs a clear warning and returns the original bytes rather than
throwing. A coremod that throws during class loading takes the whole game down,
so it fails soft by design — you would see:

```
[QuestForgeTweaks] Expected pattern not found: no setActive(Z)V call in ...
```

Then in game:

1. Open the quest book and click a deep locked quest. `Railcraft: The Tunnel
   Bore` (quest 130) is a good probe — it is five prerequisite links deep. The
   detail screen should open and the description should scroll.
2. The button should still *look* locked.
3. **Claim** should be greyed out in that detail view.
4. Pressing **Detect/Submit** on the locked quest will look pressable but
   **nothing should happen** — no completion toast, no state change, task
   counter stays at zero. This is the most important check; it proves gating
   survived.
5. The nine secret quests (IDs 71, 72, 73, 75, 76, 141, 142, 143, 144) should
   still be absent from the map.

---

## Fallback: direct jar patch

If a coremod is ever undesirable, the same behaviour can be had by patching
`mods\BetterQuesting-3.0.328.jar` directly. In `PanelButtonQuest`, the relevant
bytecode tail of `<init>` is, with verified file offsets:

```
 368 (file 0x2354) ifne -> 376      ; if canUserEdit, jump to "true"
 371 (file 0x2357) iload 9          ; push 'lock'
 373 (file 0x2359) ifne -> 380      ; if locked, jump to "false"   <-- the block
 376 (file 0x235C) iconst_1
 377 (file 0x235D) goto -> 381
 380 (file 0x2360) iconst_0
 381 (file 0x2361) invokevirtual PanelButtonQuest.setActive(Z)V
```

The five bytes at file offsets `0x2357`–`0x235B` are `15 09 9A 00 07`.
Replacing them with five `nop` (`00 00 00 00 00`) makes both paths fall through
to `iconst_1`. Offsets stay identical, so the existing `StackMapTable` remains
valid.

This is recorded only as a fallback. **The coremod is preferred** because it
survives jar replacement and pack updates, and because it leaves
`mods\BetterQuesting-3.0.328.jar` untouched (SHA-256
`1BE0BDCDEB916D1A47D4CC89A4C3ACCDDF58329B60B58BAEDDC06F41C156D363`).
