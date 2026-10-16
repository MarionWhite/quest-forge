package com.questforge;

import java.util.List;

import net.minecraft.launchwrapper.IClassTransformer;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.ClassNode;

/**
 * Stops GraveStones drawing its item beam while a shader pack is running.
 *
 * A grave that still holds items draws a 256-block column around itself from
 * TileEntitySpecialRendererGrave.renderBeam: GL_TEXTURE_2D off, no UVs, depth
 * writes off, additive blending at 11% alpha. Fixed-function GL turns that into
 * a faint glow. Sildur's Vibrant is deferred, and a G-buffer cannot blend, so
 * the same quads become an opaque column that samples whatever texture happens
 * to be bound at UV 0,0 -- a dark, noisy pillar that blacks out everything
 * behind the gravestone. Nothing about the beam can be drawn correctly in a
 * G-buffer, so with a pack on it is skipped; without one it is untouched.
 *
 * The patch is a guard at the head of renderBeam:
 *
 *     if (ShaderState.active()) return;
 *
 * renderBeam is private, void, and only ever called from renderTileEntityAt, so
 * returning early skips the beam and nothing else. Its GL state changes are all
 * inside the method, so skipping it also skips their restores.
 */
public class GraveBeamTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET =
            "net.subaraki.gravestone.client.renderer.TileEntitySpecialRendererGrave";

    private static final String METHOD = "renderBeam";
    private static final String METHOD_DESC =
            "(Lnet/subaraki/gravestone/tileentity/TileEntityGravestone;DDD)V";

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

            MethodNode beam = null;
            @SuppressWarnings("unchecked")
            List<MethodNode> methods = node.methods;
            for (MethodNode m : methods) {
                if (METHOD.equals(m.name) && METHOD_DESC.equals(m.desc)) {
                    beam = m;
                }
            }

            if (beam == null) {
                LOG.warn("[QuestForgeTweaks] No {}{} in {} - GraveStones may have changed. "
                        + "Leaving class untouched; grave beams will stay black under shaders.",
                        METHOD, METHOD_DESC, TARGET);
                return basicClass;
            }

            LabelNode draw = new LabelNode();
            InsnList guard = new InsnList();
            guard.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "com/questforge/ShaderState",
                    "active", "()Z", false));
            guard.add(new JumpInsnNode(Opcodes.IFEQ, draw));
            guard.add(new InsnNode(Opcodes.RETURN));
            guard.add(draw);
            beam.instructions.insert(guard);

            // The new jump target needs a stack map frame.
            ClassWriter writer = new SafeClassWriter(reader, ClassWriter.COMPUTE_FRAMES);
            node.accept(writer);
            byte[] result = writer.toByteArray();

            LOG.info("[QuestForgeTweaks] Transform applied: GraveStones renderBeam skips while a "
                    + "shader pack is active ({} -> {} bytes).", basicClass.length, result.length);

            return result;
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET
                    + "; returning original bytes. Grave beams will stay black under shaders.", t);
            return basicClass;
        }
    }

    /** See PanelButtonQuestTransformer.SafeClassWriter. */
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
