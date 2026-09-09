package com.questforge.content.client;

import java.util.HashMap;
import java.util.Map;

import net.minecraft.util.ResourceLocation;

/**
 * Which loading plate belongs to which dimension.
 *
 * The art is 27 cinematic 16:9 stills, one per dimension the pack can send you
 * to, produced in tools/branding/loading-plates. They were finished and then sat
 * unused: nothing shipped them and nothing drew them.
 *
 * The table is written out rather than derived from the file names because the
 * mapping is the interesting part and it is not guessable -- Ilum is 32 and
 * Korriban is 35 because that is how the Legends mod registered them, and a
 * renamed file should not silently point a dimension at someone else's art.
 * Dimension ids are from the plate table in that directory's README.
 *
 * The overworld deliberately has no plate. You see it on first join, before any
 * of this is interesting, and a still of plains would say nothing.
 */
public final class LoadingPlates {

    private static final String PATH = "qfcontent:textures/gui/loading/";

    /** Dimension id to plate file, and to the name drawn over it. */
    private static final Map<Integer, String[]> PLATES = new HashMap<Integer, String[]>();

    static {
        put(-1, "01-nether", "The Nether");
        put(1, "02-end", "The End");
        put(7, "03-twilight-forest", "Twilight Forest");
        put(-37, "04-dream-world", "Dream World");
        put(-38, "05-torment", "Torment");
        put(-39, "06-mirror-world", "Mirror World");
        put(-42, "07-lost-world", "The Lost World");
        put(4, "08-compact-machines", "Compact Machines");
        put(30, "09-outer-space", "Outer Space");
        put(31, "10-mars", "Mars");
        put(32, "11-ilum", "Ilum");
        put(33, "12-hurikane", "Hurikane");
        put(34, "13-tython", "Tython");
        put(35, "14-korriban", "Korriban");
        put(36, "15-tatooine", "Tatooine");
        put(50, "16-speed-force", "Speed Force");
        put(51, "17-wakanda", "Wakanda");
        put(53, "18-kingpin", "Kingpin Takedown");
        put(55, "19-quantum-realm", "Quantum Realm");
        put(58, "20-imortus", "Imortus");
        put(66, "21-underworld", "The Underworld");
        put(80, "22-utopia", "Utopia");
        put(81, "23-mining", "Extreme Mining");
        put(82, "24-village-mania", "Village Mania");
        put(83, "25-danger-islands", "Danger Islands");
        put(84, "26-crystal", "Crystal");
        put(85, "27-chaos", "Chaos");
    }

    private static final Map<Integer, ResourceLocation> CACHE =
            new HashMap<Integer, ResourceLocation>();

    private LoadingPlates() {
    }

    private static void put(int dimension, String file, String name) {
        PLATES.put(Integer.valueOf(dimension), new String[] { file, name });
    }

    /** The plate for a dimension, or null if it has none. */
    public static ResourceLocation texture(int dimension) {
        Integer key = Integer.valueOf(dimension);
        ResourceLocation cached = CACHE.get(key);

        if (cached != null) {
            return cached;
        }

        String[] entry = PLATES.get(key);

        if (entry == null) {
            return null;
        }

        ResourceLocation made = new ResourceLocation(PATH + entry[0] + ".jpg");
        CACHE.put(key, made);
        return made;
    }

    /** The name drawn over the plate, or null if the dimension has none. */
    public static String name(int dimension) {
        String[] entry = PLATES.get(Integer.valueOf(dimension));
        return entry == null ? null : entry[1];
    }

    /** How many dimensions have art. Used by the pack verifier. */
    public static int count() {
        return PLATES.size();
    }
}
