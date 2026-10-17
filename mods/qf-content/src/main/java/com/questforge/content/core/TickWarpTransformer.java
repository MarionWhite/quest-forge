package com.questforge.content.core;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

import net.minecraft.launchwrapper.IClassTransformer;

/**
 * Census-only tick-warp: lets a census server run its ticks back to back
 * instead of one every 50 ms.
 *
 * A census server spends about 2 ms of every 50 ms tick working and the rest
 * asleep, and every census window is counted in ticks, so the sleep is pure
 * waiting. The obvious patch, taking the sleep out of MinecraftServer.run,
 * does nothing in this pack: FastCraft replaces that loop with its own
 * (fastcraft.u.a, called from run through fastcraft.H.aq) and excludes its own
 * package from every transformer. It is patched from the other side instead.
 *
 * Injected equivalent, at the head of MinecraftServer.tick():
 *
 *   public void tick() {
 *       com.questforge.content.census.TickWarp.beforeTick(this);
 *       ... original body: one full tick ...
 *   }
 *
 * beforeTick runs further complete ticks (by calling tick() itself, guarded
 * against re-entry) until a real-time budget below 50 ms is spent, so the
 * outer loop, whichever mod owns it, still sees a tick that returned in time
 * and sleeps the remainder. Neither loop's catch-up logic ever sees the server
 * fall behind, and 1.7.10 has no hang watchdog. Every tick is an ordinary
 * tick() call, so FML's ServerTickEvents, world, entity, network and autosave
 * ticking all happen per tick exactly as before.
 *
 * Inert unless the JVM was started with -Dqf.census.tickwarp=true: without it
 * transform() hands back the very array it was given, so the class is
 * byte-identical to an unpatched one.
 *
 * tick() is found by name (MCP "tick" in dev, SRG "func_71217_p" in the pack)
 * and descriptor ()V; this runs after FML's deobfuscation (SortingIndex 1001).
 */
public class TickWarpTransformer implements IClassTransformer {

    private static final String TARGET = "net.minecraft.server.MinecraftServer";
    private static final String HOOK_OWNER = "com/questforge/content/census/TickWarp";

    static final boolean ENABLED = "true".equalsIgnoreCase(System.getProperty("qf.census.tickwarp"));

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (!ENABLED || basicClass == null || !TARGET.equals(transformedName)) return basicClass;

        ClassNode node = new ClassNode();
        new ClassReader(basicClass).accept(node, 0);

        MethodNode target = null;
        for (MethodNode m : node.methods) {
            if ("()V".equals(m.desc) && ("tick".equals(m.name) || "func_71217_p".equals(m.name))) {
                target = m;
                break;
            }
        }
        if (target == null) {
            System.err.println("[QuestForgeContent] Tick-warp requested but MinecraftServer.tick() "
                    + "was not found; the server will run at normal speed.");
            return basicClass;
        }

        InsnList inject = new InsnList();
        inject.add(new VarInsnNode(Opcodes.ALOAD, 0));
        inject.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOK_OWNER, "beforeTick",
                "(Lnet/minecraft/server/MinecraftServer;)V", false));
        // Stack-neutral and no branch, so no stackmap frame is needed.
        target.instructions.insert(inject);

        System.out.println("[QuestForgeContent] Tick-warp ON: patched MinecraftServer." + target.name
                + " to run ticks back to back (census only; -Dqf.census.tickwarp).");

        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        return writer.toByteArray();
    }
}
