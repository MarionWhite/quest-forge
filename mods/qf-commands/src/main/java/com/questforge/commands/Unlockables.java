package com.questforge.commands;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Every command a ticket can grant.
 *
 * This is the whole configuration surface. Adding a command means adding one
 * entry here; the item, the tooltip, the /commands listing, the command itself
 * and the loot entry all follow from it.
 *
 * <h3>Order is frozen</h3>
 *
 * A ticket's damage value is its position in this list, so reordering or
 * inserting reassigns every ticket already sitting in a chest. Append new
 * entries at the end. The <em>unlocks</em> a player owns are stored by
 * {@link Unlockable#id} and are safe to reorder -- it is only the item that is
 * positional.
 */
public final class Unlockables {

    /**
     * <em>Where</em> a ticket is found. Not how often -- every ticket is rare,
     * and the drop rates live in TicketLoot.
     *
     * The distinction is the point of the dimension tickets. A dimension you can
     * reach by ordinary means gets a ticket that can turn up anywhere. A
     * dimension the pack gates behind a quest line gets its ticket only
     * <em>inside itself</em> -- so the command can never skip the quest, and
     * what it actually buys is never having to do the journey twice.
     */
    public enum Source {
        /**
         * Rare in overworld loot: dungeons, strongholds, villages, mineshafts.
         * Named for the place, not the odds -- these are as rare as the rest.
         */
        WORLD_LOOT,

        /** Rare inside its own dimension only, from bosses and what lives there. */
        IN_DIMENSION,

        /** Not in loot at all. Given, or granted by an operator. */
        NONE
    }

    private static final List<Unlockable> ALL = new ArrayList<Unlockable>();
    private static final Map<String, Unlockable> BY_ID = new HashMap<String, Unlockable>();
    private static final Map<String, Source> SOURCES = new HashMap<String, Source>();

    private Unlockables() {
    }

    static {
        // ------------------------------------------------------------------
        // Utility
        // ------------------------------------------------------------------

        add(new VaultAccess(), Source.WORLD_LOOT);
        add(new HomeAccess(), Source.WORLD_LOOT);

        // ==================================================================
        // Dimensions
        // ==================================================================
        //
        // Which of these is IN_DIMENSION is not a guess. The pack says so
        // itself, in three places that agree:
        //
        //   1. Quest #73, "Dimensional Traveler" -- "a brick from every sky the
        //      pack actually has" -- asks for a souvenir from exactly seven
        //      worlds: the Nether, Twilight Forest, the End, the Crystal
        //      Dimension, the Synapse, the Dream World and the Lost World.
        //
        //   2. The numbered chapters are the pack's spine, and five of them are
        //      built around reaching somewhere: Ch 3 Twilight, Ch 5 Dark Paths
        //      (Witchery's three), Ch 6 The End, Ch 7 OreSpawn (Crystal) and
        //      Ch 8 TragicMC (the Synapse key chain).
        //
        //   3. Several quests are about the journey itself, and gate it behind
        //      earlier work: #14 builds the Twilight portal, #45 the Spirit
        //      Portal, #107 the road to Torment, #108 the Dreamworld, #122 the
        //      Crystal portal ("waits until the Queen is a receipt"), #134 the
        //      Synapse Dimensional Key.
        //
        // Everything else is reached by crafting a thing and using it, with no
        // questbook step attached. The Legends dimensions are the clearest
        // case: thirteen worlds, no questbook mention anywhere, and entry is a
        // console purchase or a mod ability. Quest #433 draws the same line
        // inside OreSpawn in the author's own words -- the sky dimensions are
        // "the commute", and "Crystal is later".
        //
        // Ordered to match the loading plates in qf-content, then the two
        // TragicMC dimensions, which have no plate art yet.
        // ------------------------------------------------------------------

        // -- Vanilla and vanilla-adjacent ----------------------------------

        // The way back. Every other dimension ticket is a way out of the
        // Overworld and none of them was a way home, which made a one-way trip
        // out of anything you could not build a return portal for.
        dim("overworld", 0, "The Overworld", Source.WORLD_LOOT,
            "walking back through whatever door you came out of");

        dim("nether", -1, "The Nether", Source.WORLD_LOOT,
            "a frame of obsidian, lit with flint and steel");

        // Ch 6, thirteen quests, and the whole of Hardcore Ender Expansion
        // sits behind the same twelve eyes.
        dim("end", 1, "The End", Source.IN_DIMENSION,
            "a stronghold's portal, filled with eyes of ender");

        // -- Twilight Forest -----------------------------------------------

        // Ch 3, fifteen quests. Quest #14 is the portal ritual itself, gated
        // behind Diamond Gear: the pack made building it a step, so a ticket in
        // world loot would sell that step.
        dim("twilight_forest", 7, "Twilight Forest", Source.IN_DIMENSION,
            "a flower-ringed pool, with a diamond thrown in");

        // -- Witchery, Ch 5: Dark Paths ------------------------------------
        //
        // A chain, not three separate doors: the Circle Talisman opens the
        // Spirit World, the Spirit World opens the Dreamworld, and Leonard's
        // Bargain opens the road to Torment. Witchery's config calls the third
        // one the Mirror dimension; the game and the questbook both call it the
        // Spirit World, so the ticket does too.

        dim("dream_world", -37, "Dream World", Source.IN_DIMENSION,
            "a Dream Weaver hung over your bed, and sleep");

        dim("torment", -38, "Torment", Source.IN_DIMENSION,
            "a Brazier, a Demon Heart, and an infernal rite");

        dim("spirit_world", -39, "The Spirit World", Source.IN_DIMENSION,
            "a Spirit Portal, built after the Circle Talisman");

        // -- Welcome to the Jungle -----------------------------------------

        // Danger Zone: #420 Soul Sapphire, then #421 The Book of Scale, whose
        // text says outright that "the Lost World portal is later, and it wants
        // the ceremonial kit". The sapphire is one of the seven souvenirs.
        dim("lost_world", -42, "The Lost World", Source.IN_DIMENSION,
            "the Saur-Ohn portal and its ceremonial kit");

        // -- Compact Machines ----------------------------------------------

        // No ticket. The dimension is a backing store for your own machines --
        // a grid of cubes with void between them -- so there is nowhere to
        // arrive that is not either inside someone's machine or a long fall.
        // The command stays for operators; nothing hands it out.
        dim("compact_machines", 4, "Compact Machines", Source.NONE,
            "a Personal Shrinking Device, used on your own machine");

        // -- The Legends Mod -----------------------------------------------
        //
        // Thirteen dimensions, and the questbook mentions none of them. Entry
        // is a Galactic Console block and a credit balance, or a mod ability
        // holding a door open. That is the Legends mod's own economy, not the
        // pack's progression, so a ticket here skips a purchase rather than a
        // quest line.

        // No ticket. Outer Space is the void it is named after: its chunk
        // provider writes one block where Mars writes eleven, and what you can
        // stand on there was placed as a structure. The Galactic Console flies
        // you onto one; a teleport that only knows coordinates cannot find
        // them, so the command refuses far more often than it works.
        dim("outer_space", 30, "Outer Space", Source.NONE,
            "the Galactic Console");
        dim("mars", 31, "Mars", Source.WORLD_LOOT,
            "the Galactic Console, for 100 credits");
        dim("ilum", 32, "Ilum", Source.WORLD_LOOT,
            "the Galactic Console, for 1000 credits");
        dim("hurikane", 33, "Hurikane", Source.WORLD_LOOT,
            "the Galactic Console, for 2000 credits");
        dim("tython", 34, "Tython", Source.WORLD_LOOT,
            "the Galactic Console, for 25 credits");
        dim("korriban", 35, "Korriban", Source.WORLD_LOOT,
            "the Galactic Console, for 25 credits");
        dim("tatooine", 36, "Tatooine", Source.WORLD_LOOT,
            "the Galactic Console, for 500 credits");
        dim("speed_force", 50, "Speed Force", Source.WORLD_LOOT,
            "a speedster's own power, tearing a portal open");
        dim("wakanda", 51, "Wakanda", Source.WORLD_LOOT,
            "a Wakandan Map");
        // No ticket, for the same reason: the arena is built when its fight
        // starts and is an empty shell the rest of the time.
        dim("kingpin", 53, "Kingpin Takedown", Source.NONE,
            "starting the Kingpin Takedown boss battle");
        dim("quantum_realm", 55, "Quantum Realm", Source.WORLD_LOOT,
            "Pym Particles, and shrinking past the limit");
        dim("imortus", 58, "Imortus", Source.WORLD_LOOT,
            "the Legends mod's own route");
        dim("underworld", 66, "The Underworld", Source.WORLD_LOOT,
            "the Legends mod's own route");

        // -- OreSpawn --------------------------------------------------------
        //
        // Six dimensions, all entered the same way: a portal frame built from
        // that dimension's own block. Quest #433 separates them for us -- the
        // sky dimensions are "the commute", reachable straight after First
        // Contact, while "Crystal is later, and it waits until the Queen is a
        // receipt". Only Crystal is gated, and #122 gates it behind #24.

        dim("utopia", 80, "Utopia", Source.WORLD_LOOT,
            "an OreSpawn portal frame of that world's own block");
        dim("mining", 81, "Extreme Mining", Source.WORLD_LOOT,
            "an OreSpawn portal frame of that world's own block");
        dim("village_mania", 82, "Village Mania", Source.WORLD_LOOT,
            "an OreSpawn portal frame of that world's own block");
        dim("danger_islands", 83, "Danger Islands", Source.WORLD_LOOT,
            "an OreSpawn portal frame of that world's own block");

        dim("crystal", 84, "Crystal", Source.IN_DIMENSION,
            "a portal frame of crystal blocks, after the Queen");

        dim("chaos", 85, "Chaos", Source.WORLD_LOOT,
            "an OreSpawn portal frame of that world's own block");

        // -- TragicMC, Ch 8 --------------------------------------------------
        //
        // Appended after the plate-ordered block because neither has loading
        // plate art yet. The Synapse is one of the seven souvenirs in #73 and
        // the end of a four-quest chain (#131 crystal, #132 core, #133 link,
        // #134 key); the Collision is opened by a key from the same family,
        // forged off the same chain.

        dim("synapse", 3, "The Synapse", Source.IN_DIMENSION,
            "a Synapse Dimensional Key, used on open ground");
        dim("collision", 2, "The Collision", Source.IN_DIMENSION,
            "a Collision Dimensional Key, used on open ground");
    }

    /**
     * @param entry how a player would normally arrive, phrased to follow
     *              "Normally reached by". The tooltip says what the ticket is a
     *              substitute for, which is the only way to judge whether you
     *              want to spend it here or keep it.
     */
    private static void dim(String command, int dimension, String title, Source source,
                            String entry) {
        String[] where;

        switch (source) {
        case IN_DIMENSION:
            where = new String[] {
                "A rare find inside " + title + " itself, and nowhere",
                "else -- so it is a way back and never a way in.",
                "Arriving the first time is a step the questbook",
                "gates, and nothing here can skip it." };
            break;

        case NONE:
            where = new String[] {
                "There is no ticket for this. " + title + " has nowhere",
                "solid to arrive at, so the command only ever refuses and",
                "is left to operators. If you are holding this, someone",
                "made it on purpose -- it cannot be redeemed." };
            break;

        default:
            where = new String[] {
                "A rare find in world loot: dungeons, mineshafts,",
                "strongholds. The questbook gates nothing on reaching",
                title + ", so this saves the trip rather than",
                "skipping a quest." };
            break;
        }

        List<String> lines = new ArrayList<String>();
        lines.add("Travel to " + title + " from anywhere.");
        lines.add("");
        lines.add("You arrive standing on solid ground. Nothing is built,");
        lines.add("no portal is opened, and nothing is consumed.");
        lines.add("");
        lines.add("Normally reached by " + entry + ".");
        lines.add("");
        Collections.addAll(lines, where);

        // Said on the item, not only in the chat message after redeeming, so it
        // is knowable before spending the ticket rather than after.
        if (dimension != 0) {
            lines.add("");
            lines.add("Your first dimension ticket also grants /overworld,");
            lines.add("so this cannot leave you stranded.");
        }

        add(new DimensionTravel("dim." + command, command, dimension, title,
                lines.toArray(new String[lines.size()])), source);
    }

    private static void add(Unlockable u, Source source) {
        ALL.add(u);
        BY_ID.put(u.id, u);
        SOURCES.put(u.id, source);
    }

    public static List<Unlockable> all() {
        return Collections.unmodifiableList(ALL);
    }

    public static Unlockable byId(String id) {
        return BY_ID.get(id);
    }

    /**
     * The way home.
     *
     * Granted alongside a player's first dimension ticket, wherever that ticket
     * leads. A ticket to somewhere new is not a gift if it is one-way, and
     * being stranded in Torment is a poor reward for finding something rare.
     */
    public static Unlockable wayHome() {
        return byId("dim.overworld");
    }

    /** Registry position, which is what the ticket item's damage value holds. */
    public static int indexOf(Unlockable u) {
        return ALL.indexOf(u);
    }

    public static Unlockable byIndex(int index) {
        return index >= 0 && index < ALL.size() ? ALL.get(index) : null;
    }

    public static Source sourceOf(Unlockable u) {
        Source s = SOURCES.get(u.id);
        return s == null ? Source.NONE : s;
    }

    /**
     * The ticket that may only be found inside the given dimension, if that
     * dimension is one of the gated ones.
     *
     * @return null for a dimension whose ticket is in the world-loot pool, and
     *         for any dimension this mod has no entry for
     */
    public static Unlockable gatedFor(int dimension) {
        for (Unlockable u : ALL) {
            if (u instanceof DimensionTravel
                    && ((DimensionTravel) u).dimension == dimension
                    && sourceOf(u) == Source.IN_DIMENSION) {
                return u;
            }
        }

        return null;
    }

    public static int count() {
        return ALL.size();
    }
}
