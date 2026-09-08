package com.questforge.content.jukebox;

import java.util.ArrayList;
import java.util.List;

/**
 * What plays next.
 *
 * Kept deliberately separate from {@link Playback}, which knows how to get one
 * track sounding and nothing else. This decides which track that should be, so
 * finishing a song, pressing skip and queueing something up while another track
 * plays all run through the same short path.
 *
 * The queue holds the track that is playing as well as the ones waiting, so the
 * player can see where they are in it and step backwards, the way any music player
 * behaves. Position is an index into that list rather than a separate "history".
 */
public final class Queue {

    private static final List<Track> items = new ArrayList<Track>();

    /** Index of the track currently playing, or -1 when the queue is not driving. */
    private static int position = -1;

    private Queue() { }

    public static List<Track> items() { return new ArrayList<Track>(items); }
    public static int size() { return items.size(); }
    public static int position() { return position; }
    public static boolean isEmpty() { return items.isEmpty(); }

    public static Track current() {
        return position >= 0 && position < items.size() ? items.get(position) : null;
    }

    /**
     * Plays a track picked from anywhere in the browser, right now.
     *
     * The rest of the queue survives, which is the whole difference from clearing
     * it: picking a song out of a search is a decision about what to hear next,
     * not an instruction to throw away everything lined up behind it. What was
     * playing is dropped -- it has been skipped away from, and leaving it above the
     * new track would make Previous walk straight back into it -- and the new track
     * takes its slot, so whatever was waiting still plays in order afterwards.
     */
    public static void playImmediately(Track track, double x, double y, double z) {
        int slot = items.size();
        if (position >= 0 && position < items.size()) {
            slot = position;
            items.remove(slot);
        }
        items.add(slot, track);
        position = slot;
        Playback.play(track, x, y, z);
    }

    /**
     * Plays an entry already in the queue, dropping whatever was playing. Clicking
     * a row in the queue view means the same thing as clicking one in a search:
     * play this, and let the rest follow.
     */
    public static void playFromQueue(int index, double x, double y, double z) {
        if (index < 0 || index >= items.size()) return;

        if (position >= 0 && position < items.size() && position != index) {
            items.remove(position);
            if (position < index) index--;
        }
        position = index;
        Playback.play(items.get(index), x, y, z);
    }

    /** Plays a whole list from the top, replacing what was queued. */
    public static void replaceWith(List<Track> tracks, double x, double y, double z) {
        if (tracks == null || tracks.isEmpty()) return;
        items.clear();
        items.addAll(tracks);
        position = 0;
        Playback.play(items.get(0), x, y, z);
    }

    /**
     * Takes the playing entry out and stops driving, leaving the rest waiting.
     * What the Clear Song button does -- clearing the whole queue from a control
     * sitting next to Play was never what anyone meant by pressing it.
     */
    public static void dropCurrent() {
        if (position >= 0 && position < items.size()) {
            items.remove(position);
            // Step back one so Next plays what followed rather than restarting the
            // queue from the top: after the removal, that track sits where the
            // cleared one was.
            position--;
        } else {
            position = -1;
        }
    }

    /** Adds to the end without disturbing what is playing. */
    public static void add(Track track) {
        items.add(track);
    }

    /** Slots in directly after the current track. */
    public static void playNext(Track track) {
        if (position < 0 || items.isEmpty()) items.add(track);
        else items.add(Math.min(position + 1, items.size()), track);
    }

    /** Queues a whole playlist, keeping its order. */
    public static void addAll(List<Track> tracks) {
        for (int i = 0; i < tracks.size(); i++) items.add(tracks.get(i));
    }

    /**
     * Starts playing a queue from one of its entries -- clicking a row in the
     * queue view.
     */
    public static void jumpTo(int index, double x, double y, double z) {
        if (index < 0 || index >= items.size()) return;
        position = index;
        Playback.play(items.get(index), x, y, z);
    }

    public static void remove(int index) {
        if (index < 0 || index >= items.size()) return;
        items.remove(index);
        // Keep pointing at the same track after something above it disappears.
        if (index < position) position--;
        else if (index == position) position--;
    }

    public static void clear() {
        items.clear();
        position = -1;
    }

    /** Moves an entry one place up or down, for reordering by hand. */
    public static void move(int index, int delta) {
        int target = index + delta;
        if (index < 0 || index >= items.size() || target < 0 || target >= items.size()) return;

        Track t = items.remove(index);
        items.add(target, t);

        if (position == index) position = target;
        else if (position == target) position = index;
    }

    public static boolean hasNext() { return position + 1 < items.size(); }
    public static boolean hasPrevious() { return position > 0; }

    /** Advances and plays. Returns false when the queue has run out. */
    public static boolean next(double x, double y, double z) {
        if (!hasNext()) return false;
        position++;
        Playback.play(items.get(position), x, y, z);
        return true;
    }

    public static boolean previous(double x, double y, double z) {
        if (!hasPrevious()) return false;
        position--;
        Playback.play(items.get(position), x, y, z);
        return true;
    }

    /**
     * Called when a track ends by itself. Looping a single track is handled in
     * {@link Playback}; this only runs when the queue should move on.
     */
    static boolean advanceOnFinish(double x, double y, double z) {
        return next(x, y, z);
    }

    /**
     * Replaces the whole queue in one go, for {@link Speakers} swapping one owner's
     * list out for another's.
     *
     * Nothing is played and nothing is stopped here: which of those should happen
     * belongs to whoever is doing the swapping, not to the list itself.
     */
    static void restore(List<Track> saved, int at) {
        items.clear();
        if (saved != null) items.addAll(saved);
        position = at >= 0 && at < items.size() ? at : -1;
    }
}
