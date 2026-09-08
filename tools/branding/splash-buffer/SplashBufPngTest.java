import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.IntBuffer;
import javax.imageio.ImageIO;
public class SplashBufPngTest {
    public static void main(String[] args) throws Exception {
        int cap = 16 * 1024 * 1024;
        IntBuffer buf = IntBuffer.allocate(cap);
        BufferedImage img = ImageIO.read(new File(args[0]));
        int w = img.getWidth(), h = img.getHeight();
        buf.clear();
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                buf.put(img.getRGB(x, y));
            }
        }
        buf.position(0).limit(w * h);
        System.out.println("OK png " + w + "x" + h + " type=" + img.getType()
            + " pixels=" + (w * (long) h) + " remaining=" + buf.remaining()
            + " cap=" + cap);
    }
}
