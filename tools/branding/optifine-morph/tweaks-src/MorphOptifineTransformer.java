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
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;

/**
 * QuestForgeTweaks transformer for Morph + OptiFine E7.
 *
 * Two independent patches; each fails soft if the target is missing:
 *
 * 1. morph.common.core.EventHandler.onRenderHand
 *    Same reentrancy guard as Morph-Beta-0.9.3-QF-OPTIFINE.jar:
 *    if (MorphHandGuard.shouldSkip()) return;
 *    MorphHandGuard.enter();
 *    ...original...
 *    MorphHandGuard.leave();  // before every return
 *
 * 2. GLAllocation.deleteDisplayLists / func_74523_b
 *    After Map.remove, if the value is null, return instead of NPE.
 *    Belt-and-suspenders for the kill-acquire crash; the work-folder
 *    Morph jar already NOPs Morph's own deleteDisplayLists calls.
 *
 * Register in QuestForgeCore.getASMTransformerClass after
 * PanelButtonQuestTransformer. Do not rebuild/install Tweaks into live
 * mods\\ until the owner has tested the work-folder Morph jar.
 */
public class MorphOptifineTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String MORPH_HANDLER = "morph.common.core.EventHandler";
    private static final String GL_DEOBF = "net.minecraft.client.renderer.GLAllocation";
    private static final String GL_OBF = "ban";
    private static final String GUARD = "com/questforge/MorphHandGuard";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) {
            return basicClass;
        }
        if (MORPH_HANDLER.equals(transformedName) || MORPH_HANDLER.equals(name)) {
            return patchOnRenderHand(basicClass);
        }
        if (GL_DEOBF.equals(transformedName) || GL_OBF.equals(transformedName)
                || GL_DEOBF.equals(name) || GL_OBF.equals(name)) {
            return patchDeleteDisplayLists(transformedName, basicClass);
        }
        return basicClass;
    }

    private byte[] patchOnRenderHand(byte[] basicClass) {
        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            MethodNode target = null;
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                if ("onRenderHand".equals(m.name)
                        && m.desc != null
                        && m.desc.contains("RenderHandEvent")) {
                    target = m;
                    break;
                }
            }
            if (target == null) {
                LOG.warn("[QuestForgeTweaks] Morph EventHandler.onRenderHand not found; leaving untouched.");
                return basicClass;
            }

            LabelNode cont = new LabelNode();
            InsnList prefix = new InsnList();
            prefix.add(new MethodInsnNode(Opcodes.INVOKESTATIC, GUARD, "shouldSkip", "()Z", false));
            prefix.add(new JumpInsnNode(Opcodes.IFEQ, cont));
            prefix.add(new InsnNode(Opcodes.RETURN));
            prefix.add(cont);
            prefix.add(new MethodInsnNode(Opcodes.INVOKESTATIC, GUARD, "enter", "()V", false));
            target.instructions.insert(prefix);

            AbstractInsnNode[] insns = target.instructions.toArray();
            boolean seenCont = false;
            int leaves = 0;
            for (int i = 0; i < insns.length; i++) {
                AbstractInsnNode insn = insns[i];
                if (insn == cont) {
                    seenCont = true;
                    continue;
                }
                if (!seenCont) {
                    continue;
                }
                int op = insn.getOpcode();
                if (op == Opcodes.RETURN || op == Opcodes.ATHROW) {
                    InsnList leave = new InsnList();
                    leave.add(new MethodInsnNode(Opcodes.INVOKESTATIC, GUARD, "leave", "()V", false));
                    target.instructions.insertBefore(insn, leave);
                    leaves++;
                }
            }

            ClassWriter writer = new SafeClassWriter(reader, ClassWriter.COMPUTE_MAXS);
            node.accept(writer);
            byte[] result = writer.toByteArray();
            LOG.info("[QuestForgeTweaks] Morph onRenderHand reentrancy guard applied ({} leave sites, {} -> {} bytes).",
                    leaves, basicClass.length, result.length);
            return result;
        } catch (Throwable t) {
            LOG.warn("[QuestForgeTweaks] Morph onRenderHand transform failed; returning original bytes.", t);
            return basicClass;
        }
    }

    private byte[] patchDeleteDisplayLists(String transformedName, byte[] basicClass) {
        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            MethodNode target = null;
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                if (("deleteDisplayLists".equals(m.name) || "func_74523_b".equals(m.name))
                        && "(I)V".equals(m.desc)) {
                    target = m;
                    break;
                }
            }
            if (target == null) {
                LOG.warn("[QuestForgeTweaks] GLAllocation.deleteDisplayLists not found in {}; leaving untouched.",
                        transformedName);
                return basicClass;
            }

            AbstractInsnNode[] insns = target.instructions.toArray();
            MethodInsnNode removeCall = null;
            for (int i = 0; i < insns.length; i++) {
                int op = insns[i].getOpcode();
                if (op != Opcodes.INVOKEVIRTUAL && op != Opcodes.INVOKEINTERFACE) {
                    continue;
                }
                MethodInsnNode min = (MethodInsnNode) insns[i];
                if ("remove".equals(min.name) && min.desc != null
                        && min.desc.startsWith("(Ljava/lang/Object;)")) {
                    removeCall = min;
                    break;
                }
            }
            if (removeCall == null) {
                LOG.warn("[QuestForgeTweaks] No Map.remove in {}; leaving untouched.", transformedName);
                return basicClass;
            }

            LabelNode ok = new LabelNode();
            InsnList guard = new InsnList();
            guard.add(new InsnNode(Opcodes.DUP));
            guard.add(new JumpInsnNode(Opcodes.IFNONNULL, ok));
            guard.add(new InsnNode(Opcodes.POP));
            guard.add(new InsnNode(Opcodes.RETURN));
            guard.add(ok);
            target.instructions.insert(removeCall, guard);

            ClassWriter writer = new SafeClassWriter(reader, ClassWriter.COMPUTE_MAXS);
            node.accept(writer);
            byte[] result = writer.toByteArray();
            LOG.info("[QuestForgeTweaks] GLAllocation.deleteDisplayLists null-guard applied on {} ({} -> {} bytes).",
                    transformedName, basicClass.length, result.length);
            return result;
        } catch (Throwable t) {
            LOG.warn("[QuestForgeTweaks] GLAllocation transform failed; returning original bytes.", t);
            return basicClass;
        }
    }

    private static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(ClassReader reader, int flags) {
            super(reader, flags);
        }

        @Override
        protected String getCommonSuperClass(String type1, String type2) {
            try {
                return super.getCommonSuperClass(type1, type2);
            } catch (Throwable t) {
                return "java/lang/Object";
            }
        }
    }
}
