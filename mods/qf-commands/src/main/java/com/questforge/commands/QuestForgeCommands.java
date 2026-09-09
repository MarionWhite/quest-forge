package com.questforge.commands;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import net.minecraft.item.Item;
import net.minecraftforge.common.MinecraftForge;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import cpw.mods.fml.common.event.FMLServerStartingEvent;
import cpw.mods.fml.common.network.NetworkRegistry;
import cpw.mods.fml.common.registry.GameRegistry;

/**
 * Commands a player earns by finding a ticket, rather than by being given op.
 *
 * The whole mod is one registry ({@link Unlockables}), one item that redeems an
 * entry from it, and one CommandBase per entry. Adding a command touches only
 * the registry.
 */
@Mod(modid = QuestForgeCommands.MODID, name = "QuestForge Commands",
     version = "1.0.0", acceptableRemoteVersions = "*")
public class QuestForgeCommands {

    public static final String MODID = "qfcommands";

    public static final int GUI_VAULT = 0;

    @Mod.Instance(MODID)
    public static QuestForgeCommands instance;

    public static Item ticket;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        ticket = new ItemTicket();
        GameRegistry.registerItem(ticket, "lottery_ticket");
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        NetworkRegistry.INSTANCE.registerGuiHandler(this, new GuiHandler());
        MinecraftForge.EVENT_BUS.register(new TicketLoot());

        // PlayerChangedDimensionEvent is posted on FML's bus, not Forge's, so
        // registering this on EVENT_BUS would compile, load, and silently never
        // fire.
        FMLCommonHandler.instance().bus().register(new TravelTips());
    }

    /**
     * Commands are registered per server start, which is where 1.7.10 wants
     * them: the handler is rebuilt for each world, so registering once at init
     * would leave the second world you open with none.
     *
     * <h3>Why the name check</h3>
     *
     * CommandHandler.registerCommand does a plain map put on the command's own
     * name, so registering a name another mod already took silently replaces
     * theirs -- and with 119 mods loaded, single words like "mining" and "end"
     * are not safe to assume. Taking someone else's command away is worse than
     * not having ours, so a clash is skipped and named in the log, where it can
     * be fixed by renaming the entry in {@link Unlockables}.
     */
    @Mod.EventHandler
    public void serverStarting(FMLServerStartingEvent event) {
        Map<?, ?> taken = event.getServer().getCommandManager().getCommands();

        if (!taken.containsKey("commands")) {
            event.registerServerCommand(new CommandList());
        }

        int dimensions = 0;
        int registered = 0;
        List<String> clashes = new ArrayList<String>();

        for (Unlockable u : Unlockables.all()) {
            // One registration per name: an entry that carries both /home and
            // /sethome needs both words to exist, sharing the one unlock.
            for (String name : u.commands) {
                if (taken.containsKey(name)) {
                    clashes.add(name);
                    continue;
                }

                event.registerServerCommand(new UnlockedCommand(u, name));
                registered++;
            }

            if (u instanceof DimensionTravel) {
                dimensions++;
            }
        }

        // Says what actually registered. The failure this catches is a command
        // silently missing because its entry was added to the registry but the
        // world was opened before the mod reloaded -- which looks identical to
        // the command simply not existing.
        int names = 0;

        for (Unlockable u : Unlockables.all()) {
            names += u.commands.length;
        }

        System.out.println("[QuestForgeCommands] registered " + registered + " of " + names
                + " commands across " + Unlockables.count() + " tickets ("
                + dimensions + " dimensions)");

        if (!clashes.isEmpty()) {
            System.out.println("[QuestForgeCommands] NOT registered, name already taken by"
                    + " another mod: /" + join(clashes, ", /")
                    + " -- rename these in Unlockables to make their tickets work.");
        }
    }

    private static String join(List<String> parts, String separator) {
        StringBuilder out = new StringBuilder();

        for (String part : parts) {
            if (out.length() > 0) {
                out.append(separator);
            }
            out.append(part);
        }

        return out.toString();
    }
}
