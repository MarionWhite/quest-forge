package com.questforge.content.core;

import java.util.ArrayList;
import java.util.List;

import net.minecraft.launchwrapper.IClassTransformer;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * Watches ore veins being placed, so their generation parameters can be read
 * exactly rather than estimated.
 *
 * WHY THIS EXISTS. Counting ore blocks in finished chunks measures the RESULT of
 * generation, which is noisy: an ore at one vein per four hundred chunks needs an
 * enormous sample before its rate settles down. But the parameters themselves are
 * not hidden. Half of them are ordinary object state --
 *
 *     private Block field_150519_a;   // which ore
 *     private int numberOfBlocks;     // vein size
 *
 * -- and the other half live at the call site, as a loop bound and two arguments:
 *
 *     this.genStandardOre1(20, this.coalGen, 0, 128);   // 20 veins, y 0..128
 *
 * You cannot read a for-loop's bound off an object, which is why no registry can
 * report ore rarity. You CAN watch the loop run. Every vein in the game -- vanilla
 * and modded alike -- is placed by a call to WorldGenMinable.generate, so a hook on
 * that one method reports the ore, its vein size and its exact position, once per
 * vein. Counting those calls per chunk gives the real frequency directly: 20 coal,
 * 1 diamond, whatever this pack's configs actually produce.
 *
 * HOW IT AVOIDS OBFUSCATED NAMES. Nothing here is matched by field or method name,
 * because those differ between the development workspace and a real server. The
 * class is found by name (transformers get the deobfuscated name), and everything
 * inside it structurally:
 *
 *  - The three-argument constructor is the one whose descriptor is (LX;ILX;)V with
 *    the SAME class X in both object positions -- that shape is unique here. Its
 *    three PUTFIELDs, in order, are the ore field, the size field and the target
 *    field, because that is the order the constructor assigns them.
 *  - The metadata field is the single int PUTFIELD in the four-argument constructor.
 *  - generate() is the method taking (something, java.util.Random, int, int, int)
 *    and returning boolean. java.util.Random is never obfuscated, which makes that
 *    descriptor a reliable fingerprint.
 *
 * The hook takes the block as java.lang.Object for the same reason: naming
 * net.minecraft.block.Block in a descriptor would bake in a name that changes.
 */
public class OreGenTransformer implements IClassTransformer {

    private static final String TARGET = "net.minecraft.world.gen.feature.WorldGenMinable";

