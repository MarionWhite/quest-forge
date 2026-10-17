package com.questforge;

/**
 * Called in place of ClassLoader.loadClass from LittleMaidMob's model scan; see
 * MmmScanTransformer.
 */
public final class MmmScanGuard {

    private MmmScanGuard() {
    }

    /**
     * Loads a class the way the scan did, but a class that cannot be loaded comes
     * back as Void.class -- which is not a model, so the scan's own type check
     * skips it -- instead of an Error that ends mod loading.
     */
    public static Class<?> load(ClassLoader loader, String name) {
        try {
            return loader.loadClass(name);
        } catch (Throwable t) {
            return Void.class;
        }
    }
}
