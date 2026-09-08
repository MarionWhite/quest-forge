package com.questforge.content.ench.enchants;

import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;
import com.questforge.content.net.PacketJammer;
import com.questforge.content.net.QFNetwork;

/**
 * The five enchantments whose effect lives outside the ordinary hook system.
 *
 * Four of them have no hooks at all. Reach is two bytecode patches; Tracker and
 * Prospector are drawn by the client from data it already has; Torchlight is a
 * block placed by a tick handler. They are declared here so they register, get an
 * ID, appear on books and show up in tooltips like every other enchantment -- the
 * registry should not have holes in it just because an effect is implemented
 * somewhere unusual.
 *
 * Jammer is the exception, and the only enchantment in the mod that sends a packet:
 * its effect happens on somebody else's screen.
 */
public class ClientEnchants {

    /** Longer swings. Implemented by ReachTransformer + QFReachHooks. */
    public static class Reach extends QFEnchantment {

        public Reach(int id) {
            super(id, "qf.reach", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // a passive range change; doubling it means nothing
        }
    }

    /** Living things outlined through walls. Implemented by TrackerFX. */
    public static class Tracker extends QFEnchantment {

        public Tracker(int id) {
            super(id, "qf.tracker", Rarity.COMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }
    }

    /** A readout of nearby ore. Implemented by ProspectorHUD. */
    public static class Prospector extends QFEnchantment {

        public Prospector(int id) {
            super(id, "qf.prospector", Rarity.RARE, EnchantCategory.PICKAXE, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }
    }

    /** The pickaxe glows. Implemented by BlockEnchantLight + TorchlightUpkeep. */
    public static class Torchlight extends QFEnchantment {

        public Torchlight(int id) {
            super(id, "qf.torchlight", Rarity.UNCOMMON, EnchantCategory.PICKAXE, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }
    }

    /**
     * Every hit makes the victim's screen worse, and consecutive hits make it worse
     * still. Players only -- there is no screen to ruin on a zombie.
     */
    public static class Jammer extends QFEnchantment {

        /** A hit this long after the last one starts the escalation over. */
        private static final int WINDOW = 100;

        /** Resolution divisor at the first hit, and how much each further hit adds. */
        private static final int BASE_FACTOR = 3;
        private static final int FACTOR_PER_HIT = 2;
        private static final int MAX_FACTOR = 16;

        /** How long a single hit's jam lasts, before level scaling. */
        private static final int BASE_TICKS = 60;

        private static class Hits {
            int count;
            int lastTick;
        }

        /** Keyed on the victim: the escalation is a property of who is being hit. */
        private static final Map<EntityPlayer, Hits> STREAK = new WeakHashMap<EntityPlayer, Hits>();

        public Jammer(int id) {
            super(id, "qf.jammer", Rarity.LEGENDARY, EnchantCategory.WEAPON, 3);
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.world == null || ctx.world.isRemote) return;
            if (!(ctx.target instanceof EntityPlayerMP)) return;
            if (ctx.target == ctx.user) return;

            EntityPlayerMP victim = (EntityPlayerMP) ctx.target;

            Hits hits = STREAK.get(victim);
            if (hits == null) {
                hits = new Hits();
                STREAK.put(victim, hits);
            }
            if (victim.ticksExisted - hits.lastTick > WINDOW) {
                hits.count = 0;
            }
            hits.count++;
            hits.lastTick = victim.ticksExisted;

            int factor = Math.min(MAX_FACTOR,
                    BASE_FACTOR + (hits.count - 1) * FACTOR_PER_HIT + (ctx.level - 1));
            int ticks = BASE_TICKS + (40 * ctx.level);

            QFNetwork.toPlayer(new PacketJammer(factor, ticks), victim);
        }
    }
}
