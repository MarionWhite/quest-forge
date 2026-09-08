package com.questforge.content.jukebox;

import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagList;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.World;
import net.minecraft.world.WorldSavedData;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * Every tower speaker on the server, filed under the code you pair it with.
 *
 * <h3>Why a registry and not just the block</h3>
 * A jukebox can be paired with a speaker 150 blocks away, and at that distance the
 * speaker is outside the client's loaded chunks -- there is no tile entity anywhere
 * to ask where it is or how loud it should be. Worse, on the server the speaker's
 * chunk may not be loaded either, so a jukebox cannot reach across to read it when
 * someone presses play. Saved data is always loaded, so the record is always
 * answerable, and pairing keeps working whether or not anyone is standing near the
 * speaker.
 *
 * It lives in dimension zero's storage on purpose. Codes have to be unique across
 * the whole server, and per-dimension storage would happily hand out the same code
 * in the Nether that the overworld already used.
 *
 * <h3>Codes are never reused</h3>
 * {@link #issued} keeps every code ever handed out, including those whose speaker
 * has since been broken. Freeing a code would mean a jukebox still holding it could
 * silently re-pair with somebody else's new speaker, which is a strange enough
 * failure that the few bytes a dead code costs are worth it.
 */
public class SpeakerRegistry extends WorldSavedData {

    private static final String KEY = "qf_speakers";

    /**
     * Crockford's alphabet: no I, L, O or U, so a code read off a screen and typed
     * back in cannot become a different valid code through a one/ell mix-up.
     */
    private static final char[] ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ".toCharArray();

    private static final Random RANDOM = new Random();

    /** What a paired speaker is, everywhere outside its own tile entity. */
    public static final class Entry {
        public String code = "";
        public int dim;
        public int x, y, z;
        public String name = "Speaker";
        /** Index into the tower range table. */
        public int range = 2;
        public float volume = 0.85f;
        public float bass, treble;

        /**
         * Who this speaker answers to: "" when unpaired, otherwise an owner key
         * from {@link SpeakerRegistry#blockOwner} or {@link SpeakerRegistry#itemOwner}.
         *
         * The pairing is held here, not on the jukebox, and that is the point. A
         * jukebox derives its device list by asking which speakers name it, so there
         * is exactly one copy of the fact and nothing to keep in step -- which
         * matters because either end can be in an unloaded chunk when the other is
         * being changed.
         */
        public String pairedTo = "";

        /** Whether this speaker is switched on in its owner's device list. */
        public boolean enabled = true;

        public Entry copy() {
            Entry e = new Entry();
            e.code = code; e.dim = dim; e.x = x; e.y = y; e.z = z;
            e.name = name; e.range = range; e.volume = volume;
            e.bass = bass; e.treble = treble;
            e.pairedTo = pairedTo; e.enabled = enabled;
            return e;
        }

        void write(NBTTagCompound tag) {
            tag.setString("Code", code);
            tag.setInteger("Dim", dim);
            tag.setInteger("X", x);
            tag.setInteger("Y", y);
            tag.setInteger("Z", z);
            tag.setString("Name", name);
            tag.setInteger("Range", range);
            tag.setFloat("Vol", volume);
            tag.setFloat("Bass", bass);
            tag.setFloat("Treble", treble);
            tag.setString("Paired", pairedTo);
            tag.setBoolean("On", enabled);
        }

        static Entry read(NBTTagCompound tag) {
            Entry e = new Entry();
            e.code = tag.getString("Code");
            e.dim = tag.getInteger("Dim");
            e.x = tag.getInteger("X");
            e.y = tag.getInteger("Y");
            e.z = tag.getInteger("Z");
            e.name = tag.hasKey("Name") ? tag.getString("Name") : "Speaker";
            e.range = tag.getInteger("Range");
            e.volume = tag.hasKey("Vol") ? tag.getFloat("Vol") : 0.85f;
            e.bass = tag.getFloat("Bass");
            e.treble = tag.getFloat("Treble");
            e.pairedTo = tag.getString("Paired");
            e.enabled = !tag.hasKey("On") || tag.getBoolean("On");
            return e;
        }
    }

    private final Map<String, Entry> byCode = new HashMap<String, Entry>();

    /** Every code ever issued, so none is ever handed out twice. */
    private final Set<String> issued = new HashSet<String>();

    /**
     * Owners whose own speaker is switched off in their device list.
     *
     * Kept here rather than on the jukebox's tile entity or the JBL's item so that a
     * block and a carried item can be muted the same way, by the same packet, with
     * no second storage format to keep in step. Absence means on, so the common case
     * costs nothing.
     */
    private final Set<String> mutedOwners = new HashSet<String>();

    public SpeakerRegistry() { super(KEY); }

    public SpeakerRegistry(String key) { super(key); }

    // ------------------------------------------------------------------
    // Reaching it
    // ------------------------------------------------------------------

    /** The one registry for this server, or null on a client. */
    public static SpeakerRegistry get(World world) {
        if (world == null || world.isRemote) return null;
        MinecraftServer server = MinecraftServer.getServer();
        if (server == null) return null;

        World store = server.worldServerForDimension(0);
        if (store == null) store = world;

        SpeakerRegistry data =
                (SpeakerRegistry) store.mapStorage.loadData(SpeakerRegistry.class, KEY);
        if (data == null) {
            data = new SpeakerRegistry();
            store.mapStorage.setData(KEY, data);
            data.markDirty();
        }
        return data;
    }

    // ------------------------------------------------------------------
    // Codes
    // ------------------------------------------------------------------

    /**
     * A code no speaker on this server has ever had.
     *
     * Random rather than counted so a code carries no hint of how many speakers
     * exist or what order they were made in, and checked against everything ever
     * issued so the randomness cannot betray us.
     */
    public String issue() {
        for (int attempt = 0; attempt < 64; attempt++) {
            String code = random();
            if (issued.add(code)) {
                markDirty();
                return code;
            }
        }
        // Forty bits of space against a handful of speakers; getting here means
        // something is very wrong, and a code that repeats is worse than a long one.
        String fallback = random() + "-" + random();
        issued.add(fallback);
        markDirty();
        return fallback;
    }

    private static String random() {
        StringBuilder out = new StringBuilder(9);
        for (int i = 0; i < 8; i++) {
            if (i == 4) out.append('-');
            out.append(ALPHABET[RANDOM.nextInt(ALPHABET.length)]);
        }
        return out.toString();
    }

    /** Codes are read back off a screen, so accept them the way people retype them. */
    public static String normalise(String raw) {
        if (raw == null) return "";
        StringBuilder out = new StringBuilder();
        for (char c : raw.trim().toUpperCase().toCharArray()) {
            if (c == 'I' || c == 'L') out.append('1');
            else if (c == 'O') out.append('0');
            else if (c == 'U') out.append('V');
            else if (c >= '0' && c <= '9') out.append(c);
            else if (c >= 'A' && c <= 'Z') out.append(c);
        }
        String flat = out.toString();
        if (flat.length() == 8) return flat.substring(0, 4) + "-" + flat.substring(4);
        return flat;
    }

    // ------------------------------------------------------------------
    // Entries
    // ------------------------------------------------------------------

    public Entry find(String code) {
        return code == null ? null : byCode.get(normalise(code));
    }

    public void put(Entry e) {
        if (e == null || e.code.isEmpty()) return;
        byCode.put(e.code, e);
        issued.add(e.code);
        markDirty();
    }

    public void remove(String code) {
        if (code == null) return;
        if (byCode.remove(normalise(code)) != null) markDirty();
    }

    /** Whether an owner's own speaker is sounding. */
    public boolean ownerEnabled(String ownerKey) {
        return ownerKey != null && !mutedOwners.contains(ownerKey);
    }

    public void setOwnerEnabled(String ownerKey, boolean on) {
        if (ownerKey == null || ownerKey.isEmpty()) return;
        if (on ? mutedOwners.remove(ownerKey) : mutedOwners.add(ownerKey)) markDirty();
    }

    public List<Entry> all() {
        return new ArrayList<Entry>(byCode.values());
    }

    /** Every speaker paired with one owner, in a stable order. */
    public List<Entry> pairedWith(String ownerKey) {
        List<Entry> out = new ArrayList<Entry>();
        if (ownerKey == null || ownerKey.isEmpty()) return out;
        for (Entry e : byCode.values()) {
            if (ownerKey.equals(e.pairedTo)) out.add(e);
        }
        // By code, so the list does not shuffle between openings of the screen.
        java.util.Collections.sort(out, new java.util.Comparator<Entry>() {
            @Override public int compare(Entry a, Entry b) { return a.code.compareTo(b.code); }
        });
        return out;
    }

    /** How far a jukebox may reach to pair, in blocks. */
    public static final int PAIR_RANGE = 150;

    /** The owner key for a jukebox block. */
    public static String blockOwner(int dim, int x, int y, int z) {
        return "B:" + dim + ":" + x + ":" + y + ":" + z;
    }

    /** The owner key for a carried JBL. */
    public static String itemOwner(String speakerId) {
        return "S:" + speakerId;
    }

    // ------------------------------------------------------------------
    // Storage
    // ------------------------------------------------------------------

    @Override
    public void readFromNBT(NBTTagCompound tag) {
        byCode.clear();
        issued.clear();

        NBTTagList list = tag.getTagList("Speakers", 10);
        for (int i = 0; i < list.tagCount(); i++) {
            Entry e = Entry.read(list.getCompoundTagAt(i));
            if (!e.code.isEmpty()) {
                byCode.put(e.code, e);
                issued.add(e.code);
            }
        }
        NBTTagList spent = tag.getTagList("Issued", 8);
        for (int i = 0; i < spent.tagCount(); i++) issued.add(spent.getStringTagAt(i));

        mutedOwners.clear();
        NBTTagList muted = tag.getTagList("Muted", 8);
        for (int i = 0; i < muted.tagCount(); i++) mutedOwners.add(muted.getStringTagAt(i));
    }

    @Override
    public void writeToNBT(NBTTagCompound tag) {
        NBTTagList list = new NBTTagList();
        for (Entry e : byCode.values()) {
            NBTTagCompound one = new NBTTagCompound();
            e.write(one);
            list.appendTag(one);
        }
        tag.setTag("Speakers", list);

        NBTTagList spent = new NBTTagList();
        for (String code : issued) spent.appendTag(new net.minecraft.nbt.NBTTagString(code));
        tag.setTag("Issued", spent);

        NBTTagList muted = new NBTTagList();
        for (String owner : mutedOwners) muted.appendTag(new net.minecraft.nbt.NBTTagString(owner));
        tag.setTag("Muted", muted);
    }
}
