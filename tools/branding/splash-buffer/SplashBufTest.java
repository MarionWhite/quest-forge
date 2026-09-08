import java.nio.IntBuffer;

/** Replay Forge SplashProgress$Texture pixel upload against the NEW buffer size. */
public class SplashBufTest {
    public static void main(String[] args) {
        final int cap = 16 * 1024 * 1024; // 16,777,216
        final int w = 3840;
        final int h = 2160;
        final int pixels = w * h;
        IntBuffer buf = IntBuffer.allocate(cap);
        buf.clear();
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                buf.put((y << 16) ^ x);
            }
        }
        buf.position(0).limit(pixels);
        if (buf.remaining() != pixels) {
            System.out.println("FAIL remaining=" + buf.remaining() + " expected=" + pixels);
            System.exit(1);
        }
        System.out.println("OK cap=" + cap
            + " put=" + pixels
            + " remaining=" + buf.remaining()
            + " headroom=" + (cap - pixels));
    }
}
