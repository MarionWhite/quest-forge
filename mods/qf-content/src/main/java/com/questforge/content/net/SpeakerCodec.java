package com.questforge.content.net;

import com.questforge.content.jukebox.SpeakerRegistry;
import io.netty.buffer.ByteBuf;

/**
 * How a speaker's record travels, and what is allowed through.
 *
 * Everything here that reads is reading something a client sent, so every field is
 * bounded on the way in rather than trusted and clamped later. A name is capped
 * before it is ever stored, indexes are pinned to the tables they index, and levels
 * are held to the range the sliders can actually produce -- a packet is a request,
 * not an instruction.
 */
public final class SpeakerCodec {

    /** Long enough to name a speaker, short enough that the list still lays out. */
    public static final int MAX_NAME = 24;

    /** Codes are eight characters and a dash; the slack is for a paste with spaces. */
    public static final int MAX_CODE = 32;

    /** How many devices one owner may have. Past this the list stops being usable. */
    public static final int MAX_DEVICES = 12;

    private SpeakerCodec() { }

    // ------------------------------------------------------------------
    // Strings
    // ------------------------------------------------------------------

    public static void writeString(ByteBuf buf, String s, int cap) {
        byte[] raw;
        try {
            raw = (s == null ? "" : s).getBytes("UTF-8");
        } catch (Exception e) {
            raw = new byte[0];
        }
        int len = Math.min(raw.length, cap);
        buf.writeByte(len);
        buf.writeBytes(raw, 0, len);
    }

    public static String readString(ByteBuf buf, int cap) {
        int len = buf.readUnsignedByte();
        if (len > cap) len = cap;
        byte[] raw = new byte[len];
        buf.readBytes(raw);
        try {
            return new String(raw, "UTF-8");
        } catch (Exception e) {
            return "";
        }
    }

    /**
     * A name safe to show and to store.
     *
     * Control characters are dropped rather than escaped, because the one thing a
     * name is for is being drawn in a list, and section signs would let a client
     * recolour or hide text in everybody else's screen.
     */
    public static String cleanName(String raw) {
        if (raw == null) return "Speaker";
        StringBuilder out = new StringBuilder();
        for (char c : raw.toCharArray()) {
            if (c < ' ' || c == 127 || c == '§') continue;
            out.append(c);
            if (out.length() >= MAX_NAME) break;
        }
        String name = out.toString().trim();
        return name.isEmpty() ? "Speaker" : name;
    }

    // ------------------------------------------------------------------
    // Entries
    // ------------------------------------------------------------------

    public static void writeEntry(ByteBuf buf, SpeakerRegistry.Entry e) {
        writeString(buf, e.code, MAX_CODE);
        writeString(buf, e.name, MAX_NAME);
        buf.writeInt(e.dim);
        buf.writeInt(e.x);
        buf.writeInt(e.y);
        buf.writeInt(e.z);
        buf.writeByte(e.range);
        buf.writeFloat(e.volume);
        buf.writeFloat(e.bass);
        buf.writeFloat(e.treble);
        buf.writeBoolean(e.enabled);
        writeString(buf, e.pairedTo, 64);
    }

    public static SpeakerRegistry.Entry readEntry(ByteBuf buf) {
        SpeakerRegistry.Entry e = new SpeakerRegistry.Entry();
        e.code = SpeakerRegistry.normalise(readString(buf, MAX_CODE));
        e.name = cleanName(readString(buf, MAX_NAME));
        e.dim = buf.readInt();
        e.x = buf.readInt();
        e.y = buf.readInt();
        e.z = buf.readInt();
        e.range = clampRange(buf.readByte());
        e.volume = clampVolume(buf.readFloat());
        e.bass = clampTone(buf.readFloat());
        e.treble = clampTone(buf.readFloat());
        e.enabled = buf.readBoolean();
        e.pairedTo = readString(buf, 64);
        return e;
    }

    // ------------------------------------------------------------------
    // Bounds
    // ------------------------------------------------------------------

    /** Indexes the tower range table, which has six entries. */
    public static int clampRange(int i) {
        return i < 0 ? 0 : i > 5 ? 5 : i;
    }

    public static float clampVolume(float v) {
        if (v != v) return 0.85f;                       // NaN
        return v < 0f ? 0f : v > 2.5f ? 2.5f : v;
    }

    public static float clampTone(float db) {
        if (db != db) return 0f;                        // NaN
        return db < -12f ? -12f : db > 12f ? 12f : db;
    }
}
