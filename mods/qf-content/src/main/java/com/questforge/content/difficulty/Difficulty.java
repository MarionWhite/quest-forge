package com.questforge.content.difficulty;

import java.io.File;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EnumCreatureType;
import net.minecraft.entity.IEntityOwnable;
import net.minecraft.entity.boss.IBossDisplayData;
import net.minecraft.entity.monster.IMob;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.util.MathHelper;
import net.minecraft.world.World;

import com.questforge.content.QuestForgeContent;

/**
 * Difficulty tiers by map position: the state and the lookups.
 *
 * The map is the baked grid in the world folder ({@link TierGrid}); the numbers
 * are {@link DifficultyConfig}. Both are read when the overworld loads on the
 * server and dropped when it unloads. With no grid file {@link #active} is false
 * and every hook returns at once: test worlds, census nodes and today's worlds are
 * untouched. See docs/design/world/r14/difficulty-mechanism.md.
 *
 * A mob's tier is fixed when it first joins the world, from the place it joined,
 * and kept in its ForgeData ({@link #TAG_TIER}), so a T5 mob that chases someone
 * into a spawn pocket stays T5 and a reloaded chunk never rescales anything.
 */
public final class Difficulty {

    public static final String TAG_TIER = "qfTier";
    public static final String TAG_HOW = "qfTierHow";

    private static TierGrid grid;
    private static DifficultyConfig config;
    private static File worldDir;

    private Difficulty() {}

    /** True when a grid is loaded and the feature is switched on. */
    public static boolean active() {
        return grid != null && config != null && config.enabled;
    }

    public static TierGrid grid() {
        return grid;
    }

    public static DifficultyConfig config() {
        return config;
    }

    static File configFile() {
        return new File(QuestForgeContent.configDir(), "qfcontent-difficulty.cfg");
    }

    /** Called when the overworld loads on the server: read the config and the grid, if there is one. */
    static void load(File dir) {
        worldDir = dir;
        reload();
    }

    /** Re-reads both files (also /qfdifficulty reload). Returns a one-line summary. */
    public static String reload() {
        grid = null;
        config = null;
        if (worldDir == null) return "no world loaded";
        DifficultyConfig k;
        try {
            k = DifficultyConfig.load(configFile());
        } catch (Throwable t) {
            QuestForgeContent.log.error("[difficulty] cannot read " + configFile() + "; tiers off", t);
            return "config unreadable; tiers off";
        }
        File f = new File(worldDir, k.gridFile);
        if (!f.isFile()) {
            QuestForgeContent.log.info("[difficulty] no tier grid at " + f + "; difficulty tiers inactive");
            return "no grid at " + f + "; inactive";
        }
        try {
            grid = TierGrid.read(f);
        } catch (Throwable t) {
            QuestForgeContent.log.error("[difficulty] cannot read the tier grid " + f + "; tiers off", t);
            return "grid unreadable (" + t.getMessage() + "); inactive";
        }
        config = k;
        boolean inert = true;
        for (int t = DifficultyConfig.MIN_TIER; t <= k.maxTier; t++) inert &= k.tiers[t].inert();
        String s = "tier grid " + grid + " from " + f + (k.enabled ? "" : " (disabled in config)")
                + (inert ? "; every tier at defaults (no change to play)" : "; tier settings active");
        QuestForgeContent.log.info("[difficulty] " + s);
        if (!inert) {
            for (int t = DifficultyConfig.MIN_TIER; t <= k.maxTier; t++) {
                if (!k.tiers[t].inert()) QuestForgeContent.log.info("[difficulty]   T" + t + ": " + k.tiers[t]);
            }
        }
        return s;
    }

    static void unload() {
        grid = null;
        config = null;
        worldDir = null;
    }

    /** Where a tier came from. */
    public enum How { GRID, CAVE, OUTSKIRTS, OUTSKIRTS_CAVE, CAGE }

    /** A tier and how it was found. */
    public static final class Where {
        public final int tier;
        public final int gridTier;   // before the cave bonus; -1 outside the grid
        public final How how;
        public final boolean pocket;

        Where(int tier, int gridTier, How how, boolean pocket) {
            this.tier = tier;
            this.gridTier = gridTier;
            this.how = how;
            this.pocket = pocket;
        }

