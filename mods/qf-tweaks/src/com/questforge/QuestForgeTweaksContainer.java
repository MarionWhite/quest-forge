package com.questforge;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Arrays;

import com.google.common.eventbus.EventBus;

import cpw.mods.fml.common.DummyModContainer;
import cpw.mods.fml.common.LoadController;
import cpw.mods.fml.common.ModMetadata;

/**
 * Gives the coremod a mod entry of its own, so it has a version that shows in the
 * mod list and travels in the login handshake.
 *
 * Without it qf-tweaks was invisible to everything that compares packs: a coremod
 * with no container is not in Loader's mod list, so neither FML nor qf-content's
 * pack check could tell a September jar from an October one, even though the
 * grave and Morph fixes live here.
 *
 * FML does not enforce this version itself (a DummyModContainer registers no
 * network checker), which is what we want: a server without qf-tweaks still
 * accepts clients that have it. qf-content's pack check compares it whenever
 * both sides have it.
 *
 * The version is written into the jar by build.bat (qftweaks-version.txt), from
 * the last git commit that touched mods/qf-tweaks.
 */
public class QuestForgeTweaksContainer extends DummyModContainer {

    public QuestForgeTweaksContainer() {
        super(metadata());
    }

    private static ModMetadata metadata() {
        ModMetadata m = new ModMetadata();
        m.modId = "qftweaks";
        m.name = "QuestForge Tweaks";
        m.version = readVersion();
        m.description = "Quest Forge's coremod: bytecode fixes for other mods "
                + "(BetterQuesting, GraveStones, Morph, CustomMenu, LittleMaidMob, Lucky Block, Decocraft).";
        m.authorList = Arrays.asList("suaz");
        return m;
    }

    private static String readVersion() {
        InputStream in = QuestForgeTweaksContainer.class.getResourceAsStream("/qftweaks-version.txt");
        if (in == null) return "1.1.0+unknown";
        try {
            BufferedReader r = new BufferedReader(new InputStreamReader(in, "UTF-8"));
            String line = r.readLine();
            r.close();
            return (line == null || line.trim().isEmpty()) ? "1.1.0+unknown" : line.trim();
        } catch (Exception e) {
            return "1.1.0+unknown";
        }
    }

    /** True, or FML leaves the container out of the active mod list. */
    @Override
    public boolean registerBus(EventBus bus, LoadController controller) {
        return true;
    }
}
