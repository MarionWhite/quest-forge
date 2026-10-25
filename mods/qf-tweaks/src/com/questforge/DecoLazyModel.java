package com.questforge;

import java.awt.image.BufferedImage;
import java.awt.image.DataBuffer;
import java.io.ByteArrayInputStream;
import java.util.Arrays;
import java.util.Collection;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import com.mia.craftstudio.CSModel;
import com.mia.craftstudio.CraftStudioLib;
import com.mia.craftstudio.libgdx.Matrix4;
import com.mia.craftstudio.libgdx.Quaternion;
import com.mia.craftstudio.libgdx.Vector3;
import com.mia.craftstudio.minecraft.CraftStudioModelWrapper;
import com.mia.craftstudio.minecraft.CraftStudioModelWrapper.NodeWrapper;
import com.mia.craftstudio.minecraft.ModelMetadata;
import com.mia.craftstudio.minecraft.ProjectionHelper;
import com.mia.craftstudio.utils.ImageIOCS;
import com.mia.props.Props;

import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.LoaderState;
import cpw.mods.fml.relauncher.FMLLaunchHandler;

/**
 * Runtime half of DecoLazyTransformer: called from the patched Decocraft code.
 * Compiled against Decocraft.jar; loaded only when Decocraft's patched classes
 * run, so a pack without Decocraft never resolves it.
 *
 * Threading. In singleplayer the client thread (rendering: getVertices(0) from
 * the VBO builder) and the server thread (collision: getExtend(rotation)) share
 * the same wrappers. A rotation is rebuilt under the wrapper's monitor into
 * fresh arrays, and only then published by setting that rotation's bit in the
 * node's volatile qf$state, so a reader that sees the bit sees complete arrays;
 * a reader that does not takes the monitor and finds the work done. The fast
 * path is one volatile read (a plain load on x86) and an array read.
 */
public final class DecoLazyModel {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    /** -Dqf.decolazy.verify=true: recompute every rotation at startup and compare. */
    static final boolean VERIFY = Boolean.getBoolean("qf.decolazy.verify");

    /** qf$state bit 16: the arrays built by the constructor were released. */
    static final int RELEASED = 1 << 16;

    private static int wrappers, nodeWrappers, verifyNodes, verifyMismatches;
    private static long verifyNanos;
    private static int rebuilds;
    private static boolean warnedGetters, warnedTexture;

    private DecoLazyModel() {
    }

    // ------------------------------------------------------------ vertices

    /** In place of NodeWrapper.getVertices(int). */
    public static Vector3[] vertices(NodeWrapper nw, int orient) {
        int s = nw.qf$state;
        if (s == 0 || (s & (1 << orient)) != 0) {
            return nw.vertices[orient];
        }
        rebuild(nw.modelWrapper, orient);
        return nw.vertices[orient];
    }

    /** In place of NodeWrapper.getExtend(int). */
    public static Vector3[] extend(NodeWrapper nw, int orient) {
        int s = nw.qf$state;
        if (s == 0 || (s & (1 << orient)) != 0) {
            return nw.extend[orient];
        }
        rebuild(nw.modelWrapper, orient);
        return nw.extend[orient];
    }

    /**
     * End of CraftStudioModelWrapper's constructor: the wrapper's extents are
     * derived, so the per-node arrays behind them can go.
     */
    public static void built(CraftStudioModelWrapper w) {
        if (!DecoLazyTransformer.nodeGettersPatched) {
            if (!warnedGetters) {
                warnedGetters = true;
                LOG.warn("[QuestForgeTweaks] Decocraft lazy models: NodeWrapper's getters were not patched; "
                        + "keeping every per-node vertex array (no memory saved there).");
            }
            return;
        }
        if (VERIFY) {
            verify(w);
        }
        Collection<NodeWrapper> nodes = w.nodeCache.values();
        for (NodeWrapper nw : nodes) {
            Arrays.fill(nw.vertices, null);
            Arrays.fill(nw.extend, null);
            nw.qf$state = RELEASED;
        }
        wrappers++;
        nodeWrappers += nodes.size();
    }

    private static void rebuild(CraftStudioModelWrapper w, final int orient) {
        synchronized (w) {
            NodeWrapper any = null;
            for (NodeWrapper nw : w.nodeCache.values()) {
                any = nw;
                break;
            }
            if (any == null || (any.qf$state & (1 << orient)) != 0) {
                return;     // another thread got here first
            }
            ModelMetadata md = w.metadata;
            Matrix4 top = topMatrix(md.scale, orient);
            for (CSModel.ModelNode node : md.csmodel.getTopNodes()) {
                computeNode(w, node, top, orient, new Sink() {
                    @Override
                    public void put(NodeWrapper nw, Vector3[] v, Vector3[] ext) {
                        nw.vertices[orient] = v;
                        nw.extend[orient] = ext;
                    }
                });
            }
            // Publish: the volatile write orders the array stores above before it.
            for (NodeWrapper nw : w.nodeCache.values()) {
                nw.qf$state = nw.qf$state | (1 << orient);
            }
            int n = ++rebuilds;
            if (n <= 3) {
                LOG.info("[QuestForgeTweaks] Decocraft lazy models: rebuilt rotation {} of '{}' on first use ({})",
                        orient, md.craftstudioAssetName, n == 3 ? "further rebuilds are not logged" : "rebuild " + n);
            }
        }
    }

