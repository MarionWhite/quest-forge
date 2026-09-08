package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;
import net.minecraft.client.audio.ISound;
import net.minecraft.client.audio.MusicTicker;

import java.lang.reflect.Field;

/**
 * Reaches the background music track Minecraft is currently playing.
 *
 * MusicTicker keeps its current sound private and Minecraft keeps the ticker
 * private, but stopping music that is already sounding needs that object --
 * lowering the category volume only governs what starts next, not what is already
 * mid-stream.
 *
 * Fields are located by TYPE, never by name. Names differ between the development
 * workspace and the reobfuscated jar the pack loads, so a name lookup would work
 * here and silently return nothing where it matters.
 */
public final class MusicTickerAccess {

    private static boolean resolved;
    private static Field tickerField;    // Minecraft -> MusicTicker
    private static Field musicField;     // MusicTicker -> ISound

    private MusicTickerAccess() { }

    private static void resolve() {
        if (resolved) return;
        resolved = true;
        try {
            for (Field f : Minecraft.class.getDeclaredFields()) {
                if (MusicTicker.class.isAssignableFrom(f.getType())) {
                    f.setAccessible(true);
                    tickerField = f;
                    break;
                }
            }
            for (Field f : MusicTicker.class.getDeclaredFields()) {
                if (ISound.class.isAssignableFrom(f.getType())) {
                    f.setAccessible(true);
                    musicField = f;
                    break;
                }
            }
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not reach the music ticker; "
                    + "music already playing will not be interrupted", t);
        }
    }

    /** The music track currently held by the game, or null if there is none. */
    public static ISound currentMusic(Minecraft game) {
        resolve();
        if (tickerField == null || musicField == null || game == null) return null;
        try {
            Object ticker = tickerField.get(game);
            if (ticker == null) return null;
            return (ISound) musicField.get(ticker);
        } catch (Throwable t) {
            return null;
        }
    }

    /** Human-readable state, for the diagnostic command. */
    public static String describe(Minecraft game) {
        resolve();
        if (tickerField == null) return "ticker field not found";
        if (musicField == null) return "music field not found";

        ISound music = currentMusic(game);
        if (music == null) return "none held";

        boolean playing = game.getSoundHandler() != null
                && game.getSoundHandler().isSoundPlaying(music);
        return music.getPositionedSoundLocation() + (playing ? "  PLAYING" : "  stopped");
    }
}
