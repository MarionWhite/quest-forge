import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.util.CheckClassAdapter;

import net.minecraft.launchwrapper.IClassTransformer;

import com.questforge.content.core.ContainerTransformer;
import com.questforge.content.core.OreGenTransformer;
import com.questforge.content.core.ReachTransformer;

/**
 * Runs every ASM transformer against the real Minecraft classes, offline.
 *
 * This exists because the alternative is launching the game and walking to the
 * situation that loads the patched class -- and two of the three patched classes
 * (PlayerControllerMP, NetHandlerPlayServer) only load once you are in a world, so
 * a bad patch would not surface until minutes into a manual test.
 *
 * Each class is checked three ways:
 *
 *   1. the transformer actually matched something -- a transformer that quietly
 *      fails to find its target returns the input unchanged, which looks identical
 *      to success from the outside
 *   2. ASM's own analysis passes
 *   3. the real JVM verifier accepts it, by defining the transformed bytes in a
 *      throwaway classloader and linking them. This is the check that would have
 *      caught the missing stackmap frame in the Container patch.
 *
 * Run with: ./gradlew checkTransformers
 */
public class TransformerCheck {

    private static int failures;

    public static void main(String[] args) throws Exception {
        check(new ContainerTransformer(), "net.minecraft.inventory.Container");
        check(new ReachTransformer(), "net.minecraft.client.multiplayer.PlayerControllerMP");
        check(new ReachTransformer(), "net.minecraft.network.NetHandlerPlayServer");
        check(new OreGenTransformer(), "net.minecraft.world.gen.feature.WorldGenMinable");

        if (failures > 0) {
            System.err.println("\n" + failures + " transformer check(s) FAILED.");
            System.exit(1);
        }
        System.out.println("\nAll transformer checks passed.");
    }

    private static void check(IClassTransformer transformer, String className) throws Exception {
        System.out.println("--- " + className);

        byte[] original = read(className);
        if (original == null) {
            fail("could not read the class off the classpath");
            return;
        }

        byte[] patched = transformer.transform(className, className, original);

        if (patched == null) {
            fail("transformer returned null");
            return;
        }
        if (patched == original || java.util.Arrays.equals(patched, original)) {
            fail("transformer did not change anything -- it found no target");
            return;
        }

        if (!analyses(patched, className)) return;
        if (!links(patched, className)) return;

        System.out.println("    ok (" + original.length + " -> " + patched.length + " bytes)");
    }

    /** ASM's own consistency analysis. */
    private static boolean analyses(byte[] patched, String className) {
        StringWriter out = new StringWriter();
        try {
            CheckClassAdapter.verify(new ClassReader(patched), false, new PrintWriter(out));
        } catch (Throwable t) {
            fail("ASM analysis threw: " + t);
            return false;
        }

        String report = out.toString();
        if (report.contains("Error") || report.contains("Exception")) {
            fail("ASM analysis rejected the result:\n" + report);
            return false;
        }
        return true;
    }

    /**
     * The real thing: define the patched bytes and force linking, which is when
     * the JVM verifier runs. Everything else resolves through the parent loader.
     */
    private static boolean links(byte[] patched, String className) {
        try {
            new ClassLoader(TransformerCheck.class.getClassLoader()) {
                Class<?> define(String name, byte[] bytes) {
                    Class<?> c = defineClass(name, bytes, 0, bytes.length);
                    resolveClass(c);
                    return c;
                }
            }.define(className, patched);
            return true;
        } catch (VerifyError e) {
            fail("JVM verifier REJECTED the patched class: " + e.getMessage());
            return false;
        } catch (Throwable t) {
            // A NoClassDefFoundError here is about the environment, not the patch:
            // report it rather than pretending the check passed.
            fail("could not link the patched class: " + t);
            return false;
        }
    }

    private static byte[] read(String className) throws Exception {
        InputStream in = TransformerCheck.class.getClassLoader()
                .getResourceAsStream(className.replace('.', '/') + ".class");
        if (in == null) return null;

        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
            return out.toByteArray();
        } finally {
            in.close();
        }
    }

    private static void fail(String message) {
        System.err.println("    FAILED: " + message);
        failures++;
    }
}
