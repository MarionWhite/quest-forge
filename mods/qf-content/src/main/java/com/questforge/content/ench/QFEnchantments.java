package com.questforge.content.ench;

import java.lang.reflect.Constructor;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import net.minecraft.enchantment.Enchantment;
import net.minecraftforge.common.config.Configuration;

import com.questforge.content.QuestForgeContent;
import com.questforge.content.ench.enchants.AbilityEnchants;
import com.questforge.content.ench.enchants.ArmorEnchants;
import com.questforge.content.ench.enchants.ClientEnchants;
import com.questforge.content.ench.enchants.BowEnchants;
import com.questforge.content.ench.enchants.CombatEnchants;
import com.questforge.content.ench.enchants.EnchantVigor;
import com.questforge.content.ench.enchants.EnchantBerserk;
import com.questforge.content.ench.enchants.EnchantExecutioner;
import com.questforge.content.ench.enchants.EnchantFrostbite;
import com.questforge.content.ench.enchants.EnchantMagnetize;
import com.questforge.content.ench.enchants.EnchantMultiStrike;
import com.questforge.content.ench.enchants.EnchantNightsight;
import com.questforge.content.ench.enchants.EnchantSoulbound;
import com.questforge.content.ench.enchants.MiscEnchants;
import com.questforge.content.ench.enchants.PotionEnchants;
import com.questforge.content.ench.enchants.PvpEnchants;
import com.questforge.content.ench.enchants.ToolEnchants;
import com.questforge.content.ench.enchants.WeaponEnchants2;

/**
 * Registration and ID allocation.
 *
 * 1.7.10 has 256 enchantment ID slots for vanilla and every mod combined, and the
 * Enchantment constructor throws on a duplicate -- a hard crash at load. A pack
 * audit found 67 already in use, so this allocates from 132, inside the largest
 * free run (132-189).
 *
 * IDs are written back to the config on first run and reused forever after. That
 * matters: an enchantment ID is stored as a bare number on every enchanted item,
 * so if IDs shifted when a mod was added or removed, every item already enchanted
 * would silently become a different enchantment.
 */
public class QFEnchantments {

    private static final String CATEGORY = "enchantment_ids";
    private static final int DEFAULT_BASE = 132;

    private static final Map<Integer, QFEnchantment> BY_ID = new HashMap<Integer, QFEnchantment>();
    private static final Map<String, QFEnchantment> BY_NAME = new HashMap<String, QFEnchantment>();
    private static final List<QFEnchantment> ALL = new ArrayList<QFEnchantment>();

    /** Read by the dispatcher to decide whether to run every proc twice. */
    public static QFEnchantment multiStrike;

    /** Read by AttributeUpkeep, which drives it from outside the hook system. */
    public static QFEnchantment vigor;
    public static QFEnchantment turtle;

    /** Read by the Soulbound handler, which is driven from the bridge. */
    public static QFEnchantment soulbound;

    /**
     * The four whose effects live outside the hook system and so have to be looked
     * up by name from wherever they are actually implemented: the reach bytecode
     * hooks, the two client renderers, and the light-block upkeep.
     */
    public static QFEnchantment demonForged;
    public static QFEnchantment fortuneV;
    public static QFEnchantment fortuneX;
    public static QFEnchantment bold;
    /** Read by the client tick, which applies Flippers to the local player. */
    public static QFEnchantment flippers;
    public static QFEnchantment reach;
    public static QFEnchantment tracker;
    public static QFEnchantment prospector;
    public static QFEnchantment torchlight;

    /**
     * Every ID already pinned in the config, including ones belonging to
     * enchantments that have not registered yet.
     *
     * Without this, auto-allocation looks only at Enchantment.enchantmentsList --
     * which reflects what has been CONSTRUCTED so far, not what is RESERVED. A
     * newly added enchantment registering before an older one would take the
     * older one's pinned slot, and every item already carrying that enchantment
     * would silently become something else.
     */
    private static final java.util.Set<Integer> RESERVED = new java.util.HashSet<Integer>();

