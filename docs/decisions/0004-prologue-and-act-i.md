# 0004 — The Prologue and Act I: structure accepted, parties out, voice rejected

**Date:** 2026-10-25
**Status:** accepted (Decisions sheet 1, cards act1-01 … act1-10; GitHub issue #10;
`answers/s001.json`)

## Decisions

Structure, all as recommended in [review-2026-10-19](../design/quests/review-2026-10-19.md) §5:

1. **Act boundaries** as planned: Twilight splits at the Hydra, TragicMC stays whole in
   Act IV, the Act III finale asks for Ultimate Gear.
2. **One tab per act** ("II: Old Powers" holds Twilight and Witchery side by side).
3. **The /home ticket** ends the Prologue (480 Into the Chronicle).
4. **The jukebox** is a quest reward *and* gets a recipe in qf-content.
6. **17 Prologue quests**, not the lean 12.
7. **Wood and the crafting table** move into Arrival; Act I starts at iron.
8. **The three reward cuts** on the moved quests.
10. **Zombie Pigmen count** toward The First Night.

Two answers overrule the plan:

- **5. Parties: there are none.** The author: "I don't want any quest sharing. Everyone has
  their own quests and their own rewards." Together with sheet 1's srv-quests (personal
  progression) this removes BetterQuesting parties from the design: `party_enable=0` on the
  server, quest 478 You and Your Party goes, every "you and your party" line goes, and the
  act-structure §6 rules that assumed a party (a hunt credits the whole party; finales as a
  convergence of the party's hunts) are void. **Open consequence, for the author:** a hunt
  task credits only the player who lands the kill, so a friend who helped kill the Hydra but
  did not land the final blow gets no credit and must kill it again. See sheet 2.
- **9. The voice is rejected.** "Completely rethink the voice … this just reads as a random
  jumble of words. This isn't a compelling or interesting story, and I'd rather do something
  that doesn't take itself so seriously." The audit 4.7 house voice (hook, true paragraph,
  kept quote, task line) does not spread. WP-10 is halted. The quest writers produce samples
  in a lighter register for the author to pick from before any text is written at scale.

## Why

The data restructure (WP-6) is what the review asked to confirm, and it was confirmed whole.
The party model and the voice were both assumptions the audit made without the author, and
the author rejected both once they were stated plainly.

## Consequences

- `tools/quests/patches/wp6_acts.py --decisions docs/decisions/answers/s001.json` builds the
  draft to these answers; the drafts stay drafts (not applied to `pack/config`) until the
  voice is settled and the texts exist, since the only texts the drafts hold are in the
  rejected voice or are `[WRITE:]` placeholders.
- The writing brief ([wp6-writing-brief](../design/quests/wp6-writing-brief.md)) is amended:
  no party language, 478 removed, voice samples first.
- The jukebox recipe is qf-content code.
