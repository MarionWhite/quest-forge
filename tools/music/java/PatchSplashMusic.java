import java.nio.file.Files;
import java.nio.file.Paths;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/**
 * Prepends INVOKESTATIC SplashMusic.start/stop to SplashProgress.start/finish.
 * Writes a patched class file only — does not touch the jar.
 *
 * Usage: PatchSplashMusic <SplashProgress.in> <SplashProgress.out>
 */
public class PatchSplashMusic {
    public static void main(String[] args) throws Exception {
        byte[] in = Files.readAllBytes(Paths.get(args[0]));
        final int[] hits = new int[2];
        ClassReader cr = new ClassReader(in);
        ClassWriter cw = new ClassWriter(cr, 0);
        cr.accept(new org.objectweb.asm.ClassVisitor(Opcodes.ASM5, cw) {
            @Override
            public MethodVisitor visitMethod(int access, final String name, String desc, String sig, String[] ex) {
                MethodVisitor mv = super.visitMethod(access, name, desc, sig, ex);
                if (!"()V".equals(desc) || (!"start".equals(name) && !"finish".equals(name))) {
                    return mv;
                }
                return new MethodVisitor(Opcodes.ASM5, mv) {
                    @Override
                    public void visitCode() {
                        super.visitCode();
                        String callee = "start".equals(name) ? "start" : "stop";
                        super.visitMethodInsn(Opcodes.INVOKESTATIC, "qf/splash/SplashMusic", callee, "()V", false);
                        hits["start".equals(name) ? 0 : 1]++;
                    }
                };
            }
        }, 0);
        if (hits[0] != 1 || hits[1] != 1) {
            throw new IllegalStateException("expected one start and one finish inject, got start=" + hits[0] + " finish=" + hits[1]);
        }
        byte[] out = cw.toByteArray();
        Files.write(Paths.get(args[1]), out);
        System.out.println("patched SplashProgress start+finish " + in.length + " -> " + out.length);
    }
}