    /** The per-rotation model matrix, exactly as CraftStudioModelWrapper.computeExtend builds it. */
    private static Matrix4 topMatrix(float scale, int orient) {
        Matrix4 i = new Matrix4();
        Matrix4 centerBlock = new Matrix4();
        centerBlock.translate(0.5F, 0.0F, 0.5F);
        i.mul(centerBlock);
        Matrix4 scaleModel = new Matrix4();
        scaleModel.setToScaling(scale, scale, scale);
        i.mul(scaleModel);
        Matrix4 invertAxe = new Matrix4();
        invertAxe.rotate(new Vector3(0.0F, 0.0F, 1.0F), 180.0F);
        i.mul(invertAxe);
        Matrix4 rotation = new Matrix4();
        rotation.rotate(new Vector3(0.0F, 1.0F, 0.0F), (float) orient * 360.0F / 16.0F);
        i.mul(rotation);
        return i;
    }

    private interface Sink {
        void put(NodeWrapper nw, Vector3[] vertices, Vector3[] extend);
    }

    /** One node and its children, exactly as NodeWrapper.computeVertices does it, into fresh arrays. */
    private static void computeNode(CraftStudioModelWrapper w, CSModel.ModelNode node, Matrix4 matrix, int orient, Sink out) {
        NodeWrapper nw = w.nodeCache.get(node);
        Matrix4 pushed = matrix.cpy();
        float[] scaledSize = node.getSize(0.0625F);
        Matrix4 position = new Matrix4();
        position.setTranslation(node.getPosition()[0], -node.getPosition()[1], -node.getPosition()[2]);
        pushed.mul(position);
        Quaternion quat = node.getOrientation();
        quat.y *= -1.0F;
        quat.z *= -1.0F;
        pushed.mul(new Matrix4(quat));
        Matrix4 offset = new Matrix4();
        offset.setTranslation(node.getOffset()[0], node.getOffset()[1] * -1.0F, node.getOffset()[2] * -1.0F);
        pushed.mul(offset);
        Matrix4 mWorldScaling = pushed.cpy();
        Matrix4 scaling = new Matrix4();
        scaling.setToScaling(Math.abs(node.getScale()[0]), Math.abs(node.getScale()[1]), Math.abs(node.getScale()[2]));
        mWorldScaling.mul(scaling);
        Vector3[] v = new Vector3[8];
        v[0] = (new Vector3(-scaledSize[0] / 2.0F, -scaledSize[1] / 2.0F, -scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[1] = (new Vector3(-scaledSize[0] / 2.0F, -scaledSize[1] / 2.0F, scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[2] = (new Vector3(-scaledSize[0] / 2.0F, scaledSize[1] / 2.0F, -scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[3] = (new Vector3(-scaledSize[0] / 2.0F, scaledSize[1] / 2.0F, scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[4] = (new Vector3(scaledSize[0] / 2.0F, -scaledSize[1] / 2.0F, -scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[5] = (new Vector3(scaledSize[0] / 2.0F, -scaledSize[1] / 2.0F, scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[6] = (new Vector3(scaledSize[0] / 2.0F, scaledSize[1] / 2.0F, -scaledSize[2] / 2.0F)).mul(mWorldScaling);
        v[7] = (new Vector3(scaledSize[0] / 2.0F, scaledSize[1] / 2.0F, scaledSize[2] / 2.0F)).mul(mWorldScaling);
        out.put(nw, v, ProjectionHelper.getExtend(v));
        for (CSModel.ModelNode child : node.getChildren()) {
            computeNode(w, child, pushed, orient, out);
        }
    }

    /** -Dqf.decolazy.verify: our rebuild against Decocraft's arrays, every rotation, bit for bit. */
    private static void verify(CraftStudioModelWrapper w) {
        long t0 = System.nanoTime();
        final int[] bad = new int[1];
        final int[] seen = new int[1];
        for (int orient = 0; orient < 16; orient++) {
            final int o = orient;
            Matrix4 top = topMatrix(w.metadata.scale, orient);
            for (CSModel.ModelNode node : w.metadata.csmodel.getTopNodes()) {
                computeNode(w, node, top, orient, new Sink() {
                    @Override
                    public void put(NodeWrapper nw, Vector3[] v, Vector3[] ext) {
                        seen[0]++;
                        if (!same(v, nw.vertices[o]) || !same(ext, nw.extend[o])) {
                            bad[0]++;
                        }
                    }
                });
            }
        }
        verifyNanos += System.nanoTime() - t0;
        verifyNodes += seen[0];
        verifyMismatches += bad[0];
        if (bad[0] != 0) {
            LOG.warn("[QuestForgeTweaks] Decocraft lazy models VERIFY: '{}' {} of {} node-rotations differ from Decocraft's",
                    w.metadata.craftstudioAssetName, bad[0], seen[0]);
        }
    }

    private static boolean same(Vector3[] a, Vector3[] b) {
        if (a == null || b == null || a.length != b.length) return false;
        for (int i = 0; i < a.length; i++) {
            if (a[i] == null || b[i] == null) return false;
            if (Float.floatToIntBits(a[i].x) != Float.floatToIntBits(b[i].x)
                    || Float.floatToIntBits(a[i].y) != Float.floatToIntBits(b[i].y)
                    || Float.floatToIntBits(a[i].z) != Float.floatToIntBits(b[i].z)) {
                return false;
            }
        }
        return true;
    }

    // ------------------------------------------------------------- textures

    private static CSModel lastModel;
    private static BufferedImage lastImage;
    private static int decodes;

    /** In place of CSModel.getTexture(). */
    public static BufferedImage texture(CSModel m) {
        BufferedImage t = m.texture;
        if (t != null) {
            return t;
        }
        synchronized (DecoLazyModel.class) {
            // ImageIOCS shares one PNGImageReader, so decodes are serialised; the
            // one-entry cache covers a caller that asks for the same model's
            // texture several times in a row (wrapperCallback asks five times).
            if (m == lastModel && lastImage != null) {
                return lastImage;
            }
            BufferedImage img = null;
            try {
                img = ImageIOCS.read(new ByteArrayInputStream(m.texture_data));
            } catch (Throwable e) {
                LOG.warn("[QuestForgeTweaks] Decocraft lazy models: could not decode a prop texture; using the default", e);
            }
            if (img == null) {
                img = CraftStudioLib.getDefaultTexture();
            }
            lastModel = m;
            lastImage = img;
            decodes++;
            return img;
        }
    }

    /** End of Props.loadModels(): both sides. */
    public static void afterLoadModels() {
        LOG.info("[QuestForgeTweaks] Decocraft lazy models: released the per-node vertex arrays of {} model wrappers "
                + "({} node wrappers, about {} Vector3 objects, ~{} MB); a rotation is rebuilt the first time a prop "
                + "with it is drawn or collided with.", wrappers, nodeWrappers, nodeWrappers * 160L,
                nodeWrappers * 160L * 24L >> 20);
        if (VERIFY) {
            LOG.info("[QuestForgeTweaks] Decocraft lazy models VERIFY: {} node-rotations recomputed in {} ms, {} mismatches",
                    verifyNodes, verifyNanos / 1000000L, verifyMismatches);
        }
        if (!DecoLazyTransformer.texturePatched) {
            warnTextureUnpatched();
            return;
        }
        if (FMLLaunchHandler.side().isServer()) {
            releaseTextures("loadModels (dedicated server)");
        } else {
            LOG.info("[QuestForgeTweaks] Decocraft lazy models: decoded textures stay until the resource reload that "
                    + "follows mod loading (they are uploaded to the GPU twice during startup).");
        }
    }

    /** End of the resource-reload listener (client). */
    public static void afterReload() {
        if (!DecoLazyTransformer.texturePatched) {
            warnTextureUnpatched();
            return;
        }
        if (Loader.instance().hasReachedState(LoaderState.AVAILABLE)) {
            releaseTextures("resource reload");
        } else {
            LOG.info("[QuestForgeTweaks] Decocraft lazy models: startup resource reload; textures kept for the next one.");
        }
    }

    private static void warnTextureUnpatched() {
        if (!warnedTexture) {
            warnedTexture = true;
            LOG.warn("[QuestForgeTweaks] Decocraft lazy models: CSModel.getTexture() was not patched; "
                    + "keeping every decoded prop texture (no memory saved there).");
        }
    }

    private static void releaseTextures(String why) {
        int n = 0;
        long bytes = 0;
        Collection<CSModel> models = models();
        for (CSModel m : models) {
            BufferedImage t = m.texture;
            if (t != null) {
                bytes += rasterBytes(t);
                m.texture = null;
                n++;
            }
        }
        synchronized (DecoLazyModel.class) {
            lastModel = null;
            lastImage = null;
        }
        LOG.info("[QuestForgeTweaks] Decocraft lazy models: released {} decoded prop textures (~{} MB) after {}; "
                + "{} decoded on demand so far. They are decoded again from the models' PNG bytes when needed.",
                n, bytes >> 20, why, decodes);
    }

    private static Collection<CSModel> models() {
        Map<Integer, CSModel> all = Props.csproject.getModels();
        return all.values();
    }

    private static long rasterBytes(BufferedImage img) {
        try {
            DataBuffer db = img.getRaster().getDataBuffer();
            return (long) db.getSize() * (DataBuffer.getDataTypeSize(db.getDataType()) / 8);
        } catch (Throwable t) {
            return (long) img.getWidth() * img.getHeight() * 4;
        }
    }
}
