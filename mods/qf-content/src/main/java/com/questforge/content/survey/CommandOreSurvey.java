package com.questforge.content.survey;

import java.util.List;
import java.util.Map;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.WorldServer;

import net.minecraft.server.MinecraftServer;

/**
 * /qfsurvey -- drives the ore survey.
 *
 * The whole point is that nobody has to fly anywhere: "start" generates chunks
 * server-side, counts them and discards them, entirely without a player.
 */
public class CommandOreSurvey extends CommandBase {

    private static final int DEFAULT_CHUNKS = 5000;

    /**
     * Deliberately high. The interesting ores are the rare ones, and a rare ore is
     * exactly the thing a small sample gets wrong: at one vein per several hundred
     * chunks, a thousand-chunk survey is measuring noise. There is no reason to cap
     * this below what someone is willing to wait for.
     */
    private static final int MAX_CHUNKS = 1000000;

    @Override
    public String getCommandName() {
        return "qfsurvey";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/qfsurvey <start [chunksPerDim] [budgetMs] [dim] | status | stop | show | missing | clear>";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 2;   // operators only: it generates terrain
    }

    @Override
    @SuppressWarnings("rawtypes")
    public List addTabCompletionOptions(ICommandSender sender, String[] args) {
        if (args.length == 1) {
            return getListOfStringsMatchingLastWord(args,
                    new String[] { "start", "status", "stop", "show", "clear", "missing", "veins" });
        }
        return null;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        String action = args.length > 0 ? args[0].toLowerCase() : "status";

        if ("start".equals(action)) {
            start(sender, args);
        } else if ("stop".equals(action)) {
            OreSurvey.stop();
            say(sender, EnumChatFormatting.YELLOW, "Survey stopped and saved.");
        } else if ("clear".equals(action)) {
            OreSurvey.clear();
            OreSurveyStore.save();
            say(sender, EnumChatFormatting.YELLOW, "Survey data cleared.");
        } else if ("veins".equals(action)) {
            veins(sender);
        } else if ("missing".equals(action)) {
            missing(sender);
        } else if ("show".equals(action)) {
            show(sender, args.length > 1 ? Math.max(1, parseInt(sender, args[1])) : 20);
        } else {
            status(sender);
        }
    }

    private void start(ICommandSender sender, String[] args) {
        if (OreSurvey.isRunning()) {
            say(sender, EnumChatFormatting.RED, "A survey is already running. /qfsurvey status");
            return;
        }

        int chunks = DEFAULT_CHUNKS;
        if (args.length > 1) {
            chunks = Math.max(1, Math.min(MAX_CHUNKS, parseInt(sender, args[1])));
        }

        // Optional: milliseconds of each tick to spend. Left off, the survey decides
        // for itself based on whether anyone is online.
        int budgetMs = 0;
        if (args.length > 2) {
            budgetMs = Math.max(1, Math.min(45, parseInt(sender, args[2])));
        }

        // With no dimension named, survey ALL of them. An overworld-only survey
        // misses every nether and End ore, and this pack has dozens of dimensions --
        // nobody should have to drive that by hand.
        if (args.length > 3) {
            int dim = parseInt(sender, args[3]);
            WorldServer world = MinecraftServer.getServer().worldServerForDimension(dim);
            if (world == null) {
                say(sender, EnumChatFormatting.RED, "Dimension " + dim + " is not loaded.");
                return;
            }
            OreSurvey.start(world, chunks, budgetMs);
            say(sender, EnumChatFormatting.GREEN, "Surveying " + chunks
                    + " chunks in dimension " + dim + ". Run /qfsurvey status.");
            return;
        }

        OreSurvey.startAll(chunks, budgetMs);
        say(sender, EnumChatFormatting.GREEN, "Surveying " + chunks
                + " chunks in EVERY dimension. No player needed; run /qfsurvey status.");
    }

    private void status(ICommandSender sender) {
        if (OreSurvey.isRunning()) {
            say(sender, EnumChatFormatting.AQUA, "Running: " + OreSurvey.completed()
                    + " measured, " + OreSurvey.remaining() + " to go ("
                    + OreSurvey.generated() + " chunks generated).");
        } else {
            say(sender, EnumChatFormatting.GRAY, "Not running.");
        }
        say(sender, EnumChatFormatting.GRAY, "Total chunks sampled: " + OreSurvey.chunksSampled()
                + " | ore types known: " + OreSurvey.knownOreTypes()
                + " | observed: " + OreSurvey.counts().size());

        for (Map.Entry<Integer, Integer> e : OreSurvey.chunksByDimension().entrySet()) {
            Map<Integer, Integer> perDim =
                    OreSurvey.countsByDimension().get(e.getKey());
            say(sender, EnumChatFormatting.DARK_GRAY, "  dim " + e.getKey() + ": "
                    + e.getValue() + " chunks, "
                    + (perDim == null ? 0 : perDim.size()) + " ore types");
        }
    }

