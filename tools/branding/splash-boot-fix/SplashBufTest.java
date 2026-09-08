import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.IntBuffer;
import javax.imageio.ImageIO;

/** Mimic Forge 1.7.10 SplashProgress$Texture pixel upload into the 4M-int buffer. */
public class SplashBufTest {
    public static void main(String[] args) throws Exception {
        int cap = 4 * 1024 * 1024;
        IntBuffer buf = IntBuffer.allocate(cap);
        for (String path : args) {
            buf.clear();
            BufferedImage img = ImageIO.read(new File(path));
            if (img == null) {
                System.out.println("FAIL cannot decode " + path);
                System.exit(2);
            }
            int w = img.getWidth();
            int h = img.getHeight();
            try {
                for (int y = 0; y < h; y++) {
                    for (int x = 0; x < w; x++) {
                        buf.put(img.getRGB(x, y));
                    }
                }
                System.out.println("OK " + path + " " + w + "x" + h
                    + " type=" + img.getType()
                    + " pixels=" + (w * (long) h)
                    + " remaining=" + buf.remaining());
            } catch (Exception e) {
                System.out.println("FAIL " + path + " " + w + "x" + h
                    + " pixels=" + (w * (long) h) + " " + e);
                System.exit(1);
            }
        }
    }
}
