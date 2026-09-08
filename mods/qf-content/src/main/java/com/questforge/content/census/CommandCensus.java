package com.questforge.content.census;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.WorldServer;

import com.questforge.content.QuestForgeContent;

/**
 * /qfcensus -- measures the pack.
 *
 * Everything the enchantment balance rests on is a number about this pack: what a
 * boss hits for, what the best armour actually stops, what the strongest weapon
 * swings for. Those numbers are not in any config in a form worth trusting, and
 * they are not in the jars either once a mod scales them at runtime. So they get
 * measured, here, in the running game.
 *
 * Run "calibrate" first. It has a known answer, and if it fails then nothing else
 * this command produces means anything.
 */
public class CommandCensus extends CommandBase {

    @Override
    public String getCommandName() {
        return "qfcensus";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/qfcensus <calibrate | gear | mobs | all | status | stop>";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 2;   // operators only: it spawns several hundred entities
    }

    @Override
    @SuppressWarnings("rawtypes")
    public List addTabCompletionOptions(ICommandSender sender, String[] args) {
        if (args.length == 1) {
            return getListOfStringsMatchingLastWord(args,
                    new String[] { "calibrate", "gear", "mobs", "all", "status", "stop" });
        }
        return null;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        String action = args.length > 0 ? args[0].toLowerCase() : "status";
        File configDir = configDir();
        WorldServer world = MinecraftServer.getServer().worldServerForDimension(0);

        if ("calibrate".equals(action)) {
            String result = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + result);
            reply(sender, result.startsWith("OK")
                    ? EnumChatFormatting.GREEN + result
                    : EnumChatFormatting.RED + result);
            return;
        }

        if ("gear".equals(action) || "all".equals(action)) {
            reply(sender, "Measuring gear...");
            String cal = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + cal);
            reply(sender, cal.startsWith("OK") ? EnumChatFormatting.GREEN + cal
                                               : EnumChatFormatting.RED + cal);
            long t0 = System.currentTimeMillis();
            GearCensus.run(configDir, CensusProbe.player(world));
            reply(sender, EnumChatFormatting.GREEN + "Gear census written in "
                    + (System.currentTimeMillis() - t0) + " ms. See config/qfcontent-census-*.tsv");
        }

        if ("mobs".equals(action) || "all".equals(action)) {
            if (MobCensus.isRunning()) {
                reply(sender, EnumChatFormatting.YELLOW + "Already running. " + MobCensus.status());
                return;
            }
            String cal = CensusProbe.calibrate(world);
            QuestForgeContent.log.info("[census] calibration: " + cal);
            if (!cal.startsWith("OK")) {
                reply(sender, EnumChatFormatting.RED
                        + "Calibration failed, refusing to run: " + cal);
                return;
            }
            reply(sender, EnumChatFormatting.GREEN + cal);
            MobCensus.start(world, configDir);
            reply(sender, "Mob census started. It spawns every registered entity one at a time; "
                    + "expect a few minutes. /qfcensus status to follow it.");
            return;
        }

        if ("status".equals(action)) {
            reply(sender, MobCensus.status());
            return;
        }

        if ("stop".equals(action)) {
            MobCensus.stop();
            reply(sender, "Stopped.");
            return;
        }

        if (!"gear".equals(action) && !"all".equals(action)) {
            reply(sender, getCommandUsage(sender));
        }
    }

    /**
     * The directory the rest of the mod writes to, captured in preInit.
     * Deriving it from the server's working directory instead gets it wrong on an
     * integrated server, which is where this will usually be run.
     */
    private static File configDir() {
        File dir = QuestForgeContent.configDir();
        return dir != null ? dir : new File(MinecraftServer.getServer().getFile("."), "config");
    }

    private static void reply(ICommandSender sender, String message) {
        sender.addChatMessage(new ChatComponentText("[qfcensus] " + message));
    }
}
