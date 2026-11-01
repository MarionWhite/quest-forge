# r015: packs, five HUD designs (texture-dev, 2026-11-01)

Work order: ops/checkpoints/r015-plan.md "Packs". Base/builders/traps: r014-packs.md.

## Progress log
### 2026-11-01 step 1: hook extended, bench jar built
- XpBarStyle.java (mods/qf-content/.../client): new keys text.boss, qf.boss.outline (8-way outline round the boss
  name), qf.boss.frame=u,v,w,h (sprite centred on the boss bar, drawn after it; odd h centres exactly). Same hook,
  same owner yes needed. Copied to worktree C:\qfb\wt-r011-fb, built (-PqfDebugTools=true) ->
  C:\qfb\renderq\jars-r015\QuestForgeContent-1.0.0.jar.
- Next: tools/textures/qf_hud_r015.py (5 designs), mock sheet, spec textures-r015-packs.json, submit.
### 2026-11-01 step 2: five designs built, render SUBMITTED
- tools/textures/qf_hud_r015.py (own art): A gilded, B cloisonne, C ironbound, D moonsilver, E obsidian. Each: band
  behind hearts/food/armour rows (container carries it; divider identical in GUI cols 0 and 8 so both draw orders
  match), gem icons, hotbar + selection, XP strip, medallion PLATE=(0,100,26,15), boss strip, boss frame
  FRAME=(0,120,214,15), color.properties (text.xpbar, qf.xpbar.*, text.boss, qf.boss.outline, qf.boss.frame).
  Offline mock: `--mock OUT.png --icons OUT2.png` (exact Forge draw order, vanilla font from minecraft.jar read only,
  GUI 4 + true GUI 1 sampling of odd texels).
- Zips: C:\qfb\textures\r015\QF-r015-hud-<design>.zip. Spec tools/renderq/specs/textures-r015-packs.json
  (pk15a..pk15e, gui_hud, measure 220, jars-r015).
- SUBMITTED 1101-101607-textures-r015-packs (2 submissions ahead at 10:16; owner busy).
- Next: `py -3.10 -I tools/renderq/renderq.py wait 1101-101607-textures-r015-packs`; check bench-pk15{a..e}-gui_hud.png
  in C:\qfb\shaderdev\rounds\screenshots: hotbar/bands ours, medallion behind the number (number recoloured), boss
  name outlined, boss frame drawn, food full, 7.5 hearts, no screen, chat clear. Then r015_packs_handoff.py.
