import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.io.*;
import java.util.*;
import java.util.zip.*;

/**
 * Null-guard CodeChickenLib's WorldExtension chunk accessors.
 *
 * WorldExtension keeps chunkMap: Chunk -> ChunkExtension. On a dedicated
 * server, WorldExtensionManager removes an entry in onChunkDataSave whenever
 * the saved chunk is unmodified, but onChunkUnLoad then calls
 * chunkMap.get(chunk).unload() with no null check. Mass pregeneration saves
 * and then unloads chunks constantly, so it dereferences null and takes the
 * server down.
 *
 * unwatchChunk already guards with ifnull. This applies the author's own
 * idiom to the six accessors that do not. It only skips bookkeeping for a
 * chunk the map has already forgotten; it cannot affect worldgen.
 */
public class PatchCCL {
    static final String OWNER = "codechicken/lib/world/WorldExtension";
    static final String EXT = "codechicken/lib/world/ChunkExtension";

    // method name -> {descriptor, ChunkExtension method, its descriptor}
    static final String[][] TARGETS = {
        {"loadChunk",        "(Lnet/minecraft/world/chunk/Chunk;)V", "load", "()V", ""},
        {"unloadChunk",      "(Lnet/minecraft/world/chunk/Chunk;)V", "unload", "()V", ""},
        {"sendChunkUpdates", "(Lnet/minecraft/world/chunk/Chunk;)V", "sendUpdatePackets", "()V", ""},
        {"loadChunkData",    "(Lnet/minecraft/world/chunk/Chunk;Lnet/minecraft/nbt/NBTTagCompound;)V", "loadData", "(Lnet/minecraft/nbt/NBTTagCompound;)V", "L"},
        {"saveChunkData",    "(Lnet/minecraft/world/chunk/Chunk;Lnet/minecraft/nbt/NBTTagCompound;)V", "saveData", "(Lnet/minecraft/nbt/NBTTagCompound;)V", "L"},
        {"watchChunk",       "(Lnet/minecraft/world/chunk/Chunk;Lnet/minecraft/entity/player/EntityPlayerMP;)V", "watchPlayer", "(Lnet/minecraft/entity/player/EntityPlayerMP;)V", "L"},
    };

    public static void main(String[] a) throws Exception {
        File in = new File(a[0]), out = new File(a[1]);
        ZipFile zf = new ZipFile(in);
        ZipOutputStream zo = new ZipOutputStream(new FileOutputStream(out));
        int patched = 0;
        Enumeration<? extends ZipEntry> en = zf.entries();
        while (en.hasMoreElements()) {
            ZipEntry e = en.nextElement();
            byte[] data = read(zf.getInputStream(e));
            if (e.getName().equals(OWNER + ".class")) {
                data = patch(data);
                patched++;
            }
            ZipEntry ne = new ZipEntry(e.getName());
            ne.setTime(e.getTime());
            zo.putNextEntry(ne);
            zo.write(data);
            zo.closeEntry();
        }
        zo.close(); zf.close();
        System.out.println("patched " + patched + " class(es) -> " + out);
        if (patched != 1) { System.out.println("EXPECTED EXACTLY 1"); System.exit(2); }
    }

    static byte[] read(InputStream is) throws IOException {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        byte[] buf = new byte[8192]; int n;
        while ((n = is.read(buf)) > 0) b.write(buf, 0, n);
        is.close(); return b.toByteArray();
    }

    static byte[] patch(byte[] data) {
        ClassNode cn = new ClassNode();
        new ClassReader(data).accept(cn, 0);
        for (String[] t : TARGETS) {
            MethodNode m = find(cn, t[0], t[1]);
            if (m == null) { System.out.println("  MISSING " + t[0]); System.exit(3); }
            boolean guarded = false;
            for (AbstractInsnNode i = m.instructions.getFirst(); i != null; i = i.getNext())
                if (i.getOpcode() == Opcodes.IFNULL) guarded = true;
            if (guarded) { System.out.println("  skip (already guarded) " + t[0]); continue; }

            int extSlot = ("".equals(t[4])) ? 2 : 3;   // after this + args
            InsnList body = new InsnList();
            LabelNode end = new LabelNode();
            body.add(new VarInsnNode(Opcodes.ALOAD, 0));
            body.add(new FieldInsnNode(Opcodes.GETFIELD, OWNER, "chunkMap", "Ljava/util/HashMap;"));
            body.add(new VarInsnNode(Opcodes.ALOAD, 1));
            body.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, "java/util/HashMap", "get",
                    "(Ljava/lang/Object;)Ljava/lang/Object;", false));
            body.add(new TypeInsnNode(Opcodes.CHECKCAST, EXT));
            body.add(new VarInsnNode(Opcodes.ASTORE, extSlot));
            body.add(new VarInsnNode(Opcodes.ALOAD, extSlot));
            body.add(new JumpInsnNode(Opcodes.IFNULL, end));
            body.add(new VarInsnNode(Opcodes.ALOAD, extSlot));
            if (!"".equals(t[4])) body.add(new VarInsnNode(Opcodes.ALOAD, 2));
            body.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, EXT, t[2], t[3], false));
            body.add(end);
            body.add(new InsnNode(Opcodes.RETURN));

            m.instructions.clear();
            m.tryCatchBlocks.clear();
            if (m.localVariables != null) m.localVariables.clear();
            m.instructions.add(body);
            m.maxStack = 3;
            m.maxLocals = extSlot + 1;
            System.out.println("  guarded " + t[0]);
        }
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS) {
            protected String getCommonSuperClass(String a, String b) { return "java/lang/Object"; }
        };
        cn.accept(cw);
        return cw.toByteArray();
    }

    static MethodNode find(ClassNode cn, String name, String desc) {
        for (Object o : cn.methods) {
            MethodNode m = (MethodNode) o;
            if (m.name.equals(name) && m.desc.equals(desc)) return m;
        }
        return null;
    }
}
