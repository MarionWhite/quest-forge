package com.questforge;

import net.minecraft.launchwrapper.IClassTransformer;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * -Dqf.silent=true: the splash chant and the title-menu music stay silent.
 *
 * Agent-launched test clients (tools/trial/trial.py) run in the background while
 * the owner works or plays, and must make no sound. The game's own sounds obey
 * options.txt (trial.py sets every soundCategory to 0), but qf/splash/SplashMusic
 * plays its two wavs through Java Sound, outside the game's volume settings.
 *
 * With the property set, SplashMusic.openClip(String rel, float gain) gets
 * {@code rel = "qf-silent/none.wav"} at its head, a path no game dir or jar has,
 * so every clip it opens is null and it plays nothing (it logs one
 * "SplashMusic FAILED: open" line). Two instructions, no branch, so no stack map
 * frame changes. Without the property this transformer returns every class
 * untouched: players never set it.
 */
public class SilentTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");
    static final boolean SILENT = Boolean.getBoolean("qf.silent");

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (!SILENT || basicClass == null || !"qf.splash.SplashMusic".equals(transformedName)) {
            return basicClass;
        }
        try {
            ClassNode node = new ClassNode();
            new ClassReader(basicClass).accept(node, 0);
            for (Object o : node.methods) {
                MethodNode m = (MethodNode) o;
                if (m.name.equals("openClip") && m.desc.startsWith("(Ljava/lang/String;")
                        && (m.access & Opcodes.ACC_STATIC) != 0) {
                    InsnList head = new InsnList();
                    head.add(new LdcInsnNode("qf-silent/none.wav"));
                    head.add(new VarInsnNode(Opcodes.ASTORE, 0));
                    m.instructions.insert(head);
                    m.maxStack = Math.max(m.maxStack, 1);
                    ClassWriter w = new ClassWriter(0);
                    node.accept(w);
                    LOG.info("[QuestForgeTweaks] Transform applied: qf.splash.SplashMusic: silent (-Dqf.silent)");
                    return w.toByteArray();
                }
            }
            LOG.warn("[QuestForgeTweaks] -Dqf.silent: SplashMusic has no openClip(String, ...); left as is");
        } catch (Throwable t) {
            LOG.warn("[QuestForgeTweaks] -Dqf.silent: SplashMusic transform failed; left as is", t);
        }
        return basicClass;
    }
}
