# Krypt jump scares, v2 (design spec, 2026-10-26)

Owner on v1, after the Silverfish scare: it felt like a video-game cutscene that didn't make sense,
it teleported him somewhere he wasn't, the silverfish textures didn't load, and it wasn't scary.
He wants actual horror: screams, real creativity, Minecraft Story Mode quality, gruesome like
Mortal Kombat but in Minecraft's blocky style. His idea: if staging the scare where the player
stands is hard, freeze the player, pan the camera down, and drop them through an accurate piston
trap into the room where the scare happens. That is one idea of many.

## Rules
1. **It happens where the player is.** Run inside the real Krypt scene (`window.__krypt.scene`,
   `.camera`, `.takeover(true)`), not a separate canvas or a generic corridor. Mobs come out of
   the real geometry: a bend, a side passage, the ceiling, a wall, the floor. If a scare needs its
   own room, the player gets there on screen (piston trap, collapse, an Enderman grab). Never a cut.
2. **Dread, then the hit, then the kill.**
   - Freeze: walking locks, your footsteps stop, the music drops to silence, a heartbeat starts.
     Hold 1 to 3 s with a tell: a sound, a light dying, a glimpse.
   - Hit: fast, loud and close.
   - Kill: 2 to 4 s, blocky gore (red pixel chunks, Minecraft hurt flashes and damage tilt, the
     view knocked to the floor), a scream.
   - End: the "You died!" screen. Respawn returns you to exactly where you were, lights
     restored, mob gone.
3. **The camera is the player's head**: 1.62 m eye height, the Minecraft damage tilt and
   knockback, the death roll onto the side. No floating cinematic cameras.
4. **Accurate Minecraft**: models and textures from `site/lib/mc` (`whenMobTexturesLoaded`
   before the first frame), real sounds, the Minecraft fire overlay, nausea wobble, hurt flash,
   and blocks from the segment the player is in.
5. **Vary the entry** across the set: in-place ambush, look-back, lights-out, ceiling drop, wall
   break, piston trap, teleport grab.
6. **Length**: 6 to 10 s from the freeze to "You died!".

## The piston trap (shared mechanic)
This works as in 1.7.10:
- Sticky pistons sit hidden under the floor or in the walls.
- First a redstone click (`random.click`), then `tile.piston.in`.
- A 2 by 2 patch of the real floor is pulled sideways into the walls by sticky piston heads,
  using the textures `piston_top_sticky`, `piston_side`, `piston_bottom` and `piston_inner`.

The camera freezes and tilts down to watch the floor open over 0.6 s. Then the player falls:
- the sound is `qf.scare.fall`, and the FOV widens a little;
- they land 6 to 8 blocks down with `game.player.hurt.fall.big` and a hurt flash;
- the pit room is dressed like the segment above, with the hole and the corridor's torchlight
  still visible overhead.

The Krypt exposes `__krypt.carve(min, max)`, `__krypt.restore()` and `__krypt.solidAt(x, y, z)`.
Use them to open the floor and to pick a pit spot clear of other corridors.

## One idea per mob (build to this, improve where it plays better)
- **Zombie (look-back):** a groan behind you; the view turns to the side passage, which is empty.
  Turning back, the zombie is at your face. It grabs both sides of the view and bites, with hurt
  flashes. More arms reach out of the dark and drag you down until the view is the ceiling and
  hands cover it.
- **Skeleton (lights-out):** the torches ahead snuff out one by one toward you (`random.fizz`).
  In the dark the bow creaks, and arrows thud into the walls by your head with sparks. One hits,
  and the camera jerks. It steps into the last torch at point blank, draws, and fires.
- **Creeper (look-back):** a hiss behind you. Slow turn: its face fills the view, flashing white
  and swelling, and time slows. White-out, ringing, then muffled audio. From the floor you see
  the crater and your hotbar items scattering.
- **Spider (ceiling drop):** clicking overhead; the view tilts up to red eyes on the ceiling. It
  drops onto your face with its legs wrapping the edges of the view, then you are hauled up into
  the dark and left dangling.
- **Cave Spider (piston trap):** you fall into a cobweb pit with a spawner cage burning in the
  corner and are stuck in web (slow). Dozens pour out of the cracks; green poison pulses blur
  the view.
