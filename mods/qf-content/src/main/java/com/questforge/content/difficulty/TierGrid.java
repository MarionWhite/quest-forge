package com.questforge.content.difficulty;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.zip.CRC32;
import java.util.zip.GZIPInputStream;

/**
 * The baked difficulty map: one tier byte per chunk over the designed continent.
 *
 * Written by {@code tools/world/difficulty.py --bake}; the format is documented
 * there (write_grid) and in docs/design/world/r14/difficulty-mechanism.md. A
 * 64-byte big-endian header (magic "QFTG", version, header length, origin chunk,
 * width, height, tier range, the tier just outside, CRC-32 of the data, SHA-256 of
 * the spec), then width*height bytes, row-major by z. The whole file may be
 * gzipped; the reader looks at the first two bytes.
 *
 * Read once at world load and kept as a byte[] (9.4 MB for the r13 plan); a lookup
 * is one array read. Nothing here is sent to clients.
 */
public final class TierGrid {

    static final int MAGIC = 0x51465447; // "QFTG"
    static final int VERSION = 1;

    public final int originChunkX;
    public final int originChunkZ;
    public final int width;
    public final int height;
    public final int minTier;
    public final int maxTier;
    public final int outsideTier;
    public final String specSha256;
    public final File source;
    private final byte[] data;

    private TierGrid(File source, int x0, int z0, int w, int h, int minTier, int maxTier, int outside,
                     String sha, byte[] data) {
        this.source = source;
        this.originChunkX = x0;
        this.originChunkZ = z0;
        this.width = w;
        this.height = h;
        this.minTier = minTier;
        this.maxTier = maxTier;
        this.outsideTier = outside;
        this.specSha256 = sha;
        this.data = data;
    }

    /** Reads a grid file. Throws on anything malformed: a wrong grid is worse than none. */
    public static TierGrid read(File file) throws IOException {
        InputStream in = new BufferedInputStream(new FileInputStream(file), 1 << 16);
        try {
            in.mark(2);
            int b0 = in.read(), b1 = in.read();
            in.reset();
            if (b0 == 0x1f && b1 == 0x8b) in = new BufferedInputStream(new GZIPInputStream(in, 1 << 16), 1 << 16);
            DataInputStream d = new DataInputStream(in);
            int magic = d.readInt();
            if (magic != MAGIC) throw new IOException("not a tier grid (bad magic)");
            int version = d.readUnsignedShort();
            if (version != VERSION) throw new IOException("unsupported tier grid version " + version);
            int headerLen = d.readUnsignedShort();
            int x0 = d.readInt(), z0 = d.readInt(), w = d.readInt(), h = d.readInt();
            int tmin = d.readUnsignedByte(), tmax = d.readUnsignedByte(), tout = d.readUnsignedByte();
            d.readUnsignedByte();
            long crc = d.readInt() & 0xFFFFFFFFL;
            byte[] sha = new byte[32];
            d.readFully(sha);
            if (headerLen < 64) throw new IOException("short header (" + headerLen + ")");
            d.skipBytes(headerLen - 64);
            if (w <= 0 || h <= 0 || (long) w * h > 64L * 1024 * 1024) {
                throw new IOException("implausible grid size " + w + "x" + h);
            }
            byte[] data = new byte[w * h];
            d.readFully(data);
            CRC32 c = new CRC32();
            c.update(data);
            if (c.getValue() != crc) throw new IOException("CRC mismatch: the file is corrupt");
            StringBuilder hex = new StringBuilder();
            for (byte b : sha) hex.append(String.format("%02x", b & 0xFF));
            return new TierGrid(file, x0, z0, w, h, tmin, tmax, tout, hex.toString(), data);
        } finally {
            in.close();
        }
    }

    /** True when the chunk lies inside the grid. */
    public boolean contains(int chunkX, int chunkZ) {
        int i = chunkX - originChunkX, j = chunkZ - originChunkZ;
        return i >= 0 && j >= 0 && i < width && j < height;
    }

    /** The baked tier of a chunk inside the grid; call {@link #contains} first. */
    public int tierAtChunk(int chunkX, int chunkZ) {
        return data[(chunkZ - originChunkZ) * width + (chunkX - originChunkX)] & 0xFF;
    }

    /** Distance in blocks from (x, z) to the nearest edge of the grid; 0 inside it. */
    public double blocksOutside(double x, double z) {
        double x0 = originChunkX * 16.0, x1 = (originChunkX + width) * 16.0;
        double z0 = originChunkZ * 16.0, z1 = (originChunkZ + height) * 16.0;
        double dx = x < x0 ? x0 - x : (x > x1 ? x - x1 : 0);
        double dz = z < z0 ? z0 - z : (z > z1 ? z - z1 : 0);
        return Math.sqrt(dx * dx + dz * dz);
    }

    @Override
    public String toString() {
        return width + "x" + height + " chunks from chunk (" + originChunkX + ", " + originChunkZ + "), tiers "
                + minTier + "-" + maxTier + ", spec " + specSha256.substring(0, 12);
    }
}
