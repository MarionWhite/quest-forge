package com.questforge.content;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;

/**
 * Block's constructor is protected in 1.7.10, so every block needs its own
 * subclass. That is also where per-block behaviour goes -- override
 * onBlockActivated, randomDisplayTick, getDrops and so on.
 */
public class BlockForge extends Block {

    public BlockForge(Material material) {
        super(material);
    }
}
