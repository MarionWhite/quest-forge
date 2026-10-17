package qfbiomedump;

import java.io.File;
import java.io.PrintWriter;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.Mod.EventHandler;
import cpw.mods.fml.common.event.FMLServerStartedEvent;

/**
 * Trial-only probe: writes the live biome registry to biome-ids.tsv in the game dir once
 * the server has started (every mod has registered its biomes by then).
 *
 * Compiled against nothing but FML, so it needs no MCP workspace: Minecraft classes are
 * reached by reflection with their SRG member names, which is what a production
 * (reobfuscated) runtime exposes after FML's class-name remapping.
 */
@Mod(modid = "qfbiomedump", name = "QF biome dump (trial probe)", version = "1", acceptableRemoteVersions = "*")
public class BiomeDump {

    @EventHandler
    public void started(FMLServerStartedEvent e) {
        try {
            Class<?> bgb = Class.forName("net.minecraft.world.biome.BiomeGenBase");
            Method arr = find(bgb, "func_150565_n", "getBiomeGenArray");
            Field name = field(bgb, "field_76791_y", "biomeName");
            Field id = field(bgb, "field_76756_M", "biomeID");
            Object[] biomes = (Object[]) arr.invoke(null);
            File out = new File("biome-ids.tsv");
            PrintWriter w = new PrintWriter(out, "UTF-8");
            w.println("id\tname\tclass");
            int n = 0;
            for (int i = 0; i < biomes.length; i++) {
                Object b = biomes[i];
                if (b == null) continue;
                int bid = id.getInt(b);
                w.println(i + "\t" + name.get(b) + "\t" + b.getClass().getName()
                        + (bid != i ? "\tSLOT_MISMATCH biomeID=" + bid : ""));
                n++;
            }
            w.close();
            System.out.println("[qfbiomedump] wrote " + n + " biomes to " + out.getAbsolutePath());
        } catch (Throwable t) {
            System.out.println("[qfbiomedump] failed: " + t);
            t.printStackTrace();
        }
    }

    private static Method find(Class<?> c, String... names) throws NoSuchMethodException {
        for (String n : names) {
            try { Method m = c.getDeclaredMethod(n); m.setAccessible(true); return m; }
            catch (NoSuchMethodException ignored) {}
        }
        throw new NoSuchMethodException(names[0]);
    }

    private static Field field(Class<?> c, String... names) throws NoSuchFieldException {
        for (String n : names) {
            try { Field f = c.getDeclaredField(n); f.setAccessible(true); return f; }
            catch (NoSuchFieldException ignored) {}
        }
        throw new NoSuchFieldException(names[0]);
    }
}
