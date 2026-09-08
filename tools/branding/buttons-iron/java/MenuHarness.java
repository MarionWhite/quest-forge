import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.ByteBuffer;
import javax.imageio.ImageIO;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.*;
import qf.menu.QFButtons;

/** Stand-alone preview of the animated menu buttons at a vanilla-like layout (gui scale 3 in a 1280x720 window).
 *  Usage: MenuHarness <assetsDir(out/)> <background.jpg> <outPrefix> */
public class MenuHarness extends mainmenuserver.MainMenuFix {
    static int bound;
    @Override public void drawTexturedModalRect(int x, int y, int w, int h) {
        GL11.glBegin(GL11.GL_QUADS);
        GL11.glTexCoord2f(0, 0); GL11.glVertex2f(x, y);
        GL11.glTexCoord2f(0, 1); GL11.glVertex2f(x, y + h);
        GL11.glTexCoord2f(1, 1); GL11.glVertex2f(x + w, y + h);
        GL11.glTexCoord2f(1, 0); GL11.glVertex2f(x + w, y);
        GL11.glEnd();
    }

    public static void main(String[] a) throws Exception {
        File assets = new File(a[0]);
        int W = 1280, H = 720, scale = 3;
        Display.setDisplayMode(new DisplayMode(W, H)); Display.setTitle("menu harness"); Display.create();
        MenuHarness gui = new MenuHarness();
        gui.field_146294_l = W / scale; gui.field_146295_m = H / scale;
        int gw = gui.field_146294_l, gh = gui.field_146295_m;
        int bg = upload(ImageIO.read(new File(a[1])));
        String[] names = {"single", "multiplayer", "mods", "options", "quit"};
        int[] texIdx = {2, 4, 6, 10, 12};
        int[] tex = new int[names.length];
        for (int i = 0; i < names.length; i++) tex[i] = upload(ImageIO.read(new File(assets, names[i] + ".png")));
        // vanilla-ish layout
        int by = gh / 4 + 48, bx = gw / 2 - 100;
        int[][] rects = {{bx + 10, by - 1, 180, 24}, {bx + 10, by + 24 - 1, 180, 24}, {bx + 10, by + 48 - 1, 180, 24},
                         {bx + 5, by + 84 - 1, 90, 24}, {bx + 102 + 5, by + 84 - 1, 90, 24}};
        // hover Multiplayer, then Quit, via the test hook
        java.lang.reflect.Field dm = QFButtons.class.getDeclaredField("debugMouse"); dm.setAccessible(true);
        int frames = 150; int[] snaps = {45, 80, 149};
        for (int f = 0; f < frames; f++) {
            int[] mouse = f < 90 ? new int[]{rects[1][0] + 60, rects[1][1] + 10} : new int[]{rects[4][0] + 30, rects[4][1] + 10};
            dm.set(null, mouse);
            GL11.glViewport(0, 0, W, H);
            GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);
            GL11.glMatrixMode(GL11.GL_PROJECTION); GL11.glLoadIdentity(); GL11.glOrtho(0, gw, gh, 0, 1000, 3000);
            GL11.glMatrixMode(GL11.GL_MODELVIEW); GL11.glLoadIdentity(); GL11.glTranslatef(0, 0, -2000);
            GL11.glEnable(GL11.GL_TEXTURE_2D); GL11.glEnable(GL11.GL_BLEND); GL11.glBlendFunc(770, 771); GL11.glColor4f(1, 1, 1, 1);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, bg); gui.drawTexturedModalRect(0, 0, gw, gh);
            for (int i = 0; i < names.length; i++) {
                GL11.glBindTexture(GL11.GL_TEXTURE_2D, tex[i]);
                GL11.glColor4f(1, 1, 1, 1);
                QFButtons.drawButton(gui, rects[i][0], rects[i][1], rects[i][2], rects[i][3], texIdx[i]);
            }
            Display.update(); Display.sync(60);
            for (int s : snaps) if (f == s) snapshot(W, H, a[2] + "_f" + f + ".png");
        }
        Display.destroy();
    }

    static void snapshot(int W, int H, String path) throws Exception {
        ByteBuffer buf = BufferUtils.createByteBuffer(W * H * 4);
        GL11.glReadPixels(0, 0, W, H, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        BufferedImage out = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
            int i = ((H - 1 - y) * W + x) * 4;
            out.setRGB(x, y, ((buf.get(i) & 255) << 16) | ((buf.get(i + 1) & 255) << 8) | (buf.get(i + 2) & 255));
        }
        ImageIO.write(out, "png", new File(path)); System.out.println("wrote " + path);
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
