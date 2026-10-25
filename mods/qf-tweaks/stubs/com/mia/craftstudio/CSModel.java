package com.mia.craftstudio;

import java.awt.image.BufferedImage;
import java.util.Collection;
import java.util.Set;

import com.mia.craftstudio.libgdx.Quaternion;

/**
 * COMPILE-TIME STUB, never shipped. Decocraft's CSModel as DecoLazyTransformer
 * leaves it: the two texture fields public. Only the members DecoLazyModel uses
 * are declared; build.bat compiles this ahead of Decocraft.jar on the
 * classpath so the helper can be plain Java with direct field access, and the
 * bytecode it produces resolves against the real, transformed class at runtime.
 * Keep it in step with the transformer's `publish` calls.
 */
public class CSModel {

    public final byte[] texture_data = null;
    public BufferedImage texture;

    public Collection<ModelNode> getTopNodes() {
        throw new AssertionError("stub");
    }

    public static class ModelNode {

        public float[] getSize(float scale) {
            throw new AssertionError("stub");
        }

        public float[] getPosition() {
            throw new AssertionError("stub");
        }

        public Quaternion getOrientation() {
            throw new AssertionError("stub");
        }

        public float[] getOffset() {
            throw new AssertionError("stub");
        }

        public float[] getScale() {
            throw new AssertionError("stub");
        }

        public Set<ModelNode> getChildren() {
            throw new AssertionError("stub");
        }
    }
}
