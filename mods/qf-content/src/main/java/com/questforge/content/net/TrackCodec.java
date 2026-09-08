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

    private TrackCodec() { }

    public static void writeTracks(ByteBuf buf, List<Track> tracks) {
        int n = Math.min(tracks == null ? 0 : tracks.size(), PublicPlaylists.MAX_TRACKS);
        buf.writeShort(n);

        for (int i = 0; i < n; i++) {
            Track t = tracks.get(i);
            writeCapped(buf, t.key(), KEY);
            writeCapped(buf, t.source, 32);
            writeCapped(buf, t.title, TITLE);
            writeCapped(buf, t.artist, ARTIST);
            writeCapped(buf, t.album, ALBUM);
            writeCapped(buf, t.artUrl == null ? "" : t.artUrl, ART);
            buf.writeInt((int) Math.min(Math.max(t.durationMs, 0L), Integer.MAX_VALUE));
        }
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