- **Enderman (stare):** a figure at the end of the corridor. Static, and the view is forced to
  look at it. Each glitch cut, it is closer; then its face and the scream. It grabs you and
  teleports, and you reappear in the air over the lava chasm, falling.
- **Witch (potions):** a cackle. A bottle shatters at your feet in a purple splash; nausea
  wobble, and the corridor stretches. She walks out of the haze laughing. A second potion,
  Harming, hits red; you drop, and she leans over you.
- **Slime (piston trap):** you fall into a dark pit and land in shallow green. A huge slime
  drops from the hole above and engulfs you: the view is inside the translucent slime, the audio
  is muffled, and you suffocate. Small slimes split off.
- **Silverfish (wall break):** the stone beside you twitches (infested stone). Cracks spread,
  blocks crumble, and hundreds pour out across the floor and up your legs, with the camera
  dropping to floor level as they cover the view, chittering.
- **Blaze (heat):** shimmer and embers rise, then the blaze's breathing comes round the corner.
  Three fireballs; you catch fire with the Minecraft fire overlay, the hotbar burns, and the
  screen chars.
- **Ghast (piston trap, deep segments):** you fall into a vast netherrack cavern on a ledge over
  lava. A distant cry, then the huge face rises from below the edge: its eyes open, its mouth
  opens, and the fireball fills the screen.
- **Magma Cube (behind you):** thump, thump, closer behind. The view turns as it lands on you;
  the screen squashes flat in a lava glow.