        @Override
        public String toString() {
            return "T" + tier + " (" + how.name().toLowerCase().replace('_', '+')
                    + (gridTier >= 0 ? ", grid T" + gridTier : ", outside the grid") + (pocket ? ", spawn pocket" : "") + ")";
        }
    }

    /** True when the hooks should act in this world. */
    public static boolean appliesTo(World w) {
        return active() && w != null && !w.isRemote && config.dimensions.contains(w.provider.dimensionId);
    }

    /** The tier at a block position, caves included. Only valid when {@link #appliesTo} the world. */
    public static Where tierAt(World w, double x, double y, double z) {
        DifficultyConfig k = config;
        int bx = MathHelper.floor_double(x), by = MathHelper.floor_double(y), bz = MathHelper.floor_double(z);
        int cx = bx >> 4, cz = bz >> 4;
        int base;
        int gridTier = -1;
        boolean outskirts;
        if (grid.contains(cx, cz)) {
            base = gridTier = grid.tierAtChunk(cx, cz);
            outskirts = false;
        } else {
            base = grid.outsideTier;
            if (k.outskirtsStep > 0) base += (int) (grid.blocksOutside(x, z) / k.outskirtsStep);
            outskirts = true;
        }
        int tier = Math.min(base, k.maxTier);
        boolean cave = k.caveBonus > 0 && isCave(w, bx, by, bz, k.caveDepth);
        if (cave) tier = Math.min(tier + k.caveBonus, k.maxTier);
        How how = outskirts ? (cave ? How.OUTSKIRTS_CAVE : How.OUTSKIRTS) : (cave ? How.CAVE : How.GRID);
        boolean pocket = gridTier >= 0 && gridTier <= k.pocketMaxTier;
        return new Where(Math.max(tier, DifficultyConfig.MIN_TIER), gridTier, how, pocket);
    }

    /** No sky access and at least {@code depth} blocks under the column's top solid block. */
    static boolean isCave(World w, int x, int y, int z, int depth) {
        if (y < 0 || y > 255) return false;
        if (w.canBlockSeeTheSky(x, y, z)) return false;
        return y <= w.getTopSolidOrLiquidBlock(x, z) - depth;
    }

    /** Hostile, not a boss, not owned, not excluded: the mobs tiers apply to. */
    public static boolean eligible(Entity e) {
        if (!(e instanceof EntityLiving)) return false;
        if (!(e instanceof IMob) && !e.isCreatureType(EnumCreatureType.monster, false)) return false;
        if (isBoss(e)) return false;
        if (e instanceof IEntityOwnable) {
            IEntityOwnable o = (IEntityOwnable) e;
            if (o.getOwner() != null) return false;
            String owner = o.func_152113_b();
            if (owner != null && !owner.isEmpty()) return false;
        }
        String name = EntityList.getEntityString(e);
        return name == null || !contains(config.excludeNames, name);
    }

    /** Boss health bar, a Lycanites boss, or on the configured list. */
    public static boolean isBoss(Entity e) {
        if (e instanceof IBossDisplayData) return true;
        if (ModHooks.isLycanitesBoss(e)) return true;
        String name = EntityList.getEntityString(e);
        return name != null && config != null && contains(config.bossNames, name);
    }

    private static boolean contains(java.util.Set<String> names, String name) {
        if (names.contains(name)) return true;
        String n = norm(name);
        for (String s : names) if (norm(s).equals(n)) return true;
        return false;
    }

    private static String norm(String s) {
        return s.toLowerCase().replace(" ", "").replace("_", "");
    }

    /** The tier stamped on a mob, or 0 if it has none. */
    public static int stampedTier(Entity e) {
        NBTTagCompound d = e.getEntityData();
        return d.hasKey(TAG_TIER) ? d.getByte(TAG_TIER) : 0;
    }

    static void stamp(Entity e, int tier, How how) {
        NBTTagCompound d = e.getEntityData();
        d.setByte(TAG_TIER, (byte) tier);
        d.setString(TAG_HOW, how.name().toLowerCase());
    }

    /** True when debugLog is on; callers test it before building a message. */
    static boolean debugging() {
        return config != null && config.debugLog;
    }

    static void debug(String s) {
        if (debugging()) QuestForgeContent.log.info("[difficulty] " + s);
    }
}
