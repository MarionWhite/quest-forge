# Morph + OptiFine E7 — research and a work-folder patch

**Live instance was not changed.** Morph stays in `mods_disabled\`. iChunUtil 4.2.2, OptiFine E7, Fast Render, shaders, TEST-LAUNCH.bat, CodeChickenCore, NEI, DefaultQuests, splash, OpenBlocks.cfg are untouched.

Work folder: `C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_morph-optifine-20260904\`

Testable artifact: `Morph-Beta-0.9.3-QF-OPTIFINE.jar` (copy only when you want to test).

---

## Root cause (plain language)

Two separate OptiFine E7 bugs, both in Morph’s *client renderer*, not in gameplay logic.

### 1. Kill-acquire kick — `deleteDisplayLists` NPE

When you kill a new mob, Morph builds a copy of that mob’s model for the black “absorb” animation (`ModelHelper.getModelCubesCopy` → `ModelMorphAcquisition` → `PacketMorphAcquisition`). To force a clean compile it does:

```java
if (cube.compiled) {
    GLAllocation.deleteDisplayLists(cube.displayList);
    cube.compiled = false;
}
```

Vanilla / OptiFine `GLAllocation.deleteDisplayLists` is:

```java
GL11.glDeleteLists(id, mapDisplayLists.remove(id).intValue());
```

On OptiFine **HD U D7 and newer** (this pack is **E7**, which also adds shaders) that map often does **not** contain the list Morph is deleting — displayList can be 0, or OptiFine compiled the model another way. `remove` returns null → **NPE** on the packet thread → “fatal error, connection terminated.” You keep the morph after reconnect; the next *new* species kicks you again.

Same delete also runs in `compileRenderableModels` (morph-in model build) and every frame of `ModelMorph.updateCubeMorph` during the 60-tick transform.

This is the widely documented 1.7.10 Morph+OptiFine crash:
- [iChun/Morph#836](https://github.com/iChun/Morph/issues/836)
- [iChun/Morph#848](https://github.com/iChun/Morph/issues/848)
- [iChun/Morph#942](https://github.com/iChun/Morph/issues/942)
- [sp614x/optifine#5106](https://github.com/sp614x/optifine/issues/5106) — sp614x confirmed the NPE in `deleteDisplayLists` and noted no OptiFine class is on the stack (the *call* is Morph; the *map* is what E7 changed).

Community “fix” for years: **downgrade to OptiFine HD U D6**. D6 has **no shader support**. Unusable here.

### 2. Morph-in freeze — `onRenderHand` recursion

After kill-acquire was NOP’d, becoming a morph still froze. That is **not** another display-list NPE.

Morph `EventHandler.onRenderHand` (priority HIGHEST), if `handRenderOverride == 1` and you are morphed:

1. `event.setCanceled(true)`
2. Swap the player renderer for `renderHandInstance` (morph arm)
3. Call `mc.entityRenderer.renderHand` / `func_78476_b` (**five** call sites)

OptiFine E7 `ReflectorForge.renderFirstPersonHand` posts `RenderHandEvent` **every** time `renderHand` runs (needed for shader two-pass hands). Morph’s handler fires again → step 3 → infinite recursion → freeze / `InvocationTargetException` / `StackOverflowError`. Often **no crash-report**.

iChun’s own 1.7.10 source (GitHub `master` still has this tree):

`src/main/java/morph/common/core/EventHandler.java` lines ~173–284.

sp614x on shaders + custom hands: Forge’s `RenderHandEvent` replaces camera setup, overlays, *and* the hand; it is “totally inappropriate” for shader hand rendering. Morph is doing exactly that.

---

## What was already tried in this pack

| Attempt | Result |
|---|---|
| Two Morph jars (0.9.1 + 0.9.3) in `mods\` | Duplicate modid. Not today’s crash. |
| Enable 0.9.3 only | Kill-acquire NPE (OptiFine E7). |
| NOP `GLAllocation.func_74523_b` in `ModelHelper` (2 sites: `getModelCubesCopy` + `compileRenderableModels`) | **Kill-acquire worked.** Owner confirmed. |
| NOP the per-frame delete in `ModelMorph.updateCubeMorph` (1 site) | Did **not** stop morph-in freeze. |
| Leave `handRenderOverride=1` | Freeze on become (ant), `onRenderHand` recursion in `latest.log` (~04:35 2026-09-04). |
| Move jar to `mods_disabled` | Pack stable again. |

Current `mods_disabled\Morph-Beta-0.9.3.jar` (4:08 AM 2026-09-04) **already contains all three display-list NOPs**. Unpatched original is `_backup-playtest-20260904-032759\mods\Morph-Beta-0.9.3.jar`. 0.9.1 is `_backup-morph-20260904-044935\Morph.jar` — same bugs, do not use.

Live `config\Morph.cfg` still has `I:handRenderOverride=1`. No config key exists to disable the acquire animation.

---

## Ranked options

### A. Config-only workaround — **usable, you lose first-person morph arms**

Set `clientonly.I:handRenderOverride=0` and enable the **already-NOP’d** 0.9.3 jar (the one in `mods_disabled`).

- **Keeps:** acquire-on-kill (with the NOP), morph-in, third-person model, abilities, radial menu, shaders, OptiFine E7.
- **Loses:** first-person morph hand (vanilla Steve/Alex hand + item while morphed).
- **Why it works:** `onRenderHand` is entirely inside `if (handRenderOverride == 1)`. `0` never cancels the event and never calls `renderHand`.
- **Does not need** a new jar. Snippet: `Morph.cfg.hand-override-off.snippet.txt`.
- **Confidence with Sildur + E7:** **medium** for stability (recursion gone; kill path already proven). Visual: you will not see a creeper arm in first person.

### B. Small bytecode patch — **recommended**

Two complementary patches:

1. **Keep the three display-list NOPs** (already in the disabled jar). Morph still sets `compiled = false` and re-renders; it just does not call OptiFine’s broken map. Tiny GPU list leak per acquire/transform; irrelevant.
2. **Reentrancy guard on `onRenderHand`** (new). If Morph is already inside its own `renderHand`, return immediately **without** canceling so OptiFine’s inner call actually draws the swapped arm.

Implemented in this folder as `Morph-Beta-0.9.3-QF-OPTIFINE.jar`:

- Classes: `morph.common.core.EventHandler` (prefix + `leave()` before the method return), `com.questforge.MorphHandGuard` (new).
- Script: `patch_morph_optifine.py` (rebuilds from `mods_disabled` only).
- StackMapTable stripped on the patched method; `TEST-LAUNCH.bat` already has `-XX:+UseSplitVerifier -XX:+FailOverToOldVerifier`.

Long-term home (once a **JDK** exists — this machine is JRE 1.8.0_241 only): extend QuestForgeTweaks. Proposed sources:

- `tweaks-src/MorphHandGuard.java`
- `tweaks-src/MorphOptifineTransformer.java` (same guard + optional `GLAllocation` null-guard)

Register in `QuestForgeCore.getASMTransformerClass` **after** `PanelButtonQuestTransformer`. Do **not** run `questforge-coremod\build.bat` yet — it copies into live `mods\`.

A null-guard on `GLAllocation.deleteDisplayLists` is the “correct” fix for crash 1 and would protect any leftover Morph (or other) caller. The NOPs already proved crash 1 is gone; the Tweaks version is optional insurance.

**What you keep:** shaders, E7, Fast Render off, first-person morph arms (if the guard works), acquire animation (if the NOPs hold).

**Confidence with Sildur + E7:** **medium**. Recursion math is solid; shader two-pass hands may still look wrong (missing/double hand, wrong depth) even if they no longer freeze. That is an OptiFine-shaders limitation iChun never fixed on 1.7.10.

### C. Different Morph build — **no good 1.7.10 option**

| Build | Notes |
|---|---|
| Morph 0.9.3 | Last 1.7.10. Needs iChunUtil 4.x. Pack has 4.2.2 (leave it). |
| Morph 0.9.1 | Same `deleteDisplayLists` + `onRenderHand`. One report said 0.9.1 + **D6** was stable. D6 = no shaders. |
| iChunUtil 4.2.3 | Mentioned in #836; iChun said the profile-lookup issue is unrelated. Do not swap the library. |
| Morph 1.12.2+ | Different loader / game version. Useless here. |
| “Fixed Morph + OptiFine” Drive zip (Jul 2026, [The-1.7.10-Pack#1990](https://github.com/xJon/The-1.7.10-Pack/issues/1990)) | Author says they **removed the kill-acquire animation** via a mystery jar + cfg. Not open source. Do not install a random Drive binary. |

There is no later official 1.7.10 Morph that talks to OptiFine E7. Shader-fixer (kotmatross) does not patch Morph.

### D. Incompatible — last resort only

To run **stock** Morph 0.9.3 you would have to **drop OptiFine E7** (and therefore Sildur) and use **HD U D6**, or drop OptiFine entirely. That is the only combination the community actually signed off on. It is the wrong trade for this pack.

---

## Best recommended path

**Use B (work-folder jar) as the thing to test. Keep A as the fallback if first-person hands still explode.**

Why B first: kill-acquire is already proven with the NOPs; the remaining failure is a 10-byte reentrancy check that matches the logged stack. A works but throws away morph hands, which is half the fantasy. D sacrifices shaders. C has no real candidate.

Do **not** silently put Morph back in `mods\`. Copy the work-folder jar for a dedicated session; if it kicks or freezes, delete that one file and Morph is gone again.

---

## Prototype files / classes

| Path | What |
|---|---|
| `Morph-Beta-0.9.3-QF-OPTIFINE.jar` | Test jar. Display-list NOPs + `onRenderHand` guard + `MorphHandGuard`. |
| `com.questforge.MorphHandGuard` | `shouldSkip` / `enter` / `leave` static flag. |
| `morph.common.core.EventHandler.onRenderHand` | Inserted at pc 0: skip-if-reentering; `enter()`; `leave()` before the original return. Five `func_78476_b` calls unchanged (pcs 256, 357, 572, 689, 920). |
| `morph.client.model.ModelHelper` | Unchanged from disabled jar (2× `pop; nop; nop` on `func_74523_b`). |
| `morph.client.model.ModelMorph` | Unchanged from disabled jar (1× same NOP). |
| `patch_morph_optifine.py` | Rebuilds the jar from `mods_disabled` only. |
| `tweaks-src\*.java` | Proposed QuestForgeTweaks extension (not compiled, not installed). |
| `HOW-TO-TEST.txt` | Step-by-step. |

Live `mods\QuestForgeTweaks-1.0.jar` is still the quest-book-only coremod.

---

## How to test

See `HOW-TO-TEST.txt`. Short version:

1. Quit Minecraft.
2. Copy `Morph-Beta-0.9.3-QF-OPTIFINE.jar` into `mods\` (one Morph only).
3. Launch `TEST-LAUNCH.bat`. Fast Render stays false. Sildur on.
4. Kill a **new** mob → must stay in-world, get the morph.
5. Morph into it → must not freeze. Look around, F5, first-person hand, morph back, kill a second species.

Watch `logs\latest.log` for:

- `GLAllocation.func_74523_b` / `deleteDisplayLists` / `ModelHelper.getModelCubesCopy`
- `EventHandler.onRenderHand` repeating / `StackOverflowError` / `InvocationTargetException`
- `There was a critical exception handling a packet on channel Morph`

Then **remove the jar from `mods\`** unless it clearly held.

---

## Confidence (Sildur + OptiFine E7)

**Medium.**

- Crash 1 (kill-acquire): **high** that the existing NOPs still prevent the NPE (already playtested on this instance).
- Crash 2 (morph-in freeze): **medium-high** that the guard stops the recursion (bytecode verified: 0 bad branches, 5 `renderHand` calls intact, skip path does not cancel the inner event).
- Staying *pretty* with Sildur first-person hands: **low-medium**. OptiFine’s shader hand pass and Forge `RenderHandEvent` were never designed to compose. Possible leftover: invisible hand, double hand, or hand that ignores the shader. That is a visual bug, not a kick, and A (`handRenderOverride=0`) is the fallback.
- Not a Morph rewrite. iChun abandoned 1.7.10. No later compatible official build exists.

If the owner only cares that Morph *functions* and will accept a vanilla first-person hand, start with **A** — smaller surface, already-proven kill path, no new bytecode.
