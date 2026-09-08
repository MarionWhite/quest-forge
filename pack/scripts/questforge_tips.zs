# =============================================================================
# Quest Forge - world-load tips (Quest Book + Map only)
# =============================================================================
# Quest book key: options.txt key_key.betterquesting.quests=40 (apostrophe)
# Map key: options.txt key_key.journeymap.map_toggle=36 (J)
# Minimap: journeymap.minimap.config enabled=true, active=true
# Other join spam is silenced in jars/lang so these two sit at the bottom.
# =============================================================================

print("[QuestForge] Registering join tips...");

server.onPlayerLoggedIn(function(event as minetweaker.event.PlayerLoggedInEvent) {
    event.player.sendChat("§6Quest Forge:§f Press [§b'§f] to open the Quest Book");
    event.player.sendChat("§6Quest Forge:§f Press [§bJ§f] for the map - minimap is on");
});

<questbook:ItemQuestBook>.addTooltip("§7Press ['] to open your quests.");

print("[QuestForge] Join tips ready.");
