package com.questforge;

import java.util.ArrayList;
import java.util.List;

import cpw.mods.fml.relauncher.FMLLaunchHandler;
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
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.TryCatchBlockNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * Makes Morph 0.9.3 work under OptiFine E7. Two separate bugs, both client-side.
 *
 * 1. Killing a new mob kicked the player ("critical exception handling a packet
 *    on channel Morph"). Morph forces a model to recompile by calling
 *    GLAllocation.deleteDisplayLists on its cubes' lists, which throws when the
 *    list is not in GLAllocation's map -- and under OptiFine it often is not.
 *    Every such call (ModelHelper twice, ModelMorph once) is redirected to
 *    MorphFix.deleteDisplayList, which has the same signature.
 *
 * 2. Morphing froze the game. Morph's RenderHandEvent handler cancels the event
 *    and calls EntityRenderer.renderHand itself to draw the mob's arm. OptiFine's
 *    renderHand posts RenderHandEvent, so the handler re-entered itself until a
 *    StackOverflowError -- caught and logged by OptiFine's Reflector, then
 *    repeated next frame, so the game sat at ~0 fps writing a thousand-line trace
 *    a frame and never produced a crash report. Captured with jstack, 2026-10-16.
 *    The handler is renamed and wrapped: a re-entrant call returns without
 *    cancelling, so the inner renderHand draws the hand with the renderer Morph
 *    swapped in. The flag is cleared in a finally, so an exception in Morph's
 *    code cannot leave hands switched off.
 *
 * An earlier fix (Sep 2026) hand-patched both into the Morph jar; that copy did
 * the guard without a finally and lived only in a work folder. This replaces it,
 * so the stock Morph-Beta-0.9.3.jar is the one to install.
 */
public class MorphOptifineTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String HELPER = "com/questforge/MorphFix";
    private static final String GLALLOC = "net/minecraft/client/renderer/GLAllocation";
    private static final String DELETE = "func_74523_b";

    private static final String EVENT_HANDLER = "morph.common.core.EventHandler";
    private static final String HAND_DESC = "(Lnet/minecraftforge/client/event/RenderHandEvent;)V";
    private static final String RENAMED = "qf$onRenderHand";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) {
            return null;
        }
        boolean model = "morph.client.model.ModelHelper".equals(transformedName)
                || "morph.client.model.ModelMorph".equals(transformedName);
        boolean handler = EVENT_HANDLER.equals(transformedName);
        if (!model && !handler) {
            return basicClass;
        }

        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            String done = model ? redirectDeletes(node) : guardRenderHand(node);
            if (done == null && handler && FMLLaunchHandler.side().isServer()) {
                // FML's @SideOnly stripper has already removed the client handler.
                return basicClass;
            }
            if (done == null) {
                LOG.warn("[QuestForgeTweaks] Morph patch site not found in {} - leaving class "
                        + "untouched; Morph may crash under OptiFine.", transformedName);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: {} {}", transformedName, done);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + transformedName
                    + "; returning original bytes.", t);
            return basicClass;
        }
    }

    /** Same descriptor, static to static: stack shape and frames are unchanged. */
    private static String redirectDeletes(ClassNode node) {
        int patched = 0;
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            for (AbstractInsnNode insn : m.instructions.toArray()) {
                if (insn.getOpcode() == Opcodes.INVOKESTATIC) {
                    MethodInsnNode call = (MethodInsnNode) insn;
                    if (GLALLOC.equals(call.owner) && DELETE.equals(call.name) && "(I)V".equals(call.desc)) {
                        call.owner = HELPER;
                        call.name = "deleteDisplayList";
                        patched++;
                    }
                }
            }
        }
        return patched == 0 ? null : "now deletes display lists safely (" + patched + " site(s)).";
    }

    /**
     * Renames onRenderHand and adds, under the original name and annotations:
     *
     *   if (!MorphFix.enterHand()) return;
     *   try { qf$onRenderHand(event); } finally { MorphFix.exitHand(); }
     */
    private static String guardRenderHand(ClassNode node) {
        MethodNode orig = null;
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if ("onRenderHand".equals(m.name) && HAND_DESC.equals(m.desc)) {
                orig = m;
            }
        }
        if (orig == null) {
            return null;
        }

        MethodNode wrap = new MethodNode(Opcodes.ACC_PUBLIC, "onRenderHand", HAND_DESC, null, null);
        // The @SubscribeEvent (and @SideOnly) move to the wrapper, so the event bus
        // registers it and not the renamed original.
        wrap.visibleAnnotations = orig.visibleAnnotations;
        wrap.invisibleAnnotations = orig.invisibleAnnotations;
        orig.visibleAnnotations = null;
        orig.invisibleAnnotations = null;
        orig.name = RENAMED;
        orig.access = (orig.access & ~(Opcodes.ACC_PRIVATE | Opcodes.ACC_PROTECTED)) | Opcodes.ACC_PUBLIC;

        LabelNode go = new LabelNode();
        LabelNode start = new LabelNode();
        LabelNode end = new LabelNode();
        LabelNode handler = new LabelNode();
        InsnList in = wrap.instructions;
        in.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "enterHand", "()Z", false));
        in.add(new JumpInsnNode(Opcodes.IFNE, go));
        in.add(new InsnNode(Opcodes.RETURN));
        in.add(go);
        in.add(new FrameNode(Opcodes.F_SAME, 0, null, 0, null));
        in.add(start);
        in.add(new VarInsnNode(Opcodes.ALOAD, 0));
        in.add(new VarInsnNode(Opcodes.ALOAD, 1));
        in.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, node.name, RENAMED, HAND_DESC, false));
        in.add(end);
        in.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "exitHand", "()V", false));
        in.add(new InsnNode(Opcodes.RETURN));
        in.add(handler);
        in.add(new FrameNode(Opcodes.F_SAME1, 0, null, 1, new Object[] {"java/lang/Throwable"}));
        in.add(new VarInsnNode(Opcodes.ASTORE, 2));
        in.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "exitHand", "()V", false));
        in.add(new VarInsnNode(Opcodes.ALOAD, 2));
        in.add(new InsnNode(Opcodes.ATHROW));
        wrap.tryCatchBlocks = new ArrayList<TryCatchBlockNode>();
        wrap.tryCatchBlocks.add(new TryCatchBlockNode(start, end, handler, null));
        wrap.maxStack = 2;
        wrap.maxLocals = 3;
        methods.add(wrap);
        return "now guards onRenderHand against re-entry.";
    }
}
