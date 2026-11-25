# 0006 — QF Textures ships with the pack; glass panes connect

**Date:** 2026-10-25
**Status:** accepted (Decisions sheet 1, cards tex-glass-panes and tex-ship; issue #10;
`answers/s001.json`). Source: [textures/direction](../design/textures/direction.md).

## Decisions

- **Connected glass panes:** `glassPane=true` in `config/mcpatcherforge.cfg` (pack config,
  live client, test clients). The MCPatcher module is marked alpha, so the showcase wall's
  pane row is checked in the next render round.
- **How QF Textures ships:** the built zip ships with the pack, as every resource pack does,
  with Faithful's credit, link and licence inside; the repo keeps only the build script and
  the lists. The owner accepted that the zip contains vanilla's pixels, recoloured.

## Consequences

- One shipping zip combines QF v0 (vanilla designs, Faithful 32x where chosen, calmer grass,
  vibrance, connected glass, LabPBR maps) with the modded v1 build (ores on Faithful stone,
  backports, modded CTM, emissive maps). `build_client_release.py` includes it and the client
  profiles select it.
- Still open, on sheet 2: the F32 Modded Edition licence, the nether and end stone hosts, and
  the four uncertain backports.
