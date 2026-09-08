package com.questforge.content.survey;

import net.minecraft.block.Block;
import net.minecraft.world.World;

/**
 * The landing point for {@link com.questforge.content.core.OreGenTransformer}.
 *
 * Called once for every ore vein the game places, anywhere, by any mod that uses
 * the standard vein generator. Kept trivial on purpose: this runs inside worldgen,
 * so it must cost almost nothing when no survey is in progress.
 */
public class OreGenHooks {

    /**
     * One vein of ore, as it is being placed.
     *
     * @param oreBlock the block being generated, passed as Object so the injected
     *                 call carries no obfuscated type in its descriptor
     * @param size     the vein's nominal block count
     * @param meta     the ore's metadata
     * @param x        the vein origin, in world coordinates
     * @param world    the world being generated, passed as Object for the same
     *                 reason as the ore; used only to read the biome
     */
    public static void vein(Object oreBlock, int size, int meta, int x, int y, int z,
                            Object world) {
        if (!OreGenObservations.isRecording()) return;

        try {
            if (!(oreBlock instanceof Block)) return;
            OreGenObservations.record((Block) oreBlock, size, meta, x, y, z,
                    world instanceof World ? (World) world : null);
        } catch (Throwable ignored) {
            // Worldgen must not die because a survey aid tripped over something.
        }
    }
}
