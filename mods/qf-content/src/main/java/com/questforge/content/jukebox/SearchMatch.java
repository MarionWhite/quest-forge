package com.questforge.content.jukebox;

/**
 * How a typed query is matched against a track.
 *
 * Substring matching on the whole query, which is what this replaced, fails the
 * two things people actually type. "nirvana teen spirit" never matches
 * "Smells Like Teen Spirit" by Nirvana, because the words are split across the
 * artist and the title and are not in that order. And one slipped key means no
 * results at all, with nothing to suggest why.
 *
 * So a query is split into words and each is scored independently against the
 * title, artist and album. Word order stops mattering, mixing an artist with a
 * song works, and a near-miss still counts -- just for fewer points than an exact
 * hit, so correct spellings still win.
 */
public final class SearchMatch {

    /** Points for an exact word hit. Artist counts for most: it is the surest signal. */
    private static final int ARTIST_WEIGHT = 5;
    private static final int TITLE_WEIGHT = 4;
    private static final int ALBUM_WEIGHT = 2;

    /** Awarded when every word typed was found somewhere. */
    private static final int COMPLETE_BONUS = 6;

    /** Taken off for each word that could not be found at all. */
    private static final int MISS_PENALTY = 3;

    private SearchMatch() { }

    /** Splits a query into lowercase words, dropping punctuation. */
    public static String[] tokenize(String query) {
        if (query == null) return new String[0];
        String[] raw = query.toLowerCase().split("[^a-z0-9']+");

        int kept = 0;
        for (String r : raw) if (!r.isEmpty()) kept++;

        String[] out = new String[kept];
        int i = 0;
        for (String r : raw) if (!r.isEmpty()) out[i++] = r;
        return out;
    }

    /**
     * How well a track answers the query. Higher is better; at or below zero means
     * it is not a real answer.
     */
    public static int score(String[] tokens, String title, String artist, String album) {
        if (tokens.length == 0) return 0;

        String[] titleWords = words(title);
        String[] artistWords = words(artist);
        String[] albumWords = words(album);

        int total = 0;
        int matched = 0;

        for (String token : tokens) {
            int best = bestIn(token, artistWords, ARTIST_WEIGHT);
            int t = bestIn(token, titleWords, TITLE_WEIGHT);
            if (t > best) best = t;
            int a = bestIn(token, albumWords, ALBUM_WEIGHT);
            if (a > best) best = a;

            if (best > 0) {
                matched++;
                total += best;
            } else {
                total -= MISS_PENALTY;
            }
        }

        if (matched == tokens.length) total += COMPLETE_BONUS;
        return total;
    }

    /** True when every word typed was found, allowing for typos. */
    public static boolean matchesAll(String[] tokens, String title, String artist, String album) {
        if (tokens.length == 0) return true;

        String[] titleWords = words(title);
        String[] artistWords = words(artist);
        String[] albumWords = words(album);

        for (String token : tokens) {
            if (bestIn(token, artistWords, ARTIST_WEIGHT) == 0
                    && bestIn(token, titleWords, TITLE_WEIGHT) == 0
                    && bestIn(token, albumWords, ALBUM_WEIGHT) == 0) {
                return false;
            }
        }
        return true;
    }

    /**
     * Best score for one word against one field, cheapest test first.
     *
     * The ladder matters: an exact hit must outrank a prefix, which must outrank a
     * typo, or a fuzzy match on a common word would drown the track someone
     * actually spelled correctly.
     */
    private static int bestIn(String token, String[] words, int weight) {
        int best = 0;
        for (String w : words) {
            if (w.equals(token)) return weight;
            if (token.length() >= 3 && w.length() > token.length() && w.startsWith(token)) {
                if (weight - 1 > best) best = weight - 1;
            } else if (token.length() >= 4 && w.contains(token)) {
                if (weight - 2 > best) best = weight - 2;
            }
        }
        if (best > 0) return best;

        // Only now, having found nothing cleaner, allow for mistyping.
        int allowed = allowedEdits(token);
        if (allowed == 0) return 0;

        for (String w : words) {
            if (Math.abs(w.length() - token.length()) > allowed) continue;
            if (within(w, token, allowed)) return Math.max(1, weight - 3);
        }
        return 0;
    }

    /**
     * How far off a word may be and still count.
     *
     * Short words get no leeway: at three letters almost everything is within one
     * edit of everything else, and allowing it turns every search into noise.
     */
    private static int allowedEdits(String token) {
        if (token.length() <= 3) return 0;
        if (token.length() <= 6) return 1;
        return 2;
    }

    /**
     * Levenshtein distance, abandoned as soon as it cannot come in under the limit.
     * Two rolling rows rather than a full matrix, since only the previous one is
     * ever read.
     */
    private static boolean within(String a, String b, int limit) {
        int la = a.length(), lb = b.length();
        if (Math.abs(la - lb) > limit) return false;

        int[] previous = new int[lb + 1];
        int[] current = new int[lb + 1];
        for (int j = 0; j <= lb; j++) previous[j] = j;

        for (int i = 1; i <= la; i++) {
            current[0] = i;
            int rowBest = current[0];
            char ca = a.charAt(i - 1);

            for (int j = 1; j <= lb; j++) {
                int cost = ca == b.charAt(j - 1) ? 0 : 1;
                int value = Math.min(Math.min(current[j - 1] + 1, previous[j] + 1),
                                     previous[j - 1] + cost);
                current[j] = value;
                if (value < rowBest) rowBest = value;
            }
            // Nothing further along this row can drop below its own minimum.
            if (rowBest > limit) return false;

            int[] swap = previous;
            previous = current;
            current = swap;
        }
        return previous[lb] <= limit;
    }

    /** Field split into lowercase words. */
    private static String[] words(String field) {
        if (field == null || field.isEmpty()) return new String[0];
        return tokenize(field);
    }
}
