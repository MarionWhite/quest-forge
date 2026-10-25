package com.mia.craftstudio.minecraft;

import java.util.HashMap;

import com.mia.craftstudio.CSModel;
import com.mia.craftstudio.libgdx.Vector3;

/**
 * COMPILE-TIME STUB, never shipped. Decocraft's CraftStudioModelWrapper as
 * DecoLazyTransformer leaves it: metadata and the NodeWrapper fields public,
 * plus the qf$state field the transformer adds. See CSModel's stub for why.
 */
public class CraftStudioModelWrapper {

    public final ModelMetadata metadata = null;
    public final NodeHashCache nodeCache = null;

    public static class NodeHashCache extends HashMap<CSModel.ModelNode, NodeWrapper> {

        @Override
        public NodeWrapper get(Object key) {
            throw new AssertionError("stub");
        }
    }

    public static class NodeWrapper {

        public final CSModel.ModelNode node = null;
        public final CraftStudioModelWrapper modelWrapper = null;
        public Vector3[][] vertices;
        public Vector3[][] extend;
        /** Added by the transformer: 0 = as built; bit 16 = released; bits 0..15 = rotations rebuilt. */
        public volatile int qf$state;
    }
}
