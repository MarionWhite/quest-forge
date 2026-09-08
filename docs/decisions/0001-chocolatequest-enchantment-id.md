# 0001 — Patch ChocolateQuest's enchantment ID instead of moving Soul Shards'

**Status:** Accepted · **Date:** 2026-09-07

## Context

ChocolateQuest 1.1d was added to the pack on 2026-09-06. The first launch after
that, on 2026-09-07, crashed during FML mod init, and every launch after it
crashed identically:

```
java.lang.IllegalArgumentException: Duplicate enchantment id!
  class com.whammich.sstow.enchantment.EnchantmentSoulStealer
  and class com.chocolate.chocolateQuest.magic.EnchantmentMagicDefense
  Enchantment ID:52
```

Minecraft 1.7.10 stores an enchantment on an item by its numeric ID, in a shared
256-slot registry. Two mods claimed slot 52:

- **Soul Shards: The Old Ways** — Soul Stealer, ID configurable in
  `config/SSTOW/config.cfg`, default 52.
- **ChocolateQuest** — Magic Resist, `new EnchantmentMagicDefense(52, 1)` in the
  static initializer of `ChocolateQuest.class`. No config option exists.

Because ChocolateQuest registers during class load and Soul Shards registers
during `init`, ChocolateQuest always won the slot and Soul Shards always threw.

## Decision

Binary-patch the ChocolateQuest jar to claim ID 53 instead, and leave Soul
Shards on 52.

The obvious fix is the opposite one — Soul Shards has a config option and
ChocolateQuest does not. It was rejected because **the enchantment ID is what is
written onto the item**. A scan of the three world saves found ID 52 present on
existing gear in all of them. Moving Soul Shards would have silently reinterpreted
every Soul Stealer weapon in every world as ChocolateQuest's Magic Resist.
ChocolateQuest, by contrast, had never successfully loaded, so nothing in any
world referenced its IDs.

ID 53 was confirmed free against the runtime registry dump at
`pack/reports/qfcontent-enchantments.txt` (143 of 256 slots occupied), cross-checked
against `pack/config/qfcontent.cfg`, which pins this pack's own 81 enchantments to
132–221.

## Implementation

One instruction in `com/chocolate/chocolateQuest/ChocolateQuest.class`, the only
occurrence in the file:

```
bipush 52   ->   bipush 53
59 10 34 04 b7   ->   59 10 35 04 b7
```

The unmodified jar is kept at
`<instance>/minecraft/mod-backups/chocolateQuest-1.7.10-1.1d.jar.orig` —
deliberately outside `mods/`, which Forge scans. A diff of the patched jar against
that backup shows 1378 entries in both, none added or removed, and exactly one file
differing in content.

Verified: the pack loaded all 141 mods and reached a world, with no
`Duplicate enchantment` line in the log.

## Consequences

**This patch is invisible to CurseForge.** Updating or reinstalling ChocolateQuest
restores the stock jar and the pack crashes on launch again with the same message.
The fix is to redo the one-byte patch, not to touch Soul Shards.

Static analysis is not a reliable way to find a free enchantment ID in this pack.
Most 1.7.10 mods read their IDs from config at load time, so the number never
appears as a bytecode constant — a scan of all 111 jars recovered only a handful of
the 143 IDs actually in use. Use the runtime dump from `/qfcensus` instead.
