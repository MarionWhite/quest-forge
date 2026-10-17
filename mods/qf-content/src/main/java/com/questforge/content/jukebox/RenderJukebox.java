package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.OpenGlHelper;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.tileentity.TileEntitySpecialRenderer;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ResourceLocation;

import org.lwjgl.opengl.GL11;

/**
 * The jukebox in the world.
 *
 * The shape is {@link JukeboxModel}; this only places it, decides how bright the
 * wood is, and how fast the neon travels. A cabinet standing idle still moves --
 * that is what a bubbler does -- but it moves faster while something is playing,
 * so across a room you can see whether the thing is on.
 *
 * <p>The model is tens of thousands of vertices, and it used to be rebuilt from
 * scratch for every jukebox on every frame: six of them cost a fast machine most
 * of its frame rate. Now nearly all of it -- everything that never moves -- is
 * compiled once into display lists and only replayed. The parts that do move
 * (the braid, the columns, the analyser) look the same on every jukebox in the
 * same state, so they are built once a frame per state and replayed on each.
 */
@SideOnly(Side.CLIENT)
public class RenderJukebox extends TileEntitySpecialRenderer {

    /** Cycles per second of the colour sweep, idle and playing. */
    private static final float IDLE_RATE = 0.115F;
    private static final float PLAY_RATE = 0.330F;

    /**
     * The sweep's phase, advanced by elapsed time rather than read off the world
     * clock, so it does not jump when the rate changes.
     *
     * Wrap only where every wave in JukeboxModel.flow lands back where it
     * started: its speeds are 2.6 and 1.15 per unit, which come round to whole
     * turns together at 20 (52 and 23). Wrapping at 1 caught both part-way
     * through a cycle and snapped the light back along the tubes.
     */
    private static float phase;
    private static final float PHASE_PERIOD = 20F;

    /** Degrees per second while a track is playing. A 45 turning at speed. */
    private static final float SPIN_DPS = 156F;
    private static float spin;

    /** When a playing jukebox was last drawn, so the sweep knows to hurry. */
    private static long liveSeen;
    private static long lastNanos;
    private static long clockFrame = Long.MIN_VALUE;

    /** Milliseconds between analyser columns. Slower and it steps; faster and it blurs. */
    private static final long PUSH_MS = 55L;

    /**
     * One state the cabinet can be in -- idle, or playing -- with its own
     * analyser and its own copy of the moving parts for the current frame.
     *
     * The analyser keeps a history, as a ring the columns are read out of: a
     * record of what the level has been doing, marching left while new readings
     * enter at the right. That is what makes it scroll.
     */
    private static final class State {
        final boolean live;
        final float[] bars = new float[JukeboxModel.BARS];
        final float[] hist = new float[JukeboxModel.BARS];
        int head;
        long lastPush;
        float level = 0.085F;
        long frame = Long.MIN_VALUE;
        int lists;

        State(boolean live) {
            this.live = live;
        }

        void levels() {
            float target = 0.085F;
            if (live) {
                target = DirectAudio.amplitude(DirectAudio.OWNER);
                if (target < 0.085F) target = 0.085F;
                if (target > 1F) target = 1F;
            }
            level += (target - level) * (target > level ? 0.45F : 0.08F);

            long now = System.currentTimeMillis();
            if (now - lastPush >= PUSH_MS) {
                lastPush = now;
                float t = now * 0.001F;
                // A little shape on the incoming sample, so a steady level is
                // still a waveform rather than a flat wall marching past.
                float wob = 0.72F + 0.28F * (float) Math.sin(t * 5.3F)
                                  * (float) Math.cos(t * 2.1F);
                hist[head] = Math.min(1F, level * wob);
                head = (head + 1) % hist.length;
            }
            // Oldest on the left, each column eased so the march does not look
            // like a row of jumping blocks.
            for (int i = 0; i < bars.length; i++) {
                float want = hist[(head + i) % hist.length];
                bars[i] += (want - bars[i]) * 0.55F;
            }
        }
    }

    private static final State IDLE = new State(false), LIVE = new State(true);
    /** What the off-screen icon bake asks for; never advanced. */
    private static final State POSED = new State(false);
    private static boolean posed;

