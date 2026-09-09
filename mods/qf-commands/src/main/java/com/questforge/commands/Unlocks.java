package com.questforge.commands;

import java.util.HashSet;
import java.util.Set;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagList;
import net.minecraft.nbt.NBTTagString;

/**
 * What a player has earned, stored on the player.
 *
 * Written into the persistent half of the entity's NBT, so it survives death,
 * dimension changes and logout without this mod owning a save file or a world
 * data object. That matters for a pack: a mod that keeps player progress in its
 * own file loses it the moment someone copies a world without knowing to copy
 * the file too.
 *
 * The set is stored as strings rather than as a bitmask over the registry
 * order, so inserting a command in the middle of {@link Unlockables} does not
 * shift what everyone already owns.
 */
public final class Unlocks {

    private static final String ROOT = "QFCommands";
    private static final String LIST = "Unlocked";

    private Unlocks() {
    }

    private static NBTTagCompound root(EntityPlayer player, boolean create) {
        NBTTagCompound persisted = player.getEntityData()
                .getCompoundTag(EntityPlayer.PERSISTED_NBT_TAG);

        if (!persisted.hasKey(ROOT) && !create) {
            return null;
        }

        NBTTagCompound mine = persisted.getCompoundTag(ROOT);

        if (create) {
            persisted.setTag(ROOT, mine);
            player.getEntityData().setTag(EntityPlayer.PERSISTED_NBT_TAG, persisted);
        }

        return mine;
    }

    /** Everything this player has unlocked. Never null. */
    public static Set<String> all(EntityPlayer player) {
        Set<String> out = new HashSet<String>();
        NBTTagCompound mine = root(player, false);

        if (mine == null) {
            return out;
        }

        NBTTagList list = mine.getTagList(LIST, 8);   // 8 == string

        for (int i = 0; i < list.tagCount(); i++) {
            out.add(list.getStringTagAt(i));
        }

        return out;
    }

    public static boolean has(EntityPlayer player, String id) {
        return all(player).contains(id);
    }

    /**
     * Grants an unlock.
     *
     * @return false if the player already had it, so a ticket can refuse to be
     *         consumed rather than silently vanishing for nothing
     */
    public static boolean grant(EntityPlayer player, String id) {
        Set<String> current = all(player);

        if (!current.add(id)) {
            return false;
        }

        NBTTagList list = new NBTTagList();

        for (String s : current) {
            list.appendTag(new NBTTagString(s));
        }

        root(player, true).setTag(LIST, list);
        return true;
    }

    /** Used by the /unlocks listing and by admin revocation. */
    public static boolean revoke(EntityPlayer player, String id) {
        Set<String> current = all(player);

        if (!current.remove(id)) {
            return false;
        }

        NBTTagList list = new NBTTagList();

        for (String s : current) {
            list.appendTag(new NBTTagString(s));
        }

        root(player, true).setTag(LIST, list);
        return true;
    }
}
