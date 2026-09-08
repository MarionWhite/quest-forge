package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;
import net.minecraft.client.renderer.texture.IIconRegister;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagList;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.IIcon;

import java.util.ArrayList;
import java.util.List;

/**
 * A record: a playlist you can hold, hand to someone, and hang on a wall.
 *
 * The songs live in the item's own NBT rather than in a table keyed by an id,
 * which is what makes it an object rather than a receipt. It survives being
 * dropped, traded and carried between worlds, and there is nothing on a server to
 * keep in step with it.
 *
 * The four pressings -- black, silver, gold, platinum -- are metadata on one item
 * and differ only in how they look. A record's worth is what somebody put on it,
 * so making the good-looking ones hold more would have been a tax on taste.
 */
public class ItemVinyl extends Item {

    public static final int BLACK = 0, SILVER = 1, GOLD = 2, PLATINUM = 3;

    private static final String[] TIERS = { "black", "silver", "gold", "platinum" };

    private static final String ROOT = "Record";
    private static final String NAME = "Name";
    private static final String TRACKS = "Tracks";

    @SideOnly(Side.CLIENT)
    private IIcon[] icons;

    public ItemVinyl() {
        setUnlocalizedName("record");
        setCreativeTab(com.questforge.content.ModCreativeTab.INSTANCE);
        setHasSubtypes(true);
        setMaxDamage(0);
        // Each record is its own thing; stacking would merge two track lists
        // behind one icon.
        setMaxStackSize(1);
    }

    /**
     * Never more than one. Enforced here as well as through the max stack size,
     * because a record's whole identity is its NBT: two of them in a slot would be
     * one track list wearing another's icon, and the second would be unreachable.
     */
    @Override
    public int getItemStackLimit(ItemStack stack) { return 1; }

    public static int tier(ItemStack stack) {
        if (stack == null) return BLACK;
        int meta = stack.getItemDamage();
        return meta < 0 || meta >= TIERS.length ? BLACK : meta;
    }

    // ------------------------------------------------------------------
    // Contents
    // ------------------------------------------------------------------

    public static boolean isWritten(ItemStack stack) {
        return stack != null && stack.hasTagCompound()
                && stack.getTagCompound().hasKey(ROOT);
    }

    public static String name(ItemStack stack) {
        if (!isWritten(stack)) return "";
        return stack.getTagCompound().getCompoundTag(ROOT).getString(NAME);
    }

    public static int trackCount(ItemStack stack) {
        if (!isWritten(stack)) return 0;
        return stack.getTagCompound().getCompoundTag(ROOT).getTagList(TRACKS, 10).tagCount();
    }

    /** The songs on the record. Empty for a blank one, never null. */
    public static List<Track> tracks(ItemStack stack) {
        List<Track> out = new ArrayList<Track>();
        if (!isWritten(stack)) return out;

        NBTTagList list = stack.getTagCompound().getCompoundTag(ROOT)
                .getTagList(TRACKS, 10);   // 10 = compound

        for (int i = 0; i < list.tagCount() && out.size() < PublicPlaylists.MAX_TRACKS; i++) {
            NBTTagCompound t = list.getCompoundTagAt(i);

            // Read through the same host rules the writer applied. A record can
            // have come from another player, so the writer is not necessarily
            // this code.
            String key = com.questforge.content.net.PacketBindTrack.sanitize(t.getString("k"));
            if (key.isEmpty()) continue;

            String art = t.getString("r");
            out.add(Track.remote(key, t.getString("s"), t.getString("t"),
                                 t.getString("a"), t.getString("b"),
                                 Math.max(0, t.getInteger("d")),
                                 art.isEmpty() ? null : art));
        }
        return out;
    }

