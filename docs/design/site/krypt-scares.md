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
- **Zombie Pigman (your fault):** an idle pigman stands in a side passage, and the camera's arm
  swings and hits it by accident. Every eye in the dark turns red, the angry sound plays, and
  they rush from every passage at once.
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
