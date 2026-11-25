# 0007 — The friends' server rules

**Date:** 2026-10-25
**Status:** accepted (Decisions sheet 1, cards srv-*; issue #10; `answers/s001.json`).
Source: [server-readiness](../design/server-readiness.md) §6.

## Decisions

| Card | Decision | Note from the author |
|---|---|---|
| srv-pvp | **Leave PvP as it is**: no team, friendly fire stays, Gravity Gun unchanged | "Even if we add team functionality, I think friendly fire is a part of the game too." |
| srv-quests | **Personal progression**: no BetterQuesting parties (`party_enable=0`) | (with act1-05: "I don't want any quest sharing. Everyone has their own quests and their own rewards.") |
| srv-sleep | **Sleep vote**: the night skips when half the players, rounded down, are in bed | "half rounded down" |
| srv-afk | **Idle kick after 30 minutes** | basic for now; deliberate AFK set-ups (a water loop) are fine |
| srv-hub | **A hub at spawn**, spawn-protection 16 | a pre-game area like custom maps, well designed, lots of information, **no portals or utility**; open to more ideas; a **protected trading station** (no PvP, preview a trade before confirming) would be good |
| srv-loaders | **Apply the whole bundle** (Railcraft world anchors uncraftable, Sync chunk loading off, Chest Transporter cannot carry spawners, Time Watch pedestal bonus lowered, Lycanites events from day 2–3, op loaders stop when offline) | "draft something more comprehensive to inform me of the effects and the benefits" next round |
| srv-graves | **Accept the defaults**, written down | "we don't need to tell people not to loot graves. It's an honor based world with an honor based system." |
| srv-tools | **Opis and /tpa, yes. World border, no.** | "I don't like the idea of a world border unless it will really help with server-wide performance. The intent is to pre-generate a map, and to have the world outside of that (the outskirts) as difficult end-game territory which is procedurally generated." |

## Why

Friendly fire, personal quests and an honour system are the author's call about what kind of
server this is. The border contradicted [decision 0003](0003-designed-world.md)'s outskirts
and was proposed for performance, which is unproven; it stays off unless measurement shows
the outskirts hurt everyone, and then as a compromise.

## Consequences

- `build_play_server.py --rules` with these values, `--opis`, no `--world-border`; the rules
  post drops the grave line and keeps PvP as is.
- A loaders explainer (effect and benefit per item, with a per-item revert) goes on sheet 2.
- The hub becomes a design proposal: a lobby that also hosts the Ark-style spawn picker of
  decision 0003, information boards, and a trade station (mechanism to be found or built).
- `/tpa` as a qf-commands unlockable, earned like the other tickets.
