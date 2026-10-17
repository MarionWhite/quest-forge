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
 * Keeps Lucky Block's drop expressions working on Java 9 and later.
 *
 * Lucky Block 5.1.0 evaluates every number in its config and drop files
 * ("100", "#rand(1,5)", "0.7") through a JavaScript engine it gets from
 * {@code new ScriptEngineManager(null)} in ExpressionParser's constructor. A
 * null loader means "the bootstrap loader only", which on Java 8 finds the
 * JDK's built-in Nashorn. Java 15 removed Nashorn from the JDK, so on Java 25
 * the engine is null and every expression throws ExpressionParserException:
 * drops lose their counts, chances and NBT numbers. lwjgl3ify bundles
 * standalone Nashorn on the application class path, where a null loader
 * cannot see it. Found 2026-10-16 on the Java 25 + lwjgl3ify trial server.
 *
 * The patch adds one instruction: the null argument is passed through
 * LuckyScriptFix.loader before the constructor runs. That returns null
 * unchanged whenever null already finds a JavaScript engine (every Java 8
 * JVM), so on Java 8 the mod behaves exactly as before. No branches added, so
 * the stack map frames are untouched.
 *
 * Both sides: the server parses drops, the client parses the same config.
 */
public class LuckyScriptTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "mod.lucky.util.ExpressionParser";

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
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn.getOpcode() != Opcodes.INVOKESPECIAL) continue;
                    MethodInsnNode call = (MethodInsnNode) insn;
                    if ("javax/script/ScriptEngineManager".equals(call.owner) && "<init>".equals(call.name)
                            && "(Ljava/lang/ClassLoader;)V".equals(call.desc)) {
                        m.instructions.insertBefore(call, new MethodInsnNode(Opcodes.INVOKESTATIC,
                                "com/questforge/LuckyScriptFix", "loader",
                                "(Ljava/lang/ClassLoader;)Ljava/lang/ClassLoader;", false));
                        patched++;
                    }
                }
            }

            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] No ScriptEngineManager(ClassLoader) call in {} - leaving it "
                        + "untouched; Lucky Block expressions will fail on Java 9+.", TARGET);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: Lucky Block's script engine falls back to the "
                    + "game's class loader when the JDK has no JavaScript engine ({} site(s)).", patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }
}
