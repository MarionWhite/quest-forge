package com.questforge.content.difficulty;

import java.io.File;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import net.minecraftforge.common.config.Configuration;
import net.minecraftforge.common.config.Property;

/**
 * config/qfcontent-difficulty.cfg: what each difficulty tier does.
 *
 * Every multiplier defaults to 1.0, the keep fraction to 1.0 and the
 * armour-ignoring share to 0, so with a grid but an untouched config the game plays
 * exactly as before (the author's decision of 2026-10-25: ship the mechanism inert,
 * tune after the census). Each property's comment carries the number
 * docs/design/world/r14/difficulty-enforcement-proposal.md proposes, as a starting
 * point for that tuning; none of them is applied by default.
 */
public final class DifficultyConfig {

    public static final int MIN_TIER = 2;

    /** One tier's numbers. */
    public static final class Tier {
        public final int tier;
        public double spawnKeep = 1.0;
        public double health = 1.0;
        public double damage = 1.0;
        public double eliteOdds = 1.0;
        public double xp = 1.0;
        public double speed = 1.0;
        public double armourIgnore = 0.0;

        Tier(int tier) {
            this.tier = tier;
        }

        /** True when this tier changes nothing at all. */
        public boolean inert() {
            return spawnKeep == 1.0 && health == 1.0 && damage == 1.0 && eliteOdds == 1.0 && xp == 1.0
                    && speed == 1.0 && armourIgnore == 0.0;
        }

        @Override
        public String toString() {
            return "keep " + spawnKeep + ", health x" + health + ", damage x" + damage + ", elites x" + eliteOdds
                    + ", xp x" + xp + ", speed x" + speed + ", armour-ignoring " + armourIgnore;
        }
    }

    public boolean enabled = true;
    public String gridFile = "data/qf-tiers.bin";
    public Set<Integer> dimensions = new HashSet<Integer>(Arrays.asList(0));
    public int maxTier = 8;
    public int outskirtsStep = 4000;
    public int caveBonus = 1;
    public int caveDepth = 4;
    public int cageTier = 3;
    public int pocketMaxTier = 2;
    public boolean suppressEventsInPockets = true;
    public Set<String> bossNames = new HashSet<String>();
    public Set<String> excludeNames = new HashSet<String>();
    public boolean debugLog = false;
    public Tier[] tiers;

    /** The settings for a tier, clamped into the configured range. */
    public Tier tier(int t) {
        if (t < MIN_TIER) t = MIN_TIER;
        if (t > maxTier) t = maxTier;
        return tiers[t];
    }

    // The proposal's numbers (§3.3, §4.2, §4.3, §4.4, Q4, Q5), shown in the comments only.
    private static final String[][] PROPOSED = {
            // tier, spawnKeep, health, damage, eliteOdds, xp, speed, armourIgnore
            {"2", "0.66 (0.55 with the JAS MONSTER cap raised 70 -> 84, when T3 becomes 0.83)", "0.7", "0.8",
                    "0.45 (3% elites)", "0.8", "1.0", "0"},
            {"3", "1.0 (0.83 with the cap at 84) -- today's pack", "1.0", "1.0", "1.0 (1 in 15, today)", "1.0",
                    "1.0", "0"},
            {"4", "1.0", "1.5", "1.3", "1.5 (10% elites)", "1.5", "1.0", "0"},
            {"5", "1.0", "2.2", "1.7", "2.25 (15% elites)", "2.0", "1.0", "0"},
            {"6", "1.0", "3.0", "2.2", "3.3 (22% elites)", "3.0",
                    "no number proposed yet (only T6 is faster); try 1.15 first",
                    "0.2 (Q5's example: 20% of tier damage ignores armour); test it before use"},
    };

    private static final String[] DEFAULT_BOSSES = {
            // The bosses the combat campaign fights (tools/balance/run_campaign.py), by entity name.
            "TwilightForest.Naga", "TwilightForest.Twilight Lich", "TwilightForest.Minoshroom",
            "TwilightForest.Knight Phantom", "TwilightForest.Snow Queen", "TwilightForest.Yeti Boss",
            "TwilightForest.Tower Boss", "TwilightForest.Hydra", "TwilightForest.Ur-ghast",
            "witchery.death", "witchery.lordoftorment", "witchery.leonard", "witchery.babayaga",
            "witchery.hornedHuntsman", "WitherBoss", "EnderDragon", "HardcoreEnderExpansion.EnderDemon",
            "TragicMC.Apis", "TragicMC.Kitsune", "TragicMC.DeathReaper", "TragicMC.Polaris",
            "TragicMC.TimeController", "TragicMC.Enyvil", "TragicMC.Yeti", "TragicMC.Claymation",
            "TragicMC.Overlord", "chocolateQuest.monking",
            "Mantis", "Mothra", "Basilisk", "Emperor_Scorpion", "The_Kraken", "Mobzilla", "The_Queen",
            "The_King", "legends.Godzilla", "demonmobs.rahovart",
    };

