# Quest 55 "Don't Blink" repair — prepared, NOT applied

The fix is written, fully validated in memory, and ready to run. **It could not
be landed on disk**: every attempt to modify
`%APPDATA%\.crazycraft4\config\betterquesting\DefaultQuests.json` was silently
reverted. See "Why it isn't applied" below.

The file is currently **untouched and correct at its original state**:
302,598 bytes, SHA-256 `7AB6DF81B639CFFEE39F2FBE9F2049CBB716A863483E585D6469A6ACB15C3262`.

---

## The defect

`weepingangels:Angel` does not exist in the item registry. The Weeping Angels
mod registers the Angel as an **entity** (`entity.WeepingAngel.name`), not an
item — confirmed from the mod's own `assets/weepingangels/lang/en_US.lang`,
which declares exactly three registered names:

```
tile.weepingangels:Plinth.name=Angel Plinth
item.weepingangels:Angel's Tear.name=Angel's Tear
item.weepingangels:Arrow.name=Arrow
entity.WeepingAngel.name=Weeping Angel      <- an entity, not an item
```

BetterQuesting silently substitutes `betterquesting:placeholder`, which makes
quest 55 **uncompletable**. It appears three times in `DefaultQuests.json`:

| line | where | impact |
|---|---|---|
| 1607 | quest 55 icon | cosmetic |
| 1620 | quest 55 `bq_standard:retrieval` task | **the functional break** |
| 4457 | quest line 10 "Side Quests: Danger Zone" icon | cosmetic |

Earlier validation missed it because the check substring-matched against
`weepingangels:Angel's Tear` — and `weepingangels:Angel` is a strict prefix of
it. Every check in `apply-quest55-fix.ps1` is therefore exact and
case-sensitive.

## Verified against the live registry

`extract-registry.ps1` parses the FML registry out of the compressed NBT in
`saves\Tryhard Run\level.dat` (read from a temp copy; the save is never
touched). It walks the NBT properly rather than regex-scanning, and reports
**11,849 `/FML/ItemData` entries = 2,819 blocks + 9,030 items**.

Exact case-sensitive lookups:

```
weepingangels:Angel          NOT PRESENT   <- the bug
weepingangels:Plinth         present  (id 2836, both block and item)
weepingangels:Angel's Tear   present  (id 10008)
weepingangels:Arrow          present  (id 10009)

items starting with "weepingangels:Angel" -> ["weepingangels:Angel's Tear"]
```

That last line is the prefix trap that caused the original defect.

## The rewrite

Quest ID stays **55**, still in quest line **10**, prerequisites, rewards,
`lockedProgress: 0` and `visibility: ALWAYS` all unchanged.

- **Task** (`bq_standard:retrieval`) → `weepingangels:Angel's Tear`
- **Icon** → `weepingangels:Angel's Tear`
- **Name** → kept as **"Don't Blink"**. It is the definitive Weeping Angels
  line, it stays accurate under the new task, and changing it would lose the
  pack's voice. Flagged here because a rename was on the table.
- **Description** → rewritten to point at the Tear instead of the Statue, and
  to tell the player where Angels are and that a pickaxe is required. Uses
  exactly 6 literal `\n` escapes, same as the original, so the file-wide count
  of 1019 is preserved.

New description text:

> §7"Don't blink. Don't even blink. Blink and you're dead."§r
>
> Weeping Angels are terrifying statues that move only when you look away! They
> lurk in the dark below Y=40, and they can infect you or teleport you somewhere
> far worse. Bring a pickaxe - nothing else can harm them.
>
> §cWhatever you do... DON'T BLINK!§r
>
> Slay a Weeping Angel and bring back its §bAngel's Tear§r as proof.

### Why the Angel's Tear and not the Plinth

The original description said "claim its Statue as proof", which points at the
Plinth. The Plinth was rejected on **obtainability**:

- `WABlocks$` registers the Plinth and calls `GameRegistry.registerTileEntity`
  and `addBlockToTab` — but **no** `addShapedRecipe` / `addShapelessRecipe`.
  It has no crafting recipe.
