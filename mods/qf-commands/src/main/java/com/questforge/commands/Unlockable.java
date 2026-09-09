package com.questforge.commands;

import net.minecraft.entity.player.EntityPlayerMP;

/**
 * One command a player can earn, and the ticket that grants it.
 *
 * Everything about a command lives in one of these: what it is called, what the
 * ticket says, and what happens when it runs. Adding a command is adding an
 * entry to {@link Unlockables}, not writing another CommandBase and remembering
 * to register it in three places.
 *
 * <h3>The id is permanent</h3>
 *
 * {@link #id} is what gets written into the player's save when they consume a
 * ticket. Renaming one silently revokes the command from everyone who already
 * earned it, so it is deliberately separate from {@link #commands}, which is
 * only what they type and can be changed freely.
 *
 * <h3>One ticket can carry several commands</h3>
 *
 * A home is not a home without both halves -- setting one and going to it are
 * the same idea, and splitting them across two tickets would mean finding one
 * and being unable to use it. So an entry names as many commands as it needs;
 * they share a single id, so a single ticket unlocks all of them, and
 * {@link #run} is told which one was typed.
 */
public abstract class Unlockable {

    /** Stable key stored in the player's unlocks. Never rename one in place. */
    public final String id;

    /** What the player types, without the slash. The first is the primary. */
    public final String[] commands;

    /** Shown as the ticket's name, e.g. "Lottery Ticket: The Nether". */
    public final String title;

    /**
     * What the ticket explains, one entry per line.
     *
     * These are read by someone holding a rare item and deciding whether to use
     * it, so they say what the command does, what it costs, and what its limits
     * are -- not just its name over again.
     */
    public final String[] description;

    protected Unlockable(String id, String[] commands, String title, String... description) {
        this.id = id;
        this.commands = commands;
        this.title = title;
        this.description = description;
    }

    protected Unlockable(String id, String command, String title, String... description) {
        this(id, new String[] { command }, title, description);
    }

    /** The name this entry is listed and described under. */
    public String command() {
        return this.commands[0];
    }

    /**
     * Runs the command for a player who has already been checked for the unlock.
     *
     * @param name the command actually typed, which is what separates /home
     *             from /sethome
     * @param args everything after the command word
     * @return a message to show the player, or null to say nothing
     */
    public abstract String run(EntityPlayerMP player, String name, String[] args);

    /**
     * Whether this can run right now, beyond simply being unlocked.
     *
     * Returning a string refuses with that reason; null allows it. Used for
     * conditions that are true of the moment rather than of the player -- being
     * in the wrong place, or already being where the command would send them.
     */
    public String refuse(EntityPlayerMP player, String name, String[] args) {
        return null;
    }
}
