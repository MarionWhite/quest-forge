package com.questforge.content;

import java.util.Random;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.client.renderer.texture.IIconRegister;
import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.item.Item;
import net.minecraft.item.ItemBlock;
import net.minecraft.item.ItemStack;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.IIcon;
import net.minecraft.world.World;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.config.Configuration;
import net.minecraftforge.event.world.BlockEvent;
import net.minecraftforge.oredict.OreDictionary;
import net.minecraftforge.oredict.ShapedOreRecipe;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import cpw.mods.fml.common.event.FMLServerStartingEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.registry.GameRegistry;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Every snippet in COOKBOOK.md, as real code, so the API signatures are checked by
 * the compiler rather than trusted. This lives in the test source set: it is
 * compiled by `./gradlew build` but never ends up in the shipped jar.
 *
 * Nothing here is called at runtime.
 */
public class CookbookExamples {

    static final String MODID = QuestForgeContent.MODID;

    // --- Items -------------------------------------------------------------

    static Item plainItem() {
        Item myItem = new Item()
                .setUnlocalizedName("my_item")
                .setTextureName(MODID + ":my_item")
                .setCreativeTab(ModCreativeTab.INSTANCE)
                .setMaxStackSize(16);
        GameRegistry.registerItem(myItem, "my_item");
        return myItem;
    }

    public static class ItemSpark extends Item {
        @Override
        public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
            if (!world.isRemote) {
                player.addChatMessage(new ChatComponentText("Spark!"));
                stack.stackSize--;
            }
            return stack;
        }
    }

    // --- Blocks ------------------------------------------------------------

    public static class BlockAltar extends Block {

        private IIcon topIcon;
        private IIcon sideIcon;

        public BlockAltar() {
            super(Material.rock);
            setHardness(3.0F);
            setStepSound(Block.soundTypeStone);
            setHarvestLevel("pickaxe", 1);
            setLightLevel(0.5F);
        }

        @Override
        public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player,
                int side, float hitX, float hitY, float hitZ) {
            if (!world.isRemote) {
                player.addChatMessage(new ChatComponentText("Altar at " + x + "," + y + "," + z));
            }
            return true;
        }

        @Override
        public Item getItemDropped(int meta, Random random, int fortune) {
            return ModItems.forgeShard;
        }

        @Override
        public int quantityDropped(Random random) {
            return 2 + random.nextInt(3);
        }

        @Override
        @SideOnly(Side.CLIENT)
        public IIcon getIcon(int side, int meta) {
            return side == 1 ? topIcon : sideIcon;
        }

        @Override
        @SideOnly(Side.CLIENT)
        public void registerBlockIcons(IIconRegister reg) {
            topIcon = reg.registerIcon(MODID + ":my_block_top");
            sideIcon = reg.registerIcon(MODID + ":my_block_side");
        }
    }

    static void registerBlock(Block block) {
        GameRegistry.registerBlock(block, ItemBlock.class, "my_block");
    }

    // --- Recipes -----------------------------------------------------------

    static void recipes(Item result) {
        GameRegistry.addRecipe(new ItemStack(result),
                "ABA",
                " C ",
                'A', Items.iron_ingot,
                'B', Blocks.stone,
                'C', ModItems.forgeShard);

        GameRegistry.addShapelessRecipe(new ItemStack(result, 2),
                Items.iron_ingot, Items.redstone);

        GameRegistry.addSmelting(ModBlocks.forgeBlock, new ItemStack(ModItems.forgeShard, 3), 0.7F);

        GameRegistry.addRecipe(new ShapedOreRecipe(new ItemStack(result),
                "XX", "XX", 'X', "ingotCopper"));

        OreDictionary.registerOre("shardForge", ModItems.forgeShard);
    }

    // --- Events ------------------------------------------------------------

    static void registerHandlers() {
        MinecraftForge.EVENT_BUS.register(new MyHandler());
        FMLCommonHandler.instance().bus().register(new MyHandler());
    }

    public static class MyHandler {
        @SubscribeEvent
        public void onBreak(BlockEvent.BreakEvent event) {
            if (event.block == ModBlocks.forgeBlock) {
                event.getPlayer().addChatMessage(new ChatComponentText("You broke it."));
            }
        }
    }

    // --- Config ------------------------------------------------------------

    static void config(FMLPreInitializationEvent event) {
        Configuration cfg = new Configuration(event.getSuggestedConfigurationFile());
        cfg.load();
        boolean enableThing = cfg.getBoolean("enableThing", Configuration.CATEGORY_GENERAL,
                true, "Turn the thing on");
        int amount = cfg.getInt("amount", Configuration.CATEGORY_GENERAL, 3, 1, 64, "How many");
        if (cfg.hasChanged()) cfg.save();

        // touch them so javac does not warn them unused
        if (enableThing && amount > 0) return;
    }

    // --- Tile entities -----------------------------------------------------

    public static class TileAltar extends TileEntity {}

    static void registerTile() {
        GameRegistry.registerTileEntity(TileAltar.class, MODID + "_altar");
    }

    // --- Commands ----------------------------------------------------------

    static void commands(FMLServerStartingEvent event) {
        event.registerServerCommand(new CommandBase() {
            @Override
            public String getCommandName() {
                return "qf";
            }

            @Override
            public String getCommandUsage(ICommandSender s) {
                return "/qf";
            }

            @Override
            public void processCommand(ICommandSender sender, String[] args) {
                sender.addChatMessage(new ChatComponentText("hello"));
            }
        });
    }

    // --- Creative tab ------------------------------------------------------

    static CreativeTabs tab() {
        return ModCreativeTab.INSTANCE;
    }
}
