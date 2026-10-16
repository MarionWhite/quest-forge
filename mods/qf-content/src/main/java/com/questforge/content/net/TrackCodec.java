package com.questforge.content.net;

import cpw.mods.fml.common.network.ByteBufUtils;
import io.netty.buffer.ByteBuf;
import net.minecraft.util.MathHelper;

import java.util.ArrayList;
import java.util.List;

import com.questforge.content.jukebox.PublicPlaylists;
import com.questforge.content.jukebox.Track;

/**
 * How a list of tracks travels over the wire.
 *
 * Every field has a cap and the list has a length, both enforced on read as well
 * as on write. A packet arrives from somewhere else's computer, so the reader
 * cannot assume the writer was this code: without the caps, one client could pin
 * the server's memory with a single message claiming a few million tracks.
 *
 * The caps are also what keeps a whole playlist inside Minecraft's 32767-byte
 * payload limit, so a shared playlist never needs splitting across packets.
 */
public final class TrackCodec {

    private static final int KEY = 300, TITLE = 80, ARTIST = 60, ALBUM = 60, ART = 200;

    /**
     * The most a track list may take up on the wire, in bytes.
     *
     * The per-field caps only bound characters, not bytes. Forty tracks of plain
     * ASCII at every cap come to about 30,000 bytes, but UTF-8 spends up to three
     * bytes a character, so forty full tracks titled in Japanese or Cyrillic are
     * nearer 90,000 -- and a client-to-server payload of 32767 or more throws
     * inside C17PacketCustomPayload rather than sending. This leaves room under
     * that limit for everything else a packet carries: the discriminator, a name
     * of up to 40 characters, and a flag or a slot.
     */
    public static final int MAX_TRACK_BYTES = 32000;

    private TrackCodec() { }

    public static void writeTracks(ByteBuf buf, List<Track> tracks) {
        int n = fitting(tracks);
        buf.writeShort(n);
        for (int i = 0; i < n; i++) writeTrack(buf, tracks.get(i));
    }

    /**
     * How many tracks, from the front of the list, fit in one packet: no more than
     * MAX_TRACKS, and no more than MAX_TRACK_BYTES once encoded. writeTracks sends
     * exactly this many, so a screen can call it first and say what will be left
     * off rather than have the server quietly receive fewer.
     */
    public static int fitting(List<Track> tracks) {
        int max = Math.min(tracks == null ? 0 : tracks.size(), PublicPlaylists.MAX_TRACKS);
        ByteBuf scratch = io.netty.buffer.Unpooled.buffer();
        int bytes = 2;   // the count itself
        int n = 0;
        while (n < max) {
            scratch.clear();
            writeTrack(scratch, tracks.get(n));
            if (bytes + scratch.readableBytes() > MAX_TRACK_BYTES) break;
            bytes += scratch.readableBytes();
            n++;
        }
        return n;
    }

    private static void writeTrack(ByteBuf buf, Track t) {
        writeCapped(buf, t.key(), KEY);
        writeCapped(buf, t.source, 32);
        writeCapped(buf, t.title, TITLE);
        writeCapped(buf, t.artist, ARTIST);
        writeCapped(buf, t.album, ALBUM);
        writeCapped(buf, t.artUrl == null ? "" : t.artUrl, ART);
        buf.writeInt((int) Math.min(Math.max(t.durationMs, 0L), Integer.MAX_VALUE));
    }

    public static List<Track> readTracks(ByteBuf buf) {
        int n = MathHelper.clamp_int(buf.readShort(), 0, PublicPlaylists.MAX_TRACKS);
        List<Track> out = new ArrayList<Track>(n);

        for (int i = 0; i < n; i++) {
            String key = readCapped(buf, KEY);
            String source = readCapped(buf, 32);
            String title = readCapped(buf, TITLE);
            String artist = readCapped(buf, ARTIST);
            String album = readCapped(buf, ALBUM);
            String art = readCapped(buf, ART);
            long duration = Math.max(0, buf.readInt());

            // Checked here as well as when it is stored, so a track can never reach
            // a player's client without having passed the host rules.
            String clean = PacketBindTrack.sanitize(key);
            if (clean.isEmpty()) continue;

            out.add(Track.remote(clean, source, title, artist, album, duration,
                                 art.isEmpty() ? null : art));
        }
        return out;
    }

    public static void writeCapped(ByteBuf buf, String s, int max) {
        if (s == null) s = "";
        if (s.length() > max) s = s.substring(0, max);
        ByteBufUtils.writeUTF8String(buf, s);
    }

    public static String readCapped(ByteBuf buf, int max) {
        String s = ByteBufUtils.readUTF8String(buf);
        if (s == null) return "";
        return s.length() > max ? s.substring(0, max) : s;
    }
}
