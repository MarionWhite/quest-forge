package com.questforge;

import java.util.List;

import net.minecraft.launchwrapper.IClassTransformer;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;

/**
 * Stops LittleMaidMob's model scan crashing the game when any jar holds a class
 * that cannot be loaded.
 *
 * MMMLib's MultiModelManager.addModelClass walks every jar on the client's
 * classpath and calls ClassLoader.loadClass on each class it finds, then checks
 * whether it is a maid model. Its handler catches Exception, but a class whose
 * dependencies are absent throws NoClassDefFoundError -- an Error -- which
 * escapes and fails mod loading. UniMixins' RuntimeDecompiler (it references
 * Fernflower, which is optional) is the first such class in the jar order, so
 * any modpack with UniMixins, Hodgepodge, ArchaicFix or Angelica is affected;
 * mixin classes and other optional-dependency classes would fail next.
 * Found 2026-10-16 booting the pack under Angelica.
 *
 * The patch swaps that one loadClass call for MmmScanGuard.load, which has the
 * same stack effect (loader, name -> Class) and returns Void.class for a class
 * that cannot be loaded. The scan's own isAssignableFrom check then rejects it.
 * No branches added, so the stack map frames are untouched.
 *
 * Client only: the scan runs only when MMMLib sees a client.
 */
public class MmmScanTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "mmmlibx.lib.multiModel.texture.MultiModelManager";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) {
            return null;
        }
        if (!TARGET.equals(transformedName)) {
            return basicClass;
        }

        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            int patched = 0;
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                if (!"addModelClass".equals(m.name)) continue;
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn.getOpcode() != Opcodes.INVOKEVIRTUAL) continue;
                    MethodInsnNode call = (MethodInsnNode) insn;
                    if ("java/lang/ClassLoader".equals(call.owner) && "loadClass".equals(call.name)
                            && "(Ljava/lang/String;)Ljava/lang/Class;".equals(call.desc)) {
                        m.instructions.set(call, new MethodInsnNode(Opcodes.INVOKESTATIC,
                                "com/questforge/MmmScanGuard", "load",
                                "(Ljava/lang/ClassLoader;Ljava/lang/String;)Ljava/lang/Class;", false));
                        patched++;
                    }
                }
            }

            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] MMMLib model scan not found in {} - leaving it untouched; "
                        + "an unloadable class in any jar can still crash mod loading.", TARGET);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: LittleMaidMob's model scan skips classes "
                    + "that cannot be loaded ({} site(s)).", patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }
}
