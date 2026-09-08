package com.questforge.content.ench;

import net.minecraft.client.Minecraft;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Client side of the Reach enchantment. Called from bytecode injected at the
 * return of PlayerControllerMP.getBlockReachDistance.
 *
 * That one method feeds both the block ray trace and the entity ray trace in
 * EntityRenderer.getMouseOver, so adjusting it here extends mining range and melee
 * range together -- which is what makes this a one-line patch rather than a rewrite
 * of the targeting code.
 */
@SideOnly(Side.CLIENT)
public class QFReachClientHooks {

    /**
     * @param base the distance vanilla was about to return
     * @return the distance the player actually gets
     */
    public static float adjust(float base) {
        try {
            Minecraft mc = Minecraft.getMinecraft();
            if (mc == null || mc.thePlayer == null) return base;

            int level = QFReachHooks.levelOn(mc.thePlayer.getHeldItem());
            return level <= 0 ? base : base + level;
        } catch (Throwable t) {
            return base;
        }
    }
}