    /**
     * Holds the analyser and the neon at a chosen moment, for a picture taken
     * off screen with {@link #draw}.
     */
    public static void pose(float[] bars, float lv) {
        System.arraycopy(bars, 0, POSED.bars, 0, Math.min(bars.length, POSED.bars.length));
        POSED.level = lv;
        posed = true;
    }

    // ------------------------------------------------------------------
    // Parts
    // ------------------------------------------------------------------

    private static final int CABINET = 0, SHOULDER = 1, SIDES = 2, BACK = 3,
            FRONT = 4, HARDWARE = 5, CAPS = 6, WINDOW = 7, INLAY = 8, WELL = 9,
            PLATTER = 10, DISC = 11, TONEARM = 12, GLAZING = 13, COILS = 14,
            CHROME = 15, STRIP = 16, STATIC_PARTS = 17;
    private static final int ARCH = 0, TUBE_L = 1, TUBE_R = 2, WAVE = 3,
            MOVING_PARTS = 4;

    /** The display list of each still part, and the light each one wants. */
    private static int statics;
    private static final int[] WANTS = new int[STATIC_PARTS];
    /** Whether the still parts were compiled with a shader pack on or off. */
    private static boolean compiledUnderShaders;

    private static void emitStatic(Tessellator t, int part, int light) {
        switch (part) {
            case CABINET:  JukeboxModel.cabinet(t, light); break;
            case SHOULDER: JukeboxModel.shoulderFace(t, light); break;
            case SIDES:    JukeboxModel.sidePanels(t, light); break;
            case BACK:     JukeboxModel.backPanel(t, light); break;
            case FRONT:    JukeboxModel.front(t, light); break;
            case HARDWARE: JukeboxModel.hardware(t); break;
            case CAPS:     JukeboxModel.capitals(t); break;
            case WINDOW:   JukeboxModel.window(t); break;
            case INLAY:    JukeboxModel.backInlay(t, light); break;
            case WELL:     JukeboxModel.well(t, light); break;
            case PLATTER:  JukeboxModel.platter(t); break;
            case DISC:     JukeboxModel.disc(t); break;
            case TONEARM:  JukeboxModel.tonearm(t); break;
            case GLAZING:  JukeboxModel.glass(t); break;
            case COILS:    JukeboxModel.coils(t); break;
            case CHROME:
                JukeboxModel.chrome(t, light);
                JukeboxModel.wellFrame(t);
                JukeboxModel.trim(t);
                break;
            case STRIP:    JukeboxModel.strip(t); break;
            default: break;
        }
    }

    private static void emitMoving(Tessellator t, int part, State s) {
        switch (part) {
            case ARCH:   JukeboxModel.arch(t, phase(s), s.level); break;
            case TUBE_L: JukeboxModel.tubeLeft(t, s.level, phase(s)); break;
            case TUBE_R: JukeboxModel.tubeRight(t, s.level, phase(s)); break;
            case WAVE:   JukeboxModel.waveform(t, s.bars); break;
            default: break;
        }
    }

    private static float phase(State s) {
        return s == POSED ? posedPhase : phase;
    }

    private static float posedPhase;

    /** Compiles the still parts, once -- and again if the shader pack changes. */
    private static void ensureStatics() {
        boolean shaders = com.questforge.content.client.Shaders.active();
        if (statics != 0 && shaders == compiledUnderShaders) return;
        if (statics == 0) statics = GL11.glGenLists(STATIC_PARTS);
        compiledUnderShaders = shaders;
        Tessellator t = Tessellator.instance;
        for (int p = 0; p < STATIC_PARTS; p++) {
            JukeboxModel.compiling = true;
            JukeboxModel.asked = 0;
            GL11.glNewList(statics + p, GL11.GL_COMPILE);
            t.startDrawingQuads();
            // Any light but LIT reads as "the room's light" while compiling.
            emitStatic(t, p, 0);
            t.draw();
            GL11.glEndList();
            JukeboxModel.compiling = false;
            WANTS[p] = JukeboxModel.asked;
            if (WANTS[p] == (JukeboxModel.SELF_LIT | JukeboxModel.ROOM_LIT)) {
                // One list can only be replayed at one light. Draw it live.
                System.out.println("[QuestForgeContent] jukebox part " + p
                        + " mixes self-lit and room-lit geometry; drawing it live");
            }
        }
    }

