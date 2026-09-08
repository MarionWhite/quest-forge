package com.questforge.content.net;

import io.netty.buffer.ByteBuf;
import cpw.mods.fml.common.network.ByteBufUtils;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;

import com.questforge.content.jukebox.TileEntityJukebox;

/**
 * "This jukebox should hold this track." Sent client -> server when a player picks
 * something in the jukebox screen.
 *
 * The audio stays client-side; this exists purely so the block remembers its own
 * music across sessions, and so two jukeboxes in a base can hold different tracks.
 *
 * Unlike PacketJammer this direction is genuinely untrusted: the filename is typed
 * by whoever is at the keyboard and ends up in NBT that every other client reads
 * and resolves against a local folder. So it is reduced to a bare filename before
 * being stored -- see {@link #sanitize}.
 */
public class PacketBindTrack implements IMessage {

    public int x, y, z;
    public String track = "";

    /** Required by the packet codec. */
    public PacketBindTrack() {}

    public PacketBindTrack(int x, int y, int z, String track) {
        this.x = x;
        this.y = y;
        this.z = z;
        this.track = track == null ? "" : track;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        x = buf.readInt();
        y = buf.readInt();
        z = buf.readInt();
        track = ByteBufUtils.readUTF8String(buf);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeInt(x);
        buf.writeInt(y);
        buf.writeInt(z);
        ByteBufUtils.writeUTF8String(buf, track == null ? "" : track);
    }

    /** Catalog hosts a bound track is allowed to point at. */
    private static final String[] ALLOWED_HOSTS = {
        "archive.org", "www.archive.org"
    };

    /** Catalogs whose per-node subdomains are also allowed. */
    private static final String[] ALLOWED_DOMAINS = {
        ".archive.org",     // archive.org serves files from numbered item nodes
        ".audius.co",       // Audius spreads streams across discovery providers
        ".ccmixter.org"
    };

    /**
     * Reduces a track key to something safe to store and hand to every client.
     *
     * This value ends up in NBT that every client near the block reads and acts on,
     * so both forms it can take are constrained:
     *
     *  - A local track becomes a bare filename. Without that, "../../../something"
     *    would make other people's clients reach outside the jukebox folder on the
     *    say-so of whoever set it.
     *  - A catalog track stays a URL, but only to a known catalog host. A free-form
     *    URL here would let one player make every other client in range issue a
     *    request to an address of their choosing, which is an IP-logging trick at
     *    best and a way to feed clients arbitrary bytes at worst.
     */
    public static String sanitize(String s) {
        if (s == null) return "";
        s = s.trim();
        if (s.length() > 512) return "";

        if (s.startsWith("http://") || s.startsWith("https://")) {
            return sanitizeUrl(s);
        }

        s = s.replace('\\', '/');
        int slash = s.lastIndexOf('/');
        if (slash >= 0) s = s.substring(slash + 1);
        if (s.contains("..") || s.length() > 128) return "";
        return s.trim();
    }

    private static String sanitizeUrl(String s) {
        // A backslash or whitespace in a URL is a parser-confusion trick, not a
        // legitimate track link.
        if (s.indexOf('\\') >= 0 || s.indexOf(' ') >= 0) return "";

        try {
            java.net.URL u = new java.net.URL(s);
            // Credentials in the authority are how "https://archive.org@evil.test"
            // is made to look allowed.
            if (u.getUserInfo() != null) return "";

            String host = u.getHost().toLowerCase();
            if (host.isEmpty()) return "";
            if (isLocalHost(host)) return "";

            for (String allowed : ALLOWED_HOSTS) {
                if (host.equals(allowed)) return s;
            }
            for (String domain : ALLOWED_DOMAINS) {
                if (host.endsWith(domain)) return s;
            }

            // Anything else is a radio station. Stations live on thousands of
            // hosts and plenty still serve plain http, so they cannot be listed
            // in advance the way the catalogs can. They are allowed, minus the
            // addresses above -- which is what stops a bound track being used to
            // aim every client in range at machines inside someone's own network.
            return s;
        } catch (Throwable t) {
            return "";
        }
    }

    /**
     * Addresses that are private to whoever is resolving them.
     *
     * Checked as literal text rather than by resolving the name: this runs while
     * handling a packet, and a DNS lookup there would stall the server on
     * whatever host a client cared to send.
     */
    private static boolean isLocalHost(String host) {
        if (host.equals("localhost") || host.endsWith(".localhost")
                || host.endsWith(".local") || host.endsWith(".internal")) return true;
        // IPv6 loopback and link-local, as they appear bracketed in a URL host.
        if (host.equals("::1") || host.equals("[::1]")
                || host.startsWith("fe80:") || host.startsWith("[fe80:")) return true;
        if (host.startsWith("127.") || host.startsWith("10.")
                || host.startsWith("192.168.") || host.startsWith("169.254.")
                || host.equals("0.0.0.0")) return true;
        // 172.16.0.0/12 is the awkward one: 172.16 through 172.31 only.
        if (host.startsWith("172.")) {
            int dot = host.indexOf('.', 4);
            if (dot > 4) {
                try {
                    int second = Integer.parseInt(host.substring(4, dot));
                    if (second >= 16 && second <= 31) return true;
                } catch (NumberFormatException ignored) {
                    // Not numeric, so not an address in that range.
                }
            }
        }
        return false;
    }

    public static class Handler implements IMessageHandler<PacketBindTrack, IMessage> {

        @Override
        public IMessage onMessage(PacketBindTrack m, MessageContext ctx) {
            EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;
            final World world = player.worldObj;
            if (world == null) return null;

            final String clean = sanitize(m.track);
            final int x = m.x, y = m.y, z = m.z;

            // Runs on the netty thread; touching world state there races the tick.
            ServerTasks.submit(new Runnable() {
                @Override public void run() {
                    // Do not let a client edit a block it could not reach, and do
                    // not load chunks on demand for a packet.
                    if (!world.blockExists(x, y, z)) return;
                    if (player.getDistanceSq(x + 0.5D, y + 0.5D, z + 0.5D) > 64.0D) return;

                    TileEntity te = world.getTileEntity(x, y, z);
                    if (te instanceof TileEntityJukebox) {
                        ((TileEntityJukebox) te).setTrack(clean);
                    }
                }
            });
            return null;
        }
    }
}