    /**
     * The exact generation parameters, read off the running game.
     *
     * Not a sample of the result -- the arguments the generator was written with:
     * how many veins per chunk, how big, in what height band.
     */
    private void veins(ICommandSender sender) {
        java.util.Map<Integer, java.util.Map<Integer, OreGenObservations.Vein>> all =
                OreGenObservations.byDimension();

        if (all.isEmpty()) {
            say(sender, EnumChatFormatting.GRAY, "No veins recorded yet. Run /qfsurvey start.");
            return;
        }

        for (Map.Entry<Integer, java.util.Map<Integer, OreGenObservations.Vein>> dim
                : all.entrySet()) {

            // The chunks the recorder actually watched, NOT the survey's running
            // total -- see OreGenObservations.WATCHED.
            int chunks = OreGenObservations.watched(dim.getKey().intValue());
            if (chunks <= 0) continue;

            com.questforge.content.QuestForgeContent.log.info("--- Dimension " + dim.getKey()
                    + ", veins watched over " + chunks + " chunks ("
                    + OreGenObservations.uncounted(dim.getKey().intValue())
                    + " of them yielded no block count) ---");
            com.questforge.content.QuestForgeContent.log.info(String.format(
                    "    %-44s %10s %8s %10s", "ore", "veins/chunk", "size", "y range"));

            for (Map.Entry<Integer, OreGenObservations.Vein> e : dim.getValue().entrySet()) {
                OreGenObservations.Vein v = e.getValue();
                com.questforge.content.QuestForgeContent.log.info(String.format(
                        "    %-44s %10.3f %8.1f %4d..%-4d",
                        OreSurveyStore.describe(e.getKey().intValue()),
                        (double) v.veins / chunks,
                        v.averageSize(), v.minY, v.maxY));
            }
        }

        say(sender, EnumChatFormatting.AQUA,
                "Exact vein parameters for " + all.size() + " dimension(s) written to the log.");
    }

    /**
     * Ore-dictionary entries the survey has never seen, so they can be judged.
     *
     * Goes to the log rather than to chat: there can be dozens, and the point is to
     * read them next to each other.
     */
    private void missing(ICommandSender sender) {
        java.util.List<String> lines = OreSurvey.missing();

        com.questforge.content.QuestForgeContent.log.info("--- Ore types never observed ("
                + lines.size() + " of " + OreSurvey.knownOreTypes() + " known keys), after "
                + OreSurvey.chunksSampled() + " chunks ---");
        for (String line : lines) {
            com.questforge.content.QuestForgeContent.log.info("    " + line);
        }
        com.questforge.content.QuestForgeContent.log.info("--- end ---");

        say(sender, EnumChatFormatting.AQUA, lines.size() + " ore-dictionary entries never "
                + "observed in " + OreSurvey.chunksSampled() + " chunks; listed in the log.");
    }

    /** The most abundant ores measured so far, as a share of all ore seen. */
    private void show(ICommandSender sender, int limit) {
        if (OreSurvey.counts().isEmpty()) {
            say(sender, EnumChatFormatting.GRAY, "Nothing measured yet. /qfsurvey start");
            return;
        }

        List<Map.Entry<Integer, Integer>> entries = OreSurveyStore.ranked();

        long total = 0;
        for (Map.Entry<Integer, Integer> e : entries) total += e.getValue().intValue();
        if (total <= 0) return;

        say(sender, EnumChatFormatting.AQUA, "Measured over "
                + OreSurvey.chunksSampled() + " chunks, " + entries.size() + " ore types:");

        for (int i = 0; i < entries.size() && i < limit; i++) {
            Map.Entry<Integer, Integer> e = entries.get(i);
            double share = (100.0 * e.getValue().intValue()) / total;
            double perChunk = OreSurvey.chunksSampled() > 0
                    ? (double) e.getValue().intValue() / OreSurvey.chunksSampled() : 0;

            say(sender, EnumChatFormatting.GRAY, String.format("  %-24s %5.2f%%  (%.1f per chunk)",
                    OreSurveyStore.describe(e.getKey().intValue()), share, perChunk));
        }
        say(sender, EnumChatFormatting.DARK_GRAY, "Full results: config/"
                + (OreSurveyStore.file() == null ? "qfcontent-oresurvey.txt"
                                                 : OreSurveyStore.file().getName()));
    }

    /** The sender's world if they have one, otherwise the overworld. */
    private static WorldServer worldOf(ICommandSender sender) {
        if (sender instanceof EntityPlayerMP) {
            net.minecraft.world.World w = ((EntityPlayerMP) sender).worldObj;
            if (w instanceof WorldServer) return (WorldServer) w;
        }

        WorldServer[] worlds = MinecraftServer.getServer().worldServers;
        return (worlds == null || worlds.length == 0) ? null : worlds[0];
    }

    private static void say(ICommandSender sender, EnumChatFormatting colour, String message) {
        sender.addChatMessage(new ChatComponentText(colour + message));
    }
}
