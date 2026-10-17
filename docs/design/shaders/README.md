# Quest Forge shader pack

A shader pack written from scratch for this modpack, on OptiFine 1.7.10 HD U E7.
The goal is a near-photoreal look that still reads as Minecraft, holds frame
rate on weaker PCs, and treats the pack's modded blocks, dimensions and custom
renderers as first-class.

## Why our own pack

Measured on 2026-10-16 (see [`../../setup/hosting-a-server.md`](../../setup/hosting-a-server.md)
and the qf-tweaks GL-error fix):

- **Complementary does not render on E7.** It needs `shadowcomp`, conditional
  programs and uniforms that E7 lacks, and its licence forbids modifying it.
- **Sildur's Vibrant works but cannot go further.** It ignores specular maps and
  its own 1.7.10 block mappings are partly invalid on E7.
- **No PBR texture pack exists for the 1.7.10 layout**, and a vanilla-only one
  would leave the pack's ~5,200 modded block textures inconsistent.
- **The frame budget is CPU-side.** With the GL-error fix, Vibrant High runs
  140–170 fps at 1440p with the GPU about 44% busy. Pixel cost is cheap here;
  extra geometry passes are not.

## Licence stance

Our code is our own and we choose its licence. We learn techniques from any
pack, but copy code only from public-domain or MIT sources, keeping their
notices. No code from Complementary, BSL, Sildur's, SEUS, Photon, Bliss or any
GPL pack. The details and the per-pack licence table are in
[`research/techniques.md`](research/techniques.md).

## Documents

| File | What it is |
|---|---|
| [`look-bible.md`](look-bible.md) | What "the look" means. The critic scores against this. |
| [`performance-rules.md`](performance-rules.md) | Hard rules and per-tier frame budgets. |
| [`review-loop.md`](review-loop.md) | How every iteration is rendered, critiqued, and sent to the owner's phone. |
| [`research/`](research/) | The three source reports, 2026-10-16: performance, desirability, techniques and licences. |

## Platform facts (verified in the E7 jar, 2026-10-16)

Present: gbuffers programs, `shadow`, `deferred`–`deferred7`, `composite`–`composite7`,
`final`; colortex0–7 with formats, per-buffer clear and mipmaps; hardware shadow
filtering, `shadowcolor0/1`, `shadowtex0/1`; `frameCounter`, previous-frame
matrices and camera position (so TAA and reprojection work); `heldItemId`;
`block.properties`; custom uniforms; custom textures; `shadowTranslucent`,
`shadowDistanceRenderMul`.

Absent: `shadowcomp`, `prepare`, compute, geometry shaders, `program.X.enabled`
(use profile `!program.X` instead), per-buffer resolution scaling, `separateAo`,
entity removal from the shadow pass.

Unresolved (the two research reports disagree): whether `flip.*` buffer
directives work. Settle with an in-game probe before relying on ping-pong buffers.

Traps: OptiFine enables the whole shadow pass if any shadow sampler is declared
anywhere, `#ifdef` or not. `centerDepthSmooth` forces a `glReadPixels` every
frame. Mentioning `colortex7` allocates all eight buffers. E7's own block-mapping
reload is broken, and so is its mod-domain lookup; both need the qf-tweaks patch
before modded block IDs reach any shader.
