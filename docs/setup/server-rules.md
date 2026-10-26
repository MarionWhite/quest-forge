# Quest Forge server rules

The post for the friends, 2026-10-25. Short on purpose: it goes on a board at
the hub and in the Discord. Every rule here is the owner's decision
([decision 0007](../decisions/0007-server-rules.md)); the server settings behind
them are `tools/server/rules.json`, applied with `build_play_server.py --rules`
([`hosting-a-server.md`](hosting-a-server.md#the-owners-decisions-rules)).

---

**Welcome to Quest Forge.** It is a small server for friends. These rules exist
so nobody loses a week of work, and so the server stays fast enough for all of
us.

1. **Ask before you touch it.** Other people's builds, chests, machines, pets
   and vehicles are theirs. Griefing is only for consenting targets. Half the
   pack breaks blocks (ICBM, OreSpawn bosses, MCHeli, Lucky Blocks, Pandora's
   Box): aim them away from anyone's base.

2. **PvP is on, and friendly fire is part of the game.** Stray hits from
   Legends powers, helicopters, missiles and the Gravity Gun hurt your friends
   the same as anyone, so aim with care and stand clear of a fight you are not
   in. A duel needs nobody's permission but your opponent's.

3. **Quests are personal.** There are no quest parties: everyone has their own
   quests and their own rewards. Lending someone the item a quest asks for is
   fine (the book does not take it), but earn your own big rewards instead of
   passing one set around.

4. **Sleep.** When half the people online, rounded down, are in bed, the night
   skips: one of two, two of four, three of six. With three, five or seven
   online it takes one more (two, three, four); from eight up it is exactly
   half. Anyone underground (below sea level) is not counted either way. If it
   is night and you are busy, hop in a bed when asked.

5. **AFK.** The server kicks you after 30 minutes idle. An idle player keeps
   169 chunks and a full share of monsters loaded all night, so log out
   instead. A deliberate AFK set-up (a water loop that keeps you moving, say)
   is fine.

6. **The hub at spawn.** Spawn is the shared place: the rules board, the
   information boards and, once it is built, the trading station. There are no
   portals and nothing useful parked there on purpose. The 16 blocks around
   spawn are protected: you cannot place or break there. Build your own base
   elsewhere, and keep machines and farms out of the spawn chunks: they run 24
   hours a day there.

7. **Chunk loaders.** ChickenChunks loaders: up to 49 chunks each of you, and
   they switch off while you are offline (the host's too). Railcraft World
   Anchors cannot be crafted here; use Personal Anchors (they run on ender
   pearls while you are online). Sync shells do not keep chunks loaded. If your
   base needs more than that, ask.

8. **The things that melt the server.** Chest Transporters do not pick up mob
   spawners here, and the Watch of Flowing Time in a pedestal gives machines
   no speed bonus. Park Archimedes ships by decompiling them; a parked ship
   entity is how ships get lost.

9. **Ender Chests are shared.** Anyone who sets the same three colours opens
   the same chest. Diamond-lock yours for a private one; use the shared
   colours as mailboxes.

10. **Backups and restarts.** The world is backed up every hour and the server
    restarts every day at 05:00 (you get 10, 5 and 1 minute warnings). If
    something of yours vanishes, say when it happened; an hourly backup can
    bring it back.

11. **Stay on the current pack.** Install from the release link, never by
    adding mods yourself. If the server refuses you, read
    [why-was-i-refused.md](why-was-i-refused.md): it tells you which side is
    out of date.

---

## Not rules, but good to know

- When you die, a grave holds your things, and death costs 5 skill points, so
  bring a Sync shell or a bed before a boss. It is an honour-based world: we
  trust you with each other's graves.
- The server is in online mode: your Minecraft name is your account's name.
- `/home`, the vault and dimension tickets are unlocked through qf-commands'
  lottery tickets. `/tpa <player>` (ask to teleport to a friend; they answer
  `/tpaccept`, which needs no ticket) is built and arrives with the next pack
  release.
- Lycanites' random mob events start on day 3, not day 0.
- Voice chat is proximity-based and cuts at 40 blocks.
- Flight is allowed (Transformers, Legends, gliders), so flying is not a
  cheat report.
- Two known crashes (Legends lightning) restart the server within a minute.
  If it happens, wait, then reconnect.
