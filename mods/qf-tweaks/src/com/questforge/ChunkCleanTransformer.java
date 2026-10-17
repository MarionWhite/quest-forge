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
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.TypeInsnNode;

/**
 * Stops ChickenChunks crashing the server tick when a player moves far at once.
 *
 * ChunkLoaderManager.cleanChunks walks ChunkProviderServer.loadedChunks -- the
 * live list -- and, for each chunk no player is near any more, removes the
 * players still watching it. Removing a watcher posts Forge's ChunkWatchEvent,
 * and anything that loads a chunk in response adds to the list being walked:
 * ConcurrentModificationException in the server tick loop, which ends the
 * session for everyone.
 *
 * HOW SURE WE ARE. The one crash observed (2026-10-16) came from a benchmark
 * that teleported the player from the client thread -- a cross-thread write
 * into the integrated server, which the harness has since stopped doing. That
 * alone explains it, so a real server may never hit this. The patch is kept
 * because the loop stays unsafe against any ChunkWatchEvent handler that loads
 * a chunk, and walking a copy costs nothing.
 *
 * The patch walks a copy instead: `new ArrayList(loadedChunks).iterator()`. A
 * chunk loaded during the pass is simply considered on the next one. Inserted
 * between the GETFIELD and the iterator() call; no branches, so the existing
 * stack map frames stay valid and only max stack grows.
 *
 * Server side, so QuestForgeTweaks must be on the server (it already is).
 */
public class ChunkCleanTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String TARGET = "codechicken.chunkloader.ChunkLoaderManager";
    private static final String PROVIDER = "net/minecraft/world/gen/ChunkProviderServer";
    /** ChunkProviderServer.loadedChunks, by its SRG name: mods are shipped SRG-named. */
    private static final String LOADED = "field_73245_g";

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
                if (!"cleanChunks".equals(m.name)) continue;
                for (AbstractInsnNode insn : m.instructions.toArray()) {
                    if (insn.getOpcode() != Opcodes.GETFIELD) continue;
                    FieldInsnNode f = (FieldInsnNode) insn;
                    if (!PROVIDER.equals(f.owner) || !LOADED.equals(f.name)) continue;
                    AbstractInsnNode next = f.getNext();
                    if (!(next instanceof MethodInsnNode) || !"iterator".equals(((MethodInsnNode) next).name)) {
                        continue;
                    }
                    InsnList copy = new InsnList();
                    copy.add(new TypeInsnNode(Opcodes.NEW, "java/util/ArrayList"));
                    copy.add(new InsnNode(Opcodes.DUP_X1));
                    copy.add(new InsnNode(Opcodes.SWAP));
                    copy.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, "java/util/ArrayList", "<init>",
                            "(Ljava/util/Collection;)V", false));
                    m.instructions.insert(f, copy);
                    m.maxStack += 2;
                    patched++;
                }
            }

            if (patched == 0) {
                LOG.warn("[QuestForgeTweaks] ChickenChunks cleanChunks loop not found in {} - leaving "
                        + "class untouched; a long teleport can still crash the server tick.", TARGET);
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: ChickenChunks cleanChunks walks a copy "
                    + "of the loaded-chunk list ({} site(s)).", patched);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Transform failed for " + TARGET + "; returning original bytes.", t);
            return basicClass;
        }
    }
}
