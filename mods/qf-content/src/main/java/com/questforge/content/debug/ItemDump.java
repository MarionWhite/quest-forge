package com.questforge.content.debug;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.imageio.ImageIO;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiMainMenu;
import net.minecraft.client.renderer.OpenGlHelper;
import net.minecraft.client.renderer.RenderHelper;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.entity.RenderItem;
import net.minecraft.client.shader.Framebuffer;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.ai.attributes.AttributeModifier;
import net.minecraft.item.Item;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemBlock;
import net.minecraft.item.ItemBow;
import net.minecraft.item.ItemFood;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemSword;
import net.minecraft.item.ItemTool;
import net.minecraft.item.crafting.CraftingManager;
import net.minecraft.item.crafting.FurnaceRecipes;
import net.minecraft.item.crafting.IRecipe;
import net.minecraft.item.crafting.ShapedRecipes;
import net.minecraft.item.crafting.ShapelessRecipes;
import net.minecraft.util.WeightedRandomChestContent;
import net.minecraftforge.common.ChestGenHooks;
import net.minecraftforge.oredict.OreDictionary;
import net.minecraftforge.oredict.ShapedOreRecipe;
import net.minecraftforge.oredict.ShapelessOreRecipe;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;

import com.google.gson.stream.JsonWriter;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Writes every item in the running pack -- name, mod, creative tab, ore names,
 * tooltip, a few stats, a 32-pixel icon -- plus the crafting and smelting
 * recipes, for the item browser on the site (tools/items/).
 *
 * -Dqf.itemdump=<dir> asks for it. It runs at the title screen, so no world or
 * save is needed, and -Dqf.itemdump.quit=1 closes the game once it is written.
 *
 * Why at the title screen and through RenderItem: the list a player can see is
 * what each item's getSubItems hands out, and the icon a player sees is what the
 * GUI path draws, custom IItemRenderers included. Reading textures out of the
 * jars instead would get every 3D block, model and tinted item wrong. Each icon
 * gets its own viewport and scissor, so a renderer that draws far outside its
 * slot (MCHeli's aircraft do) is clipped to its own cell instead of painting
 * over its neighbours.
 *
 * Every item is wrapped on its own: one mod's getSubItems or renderer throwing
 * costs that item, never the dump. Failures are counted in summary.json.
 */
@SideOnly(Side.CLIENT)
public class ItemDump {

    private static final String OUT = System.getProperty("qf.itemdump", "");
    private static final boolean QUIT = "1".equals(System.getProperty("qf.itemdump.quit", ""));

    /** Icon cell in pixels; a GUI slot is 16 units, so this is 2x. */
    private static final int CELL = 32;
    /** Cells per sheet side: 64 x 64 = 4096 icons in a 2048-pixel sheet. */
    private static final int SIDE = 64;
    private static final int PER_SHEET = SIDE * SIDE;
    /** Icons drawn per frame. Small enough that no single frame keeps the GPU long. */
    private static final int PER_FRAME = 192;
    /** Some items generate thousands of variants; past this they are noise. */
    private static final int MAX_SUBITEMS = 512;
    private static final int MAX_TOOLTIP = 10;

    private static final int WILDCARD = OreDictionary.WILDCARD_VALUE;

    private int ticks;
    private int stage;

    private final List<Entry> entries = new ArrayList<Entry>();
    private final RenderItem render = new RenderItem();
    private Framebuffer fb;
    private int next;
    private int sheet = -1;
    private int renderFailures;
    private int subItemFailures;
    private int metaFailures;
    private long started;

    public static boolean enabled() {
        return !OUT.isEmpty();
    }

    /** One stack the browser lists. */
    private static final class Entry {
        String key;
        ItemStack stack;
        String registry;
        String mod;
        int meta;
        String name = "";
        String unloc = "";
        String nbt;
        String tab;
        String kind;
        String rarity;
        int stackSize;
        int durability;
        double attack = Double.NaN;
        int armor = -1;
        String armorSlot;
        int food = -1;
        List<String> ores = new ArrayList<String>();
        List<String> tooltip = new ArrayList<String>();
        boolean blank;
        boolean renderFailed;
    }

    @SubscribeEvent
    public void onRender(TickEvent.RenderTickEvent event) {
        if (event.phase != TickEvent.Phase.END || stage > 2) return;
        Minecraft mc = Minecraft.getMinecraft();
        // The title screen, after every mod's postInit and the resource reload that
        // follows it. CustomMenu replaces GuiMainMenu, so any screen with no world
        // will do once things have settled.
        if (stage == 0) {
            if (mc.theWorld != null || mc.currentScreen == null || ++ticks < 200) return;
            stage = 1;
            started = System.currentTimeMillis();
            try {
                collect(mc);
                System.out.println("[ItemDump] " + entries.size() + " stacks; rendering icons");
            } catch (Throwable t) {
                System.out.println("[ItemDump] FAILED collecting: " + t);
                t.printStackTrace();
                stage = 3;
                return;
            }
        }
        if (stage == 1) {
            try {
                renderSome(mc);
            } catch (Throwable t) {
                System.out.println("[ItemDump] FAILED rendering: " + t);
                t.printStackTrace();
                stage = 2;
            }
            if (next >= entries.size()) {
                finishSheet();
                stage = 2;
            }
            return;
        }
        stage = 3;
        try {
            write(mc);
            System.out.println("[ItemDump] wrote " + OUT + " in "
                    + (System.currentTimeMillis() - started) / 1000 + " s");
        } catch (Throwable t) {
            System.out.println("[ItemDump] FAILED writing: " + t);
            t.printStackTrace();
        }
        if (fb != null) {
            fb.deleteFramebuffer();
            fb = null;
        }
        if (QUIT) {
            mc.shutdown();
        }
    }

    // -------------------------------------------------------------- collecting

    private void collect(Minecraft mc) {
        Set<String> seen = new LinkedHashSet<String>();
        List<String> names = new ArrayList<String>();
        for (Object k : Item.itemRegistry.getKeys()) names.add(String.valueOf(k));
        java.util.Collections.sort(names);
        for (String regName : names) {
            Item item = (Item) Item.itemRegistry.getObject(regName);
            if (item == null) continue;
            List<ItemStack> subs = new ArrayList<ItemStack>();
            try {
                List<?> raw = new ArrayList<Object>();
                item.getSubItems(item, item.getCreativeTab(), raw);
                for (Object o : raw) {
                    if (o instanceof ItemStack && ((ItemStack) o).getItem() != null) subs.add((ItemStack) o);
                    if (subs.size() >= MAX_SUBITEMS) break;
                }
            } catch (Throwable t) {
                subItemFailures++;
            }
            if (subs.isEmpty()) subs.add(new ItemStack(item, 1, 0));
            for (ItemStack s : subs) {
                Entry e = describe(regName, s);
                if (e != null && seen.add(e.key)) entries.add(e);
            }
        }
    }

    private Entry describe(String regName, ItemStack stack) {
        Entry e = new Entry();
        e.stack = stack.copy();
        e.stack.stackSize = 1;
        e.registry = regName;
        int colon = regName.indexOf(':');
        e.mod = colon < 0 ? "minecraft" : regName.substring(0, colon);
        e.meta = stack.getItemDamage();
        e.key = regName + "@" + e.meta;
        if (stack.stackTagCompound != null && !stack.stackTagCompound.hasNoTags()) {
            String nbt = stack.stackTagCompound.toString();
            e.nbt = nbt.length() > 400 ? nbt.substring(0, 400) + "..." : nbt;
            e.key += "#" + Integer.toHexString(nbt.hashCode());
        }
        Item item = stack.getItem();
        try {
            e.name = stack.getDisplayName();
        } catch (Throwable t) {
            metaFailures++;
        }
        try {
            e.unloc = stack.getUnlocalizedName();
        } catch (Throwable t) {
            // name stays empty
        }
        try {
            CreativeTabs tab = item.getCreativeTab();
            if (tab != null) e.tab = tab.getTranslatedTabLabel();
        } catch (Throwable t) {
            // no tab
        }
        try {
            for (int id : OreDictionary.getOreIDs(stack)) e.ores.add(OreDictionary.getOreName(id));
        } catch (Throwable t) {
            // no ore names
        }
        try {
            List<?> lines = stack.getTooltip(null, false);
            for (int i = 1; i < lines.size() && e.tooltip.size() < MAX_TOOLTIP; i++) {
                String line = String.valueOf(lines.get(i));
                if (!line.trim().isEmpty()) e.tooltip.add(line);
            }
        } catch (Throwable t) {
            // Many mods read the player in addInformation; there is none here.
        }
        try {
            e.rarity = stack.getRarity().rarityName;
            e.stackSize = stack.getMaxStackSize();
            e.durability = stack.isItemStackDamageable() ? stack.getMaxDamage() : 0;
        } catch (Throwable t) {
            metaFailures++;
        }
        try {
            Collection<?> mods = stack.getAttributeModifiers().get("generic.attackDamage");
            if (mods != null && !mods.isEmpty()) {
                double sum = 0;
                for (Object o : mods) {
                    AttributeModifier m = (AttributeModifier) o;
                    if (m.getOperation() == 0) sum += m.getAmount();
                }
                // As the tooltip shows it: the player's own 1 point plus the item's.
                e.attack = sum + 1;
            }
        } catch (Throwable t) {
            // no attack figure
        }
        if (item instanceof ItemArmor) {
            ItemArmor a = (ItemArmor) item;
            e.armor = a.damageReduceAmount;
            e.armorSlot = new String[] {"head", "chest", "legs", "feet"}[Math.max(0, Math.min(3, a.armorType))];
        }
        if (item instanceof ItemFood) {
            try {
                e.food = ((ItemFood) item).func_150905_g(stack);
            } catch (Throwable t) {
                // no food value
            }
        }
        e.kind = kind(item, e);
        return e;
    }

    private static String kind(Item item, Entry e) {
        if (item instanceof ItemBlock) return "block";
        if (item instanceof ItemArmor) return "armor";
        if (item instanceof ItemSword) return "weapon";
        if (item instanceof ItemBow) return "bow";
        if (item instanceof ItemTool) return "tool";
        if (item instanceof ItemFood) return "food";
        if (!Double.isNaN(e.attack) && e.attack > 1) return "weapon";
        return "item";
    }

    // --------------------------------------------------------------- rendering

    private void renderSome(Minecraft mc) {
        int end = Math.min(entries.size(), next + PER_FRAME);
        int px = CELL * SIDE;
        while (next < end) {
            int s = next / PER_SHEET;
            if (s != sheet) {
                finishSheet();
                sheet = s;
                if (fb == null) fb = new Framebuffer(px, px, true);
                fb.setFramebufferColor(0F, 0F, 0F, 0F);
                fb.framebufferClear();
            }
            fb.bindFramebuffer(false);
            drawCell(mc, entries.get(next), next % PER_SHEET);
            next++;
        }
        GL11.glDisable(GL11.GL_SCISSOR_TEST);
        mc.getFramebuffer().bindFramebuffer(true);
    }

    private void drawCell(Minecraft mc, Entry e, int cell) {
        int px = CELL * SIDE;
        int cx = (cell % SIDE) * CELL;
        int cy = px - (cell / SIDE + 1) * CELL;
        int modelDepth = GL11.glGetInteger(GL11.GL_MODELVIEW_STACK_DEPTH);
        int projDepth = GL11.glGetInteger(GL11.GL_PROJECTION_STACK_DEPTH);
        int attribDepth = GL11.glGetInteger(GL11.GL_ATTRIB_STACK_DEPTH);
        GL11.glPushAttrib(GL11.GL_ALL_ATTRIB_BITS);
        GL11.glViewport(cx, cy, CELL, CELL);
        GL11.glEnable(GL11.GL_SCISSOR_TEST);
        GL11.glScissor(cx, cy, CELL, CELL);
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glPushMatrix();
        GL11.glLoadIdentity();
        // The GUI's own projection, sized to one slot.
        GL11.glOrtho(0, 16, 16, 0, 1000, 3000);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glPushMatrix();
        GL11.glLoadIdentity();
        GL11.glTranslatef(0F, 0F, -2000F);
        try {
            mc.entityRenderer.disableLightmap(0);
            GL11.glColor4f(1F, 1F, 1F, 1F);
            GL11.glEnable(GL11.GL_DEPTH_TEST);
            GL11.glEnable(GL12.GL_RESCALE_NORMAL);
            RenderHelper.enableGUIStandardItemLighting();
            render.zLevel = 100F;
            render.renderItemAndEffectIntoGUI(mc.fontRenderer, mc.getTextureManager(), e.stack, 0, 0);
            RenderHelper.disableStandardItemLighting();
        } catch (Throwable t) {
            e.renderFailed = true;
            renderFailures++;
            resetTessellator();
        }
        // A renderer that threw, or that never popped what it pushed, must not
        // leave the next cell drawing under its transforms.
        while (GL11.glGetInteger(GL11.GL_MODELVIEW_STACK_DEPTH) > modelDepth + 1) GL11.glPopMatrix();
        GL11.glPopMatrix();
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        while (GL11.glGetInteger(GL11.GL_PROJECTION_STACK_DEPTH) > projDepth + 1) GL11.glPopMatrix();
        GL11.glPopMatrix();
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        while (GL11.glGetInteger(GL11.GL_ATTRIB_STACK_DEPTH) > attribDepth) GL11.glPopAttrib();
    }

    private static void resetTessellator() {
        Tessellator t = Tessellator.instance;
        for (String n : new String[] {"isDrawing", "field_78415_z"}) {
            try {
                Field f = Tessellator.class.getDeclaredField(n);
                f.setAccessible(true);
                if (f.getBoolean(t)) t.draw();
                return;
            } catch (NoSuchFieldException next) {
                // try the other name
            } catch (Throwable other) {
                return;
            }
        }
    }

    /** Reads the sheet in progress back and writes it, marking empty cells. */
    private void finishSheet() {
        if (sheet < 0 || fb == null) return;
        int px = CELL * SIDE;
        fb.bindFramebuffer(false);
        ByteBuffer buf = BufferUtils.createByteBuffer(px * px * 4);
        GL11.glReadPixels(0, 0, px, px, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        Minecraft.getMinecraft().getFramebuffer().bindFramebuffer(true);
        BufferedImage img = new BufferedImage(px, px, BufferedImage.TYPE_INT_ARGB);
        int[] alpha = new int[PER_SHEET];
        for (int y = 0; y < px; y++) {
            for (int x = 0; x < px; x++) {
                int i = ((px - 1 - y) * px + x) * 4;
                int r = buf.get(i) & 0xFF, g = buf.get(i + 1) & 0xFF;
                int b = buf.get(i + 2) & 0xFF, a = buf.get(i + 3) & 0xFF;
                img.setRGB(x, y, (a << 24) | (r << 16) | (g << 8) | b);
                if (a > 8) alpha[(y / CELL) * SIDE + x / CELL]++;
            }
        }
        int first = sheet * PER_SHEET;
        for (int c = 0; c < PER_SHEET && first + c < entries.size(); c++) {
            if (alpha[c] < 4) entries.get(first + c).blank = true;
        }
        try {
            File out = new File(OUT, "icons-" + sheet + ".png");
            out.getAbsoluteFile().getParentFile().mkdirs();
            ImageIO.write(img, "png", out);
            System.out.println("[ItemDump] sheet " + sheet + " written");
        } catch (Exception ex) {
            System.out.println("[ItemDump] sheet " + sheet + " FAILED: " + ex);
        }
        sheet = -1;
    }

    // ----------------------------------------------------------------- writing

    private void write(Minecraft mc) throws Exception {
        File dir = new File(OUT);
        dir.mkdirs();

        JsonWriter w = open(new File(dir, "items.json"));
        w.beginArray();
        for (int i = 0; i < entries.size(); i++) {
            Entry e = entries.get(i);
            w.beginObject();
            w.name("key").value(e.key);
            w.name("id").value(e.registry);
            w.name("meta").value(e.meta);
            w.name("mod").value(e.mod);
            w.name("name").value(e.name);
            w.name("unloc").value(e.unloc);
            if (e.nbt != null) w.name("nbt").value(e.nbt);
            if (e.tab != null) w.name("tab").value(e.tab);
            w.name("kind").value(e.kind);
            if (e.rarity != null) w.name("rarity").value(e.rarity);
            w.name("stack").value(e.stackSize);
            if (e.durability > 0) w.name("durability").value(e.durability);
            if (!Double.isNaN(e.attack)) w.name("attack").value(e.attack);
            if (e.armor >= 0) w.name("armor").value(e.armor).name("slot").value(e.armorSlot);
            if (e.food >= 0) w.name("food").value(e.food);
            strings(w, "ores", e.ores);
            strings(w, "tooltip", e.tooltip);
            w.name("icon").value(i);
            if (e.blank) w.name("blank").value(true);
            if (e.renderFailed) w.name("renderFailed").value(true);
            w.endObject();
        }
        w.endArray();
        w.close();

        writeRecipes(new File(dir, "recipes.json"));
        writeLoot(new File(dir, "loot.json"));

        w = open(new File(dir, "mods.json"));
        w.beginObject();
        for (Map.Entry<String, ModContainer> m : Loader.instance().getIndexedModList().entrySet()) {
            ModContainer c = m.getValue();
            w.name(m.getKey()).beginObject();
            w.name("name").value(c.getName());
            w.name("version").value(c.getVersion());
            File src = c.getSource();
            w.name("file").value(src == null ? "" : src.getName());
            w.endObject();
        }
        w.endObject();
        w.close();

        w = open(new File(dir, "summary.json"));
        w.beginObject();
        w.name("stacks").value(entries.size());
        w.name("sheets").value((entries.size() + PER_SHEET - 1) / PER_SHEET);
        w.name("cell").value(CELL);
        w.name("side").value(SIDE);
        w.name("renderFailures").value(renderFailures);
        w.name("subItemFailures").value(subItemFailures);
        w.name("metaFailures").value(metaFailures);
        int blank = 0;
        for (Entry e : entries) if (e.blank) blank++;
        w.name("blankIcons").value(blank);
        w.name("seconds").value((System.currentTimeMillis() - started) / 1000);
        w.endObject();
        w.close();
    }

    private void writeRecipes(File file) throws Exception {
        // ShapedOreRecipe keeps the very list OreDictionary.getOres returns, so the
        // ore name of an ingredient is found by identity, not by guessing.
        Map<Object, String> oreLists = new IdentityHashMap<Object, String>();
        for (String ore : OreDictionary.getOreNames()) oreLists.put(OreDictionary.getOres(ore), ore);

        JsonWriter w = open(file);
        w.beginObject();
        w.name("crafting").beginArray();
        int other = 0;
        Map<String, Integer> otherTypes = new HashMap<String, Integer>();
        for (Object o : CraftingManager.getInstance().getRecipeList()) {
            IRecipe r = (IRecipe) o;
            ItemStack out;
            try {
                out = r.getRecipeOutput();
            } catch (Throwable t) {
                continue;
            }
            if (out == null || out.getItem() == null) {
                String type = r.getClass().getName();
                Integer n = otherTypes.get(type);
                otherTypes.put(type, n == null ? 1 : n + 1);
                other++;
                continue;
            }
            try {
                if (r instanceof ShapedRecipes) {
                    ShapedRecipes s = (ShapedRecipes) r;
                    begin(w, "shaped", out);
                    w.name("w").value(s.recipeWidth).name("h").value(s.recipeHeight);
                    w.name("in").beginArray();
                    for (ItemStack in : s.recipeItems) ingredient(w, in, oreLists);
                    w.endArray().endObject();
                } else if (r instanceof ShapedOreRecipe) {
                    ShapedOreRecipe s = (ShapedOreRecipe) r;
                    begin(w, "shaped", out);
                    w.name("w").value(intField(ShapedOreRecipe.class, s, "width", 3));
                    w.name("h").value(intField(ShapedOreRecipe.class, s, "height", 3));
                    w.name("in").beginArray();
                    for (Object in : s.getInput()) ingredient(w, in, oreLists);
                    w.endArray().endObject();
                } else if (r instanceof ShapelessRecipes) {
                    begin(w, "shapeless", out);
                    w.name("in").beginArray();
                    for (Object in : ((ShapelessRecipes) r).recipeItems) ingredient(w, in, oreLists);
                    w.endArray().endObject();
                } else if (r instanceof ShapelessOreRecipe) {
                    begin(w, "shapeless", out);
                    w.name("in").beginArray();
                    for (Object in : ((ShapelessOreRecipe) r).getInput()) ingredient(w, in, oreLists);
                    w.endArray().endObject();
                } else {
                    // A mod's own recipe class: the output is real, the grid is not readable.
                    begin(w, "special", out);
                    w.name("class").value(r.getClass().getName());
                    w.endObject();
                }
            } catch (Throwable t) {
                other++;
            }
        }
        w.endArray();

        w.name("smelting").beginArray();
        for (Object o : FurnaceRecipes.smelting().getSmeltingList().entrySet()) {
            Map.Entry<?, ?> m = (Map.Entry<?, ?>) o;
            ItemStack in = (ItemStack) m.getKey(), out = (ItemStack) m.getValue();
            if (in == null || out == null || in.getItem() == null || out.getItem() == null) continue;
            begin(w, "smelting", out);
            w.name("in").beginArray();
            ingredient(w, in, oreLists);
            w.endArray().endObject();
        }
        w.endArray();

        w.name("unreadable").value(other);
        w.name("unreadableTypes").beginObject();
        for (Map.Entry<String, Integer> m : otherTypes.entrySet()) w.name(m.getKey()).value(m.getValue());
        w.endObject();

        w.name("ores").beginObject();
        Map<String, List<String>> ores = new LinkedHashMap<String, List<String>>();
        for (String ore : OreDictionary.getOreNames()) {
            List<String> keys = new ArrayList<String>();
            for (ItemStack s : OreDictionary.getOres(ore)) {
                String k = ref(s);
                if (k != null) keys.add(k);
            }
            if (!keys.isEmpty()) ores.put(ore, keys);
        }
        for (Map.Entry<String, List<String>> m : ores.entrySet()) strings(w, m.getKey(), m.getValue());
        w.endObject();
        w.endObject();
        w.close();
    }

    /**
     * Every ChestGenHooks category -- vanilla's dungeon, mineshaft, stronghold, temple and
     * blacksmith chests, plus any a mod registers -- with each entry's weight and stack
     * range, so the browser can say "found in dungeon chests" from the table itself.
     */
    @SuppressWarnings("unchecked")
    private static void writeLoot(File file) throws Exception {
        Field mapField = ChestGenHooks.class.getDeclaredField("chestInfo");
        mapField.setAccessible(true);
        Map<String, ChestGenHooks> map = (Map<String, ChestGenHooks>) mapField.get(null);
        Field contentsField = ChestGenHooks.class.getDeclaredField("contents");
        contentsField.setAccessible(true);
        JsonWriter w = open(file);
        w.beginObject();
        for (Map.Entry<String, ChestGenHooks> m : map.entrySet()) {
            ChestGenHooks info = m.getValue();
            List<WeightedRandomChestContent> contents =
                    (List<WeightedRandomChestContent>) contentsField.get(info);
            w.name(m.getKey()).beginObject();
            w.name("rollsMin").value(info.getMin());
            w.name("rollsMax").value(info.getMax());
            w.name("items").beginArray();
            for (WeightedRandomChestContent c : contents) {
                String k = ref(c.theItemId);
                if (k == null) continue;
                w.beginArray().value(k).value(c.itemWeight)
                        .value(c.theMinimumChanceToGenerateItem)
                        .value(c.theMaximumChanceToGenerateItem).endArray();
            }
            w.endArray().endObject();
        }
        w.endObject();
        w.close();
    }

    private static void begin(JsonWriter w, String type, ItemStack out) throws Exception {
        w.beginObject();
        w.name("type").value(type);
        w.name("out").value(ref(out));
        if (out.stackSize > 1) w.name("count").value(out.stackSize);
    }

    /** An ingredient: null for an empty slot, "id@meta" (meta "*" for any), "ore:name", or alternatives. */
    private static void ingredient(JsonWriter w, Object in, Map<Object, String> oreLists) throws Exception {
        if (in == null) {
            w.nullValue();
        } else if (in instanceof ItemStack) {
            String k = ref((ItemStack) in);
            if (k == null) w.nullValue();
            else w.value(k);
        } else if (in instanceof List) {
            String ore = oreLists.get(in);
            if (ore != null) {
                w.value("ore:" + ore);
            } else {
                w.beginArray();
                int n = 0;
                for (Object o : (List<?>) in) {
                    if (!(o instanceof ItemStack)) continue;
                    String k = ref((ItemStack) o);
                    if (k != null && n++ < 16) w.value(k);
                }
                w.endArray();
            }
        } else {
            w.nullValue();
        }
    }

    private static String ref(ItemStack s) {
        if (s == null || s.getItem() == null) return null;
        Object name = Item.itemRegistry.getNameForObject(s.getItem());
        if (name == null) return null;
        int meta = s.getItemDamage();
        return name + "@" + (meta == WILDCARD ? "*" : String.valueOf(meta));
    }

    private static int intField(Class<?> c, Object o, String name, int fallback) {
        try {
            Field f = c.getDeclaredField(name);
            f.setAccessible(true);
            return f.getInt(o);
        } catch (Throwable t) {
            return fallback;
        }
    }

    private static void strings(JsonWriter w, String name, List<String> values) throws Exception {
        if (values.isEmpty()) return;
        w.name(name).beginArray();
        for (String v : values) w.value(v);
        w.endArray();
    }

    private static JsonWriter open(File f) throws Exception {
        JsonWriter w = new JsonWriter(new OutputStreamWriter(new FileOutputStream(f), "UTF-8"));
        w.setIndent("");
        return w;
    }
}
