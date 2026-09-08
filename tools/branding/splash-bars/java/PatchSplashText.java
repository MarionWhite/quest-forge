import java.io.File;
import java.nio.file.Files;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/**
 * Surgical splash-text patches. Writes class files only — do not use this to rewrite a jar.
 *
 * SplashProgress$3.drawBar: FontRenderer.b(text,x,y,0) overwrites the GL font colour with
 * opaque black. Replace that 0 with SplashProgress.access$1000() (splash.properties font=).
 *
 * SplashFontRenderer.getResourceInputStream: FontRenderer measures glyph widths from the
 * main resource manager (vanilla ascii.png) while the splash binds the HD font from
 * resources/. Point the stream at SplashProgress.access$1600 so widths match the drawn atlas.
 *
 * Usage: PatchSplashText <SplashProgress$3.in> <SplashProgress$3.out>
 *                       <SplashFontRenderer.in> <SplashFontRenderer.out>
 */
public class PatchSplashText {
    static int colorFixes, streamFixes;

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException("PatchSplashText $3.in $3.out Font.in Font.out");
        }
        Files.write(new File(args[1]).toPath(), patchDrawBar(Files.readAllBytes(new File(args[0]).toPath())));
        Files.write(new File(args[3]).toPath(), patchFontStream(Files.readAllBytes(new File(args[2]).toPath())));
        if (colorFixes != 2 || streamFixes != 1) {
            throw new IllegalStateException("unexpected patch counts color=" + colorFixes + " stream=" + streamFixes);
        }
        System.out.println("patched drawString colour x" + colorFixes + ", font stream x" + streamFixes);
    }

    static byte[] patchDrawBar(byte[] cls) {
        ClassReader cr = new ClassReader(cls);
        ClassWriter cw = new ClassWriter(0);
        cr.accept(new ClassVisitor(Opcodes.ASM5, cw) {
            @Override
            public MethodVisitor visitMethod(int acc, String name, String desc, String sig, String[] ex) {
                MethodVisitor mv = super.visitMethod(acc, name, desc, sig, ex);
                if (!name.equals("drawBar")) return mv;
                return new MethodVisitor(Opcodes.ASM5, mv) {
                    @Override
                    public void visitMethodInsn(int op, String owner, String mname, String mdesc, boolean itf) {
                        if (op == Opcodes.INVOKEVIRTUAL
                                && owner.equals("cpw/mods/fml/client/SplashProgress$SplashFontRenderer")
                                && mname.equals("b")
                                && mdesc.equals("(Ljava/lang/String;III)I")) {
                            colorFixes++;
                            super.visitInsn(Opcodes.POP);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC,
                                    "cpw/mods/fml/client/SplashProgress",
                                    "access$1000", "()I", false);
                        }
                        super.visitMethodInsn(op, owner, mname, mdesc, itf);
                    }
                };
            }
        }, 0);
        return cw.toByteArray();
    }

    static byte[] patchFontStream(byte[] cls) {
        ClassReader cr = new ClassReader(cls);
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cr.accept(new ClassVisitor(Opcodes.ASM5, cw) {
            @Override
            public MethodVisitor visitMethod(int acc, String name, String desc, String sig, String[] ex) {
                if (!name.equals("getResourceInputStream")) {
                    return super.visitMethod(acc, name, desc, sig, ex);
                }
                MethodVisitor dest = super.visitMethod(acc, name, desc, sig, ex);
                dest.visitCode();
                dest.visitVarInsn(Opcodes.ALOAD, 1);
                dest.visitMethodInsn(Opcodes.INVOKESTATIC,
                        "cpw/mods/fml/client/SplashProgress",
                        "access$1600",
                        "(Lbqx;)Ljava/io/InputStream;", false);
                dest.visitInsn(Opcodes.ARETURN);
                dest.visitMaxs(1, 2);
                dest.visitEnd();
                streamFixes++;
                return new MethodVisitor(Opcodes.ASM5) {};
            }
        }, 0);
        return cw.toByteArray();
    }
}
