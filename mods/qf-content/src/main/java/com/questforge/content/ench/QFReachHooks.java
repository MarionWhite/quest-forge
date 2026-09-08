package com.questforge.content.ench;

import java.lang.reflect.Field;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.ItemStack;

/**
 * Server side of the Reach enchantment. Called from bytecode injected into
 * NetHandlerPlayServer, in place of its hardcoded 36.0D distance checks.
 *
 * Kept separate from QFReachClientHooks so that nothing on a dedicated server ever
 * has cause to resolve a client-only class.
 */
public class QFReachHooks {

    /** Vanilla's tolerance. Returned unchanged whenever anything is unclear. */
    private static final double VANILLA_SQ = 36.0D;

    /** Vanilla allows six blocks server-side even though the client aims at 4.5. */
    private static final double VANILLA_RADIUS = 6.0D;

    private static Field playerField;
    private static boolean playerFieldSearched;

    /**
     * How far this player is currently allowed to reach, squared.
     *
     * Never returns less than vanilla: this raises a ceiling, it must never
     * introduce a new way for a legitimate click to be rejected.
     *
     * @param handler the NetHandlerPlayServer the check is running inside. Typed as
     *                Object so the descriptor in the transformer needs no obfuscated
     *                class name.
     */
    public static double serverReachSq(Object handler) {
        try {
            EntityPlayerMP player = playerOf(handler);
            if (player == null) return VANILLA_SQ;

            int level = levelOn(player.getHeldItem());
            if (level <= 0) return VANILLA_SQ;

            double radius = VANILLA_RADIUS + level;
            return radius * radius;
        } catch (Throwable t) {
            // A distance check is not worth crashing a connection over.
            return VANILLA_SQ;
        }
    }

    static int levelOn(ItemStack stack) {
        QFEnchantment ench = QFEnchantments.reach;
        if (ench == null || stack == null) return 0;
        return EnchantmentHelper.getEnchantmentLevel(ench.effectId, stack);
    }

    /**
     * The handler's player, found by type rather than by name.
     *
     * The field is playerEntity in a dev workspace and field_147369_b in a real
     * instance; it is the only EntityPlayerMP the class holds either way.
     */
    private static EntityPlayerMP playerOf(Object handler) throws IllegalAccessException {
        if (handler == null) return null;

        if (!playerFieldSearched) {
            playerFieldSearched = true;
            for (Field f : handler.getClass().getDeclaredFields()) {
                if (EntityPlayerMP.class.isAssignableFrom(f.getType())) {
                    f.setAccessible(true);
                    playerField = f;
                    break;
                }
            }
            if (playerField == null) {
                com.questforge.content.QuestForgeContent.log.error(
                        "Reach: no EntityPlayerMP field on " + handler.getClass().getName()
                        + "; falling back to vanilla range.");
            }
        }

        if (playerField == null) return null;
        return (EntityPlayerMP) playerField.get(handler);
    }
}
