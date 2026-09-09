package com.questforge.commands;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.WorldServer;

/**
 * /sethome and /home: one place of your own, and the way back to it.
 *
 * Both halves are one unlockable because they are one idea. A ticket that gave
 * only /home would be useless until you found its other half, and a ticket that
 * gave only /sethome would let you mark a spot you could never return to.
 *
 * <h3>Not a respawn point</h3>
 *
 * This deliberately does not touch the bed spawn. Vanilla's respawn location is
 * a single value that beds, Witchery's rites, TragicMC and the grave mods all
 * read and write, and moving it from under them causes the kind of bug that
 * only shows up the first time somebody dies. The home is this mod's own record
 * and nothing else looks at it.
 */
public class HomeAccess extends Unlockable {

    private static final String ROOT = "QFCommands";
    private static final String TAG = "Home";

    public HomeAccess() {
        super("home", new String[] { "home", "sethome" }, "Home",
                "Two commands, one ticket.",
                "",
                EnumChatFormatting.WHITE + "/sethome" + EnumChatFormatting.GRAY
                        + " marks where you are standing.",
                EnumChatFormatting.WHITE + "/home" + EnumChatFormatting.GRAY
                        + " takes you back to it from anywhere,",
                "including from another dimension.",
                "",
                "You keep one home at a time; setting a new one",
                "replaces the old. It survives death and follows you",
                "between worlds.",
                "",
                "This is NOT your respawn point. Beds, graves and the",
                "mods that move your spawn are left alone, so nothing",
                "here changes where you wake up after dying.",
                "",
                "A rare find in world loot.");
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

    private static NBTTagCompound home(EntityPlayer player) {
        NBTTagCompound root = mine(player, false);
        return root.hasKey(TAG) ? root.getCompoundTag(TAG) : null;
    }

    @Override
    public String refuse(EntityPlayerMP player, String name, String[] args) {
        if ("sethome".equals(name)) {
            return null;
        }

        NBTTagCompound spot = home(player);

        if (spot == null) {
            return "You have not set a home yet. Stand where you want it and type /sethome.";
        }

        if (player.ridingEntity != null || player.riddenByEntity != null) {
            return "Dismount first.";
        }

        MinecraftServer server = MinecraftServer.getServer();

        if (server == null || server.worldServerForDimension(spot.getInteger("Dim")) == null) {
            return "The dimension your home is in is not loaded on this server.";
        }

        return null;
    }

    @Override
    public String run(EntityPlayerMP player, String name, String[] args) {
        return "sethome".equals(name) ? set(player) : go(player);
    }

    private String set(EntityPlayerMP player) {
        NBTTagCompound spot = new NBTTagCompound();
        spot.setDouble("X", player.posX);
        spot.setDouble("Y", player.posY);
        spot.setDouble("Z", player.posZ);
        spot.setFloat("Yaw", player.rotationYaw);
        spot.setFloat("Pitch", player.rotationPitch);
        spot.setInteger("Dim", player.dimension);

        mine(player, true).setTag(TAG, spot);

        return EnumChatFormatting.GOLD + "Home set" + EnumChatFormatting.GRAY + " at "
                + (int) player.posX + ", " + (int) player.posY + ", " + (int) player.posZ + ".";
    }

    private String go(EntityPlayerMP player) {
        NBTTagCompound spot = home(player);
        int dim = spot.getInteger("Dim");
        double x = spot.getDouble("X");
        double y = spot.getDouble("Y");
        double z = spot.getDouble("Z");

        if (player.dimension != dim) {
            MinecraftServer server = MinecraftServer.getServer();
            WorldServer destination = server.worldServerForDimension(dim);

            // The exact spot is known, so the landing scan is skipped entirely --
            // the player stood here to set it. SafeTeleporter is still used
            // because it is the thing that refuses to dig a portal on arrival.
            server.getConfigurationManager().transferPlayerToDimension(player, dim,
                    new SafeTeleporter(destination, new int[] {
                        net.minecraft.util.MathHelper.floor_double(x),
                        net.minecraft.util.MathHelper.floor_double(y),
                        net.minecraft.util.MathHelper.floor_double(z) }));
        }

        player.playerNetServerHandler.setPlayerLocation(
                x, y, z, spot.getFloat("Yaw"), spot.getFloat("Pitch"));
        player.fallDistance = 0F;

        return EnumChatFormatting.GRAY + "Welcome home.";
    }
}