- **Zombie Pigman (your fault, the owner's version):** a diamond ore block glints in the floor
  just ahead (1.7.10 `diamond_ore`, a faint sparkle catching the torchlight). The walk slows, the
  view drifts down to it, you step up and raise the iron pickaxe, and each swing spreads the
  1.7.10 destroy-stage cracks with the dig sound. One swing from breaking it you stop: a beat of
  silence. On the swing that would break it, a pigman steps into the gap from just out of view and
  the pick lands in him: the hurt flash, `mob.zombiepig.zpigangry`, and his face snaps round to
  yours in the FNAF lunge with the screech. Your hit is what angers him. After the static every
  pigman in the dark turns red-eyed, the head flicks from eyes to eyes, they rush from every
  passage at once and close round you, and they cut you down with the death scream. Death
  message: "Steve was slain by Zombie Pigman".
- **Wither Skeleton (deep only):** black fog, just its eyes. Its stone sword scrapes the wall in
  sparks. The Wither effect blackens your hearts and the edges of the view. One swing, and the
  view drops and rolls across the floor to look up at its feet.

## Sounds
The audio task adds these to `site/lib/sfx`. Names are fixed so the scares can use them now:
- `qf.scare.scream`, `qf.scare.scream_far`, `qf.scare.shriek`, `qf.scare.stinger`, `qf.scare.hit`
- `qf.scare.heartbeat` (loop), `qf.scare.breath` (loop), `qf.scare.whisper`, `qf.scare.drone` (loop)
- `qf.scare.fall`, `qf.scare.crunch`, `qf.scare.gore`, `qf.scare.ringing` (loop),
  `qf.scare.chitter` (loop), `qf.scare.cackle`

Reuse the existing bank wherever a real Minecraft sound fits.

## Testing and approval
- **J** opens a small Minecraft-style picker at the bottom left listing the 14 scares, each
  marked approved or not yet. A click or the number keys play one where you stand, and Esc
  closes it. It works on the live page.
- `site/graves/scares/approved.json` holds `{"approved": []}`. The random director only uses
  approved scares, so an empty list means no random scares. The owner approves by telling Claude,
  and the "everyone gets hit once" guarantee applies once one scare is approved.
- Verify on the real page with `graves/?demo&at=<0..1>&scare=<mob>&scareat=<ms>&dump=1`, in at
  least three different segments. No test page ships under `site/`.

## v3 (2026-10-26): FNAF-level terror, failed jumps, real screams
The owner played v2: high-quality animation, but "they aren't scary enough". The Silverfish and
Cave Spider scares are "almost there, but that is a specific type of fear". The Magma Cube is
"kind of boring". The Wither Skeleton "starts off cool, and is a cool idea with the sparks, but
it ends kind of boring". His brief: "take some inspiration from FNAF for the jumpscares, and be
creative. Make me piss my pants even though I know it's coming." The scream audio is "terrible".
He wants "a man dying, screaming for his life, like the MK9 audio. Grotesque and harrowing."

What FNAF does, translated to Minecraft:
- **The lunge.** The jump is a face rushing the lens in about 0.25 s: the mob's face fills the
  frame, the head jitters and shakes on a fast random wobble, the jaw opens, and the eyes are
  lit. It comes with the loudest sound on the page, a screech layered from the mob's own scream,
  `qf.scare.jumpscreech` and static. Then screen tear, a short static cut, and the kill. Every
  scare ends its build-up with a lunge, adapted to the mob.
- **Silence is the weapon.** Before the lunge, everything drops away: music, ambience, even your
  footsteps. One small sound, such as a breath, a click or a single note, makes you lean in.
- **Unpredictable timing.** Randomise the dread length (±40%) and use fake-outs. A stinger hits
  with nothing there, you relax, and the real lunge comes 1 to 3 s later from a different
  direction. Knowing it is coming must not help.
- **"It moved when you weren't looking".** The view is turned away, then back, and the threat is
  closer, or gone, which is worse.
- **Power out.** Lights die one by one. In the dark, only eyes, and a tune; a note-block melody
  plays the role of FNAF's music box. When the tune stops, the lunge comes.
- **Static and hallucination.** Single-frame flashes of a face, a "you can't escape"-style
  sign, or the mob somewhere it can't be.

Required changes:
- **Every scare gets a FNAF lunge**, built per mob, and a randomised, fake-out-capable build-up.
  Keep what the owner liked: the creepy-crawly swarms of the Silverfish and Cave Spider, the
  Wither Skeleton's sparks, the in-place staging and the accuracy.
- **Magma Cube, redone.** For example: total darkness, then a single orange core pulsing in the
  black ahead. Thump, thump, the glow vanishes, silence. Small cubes leap at the face from every
  side. The big one opens its layers like a jaw, the core blazing, and lunges into the lens.
- **Wither Skeleton, new ending.** For example: the scrape stops, then silence. The view drifts
  to the side, where nothing is. Turning back, the skull is inches away, jaw jittering, and it
  lunges with a screech. The stone sword runs through: look down at the blade through your chest
  as the wither black creeps in. The head falls and rolls, and from the floor you see your own
  body. It picks the head up to its face, MK-fatality style.
- **Screams.** Use the new recorded-voice set from the audio task (`qf.scare.death_scream`,
  `qf.scare.jumpscreech`, `qf.scare.underwater`). Every kill ends on a man screaming for his life.
- **New: failed jumps at gaps.** Listen for `krypt-gap` (see `krypt-endless.md`). Each approved
  gap death takes over 15% of jumps; until approval, only the J picker plays them.
  - **Lava:** the jump falls short and your toes clip the edge. Your first-person hands grab the
    rim, then the fingers slip. You plunge with the fire overlay and the death scream, and the
    view sinks into orange.
  - **Water:** the jump lands short with a splash. Underwater it is blue and muffled, and you
    struggle toward the light. A zombie's hand grabs your ankle: look down at its face in the
    murk, and it pulls you down. Bubbles, the underwater scream, the bite, blood in the water.
  - Add both to the J picker as "Lava fall" and "Drowned grab".

## v4 (round 7, 2026-10-27): Story Mode, not FNAF
The owner on v3: "The FNAF inspiration was taken too strongly." Only the Enderman and the Creeper
fully satisfy him; both are approved and stay as they are. The Pigman was "almost perfect": less
FNAF. v4 supersedes the v3 rules above wherever they disagree.

Why the Enderman and the Creeper work, and what every scare now does:
- **The mob's own mechanic is the scare.** The stare and the teleport; the silent walk-up, the
  hiss and the swell. Each scare is built on what that mob does in the game.
- **The blow lands in the world.** No face rushing the lens, no jitter, no tear, no static cut.
  The mob steps in, leaps, shoots or bites, the head is knocked (`story.js` kick), and the kill
  leaves a mark: the hole, the crater, the blade, the char.
- **Its own sounds.** The mob's cry at full voice with a low hit under it (`story.js` roar), not
  the screech or a stinger. A death scream is one recorded take that plays through; a second
  one never starts over it.
- **At most one device per scare, and only where the mob explains it**: the lights dying for the
  Skeleton, the Magma Cube and the Wither Skeleton's fog; the freeze in the Cave Spider's trap;
  a short colour split on the Pigman's blow.

Per mob, in one line: Zombie, the look-back to arm's length, or the walk out of the dark while
you back into a second one. Skeleton, the miss, the standoff, the shot. Spider, it crawls the
ceiling and drops in front of you, rears and leaps. Cave Spider, the one on the pit wall rears
and leaps. Witch, Slowness, Poison, then Harming in your face as she bends over you. Slime,
squeezes through the hole or hops onto you. Silverfish, the wall bursts into the swarm. Blaze,
the flare and the two volleys. Ghast, the charge and the fireball across the drop. Magma Cube,
it hops in opening like an accordion, then leaps and comes down on you. Pigman, the step and the
chop, then the horde. Wither Skeleton, it stands over you, rattles and runs you through. Lava
fall, the rim, the slip. Drowned grab, it has your ankles, climbs you and bites.

## v5 (round 8, 2026-10-27): entrances that make sense, sounds that stop
The owner's rules this round, for every scare: no mob appears in view out of nowhere (it comes from a
grave, a door, a hole, the ceiling, or the dark beyond the light); the camera turns only for something
the viewer perceives (a sound, a sight, a touch); mobs act on their own nature and never wait for the
player to look back; every sound and loop a scare starts stops when it ends and on Enter.
- **Sounds that stop.** Every scare sound goes through `scares.js` scareAudio(): a one-shot plays one
  pass even of an event the manifest loops, all are tagged "scare", and Enter stops any still sounding.
  `qfaudio.voices()` lists what is sounding; `node tools/site/scare_flow.mjs [--only A,B] [--mood]`
  plays every scare live and fails if a scare loop still sounds at the death screen or any scare sound
  after Enter (the Silverfish's chitter played on forever: a looping event used as a one-shot).
- **Blaze**: out of the nearest grave (`kr.gravesNear`): a crackle and a breath under the floor turn
  the head to it, the plot in front of the headstone cracks with the glow seeping through, bursts, and
  it rises out of the pit and floats out; then the round-7 volley. No grave within 16 m: the floor ahead.
- **Ghast**: one fireball only, after it has shown itself and charged. On the look-back it floats in
  out of the dark while you look away.
- **Magma Cube** (the owner's script): the lights dim; a size-1 cube comes out of the dark in small,
  low hops (EntitySlime's squish, at most about twice as tall as wide for a tick or two; flame on each
  landing, the small squelch), to your feet, and you look down at it; a heavy thud behind, an orange
  light growing on the floor round it, the big squelch right behind; the head snaps round into the face
  of a massive one (as big as the corridor behind allows, sizes 4 to 12, size 6 in a 4-high crypt),
  which lunges low along the floor as you go over backwards, its slices opening on the core, and takes
  you in: its dark insides with orange seams round you, the core over you, three chews that jolt the
  view, black, the death screen. The engulf is about 2 s, with no full-frame fills.

### Round 8b: the start and the hotbar (all scares)
- **Nothing before the first frame.** The rig's group stays hidden until the scare's first frame has placed
  everything, and its world matrices are brought up to date after every frame's update (the renderer updates them
  before `scene.onBeforeRender`, where the live run evaluates, so every mob was drawn one frame behind: at its build
  pose on the first frame, where it had been on the frame it appeared). The owner saw both as "the mob will flash
  on the screen in front of me, and disappear". `tools/site/scare_flow.mjs` watches every frame from the J press:
  nothing of the rig on screen before the first frame, no mob drawn where its script did not put it, no other
  mob in view.
- **One loadout** (`scares/loadout.js`): an iron sword, an iron pickaxe, 23 torches, 6 bread, 3 apples, four empty
  slots; hunger 8.5 shanks, XP level 7. The selected slot is what the hand holds: no scene draws a bare hand, so an
  empty hand selects an empty slot; the Zombie Pigman's pickaxe selects its slot as it comes up and the slot
  empties as it leaves the hand at the fall; the Wither Skeleton's shadow holds the sword, which is selected. The
  Creeper scatters these items, the Blaze burns them, and at death the hotbar empties (the inventory drops).