    /** Rebuilds a state's moving parts, once per frame. */
    private static void refresh(State s, long frame) {
        if (s.frame == frame) return;
        s.frame = frame;
        s.levels();
        if (s.lists == 0) s.lists = GL11.glGenLists(MOVING_PARTS);
        Tessellator t = Tessellator.instance;
        for (int p = 0; p < MOVING_PARTS; p++) {
            JukeboxModel.compiling = true;
            GL11.glNewList(s.lists + p, GL11.GL_COMPILE);
            t.startDrawingQuads();
            emitMoving(t, p, s);
            t.draw();
            GL11.glEndList();
            JukeboxModel.compiling = false;
        }
    }

    /** Sets the lightmap a list is replayed at. */
    private static void lightmap(int b) {
        OpenGlHelper.setLightmapTextureCoords(OpenGlHelper.lightmapTexUnit,
                                              b & 0xFFFF, b >>> 16);
    }

    // ------------------------------------------------------------------
    // Drawing
    // ------------------------------------------------------------------

    @Override
    public void renderTileEntityAt(TileEntity te, double x, double y, double z,
                                   float partial) {
        if (!(te instanceof TileEntityJukebox)) return;

        int meta = te.getWorldObj() == null ? 0
                : te.getWorldObj().getBlockMetadata(te.xCoord, te.yCoord, te.zCoord);
        int look = BlockJukebox.facing(meta);

        // Sampled OUTSIDE the cabinet. yCoord + 1 is the jukebox's own upper
        // half, and a block with default light opacity is dark inside, so the
        // whole cabinet was being drawn at light level zero -- which is why the
        // walnut looked black however bright its sheet was made.
        int light = te.getWorldObj() == null ? JukeboxModel.LIT : brightest(te);

        // Everything drawn in one frame shares its partial tick and world time,
        // so the pair names the frame: the clock and each state's moving parts
        // advance once per frame however many jukeboxes are on screen. They used
        // to advance once per jukebox, so six of them spun the records six times
        // too fast.
        long frame = te.getWorldObj() == null ? 0L
                : (te.getWorldObj().getTotalWorldTime() << 32)
                  ^ Float.floatToIntBits(partial);
        boolean live = playing(te);
        if (live) liveSeen = System.currentTimeMillis();
        tick(frame);

        GL11.glPushMatrix();
        GL11.glTranslated(x, y, z);
        GL11.glTranslatef(0.5F, 0F, 0.5F);
        GL11.glRotatef(-look * 90F, 0F, 1F, 0F);
        GL11.glTranslatef(-0.5F, 0F, -0.5F);

        State s = live ? LIVE : IDLE;
        ensureStatics();
        refresh(s, frame);
        render(light, s, live ? spin : 0F, ((TileEntityJukebox) te).getDisc(), true);

        GL11.glPopMatrix();
    }

    /**
     * Draws the whole cabinet at the current origin, built fresh.
     *
     * For the item renderer and the icon bake: one-off draws that have no tile
     * entity and are not worth a cache of their own.
     */
    public static void draw(int light, float atPhase, float atSpin, int tier) {
        posedPhase = atPhase;
        if (!posed) {
            // Unless a picture asked for a moment, show the idle cabinet as it is.
            System.arraycopy(IDLE.bars, 0, POSED.bars, 0, POSED.bars.length);
            POSED.level = IDLE.level;
        }
        render(light, POSED, atSpin, tier, false);
    }

