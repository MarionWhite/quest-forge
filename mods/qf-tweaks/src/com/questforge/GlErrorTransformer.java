package com.questforge;

import java.util.List;

import net.minecraft.launchwrapper.IClassTransformer;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * Stops OptiFine's shader error check costing most of every frame.
 *
 * OptiFine 1.7.10 E7 calls Shaders.checkGLError at about thirty checkpoints a
 * frame, and on any pending error it does System.err.format -- unconditionally,
 * with no setting to turn it off. Sildur's Vibrant v2.01 is written for newer
 * OptiFine and leaves an "Invalid operation" pending at most of those
 * checkpoints, so every frame printed about thirty lines. stderr goes through
 * FML's TracingPrintStream, which flushes on every line, and in TEST-LAUNCH.bat
 * it lands in a console window, which is slower still.
 *
 * Measured on 2026-10-16 (7900X, RTX 5070 Ti, 2560x1440, Vibrant High): 75% of
 * render-thread samples were inside that print, at 22-30 fps with the GPU 10%
 * busy. The errors themselves change nothing on screen.
 *
 * The patch replaces the body of all three checkGLError overloads with a call to
 * the matching GlErrorLog.check, which calls glGetError exactly as before (so the error flag is still cleared and
 * the return value is the same) but logs each distinct error once. Same
 * signature, so no caller changes, and the new body has no branches, so it
 * needs no stack map frames of its own.
 *
 * Client only: OptiFine does not load on a dedicated server.
 */
public class GlErrorTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "shadersmod.client.Shaders";

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

            // Three overloads, one to three Strings: the checkpoint, plus the
            // program and uniform names the uniform setters pass. All of them
            // print, and Vibrant's fog uniforms alone hit the two-String one
            // about twenty times a frame.
            int patched = 0;
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                int strings = stringArgs(m);
                if (!"checkGLError".equals(m.name) || strings == 0
                        || (m.access & Opcodes.ACC_STATIC) == 0) {
                    continue;
                }
                InsnList body = new InsnList();
                for (int i = 0; i < strings; i++) {
                    body.add(new VarInsnNode(Opcodes.ALOAD, i));
                }
                body.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "com/questforge/GlErrorLog",
                        "check", m.desc, false));
                body.add(new InsnNode(Opcodes.IRETURN));
                m.instructions = body;
                m.tryCatchBlocks.clear();
                if (m.localVariables != null) m.localVariables.clear();
                m.maxStack = strings;
                m.maxLocals = strings;
                patched++;
            }
            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] Shaders.checkGLError not found - leaving OptiFine "
                        + "untouched; shader GL errors will still be printed every frame.");
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: OptiFine shader GL errors are logged "
                    + "once each instead of every frame ({} overload(s)).", patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }

    /** 1-3 for (String...)I with only String parameters, else 0. */
    private static int stringArgs(MethodNode m) {
        if ("(Ljava/lang/String;)I".equals(m.desc)) return 1;
        if ("(Ljava/lang/String;Ljava/lang/String;)I".equals(m.desc)) return 2;
        if ("(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)I".equals(m.desc)) return 3;
        return 0;
    }
}
