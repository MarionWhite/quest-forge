package com.questforge.content.ench;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Remembers which block positions have already been duplicated, so Bountiful
 * cannot be farmed.
 *
 * Without this the loop is trivial: break a block, get two, place one back, break
 * it again. Recording the position closes it -- the same spot only pays out once.
 *
 * Bounded two ways, because this is written to on every qualifying block break and
 * must never grow without limit: entries expire after a while, and the map itself
 * is capped with the oldest evicted first.
 */
public class DuplicationMemory {

    /** How long a position stays spent. Five minutes at 20 ticks per second. */
    private static final long EXPIRY_TICKS = 6000L;

    private static final int MAX_ENTRIES = 8192;

    /** Access-ordered so eviction drops the least recently touched entry. */
    private static final LinkedHashMap<Long, Long> SEEN =
            new LinkedHashMap<Long, Long>(256, 0.75F, true) {
                private static final long serialVersionUID = 1L;

                @Override
                protected boolean removeEldestEntry(Map.Entry<Long, Long> eldest) {
                    return size() > MAX_ENTRIES;
                }
            };

    /**
     * @return true if this position has not been duplicated recently, in which case
     *         it is now recorded as spent.
     */
    public static boolean claim(int dimension, int x, int y, int z, long worldTime) {
        Long key = Long.valueOf(key(dimension, x, y, z));

        Long spentAt = SEEN.get(key);
        if (spentAt != null && (worldTime - spentAt.longValue()) < EXPIRY_TICKS) {
            return false;
        }

        SEEN.put(key, Long.valueOf(worldTime));
        return true;
    }

    /**
     * Packs a dimension and a block position into one long.
     *
     * Y is 8 bits (0-255), X and Z are 26 each, which covers +/-33 million blocks --
     * past the vanilla world border. The dimension takes the remaining 4 bits, so
     * dimension ids outside 0-15 collide; that only means an occasional missed
     * duplication in an exotic dimension, never a wrong drop.
     */
    private static long key(int dimension, int x, int y, int z) {
        return ((long) (dimension & 0xF) << 60)
                | ((long) (x & 0x3FFFFFF) << 34)
                | ((long) (z & 0x3FFFFFF) << 8)
                | (long) (y & 0xFF);
    }
}