    public static void register(Configuration cfg) {
        RESERVED.clear();
        net.minecraftforge.common.config.ConfigCategory cat = cfg.getCategory(CATEGORY);
        for (net.minecraftforge.common.config.Property p : cat.getValues().values()) {
            int pinned = p.getInt(0);
            if (pinned > 0) RESERVED.add(Integer.valueOf(pinned));
        }

        cfg.addCustomCategoryComment(CATEGORY,
                "Enchantment IDs, pinned on first run. Do NOT change these once you have\n"
              + "played with them: the ID is what is stored on an enchanted item, so\n"
              + "changing it turns every existing copy into a different enchantment.\n"
              + "Valid range is 0-255 and is shared with every other mod.");

        // --- Meta -------------------------------------------------------
        multiStrike = add(cfg, "multistrike", EnchantMultiStrike.class);

        // --- Weapons ----------------------------------------------------
        add(cfg, "executioner", EnchantExecutioner.class);
        add(cfg, "berserk", EnchantBerserk.class);
        add(cfg, "frostbite", EnchantFrostbite.class);
        add(cfg, "colossus", CombatEnchants.Colossus.class);
        add(cfg, "feast", CombatEnchants.Feast.class);
        add(cfg, "poisonous", CombatEnchants.Poisonous.class);
        add(cfg, "venomous", CombatEnchants.Venomous.class);
        add(cfg, "blind", CombatEnchants.Blind.class);
        add(cfg, "suplex", CombatEnchants.Suplex.class);
        add(cfg, "daze", CombatEnchants.Daze.class);
        add(cfg, "roulette", CombatEnchants.Roulette.class);
        add(cfg, "cultist", CombatEnchants.Cultist.class);
        add(cfg, "killingblow", CombatEnchants.KillingBlow.class);
        add(cfg, "momentum", CombatEnchants.Momentum.class);
        add(cfg, "riposte", CombatEnchants.Riposte.class);
        add(cfg, "rupture", WeaponEnchants2.Rupture.class);
        add(cfg, "arc", WeaponEnchants2.Arc.class);
        add(cfg, "disarm", WeaponEnchants2.Disarm.class);
        add(cfg, "assassinate", WeaponEnchants2.Assassinate.class);
        add(cfg, "sunder", WeaponEnchants2.Sunder.class);
        add(cfg, "rage", WeaponEnchants2.Rage.class);
        add(cfg, "cripple", WeaponEnchants2.Cripple.class);
        add(cfg, "accelerant", WeaponEnchants2.Accelerant.class);
        add(cfg, "lich", WeaponEnchants2.Lich.class);
        add(cfg, "excalibur", WeaponEnchants2.Excalibur.class);
        demonForged = add(cfg, "demonforged", WeaponEnchants2.DemonForged.class);
        add(cfg, "necromancer", WeaponEnchants2.Necromancer.class);
        add(cfg, "alpha", WeaponEnchants2.Alpha.class);
        add(cfg, "bastion", WeaponEnchants2.Bastion.class);
        add(cfg, "trade", PvpEnchants.Trade.class);
        add(cfg, "decapitate", MiscEnchants.Decapitate.class);
        add(cfg, "crushingblow", AbilityEnchants.CrushingBlow.class);
        add(cfg, "getoffme", AbilityEnchants.GetOffMe.class);
        add(cfg, "rally", AbilityEnchants.Rally.class);
        reach = add(cfg, "reach", ClientEnchants.Reach.class);
        tracker = add(cfg, "tracker", ClientEnchants.Tracker.class);
        add(cfg, "jammer", ClientEnchants.Jammer.class);

        // --- Bows -------------------------------------------------------
        add(cfg, "piercing", BowEnchants.Piercing.class);
        add(cfg, "penetrating", BowEnchants.Penetrating.class);
        add(cfg, "ricochet", BowEnchants.Ricochet.class);
        add(cfg, "bola", BowEnchants.Bola.class);
        add(cfg, "instanttransmission", BowEnchants.InstantTransmission.class);
        add(cfg, "soulentwine", BowEnchants.SoulEntwine.class);
        add(cfg, "homing", BowEnchants.Homing.class);

        // --- Tools ------------------------------------------------------
        add(cfg, "magnetize", EnchantMagnetize.class);
        add(cfg, "haste", PotionEnchants.Haste.class);
        add(cfg, "excavate", ToolEnchants.Excavate.class);
        add(cfg, "timber", ToolEnchants.Timber.class);
        add(cfg, "tunneler", ToolEnchants.Tunneler.class);
        add(cfg, "sieve", ToolEnchants.Sieve.class);
        add(cfg, "bountiful", ToolEnchants.Bountiful.class);
        add(cfg, "transmuter", ToolEnchants.Transmuter.class);
        add(cfg, "oldreliable", ToolEnchants.OldReliable.class);
        add(cfg, "ecofriendly", ToolEnchants.EcoFriendly.class);
        add(cfg, "mending", ToolEnchants.Mending.class);
        fortuneV = add(cfg, "fortune_v", MiscEnchants.FortuneV.class);
        fortuneX = add(cfg, "fortune_x", MiscEnchants.FortuneX.class);
        bold = add(cfg, "bold", MiscEnchants.Bold.class);
        prospector = add(cfg, "prospector", ClientEnchants.Prospector.class);
        torchlight = add(cfg, "torchlight", ClientEnchants.Torchlight.class);

        // --- Armor ------------------------------------------------------
        add(cfg, "nightsight", EnchantNightsight.class);
        add(cfg, "frog", PotionEnchants.Frog.class);
        add(cfg, "deft", PotionEnchants.Deft.class);
        add(cfg, "tank", PotionEnchants.Tank.class);
        add(cfg, "cockroach", PotionEnchants.Cockroach.class);
        add(cfg, "regrowth", PotionEnchants.Regrowth.class);
        add(cfg, "bulwark", ArmorEnchants.Bulwark.class);
        add(cfg, "cleansing", ArmorEnchants.Cleansing.class);
        add(cfg, "stonehide", ArmorEnchants.Stonehide.class);
        add(cfg, "rebound", ArmorEnchants.Rebound.class);
        add(cfg, "reflect", ArmorEnchants.Reflect.class);
        turtle = add(cfg, "turtle", ArmorEnchants.Turtle.class);
        add(cfg, "affliction", ArmorEnchants.Affliction.class);
        flippers = add(cfg, "flippers", ArmorEnchants.Flippers.class);
        add(cfg, "camouflage", ArmorEnchants.Camouflage.class);
        add(cfg, "sacrifice", ArmorEnchants.Sacrifice.class);
        vigor = add(cfg, "vigor", EnchantVigor.class);
        add(cfg, "polarize", PvpEnchants.Polarize.class);
        add(cfg, "frostpath", MiscEnchants.Frostpath.class);
        soulbound = add(cfg, "soulbound", EnchantSoulbound.class);

        QuestForgeContent.log.info("Registered " + ALL.size() + " custom enchantments.");
    }

