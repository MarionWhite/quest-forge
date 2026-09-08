import java.io.*;
import java.nio.file.Files;
import java.util.zip.*;
import org.objectweb.asm.*;

/** In CustomMenu's mainmenuserver/MainMenuFix.func_73863_a (drawScreen), the 4th and 5th
 *  INVOKEVIRTUAL MainMenuFix.drawTexturedModalRect(IIII)V (the visible button pass, drawn after the background)
 *  become INVOKESTATIC qf/menu/QFButtons.drawButton(Lmainmenuserver/MainMenuFix;IIII)V.
 *  Usage: PatchMenu <in.jar> <out.jar> <QFButtons.class> [extra files as jarpath=file ...] */
public class PatchMenu {
    static final String TARGET = "mainmenuserver/MainMenuFix.class";
    static int seen, replaced;

    public static void main(String[] args) throws Exception {
        File in = new File(args[0]), out = new File(args[1]);
        java.util.Map<String, byte[]> extra = new java.util.LinkedHashMap<String, byte[]>();
        extra.put("qf/menu/QFButtons.class", Files.readAllBytes(new File(args[2]).toPath()));
        for (int i = 3; i < args.length; i++) {
            String[] kv = args[i].split("=", 2);
            extra.put(kv[0], Files.readAllBytes(new File(kv[1]).toPath()));
        }
        boolean found = false;
        try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(in)));
             ZipOutputStream zout = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(out)))) {
            ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                byte[] data = readAll(zin);
                String name = e.getName();
                if (extra.containsKey(name)) continue;
                if (name.equals(TARGET)) { data = transform(data); found = true; }
                ZipEntry ne = new ZipEntry(name); ne.setTime(e.getTime());
                zout.putNextEntry(ne); zout.write(data); zout.closeEntry();
            }
            for (java.util.Map.Entry<String, byte[]> x : extra.entrySet()) {
                zout.putNextEntry(new ZipEntry(x.getKey())); zout.write(x.getValue()); zout.closeEntry();
            }
        }
        if (!found) throw new IllegalStateException("MainMenuFix not found");
        if (seen != 5 || replaced != 2) throw new IllegalStateException("unexpected counts seen=" + seen + " replaced=" + replaced);
        System.out.println("patched MainMenuFix.drawScreen: " + replaced + " of " + seen + " plate draws redirected; added " + extra.keySet());
    }

    static byte[] transform(byte[] cls) {
        ClassReader cr = new ClassReader(cls);
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cr.accept(new ClassVisitor(Opcodes.ASM5, cw) {
            @Override public MethodVisitor visitMethod(int acc, String name, String desc, String sig, String[] ex) {
                MethodVisitor mv = super.visitMethod(acc, name, desc, sig, ex);
                if (!(name.equals("func_73863_a") && desc.equals("(IIF)V"))) return mv;
                return new MethodVisitor(Opcodes.ASM5, mv) {
                    @Override public void visitMethodInsn(int op, String owner, String mname, String mdesc, boolean itf) {
                        if (op == Opcodes.INVOKEVIRTUAL && owner.equals("mainmenuserver/MainMenuFix")
                                && mname.equals("drawTexturedModalRect") && mdesc.equals("(IIII)V")) {
                            int idx = seen++;
                            if (idx == 3 || idx == 4) {
                                replaced++;
                                // local 11 is the mod's buttonTextures index j; pass it so QFButtons knows which button this is
                                super.visitVarInsn(Opcodes.ILOAD, 11);
                                super.visitMethodInsn(Opcodes.INVOKESTATIC, "qf/menu/QFButtons", "drawButton", "(Lmainmenuserver/MainMenuFix;IIIII)V", false);
                                return;
                            }
                        }
                        super.visitMethodInsn(op, owner, mname, mdesc, itf);
                    }
                };
            }
        }, 0);
        return cw.toByteArray();
    }

    static byte[] readAll(InputStream is) throws IOException {
        ByteArrayOutputStream bo = new ByteArrayOutputStream(); byte[] b = new byte[65536]; int n;
        while ((n = is.read(b)) > 0) bo.write(b, 0, n);
        return bo.toByteArray();
    }
}
