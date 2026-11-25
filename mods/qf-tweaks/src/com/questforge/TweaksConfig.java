package com.questforge;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Properties;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * config/qftweaks.cfg: the switches for this coremod's optional patches.
 *
 * Read at the first transform that needs a switch, which is during coremod
 * loading -- before Forge's own Configuration class is safe to use, so this is
 * a plain java.util.Properties file. The game dir comes from the coremod's
 * injectData (QuestForgeCore.gameDir); without it (unit runs) the file is
 * looked for relative to the working directory, which is the game dir too.
 *
 * A missing file is written with the defaults, so the switches are
 * discoverable. A system property of the same purpose (-Dqf.decolazy=false)
 * wins over the file: that is how trials A/B a patch without editing config.
 */
public final class TweaksConfig {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private static final String FILE = "qftweaks.cfg";

    private static final String KEY_DECO_LAZY = "decocraft.lazyModels";

    private static Properties props;

    private TweaksConfig() {
    }

    /** Decocraft props keep their model data only while needed (DecoLazyTransformer). */
    public static boolean decocraftLazyModels() {
        return flag(KEY_DECO_LAZY, "qf.decolazy", true);
    }

    private static synchronized boolean flag(String key, String sysProp, boolean dflt) {
        String o = System.getProperty(sysProp);
        if (o != null && !o.trim().isEmpty()) {
            return Boolean.parseBoolean(o.trim());
        }
        String v = load().getProperty(key);
        return v == null ? dflt : Boolean.parseBoolean(v.trim());
    }

    private static Properties load() {
        if (props != null) {
            return props;
        }
        props = new Properties();
        File dir = QuestForgeCore.gameDir != null ? new File(QuestForgeCore.gameDir, "config") : new File("config");
        File f = new File(dir, FILE);
        if (f.isFile()) {
            InputStream in = null;
            try {
                in = new FileInputStream(f);
                props.load(in);
            } catch (IOException e) {
                LOG.warn("[QuestForgeTweaks] could not read " + f + "; using defaults", e);
            } finally {
                close(in);
            }
        }
        if (!props.containsKey(KEY_DECO_LAZY)) {
            props.setProperty(KEY_DECO_LAZY, "true");
            write(f, dir);
        }
        return props;
    }

    private static void write(File f, File dir) {
        OutputStream out = null;
        try {
            if (!dir.isDirectory() && !dir.mkdirs()) {
                return;
            }
            out = new FileOutputStream(f);
            props.store(out, "QuestForgeTweaks switches. -Dqf.<name> on the command line overrides a line here.\n"
                    + " decocraft.lazyModels: Decocraft keeps about 550 MB of prop models in memory from startup on;\n"
                    + "   true frees them after startup and rebuilds a prop's model the first time it is drawn or\n"
                    + "   collided with (-Dqf.decolazy=false switches it off for one launch).");
            LOG.info("[QuestForgeTweaks] wrote {}", f);
        } catch (IOException e) {
            LOG.warn("[QuestForgeTweaks] could not write " + f, e);
        } finally {
            close(out);
        }
    }

    private static void close(java.io.Closeable c) {
        if (c != null) {
            try {
                c.close();
            } catch (IOException ignored) {
                // nothing to do
            }
        }
    }
}
