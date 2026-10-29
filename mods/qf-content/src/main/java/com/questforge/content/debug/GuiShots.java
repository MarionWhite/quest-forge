package com.questforge.content.debug;

import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiEnchantment;
import net.minecraft.client.gui.GuiHopper;
import net.minecraft.client.gui.GuiRepair;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.inventory.GuiBeacon;
import net.minecraft.client.gui.inventory.GuiBrewingStand;
import net.minecraft.client.gui.inventory.GuiChest;
import net.minecraft.client.gui.inventory.GuiContainerCreative;
import net.minecraft.client.gui.inventory.GuiCrafting;
import net.minecraft.client.gui.inventory.GuiDispenser;
import net.minecraft.client.gui.inventory.GuiFurnace;
import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.boss.BossStatus;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.inventory.ContainerEnchantment;
import net.minecraft.inventory.ContainerWorkbench;
import net.minecraft.inventory.InventoryBasic;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagList;
import net.minecraft.tileentity.TileEntityBeacon;
import net.minecraft.tileentity.TileEntityBrewingStand;
import net.minecraft.tileentity.TileEntityDispenser;
import net.minecraft.tileentity.TileEntityFurnace;
import net.minecraft.tileentity.TileEntityHopper;
import net.minecraft.world.WorldSettings;
import cpw.mods.fml.relauncher.ReflectionHelper;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * FrameBench's GUI views (r011 texture review): a screen opened over a view's camera, filled with
 * sample items, so a resource pack's GUI, item and custom-item textures are judged in the real
 * game. Only views named gui_* reach this class; every other FrameBench scene is unchanged.
 */
@SideOnly(Side.CLIENT)
final class GuiShots {
    private GuiShots() { }

    private static final Map<GuiScreen, Boolean> OURS = new WeakHashMap<GuiScreen, Boolean>();
    private static String opened;     // the scene whose screen is open

    static boolean isOurs(GuiScreen s) {
        return OURS.containsKey(s);
    }

    private static ItemStack potion(int damage) {
        return new ItemStack(Items.potionitem, 1, damage);
    }

    private static ItemStack book(int ench, int lvl) {
        ItemStack b = new ItemStack(Items.enchanted_book);
        NBTTagList l = new NBTTagList();
        NBTTagCompound e = new NBTTagCompound();
        e.setShort("id", (short) ench);
        e.setShort("lvl", (short) lvl);
        l.appendTag(e);
        NBTTagCompound t = new NBTTagCompound();
        t.setTag("StoredEnchantments", l);
        b.setTagCompound(t);
        return b;
    }

    private static ItemStack worn(Item i, float used) {
        return new ItemStack(i, 1, (int) (i.getMaxDamage() * used));
    }

    /** Hotbar, then three rows: weapons and tools, potions and books, food and materials. */
    private static ItemStack[] sampleInventory() {
        return new ItemStack[] {
            new ItemStack(Items.diamond_sword), new ItemStack(Items.bow), worn(Items.iron_pickaxe, 0.8F),
            potion(8261), book(16, 5), new ItemStack(Items.golden_apple), new ItemStack(Items.compass),
            new ItemStack(Items.bread, 23), new ItemStack(Items.ender_pearl, 16),
            // row 1
            new ItemStack(Items.iron_sword), new ItemStack(Items.golden_sword), worn(Items.stone_sword, 0.7F),
            new ItemStack(Items.diamond_axe), new ItemStack(Items.iron_shovel), new ItemStack(Items.flint_and_steel),
            new ItemStack(Items.shears), new ItemStack(Items.fishing_rod), new ItemStack(Items.arrow, 64),
            // row 2
            potion(8193), potion(8194), potion(8195), potion(16388), potion(8230), potion(8270),
            book(0, 4), book(20, 2), book(51, 1),
            // row 3
            new ItemStack(Items.diamond, 12), new ItemStack(Items.emerald, 5), new ItemStack(Items.gold_ingot, 32),
            new ItemStack(Items.redstone, 64), new ItemStack(Items.blaze_rod, 3), new ItemStack(Items.cooked_beef, 9),
            new ItemStack(Items.cake), new ItemStack(Items.lava_bucket), new ItemStack(Items.record_cat),
        };
    }

    /** Server thread: inventory, armour and game mode for the scene. */
    static void setUpServer(EntityPlayerMP mp, String scene) {
        ItemStack[] inv = sampleInventory();
        for (int i = 0; i < mp.inventory.mainInventory.length; i++) {
            mp.inventory.mainInventory[i] = i < inv.length ? inv[i] : null;
        }
        mp.inventory.armorInventory[0] = null;                                    // boots: the empty-slot icon
        mp.inventory.armorInventory[1] = new ItemStack(Items.iron_leggings);
        mp.inventory.armorInventory[2] = new ItemStack(Items.diamond_chestplate);
        mp.inventory.armorInventory[3] = null;                                    // helmet: the empty-slot icon
        mp.inventory.currentItem = 0;
        mp.inventory.markDirty();
        boolean survival = scene.equals("gui_hud") || scene.equals("gui_inventory");
        mp.setGameType(survival ? WorldSettings.GameType.SURVIVAL : WorldSettings.GameType.CREATIVE);
        if (survival) {
            mp.experienceLevel = 0;
            mp.addExperienceLevel(27);
            mp.experience = 0.6F;
            mp.setHealth(15F);                                                    // seven and a half hearts
            // seven shanks, set (not subtracted): this runs more than once per scene, and -6 per call left the
            // r013 HUD shots at 7, 4 and 1 shanks
            mp.getFoodStats().addStats(14 - mp.getFoodStats().getFoodLevel(), 0F);
        }
    }

