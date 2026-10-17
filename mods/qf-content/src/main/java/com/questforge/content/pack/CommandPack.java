package com.questforge.content.pack;

import java.util.Map;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.util.ChatComponentText;

import com.questforge.content.Tags;

/**
 * {@code /qfpack}: what pack this side runs, and what the login check demands.
 *
 * {@code /qfpack files} adds each fingerprinted config's digest, which is how a
 * host finds the file a refused friend has wrong: run tools/pack_fingerprint.py
 * --files on the friend's config folder and compare. Read-only, so anyone may run it.
 */
public class CommandPack extends CommandBase {

    @Override
    public String getCommandName() {
        return "qfpack";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/qfpack [files]";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 0;
    }

    @Override
    public boolean canCommandSenderUseCommand(ICommandSender sender) {
        return true;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        PackFingerprint.Result r = PackCheck.local();
        if (r == null) {
            say(sender, "The pack fingerprint is computed once loading finishes; try again shortly.");
            return;
        }
        say(sender, "Pack " + PackCheck.displayDate(PackCheck.packDate) + ", fingerprint " + r.fingerprint
                + " (qf-content " + Tags.VERSION + ")");
        if (!PackCheck.expectedOverride.isEmpty()) {
            say(sender, "Clients must send " + PackCheck.expectedOverride
                    + " (expectedFingerprint override in qfcontent.cfg)");
        }
        if (!PackCheck.alsoAccept.isEmpty()) {
            say(sender, "Also accepted: " + PackCheck.alsoAccept);
        }
        Map<String, String> mods = PackCheck.localMods();
        say(sender, mods.size() + " mods, digest " + PackFingerprint.modsDigest(mods)
                + "; check " + (PackCheck.enabled ? "on" : "OFF")
                + (PackCheck.checkModVersions ? ", mod versions compared" : ", mod versions not compared"));
        if (args.length > 0 && "files".equalsIgnoreCase(args[0])) {
            for (Map.Entry<String, String> e : r.digests.entrySet()) {
                say(sender, "  " + e.getValue() + "  " + e.getKey());
            }
        }
    }

    private static void say(ICommandSender sender, String text) {
        sender.addChatMessage(new ChatComponentText(text));
    }
}