    private static final String HOOKS = "com/questforge/content/survey/OreGenHooks";
    // The trailing Object is the World the vein is being placed in, needed to look
    // up the biome. Passed as Object for the same reason the ore is: the injected
    // call then carries no obfuscated type in its descriptor, so this one string
    // is correct in both the dev workspace and a real server.
    private static final String HOOK_DESC = "(Ljava/lang/Object;IIIIILjava/lang/Object;)V";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null || !TARGET.equals(transformedName)) return basicClass;

        try {
            ClassNode node = new ClassNode();
            new ClassReader(basicClass).accept(node, 0);

            Fields fields = findFields(node);
            if (fields == null) {
                System.out.println("[QuestForgeContent] WorldGenMinable did not have the "
                        + "expected constructor shape; vein tracking disabled.");
                return basicClass;
            }

            MethodNode generate = findGenerate(node);
            if (generate == null) {
                System.out.println("[QuestForgeContent] WorldGenMinable.generate not found; "
                        + "vein tracking disabled.");
                return basicClass;
            }

            InsnList probe = new InsnList();
            probe.add(new VarInsnNode(Opcodes.ALOAD, 0));
            probe.add(new FieldInsnNode(Opcodes.GETFIELD, node.name, fields.ore, fields.oreDesc));
            probe.add(new VarInsnNode(Opcodes.ALOAD, 0));
            probe.add(new FieldInsnNode(Opcodes.GETFIELD, node.name, fields.size, "I"));

            if (fields.meta == null) {
                probe.add(new org.objectweb.asm.tree.InsnNode(Opcodes.ICONST_0));
            } else {
                probe.add(new VarInsnNode(Opcodes.ALOAD, 0));
                probe.add(new FieldInsnNode(Opcodes.GETFIELD, node.name, fields.meta, "I"));
            }

            // generate(this, world, random, x, y, z): x/y/z are locals 3, 4 and 5,
            // and the World is local 1.
            probe.add(new VarInsnNode(Opcodes.ILOAD, 3));
            probe.add(new VarInsnNode(Opcodes.ILOAD, 4));
            probe.add(new VarInsnNode(Opcodes.ILOAD, 5));
            probe.add(new VarInsnNode(Opcodes.ALOAD, 1));
            probe.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOKS, "vein", HOOK_DESC, false));

            // At the very top of the method, so it runs once per vein and before any
            // branch target -- which keeps it stack-neutral and needing no new frame.
            generate.instructions.insert(probe);

            ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
            node.accept(writer);

            System.out.println("[QuestForgeContent] Patching WorldGenMinable.generate to record "
                    + "ore veins (ore=" + fields.ore + ", size=" + fields.size
                    + ", meta=" + fields.meta + ").");
            return writer.toByteArray();

        } catch (Throwable t) {
            // A survey aid is never worth failing to launch over.
            System.out.println("[QuestForgeContent] Could not patch WorldGenMinable: " + t);
            return basicClass;
        }
    }

    /** The field names this class happens to use, worked out from its constructors. */
    private static class Fields {
        String ore;
        String oreDesc;
        String size;
        String meta;
    }

    private static Fields findFields(ClassNode node) {
        Fields found = null;

        for (MethodNode method : node.methods) {
            if (!"<init>".equals(method.name)) continue;

            String blockType = sameTypeThreeArg(method.desc);
            if (blockType == null) continue;

            List<FieldInsnNode> puts = putFields(method);
            if (puts.size() < 3) continue;

            // Assigned in order: ore block, vein size, target block.
            if (!puts.get(0).desc.equals(blockType)) continue;
            if (!"I".equals(puts.get(1).desc)) continue;

            found = new Fields();
            found.ore = puts.get(0).name;
            found.oreDesc = puts.get(0).desc;
            found.size = puts.get(1).name;
            break;
        }

        if (found == null) return null;

        // The metadata-carrying constructor: (Block, int meta, int number, Block).
        for (MethodNode method : node.methods) {
            if (!"<init>".equals(method.name)) continue;
            if (!isFourArgMetaCtor(method.desc, found.oreDesc)) continue;

            for (FieldInsnNode put : putFields(method)) {
                if ("I".equals(put.desc) && !put.name.equals(found.size)) {
                    found.meta = put.name;
                    break;
                }
            }
        }

        return found;
    }

    /** Returns the object type if the descriptor is (LX;ILX;)V with the same X twice. */
    private static String sameTypeThreeArg(String desc) {
        if (desc == null || !desc.endsWith(")V")) return null;

        int open = desc.indexOf('(');
        String args = desc.substring(open + 1, desc.indexOf(')'));

        if (!args.startsWith("L")) return null;
        int firstEnd = args.indexOf(';');
        if (firstEnd < 0) return null;

        String type = args.substring(0, firstEnd + 1);
        return args.equals(type + "I" + type) ? type : null;
    }

    private static boolean isFourArgMetaCtor(String desc, String blockType) {
        if (desc == null) return false;
        int open = desc.indexOf('(');
        int close = desc.indexOf(')');
        if (open < 0 || close < 0) return false;
        return desc.substring(open + 1, close).equals(blockType + "II" + blockType);
    }

    private static List<FieldInsnNode> putFields(MethodNode method) {
        List<FieldInsnNode> puts = new ArrayList<FieldInsnNode>();
        for (AbstractInsnNode insn : method.instructions.toArray()) {
            if (insn.getOpcode() == Opcodes.PUTFIELD) puts.add((FieldInsnNode) insn);
        }
        return puts;
    }

    /**
     * generate(World, Random, int, int, int) -> boolean.
     *
     * Matched on java.util.Random, which no obfuscator touches, so this fingerprint
     * survives the difference between the dev workspace and a real server.
     */
    private static MethodNode findGenerate(ClassNode node) {
        for (MethodNode method : node.methods) {
            String desc = method.desc;
            if (desc == null || !desc.endsWith("III)Z")) continue;
            if (desc.indexOf("Ljava/util/Random;") < 0) continue;
            if ((method.access & Opcodes.ACC_STATIC) != 0) continue;
            return method;
        }
        return null;
    }
}
