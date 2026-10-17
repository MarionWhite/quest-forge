package com.questforge;

import java.util.List;

import net.minecraft.launchwrapper.IClassTransformer;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

/**
 * The Quest Forge loading screen and splash music, applied to whatever Forge
 * jar the client runs, instead of living only in a hand-patched 1558 jar.
 *
 * Until 2026-10-17 the whole loading sequence was byte-patched into the
 * client's Forge 1558 universal jar (tools/branding/splash-bars/java/PatchSplash*.java,
 * tools/music/java/PatchSplashMusic.java, plus hand edits nobody scripted). The
 * Angelica client runs stock Forge 1614, so this transformer makes the same
 * changes at class-load time. Decompiling the live 1558 jar against stock
 * 1614 gives the complete list -- the two SplashProgress versions are otherwise
 * identical:
 *
 *   SplashProgress
 *     start()        head: SplashMusic.start()               (the chant)
 *     finish()       head: SplashMusic.stop()                (menu swell, chant fade)
 *     <clinit>       the upload IntBuffer 4M -> 16M ints     (the 3840x2160 mural is
 *                    8.3M pixels; stock 1614 throws BufferOverflowException on it)
 *   SplashProgress$3 (the splash thread's Runnable)
 *     run()          the logo quad (64,-16)-(576,496) -> (-1600,-840)-(2240,1320):
 *                    the mural fills the screen instead of sitting in a 512 box
 *     drawBar()      first glScalef -> QFBars.beginBar; the three drawBox -> QFBars.drawBox;
 *                    the two drawString colour arguments 0 -> fontColor
 *   SplashProgress$SplashFontRenderer
 *     getResourceInputStream   read glyph widths from the splash's own resources/
 *   SplashProgress$Texture
 *     bind()         head: the corner emblem's pulse
 *
 * The Forge-side halves (qf/splash/QFBars, SplashMusic and its two helpers)
 * now ship inside this coremod's jar, so stock Forge has them too. Each patch
 * looks for the stock code first and is skipped when it is already patched,
 * so on the OptiFine client's hand-patched 1558 jar this transformer changes
 * nothing it already had and adds only the two logging hooks:
 *
 *   SplashProgress$3.run    before Display.update: QFSplash.frame()   (first-frame log;
 *                           with -Dqf.splash.shots=DIR it also saves the frame)
 *   SplashProgress.finish   head: QFSplash.finishing()                (music hand-off log)
 *
 * Only INVOKESTATIC calls and constants are added: no branches, no locals, so
 * the stack map frames stay valid (ClassWriter(0)).
 *
 * Client only: SplashProgress never loads on a dedicated server.
 */
public class SplashTransformer implements IClassTransformer {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String SP = "cpw/mods/fml/client/SplashProgress";
    private static final String BARS = "qf/splash/QFBars";
    private static final String MUSIC = "qf/splash/SplashMusic";
    private static final String HOOK = "qf/splash/QFSplash";

