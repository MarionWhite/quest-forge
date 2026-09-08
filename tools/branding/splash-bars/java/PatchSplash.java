import java.io.*;
import java.nio.file.Files;
import java.util.*;
import java.util.zip.*;

import org.objectweb.asm.*;

/**
 * Rewrites cpw/mods/fml/client/SplashProgress$3.drawBar in a Forge 1.7.10 universal jar:
 *   INVOKESPECIAL SplashProgress$3.drawBox(II)V   -> INVOKESTATIC qf/splash/QFBars.drawBox(Ljava/lang/Object;II)V  (x3)
 *   first INVOKESTATIC GL11.glScalef(FFF)V        -> INVOKESTATIC qf/splash/QFBars.beginBar(FFF)V                (x1)
 * and adds qf/splash/QFBars.class to the jar. Usage: PatchSplash <in.jar> <out.jar> <QFBars.class>
 */
public class PatchSplash {
    static final String TARGET = "cpw/mods/fml/client/SplashProgress$3.class";
    static int boxCount, scaleCount;

    public static void main(String[] args) throws Exception {
        File in = new File(args[0]), out = new File(args[1]), helper = new File(args[2]);
        byte[] helperBytes = Files.readAllBytes(helper.toPath());
        boolean found = false;
        try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(in)));
             ZipOutputStream zout = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(out)))) {
            ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                byte[] data = readAll(zin);
                String name = e.getName();
                if (name.equals("qf/splash/QFBars.class")) continue;          // replaced below
                if (name.equals(TARGET)) { data = transform(data); found = true; }
                ZipEntry ne = new ZipEntry(name);
                ne.setTime(e.getTime());
                zout.putNextEntry(ne); zout.write(data); zout.closeEntry();
            }
            ZipEntry he = new ZipEntry("qf/splash/QFBars.class");
            zout.putNextEntry(he); zout.write(helperBytes); zout.closeEntry();
        }
        if (!found) throw new IllegalStateException("target class not found in jar");
        if (boxCount != 3 || scaleCount != 1)
            throw new IllegalStateException("unexpected patch counts: drawBox=" + boxCount + " glScalef=" + scaleCount);
        System.out.println("patched " + TARGET + ": drawBox x" + boxCount + ", beginBar x" + scaleCount + " -> " + out);
    }

    static byte[] transform(byte[] cls) {
        ClassReader cr = new ClassReader(cls);
        ClassWriter cw = new ClassWriter(0);
        cr.accept(new ClassVisitor(Opcodes.ASM5, cw) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] ex) {
                MethodVisitor mv = super.visitMethod(access, name, desc, sig, ex);
                if (!name.equals("drawBar")) return mv;
                return new MethodVisitor(Opcodes.ASM5, mv) {
                    boolean scaled;
                    @Override
                    public void visitMethodInsn(int op, String owner, String mname, String mdesc, boolean itf) {
                        if (op == Opcodes.INVOKESPECIAL && owner.equals("cpw/mods/fml/client/SplashProgress$3")
                                && mname.equals("drawBox") && mdesc.equals("(II)V")) {
                            boxCount++;
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, "qf/splash/QFBars", "drawBox", "(Ljava/lang/Object;II)V", false);
                            return;
                        }
                        if (!scaled && op == Opcodes.INVOKESTATIC && owner.equals("org/lwjgl/opengl/GL11")
                                && mname.equals("glScalef") && mdesc.equals("(FFF)V")) {
                            scaled = true; scaleCount++;
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, "qf/splash/QFBars", "beginBar", "(FFF)V", false);
                            return;
                        }
                        super.visitMethodInsn(op, owner, mname, mdesc, itf);
                    }
                };
            }
        }, 0);
        return cw.toByteArray();
    }

    static byte[] readAll(InputStream is) throws IOException {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] b = new byte[65536]; int n;
        while ((n = is.read(b)) > 0) bo.write(b, 0, n);
        return bo.toByteArray();
    }
}