    /** Presses a record. Server side: this is what makes the contents official. */
    public static void write(ItemStack stack, String label, List<Track> tracks) {
        if (stack == null) return;
        if (!stack.hasTagCompound()) stack.setTagCompound(new NBTTagCompound());

        NBTTagList list = new NBTTagList();
        for (int i = 0; i < tracks.size() && i < PublicPlaylists.MAX_TRACKS; i++) {
            Track track = tracks.get(i);
            String key = com.questforge.content.net.PacketBindTrack.sanitize(track.key());
            if (key.isEmpty()) continue;

            NBTTagCompound t = new NBTTagCompound();
            t.setString("k", key);
            t.setString("s", clip(track.source, 32));
            t.setString("t", clip(track.title, 80));
            t.setString("a", clip(track.artist, 60));
            t.setString("b", clip(track.album, 60));
            t.setInteger("d", (int) Math.min(Math.max(track.durationMs, 0L), Integer.MAX_VALUE));
            if (track.artUrl != null) t.setString("r", clip(track.artUrl, 200));
            list.appendTag(t);
        }

        NBTTagCompound root = new NBTTagCompound();
        root.setString(NAME, clip(label, PublicPlaylists.MAX_NAME));
        root.setTag(TRACKS, list);
        stack.getTagCompound().setTag(ROOT, root);
    }

    /** Wipes a record back to blank, ready to be pressed again. */
    public static void erase(ItemStack stack) {
        if (stack == null || !stack.hasTagCompound()) return;
        stack.getTagCompound().removeTag(ROOT);
        // An empty compound left behind makes two otherwise identical blanks
        // refuse to stack and shows up in /give output as noise.
        if (stack.getTagCompound().hasNoTags()) stack.setTagCompound(null);
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        s = s.replace('§', ' ').trim();
        return s.length() <= max ? s : s.substring(0, max);
    }

    // ------------------------------------------------------------------
    // Appearance
    // ------------------------------------------------------------------

    @Override
    public String getUnlocalizedName(ItemStack stack) {
        return "item.record_" + TIERS[tier(stack)];
    }

    @Override
    public String getItemStackDisplayName(ItemStack stack) {
        String label = name(stack);
        String base = super.getItemStackDisplayName(stack);
        return label.isEmpty() ? base : base + ": " + label;
    }

    /** A pressed record catches the light, so a full one stands out in a chest. */
    @Override
    public boolean hasEffect(ItemStack stack, int pass) { return isWritten(stack); }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    @Override
    public void addInformation(ItemStack stack, EntityPlayer player,
                               List tooltip, boolean advanced) {
        if (!isWritten(stack)) {
            tooltip.add(EnumChatFormatting.GRAY + "Blank");
            tooltip.add(EnumChatFormatting.DARK_GRAY
                    + "Use on a jukebox to choose songs and cut it");
            return;
        }

        int n = trackCount(stack);
        tooltip.add(EnumChatFormatting.GRAY + "" + n + (n == 1 ? " song" : " songs"));
        // The track list itself lives behind the inventory menu rather than in a
        // tooltip that would cover half the screen on a full record.
        tooltip.add(EnumChatFormatting.DARK_GRAY + "Point at it in your inventory and");
        tooltip.add(EnumChatFormatting.DARK_GRAY + "press " + RecordKeys.keyName()
                + " to list its songs or erase it");
        tooltip.add(EnumChatFormatting.DARK_GRAY
                + "Use on a jukebox to add its songs to your library");
    }

    @SideOnly(Side.CLIENT)
    @Override
    public void registerIcons(IIconRegister register) {
        icons = new IIcon[TIERS.length];
        for (int i = 0; i < TIERS.length; i++) {
            icons[i] = register.registerIcon(
                    com.questforge.content.QuestForgeContent.MODID + ":record_" + TIERS[i]);
        }
    }

    @SideOnly(Side.CLIENT)
    @Override
    public IIcon getIconFromDamage(int meta) {
        return icons[meta < 0 || meta >= icons.length ? 0 : meta];
    }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    @Override
    public void getSubItems(Item item, CreativeTabs tab, List out) {
        for (int i = 0; i < TIERS.length; i++) out.add(new ItemStack(item, 1, i));
    }
}
