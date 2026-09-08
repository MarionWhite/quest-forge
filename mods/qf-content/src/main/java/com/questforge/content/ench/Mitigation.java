package com.questforge.content.ench;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemStack;
import net.minecraft.potion.Potion;
import net.minecraft.util.DamageSource;

/**
 * What an incoming hit will actually cost, after vanilla has finished with it.
 *
 * LivingHurtEvent -- where every onDamaged hook runs -- fires BEFORE
 * applyArmorCalculations and applyPotionDamageCalculations. So the damage figure
 * an armor enchantment sees is the raw swing, not the number that will reach the
 * health bar. For an enchantment that reduces damage that distinction does not
 * matter, because a fraction of the raw hit is the same fraction of the final
 * one. For an enchantment that asks "would this hit kill me?" it matters
 * enormously: in this pack a boss swings for several times a player's maximum
 * health, and full enchanted diamond divides that by twenty-five.
 *
 * This mirrors the vanilla arithmetic so those enchantments can ask the question
 * about the number that will really land.
 */
public final class Mitigation {

    private Mitigation() {}

    /**
     * The damage that will reach the health bar, given a raw LivingHurtEvent
     * amount. Absorption is deliberately not included: it is a buffer in front
     * of the health bar rather than a reduction, and the callers here are asking
     * about health.
     *
     * Two things stop this from being exact, both of them small. Custom armor
     * enchantments on OTHER pieces may not have run yet, because each piece is
     * dispatched separately; and a mod may alter damage in a later listener.
     */
    public static float predict(EntityLivingBase user, DamageSource source, float raw) {
        if (user == null || raw <= 0.0F) return raw;
        if (source != null && source.isDamageAbsolute()) return raw;

        float amount = raw;

        if (source == null || !source.isUnblockable()) {
            amount = afterArmour(user, amount);
        }

        // applyPotionDamageCalculations: resistance, then protection enchantments
        if (user.isPotionActive(Potion.resistance) && source != DamageSource.outOfWorld) {
            int level = (user.getActivePotionEffect(Potion.resistance).getAmplifier() + 1) * 5;
            amount = (amount * (25 - level)) / 25.0F;
        }
        if (amount <= 0.0F) return 0.0F;

        ItemStack[] worn = user.getLastActiveItems();
        if (worn != null && source != null) {
            int protection = EnchantmentHelper.getEnchantmentModifierDamage(worn, source);
            if (protection > 20) protection = 20;
            if (protection > 0) {
                amount = (amount * (25 - protection)) / 25.0F;
            }
        }
        return amount;
    }

    /**
     * The armour step, read-only.
     *
     * A player does NOT use vanilla's applyArmorCalculations. Forge patches
     * EntityPlayer.damageEntity to call ISpecialArmor.ArmorProperties.ApplyArmor
     * instead, which sums a per-piece absorption ratio rather than reading
     * getTotalArmorValue, and which caps each piece by its REMAINING DURABILITY.
     * Below 25 points with ordinary armour the two agree exactly, which is why
     * this went unnoticed; at and above 25 they do not, and this pack has
     * several sets up there. Durability is what stops a 25-point set from being
     * permanently invulnerable: the cap binds as pieces wear down.
     *
     * ApplyArmor also SPENDS durability as a side effect, so it cannot be called
     * to ask a question. This mirrors its arithmetic and touches nothing.
     *
     * Every plain ItemArmor gets Priority 0, so all worn pieces land in a single
     * priority group and StandardizeList reduces to the two branches below. A
     * piece implementing ISpecialArmor could declare another priority; none in
     * this pack does, and querying one would mean calling into mod code from a
     * prediction, so those pieces are read as their plain armour value.
     */
    private static float afterArmour(EntityLivingBase user, float amount) {
        if (!(user instanceof EntityPlayer)) {
            // Mobs really do use the vanilla formula: EntityLivingBase.damageEntity
            // calls applyArmorCalculations directly.
            return (amount * (25 - user.getTotalArmorValue())) / 25.0F;
        }

        ItemStack[] worn = ((EntityPlayer) user).inventory.armorInventory;
        double scaled = amount * 25.0D;      // ApplyArmor works in 25ths
        double total = 0.0D;
        int count = 0;
        double[] ratios = new double[worn.length];
        double[] caps = new double[worn.length];

        for (int i = 0; i < worn.length; i++) {
            ItemStack piece = worn[i];
            if (piece == null || !(piece.getItem() instanceof ItemArmor)) continue;
            ItemArmor armour = (ItemArmor) piece.getItem();
            ratios[count] = armour.damageReduceAmount / 25.0D;
            caps[count] = armour.getMaxDamage() + 1 - piece.getItemDamage();
            total += ratios[count];
            count++;
        }
        if (count == 0) return amount;

        // StandardizeList, single priority group. Sorted by AbsorbMax * 100 /
        // AbsorbRatio ascending, so the piece closest to breaking is capped first
        // and the pieces after it renormalise against what is left.
        sortByHeadroom(ratios, caps, count);

        int start = 0;
        while (true) {
            total = 0.0D;
            for (int i = 0; i < count; i++) total += ratios[i];

            if (total > 1.0D) {
                // Normalise toward 1.0. A piece that lacks the durability to
                // cover its share is capped at its remaining durability instead,
                // and that ends the pass: the capped ratio then counts toward the
                // divisor for the pieces after it, on the next pass.
                boolean capped = false;
                for (int y = start; y < count; y++) {
                    double normalised = ratios[y] / total;
                    if (normalised * scaled > caps[y]) {
                        ratios[y] = caps[y] / scaled;
                        start = y + 1;
                        capped = true;
                        break;
                    }
                    ratios[y] = normalised;
                }
                if (!capped || start >= count) break;
            } else {
                // The branch that is easy to miss. Below a full 1.0 of absorption
                // no normalising happens, but the durability cap still binds.
                for (int y = start; y < count; y++) {
                    if (scaled * ratios[y] > caps[y]) ratios[y] = caps[y] / scaled;
                }
                break;
            }
        }

        total = 0.0D;
        for (int i = 0; i < count; i++) total += ratios[i];
        // ApplyArmor never clamps the total, so it can return a negative number;
        // EntityPlayer.damageEntity then stops at `if (amount <= 0) return`.
        if (total > 1.0D) total = 1.0D;

        return (float) (scaled * (1.0D - total) / 25.0D);
    }

    /** ArmorProperties.compareTo, for one priority group: AbsorbMax * 100 / AbsorbRatio ascending. */
    private static void sortByHeadroom(double[] ratios, double[] caps, int count) {
        for (int i = 1; i < count; i++) {
            double r = ratios[i], c = caps[i];
            int rank = ratios[i] == 0.0D ? 0 : (int) (caps[i] * 100.0D / ratios[i]);
            int j = i - 1;
            while (j >= 0) {
                int other = ratios[j] == 0.0D ? 0 : (int) (caps[j] * 100.0D / ratios[j]);
                if (other <= rank) break;
                ratios[j + 1] = ratios[j];
                caps[j + 1] = caps[j];
                j--;
            }
            ratios[j + 1] = r;
            caps[j + 1] = c;
        }
    }

    /** Whether this hit, as it stands, would leave the wearer at or below {@code floor}. */
    public static boolean wouldLeaveAtOrBelow(EntityLivingBase user, DamageSource source,
            float raw, float floor) {
        if (user == null) return false;
        return user.getHealth() - predict(user, source, raw) <= floor;
    }
}
