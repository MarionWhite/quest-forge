package com.questforge.content.jukebox;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Which speaker's music is loaded, and what every other one was left playing.
 *
 * A jukebox and every JBL a player owns each have a queue of their own, but only one
 * of them is ever sounding: there is a single audio pipeline, and only the speaker in
 * your hand is allowed to play. So rather than making {@link Queue} into something
 * instanced -- which would mean threading an owner through every call that touches
 * playback -- the one queue is swapped. Opening a speaker files away whatever was
 * loaded under its owner's name and unpacks that speaker's own list.
 *
 * The upshot is what you would expect from carrying several speakers: each remembers
 * where it was, switching between them does not disturb any of them, and the jukebox
 * on the wall keeps its queue while you walk around with a different one.
 *
 * This is client-side and lasts for the session. A queue is listening state, not
 * property: it is not written into the item, so handing a JBL to someone hands over
 * the speaker and not your playlist -- records are the thing that carries music
 * between players.
 */
public final class Speakers {

    /** The queue that belongs to a wall jukebox rather than to any speaker. */
    private static final String BLOCK = "";

    private static final class State {
        final List<Track> items;
        final int position;

        State(List<Track> items, int position) {
            this.items = items;
            this.position = position;
        }
    }

    private static final Map<String, State> parked = new HashMap<String, State>();

    /** The speaker whose queue is loaded, or null while a jukebox owns it. */
    private static String active;

    private Speakers() { }

    public static String active() { return active; }

    public static boolean isSpeaker() { return active != null; }

    /** True when this is the speaker currently loaded. */
    public static boolean isActive(String id) {
        return id != null && id.equals(active);
    }

    // ------------------------------------------------------------------
    // Switching
    // ------------------------------------------------------------------

    /**
     * Loads a speaker's queue, filing away whatever was loaded before it.
     *
     * Playback stops on the way through. Carrying the previous speaker's track over
     * into this one's queue would leave the two disagreeing about what is playing,
     * and the position index would be pointing into a list that no longer holds it.
     */
    public static void open(String id) {
        if (id == null || id.equals(active)) return;
        park();
        active = id;
        unpark(id);
    }

    /** Hands the queue back to a jukebox. */
    public static void openBlock() {
        if (active == null) return;
        park();
        active = null;
        unpark(BLOCK);
    }

    private static void park() {
        parked.put(active == null ? BLOCK : active,
                   new State(Queue.items(), Queue.position()));
    }

    private static void unpark(String key) {
        Playback.stop();
        Playback.forget();
        State state = parked.get(key);
        if (state == null) Queue.restore(new ArrayList<Track>(), -1);
        else Queue.restore(state.items, state.position);
    }

    /**
     * Forgets a speaker that no longer exists, so a queue cannot outlive the item
     * it belonged to and quietly come back on a newly crafted one.
     */
    public static void discard(String id) {
        if (id == null) return;
        parked.remove(id);
        if (id.equals(active)) {
            active = null;
            Queue.restore(new ArrayList<Track>(), -1);
        }
    }
}
