# r011: process reset after the owner's r010 feedback

Input: docs/design/shaders/feedback/r010.json (owner, 2026-10-28 01:38Z, issue #14) and two meteor reference photos in
docs/design/shaders/feedback/attachments/r010/ (a wide meteor shower over the Milky Way; long thin straight streaks,
many at once, all from one radiant).

## The owner's verdict, verbatim
"Once again we are falling short of the expected progress. We are using a lot of resources each round for minimal
return. We need to reconsider how we are doing things at a high level. The same questions are being posed each round
with very minimal effort to execute on the feedback. We need to start just copying from the packs that are doing
things right, and then we can try to improve upon them. This isn't intended to make money, and there's nothing on
the line here. I just want a good looking pack for my private server."

Frills (all "neither", rated 5 for importance): "these all look like shit. They make the tree look spiky. Please
actually check to see what stay true does because I'm sick of the guess work." "We're getting to the point where we
need to just copy the texture maps of stay true, and we can make changes directly to it to make it our own."
Crop variants: "a good idea, but this is the wrong execution."

## Picks
meteors B (storm) 3/5, perf must come back; reference photos. sunset-full A 3/5: the sun is one hot spot, it must
light the whole atmosphere. sun-cloud B (rays on) 4/5 "only if we can afford them". forest-light B. underwater A 5/5.
river A (must differ from ocean and coast). gold A; diamond and emerald glassier, more reflective. checks C.
tex-wall B, "keep metallic textures for the actual metals". tex-leaves A (Faithful) but dislikes Faithful's leaves;
wants Stay True's. tex-leaves-tree: transparency yes, realistic volume and structure. tex-farm B and farm-close B
(dense). tex-items C, wants one more full art-style set before committing.

## Facts found 2026-10-27 (not guesses)
- We never had Stay True on disk. Every leaf, frill and wheat attempt was built from two owner screenshots.
  Stay True is CurseForge-only (Modrinth search: only add-ons); CurseForge's API is behind Cloudflare from here.
- Stay True is 1.14+; its frills are JSON block models (direction.md l.442). Its licence (direction.md l.153): ARR;
  the author's FAQ allows use in modpacks with credit, not edits.
- C:\qfb\refpacks holds BSL 10.1.8, Complementary Reimagined r5.9.3, Photon 1.4 (official Modrinth files).
  - Photon licence: modify for personal use; redistribute modified or unmodified portions, including in a modpack,
    except on paid platforms (Modrinth, CurseForge); keep its LICENSE in substantial copies. Has
    include/sky/atmosphere.glsl with a precomputed scattering LUT (image/atmosphere/scattering.dat) and
    include/sky/crepuscular_rays.glsl.
  - Complementary: modified packs allowed only under its own licence with conditions (1.3); no edits in a modpack.
  - BSL: lib/atmospherics/lightShafts.glsl; licence not checked yet.

## Next
Proposal to the owner (this session's reply). No round work starts until the owner answers.
