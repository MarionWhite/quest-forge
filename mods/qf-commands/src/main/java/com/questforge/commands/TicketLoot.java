package com.questforge.commands;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.boss.IBossDisplayData;
import net.minecraft.entity.item.EntityItem;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.event.entity.living.LivingDropsEvent;

/**
 * Where tickets come from.
 *
 * <h3>Why drops and not chest loot</h3>
 *
 * ChestGenHooks weights bottom out at 1, and a vanilla dungeon chest's whole
 * table only sums to about 114 across 8 rolls. One ticket at weight 1 therefore
 * turns up in roughly one dungeon chest in fifteen -- and there are twenty-one
 * world-loot tickets to place. Spread over the eight vanilla categories that is
 * a ticket in one chest in six, which is not rare by any reading of the word.
 * The weight cannot go lower, so chest loot simply cannot express this.
 *
 * A drop chance can. The three constants below are the whole tuning surface and
 * they mean exactly what they say.
 *
 * <h3>What drops where</h3>
 *
 * A gated dimension's ticket drops only inside that dimension -- mostly from
 * whatever counts as a boss there, rarely from anything else so that a
 * dimension with no boss still yields one eventually. It is a way back, never a
 * way in.
 *
 * Everything else is drawn from the world-loot pool on any kill, anywhere, and
 * picks a command the player does not already have -- so the pool empties as
 * they collect it rather than handing out duplicates forever.
 */
public class TicketLoot {

    /** One kill in this many drops a ticket from the world-loot pool. */
    public static final int WORLD_LOOT_ODDS = 5000;

    /** One boss kill in this many drops its own dimension's ticket. */
    public static final int BOSS_ODDS = 10;

    /** One ordinary kill inside a gated dimension in this many does the same. */
    public static final int IN_DIMENSION_ODDS = 3000;

    /**
     * Health at which a mob counts as a boss even though it does not say so.
     *
     * IBossDisplayData is the honest signal -- it is what draws the boss bar,
     * so Twilight Forest, TragicMC and OreSpawn bosses all implement it. The
     * health floor catches anything that skips the bar, and sits high enough
     * that Infernal Mobs' buffed ordinary mobs do not clear it.
     */
    public static final float BOSS_HEALTH = 150F;

    @SubscribeEvent
    public void onLivingDrops(LivingDropsEvent event) {
        EntityLivingBase dead = event.entityLiving;

        if (dead == null || dead.worldObj == null || dead.worldObj.isRemote) {
            return;
        }

        // Only a player's kill pays out. Otherwise a mob farm, or two mobs
        // fighting in a loaded chunk, prints tickets with nobody present.
        if (!(event.source.getEntity() instanceof EntityPlayer)) {
            return;
        }

        EntityPlayer player = (EntityPlayer) event.source.getEntity();
        Random rand = dead.worldObj.rand;

        Unlockable gated = Unlockables.gatedFor(dead.dimension);

        if (gated != null) {
            if (Unlocks.has(player, gated.id)) {
                return;
            }

            boolean boss = dead instanceof IBossDisplayData || dead.getMaxHealth() >= BOSS_HEALTH;
            int odds = boss ? BOSS_ODDS : IN_DIMENSION_ODDS;

            if (rand.nextInt(odds) == 0) {
                drop(event, gated);
            }

            // A gated dimension pays out its own ticket and nothing else.
            // Finding a ticket for somewhere across the pack while standing in
            // Torment would read as a bug even though it is not.
            return;
        }

        if (rand.nextInt(WORLD_LOOT_ODDS) != 0) {
            return;
        }

        Unlockable prize = pickWorldLoot(player, rand);

        if (prize != null) {
            drop(event, prize);
        }
    }

    /**
     * A world-loot command this player has not earned, or null once they have
     * them all. Uniform across what is left, so the last few are no rarer per
     * drop than the first.
     */
    private static Unlockable pickWorldLoot(EntityPlayer player, Random rand) {
        List<Unlockable> pool = new ArrayList<Unlockable>();

        for (Unlockable u : Unlockables.all()) {
            if (Unlockables.sourceOf(u) == Unlockables.Source.WORLD_LOOT
                    && !Unlocks.has(player, u.id)) {
                pool.add(u);
            }
        }

        return pool.isEmpty() ? null : pool.get(rand.nextInt(pool.size()));
    }

    private static void drop(LivingDropsEvent event, Unlockable u) {
        EntityLivingBase dead = event.entityLiving;
        ItemStack stack = new ItemStack(QuestForgeCommands.ticket, 1, Unlockables.indexOf(u));

        event.drops.add(new EntityItem(dead.worldObj,
                dead.posX, dead.posY + dead.height / 2D, dead.posZ, stack));
    }
}
