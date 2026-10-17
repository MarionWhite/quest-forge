# `morph-probe/` — how the Morph fix was found (2026-10-16)

Morph 0.9.3 had been broken in this pack for months, and several earlier attempts
blamed the wrong thing. This folder keeps the probe that finally pinned it down, so a
future break can be reproduced the same way. The fix itself is
`MorphOptifineTransformer` in qf-tweaks (commit `31da143`). The stock Morph jar is
installed with no other changes.

## The two bugs

| Symptom | Real cause | Fix |
|---|---|---|
| Killing a new mob kicked the player | Morph forces a model recompile with `GLAllocation.deleteDisplayLists`, which throws when OptiFine's display lists aren't in GLAllocation's map | The three calls go to `MorphFix.deleteDisplayList`. It keeps vanilla's behaviour when that works, and otherwise frees the list with `glDeleteLists`. |
| Morphing "crashed the server" | A **freeze**, not a crash. Morph's `RenderHandEvent` handler calls `EntityRenderer.renderHand`; OptiFine's `renderHand` posts `RenderHandEvent` again, so it recursed until a StackOverflowError. OptiFine caught and logged it every frame (54 MB of log), so there was no crash report. In singleplayer the frozen client looks like a dead server. | The handler is wrapped in a re-entry guard that is cleared in a `finally`. |

## The process

1. **A copy of the full pack** (`C:\qfm\client`, now deleted) with a jdwp debug port
   (`run_probe.ps1`). It reads `bin\` and `assets\` from the live instance and never
   writes to it, and it refuses to start if another client is running.
2. **A scripted probe mod** (`src/qfprobe/MorphProbe.java`, compiled with JDK 8
   `-source 1.6` against the Forge universal jar only).
   - It loads a world through `GuiSelectWorld`, sets peaceful at login, and kills a mob.
   - It then morphs, toggles F5, opens the inventory and pause menu, morphs into a
     second species and demorphs, writing a heartbeat to `morphprobe.log`.
   - It reaches vanilla members by SRG name via reflection.
   - See `memory/questforge-unattended-client-probe.md` for the traps this avoids.
3. **`jdb_watch.sh`** attaches jdb once the world is loaded and breaks on every
   `CrashReport` construction, printing the real cause. The crash handler's own NPE
   had been hiding it.
4. **`jstack` on the frozen client** showed the `onRenderHand` recursion. That was the
   moment the "crash" turned out to be a freeze.
5. **The fix landed as a qf-tweaks transformer** on the stock jar. The scripted run
   then passed every step on the full pack with Sildur's Vibrant, and a dedicated
   server booted with Morph and `/morph`.

## Lessons

- **The September guard jar worked; it was wrongly blamed.** It was blamed for an NPE at
  `EntityRenderer:1464` that recurred three times that afternoon with Morph removed. That
  NPE came from main-menu work.
- **log4j keeps only 7 logs a day,** so the evidence behind an old theory gets
  overwritten. Re-verify against a fresh run.
- **Never change world state from the client thread in a probe.** It produces crashes
  that real play never does.

## Reproducing a future break

Start slim, not with a full copy:

```
py -3.10 tools/trial/trial.py build morph morph --bundle inspect --world <save>
```

This boots in about 15 s. Drop `MorphProbe.jar`, built from `src/`, into the trial's
`mods/` for a scripted run. Use the full pack only if the bug needs other mods.
