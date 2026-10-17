# Review loop

How each iteration of the shader is judged before it reaches the owner. The aim
is that the owner only ever sees frames a strong critic already thinks are
close, and only ever answers questions a machine cannot: taste.

## The cycle

1. **Change.** One feature or fix at a time, on a branch of the shader source.
2. **Render the scene set** with the benchmark harness on a slim trial (only the
   mods the scene needs, about 15 s to boot). Every scene gives a 2560×1440
   screenshot plus frame-time statistics.
3. **Automatic checks**, before any model looks:
   - frame-time budget for the tier (`performance-rules.md`); 1% low and frames
     over 33 ms must not get worse;
   - clipped highlights and crushed shadows (percent of pixels at 0 or 255);
   - mean luminance per scene against its target band (night and cave floors);
   - temporal noise: the difference between two consecutive frames of a still
     camera.
   A change that fails these goes back to step 1 without spending a critic call.
4. **Critic.** A subagent on the strongest available model receives the look
   bible, the owner's taste profile, the latest owner feedback, and for each scene
   the new frame, the previous best and the Vibrant baseline. It returns JSON:
   per-scene scores on the rubric below, specific defects with where they are in
   the frame, and the single most valuable next change. It never sees our code,
   only pixels and numbers, so it judges the result rather than the intent.
5. **Gate.** A round goes to the owner only when every scene scores at least 7 on
   every Tier A item, no defect is marked severe, budgets pass, and the mean
   overall score is at least 8 and higher than the last round the owner saw.
   Otherwise the critic's top change becomes step 1.
6. **Round.** When the gate passes, the frames are uploaded to the Shader Lab page
   (https://claude.ai/artifact/C7LvLPJEpxazScuaLjJo3Q) as a round. Where the
   critic found a genuine taste choice (warmer or cooler sunset, haze density), the
   round offers two or three variants of that one axis instead of a single frame.
   A push notification goes to the owner's phone.
7. **Learn.** The owner's picks, ratings and notes are read from the page's
   database. They are summarised into the taste profile (the page's "What I've
   learned" panel and the end of `look-bible.md`), and any rule they contradict is
   rewritten. The next critic call sees the new profile.

## Rubric (each 0–10)

| Group | Items |
|---|---|
| Comfort (Tier A) | readable darkness · calm exposure · neutral colour · golden hour without wash · temporal stability · clear near field |
| Realism (Tier B) | sky · clouds · shadows · AO · water · block light · wetness · bloom restraint |
| Quest Forge (Tier C) | modded materials · dimension sky/fog · custom renderers |
| Defects | each with severity (minor / major / severe) and location |
| Overall | one number, against the look bible and taste profile |

Anti-patterns from the look bible are automatic deductions.

## Scene set

Each scene is a fixed world, position, camera and time, so frames are
comparable across iterations:

- Plains at noon, forest at golden hour, mountain range at sunrise
- Ocean shore at noon and at sunset; underwater
- Night under a full moon and a new moon; a torch-lit cave
- Rain, then the same place 3 minutes after rain
- The block gallery (vanilla next to modded look-alikes)
- Twilight Forest canopy, the Nether, the End, and two more modded dimensions
- The pack's own custom renderers (jukebox, record case, speakers)
- Failure-class probes: a Legends laser, a McHeli aircraft held and flown, a
  modded particle effect, a mob crowd (entity shadows, frame time)

## Phone notifications

The owner gets a push notification when a round is ready. It reaches the phone
only while this Claude Code session is connected to the Claude app with Remote
Control; otherwise it appears on the PC only.
