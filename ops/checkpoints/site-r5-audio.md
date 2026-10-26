# site-r5-audio (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: `site/lib/sfx/*`, `tools/site/build_sfx.py`, `tools/music/site_cues.py`, and any new
`tools/music/` file for this task.
Previous state: `ops/checkpoints/site-audio.md`.

## Owner's words (2026-10-26)
- On the Krypt scares: "I want actual horror here, and scream effects could help."

## Done means
- [ ] Add these events to the bank and manifest, mono AAC `.m4a` as before, with a peak around
  -1 dBFS:
  - `qf.scare.scream`: a close human scream of terror, 1 to 2 s, 3 variants.
  - `qf.scare.scream_far`: a distant echoing scream, 2 to 3 s, 2 variants.
  - `qf.scare.shriek`: an inhuman shriek for the hit, 0.5 to 1 s, 3 variants.
  - `qf.scare.stinger`: an orchestral or noise stab, 1.5 s, 3 variants.
  - `qf.scare.hit`: a sub-boom plus a crack, 0.4 s.
  - Loops, seamless: `qf.scare.heartbeat` (slow to fast variants), `qf.scare.breath` (ragged
    breathing), `qf.scare.drone` (low dread pad), `qf.scare.ringing` (tinnitus after the
    explosion) and `qf.scare.chitter` (a swarm of insects).
  - `qf.scare.whisper`: unintelligible whispers, 3 variants.
  - `qf.scare.fall`: a falling whoosh, 1 s.
  - `qf.scare.crunch`: bone crunch, 3 variants.
  - `qf.scare.gore`: a wet tear, 3 variants.
  - `qf.scare.cackle`: a witch cackle, 2 variants. The bank has no witch sounds.
- [ ] **Source:**
  - Synthesise, or process existing bank sounds (pitch, stretch, layer, reverse, distort) in a
    script. For example, layer `mob.ghast.scream` and `mob.endermen.scream` with formant
    synthesis for screams.
  - Or use CC0 recordings, with each source URL and licence recorded in the bank's README.
  - Nothing all-rights-reserved. Note which events derive from Mojang sounds, so `--own-only`
    builds can drop or replace them.
- [ ] They must sound like horror, not like a synth demo. Render a preview strip, then listen by
  analysis: check the envelope and spectrum and look for clipping. Report what a human should
  listen to first.
- [ ] `python3 -I tools/site/check_sounds.py` exits 0 on the whole site.

## Done
(nothing yet)
