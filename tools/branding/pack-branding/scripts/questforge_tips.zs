# =============================================================================
# Quest Forge - world-load Quest Book tip
# =============================================================================
# Map tip source: JourneyMap announceMod (every join), lang keys
#   jm.common.chat_announcement + jm.common.mapgui_only_ready
#   -> "§eJourneyMap:§f Press [§bJ§f]"
# JourneyMap has no extra custom announce line, so this matches that channel
# via CraftTweaker 3.1 IServer.onPlayerLoggedIn (also every join).
# Keybind confirmed from options.txt: key_key.betterquesting.quests=40 (apostrophe)
# =============================================================================

print("[QuestForge] Registering quest book join tip...");

server.onPlayerLoggedIn(function(event as minetweaker.event.PlayerLoggedInEvent) {
    event.player.sendChat("§eQuest Book:§f Press [§b'§f] to open");
});

<questbook:ItemQuestBook>.addTooltip("§7Press ['] to open your quests.");

print("[QuestForge] Quest book join tip ready.");
