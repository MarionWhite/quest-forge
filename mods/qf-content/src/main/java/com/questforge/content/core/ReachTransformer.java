package com.questforge.content.core;

import java.util.ListIterator;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

import net.minecraft.launchwrapper.IClassTransformer;

/**
 * Makes the Reach enchantment possible.
 *
 * 1.7.10 has no reach attribute -- generic.attackSpeed and generic.reachDistance
 * are both later additions -- so range is a hardcoded number, and both ends of the
 * connection enforce their own copy of it.
 *
 *   PlayerControllerMP.getBlockReachDistance() decides how far the CLIENT will even
 *   look for a target. That one method feeds both the block ray trace and the
 *   entity ray trace in EntityRenderer.getMouseOver, so patching it extends mining
 *   and melee together. Without it an extended swing hits nothing, because the
 *   client never found anything to swing at.
 *
 *   NetHandlerPlayServer's 36.0D decides how far the SERVER will believe an attack
 *   on an entity. Without it the client aims fine and the server drops the packet.
 *
 * The server's BLOCK reach is deliberately not patched here: Forge already replaced
 * those checks with ItemInWorldManager.getBlockReachDistance(), which has a public
 * setter, so ReachUpkeep does that half with an ordinary API call instead.
 *
 * Both patches are made by shape rather than by name -- the client method by its
 * 5.0F/4.5F constants, the server check by its value -- so neither depends on MCP
 * or SRG naming and the same jar works in a dev workspace and in the pack.
 */
public class ReachTransformer implements IClassTransformer {

    private static final String CONTROLLER = "net.minecraft.client.multiplayer.PlayerControllerMP";
    private static final String NET_HANDLER = "net.minecraft.network.NetHandlerPlayServer";

    private static final String HOOKS = "com/questforge/content/ench/QFReachHooks";
    private static final String CLIENT_HOOKS = "com/questforge/content/ench/QFReachClientHooks";

    /** Vanilla's server-side "close enough to have clicked that" tolerance, squared. */
    private static final double SERVER_REACH_SQ = 36.0D;

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) return basicClass;

        if (CONTROLLER.equals(transformedName)) return patchClient(basicClass);
        if (NET_HANDLER.equals(transformedName)) return patchServer(basicClass);
        return basicClass;
    }

    /**
     * Wraps the return value of getBlockReachDistance.
     *
     * Injecting at every FRETURN rather than at the head keeps the patch
     * stack-neutral -- the original float is already on the stack, the hook
     * consumes it and pushes the adjusted one -- so no stackmap frame is needed.
     */
    private byte[] patchClient(byte[] basicClass) {
        ClassNode node = read(basicClass);

        MethodNode target = null;
        for (MethodNode m : node.methods) {
            if ("()F".equals(m.desc) && loadsBoth(m, 5.0F, 4.5F)) {
                target = m;
                break;
            }
        }

        if (target == null) {
            System.err.println("[QuestForgeContent] Could not find "
                    + "PlayerControllerMP.getBlockReachDistance by its constants; "
                    + "Reach will not extend targeting range.");
            return basicClass;
        }

        int patched = 0;
        ListIterator<AbstractInsnNode> it = target.instructions.iterator();
        while (it.hasNext()) {
            AbstractInsnNode insn = it.next();
            if (insn.getOpcode() != Opcodes.FRETURN) continue;

            InsnList call = new InsnList();
            call.add(new MethodInsnNode(Opcodes.INVOKESTATIC,
                    CLIENT_HOOKS, "adjust", "(F)F", false));
            target.instructions.insertBefore(insn, call);
            patched++;
        }

        System.out.println("[QuestForgeContent] Patching PlayerControllerMP."
                + target.name + " for Reach (" + patched + " return site(s)).");
        return write(node);
    }

    /**
     * Replaces the hardcoded 36.0D entity-reach tolerance with a per-player value.
     *
     * There is exactly one of these, in processUseEntity. The block-breaking and
     * block-placing checks in this same class already go through Forge's settable
     * getBlockReachDistance, so they are left alone.
     *
     * The handler itself is passed to the hook rather than its player field: the
     * field's name differs between a dev workspace and a real instance, and
     * looking it up reflectively on the far side costs one lookup ever.
     */
    private byte[] patchServer(byte[] basicClass) {
        ClassNode node = read(basicClass);
        int patched = 0;

        for (MethodNode m : node.methods) {
            // Collected first, then rewritten. Mutating an InsnList through its own
            // iterator is version-sensitive; two passes are not.
            java.util.List<AbstractInsnNode> constants = new java.util.ArrayList<AbstractInsnNode>();

            ListIterator<AbstractInsnNode> it = m.instructions.iterator();
            while (it.hasNext()) {
                AbstractInsnNode insn = it.next();
                if (!(insn instanceof LdcInsnNode)) continue;

                Object cst = ((LdcInsnNode) insn).cst;
                if (cst instanceof Double && ((Double) cst).doubleValue() == SERVER_REACH_SQ) {
                    constants.add(insn);
                }
            }

            for (AbstractInsnNode insn : constants) {
                InsnList call = new InsnList();
                call.add(new VarInsnNode(Opcodes.ALOAD, 0));
                call.add(new MethodInsnNode(Opcodes.INVOKESTATIC,
                        HOOKS, "serverReachSq", "(Ljava/lang/Object;)D", false));

                m.instructions.insertBefore(insn, call);
                m.instructions.remove(insn);
                patched++;
            }
        }

        if (patched == 0) {
            System.err.println("[QuestForgeContent] Found no 36.0D entity-reach check in "
                    + "NetHandlerPlayServer; Reach will still extend mining range, but "
                    + "attacks beyond six blocks will be rejected by the server.");
            return basicClass;
        }

        System.out.println("[QuestForgeContent] Patching NetHandlerPlayServer for Reach ("
                + patched + " distance check(s)).");
        return write(node);
    }

    private static boolean loadsBoth(MethodNode m, float a, float b) {
        boolean foundA = false;
        boolean foundB = false;

        ListIterator<AbstractInsnNode> it = m.instructions.iterator();
        while (it.hasNext()) {
            AbstractInsnNode insn = it.next();
            if (!(insn instanceof LdcInsnNode)) continue;

            Object cst = ((LdcInsnNode) insn).cst;
            if (!(cst instanceof Float)) continue;

            float value = ((Float) cst).floatValue();
            if (value == a) foundA = true;
            if (value == b) foundB = true;
        }
        return foundA && foundB;
    }

    private static ClassNode read(byte[] basicClass) {
        ClassNode node = new ClassNode();
        new ClassReader(basicClass).accept(node, 0);
        return node;
    }

    private static byte[] write(ClassNode node) {
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        return writer.toByteArray();
    }
}