    /** Client thread, every tick of a gui_ scene: keep the boss bar up, or the screen open. */
    static void client(Minecraft mc, String scene) {
        if (scene.equals("gui_hud")) {
            BossStatus.bossName = "Ender Dragon";
            BossStatus.healthScale = 0.62F;
            BossStatus.statusBarTime = 100;
            BossStatus.hasColorModifier = false;
            return;
        }
        if (mc.thePlayer == null || mc.theWorld == null) return;
        if (scene.equals(opened) && mc.currentScreen != null && OURS.containsKey(mc.currentScreen)) return;
        GuiScreen g = make(mc, scene.substring(4));
        if (g == null) return;
        OURS.put(g, Boolean.TRUE);
        opened = scene;
        mc.displayGuiScreen(g);
    }

    private static GuiScreen make(Minecraft mc, String kind) {
        EntityPlayer p = mc.thePlayer;
        int x = (int) Math.floor(p.posX), y = (int) Math.floor(p.posY), z = (int) Math.floor(p.posZ);
        if (kind.equals("inventory")) return new GuiInventory(p);
        if (kind.startsWith("creative")) {
            CreativeTabs tab = CreativeTabs.tabCombat;
            String t = kind.length() > 9 ? kind.substring(9) : "combat";
            if (t.equals("tools")) tab = CreativeTabs.tabTools;
            else if (t.equals("brewing")) tab = CreativeTabs.tabBrewing;
            else if (t.equals("materials")) tab = CreativeTabs.tabMaterials;
            else if (t.equals("food")) tab = CreativeTabs.tabFood;
            else if (t.equals("redstone")) tab = CreativeTabs.tabRedstone;
            else if (t.equals("misc")) tab = CreativeTabs.tabMisc;
            ReflectionHelper.setPrivateValue(GuiContainerCreative.class, null, tab.getTabIndex(),
                    "selectedTabIndex", "field_147058_w");
            return new GuiContainerCreative(p);
        }
        if (kind.equals("furnace")) {
            TileEntityFurnace f = new TileEntityFurnace();
            f.setInventorySlotContents(0, new ItemStack(Blocks.iron_ore, 7));
            f.setInventorySlotContents(1, new ItemStack(Items.coal, 12));
            f.setInventorySlotContents(2, new ItemStack(Items.iron_ingot, 5));
            f.furnaceBurnTime = 900;
            f.currentItemBurnTime = 1600;
            f.furnaceCookTime = 120;
            return new GuiFurnace(p.inventory, f);
        }
        if (kind.equals("crafting")) {
            GuiCrafting g = new GuiCrafting(p.inventory, mc.theWorld, x, y, z);
            ContainerWorkbench c = (ContainerWorkbench) g.inventorySlots;
            c.craftMatrix.setInventorySlotContents(1, new ItemStack(Items.diamond));
            c.craftMatrix.setInventorySlotContents(4, new ItemStack(Items.diamond));
            c.craftMatrix.setInventorySlotContents(7, new ItemStack(Items.stick));
            return g;
        }
        if (kind.equals("chest")) {
            InventoryBasic box = new InventoryBasic("Chest", false, 27);
            ItemStack[] inv = sampleInventory();
            for (int i = 0; i < 27 && i < inv.length; i += 2) box.setInventorySlotContents(i, inv[inv.length - 1 - i]);
            return new GuiChest(p.inventory, box);
        }
        if (kind.equals("brewing")) {
            TileEntityBrewingStand b = new TileEntityBrewingStand();
            b.setInventorySlotContents(0, potion(8197));
            b.setInventorySlotContents(1, potion(8229));
            b.setInventorySlotContents(2, potion(16453));
            b.setInventorySlotContents(3, new ItemStack(Items.glowstone_dust, 6));
            ReflectionHelper.setPrivateValue(TileEntityBrewingStand.class, b, 220, "brewTime", "field_145946_k");
            return new GuiBrewingStand(p.inventory, b);
        }
        if (kind.equals("enchanting")) {
            // A sword in the table, or no option rows draw: an empty table draws the disabled row, which some
            // packs (Faithless) leave transparent. Levels are set by hand (the client never computes them).
            GuiEnchantment g = new GuiEnchantment(p.inventory, mc.theWorld, x, y, z, null);
            ContainerEnchantment c = (ContainerEnchantment) g.inventorySlots;
            c.tableInventory.setInventorySlotContents(0, new ItemStack(Items.diamond_sword));
            c.enchantLevels[0] = 4;
            c.enchantLevels[1] = 17;
            c.enchantLevels[2] = 30;
            return g;
        }
        if (kind.equals("anvil")) return new GuiRepair(p.inventory, mc.theWorld, x, y, z);
        if (kind.equals("beacon")) return new GuiBeacon(p.inventory, new TileEntityBeacon());
        if (kind.equals("hopper")) return new GuiHopper(p.inventory, new TileEntityHopper());
        if (kind.equals("dispenser")) return new GuiDispenser(p.inventory, new TileEntityDispenser());
        return null;
    }
}
