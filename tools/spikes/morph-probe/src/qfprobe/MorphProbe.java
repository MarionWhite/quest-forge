package qfprobe;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.relauncher.Side;

import java.io.FileOutputStream;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiIngameMenu;
import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.GuiSelectWorld;
import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.DamageSource;
import net.minecraft.world.EnumDifficulty;
import net.minecraft.world.World;

/** Throwaway: drives kill -> acquire -> morph -> look around, logging each step. */
@Mod(modid = "qfmorphprobe", name = "QF Morph Probe", version = "1")
public class MorphProbe {
    static PrintStream file;
    static volatile String serverTask;

    int clientTicks, menuTicks, worldTicks = -1;
    boolean opened, started;

    static void log(String s) {
        String line = "[MorphProbe] " + s;
        System.out.println(line);
        System.out.flush();
        if (file != null) { file.println(System.currentTimeMillis() + " " + line); file.flush(); }
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent e) {
        try { file = new PrintStream(new FileOutputStream("morphprobe.log", true)); } catch (Exception ex) { }
        FMLCommonHandler.instance().bus().register(this);
        log("init, side=" + FMLCommonHandler.instance().getEffectiveSide());
    }

    @SubscribeEvent
    public void clientTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.func_71410_x();
        clientTicks++;
        if (mc.field_71439_g == null) {
            if (started) return;
            GuiScreen cur = mc.field_71462_r;
            if (!opened && clientTicks > 100 && cur != null && !(cur instanceof GuiSelectWorld)) {
                log("opening GuiSelectWorld over " + cur.getClass().getName());
                mc.func_147108_a(new GuiSelectWorld(cur));
                opened = true;
                menuTicks = clientTicks;
            } else if (opened && clientTicks - menuTicks > 40 && cur instanceof GuiSelectWorld) {
                log("loading world 0");
                ((GuiSelectWorld) cur).func_146615_e(0);
                started = true;
            }
            return;
        }
        worldTicks++;
        int w = worldTicks;
        if (w % 40 == 0) {
            log("heartbeat w=" + w + " screen=" + (mc.field_71462_r == null ? "none" : mc.field_71462_r.getClass().getSimpleName())
                + " view=" + mc.field_71474_y.field_74320_O + " clientMorphed=" + clientMorphed(mc));
        }
        switch (w) {
            case 100: serverTask = "setup"; break;
            case 200: serverTask = "kill:Pig"; break;
            case 320: serverTask = "morph:Pig"; break;
            case 520: log("STEP third person"); mc.field_71474_y.field_74320_O = 1; break;
            case 620: log("STEP first person"); mc.field_71474_y.field_74320_O = 0; break;
            case 680: log("STEP open inventory"); mc.func_147108_a(new GuiInventory(mc.field_71439_g)); break;
            case 780: log("STEP close inventory"); mc.func_147108_a(null); break;
            case 820: log("STEP open pause menu"); mc.func_147108_a(new GuiIngameMenu()); break;
            case 900: log("STEP close pause menu"); mc.func_147108_a(null); break;
            case 940: serverTask = "kill:Cow"; break;
            case 1060: serverTask = "morph:Cow"; break;
            case 1300: serverTask = "demorph"; break;
            case 1500: log("DONE - all steps survived"); mc.func_71400_g(); break;
            default:
        }
    }

    static boolean clientMorphed(Minecraft mc) {
        try {
            Object proxy = Class.forName("morph.common.Morph").getField("proxy").get(null);
            Object thc = proxy.getClass().getField("tickHandlerClient").get(proxy);
            java.util.Map m = (java.util.Map) thc.getClass().getField("playerMorphInfo").get(thc);
            return m.containsKey(mc.field_71439_g.func_70005_c_());
        } catch (Throwable t) { return false; }
    }

    @SubscribeEvent
    public void serverTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        String task = serverTask;
        if (task == null) return;
        serverTask = null;
        MinecraftServer server = MinecraftServer.func_71276_C();
        List players = server.func_71203_ab().field_72404_b;
        if (players.isEmpty()) { log("no players for " + task); return; }
        EntityPlayerMP player = (EntityPlayerMP) players.get(0);
        World world = player.field_70170_p;
        log("STEP server " + task + " player=" + player.func_70005_c_() + " hp=" + player.func_110143_aJ());
        try {
            if (task.equals("setup")) {
                server.func_147139_a(EnumDifficulty.PEACEFUL);
                world.func_72877_b(6000L);
                player.func_70606_j(player.func_110138_aP());
            } else if (task.startsWith("kill:")) {
                String name = task.substring(5);
                Entity ent = EntityList.func_75620_a(name, world);
                ent.func_70012_b(player.field_70165_t + 2.5, player.field_70163_u, player.field_70161_v, 0f, 0f);
                world.func_72838_d(ent);
                boolean hit = ((EntityLivingBase) ent).func_70097_a(DamageSource.func_76365_a(player), 1000f);
                log("killed " + name + " hit=" + hit + " dead=" + ((EntityLivingBase) ent).func_110143_aJ());
            } else if (task.startsWith("morph:")) {
                String want = task.substring(6);
                Object proxy = Class.forName("morph.common.Morph").getField("proxy").get(null);
                Object ths = proxy.getClass().getField("tickHandlerServer").get(proxy);
                Method gpm = ths.getClass().getMethod("getPlayerMorphs", World.class, EntityPlayer.class);
                List states = (List) gpm.invoke(ths, world, player);
                String id = null;
                for (Object st : states) {
                    Object inst = st.getClass().getField("entInstance").get(st);
                    String ident = (String) st.getClass().getField("identifier").get(st);
                    log("  has state " + ident + " -> " + (inst == null ? "null" : inst.getClass().getName()));
                    if (inst != null && inst.getClass().getSimpleName().contains(want)) id = ident;
                }
                if (id == null) { log("no acquired state for " + want); return; }
                Class pk = Class.forName("morph.common.packet.PacketGuiInput");
                Object packet = pk.getConstructor(int.class, String.class, boolean.class).newInstance(0, id, false);
                pk.getMethod("execute", Side.class, EntityPlayer.class).invoke(packet, Side.SERVER, player);
                log("sent morph into " + id);
            } else if (task.equals("demorph")) {
                server.func_71187_D().func_71556_a(server, "morph demorph " + player.func_70005_c_());
            }
        } catch (Throwable t) {
            log("server task " + task + " threw " + t);
            t.printStackTrace(System.out);
        }
    }
}
