package com.questforge.content.core;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FrameNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

import net.minecraft.launchwrapper.IClassTransformer;

/**
 * Injects a hook at the head of net.minecraft.inventory.Container.slotClick.
 *
 * The method is matched by DESCRIPTOR, not by name. slotClick is the only method
 * in Container with the signature (int,int,int,EntityPlayer) -> ItemStack, so
 * this works unchanged in a dev workspace (MCP name "slotClick") and in a real
 * instance (SRG name "func_75144_a") without hardcoding either.
 *
 * Injected equivalent:
 *
 *   public ItemStack slotClick(int slotId, int button, int mode, EntityPlayer player) {
 *       if (QFHooks.onSlotClick(this, slotId, button, mode, player)) return null;
 *       ... original body ...
 *   }
 */
public class ContainerTransformer implements IClassTransformer {

    private static final String TARGET = "net.minecraft.inventory.Container";

    private static final String DESC =
            "(IIILnet/minecraft/entity/player/EntityPlayer;)Lnet/minecraft/item/ItemStack;";

    private static final String HOOK_OWNER = "com/questforge/content/ench/QFHooks";
    private static final String HOOK_NAME = "onSlotClick";
    private static final String HOOK_DESC =
            "(Lnet/minecraft/inventory/Container;IIILnet/minecraft/entity/player/EntityPlayer;)Z";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null || !TARGET.equals(transformedName)) return basicClass;

        ClassNode node = new ClassNode();
        new ClassReader(basicClass).accept(node, 0);

        MethodNode target = null;
        for (MethodNode m : node.methods) {
            if (DESC.equals(m.desc)) {
                target = m;
                break;
            }
        }

        if (target == null) {
            System.err.println("[QuestForgeContent] FAILED to find Container.slotClick by "
                    + "descriptor " + DESC + " -- drag-and-drop enchanting will not work.");
            return basicClass;
        }

        System.out.println("[QuestForgeContent] Patching Container." + target.name
                + " for drag-and-drop enchanting.");

        LabelNode skip = new LabelNode();
        InsnList inject = new InsnList();
        inject.add(new VarInsnNode(Opcodes.ALOAD, 0));   // this
        inject.add(new VarInsnNode(Opcodes.ILOAD, 1));   // slotId
        inject.add(new VarInsnNode(Opcodes.ILOAD, 2));   // clickedButton
        inject.add(new VarInsnNode(Opcodes.ILOAD, 3));   // mode
        inject.add(new VarInsnNode(Opcodes.ALOAD, 4));   // player
        inject.add(new MethodInsnNode(Opcodes.INVOKESTATIC,
                HOOK_OWNER, HOOK_NAME, HOOK_DESC, false));
        inject.add(new JumpInsnNode(Opcodes.IFEQ, skip)); // hook returned false -> vanilla
        inject.add(new InsnNode(Opcodes.ACONST_NULL));    // handled -> return null
        inject.add(new InsnNode(Opcodes.ARETURN));
        inject.add(skip);
        // Java 7+ bytecode requires a stackmap frame at every branch target. At this
        // label the locals and stack are exactly as they were on method entry, so
        // F_SAME is correct -- and far cheaper than COMPUTE_FRAMES, which would need
        // to resolve common superclasses through the launch classloader.
        inject.add(new FrameNode(Opcodes.F_SAME, 0, null, 0, null));

        target.instructions.insert(inject);

        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        return writer.toByteArray();
    }
}
