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
 * Keeps AsieLib's saved nicknames loading under a newer Gson.
 *
 * NicknameRepository.loadNicknames reads nicknames.json (in the server folder)
 * with gson.fromJson(reader, TypeToken<HashBiMap<String,String>>) and casts the
 * result to Gson's LinkedTreeMap. That only ever worked because Gson 2.2.4 hands
 * out a LinkedTreeMap for any Map type it cannot construct, HashBiMap included.
 * Gson 2.10 (lwjgl3ify's, on Java 25) refuses instead: "Unable to create
 * instance of class com.google.common.collect.HashBiMap". The file exists from
 * the second boot on (AsieLib writes "{}" at shutdown), so every later boot
 * printed that stack trace and dropped any /nick names. Found 2026-10-16 on the
 * Java 25 + lwjgl3ify trial server.
 *
 * The patch swaps that one fromJson call for AsieNickFix.fromJson, which has
 * the same stack effect (gson, reader, type -> Object). It makes the original
 * call first and returns its result; only if Gson throws does it parse the same
 * text as a Map<String,String>, which is the LinkedTreeMap AsieLib expects. On
 * Java 8 the original call succeeds, so nothing changes. No branches added, so
 * the stack map frames are untouched.
 *
 * Server side in practice: the repository is loaded in AsieLib's init.
 */
public class AsieNickTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "pl.asie.lib.chat.NicknameRepository";

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
                if (!"loadNicknames".equals(m.name) || !"()V".equals(m.desc)) continue;
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn.getOpcode() != Opcodes.INVOKEVIRTUAL) continue;
                    MethodInsnNode call = (MethodInsnNode) insn;
                    if ("com/google/gson/Gson".equals(call.owner) && "fromJson".equals(call.name)
                            && "(Ljava/io/Reader;Ljava/lang/reflect/Type;)Ljava/lang/Object;".equals(call.desc)) {
                        m.instructions.set(call, new MethodInsnNode(Opcodes.INVOKESTATIC,
                                "com/questforge/AsieNickFix", "fromJson",
                                "(Lcom/google/gson/Gson;Ljava/io/Reader;Ljava/lang/reflect/Type;)Ljava/lang/Object;",
                                false));
                        patched++;
                    }
                }
            }

            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] No Gson.fromJson(Reader, Type) call in {}.loadNicknames - "
                        + "leaving it untouched; nicknames fail to load under Gson 2.10+.", TARGET);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: AsieLib nicknames load through AsieNickFix "
                    + "({} site(s)).", patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }
}
