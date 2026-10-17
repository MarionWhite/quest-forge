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
 * Keeps Recurrent Complex's loot tables with NBT loading under a newer Gson.
 *
 * RC writes item NBT in a "safe" form, where every tag is wrapped as
 * {"nbtType":"short","nbt":1}. Its NBTTagCompoundSerializer and
 * NBTTagListSerializer decode each child by asking the Gson context for
 * NbtToJson.getNBTTypeSmart(child). For a wrapper that is always
 * NBTTagCompound, because the wrapper is a JSON object. The adapter behind it
 * (a type-hierarchy adapter for NBTBase) reads "nbtType" and returns whatever
 * the tag really is, an NBTTagShort here. Gson 2.2.4, which Forge ships, never
 * checked the result. The Gson 2.10 that lwjgl3ify puts in front of it on Java
 * 25 does: "returned wrong type; requested NBTTagCompound but got NBTTagShort".
 * The whole file then fails to load. Four of RC's bundled inventory generators
 * hold enchanted books in this form (Holy, PeacefulCrypt, TribalChest, Unholy),
 * so those structures generated without their loot. Found 2026-10-16 on the
 * Java 25 + lwjgl3ify trial server.
 *
 * The patch swaps the getNBTTypeSmart call in those two classes for
 * RecNbtFix.type, which has the same signature. It returns NBTBase for a
 * wrapper object when the running Gson is newer than 2.2.4, and otherwise
 * exactly what getNBTTypeSmart returns. NBTBase reaches the same adapter and
 * passes Gson's check. On Java 8 (Gson 2.2.4) nothing changes. No branches
 * added, so the stack map frames are untouched.
 *
 * Both sides: servers generate the structures, and a Java 25 client's
 * integrated server does too.
 */
public class RecNbtTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String COMPOUND = "ivorius.reccomplex.json.NBTTagCompoundSerializer";
    private static final String LIST = "ivorius.reccomplex.json.NBTTagListSerializer";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) {
            return null;
        }
        if (!COMPOUND.equals(transformedName) && !LIST.equals(transformedName)) {
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
                    if (insn.getOpcode() != Opcodes.INVOKESTATIC) continue;
                    MethodInsnNode call = (MethodInsnNode) insn;
                    if ("ivorius/reccomplex/json/NbtToJson".equals(call.owner)
                            && "getNBTTypeSmart".equals(call.name)
                            && "(Lcom/google/gson/JsonElement;)Ljava/lang/Class;".equals(call.desc)) {
                        call.owner = "com/questforge/RecNbtFix";
                        call.name = "type";
                        patched++;
                    }
                }
            }

            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] No getNBTTypeSmart call in {} - leaving it untouched; "
                        + "RC loot with NBT fails to load under Gson 2.10+.", transformedName);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: {} decodes wrapped NBT tags through "
                    + "RecNbtFix ({} site(s)).", transformedName, patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + transformedName
                    + "; returning original bytes.", t);
            return basicClass;
        }
    }
}
