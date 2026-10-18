# Angelica client: the 30-minute hand test

The unattended probe (2026-10-17, [`../design/angelica-decision.md`](../design/angelica-decision.md))
placed, used and photographed everything it could. These checks need a person:
real mouse and keyboard input, or watching something move. Do them on the
Angelica client built by `tools/angelica-client/build_angelica_client.py`
(`LAUNCH-ANGELICA.bat`), in a creative singleplayer world with cheats on.

Do every check twice: once with shaders off, once with **Complementary
Unbound** on. Press **F8** for the shader-pack screen (or **F4** to toggle the
pack you last picked). The first switch takes 10 to 30 seconds while the pack
compiles.

Write down pass/fail and anything odd. If something breaks, keep the world and
copy `logs\latest.log` before restarting.

## Before you start (2 min)

- [ ] The loading screen is the Quest Forge one: the knight mural fills the
      screen, the bars are glowing magma troughs, the corner emblem breathes,
      and the chant plays from the first second. At the title screen the menu
      music swells in while the chant fades. If it looks like Forge's white
      screen with red bars, stop: the QuestForgeTweaks jar is wrong.
- [ ] `/gamemode 1`, `/time set 6000`, `/weather clear`, `/difficulty 0`.

## PortalGun (5 min)

- [ ] Give yourself both guns: `/give @p PortalGun:PortalGunBlue` and
      `/give @p PortalGun:PortalGunOrange`.
- [ ] Fire blue (right click) at one wall and orange at another, about ten
      blocks apart. Both portals appear, flat on the wall, the right colour.
- [ ] Look into each portal. You see through to the other side: the view
      inside is the room at the other portal, not black, not the sky, not a
      flickering copy of your own screen.
- [ ] Walk through both ways. You come out of the other portal facing away
      from it.
- [ ] With Complementary on: the view through the portal still renders (it may
      be darker or flatter than the main view; black or a frozen image is a fail).

## Transformers (5 min)

- [ ] Equip a full Transformer armour set from the creative tab (the
      Transformers tab; Skystrike is a jet).
- [ ] Press the transform key (**Up arrow** by default). The robot turns into
      its vehicle with the animation, and back again on the second press.
- [ ] In vehicle form: drive or fly a few seconds. The model has its textures,
      nothing is stretched or missing.
- [ ] With Complementary on: the robot and the vehicle render (Transformers
      takes its own shader-safe path; there should be no black or see-through
      parts).

## MCHeli (5 min)

- [ ] Take a helicopter from the MCHeli creative tab (the AH-64 Apache is a
      good one) and place it on flat ground.
- [ ] Get in (right click). Hold **W** (MCHeli's throttle, `KeyUp` in
      `config\mcheli.cfg`). The main and tail rotors spin up and keep spinning.
      (MCHeli's camera-mode key is also **C**, as it is on the E7 client.)
- [ ] Lift off and fly a short circle. The rotor blur, the cockpit and the
      HUD draw correctly.
- [ ] With Complementary on: the rotors still spin and are visible, and the
      cockpit glass is not an opaque black sheet.

## Malisis doors (2 min)

- [ ] Place a wooden door, a trapdoor and a fence gate. Open and close each.
      They **swing** smoothly over a fraction of a second rather than snapping
      open (Malisis animates them).
- [ ] Same with Complementary on.

## Morph (4 min)

- [ ] Kill a pig (or any mob) with a sword. Its morph is acquired: the
      acquisition animation plays and you are not kicked.
- [ ] Open the morph selector (**[** and **]** by default), pick the pig and
      confirm. You turn into the pig with the transition animation and the
      game keeps running (the old bug was a silent freeze here).
- [ ] Switch back to yourself from the selector.
- [ ] Known and harmless: `/morph morph <you> Pig` answers "Error creating mob
      morph" if you already own the pig morph. That is Morph refusing a morph
      you already have, not a renderer problem; pick it from the selector instead.

## Shaders and the pack's own renderers (4 min)

- [ ] Place a qf-content **jukebox** and a **record case** on a wall with a
      record in it (`qfcontent:record_case`, `qfcontent:record`). With shaders
      off the case shows its glass reflection; with Complementary on the mat,
      the record and the plaque stay visible behind the frame (not a black
      rectangle) and the jukebox chrome is not dark.
- [ ] Hold a torch and a glowstone block in the dark. Dynamic light follows you
      (Angelica's own dynamic lights).
- [ ] Press **C**: the view zooms like OptiFine's zoom and returns when released.

## Psychedelicraft (2 min, record only)

- [ ] Drink or smoke something from Psychedelicraft. Write down whether the
      screen effects appear. Under Angelica its drug-vision shaders fail to
      compile ("Error creating shader" in the log), so the effects are expected
      to be missing. **Nothing to fix here**: whether that is acceptable is still
      undecided.

## Frame rate (1 min)

- [ ] F3 in a busy spot. The frame rate is above your monitor's refresh rate
      with shaders off (Angelica's vsync is off by default; nothing should pin
      it at exactly 60, 144 or 240).

## Report

For each section: pass, fail, or "looks odd" with a screenshot (F2 saves to
`screenshots\`). Send the list, the screenshots of any failures, and
`logs\latest.log`.