    public static DifficultyConfig load(File file) {
        Configuration c = new Configuration(file);
        c.load();
        DifficultyConfig k = new DifficultyConfig();
        String g = "general";
        c.addCustomCategoryComment(g, "Quest Forge difficulty tiers (qf-content). The map of tiers is the baked grid in\n"
                + "the world folder; with no grid file this whole feature is off and nothing below is read.\n"
                + "See docs/design/world/r14/difficulty-mechanism.md.");
        k.enabled = c.getBoolean("enabled", g, true, "Master switch. false = inert even with a grid file.");
        k.gridFile = c.getString("gridFile", g, k.gridFile,
                "The baked tier grid, relative to the world folder (tools/world/difficulty.py --bake). May be gzipped.");
        int[] dims = c.get(g, "dimensions", new int[]{0}, "Dimensions the grid applies to. Others keep today's behaviour.")
                .getIntList();
        k.dimensions.clear();
        for (int d : dims) k.dimensions.add(d);
        k.maxTier = c.getInt("maxTier", g, 8, 6, 20,
                "Highest tier. Tiers above 6 exist only in the outskirts (beyond the grid) and in caves under T6+.");
        k.outskirtsStep = c.getInt("outskirtsStep", g, 4000, 0, 1000000,
                "Outside the grid the tier starts at the grid's edge tier (6) and rises by one every this many\n"
                        + "blocks from the edge, up to maxTier. 0 = flat T6.");
        k.caveBonus = c.getInt("caveBonus", g, 1, 0, 5, "Tiers added in caves (no sky access, below the surface).");
        k.caveDepth = c.getInt("caveDepth", g, 4, 0, 255,
                "A spot counts as a cave when it cannot see the sky AND lies at least this many blocks below the top\n"
                        + "solid block of its column (so the shade of a tree or an overhang is not a cave).");
        k.cageTier = c.getInt("cageTier", g, 3, MIN_TIER, 20,
                "Player-made spawners (Soul Shards cages) always use this tier, wherever they stand.");
        k.pocketMaxTier = c.getInt("pocketMaxTier", g, 2, 0, 20,
                "A spawn pocket is where the grid tier is at most this (the pockets are the only T2 land).");
        k.suppressEventsInPockets = c.getBoolean("suppressLycanitesEventsInPockets", g, true,
                "Lycanites mob-event spawns (Boulder Dash, Arachnophobia, ...) are refused inside spawn pockets.\n"
                        + "The author's decision (2026-10-25); the event itself still runs elsewhere.");
        k.bossNames = new HashSet<String>(Arrays.asList(c.getStringList("bosses", g, DEFAULT_BOSSES,
                "Entity names (EntityList) never touched by tiers. Anything with a boss health bar\n"
                        + "(IBossDisplayData) and any Lycanites boss is excluded too, listed or not.")));
        k.excludeNames = new HashSet<String>(Arrays.asList(c.getStringList("exclude", g, new String[0],
                "Other entity names never touched by tiers.")));
        k.debugLog = c.getBoolean("debugLog", g, false, "Log every tier decision (spawns, stats, hits). Noisy.");

        k.tiers = new Tier[k.maxTier + 1];
        for (int t = MIN_TIER; t <= k.maxTier; t++) {
            Tier s = new Tier(t);
            String cat = "tier" + t;
            String[] p = t - MIN_TIER < PROPOSED.length ? PROPOSED[t - MIN_TIER] : null;
            String where = t == 2 ? "T2: the spawn pockets." : t == 3 ? "T3: most land; today's pack."
                    : t == 4 ? "T4: hard." : t == 5 ? "T5: very difficult (hot zones)." : t == 6
                    ? "T6: beyond (the outer sea and ring; the outskirts start here)."
                    : "T" + t + ": the outskirts far beyond the grid, and caves under T" + (t - 1) + ".";
            c.addCustomCategoryComment(cat, where + " Every value defaults to no change.");
            s.spawnKeep = num(c, cat, "spawnKeep", 1.0, 0, 1,
                    "Share of natural spawn attempts kept (the rest are refused). Thins low tiers.", p, 1);
            s.health = num(c, cat, "health", 1.0, 0.01, 100,
                    "Max-health multiplier, on top of everything else (MobProperties, InfernalMobs).", p, 2);
            s.damage = num(c, cat, "damage", 1.0, 0, 100,
                    "Multiplier on damage the mob deals (melee, projectiles, explosions).", p, 3);
            s.eliteOdds = num(c, cat, "eliteOdds", 1.0, 0, 100,
                    "Multiplier on InfernalMobs' chance that a spawn becomes an elite (1 in eliteRarity).", p, 4);
            s.xp = num(c, cat, "xp", 1.0, 0, 100, "Multiplier on the experience the mob drops.", p, 5);
            s.speed = num(c, cat, "speed", 1.0, 0.1, 10,
                    "Movement-speed multiplier. The author's rule: only T6 (and above) is faster.", p, 6);
            s.armourIgnore = num(c, cat, "armourIgnore", 0.0, 0, 1,
                    "Share (0-1) of the mob's damage that ignores armour. The author's rule: T6 only.", p, 7);
            k.tiers[t] = s;
        }
        if (c.hasChanged()) c.save();
        return k;
    }

    private static double num(Configuration c, String cat, String key, double def, double min, double max,
                              String what, String[] proposed, int col) {
        String comment = what + "\nProposed starting point (not applied): "
                + (proposed != null ? proposed[col] : "none yet") + ".";
        Property p = c.get(cat, key, def, comment, min, max);
        double v = p.getDouble(def);
        if (Double.isNaN(v) || v < min || v > max) v = def;
        return v;
    }
}
