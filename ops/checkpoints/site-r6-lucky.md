# site-r6-lucky (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: all of `site/lucky/*`; no other agent works there this round.
Previous state: `site-r5-lucky-life.md`, `site-r5-lucky-flow.md`, `site-r5-lucky-accuracy.md`.

## Owner's words (2026-10-26)
- "The lucky block break is in a really good spot!"
- "I would like to make it so that the blue circle on the platform is an effect of the block
  dropping, not a permanent translucent blue circle floating in the air."
- "Breathe more life into the scene, give steve a lot more things to do, and make his animation
  cleaner because he walks from one event to the next like the fucking terminator on a mission
  rather than a natural leisurely pace."
- "All of the animations for it that I was able to see look good, other than the big event mobs
  walking directly through the tree."

## Done means
- [ ] **No permanent ring:** the translucent blue ring over the dais is gone. When the block
  slams down, a shockwave ring expands on the platform surface and fades over about 0.6 s, with
  a dust puff. Nothing floats. Check every phase for other stray rings.
- [ ] **Leisurely pace:**
  - Walk at about 1.3 to 1.8 m/s, below Minecraft's 4.3 sprint feel, with ease-in and
    ease-out and a slight gait variation.
  - Paths curve rather than beeline.
  - Pause between tasks: look around, stretch, scratch his head, glance at the sky, the fire or
    the chicken.
  - Head turns lead his body.
  - Put the average speed and the pause share over 120 s of idle in the dump JSON.
- [ ] **At least 20 activities in all**, each accurate to 1.7.10 with its real sounds, and
  chained sensibly. For example:
  - farming: till, plant and harvest wheat, and bone-meal a sapling into a tree;
  - fishing, with a catch;
  - eating bread or an apple, with crumbs and the eat sound;
  - feeding and petting a dog, which needs a tamed wolf added;
  - shearing a sheep and milking a cow, which need the animals added;
  - placing torches at dusk;
  - sitting on the bench reading a book;
  - shooting a bow at a target;
  - brewing at a stand, and enchanting at a table;
  - playing a record in a jukebox and bobbing his head;
  - building a little dirt hut and breaking it down;
  - sneaking, sprint-jumping onto a block, skipping stones on the pond;
  - funny easter eggs, such as falling into the hole he just dug, or a creeper walking up
    behind him that he notices at the last second before it fizzles out.
- [ ] **Big mobs:** in the boss and grand scenes, ground mobs path around the tree trunks and
  props using their real footprint (width times scale). Giants step around. Extend
  `tools/site/nav_check.py` to cover them, and get 0 samples inside blocked cells.
- [ ] Sheet: the slam ring in 3 frames, 20 activities, a 4-frame walk showing the pace, and the
  boss scenes with big mobs clear of the tree.

## Progress
- [x] ring: permanent violet RingGeometry in stage.js removed (stage.ring is now an invisible Object3D); app.js slam() makes two expanding rings fading 0.6 s. Not yet seen in a sheet.
- [x] big mobs/tree: mobscenes.js footRadius (real model width x scale, cap 3.6), softFor(height), radius fallback 100/85/70%; ROOT CAUSE nav.js maxR=1.6 bucket limit missed boxes for agents wider than 1.6 (now 4.0). nav_check.py --bosses: 15 boss/grand scenes, 0 violations, 0 noroute. Visual sheet still to do.
- NEXT: Steve pace (walkTo speed/ease/curve/gait, pauses, stats in dump JSON), then 8+ new activities (need wolf/sheep/cow), then final sheet.
- [x] pace (steve.js walkTo: 1.75 cruise, ease in/out, drift, rounded corners + bowed long runs, head leads body; fidget() pauses after every act: around/sky/fire/stretch/scratch/shrug/rock/hum; stats in dump JSON steve.pace). 120 s idle: avgWalkSpeed 1.40 m/s, pauseShare 0.18 (will rise with new acts), nav 0 violations (3637 samples).
- NEXT: copy textures from jar (r5/lucky-accuracy/jar/mc/assets/minecraft/textures) -> site/lucky/tex; ambient wolf/sheep/cow (camp animals) ; new acts file site/lucky/acts.js (farm, sapling, eat, dog, shear, milk, torches, read, bow, notes, hut, skipstones, hole, creeper, parkour, enchant). No records.* sounds exist: use note block (note.harp etc.) not jukebox.
