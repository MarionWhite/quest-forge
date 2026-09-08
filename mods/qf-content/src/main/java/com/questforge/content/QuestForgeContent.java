package com.questforge.content;

import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.SidedProxy;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.event.FMLPostInitializationEvent;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import org.apache.logging.log4j.Logger;

// "before:gravestonemod" is load-bearing: GraveStones empties the inventory on
// LivingDeathEvent at HIGHEST priority, and Sacrifice / Soulbound must run ahead
// of it. Sorting this mod first puts DeathHandler first in that bucket.
@Mod(modid = QuestForgeContent.MODID, name = QuestForgeContent.NAME, version = Tags.VERSION,
        dependencies = "before:gravestonemod")
public class QuestForgeContent {

    public static final String MODID = "qfcontent";
    public static final String NAME = "QuestForge Content";

    @Mod.Instance(MODID)
    public static QuestForgeContent instance;

    @SidedProxy(
            clientSide = "com.questforge.content.ClientProxy",
            serverSide = "com.questforge.content.CommonProxy")
    public static CommonProxy proxy;

    public static Logger log;

    /** Captured in preInit; postInit has no accessor for it. */
    private static java.io.File configDir;

    /**
     * Where the mod writes. The census needs this too, and deriving it from the
     * server's working directory gets it wrong on an integrated server.
     */
    public static java.io.File configDir() {
        return configDir;
    }

    public static net.minecraftforge.common.config.Configuration config;

    /** The enchantment book item. */
    public static net.minecraft.item.Item enchantBook;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        log = event.getModLog();
        configDir = event.getModConfigurationDirectory();
        com.questforge.content.net.QFNetwork.register();
        com.questforge.content.survey.OreSurveyStore.setConfigDir(configDir);
        com.questforge.content.survey.OreGenObservations.setConfigDir(configDir);
        ModItems.register();
        ModBlocks.register();

        // Enchantments must register in preInit: IDs are claimed first-come, and
        // Forge freezes the block/item maps before init.
        config = new net.minecraftforge.common.config.Configuration(
                event.getSuggestedConfigurationFile());
        config.load();
        com.questforge.content.ench.QFEnchantments.register(config);
        if (config.hasChanged()) config.save();

        // Registered after the enchantments so its creative list can enumerate them.
        enchantBook = new com.questforge.content.ench.ItemEnchantBook();
        cpw.mods.fml.common.registry.GameRegistry.registerItem(enchantBook, "enchant_book");

        // Death handling registers here, in preInit, on purpose: see DeathHandler.
        net.minecraftforge.common.MinecraftForge.EVENT_BUS.register(
                new com.questforge.content.ench.DeathHandler());

        proxy.preInit(event);
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        ModRecipes.register();

        // One handler object for every enchantment; effects never touch events.
        com.questforge.content.ench.EnchantEventBridge bridge =
                new com.questforge.content.ench.EnchantEventBridge();
        net.minecraftforge.common.MinecraftForge.EVENT_BUS.register(bridge);
        cpw.mods.fml.common.FMLCommonHandler.instance().bus().register(bridge);

        proxy.init(event);
    }

    @Mod.EventHandler
    public void serverStarting(cpw.mods.fml.common.event.FMLServerStartingEvent event) {
        event.registerServerCommand(new com.questforge.content.survey.CommandOreSurvey());
        event.registerServerCommand(new com.questforge.content.census.CommandCensus());
        // Shared playlists belong to the world being opened, so the last world's
        // are dropped rather than carried into this one.
        com.questforge.content.jukebox.PublicPlaylists.reset();
        com.questforge.content.voice.VoiceServer.reset();
    }

    @Mod.EventHandler
    public void serverStopped(cpw.mods.fml.common.event.FMLServerStoppedEvent event) {
        com.questforge.content.jukebox.PublicPlaylists.reset();
        com.questforge.content.voice.VoiceServer.reset();
    }

    @Mod.EventHandler
    public void postInit(FMLPostInitializationEvent event) {
        proxy.postInit(event);

        // Both of these have to wait for postInit, when every mod has finished
        // registering: the audit so it sees the whole registry, and the loot pool so
        // a sealed tome can roll anything that ended up registered.
        com.questforge.content.ench.EnchantLoot.build();

        // A previous measurement, if there is one. Loaded before the distribution
        // is built so Transmuter can use real numbers rather than the heuristic.
        com.questforge.content.survey.OreSurveyStore.load();
        com.questforge.content.survey.OreGenObservations.load();
        com.questforge.content.ench.OreDistribution.build();
        com.questforge.content.ench.EnchantLoot.registerChestLoot();
        EnchantmentAudit.write(configDir);
        log.info(NAME + " loaded.");
    }
}