    private static void render(int light, State s, float atSpin, int tier, boolean cached) {
        boolean lit = JukeboxModel.begin();
        Tessellator t = Tessellator.instance;

        // The cabinet's UVs are in blocks, not in 0..1, so its sheet must tile.
        // Minecraft leaves entity textures clamped, and clamped UVs past 1.0
        // smear the sheet's last column across the rest of the panel.
        bind(JukeboxModel.CABINET);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_REPEAT);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_REPEAT);
        still(t, CABINET, light, cached);
        part(t, JukeboxModel.SHOULDER, SHOULDER, light, cached);
        part(t, JukeboxModel.PANEL_SIDE, SIDES, light, cached);
        part(t, JukeboxModel.PANEL_BACK, BACK, light, cached);
        part(t, JukeboxModel.FRONT, FRONT, light, cached);
        part(t, JukeboxModel.HARDWARE, HARDWARE, light, cached);
        moving(t, JukeboxModel.ARCH, ARCH, s, cached);
        moving(t, JukeboxModel.TUBE_LEFT, TUBE_L, s, cached);
        moving(t, JukeboxModel.TUBE_RIGHT, TUBE_R, s, cached);
        part(t, JukeboxModel.CAP, CAPS, light, cached);
        part(t, JukeboxModel.WINDOW, WINDOW, light, cached);
        // JukeboxModel.stars(t) twinkled over the nebula; shelved with it.
        moving(t, JukeboxModel.WHITE, WAVE, s, cached);
        part(t, JukeboxModel.WHITE, INLAY, light, cached);
        part(t, JukeboxModel.CHAMBER, WELL, light, cached);
        deck(t, light, atSpin, tier, cached);
        glazing(t, light, cached);
        part(t, JukeboxModel.COIL, COILS, light, cached);
        chromePass(t, light, cached);
        part(t, JukeboxModel.STRIP, STRIP, light, cached);

        // Leave the lightmap where the dispatcher set it for this block.
        if (cached) lightmap(light);
        JukeboxModel.end(lit);
    }

    /** Binds one sheet and draws the still part that wears it. */
    private static void part(Tessellator t, ResourceLocation tex, int p, int light,
                             boolean cached) {
        bind(tex);
        still(t, p, light, cached);
    }

    private static void still(Tessellator t, int p, int light, boolean cached) {
        if (cached && WANTS[p] != (JukeboxModel.SELF_LIT | JukeboxModel.ROOM_LIT)) {
            lightmap(WANTS[p] == JukeboxModel.SELF_LIT ? JukeboxModel.LIT : light);
            GL11.glCallList(statics + p);
            return;
        }
        t.startDrawingQuads();
        emitStatic(t, p, light);
        t.draw();
    }

    private static void moving(Tessellator t, ResourceLocation tex, int p, State s,
                               boolean cached) {
        bind(tex);
        if (cached) {
            // The moving parts are all neon: drawn at full light.
            lightmap(JukeboxModel.LIT);
            GL11.glCallList(s.lists + p);
            return;
        }
        t.startDrawingQuads();
        emitMoving(t, p, s);
        t.draw();
    }

    /**
     * The deck: platter, record and arm.
     *
     * The record's sprite has transparent corners, so it is cut out with an
     * alpha test rather than blended: a deferred pack cannot blend, and a blended
     * disc there comes out as an opaque square over the mechanism. The spin is a
     * matrix about the disc's centre, outside its list.
     */
    private static void deck(Tessellator t, int light, float atSpin, int tier,
                             boolean cached) {
        // Lean the plane back to lay the record down, then turn it about what is
        // now the platter's own axis.
        GL11.glPushMatrix();
        GL11.glTranslatef(JukeboxModel.DECK_X, JukeboxModel.DECK_Y, JukeboxModel.DECK_Z);
        GL11.glRotatef(JukeboxModel.DECK_TILT, 1F, 0F, 0F);

        part(t, JukeboxModel.CHROME, PLATTER, light, cached);

        bind(JukeboxModel.disc(tier));
        // Grooves at 512 sampled onto a disc a few hundred pixels across is
        // exactly where nearest-neighbour turns fine rings into moire.
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
        boolean wasAlpha = GL11.glIsEnabled(GL11.GL_ALPHA_TEST);
        GL11.glEnable(GL11.GL_ALPHA_TEST);
        GL11.glAlphaFunc(GL11.GL_GREATER, 0.35F);
        GL11.glPushMatrix();
        GL11.glRotatef(atSpin, 0F, 0F, 1F);
        still(t, DISC, light, cached);
        GL11.glPopMatrix();
        if (!wasAlpha) GL11.glDisable(GL11.GL_ALPHA_TEST);

        // The arm rides the deck, not the record: same frame, no spin.
        part(t, JukeboxModel.CHROME, TONEARM, light, cached);
        GL11.glPopMatrix();
    }

    /** The glazing: its sheet is highlights and nothing else, cut with alpha. */
    private static void glazing(Tessellator t, int light, boolean cached) {
        bind(JukeboxModel.GLASS);
        boolean wasAlpha = GL11.glIsEnabled(GL11.GL_ALPHA_TEST);
        GL11.glEnable(GL11.GL_ALPHA_TEST);
        GL11.glAlphaFunc(GL11.GL_GREATER, 0.5F);
        still(t, GLAZING, light, cached);
        if (!wasAlpha) GL11.glDisable(GL11.GL_ALPHA_TEST);
    }

    /**
     * The chrome trim, reflecting its surroundings.
     *
     * Without a shader pack the fixed-function pipeline can generate texture
     * coordinates from each vertex's eye-space normal, which turns the
     * environment sheet into a reflection that moves as you walk round the
     * cabinet -- the thing that separates chrome from grey paint. A shader pack
     * replaces that pipeline with GLSL and ignores glTexGen outright, so there it
     * falls back to the ordinary chrome ramp and looks exactly as it did.
     */
    private static void chromePass(Tessellator t, int light, boolean cached) {
        boolean reflect = !com.questforge.content.client.Shaders.active();
        if (reflect) {
            bind(JukeboxModel.ENV);
            GL11.glTexGeni(GL11.GL_S, GL11.GL_TEXTURE_GEN_MODE, GL11.GL_SPHERE_MAP);
            GL11.glTexGeni(GL11.GL_T, GL11.GL_TEXTURE_GEN_MODE, GL11.GL_SPHERE_MAP);
            GL11.glEnable(GL11.GL_TEXTURE_GEN_S);
            GL11.glEnable(GL11.GL_TEXTURE_GEN_T);
        } else {
            bind(JukeboxModel.CHROME);
        }
        still(t, CHROME, light, cached);
        if (reflect) {
            GL11.glDisable(GL11.GL_TEXTURE_GEN_S);
            GL11.glDisable(GL11.GL_TEXTURE_GEN_T);
        }
    }

    // ------------------------------------------------------------------
    // Clock and world
    // ------------------------------------------------------------------

    /** Advances the shared clock, once per frame. */
    private static void tick(long frame) {
        if (frame == clockFrame) return;
        clockFrame = frame;
        long now = System.nanoTime();
        if (lastNanos == 0L) lastNanos = now;
        float dt = (now - lastNanos) / 1.0e9F;
        lastNanos = now;
        // A paused game should not wind the sweep forward by a minute.
        if (dt > 0.2F) dt = 0.2F;
        boolean anyLive = System.currentTimeMillis() - liveSeen < 250L;
        phase += dt * (anyLive ? PLAY_RATE : IDLE_RATE);
        if (phase >= PHASE_PERIOD) phase -= PHASE_PERIOD;
        if (anyLive) {
            spin += dt * SPIN_DPS;
            if (spin >= 360F) spin -= 360F;
        }
    }

    /** The phase the item renderer draws at. */
    static float phase() {
        return phase;
    }

    /** The best light reaching the cabinet, taken from the air around it. */
    private static int brightest(TileEntity te) {
        net.minecraft.world.World w = te.getWorldObj();
        int x = te.xCoord, y = te.yCoord, z = te.zCoord;
        int best = w.getLightBrightnessForSkyBlocks(x, y + 2, z, 0);
        best = Math.max(best, w.getLightBrightnessForSkyBlocks(x + 1, y + 1, z, 0));
        best = Math.max(best, w.getLightBrightnessForSkyBlocks(x - 1, y + 1, z, 0));
        best = Math.max(best, w.getLightBrightnessForSkyBlocks(x, y + 1, z + 1, 0));
        best = Math.max(best, w.getLightBrightnessForSkyBlocks(x, y + 1, z - 1, 0));
        return best;
    }

    private static void bind(ResourceLocation tex) {
        Minecraft.getMinecraft().getTextureManager().bindTexture(tex);
    }

    /**
     * True while this client is hearing something out of this block.
     *
     * The source position is the lower half's centre, which is what the block
     * hands the audio layer -- the same triple, or this never matches.
     */
    private static boolean playing(TileEntity te) {
        return DirectAudio.isActive()
                && JukeboxTicker.isSourceAt(te.xCoord + 0.5D,
                                            te.yCoord + 0.5D,
                                            te.zCoord + 0.5D);
    }
}