    private static QFEnchantment add(Configuration cfg, String name,
            Class<? extends QFEnchantment> clazz) {

        int configured = cfg.get(CATEGORY, name, 0,
                "0 = allocate a free ID automatically and pin it here").getInt();

        int id = (configured > 0) ? configured : findFreeId();

        if (id < 0) {
            QuestForgeContent.log.error("No free enchantment ID for '" + name
                    + "'. All 256 slots are taken; skipping it.");
            return null;
        }
        if (Enchantment.enchantmentsList[id] != null) {
            QuestForgeContent.log.error("Enchantment ID " + id + " for '" + name
                    + "' is taken by " + Enchantment.enchantmentsList[id].getClass().getName()
                    + ". Change it in the config; skipping it to avoid a crash.");
            return null;
        }

        QFEnchantment ench;
        try {
            Constructor<? extends QFEnchantment> ctor = clazz.getConstructor(int.class);
            ench = ctor.newInstance(Integer.valueOf(id));
        } catch (Exception e) {
            QuestForgeContent.log.error("Could not construct enchantment '" + name
                    + "' (" + clazz.getName() + "); it needs a public (int) constructor.", e);
            return null;
        }

        BY_ID.put(Integer.valueOf(id), ench);
        BY_NAME.put(ench.getName(), ench);
        ALL.add(ench);

        // Newly allocated IDs join the reserved set too, so a later auto-allocation
        // in this same pass cannot pick the same slot.
        RESERVED.add(Integer.valueOf(id));
        cfg.get(CATEGORY, name, 0).set(id);
        return ench;
    }

    /**
     * First slot that is neither occupied by a constructed enchantment nor
     * reserved by a config pin. Searches from the default base upward, then wraps.
     */
    private static int findFreeId() {
        for (int i = DEFAULT_BASE; i < Enchantment.enchantmentsList.length; i++) {
            if (isAvailable(i)) return i;
        }
        for (int i = 0; i < DEFAULT_BASE; i++) {
            if (isAvailable(i)) return i;
        }
        return -1;
    }

    private static boolean isAvailable(int id) {
        return Enchantment.enchantmentsList[id] == null
                && !RESERVED.contains(Integer.valueOf(id));
    }

    public static QFEnchantment byId(int id) {
        return BY_ID.get(Integer.valueOf(id));
    }

    /** Books store the name, not the ID, so they survive a config edit. */
    public static QFEnchantment byName(String name) {
        return name == null ? null : BY_NAME.get(name);
    }

    public static List<QFEnchantment> all() {
        return ALL;
    }
}
