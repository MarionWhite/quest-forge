package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;
import net.minecraft.client.renderer.texture.IIconRegister;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.World;

import java.util.List;
import java.util.UUID;

/**
 * The JBL: a jukebox you carry.
 *
 * Everything the wall jukebox can do, sounding from your own shoulder instead of
 * from a block, and moving with you. It plays only while it is the thing in your
 * hand, which is what keeps a pocketful of them from turning into a pocketful of
 * simultaneous music -- and what makes putting one away a deliberate act rather
 * than a menu.
 *
 * Each speaker carries an id, stamped the first time it is used. That id is what
 * makes a hotbar of them behave as separate speakers rather than as one: it is the
 * name their queues are filed under. Without it two JBLs would be indistinguishable
 * -- identical items with identical NBT -- and would share a single queue between
 * them.
 *
 * The id is written by the server, because that is the only side whose change to an
 * item's NBT survives. The client is told which speaker to open by the packet that
 * opens the screen, so it never has to guess or wait for the stack to sync.
 */
public class ItemSpeaker extends Item {

    private static final String ROOT = "Speaker";
    private static final String ID = "Id";

    public ItemSpeaker() {
        setUnlocalizedName("jbl");
        setCreativeTab(com.questforge.content.ModCreativeTab.INSTANCE);
        setMaxDamage(0);
        // Each one is its own speaker with its own queue; a stack of them could
        // only ever be one speaker wearing the count of several.
        setMaxStackSize(1);
    }

    @Override
    public int getItemStackLimit(ItemStack stack) { return 1; }

    // ------------------------------------------------------------------
    // Identity
    // ------------------------------------------------------------------

    /** The speaker's id, or empty if it has never been switched on. */
    public static String id(ItemStack stack) {
        if (stack == null || !stack.hasTagCompound()) return "";
        return stack.getTagCompound().getCompoundTag(ROOT).getString(ID);
    }

    /** Stamps an id if there is not one yet, and returns it. Server side. */
    public static String ensureId(ItemStack stack) {
        String existing = id(stack);
        if (!existing.isEmpty()) return existing;

        if (!stack.hasTagCompound()) stack.setTagCompound(new NBTTagCompound());
        NBTTagCompound root = stack.getTagCompound().getCompoundTag(ROOT);
        String fresh = UUID.randomUUID().toString();
        root.setString(ID, fresh);
        stack.getTagCompound().setTag(ROOT, root);
        return fresh;
    }

    // ------------------------------------------------------------------
    // Using
    // ------------------------------------------------------------------

    @Override
    public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
        // The server does the whole job: it stamps the id, then tells that one
        // client to open the screen for it. Opening from the client's own copy of
        // this call would race the id back down the wire, and the first click on a
        // new speaker would open nothing.
        if (world.isRemote) return stack;

        String id = ensureId(stack);
        com.questforge.content.net.QFNetwork.toPlayer(
                new com.questforge.content.net.PacketOpenSpeaker(id),
                (net.minecraft.entity.player.EntityPlayerMP) player);
        return stack;
    }

    // ------------------------------------------------------------------
    // Appearance
    // ------------------------------------------------------------------

    @SuppressWarnings({ "unchecked", "rawtypes" })
    @Override
    public void addInformation(ItemStack stack, EntityPlayer player,
                               List tooltip, boolean advanced) {
        tooltip.add(EnumChatFormatting.GRAY + "A jukebox you carry");
        tooltip.add(EnumChatFormatting.DARK_GRAY + "Right-click to choose music");
        tooltip.add(EnumChatFormatting.DARK_GRAY + "Plays while you are holding it");
        // Said plainly, because two identical-looking speakers behaving as one
        // would be the obvious guess otherwise.
        tooltip.add(EnumChatFormatting.DARK_GRAY + "Each speaker keeps its own queue");
    }

    @SideOnly(Side.CLIENT)
    @Override
    public void registerIcons(IIconRegister register) {
        itemIcon = register.registerIcon(
                com.questforge.content.QuestForgeContent.MODID + ":jbl");
    }
}
