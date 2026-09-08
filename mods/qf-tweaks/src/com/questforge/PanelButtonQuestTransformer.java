package com.questforge;

import java.util.ArrayList;
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
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;

/**
 * Forces PanelButtonQuest's constructor to call setActive(true).
 *
 * Vanilla BetterQuesting 3.0.328 ends the constructor with:
 *
 *     this.setActive(QuestingAPI.getAPI(ApiReference.SETTINGS)
 *                        .canUserEdit(this.player) || !lock);
 *
 * so a LOCKED quest button is inactive. PanelButton.onMouseRelease only fires
 * a PEventButton when isActive() is true, so GuiQuestLines.onButtonPress never
 * runs and the GuiQuest detail screen never opens. The click is swallowed one
 * layer below the code that would render the description.
 *
 * We rewrite the argument at the call site rather than the expression that
 * produces it: immediately before the INVOKEVIRTUAL setActive(Z)V we insert
 *
 *     POP        ; discard whatever boolean was computed
 *     ICONST_1   ; push true
 *
 * The stack shape at the call is [..., this, boolean]; POP+ICONST_1 restores
 * it to [..., this, 1]. This is independent of how the boolean was computed,
 * so it survives recompiles and minor BetterQuesting updates far better than
 * matching an exact instruction pattern or hardcoded file offsets.
 *
 * Gating is NOT affected. Enforcement lives server-side:
 *   - QuestInstance.detect() re-tests isUnlocked(playerID) before any task
 *     progress is recorded.
 *   - NetQuestAction.claimQuest re-checks canClaim, which requires an existing
 *     completion record.
 *   - EventHandler.onLivingUpdate's polling loop skips quests failing
 *     isUnlocked.
 *
 * The change is also visually invisible by design: PanelButtonQuest calls
 * setTextures(btnTx, btnTx, btnTx) with the same texture for all three states,
 * already chosen from the locked preset, so an active locked button still
 * renders with its greyed frame.
 */
public class PanelButtonQuestTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET =
            "betterquesting.api2.client.gui.controls.PanelButtonQuest";

    private static final String SET_ACTIVE = "setActive";
    private static final String SET_ACTIVE_DESC = "(Z)V";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) {
            return null;
        }
        // Match only our one class; everything else passes through untouched.
        if (!TARGET.equals(transformedName)) {
            return basicClass;
        }

        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            MethodNode ctor = null;
            // ASM 5 ClassNode.methods is a raw List; cast so -source 1.7 javac accepts it.
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                if ("<init>".equals(m.name)) {
                    // PanelButtonQuest has a single constructor; if that ever
                    // changes, prefer the one that actually calls setActive.
                    if (ctor == null || containsSetActive(m)) {
                        ctor = m;
                    }
                }
            }

            if (ctor == null) {
                LOG.warn("[QuestForgeTweaks] No <init> found in {} - leaving class untouched.", TARGET);
                return basicClass;
            }

            List<MethodInsnNode> calls = new ArrayList<MethodInsnNode>();
            for (AbstractInsnNode insn : ctor.instructions.toArray()) {
                if (insn.getOpcode() == Opcodes.INVOKEVIRTUAL) {
                    MethodInsnNode min = (MethodInsnNode) insn;
                    if (SET_ACTIVE.equals(min.name) && SET_ACTIVE_DESC.equals(min.desc)) {
                        calls.add(min);
                    }
                }
            }

            if (calls.isEmpty()) {
                LOG.warn("[QuestForgeTweaks] Expected pattern not found: no setActive(Z)V call in "
                        + "{}.<init>. BetterQuesting may have changed. Leaving class untouched; "
                        + "locked quests will stay unreadable.", TARGET);
                return basicClass;
            }
            if (calls.size() > 1) {
                LOG.warn("[QuestForgeTweaks] Found {} setActive(Z)V calls in <init>; patching the "
                        + "last one only (the vanilla 3.0.328 constructor has exactly one).",
                        calls.size());
            }

            // The lock decision is the final statement of the constructor.
            MethodInsnNode target = calls.get(calls.size() - 1);

            InsnList patch = new InsnList();
            patch.add(new InsnNode(Opcodes.POP));
            patch.add(new InsnNode(Opcodes.ICONST_1));
            ctor.instructions.insertBefore(target, patch);

            ClassWriter writer = new SafeClassWriter(reader, ClassWriter.COMPUTE_FRAMES);
            node.accept(writer);
            byte[] result = writer.toByteArray();

            LOG.info("[QuestForgeTweaks] Transform applied: PanelButtonQuest.<init> now calls "
                    + "setActive(true); locked quests are readable ({} -> {} bytes).",
                    basicClass.length, result.length);

            return result;
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET
                    + "; returning original bytes. Locked quests will stay unreadable.", t);
            return basicClass;
        }
    }

    private static boolean containsSetActive(MethodNode m) {
        for (AbstractInsnNode insn : m.instructions.toArray()) {
            if (insn.getOpcode() == Opcodes.INVOKEVIRTUAL) {
                MethodInsnNode min = (MethodInsnNode) insn;
                if (SET_ACTIVE.equals(min.name) && SET_ACTIVE_DESC.equals(min.desc)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * COMPUTE_FRAMES makes ASM ask for common superclasses, which normally
     * loads classes through the transforming classloader - a classic source of
     * ClassNotFoundException and deadlocks during coremod startup. Fall back to
     * java/lang/Object instead of letting that escape.
     */
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
