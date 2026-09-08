import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.ByteBuffer;
import javax.imageio.ImageIO;

import net.minecraft.launchwrapper.Launch;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.*;
import qf.splash.QFBars;

/** Stand-alone preview of the Forge 1.7.10 splash layout using QFBars and an ascii.png bitmap font.
 *  Usage: BarHarness <gameDir> <mural.png> <ascii.png> <out.png> <fontColorHex> [width height] */
public class BarHarness {
    static int[] charWidth = new int[256];
    static int fontTex, muralTex, muralW, muralH;

    public static void main(String[] a) throws Exception {
        Launch.minecraftHome = new File(a[0]);
        int W = a.length > 5 ? Integer.parseInt(a[5]) : 1280, H = a.length > 6 ? Integer.parseInt(a[6]) : 720;
        Display.setDisplayMode(new DisplayMode(W, H)); Display.setTitle("splash harness"); Display.create();
        int fontColor = (int) Long.parseLong(a[4].replace("0x", ""), 16);
        BufferedImage mural = ImageIO.read(new File(a[1])); muralW = mural.getWidth(); muralH = mural.getHeight();
        muralTex = upload(mural);
        BufferedImage font = ImageIO.read(new File(a[2])); fontTex = upload(font); measure(font);
        // Forge setGL()
        GL11.glClearColor(1, 1, 1, 1);
        GL11.glDisable(GL11.GL_LIGHTING); GL11.glDisable(GL11.GL_DEPTH_TEST);
        GL11.glEnable(GL11.GL_BLEND); GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        String[][] bars = {{"Loading - Initializing phase 3", "5/7", "5", "7"}, {"PostInitialization - Journeymap", "69/138", "69", "138"}};
        for (int frame = 0; frame < 40; frame++) {
            GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
            GL11.glMatrixMode(GL11.GL_PROJECTION); GL11.glLoadIdentity();
            GL11.glOrtho(320 - W / 2, 320 + W / 2, 240 + H / 2, 240 - H / 2, -1, 1);
            GL11.glMatrixMode(GL11.GL_MODELVIEW); GL11.glLoadIdentity();
            // mural like Forge: 3840x2160 quad centred on (320,240)
            GL11.glColor3f(1, 1, 1); GL11.glEnable(GL11.GL_TEXTURE_2D); GL11.glBindTexture(GL11.GL_TEXTURE_2D, muralTex);
            GL11.glBegin(GL11.GL_QUADS);
            GL11.glTexCoord2f(0, 0); GL11.glVertex2f(-1600, -840);
            GL11.glTexCoord2f(0, 1); GL11.glVertex2f(-1600, 1320);
            GL11.glTexCoord2f(1, 1); GL11.glVertex2f(2240, 1320);
            GL11.glTexCoord2f(1, 0); GL11.glVertex2f(2240, -840);
            GL11.glEnd(); GL11.glDisable(GL11.GL_TEXTURE_2D);
            GL11.glPushMatrix(); GL11.glTranslatef(120, 310, 0);
            for (String[] b : bars) { drawBar(b, fontColor); GL11.glTranslatef(0, 55, 0); }
            GL11.glPopMatrix();
            Display.update(); Display.sync(30);
        }
        // read back
        ByteBuffer buf = BufferUtils.createByteBuffer(W * H * 4);
        GL11.glReadPixels(0, 0, W, H, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        BufferedImage out = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
            int i = ((H - 1 - y) * W + x) * 4;
            out.setRGB(x, y, ((buf.get(i) & 255) << 16) | ((buf.get(i + 1) & 255) << 8) | (buf.get(i + 2) & 255));
        }
        ImageIO.write(out, "png", new File(a[3]));
        System.out.println("wrote " + a[3]);
        Display.destroy();
    }

    static void drawBar(String[] b, int fontColor) {
        int step = Integer.parseInt(b[2]), steps = Integer.parseInt(b[3]);
        GL11.glPushMatrix();
        setColor(fontColor);
        QFBars.beginBar(2, 2, 1);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        drawString(b[0], 0, 0);
        GL11.glDisable(GL11.GL_TEXTURE_2D);
        GL11.glPopMatrix();
        GL11.glPushMatrix();
        GL11.glTranslatef(0, 20, 0);
        setColor(0x4A3A2A); QFBars.drawBox(null, 400, 20);
        setColor(0x1C1814); GL11.glTranslatef(1, 1, 0); QFBars.drawBox(null, 398, 18);
        setColor(0xE67A22); QFBars.drawBox(null, 398 * (step + 1) / (steps + 1), 18);
        String s = b[1];
        GL11.glTranslatef(199 - stringWidth(s), 2, 0);       // Forge: translate(199 - width, 2), scale 2
        setColor(fontColor);
        GL11.glScalef(2, 2, 1);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        drawString(s, 0, 0);
        GL11.glDisable(GL11.GL_TEXTURE_2D);
        GL11.glPopMatrix();
    }

    static void drawString(String text, float x, float y) {
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, fontTex);
        float px = x;
        for (char c : text.toCharArray()) {
            int idx = c < 256 ? c : '?';
            float u = (idx % 16) * 8 / 128f, v = (idx / 16) * 8 / 128f;
            GL11.glBegin(GL11.GL_QUADS);
            GL11.glTexCoord2f(u, v); GL11.glVertex2f(px, y);
            GL11.glTexCoord2f(u, v + 7.99f / 128f); GL11.glVertex2f(px, y + 7.99f);
            GL11.glTexCoord2f(u + 7.99f / 128f, v + 7.99f / 128f); GL11.glVertex2f(px + 7.99f, y + 7.99f);
            GL11.glTexCoord2f(u + 7.99f / 128f, v); GL11.glVertex2f(px + 7.99f, y);
            GL11.glEnd();
            px += charWidth[idx];
        }
    }

    static int stringWidth(String s) { int w = 0; for (char c : s.toCharArray()) w += charWidth[c < 256 ? c : '?']; return w; }

    static void setColor(int color) {
        GL11.glColor3ub((byte) ((color >> 16) & 0xFF), (byte) ((color >> 8) & 0xFF), (byte) (color & 0xFF));
    }

    /** Same width rule as FontRenderer.readFontTexture: rightmost non-transparent column, scaled to 8 units, +1. */
    static void measure(BufferedImage img) {
        int w = img.getWidth(), h = img.getHeight(), cw = w / 16, ch = h / 16; float f = 8f / cw;
        int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        for (int i = 0; i < 256; i++) {
            int cx = (i % 16) * cw, cy = (i / 16) * ch, last = -1;
            for (int x = cw - 1; x >= 0 && last < 0; x--)
                for (int y = 0; y < ch; y++) if (((px[(cy + y) * w + cx + x] >> 24) & 255) != 0) { last = x; break; }
            charWidth[i] = i == 32 ? 4 : (int) (0.5 + (last + 1) * f) + 1;
        }
    }

    static int upload(BufferedImage img) {
        int w = img.getWidth(), h = img.getHeight(); int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        ByteBuffer buf = BufferUtils.createByteBuffer(w * h * 4);
        for (int p : px) buf.put((byte) ((p >> 16) & 255)).put((byte) ((p >> 8) & 255)).put((byte) (p & 255)).put((byte) ((p >> 24) & 255));
        buf.flip();
        int id = GL11.glGenTextures(); GL11.glBindTexture(GL11.GL_TEXTURE_2D, id);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, w, h, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        return id;
    }
}