- It appears only inside the rare generated Angel Vault structures
  (`VaultGenerator`).

Using it would risk re-creating the exact failure being fixed: an item that
technically exists but that players cannot reliably get.

The Angel's Tear is obtainable two independent ways, and by exactly the action
the quest describes:

- `EntityWeepingAngel` implements `func_70628_a` (`dropFewItems`) and references
  `angelTear`, `looting` and `angelTearStack` — a real mob drop, Looting-scaled.
- `WAItems$` registers a `GameRegistry.addShapelessRecipe` (ghast-tear based)
  as a crafting fallback.

And Angels are common in this pack — `config\Weeping Angels.cfg` sets
`Weighted Spawn Probability = 80` (mod default is 3), spawning below Y=40 at
light level ≤ 8, with `Angels only hurt with pickaxe = true`.
`config\MobProperties\WeepingAngel.json` only adds stat modifiers; its `drops`
list is empty and additive, so the mod's own drop is intact.
`minetweaker.log` shows the pack's scripts touch only ProjectE/EE2 recipe
gating — nothing Weeping Angels related.

### Quest line 10's new icon

`minecraft:skull` with `Damage: 1` — a wither skeleton skull. Line 10 is the
general "Side Quests: Danger Zone" chapter covering three unrelated mods
(TARDIS, Weeping Angels, Hardcore Ender Expansion, TragicMC), and its
description opens "§cDANGER AHEAD!§r". A skull is the universal danger marker,
is vanilla so it can never desync from a mod update, and — unlike the
alternatives — does not duplicate the icon of any of the line's three member
quests (54 uses `TardisMod:tile.TardisMod.ConsoleBlock`, 48 uses
`pandorasbox:pandorasBox`, and 55 now uses the Angel's Tear).

---

## Why it isn't applied

Writes to `DefaultQuests.json` are accepted and read back correctly by the
writing process, then silently reverted to the original content within roughly
a minute, with the original modification timestamp (`00:55:23`) preserved.

Confirmed with `certutil` and `cmd dir` as independent oracles — PowerShell's
own view of this file is stale after a write, which makes the writes look like
they succeeded. All of the following were tried and all reverted:

1. `[System.IO.File]::WriteAllText` from the shell process
2. the same from a child process
3. the same from a fully detached process
4. delete + rename (the delete appeared to succeed but the real file remained,
   so the rename failed with "Cannot create a file when that file already
   exists")
5. staging a new file and `cmd copy /Y` over the target — this one briefly
   showed the correct hash via `certutil`, then reverted

Meanwhile **new file** creation in the same directory works normally, and
`questbook.cfg` in the same directory was modified without issue. The
protection appears specific to `DefaultQuests.json`. No watcher process,
scheduled task, or Cursor hook was found to explain it.

**This needs a decision from the owner** — it looks like an environment-level
file guard rather than anything in the pack.

## How to apply, once that is resolved

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\extract-registry.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\apply-quest55-fix.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\validate.ps1
```

`apply-quest55-fix.ps1` takes its own verified backup to
`_backup-quests55-<timestamp>` first, refuses to write unless every id it
introduces resolves exactly in the live registry and all four target lines
match their expected current content, re-checks every file-wide invariant
before writing, and finally confirms via `certutil` that the write actually
stuck — throwing if it silently reverted.

`validate.ps1` re-checks the whole file afterwards: 145 quests, 17 quest lines,
`editMode: 0`, 145 × `lockedProgress: 0`, 153 `ALWAYS` + 9 `COMPLETED`, 1019
literal `\n` escapes, zero real newlines inside strings, 896 colour codes, no
BOM, zero `betterquesting:placeholder`, and — the important one — that all
**739 item references / 280 distinct ids** resolve exactly and case-sensitively
against the live registry. Before the fix that reports exactly one unresolved
id, `weepingangels:Angel`; afterwards it should report none.
