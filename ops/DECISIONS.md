# Open decisions for the owner

Newest first. Each entry has options and a recommendation. When answered, record the answer in
the track's journal (or in docs/decisions/ for lasting calls) and delete the entry here. The
Decisions page (site) is generated from this list.

## Textures
- **Connected glass panes.** Turn on `glassPane=true` in `config/mcpatcherforge.cfg` so panes
  connect like glass blocks do. This is a one-line pack config change. *Recommend: yes.*
- **How QF Textures ships.** The pack contains recoloured vanilla pixels, which we can't put in a
  public repo. *Recommend:* the Prism instance builds it at install time from the player's own
  minecraft.jar, so no Mojang pixels are ever distributed.

## Harness / PC
- **The last ~10 ms of focus risk.** LWJGL calls SetForegroundWindow once per test-client launch,
  and the guard hands focus back within 10 ms. Removing it fully needs a qf-tweaks transformer
  that drops the call for background trials, which means a live-jar install. *Recommend:* yes,
  low risk, but it is the owner's call.

## Server
- **"Who's online" publishing** (supervisor `status_publisher`). It would show friends'
  Minecraft names on the public site. *Recommend:* ask the friends first; it's off until then.
