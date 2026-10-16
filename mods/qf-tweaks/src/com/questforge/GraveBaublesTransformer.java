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
import org.objectweb.asm.tree.IntInsnNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodNode;

/**
 * Stops a player's death disconnecting everyone on a dedicated server.
 *
 * When a player dies, GraveStones moves their four Baubles into the grave and then
 * asks Baubles to resync the slots -- in a loop to 7, copied from its seven-slot
 * RPG Inventory code. Baubles builds a PacketSyncBauble for "slot 4" without
 * complaint (getStackInSlot is bounds-checked) and sends it to every player.
 * Each client writes it into a four-element array, throws
 * ArrayIndexOutOfBoundsException in the packet handler, and is disconnected.
 *
 * Singleplayer never shows it: Baubles skips the send when the server and
 * client share a process. Found by joining a dedicated server and dying.
 *
 * The patch changes that loop bound from 7 to 4 -- the BIPUSH 7 that follows the
 * "syncSlotToClients" reflection lookup. Same type and stack shape, so the
 * class's existing stack map frames stay valid and are kept as they are.
 *
 * This one runs on the server, unlike every other patch in this coremod, so
 * QuestForgeTweaks must be installed on the server too.
 */
public class GraveBaublesTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "net.subaraki.gravestone.handler.GravestoneEventHandler";

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
                boolean afterLookup = false;
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn instanceof LdcInsnNode && "syncSlotToClients".equals(((LdcInsnNode) insn).cst)) {
                        afterLookup = true;
                    } else if (afterLookup && insn.getOpcode() == Opcodes.BIPUSH
                            && ((IntInsnNode) insn).operand == 7) {
                        ((IntInsnNode) insn).operand = 4;
                        patched++;
                        afterLookup = false;
                    }
                }
            }

            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] GraveStones Baubles sync loop not found in {} - leaving "
                        + "class untouched; deaths on a dedicated server may disconnect players.", TARGET);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: GraveStones now resyncs 4 Baubles slots, "
                    + "not 7 ({} site(s)).", patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }
}
