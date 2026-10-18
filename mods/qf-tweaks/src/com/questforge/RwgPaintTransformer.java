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
import org.objectweb.asm.tree.FrameNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * Makes RWG decorate a painted (WorldPainter) area by the biomes stored in its
 * chunks. Decision 0003, docs/design/world/poc.md "RWG decoration hook".
 *
 * GTNH Realistic World Gen alpha-1.5.2's ChunkGeneratorRealistic.populate
 * picks trees and plants from its own noise biome map (cmr.getBiomeDataAt over
 * a 9x9 chunk neighbourhood, then RealisticBiomeBase.rDecorate per noise
 * biome) and lays snow and ice from the same noise. It never reads the chunk's
 * stored biome array, so a painted BoP Redwood Forest got a tenth of its
 * redwoods, a painted desert grew forest and the painted sea froze.
 *
 * Three patches, none of which adds a branch to RWG's own methods:
 *   1. provideChunk(cx, cz) first calls RwgPaintHook.generated(this, cx, cz),
 *      so chunks RWG generates itself are never treated as painted.
 *   2. The rDecorate call in populate is redirected to a new static method
 *      qf$rDecorate with the same arguments. It asks
 *      RwgPaintHook.decoratePainted(...) first; outside the painted rectangle
 *      that returns false and the original rDecorate runs unchanged.
 *   3. populate's "snow &lt; 0.59f" test reads RwgPaintHook.snow(snow, cx, cz),
 *      which for a painted chunk runs vanilla's stored-biome ice/snow pass and
 *      returns 1 to skip RWG's.
 *
 * Server side only matters (population), but the class is the same on both.
 */
