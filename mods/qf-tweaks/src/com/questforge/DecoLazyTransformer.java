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
import org.objectweb.asm.tree.FieldNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * Decocraft 2.4.2: keep a prop's model data only while it is needed.
 *
 * Decocraft (and the PTRModelLib it bundles) builds every one of its ~800
 * CraftStudio models at startup and keeps all of it for the life of the game:
 * measured 2026-10-16 at about 550 MB of live heap in a slim trial, 43% of the
 * whole pack's heap. Two things make up almost all of it:
 *
 *  1. Per-node vertex arrays. CraftStudioModelWrapper's constructor computes,
 *     for each of the 16 placement rotations, the 8 world-space corners of
 *     every node (NodeWrapper.vertices[16][8]) plus a per-node bounding box
 *     (NodeWrapper.extend[16][2]). That is 160 Vector3 objects per node, about
 *     50,000 node wrappers (one wrapper per prop *variant*, and variants share a
 *     model): 8.1 M Vector3s, about 250 MB with their arrays. After the
 *     constructor has derived the wrapper's own extents from them, they are read
 *     again only through getVertices(rot) -- the VBO builder, which uses rot 0
 *     the first time a prop is drawn -- and getExtend(rot) -- block collision,
 *     ray tracing and particle emitters, for the rotation a placed prop has.
 *  2. Decoded textures. CSModel decodes its embedded PNG into a BufferedImage
 *     (237 MB of byte[] across the 794 models in this jar) and keeps it,
 *     although after startup it is read only by the resource-reload listener,
 *     which re-uploads every texture to the GPU on each reload (two reloads at
 *     startup, then only F3+T or a resource-pack change).
 *
 * The patch frees both once startup has used them and rebuilds them on demand:
 *
 *   CraftStudioModelWrapper.<init>(ModelMetadata)
 *       after the final `metadata.wrapperCallback()` (just before RETURN):
 *       DecoLazyModel.built(this) -- nulls every node's per-rotation arrays and
 *       marks the node lazy (a volatile int the transformer adds).
 *   CraftStudioModelWrapper$NodeWrapper.getVertices(int) / getExtend(int)
 *       body `ALOAD 0; GETFIELD vertices|extend; ILOAD 1; AALOAD; ARETURN`
 *       becomes `ALOAD 0; ILOAD 1; INVOKESTATIC DecoLazyModel.vertices|extend;
 *       ARETURN`. The helper returns the array when it is present and otherwise
 *       recomputes that one rotation for the whole model (the same matrix chain
 *       as computeExtend/computeVertices, run once per rotation, under the
 *       wrapper's lock) and keeps it: a prop that is drawn or collided with
 *       costs 1/16 of what it did, a prop nobody places costs nothing.
 *   CSModel.getTexture()
 *       body `ALOAD 0; GETFIELD texture; ARETURN` becomes
 *       `ALOAD 0; INVOKESTATIC DecoLazyModel.texture; ARETURN`: the decoded
 *       image when it is still held, otherwise a fresh decode of the raw PNG
 *       bytes the model keeps anyway (10.7 MB for all of them).
 *   com.mia.props.events.ClientProxy$N (the IResourceManagerReloadListener)
 *       `onResourceManagerReload(IResourceManager)`: DecoLazyModel.afterReload()
 *       before RETURN. Once FML reports LoaderState.AVAILABLE -- i.e. after the
 *       second startup reload, so startup never decodes a texture twice -- it
 *       drops every decoded texture. A later F3+T decodes them again (a couple
 *       of seconds for 800 PNGs) and drops them again.
 *   com.mia.props.Props.loadModels()
 *       after `proxy.setupModelWrappers()`: DecoLazyModel.afterLoadModels() --
 *       logs what was released and, on a dedicated server (which never reloads
 *       resources), drops the decoded textures right there.
 *
 * Fields the helper reads are made public (CSModel.texture, texture_data;
 * NodeWrapper.vertices, extend, node, modelWrapper; CraftStudioModelWrapper
 * .metadata) and NodeWrapper gains `public volatile int qf$state` (0 = arrays
 * all present, as built; bit 16 = released; bits 0..15 = rotations rebuilt
 * since). Only straight-line code is inserted and the three rewritten bodies
 * have no branches, so the classes' stack map frames stay valid
 * (ClassWriter(0)). Nothing else in Decocraft changes: extents, placement
 * rules, item scales and resource costs are still computed by Decocraft's own
 * code at startup from the same data.
 *
 * Failing loudly: every site is matched by its exact bytecode shape above. A
 * Decocraft build that does not match logs one WARN line naming the site and
 * is left untouched; the helper then also refuses to free anything that the
 * missed site would still read (the getters guard the vertex release, the
 * getTexture patch guards the texture release), so a partial match degrades to
 * stock behaviour and never to a NullPointerException.
 *
 * Switching it off: config/qftweaks.cfg `decocraft.lazyModels=false`, or
 * -Dqf.decolazy=false on the command line (what trials use for A/B runs). With
 * it off no Decocraft class is touched. -Dqf.decolazy.verify=true makes the
 * helper recompute all 16 rotations of every wrapper at startup with its own
 * copy of the math and compare them bit for bit with Decocraft's before
 * releasing anything; the count of mismatches is logged (expected: 0).
 */
public class DecoLazyTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String HELPER = "com/questforge/DecoLazyModel";

    private static final String CSMODEL = "com.mia.craftstudio.CSModel";
    private static final String WRAPPER = "com.mia.craftstudio.minecraft.CraftStudioModelWrapper";
    private static final String NODE = WRAPPER + "$NodeWrapper";
    private static final String PROPS = "com.mia.props.Props";
    private static final String LISTENER_PREFIX = "com.mia.props.events.ClientProxy$";

    private static final String CSMODEL_I = "com/mia/craftstudio/CSModel";
    private static final String WRAPPER_I = "com/mia/craftstudio/minecraft/CraftStudioModelWrapper";
    private static final String NODE_I = WRAPPER_I + "$NodeWrapper";
    private static final String VEC3_ARR = "[Lcom/mia/craftstudio/libgdx/Vector3;";
    private static final String IMAGE = "Ljava/awt/image/BufferedImage;";
    private static final String METADATA_I = "com/mia/craftstudio/minecraft/ModelMetadata";
    private static final String PROXY_I = "com/mia/props/events/CommonProxy";
    private static final String RELOAD_LISTENER = "net/minecraft/client/resources/IResourceManagerReloadListener";
    private static final String RELOAD_DESC = "(Lnet/minecraft/client/resources/IResourceManager;)V";

    /** The state field added to NodeWrapper; see DecoLazyModel. */
    static final String STATE_FIELD = "qf$state";

    /**
     * Set when the matching site was patched. DecoLazyModel consults them before
     * freeing anything: no getter patch, no vertex release; no getTexture patch,
     * no texture release. NodeWrapper and CSModel load before the first wrapper
     * is finished and before loadModels returns, so they are settled in time.
     */
    static volatile boolean nodeGettersPatched;
    static volatile boolean texturePatched;

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null || transformedName == null) {
            return basicClass;
        }
        if (!transformedName.startsWith("com.mia.craftstudio.") && !transformedName.startsWith("com.mia.props.")) {
            return basicClass;
        }
        boolean csmodel = CSMODEL.equals(transformedName);
        boolean wrapper = WRAPPER.equals(transformedName);
        boolean nodeWrapper = NODE.equals(transformedName);
        boolean props = PROPS.equals(transformedName);
        boolean maybeListener = transformedName.startsWith(LISTENER_PREFIX);
        if (!csmodel && !wrapper && !nodeWrapper && !props && !maybeListener) {
            return basicClass;
        }
        if (!TweaksConfig.decocraftLazyModels()) {
            if (csmodel) {
                LOG.info("[QuestForgeTweaks] Decocraft lazy models are OFF (config/qftweaks.cfg or -Dqf.decolazy); "
                        + "Decocraft runs stock.");
            }
            return basicClass;
        }

        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            String done;
            if (csmodel) {
                done = patchModel(node);
            } else if (nodeWrapper) {
                done = patchNodeWrapper(node);
            } else if (wrapper) {
                done = patchWrapper(node);
            } else if (props) {
                done = patchProps(node);
            } else if (node.interfaces != null && node.interfaces.contains(RELOAD_LISTENER)) {
                done = patchReloadListener(node);
            } else {
                return basicClass;
            }
            if (done == null) {
                return basicClass;
            }

            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: {}: {}", transformedName, done);
            return writer.toByteArray();
        } catch (Throwable t) {
            // Never throw from a class transformer - it takes the game down.
            LOG.warn("[QuestForgeTweaks] Decocraft lazy-model transform failed for " + transformedName
                    + "; returning original bytes (Decocraft keeps its models the stock way).", t);
            return basicClass;
        }
    }

    // ----------------------------------------------------------------- CSModel

    private static String patchModel(ClassNode node) {
        MethodNode get = method(node, "getTexture", "()" + IMAGE);
        if (get == null || !isGetterBody(get, CSMODEL_I, "texture", IMAGE)) {
            return miss(CSMODEL, "getTexture() is not `return this.texture`", "decoded textures stay resident");
        }
        if (!publish(node, "texture", IMAGE) || !publish(node, "texture_data", "[B")) {
            return miss(CSMODEL, "fields texture / texture_data not found", "decoded textures stay resident");
        }
        InsnList body = new InsnList();
        body.add(new VarInsnNode(Opcodes.ALOAD, 0));
        body.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "texture",
                "(L" + CSMODEL_I + ";)" + IMAGE, false));
        body.add(new InsnNode(Opcodes.ARETURN));
        replaceBody(get, body, 1);
        texturePatched = true;
        return "getTexture() decodes the embedded PNG on demand once the decoded copy is released";
    }

    // ------------------------------------------------------------- NodeWrapper

    private static String patchNodeWrapper(ClassNode node) {
        MethodNode verts = method(node, "getVertices", "(I)" + VEC3_ARR);
        MethodNode ext = method(node, "getExtend", "(I)" + VEC3_ARR);
        if (verts == null || !isIndexedGetterBody(verts, NODE_I, "vertices", "[" + VEC3_ARR)) {
            return miss(NODE, "getVertices(int) is not `return this.vertices[i]`", "per-node vertex arrays stay resident");
        }
        if (ext == null || !isIndexedGetterBody(ext, NODE_I, "extend", "[" + VEC3_ARR)) {
            return miss(NODE, "getExtend(int) is not `return this.extend[i]`", "per-node vertex arrays stay resident");
        }
        if (!publish(node, "vertices", "[" + VEC3_ARR) || !publish(node, "extend", "[" + VEC3_ARR)
                || !publish(node, "node", "Lcom/mia/craftstudio/CSModel$ModelNode;")
                || !publish(node, "modelWrapper", "L" + WRAPPER_I + ";")) {
            return miss(NODE, "fields vertices / extend / node / modelWrapper not found", "per-node vertex arrays stay resident");
        }
        @SuppressWarnings("unchecked")
        List<FieldNode> fields = node.fields;
        fields.add(new FieldNode(Opcodes.ACC_PUBLIC | Opcodes.ACC_VOLATILE, STATE_FIELD, "I", null, null));

        replaceBody(verts, lazyGetter("vertices"), 2);
        replaceBody(ext, lazyGetter("extend"), 2);
        nodeGettersPatched = true;
        return "getVertices/getExtend rebuild a released rotation on first use";
    }

    private static InsnList lazyGetter(String helperMethod) {
        InsnList body = new InsnList();
        body.add(new VarInsnNode(Opcodes.ALOAD, 0));
        body.add(new VarInsnNode(Opcodes.ILOAD, 1));
        body.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, helperMethod,
                "(L" + NODE_I + ";I)" + VEC3_ARR, false));
        body.add(new InsnNode(Opcodes.ARETURN));
        return body;
    }

    // ------------------------------------------------ CraftStudioModelWrapper

    private static String patchWrapper(ClassNode node) {
        if (!publish(node, "metadata", "L" + METADATA_I + ";")) {
            return miss(WRAPPER, "field metadata not found", "per-node vertex arrays stay resident");
        }
        MethodNode init = method(node, "<init>", "(L" + METADATA_I + ";)V");
        int sites = 0;
        if (init != null) {
            for (AbstractInsnNode insn : init.instructions.toArray()) {
                if (insn.getOpcode() != Opcodes.INVOKEVIRTUAL) continue;
                MethodInsnNode call = (MethodInsnNode) insn;
                if (!METADATA_I.equals(call.owner) || !"wrapperCallback".equals(call.name) || !"()V".equals(call.desc)) {
                    continue;
                }
                if (nextReal(insn) == null || nextReal(insn).getOpcode() != Opcodes.RETURN) continue;
                InsnList hook = new InsnList();
                hook.add(new VarInsnNode(Opcodes.ALOAD, 0));
                hook.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "built", "(L" + WRAPPER_I + ";)V", false));
                init.instructions.insert(insn, hook);
                init.maxStack = Math.max(init.maxStack, 1);
                sites++;
            }
        }
        if (sites != 1) {
            return miss(WRAPPER, "<init> does not end in `metadata.wrapperCallback(); return` (" + sites + " matches)",
                    "per-node vertex arrays stay resident");
        }
        return "constructor releases the per-node vertex arrays once the extents are derived";
    }

    // ------------------------------------------------------------------ Props

    private static String patchProps(ClassNode node) {
        MethodNode load = method(node, "loadModels", "()V");
        int sites = 0;
        if (load != null) {
            for (AbstractInsnNode insn : load.instructions.toArray()) {
                if (insn.getOpcode() != Opcodes.INVOKEVIRTUAL) continue;
                MethodInsnNode call = (MethodInsnNode) insn;
                if (!PROXY_I.equals(call.owner) || !"setupModelWrappers".equals(call.name) || !"()V".equals(call.desc)) {
                    continue;
                }
                if (nextReal(insn) == null || nextReal(insn).getOpcode() != Opcodes.RETURN) continue;
                load.instructions.insert(insn, new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "afterLoadModels", "()V", false));
                sites++;
            }
        }
        if (sites != 1) {
            return miss(PROPS, "loadModels() does not end in `proxy.setupModelWrappers(); return` (" + sites + " matches)",
                    "a dedicated server keeps its decoded textures; the client still drops them after its reload");
        }
        return "loadModels() reports the release and drops server-side textures";
    }

    // ------------------------------------------------- the reload listener

    private static String patchReloadListener(ClassNode node) {
        MethodNode reload = null;
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if (RELOAD_DESC.equals(m.desc) && (m.access & Opcodes.ACC_STATIC) == 0 && !"<init>".equals(m.name)) {
                reload = m;
            }
        }
        if (reload == null) {
            return miss(node.name.replace('/', '.'), "no onResourceManagerReload(IResourceManager) method",
                    "decoded textures stay resident on the client");
        }
        int returns = 0;
        for (AbstractInsnNode insn : reload.instructions.toArray()) {
            if (insn.getOpcode() == Opcodes.RETURN) {
                reload.instructions.insertBefore(insn,
                        new MethodInsnNode(Opcodes.INVOKESTATIC, HELPER, "afterReload", "()V", false));
                returns++;
            }
        }
        if (returns == 0) {
            return miss(node.name.replace('/', '.'), "reload method has no RETURN", "decoded textures stay resident on the client");
        }
        return "resource reload drops the decoded textures once mod loading is complete (" + returns + " exit(s))";
    }

    // ---------------------------------------------------------------- helpers

    private static String miss(String where, String what, String consequence) {
        LOG.warn("[QuestForgeTweaks] Decocraft lazy models: {} in {}; leaving the class untouched ({}). "
                + "This Decocraft build differs from 2.4.2_1.7.10; the patch needs re-reading.", what, where, consequence);
        return null;
    }

    private static MethodNode method(ClassNode node, String name, String desc) {
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if (m.name.equals(name) && m.desc.equals(desc)) return m;
        }
        return null;
    }

    /** Makes a field public, whatever it was; false if the class has no such field. */
    private static boolean publish(ClassNode node, String name, String desc) {
        @SuppressWarnings("unchecked")
        List<FieldNode> fields = node.fields;
        for (FieldNode f : fields) {
            if (f.name.equals(name) && f.desc.equals(desc)) {
                f.access = (f.access & ~(Opcodes.ACC_PRIVATE | Opcodes.ACC_PROTECTED)) | Opcodes.ACC_PUBLIC;
                return true;
            }
        }
        return false;
    }

    /** `ALOAD 0; GETFIELD owner.name:desc; ARETURN`, ignoring labels, frames and line numbers. */
    private static boolean isGetterBody(MethodNode m, String owner, String field, String desc) {
        AbstractInsnNode[] r = realInsns(m);
        return r.length == 3
                && r[0].getOpcode() == Opcodes.ALOAD && ((VarInsnNode) r[0]).var == 0
                && isField(r[1], owner, field, desc)
                && r[2].getOpcode() == Opcodes.ARETURN;
    }

    /** `ALOAD 0; GETFIELD owner.name:desc; ILOAD 1; AALOAD; ARETURN`. */
    private static boolean isIndexedGetterBody(MethodNode m, String owner, String field, String desc) {
        AbstractInsnNode[] r = realInsns(m);
        return r.length == 5
                && r[0].getOpcode() == Opcodes.ALOAD && ((VarInsnNode) r[0]).var == 0
                && isField(r[1], owner, field, desc)
                && r[2].getOpcode() == Opcodes.ILOAD && ((VarInsnNode) r[2]).var == 1
                && r[3].getOpcode() == Opcodes.AALOAD
                && r[4].getOpcode() == Opcodes.ARETURN;
    }

    private static boolean isField(AbstractInsnNode insn, String owner, String name, String desc) {
        if (insn.getOpcode() != Opcodes.GETFIELD) return false;
        FieldInsnNode f = (FieldInsnNode) insn;
        return owner.equals(f.owner) && name.equals(f.name) && desc.equals(f.desc);
    }

    private static AbstractInsnNode[] realInsns(MethodNode m) {
        AbstractInsnNode[] all = m.instructions.toArray();
        int n = 0;
        for (AbstractInsnNode insn : all) {
            if (insn.getOpcode() >= 0) n++;
        }
        AbstractInsnNode[] real = new AbstractInsnNode[n];
        int i = 0;
        for (AbstractInsnNode insn : all) {
            if (insn.getOpcode() >= 0) real[i++] = insn;
        }
        return real;
    }

    private static AbstractInsnNode nextReal(AbstractInsnNode insn) {
        AbstractInsnNode n = insn.getNext();
        while (n != null && n.getOpcode() < 0) n = n.getNext();
        return n;
    }

    private static void replaceBody(MethodNode m, InsnList body, int maxStack) {
        m.instructions.clear();
        m.tryCatchBlocks.clear();
        if (m.localVariables != null) m.localVariables.clear();
        m.instructions.add(body);
        m.maxStack = Math.max(m.maxStack, maxStack);
    }
}
