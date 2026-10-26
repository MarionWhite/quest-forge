# Krypt mood layer (design spec, 2026-10-26)

The owner: "very distant echoing mob sounds, and the occasional scampering nearby. Maybe the
light does weird things sometimes, or you catch glimpses of certain mobs peeking at you from
around corners. I want this thing to be truly fucking scary and immersive."

## Rules
- **Rare enough to work.** Pick each event on its own random clock, scaled by depth and stratum.
  - The baseline is one event every 25 to 60 s of active walking.
  - The same kind never plays twice in a row.
  - Nothing plays during a scare or for 20 s after one.
- **Never explained, never resolved.** The visitor never gets a clean look. Peeks vanish when
  the camera turns or comes close, and sounds have no visible source.
- **Spatial and accurate.** Use the audio engine's HRTF panner, positions from the real
  geometry (`__krypt.corners`, side passages, walls) and real Minecraft models and sounds.
- **Mood is on by default.** It is not a jump scare, so no approval list. Reduced motion turns
  off the light effects and peeks, but keeps the sounds.

## Events
- **Distant echoes:** a zombie groan, skeleton rattle, enderman vwoop, ghast cry or spider hiss
  from far away, with a long echo tail, low-passed and coming from deep down the path or a
  side passage. Use the pre-rendered `qf.mood.far_*` set (made by the audio task) or runtime
  reverb plus the low-pass filter.
- **Scampering:** something small runs past behind the wall, left to right, close by, with
  claws on stone (`qf.mood.scamper`). Sometimes it stops right beside you.
- **Light:**
  - a torch ahead sputters and recovers;
  - one goes out as you approach and relights after you pass;
  - all lights pulse dim for a beat, once;
  - a cascade of flickers runs down the corridor toward you and stops just short.
  Use `__krypt.light`.
- **Glimpses:**
  - At the edge of the light, a mob's head and shoulder lean out from behind a corner, look at
    you, and pull back. Candidates: zombie, skeleton, creeper, enderman (tall, at the top of a
    doorway), witch.
  - Spider eyes glow in a side passage and go dark.
  - A creeper stands perfectly still in a dark alcove and is gone the next time it is in view.
  - Use real models from `site/lib/mc`, half-lit, at 12 to 30 blocks away.
- **Close calls (rare, deeper strata only):** breathing right behind you (`qf.mood.breath_near`),
  or a scrape along the wall beside you (`qf.mood.scrape`).

## Hooks
- `?mood=<event>&at=...&dump=1` forces one event for a frame dump.
- `?mood=off` turns the layer off.
- `window.__mood.trigger(kind)` fires an event for testing.
- Shift+M opens a small test list, like the scare picker.