public class RwgPaintTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "rwg.world.ChunkGeneratorRealistic";
    private static final String OWNER = "rwg/world/ChunkGeneratorRealistic";
    private static final String HOOK = "com/questforge/RwgPaintHook";
    private static final String RBB = "rwg/biomes/realistic/RealisticBiomeBase";
    private static final String RDECORATE_DESC =
            "(Lnet/minecraft/world/World;Ljava/util/Random;IILrwg/util/NoiseGenerator;Lrwg/util/CellNoise;FF)V";
    private static final String BRIDGE = "qf$rDecorate";

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

            int provide = 0, decorate = 0, snow = 0;
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                boolean isProvide = ("func_73154_d".equals(m.name) || "provideChunk".equals(m.name))
                        && "(II)Lnet/minecraft/world/chunk/Chunk;".equals(m.desc);
                boolean isPopulate = ("func_73153_a".equals(m.name) || "populate".equals(m.name))
                        && "(Lnet/minecraft/world/chunk/IChunkProvider;II)V".equals(m.desc);

                if (isProvide) {
                    InsnList head = new InsnList();
                    head.add(new VarInsnNode(Opcodes.ALOAD, 0));
                    head.add(new VarInsnNode(Opcodes.ILOAD, 1));
                    head.add(new VarInsnNode(Opcodes.ILOAD, 2));
                    head.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOK, "generated",
                            "(Ljava/lang/Object;II)V", false));
                    m.instructions.insert(head);
                    provide++;
                }

                if (isPopulate) {
                    for (AbstractInsnNode insn : m.instructions.toArray()) {
                        if (insn.getOpcode() == Opcodes.INVOKEVIRTUAL) {
                            MethodInsnNode call = (MethodInsnNode) insn;
                            if (RBB.equals(call.owner) && "rDecorate".equals(call.name)
                                    && RDECORATE_DESC.equals(call.desc)) {
                                // Same stack, receiver first: [b, world, rand, x, y, perlin, cell, strength, river]
                                m.instructions.set(call, new MethodInsnNode(Opcodes.INVOKESTATIC, OWNER, BRIDGE,
                                        "(L" + RBB + ";" + RDECORATE_DESC.substring(1), false));
                                decorate++;
                            }
                        } else if (insn.getOpcode() == Opcodes.FLOAD) {
                            AbstractInsnNode next = insn.getNext();
                            if (next instanceof LdcInsnNode && Float.valueOf(0.59f).equals(((LdcInsnNode) next).cst)) {
                                InsnList wrap = new InsnList();
                                wrap.add(new VarInsnNode(Opcodes.ILOAD, 2));
                                wrap.add(new VarInsnNode(Opcodes.ILOAD, 3));
                                wrap.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOK, "snow", "(FII)F", false));
                                m.instructions.insert(insn, wrap);
                                snow++;
                            }
                        }
                    }
                }
            }

            if (provide != 1 || decorate != 1 || snow != 1) {
                LOG.warn("[QuestForgeTweaks] RWG paint hook: unexpected {} (provideChunk {}, rDecorate {}, snow {}); "
                        + "leaving it untouched, painted chunks get RWG's noise decoration.", TARGET, provide,
                        decorate, snow);
                return basicClass;
            }

            node.methods.add(bridge());

            // Only non-branching instructions were inserted into RWG's methods and the
            // bridge carries its own frame, so frames need no recomputation.
            ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: RWG decorates painted chunks by their stored biome "
                    + "(provideChunk, rDecorate and snow pass hooked).");
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }

    /**
     * private static void qf$rDecorate(RealisticBiomeBase b, World w, Random r, int x, int y,
     *         NoiseGenerator p, CellNoise c, float strength, float river) {
     *     if (RwgPaintHook.decoratePainted(w, r, x, y, p, c, river)) return;
     *     b.rDecorate(w, r, x, y, p, c, strength, river);
     * }
     */
    private static MethodNode bridge() {
        MethodNode m = new MethodNode(Opcodes.ACC_PRIVATE | Opcodes.ACC_STATIC | Opcodes.ACC_SYNTHETIC, BRIDGE,
                "(L" + RBB + ";" + RDECORATE_DESC.substring(1), null, null);
        InsnList i = m.instructions;
        LabelNode stock = new LabelNode();
        i.add(new VarInsnNode(Opcodes.ALOAD, 1));
        i.add(new VarInsnNode(Opcodes.ALOAD, 2));
        i.add(new VarInsnNode(Opcodes.ILOAD, 3));
        i.add(new VarInsnNode(Opcodes.ILOAD, 4));
        i.add(new VarInsnNode(Opcodes.ALOAD, 5));
        i.add(new VarInsnNode(Opcodes.ALOAD, 6));
        i.add(new VarInsnNode(Opcodes.FLOAD, 8));
        i.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOK, "decoratePainted",
                "(Ljava/lang/Object;Ljava/util/Random;IILjava/lang/Object;Ljava/lang/Object;F)Z", false));
        i.add(new JumpInsnNode(Opcodes.IFEQ, stock));
        i.add(new InsnNode(Opcodes.RETURN));
        i.add(stock);
        i.add(new FrameNode(Opcodes.F_SAME, 0, null, 0, null));
        i.add(new VarInsnNode(Opcodes.ALOAD, 0));
        i.add(new VarInsnNode(Opcodes.ALOAD, 1));
        i.add(new VarInsnNode(Opcodes.ALOAD, 2));
        i.add(new VarInsnNode(Opcodes.ILOAD, 3));
        i.add(new VarInsnNode(Opcodes.ILOAD, 4));
        i.add(new VarInsnNode(Opcodes.ALOAD, 5));
        i.add(new VarInsnNode(Opcodes.ALOAD, 6));
        i.add(new VarInsnNode(Opcodes.FLOAD, 7));
        i.add(new VarInsnNode(Opcodes.FLOAD, 8));
        i.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, RBB, "rDecorate", RDECORATE_DESC, false));
        i.add(new InsnNode(Opcodes.RETURN));
        m.maxStack = 9;
        m.maxLocals = 9;
        return m;
    }
}
