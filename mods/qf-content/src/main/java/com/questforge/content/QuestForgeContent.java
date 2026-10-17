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
        com.questforge.content.pack.PackCheck.loadConfig(config);
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

        // The login pack check (server side; harmless on a client).
        cpw.mods.fml.common.FMLCommonHandler.instance().bus().register(
                new com.questforge.content.pack.PackCheck.Events());

        proxy.init(event);
    }

    @Mod.EventHandler
    public void serverStarting(cpw.mods.fml.common.event.FMLServerStartingEvent event) {
        event.registerServerCommand(new com.questforge.content.survey.CommandOreSurvey());
        event.registerServerCommand(new com.questforge.content.census.CommandCensus());
        event.registerServerCommand(new com.questforge.content.pack.CommandPack());
        // Shared playlists belong to the world being opened, so the last world's
        // are dropped rather than carried into this one.
        com.questforge.content.jukebox.PublicPlaylists.reset();
        com.questforge.content.voice.VoiceServer.reset();
    }

    /**
     * Starts a combat census automatically when the JVM was told to.
     *
     * A census takes an hour and a half, and driving it by typing into the
     * server's console ties it to whatever shell is holding that pipe -- close the
     * terminal, lose the run. Passing
     * {@code -Dqf.census.combat="Zombie TwilightForest.Hydra"} instead lets the
     * server be launched fully detached and finish on its own. The value is the
     * same argument list {@code /qfcensus combat} takes, so a target list and an
     * item registry name for the weapon both work.
     *
     * Started here rather than in serverStarting because the world has to exist
     * before anything can be spawned into it.
     */
    @Mod.EventHandler
    public void serverStarted(cpw.mods.fml.common.event.FMLServerStartedEvent event) {
        // -Dqf.census.autorun="mobs" runs any census subcommand; -Dqf.census.combat
        // is the older spelling for the combat one and still works.
        String request = System.getProperty("qf.census.autorun");
        java.util.List<String> args = new java.util.ArrayList<String>();
        if (request == null || request.trim().isEmpty()) {
            request = System.getProperty("qf.census.combat");
            if (request == null || request.trim().isEmpty()) return;
            args.add("combat");
        }

        log.info("[census] automatic census requested: " + request);
        // Commas as well as spaces, because a JVM property containing a space has
        // to survive whatever shell launched the server and frequently does not:
        // the first attempt at this arrived as a bare "Zombie" plus a demand to
        // load a main class named "TwilightForest.Hydra".
        for (String part : request.trim().split("[\\s,]+")) {
            if (!part.isEmpty()) args.add(part);
        }

        // Through the command itself, so an automated run goes past exactly the
        // same calibration gates a typed one does.
        com.questforge.content.census.CommandCensus command =
                new com.questforge.content.census.CommandCensus();
        try {
            command.processCommand(net.minecraft.server.MinecraftServer.getServer(),
                    args.toArray(new String[args.size()]));
        } catch (Throwable t) {
            log.error("[census] automatic combat census failed to start", t);
            return;
        }

        // Nobody is watching a detached server, so it stops itself when the run
        // finishes -- that is also what closes the output files.
        String what = args.isEmpty() ? "" : args.get(0).toLowerCase();
        if ("combat".equals(what)) {
            com.questforge.content.census.CombatCensus.stopServerWhenFinished();
        } else if ("mobs".equals(what) || "all".equals(what)) {
            com.questforge.content.census.MobCensus.stopServerWhenFinished();
        } else {
            // A one-shot command (gear, find, calibrate) is already finished.
            try {
                net.minecraft.server.MinecraftServer.getServer().initiateShutdown();
            } catch (Throwable ignored) {}
        }
    }

    @Mod.EventHandler
    public void serverStopped(cpw.mods.fml.common.event.FMLServerStoppedEvent event) {
        com.questforge.content.jukebox.PublicPlaylists.reset();
        com.questforge.content.voice.VoiceServer.reset();
    }

    /**
     * The pack fingerprint is taken here, after every mod's postInit, because mods
     * write their configs (and qf-content its own enchantment IDs) while loading;
     * the fingerprint has to describe the files as the game actually used them.
     */
    @Mod.EventHandler
    public void loadComplete(cpw.mods.fml.common.event.FMLLoadCompleteEvent event) {
        com.questforge.content.pack.PackCheck.computeLocal(configDir);
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
