package com.questforge;

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
import org.objectweb.asm.tree.IntInsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;

import java.util.List;

/**
 * Hands MENU music to SplashMusic's looping Clip (true sample loop).
 *
 * Vanilla streamed music.menu cannot sample-loop: it stops and re-queues,
 * which is the silent break. We skip MusicTicker's play path on MENU and
 * keep the Clip running. Game/creative/end music is untouched.
 */
public class MusicTickerTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) {
            return null;
        }
        String n = transformedName != null ? transformedName : name;
        if (isTicker(name, n)) {
            return patchTicker(basicClass);
        }
        if (isType(name, n)) {
            return patchType(basicClass);
        }
        if (isMenuTickHandler(name, n)) {
            return patchMenuTickHandler(basicClass);
        }
        return basicClass;
    }

    private static boolean isMenuTickHandler(String name, String n) {
        return "mainmenuserver.MainMenuTickHandler".equals(n)
                || "mainmenuserver.MainMenuTickHandler".equals(name)
                || "mainmenuserver/MainMenuTickHandler".equals(n);
    }

    private static boolean isTicker(String name, String n) {
        return "btg".equals(name) || "btg".equals(n)
                || "net.minecraft.client.audio.MusicTicker".equals(n);
    }

    private static boolean isType(String name, String n) {
        return "bth".equals(name) || "bth".equals(n)
                || n.endsWith("MusicTicker$MusicType")
                || "net.minecraft.client.audio.MusicTicker$MusicType".equals(n);
    }

    private byte[] patchTicker(byte[] basicClass) {
        ClassNode node = new ClassNode();
        new ClassReader(basicClass).accept(node, 0);
        int hits = 0;
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if ("<init>".equals(m.name)) {
                for (AbstractInsnNode insn = m.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                    if (insn.getOpcode() == Opcodes.BIPUSH && insn instanceof IntInsnNode) {
                        IntInsnNode ii = (IntInsnNode) insn;
                        if (ii.operand == 100) {
                            ii.operand = 0;
                            hits++;
                        }
                    }
                }
            }
            if ("()V".equals(m.desc) && !"<init>".equals(m.name) && !"<clinit>".equals(m.name)) {
                if (alreadyHooked(m)) {
                    continue;
                }
                InsnList pre = new InsnList();
                pre.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "qf/splash/SplashMusic", "onMusicTick", "()Z", false));
                LabelNode cont = new LabelNode();
                pre.add(new JumpInsnNode(Opcodes.IFEQ, cont));
                pre.add(new InsnNode(Opcodes.RETURN));
                pre.add(cont);
                m.instructions.insert(pre);
                hits++;
            }
        }
        if (hits == 0) {
            return basicClass;
        }
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        LOG.info("MusicTicker MENU handed to SplashMusic clip (" + hits + " edits)");
        return writer.toByteArray();
    }

    private byte[] patchType(byte[] basicClass) {
        ClassNode node = new ClassNode();
        new ClassReader(basicClass).accept(node, 0);
        boolean sawMenu = false;
        int hits = 0;
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if (!"<clinit>".equals(m.name)) {
                continue;
            }
            for (AbstractInsnNode insn = m.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                if (insn instanceof LdcInsnNode && "minecraft:music.menu".equals(((LdcInsnNode) insn).cst)) {
                    sawMenu = true;
                }
                if (!sawMenu || !(insn instanceof IntInsnNode)) {
                    continue;
                }
                IntInsnNode ii = (IntInsnNode) insn;
                if (insn.getOpcode() == Opcodes.BIPUSH && ii.operand == 20) {
                    ii.operand = 0;
                    hits++;
                } else if (insn.getOpcode() == Opcodes.SIPUSH && ii.operand == 600) {
                    ii.operand = 0;
                    hits++;
                    sawMenu = false;
                }
            }
        }
        if (hits == 0) {
            return basicClass;
        }
        ClassWriter writer = new ClassWriter(0);
        node.accept(writer);
        LOG.info("MusicType.MENU delay 20-600 -> 0-0");
        return writer.toByteArray();
    }

    private byte[] patchMenuTickHandler(byte[] basicClass) {
        ClassNode node = new ClassNode();
        new ClassReader(basicClass).accept(node, 0);
        int hits = 0;
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if (!"test".equals(m.name) || alreadyGuiHooked(m)) {
                continue;
            }
            InsnList pre = new InsnList();
            pre.add(new org.objectweb.asm.tree.VarInsnNode(Opcodes.ALOAD, 1));
            pre.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "qf/splash/SplashMusic", "onGuiOpenEvent", "(Ljava/lang/Object;)V", false));
            m.instructions.insert(pre);
            hits++;
        }
        if (hits == 0) {
            return basicClass;
        }
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        LOG.info("MainMenuTickHandler.test -> SplashMusic.onGuiOpenEvent");
        return writer.toByteArray();
    }

    private static boolean alreadyGuiHooked(MethodNode m) {
        AbstractInsnNode insn = m.instructions.getFirst();
        while (insn != null && insn.getOpcode() < 0) {
            insn = insn.getNext();
        }
        if (insn instanceof MethodInsnNode) {
            MethodInsnNode mi = (MethodInsnNode) insn;
            return "onGuiOpenEvent".equals(mi.name);
        }
        return false;
    }

    private static boolean alreadyHooked(MethodNode m) {
        AbstractInsnNode insn = m.instructions.getFirst();
        while (insn != null && insn.getOpcode() < 0) {
            insn = insn.getNext();
        }
        if (insn instanceof MethodInsnNode) {
            MethodInsnNode mi = (MethodInsnNode) insn;
            return "onMusicTick".equals(mi.name) && "qf/splash/SplashMusic".equals(mi.owner);
        }
        return false;
    }
}
