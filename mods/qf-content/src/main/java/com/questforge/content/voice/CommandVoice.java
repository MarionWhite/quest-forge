package com.questforge.content.voice;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.util.ChatComponentText;

import java.util.List;

/**
 * Client-side controls for proximity voice.
 *
 * Client-side because every setting here is the listener's own: which microphone,
 * how loud other people are, who they would rather not hear. None of it is the
 * server's business and none of it should need an operator.
 *
 *   /voice                  what is currently going on
 *   /voice mode ptt|open    push-to-talk or open microphone
 *   /voice devices          microphones Java can see
 *   /voice device <n>       pick one, or -1 for the system default
 *   /voice level            live input meter, for setting the gate
 *   /voice threshold <n>    open-mic gate, 0..1
 *   /voice volume <n>       how loud everyone else is, 0..2
 *   /voice mute <player>    toggle one person off
 *   /voice on | off
 */
@SideOnly(Side.CLIENT)
public class CommandVoice extends CommandBase {

    @Override public String getCommandName() { return "voice"; }

    @Override public String getCommandUsage(ICommandSender s) {
        return "/voice mode ptt|open | devices | device <n> | level | threshold <n> "
             + "| volume <n> | mute <player> | on | off";
    }

    /** Client commands are not op-gated; without this it silently does nothing. */
    @Override public boolean canCommandSenderUseCommand(ICommandSender sender) { return true; }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (args.length == 0) { status(sender); return; }

        String sub = args[0].toLowerCase();

        if ("mode".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /voice mode ptt|open"); return; }
            if (args[1].toLowerCase().startsWith("o")) {
                VoiceSettings.setMode(VoiceSettings.Mode.OPEN_MIC);
                say(sender, "§aopen microphone§r -- transmitting whenever you are above "
                        + "the gate (" + VoiceSettings.threshold() + "). "
                        + "Use /voice level to tune it.");
            } else {
                VoiceSettings.setMode(VoiceSettings.Mode.PUSH_TO_TALK);
                say(sender, "§apush to talk§r -- hold "
                        + VoiceKeys.talkKeyName() + " to speak.");
            }

        } else if ("devices".equals(sub)) {
            say(sender, "microphones Java can see:");
            for (String d : VoiceCapture.devices()) say(sender, "  " + d);
            say(sender, "  current: " + (VoiceSettings.device() < 0
                    ? "system default" : String.valueOf(VoiceSettings.device())));

        } else if ("device".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /voice device <n>  (-1 = default)"); return; }
            try {
                VoiceSettings.setDevice(Integer.parseInt(args[1]));
            } catch (NumberFormatException e) {
                say(sender, "not a number: " + args[1]);
                return;
            }
            // The capture thread only reads the device when it opens one, so an
            // already-open microphone has to be dropped for this to take effect.
            VoiceClient.stop();
            VoiceClient.start();
            say(sender, "microphone set to " + (VoiceSettings.device() < 0
                    ? "system default" : String.valueOf(VoiceSettings.device()))
                    + " -- reopening");

        } else if ("level".equals(sub)) {
            say(sender, "input level: " + meter(VoiceClient.inputLevel())
                    + "  " + String.format("%.4f", Float.valueOf(VoiceClient.inputLevel())));
            say(sender, "gate is at " + VoiceSettings.threshold()
                    + " -- run this while speaking, then set the gate just below what you see");

        } else if ("threshold".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /voice threshold <0..1>"); return; }
            try {
                VoiceSettings.setThreshold(Float.parseFloat(args[1]));
            } catch (NumberFormatException e) {
                say(sender, "not a number: " + args[1]);
                return;
            }
            say(sender, "open-mic gate now " + VoiceSettings.threshold());

        } else if ("volume".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /voice volume <0..2>"); return; }
            try {
                VoiceSettings.setVolume(Float.parseFloat(args[1]));
            } catch (NumberFormatException e) {
                say(sender, "not a number: " + args[1]);
                return;
            }
            say(sender, "voice volume now " + VoiceSettings.volume());

        } else if ("mute".equals(sub)) {
            if (args.length < 2) { say(sender, "usage: /voice mute <player>"); return; }
            boolean muted = VoiceSettings.toggleMuted(args[1]);
            say(sender, muted ? "§cmuted " + args[1] : "§aunmuted " + args[1]);

        } else if ("on".equals(sub)) {
            VoiceSettings.setEnabled(true);
            say(sender, "§avoice on");

        } else if ("off".equals(sub)) {
            VoiceSettings.setEnabled(false);
            VoiceClient.stop();
            VoicePlayback.stopAll();
            say(sender, "§cvoice off -- microphone released");

        } else {
            status(sender);
        }
    }

    private void status(ICommandSender sender) {
        say(sender, "§6proximity voice§r");
        say(sender, "  enabled  : " + VoiceSettings.isEnabled()
                + (VoiceSettings.isMuted() ? "  §c(mic muted)" : "")
                + (VoiceSettings.isDeafened() ? "  §c(deafened)" : ""));
        say(sender, "  mode     : " + (VoiceSettings.mode() == VoiceSettings.Mode.OPEN_MIC
                ? "open mic, gate " + VoiceSettings.threshold()
                : "push to talk (" + VoiceKeys.talkKeyName() + ")"));
        say(sender, "  capture  : " + (VoiceClient.isCaptureRunning() ? "running" : "stopped")
                + (VoiceClient.isTransmitting() ? "  §asending" : ""));
        say(sender, "  input    : " + meter(VoiceClient.inputLevel()));
        if (VoiceClient.micSeemsSilent()) {
            say(sender, "  §cthe microphone is open but completely silent§r -- check the");
            say(sender, "  §csystem microphone permission for Java, or a hardware mute§r");
        }
        say(sender, "  volume   : " + VoiceSettings.volume()
                + "   range " + VoiceFormat.FULL_RANGE + " to "
                + VoiceFormat.MAX_RANGE + " blocks");
        say(sender, "  hearing  : " + VoicePlayback.activeVoices() + " nearby");

        List<String> talking = VoicePlayback.speaking();
        if (!talking.isEmpty()) say(sender, "  speaking : " + join(talking));
        if (!VoiceSettings.mutedPlayers().isEmpty()) {
            say(sender, "  muted    : " + join(
                    new java.util.ArrayList<String>(VoiceSettings.mutedPlayers())));
        }
        if (VoiceClient.lastError() != null) {
            say(sender, "  §clast error: " + VoiceClient.lastError());
        }
    }

    private static String join(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(s);
        }
        return sb.toString();
    }

    /** A twenty-cell bar. Speech sits low on a linear scale, so this is amplified. */
    private static String meter(float level) {
        int filled = (int) Math.min(20f, level * 20f * 5f);
        StringBuilder sb = new StringBuilder("§a");
        for (int i = 0; i < 20; i++) {
            if (i == filled) sb.append("§8");
            sb.append(i < filled ? '|' : '.');
        }
        return sb.append("§r").toString();
    }

    private static void say(ICommandSender sender, String message) {
        sender.addChatMessage(new ChatComponentText(message));
    }
}
