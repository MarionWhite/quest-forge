# r009 textures checkpoint (orchestrator, 2026-10-26)

Brief: ops/briefs/texture-iteration.md (v2). Input: tex-* answers in docs/design/shaders/feedback/r008.json.
Start state: QF Textures v1 (cc3230e). Build: `py -3.10 -I tools/textures/build_qf_textures.py --out C:/qfb/textures/QFTextures-v2.zip`.
Nothing for v2 started; no renders submitted.

## Owner's r008 texture answers
- tex-wall A 3/5: likes B's metallic metals and diamond and B's stone brick; iron and gold too dark in A, as if unlit.
- tex-wall-close B 4/5: emerald and grass look weird; the rest is good.
- tex-glass: all the same. tex-forest A 4/5: leaves in B (edges) are "complete shit".
- tex-golden: weird artifacting in all photos.
- tex-farm C 4/5, farm-close B 3/5: wants crops as close as possible to the pack whose crops he liked, without copying it.
- tex-leaves B 3/5, tex-leaves-tree B 3/5: leaves need heavy rework; B gives the tree more shape but he dislikes the look.
- tex-pbr B 3/5 "fine". tex-items B 4/5: books good; potions boring.
- Overall: "Fix the leaves, fix the grass, fix the crops."

## Plan
1. Leaves (qf_art.py): redesign; study, never copy, the packs he liked; drop or redo the ragged-edge CTM (--leaf-edges).
2. Grass top/side: restore the crisp r007 read, no flat felt.
3. Crops: own art in the liked pack's approach; check that pack's licence first (all-rights-reserved is study only).
4. Metals: raise iron/gold albedo in the PBR set; fix emerald. No per-frame cost (hard constraint, see r009-shader).
5. Find the tex-golden artifact.
6. Potions: stronger silhouette and colour personality.
7. Render via renderq (shot mode at night); write texture_scenes.json in C:\qfb\shaderdev\r009, TEXTURES-READY; `trial.py guard`; no push.

## Progress log
(none yet)
