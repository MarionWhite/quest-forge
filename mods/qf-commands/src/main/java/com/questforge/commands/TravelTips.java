package com.questforge.commands;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.PlayerEvent;

/**
 * Tells a player how to get home, shortly after they need to know.
 *
 * The ticket that sent them somewhere said so too, but that text scrolled past
 * during a dimension change and is now behind a loading screen. This is the
 * reminder at the moment it becomes useful: standing somewhere new, wondering
 * how to leave.
 *
 * <h3>Why it stops</h3>
 *
 * It shows {@link #TIMES} times and then never again. A line that appears on
 * every dimension change forever is noise to anyone who commutes through the
 * Twilight Forest, and a tip that outlives its usefulness trains people to
 * ignore the chat. The count lives in the player's persistent NBT, so it is
 * per-player and survives logout rather than resetting every session.
 *
 * <h3>Why it hooks the dimension change and not the command</h3>
 *
 * A player who walks into a nether portal is exactly as stranded as one who
 * typed a command, so the reminder belongs on arriving anywhere, however they
 * got there. PlayerChangedDimensionEvent covers both.
 */
public class TravelTips {

    /** How many times a player is told, before it stops mentioning it. */
    private static final int TIMES = 3;

    private static final String ROOT = "QFCommands";
    private static final String TAG = "HomeTipsShown";

    @SubscribeEvent
    public void onChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event) {
        if (!(event.player instanceof EntityPlayerMP)) {
            return;
        }

        EntityPlayerMP player = (EntityPlayerMP) event.player;

        // Arriving home needs no directions home.
        if (event.toDim == 0) {
            return;
        }

        Unlockable home = Unlockables.wayHome();

        // Never advertise a command they cannot run. Someone who reached the
        // Nether through a portal with no tickets at all would only be told
        // about a way out they do not have, which is worse than silence.
        if (home == null || !Unlocks.has(player, home.id)) {
            return;
        }

        int shown = shown(player);

        if (shown >= TIMES) {
            return;
        }

        setShown(player, shown + 1);

        player.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY + "Type "
                + EnumChatFormatting.GREEN + "/" + home.command() + EnumChatFormatting.GRAY
                + " at any time to return to the Overworld."));

        if (shown + 1 == TIMES) {
            player.addChatMessage(new ChatComponentText(EnumChatFormatting.DARK_GRAY
                    + "(That is the last time this reminder appears. "
                    + EnumChatFormatting.WHITE + "/commands"
                    + EnumChatFormatting.DARK_GRAY + " lists everything you have.)"));
        }
    }

    private static NBTTagCompound mine(EntityPlayer player, boolean create) {
        NBTTagCompound data = player.getEntityData();
        NBTTagCompound persist = data.getCompoundTag(EntityPlayer.PERSISTED_NBT_TAG);
        NBTTagCompound root = persist.getCompoundTag(ROOT);

        if (create) {
            persist.setTag(ROOT, root);
            data.setTag(EntityPlayer.PERSISTED_NBT_TAG, persist);
        }

        return root;
    }

    private static int shown(EntityPlayer player) {
        return mine(player, false).getInteger(TAG);
    }

    private static void setShown(EntityPlayer player, int count) {
        mine(player, true).setInteger(TAG, count);
    }
}
