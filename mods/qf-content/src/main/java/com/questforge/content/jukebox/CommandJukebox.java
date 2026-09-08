package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;
import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import java.io.File;

/**
 * Client-side controls for the jukebox audio, driven through DirectAudio.
 *
 * Everything here goes to the direct OpenAL path. The old PaulsCode routes are gone:
 * they accept audio, claim to be playing, and render nothing inside Minecraft.
 *
 *   /jb play <path>   decode and play a file at your feet, positionally
 *   /jb tone          known-good reference tone
 *   /jb here          move the playing source to where you stand
 *   /jb gain <0-1>    master gain for our source
 *   /jb diag          what OpenAL is actually doing
 *   /jb stop
 */
public class CommandJukebox extends CommandBase {

    @Override public String getCommandName() { return "jb"; }

    @Override public String getCommandUsage(ICommandSender s) {
        return "/jb play <path> | tone | here | gain <0-1> | range | duck | diag | stop";
    }

    /** Client commands are not op-gated; without this it silently does nothing. */
    @Override public boolean canCommandSenderUseCommand(ICommandSender sender) { return true; }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        EntityPlayer p = Minecraft.getMinecraft().thePlayer;
        if (p == null) return;
        if (args.length == 0) { say(sender, getCommandUsage(sender)); return; }

        String sub = args[0].toLowerCase();

        if ("stop".equals(sub)) {
            DirectAudio.stop();
            say(sender, "stopped");

        } else if ("tone".equals(sub)) {
            say(sender, DirectAudio.startTone(p.posX, p.posY, p.posZ));

        } else if ("play".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /jb play <path to .wav>"); return; }
            StringBuilder sb = new StringBuilder(args[1]);
            for (int i = 2; i < args.length; i++) sb.append(' ').append(args[i]);
            String path = sb.toString().replace("~", System.getProperty("user.home"));
            say(sender, DirectAudio.startFile(new File(path), p.posX, p.posY, p.posZ));

        } else if ("helper".equals(sub)) {
            // "tone" runs the helper's generated-tone mode, which exercises the
            // whole subprocess path without needing capture permission -- useful
            // for separating "the pipe is broken" from "the OS said no".
            boolean tone = args.length > 1 && "tone".equalsIgnoreCase(args[1]);
            try {
                HelperSource hs = tone
                        ? HelperSource.start("--tone")
                        : HelperSource.start("--exclude", ownPid());
                say(sender, DirectAudio.start(hs, p.posX, p.posY, p.posZ));
                for (String line : hs.status()) say(sender, line);
            } catch (Throwable t) {
                say(sender, EnumChatFormatting.RED + "helper failed: " + t.getMessage());
                java.io.File bin = HelperSource.helperBinary();
                say(sender, "looked for: " + (bin == null ? "nothing found" : bin.getPath()));
            }

        } else if ("range".equals(sub)) {
            if (args.length < 3) {
                say(sender, "range is " + DirectAudio.getRefDistance()
                          + " / " + DirectAudio.getMaxDistance()
                          + "   usage: /jb range <full-within> <out-to>");
                return;
            }
            try {
                say(sender, DirectAudio.setRange(Float.parseFloat(args[1]),
                                                 Float.parseFloat(args[2])));
            } catch (NumberFormatException e) {
                say(sender, "both arguments must be numbers");
            }

        } else if ("devices".equals(sub)) {
            for (String d : CaptureSource.devices()) say(sender, d);

        } else if ("capture".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /jb capture <device index>"); return; }
            try {
                int idx = Integer.parseInt(args[1]);
                CaptureSource cs = CaptureSource.open(idx);
                say(sender, DirectAudio.start(cs, p.posX, p.posY, p.posZ));
                say(sender, EnumChatFormatting.GRAY
                        + "use headphones -- capturing a mic through speakers will feed back");
            } catch (Throwable t) {
                say(sender, "capture failed: " + t.getMessage());
            }

        } else if ("here".equals(sub)) {
            DirectAudio.setPosition(p.posX, p.posY, p.posZ);
            say(sender, "moved source to you");

        } else if ("gain".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /jb gain 0.0-1.0"); return; }
            try {
                float g = Float.parseFloat(args[1]);
                DirectAudio.setGain(g);
                say(sender, "gain = " + g);
            } catch (NumberFormatException e) {
                say(sender, "not a number: " + args[1]);
            }

        } else if ("duck".equals(sub)) {
            for (String line : JukeboxTicker.duckDiag(Minecraft.getMinecraft())) say(sender, line);

        } else if ("diag".equals(sub)) {
            for (String line : DirectAudio.diag()) say(sender, line);

        } else {
            say(sender, getCommandUsage(sender));
        }
    }

    /**
     * This JVM's pid, so the helper can exclude Minecraft from a global capture.
     * Without that the game captures its own playback and feeds it straight back in.
     * Java 8 has no ProcessHandle, so it comes from the JMX runtime name, "pid@host".
     */
    private static String ownPid() {
        try {
            String n = java.lang.management.ManagementFactory.getRuntimeMXBean().getName();
            int at = n.indexOf('@');
            return at > 0 ? n.substring(0, at) : "0";
        } catch (Throwable t) {
            return "0";
        }
    }

    private static void say(ICommandSender sender, String msg) {
        sender.addChatMessage(new ChatComponentText(EnumChatFormatting.AQUA + "[jb] "
                + EnumChatFormatting.RESET + msg));
    }
}
