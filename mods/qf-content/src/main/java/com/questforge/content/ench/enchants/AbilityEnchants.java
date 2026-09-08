package com.questforge.content.ench.enchants;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import com.questforge.content.ench.CombatState;
import com.questforge.content.ench.Cooldowns;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;
import com.questforge.content.ench.RightClickState;

/**
 * Enchantments the player triggers deliberately, rather than ones that proc.
 *
 * 1.7.10 has no "button held" signal, so the input conditions are approximated:
 * sneaking is read directly, and right-click-held is inferred from a recent
 * PlayerInteractEvent. Neither needs a custom packet.
 */
public class AbilityEnchants {

    /** Crouch and strike for a heavy hit. */
    public static class CrushingBlow extends QFEnchantment {
        private static final String ABILITY = "crushingblow";
        private static final int COOLDOWN = 200;   // 10s

        public CrushingBlow(int id) {
            super(id, "qf.crushingblow", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // an activated ability, not a proc
        }

        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (!(ctx.user instanceof EntityPlayer)) return;
            EntityPlayer player = (EntityPlayer) ctx.user;
            if (!player.isSneaking()) return;

            if (!Cooldowns.isReady(player, ABILITY)) {
                return;   // silent: spamming a message on every crouched hit would be noise
            }

            Cooldowns.start(player, ABILITY, COOLDOWN);
            ctx.damage *= 1.0F + (0.6F * ctx.level);

            if (ctx.target != null) {
                ctx.target.motionY += 0.25D;
                ctx.target.velocityChanged = true;
            }
            ctx.world.playSoundAtEntity(player, "random.anvil_land", 0.7F, 1.6F);
        }
    }

    /**
     * Hold right-click and swing to launch whatever is in front of you a very long
     * way. The panic button.
     */
    public static class GetOffMe extends QFEnchantment {
        private static final String ABILITY = "getoffme";
        private static final int COOLDOWN = 12000;   // 10 minutes: it is the far version, and this is what it costs

        public GetOffMe(int id) {
            super(id, "qf.getoffme", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (!(ctx.user instanceof EntityPlayer) || ctx.target == null) return;
            EntityPlayer player = (EntityPlayer) ctx.user;

            if (!RightClickState.isHolding(player)) return;
            if (!Cooldowns.isReady(player, ABILITY)) {
                player.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY
                        + "Not yet -- " + Cooldowns.secondsLeft(player, ABILITY) + "s."));
                return;
            }

            Cooldowns.start(player, ABILITY, COOLDOWN);

            double dx = ctx.target.posX - player.posX;
            double dz = ctx.target.posZ - player.posZ;
            double dist = Math.sqrt(dx * dx + dz * dz);

            // These are VELOCITIES, not distances. With the 1.0 vertical launch
            // below, vanilla's air drag turns one unit into roughly ten blocks of
            // travel -- so 4 to 6 here sends them somewhere between forty and sixty
            // blocks away. That is the entire point of the enchantment, and the two
            // minute cooldown above is what it costs.
            double power = 3.0D + (1.0D * ctx.level);

            if (dist > 0.0001D) {
                ctx.target.motionX += (dx / dist) * power;
                ctx.target.motionZ += (dz / dist) * power;
            }
            ctx.target.motionY += 1.0D;
            ctx.target.velocityChanged = true;
            ctx.target.fallDistance = 0F;   // the launch itself should not kill it

            ctx.world.playSoundAtEntity(player, "random.explode", 0.8F, 1.4F);
        }
    }

    /** Plays a flourish when a fight starts. Pure flavour. */
    public static class Rally extends QFEnchantment {
        private static final int OUT_OF_COMBAT = 200;

        public Rally(int id) {
            super(id, "qf.rally", Rarity.COMMON, EnchantCategory.WEAPON, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (!(ctx.user instanceof EntityPlayer) || ctx.world.isRemote) return;
            EntityPlayer player = (EntityPlayer) ctx.user;

            // Only when this is the opening blow of a fight, not every swing.
            if (CombatState.wasHurtRecently(player, OUT_OF_COMBAT)) return;
            if (!Cooldowns.isReady(player, "rally")) return;

            Cooldowns.start(player, "rally", OUT_OF_COMBAT);
            ctx.world.playSoundAtEntity(player, "note.pling", 1.0F, 0.7F);
            ctx.world.playSoundAtEntity(player, "mob.wither.spawn", 0.35F, 1.8F);
        }
    }
}