    private static final int STOCK_BUF = 4194304;     // 2048 x 2048
    private static final int QF_BUF = 16777216;       // 4096 x 4096

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null || transformedName == null
                || !transformedName.startsWith("cpw.mods.fml.client.SplashProgress")) {
            return basicClass;
        }
        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, 0);

            String what;
            if (transformedName.equals("cpw.mods.fml.client.SplashProgress")) {
                what = patchMain(node);
            } else if (transformedName.equals("cpw.mods.fml.client.SplashProgress$SplashFontRenderer")) {
                what = patchFont(node);
            } else if (transformedName.equals("cpw.mods.fml.client.SplashProgress$Texture")) {
                what = patchTexture(node);
            } else if (method(node, "drawBar") != null) {
                what = patchThread(node);
            } else {
                return basicClass;
            }
            if (what == null) {
                return basicClass;
            }
            ClassWriter writer = new ClassWriter(0);
            node.accept(writer);
            LOG.info("[QuestForgeTweaks] Transform applied: {}: {}", transformedName, what);
            return writer.toByteArray();
        } catch (Throwable t) {
            LOG.warn("[QuestForgeTweaks] Splash transform failed for " + transformedName
                    + "; returning original bytes (the loading screen falls back to Forge's).", t);
            return basicClass;
        }
    }

    // ----------------------------------------------------------------- classes

    private static String patchMain(ClassNode node) {
        StringBuilder done = new StringBuilder();
        boolean patched = callsOwner(node, MUSIC);

        MethodNode start = method(node, "start");
        MethodNode finish = method(node, "finish");
        if (!patched && start != null && finish != null) {
            start.instructions.insert(staticCall(MUSIC, "start", "()V"));
            finish.instructions.insert(staticCall(MUSIC, "stop", "()V"));
            done.append("splash music; ");
        }
        if (finish != null) {
            finish.instructions.insert(staticCall(HOOK, "finishing", "()V"));
            done.append("hand-off log; ");
        }
        MethodNode clinit = method(node, "<clinit>");
        if (clinit != null) {
            for (AbstractInsnNode insn : clinit.instructions.toArray()) {
                if (insn instanceof LdcInsnNode && Integer.valueOf(STOCK_BUF).equals(((LdcInsnNode) insn).cst)
                        && isCall(insn.getNext(), "org/lwjgl/BufferUtils", "createIntBuffer")) {
                    ((LdcInsnNode) insn).cst = Integer.valueOf(QF_BUF);
                    done.append("16M-pixel texture buffer; ");
                }
            }
        }
        if (patched) done.append("(music already in this Forge jar)");
        return done.length() == 0 ? null : done.toString();
    }

    private static String patchThread(ClassNode node) {
        StringBuilder done = new StringBuilder();
        MethodNode run = method(node, "run");
        if (run != null) {
            int mural = 0, update = 0;
            for (AbstractInsnNode insn : run.instructions.toArray()) {
                if (isVertex(insn)) {
                    LdcInsnNode y = (LdcInsnNode) insn.getPrevious();
                    LdcInsnNode x = (LdcInsnNode) y.getPrevious();
                    float fx = (Float) x.cst, fy = (Float) y.cst;
                    if ((fx == 64f || fx == 576f) && (fy == -16f || fy == 496f)) {
                        x.cst = Float.valueOf(fx == 64f ? -1600f : 2240f);
                        y.cst = Float.valueOf(fy == -16f ? -840f : 1320f);
                        mural++;
                    }
                }
                if (isCall(insn, "org/lwjgl/opengl/Display", "update")) {
                    run.instructions.insertBefore(insn, staticCall(HOOK, "frame", "()V"));
                    update++;
                }
            }
            if (mural == 4) done.append("full-screen mural; ");
            else if (mural != 0) LOG.warn("[QuestForgeTweaks] splash logo quad: {} of 4 corners matched", mural);
            if (update > 0) done.append("frame hook; ");
        }

        MethodNode bar = method(node, "drawBar");
        if (bar != null && !callsOwner(node, BARS)) {
            int scale = 0, boxes = 0, colours = 0;
            for (AbstractInsnNode insn : bar.instructions.toArray()) {
                if (insn.getType() != AbstractInsnNode.METHOD_INSN) continue;
                MethodInsnNode call = (MethodInsnNode) insn;
                if (scale == 0 && "glScalef".equals(call.name) && "(FFF)V".equals(call.desc)
                        && call.getOpcode() == Opcodes.INVOKESTATIC) {
                    // GL11 normally; GLStateManager if Angelica's redirector ran first.
                    bar.instructions.set(call, staticCall(BARS, "beginBar", "(FFF)V"));
                    scale++;
                } else if (call.getOpcode() == Opcodes.INVOKESPECIAL && call.owner.equals(node.name)
                        && "drawBox".equals(call.name) && "(II)V".equals(call.desc)) {
                    bar.instructions.set(call, staticCall(BARS, "drawBox", "(Ljava/lang/Object;II)V"));
                    boxes++;
                } else if (call.getOpcode() == Opcodes.INVOKEVIRTUAL && call.owner.startsWith(SP)
                        && "(Ljava/lang/String;III)I".equals(call.desc)
                        && call.getPrevious() != null && call.getPrevious().getOpcode() == Opcodes.ICONST_0) {
                    bar.instructions.set(call.getPrevious(), staticCall(HOOK, "fontColor", "()I"));
                    colours++;
                }
            }
            if (scale == 1 && boxes == 3) done.append("textured bars; ");
            else LOG.warn("[QuestForgeTweaks] splash drawBar: {} glScalef, {} drawBox matched (want 1, 3)", scale, boxes);
            if (colours > 0) done.append(colours).append(" text colour(s); ");
        }
        return done.length() == 0 ? null : done.toString();
    }

    private static String patchFont(ClassNode node) {
        MethodNode m = method(node, "getResourceInputStream");
        if (m == null) return null;
        for (AbstractInsnNode insn : m.instructions.toArray()) {
            if (insn.getType() == AbstractInsnNode.METHOD_INSN
                    && (((MethodInsnNode) insn).owner.equals(SP) || ((MethodInsnNode) insn).owner.equals(HOOK))) {
                return null;       // already reads the splash resources
            }
        }
        InsnList body = new InsnList();
        body.add(new VarInsnNode(Opcodes.ALOAD, 1));
        body.add(staticCall(HOOK, "open", "(Ljava/lang/Object;)Ljava/io/InputStream;"));
        body.add(new InsnNode(Opcodes.ARETURN));
        m.instructions.clear();
        m.tryCatchBlocks.clear();
        if (m.localVariables != null) m.localVariables.clear();
        m.instructions.add(body);
        m.maxStack = Math.max(m.maxStack, 1);
        return "glyph widths from the splash font";
    }

    private static String patchTexture(ClassNode node) {
        MethodNode m = method(node, "bind");
        if (m == null) return null;
        for (AbstractInsnNode insn : m.instructions.toArray()) {
            if (insn.getType() == AbstractInsnNode.METHOD_INSN && ((MethodInsnNode) insn).owner.equals(SP)) {
                return null;       // the 1558 jar's pulseIfForge is already there
            }
        }
        InsnList pre = new InsnList();
        pre.add(new VarInsnNode(Opcodes.ALOAD, 0));
        pre.add(staticCall(HOOK, "pulse", "(Ljava/lang/Object;)V"));
        m.instructions.insert(pre);
        m.maxStack = Math.max(m.maxStack, 1);
        return "emblem pulse";
    }

    // ----------------------------------------------------------------- helpers

    private static MethodNode method(ClassNode node, String name) {
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            if (m.name.equals(name)) return m;
        }
        return null;
    }

    private static boolean callsOwner(ClassNode node, String owner) {
        @SuppressWarnings("unchecked")
        List<MethodNode> methods = node.methods;
        for (MethodNode m : methods) {
            for (AbstractInsnNode insn : m.instructions.toArray()) {
                if (insn.getType() == AbstractInsnNode.METHOD_INSN && ((MethodInsnNode) insn).owner.equals(owner)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static boolean isCall(AbstractInsnNode insn, String owner, String name) {
        return insn instanceof MethodInsnNode && ((MethodInsnNode) insn).owner.equals(owner)
                && ((MethodInsnNode) insn).name.equals(name);
    }

    /** LDC float, LDC float, INVOKESTATIC glVertex2f(FF)V -- GL11 or Angelica's GLStateManager. */
    private static boolean isVertex(AbstractInsnNode insn) {
        if (!(insn instanceof MethodInsnNode)) return false;
        MethodInsnNode c = (MethodInsnNode) insn;
        if (!"glVertex2f".equals(c.name) || !"(FF)V".equals(c.desc)) return false;
        AbstractInsnNode y = c.getPrevious();
        AbstractInsnNode x = y == null ? null : y.getPrevious();
        return y instanceof LdcInsnNode && x instanceof LdcInsnNode
                && ((LdcInsnNode) y).cst instanceof Float && ((LdcInsnNode) x).cst instanceof Float;
    }

    private static MethodInsnNode staticCall(String owner, String name, String desc) {
        return new MethodInsnNode(Opcodes.INVOKESTATIC, owner, name, desc, false);
    }
}
