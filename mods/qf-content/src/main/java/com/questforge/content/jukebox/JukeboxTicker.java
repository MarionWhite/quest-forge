package com.questforge.content.jukebox;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import net.minecraft.client.Minecraft;
import net.minecraft.client.audio.ISound;
import net.minecraft.client.audio.SoundCategory;

/**
 * Keeps the audio stream fed, every client tick.
 *
 * This is not optional bookkeeping: an OpenAL streaming source that stops being
 * refilled underruns and goes silent within a fraction of a second, so this runs
 * unconditionally and as early as possible in the tick.
 *
 * It also remembers which block the current sound belongs to, so breaking a jukebox
 * or leaving the world stops the music instead of leaving it playing in mid-air,
 * and it ducks Minecraft's own music while a jukebox is audible.
 */
public class JukeboxTicker {

    /**
     * How loud the jukebox must be before the game's own music is silenced. Well
     * above zero so the far edge of the jukebox's range, where it is barely
     * audible, does not leave a huge dead zone with no music of any kind.
     */
    private static final float DUCK_THRESHOLD = 0.12f;

    private static double sx, sy, sz;
    private static boolean haveSource;

    private static boolean ducked;
    private static float restoreMusicLevel;
    private static boolean checkedStash;

    public static void setSource(double x, double y, double z) {
        sx = x; sy = y; sz = z; haveSource = true;
    }

    public static void clearSource() { haveSource = false; }

    public static boolean isSourceAt(double x, double y, double z) {
        return haveSource && Math.abs(sx - x) < 0.01
                          && Math.abs(sy - y) < 0.01
                          && Math.abs(sz - z) < 0.01;
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;

        // Anything that finished loading on a worker starts here, on the thread
        // that owns the OpenAL context.
        Playback.pump();

        Minecraft game = Minecraft.getMinecraft();

        if (!checkedStash) recoverStashedMusicLevel(game);

        // Before the spatial update, not after: this moves the anchor a carried
        // speaker sounds from, and setting it afterwards would leave every frame
        // positioned from where the player stood a tick ago.
        checkSpeakerStillHeld(game);

        // Distance volume and how directional the sound is are both recomputed from
        // where the player is standing and which way they are facing.
        if (game.renderViewEntity != null) {
            DirectAudio.updateSpatial(game.renderViewEntity.posX,
                                      game.renderViewEntity.posY,
                                      game.renderViewEntity.posZ,
                                      game.renderViewEntity.rotationYaw);
        }

        boolean wasActive = DirectAudio.isActive();
        DirectAudio.tick();
        // A track that ran to its end either loops or clears the now-playing bar.
        if (wasActive && !DirectAudio.isActive()) {
            Playback.finished();
            if (!DirectAudio.isActive() && Playback.loading() == null) clearSource();
        }

        checkSourceStillThere(game);
        updateDucking(game);

        // Leaving the world must not leave a source playing into a dead context,
        // nor carry one server's shared playlists into the next.
        if (game.theWorld == null) {
            if (DirectAudio.isActive()) Playback.stop();
            if (PublicCache.ready()) PublicCache.clear();
        }
    }

    /**
     * Keeps a portable speaker sounding from its owner, and only while they hold it.
     *
     * Two jobs, because they are the same question asked every tick. The anchor is
     * dragged to the player so the source walks with them -- an anchor sitting on the
     * listener resolves through the audio engine's own maths to full volume and no
     * direction, which is what a speaker on your shoulder should sound like.
     *
     * And putting the speaker away stops it. The music is suspended rather than
     * dropped, so drawing a sword and putting it back does not lose your place; that
     * is the difference between a speaker you can carry and one you have to keep
     * restarting.
     */
    private void checkSpeakerStillHeld(Minecraft game) {
        if (!Speakers.isSpeaker()) return;
        if (game.thePlayer == null) return;

        // A speaker has no block behind it, but Playback registers a source position
        // regardless -- and for a speaker that position is wherever the player was
        // standing when the track opened. Left registered, checkSourceStillThere
        // looks that spot up, finds air rather than a jukebox, and suspends; the next
        // tick sees the speaker still held and resumes; and because a stream whose
        // server ignores range requests restarts from the top, the track loops its
        // first half second forever. Clearing it states the true thing -- there is no
        // block -- and takes that check and breakBlock's out of the picture at once.
        clearSource();

        String want = Speakers.active();
        net.minecraft.item.ItemStack held = game.thePlayer.getHeldItem();
        boolean holding = held != null
                && held.getItem() == com.questforge.content.ModItems.speaker
                && want.equals(ItemSpeaker.id(held));

        if (holding) {
            DirectAudio.setPosition(game.thePlayer.posX, game.thePlayer.posY,
                                    game.thePlayer.posZ);
            Playback.moveTo(game.thePlayer.posX, game.thePlayer.posY,
                            game.thePlayer.posZ);
            // Picking it back up carries on from where it left off.
            if (!DirectAudio.isActive() && Playback.hasSuspended()
                    && Playback.loading() == null) {
                Playback.resumeSuspended(game.thePlayer.posX, game.thePlayer.posY,
                                         game.thePlayer.posZ);
            }
            return;
        }

        if (DirectAudio.isActive() || Playback.loading() != null) Playback.suspend();
    }

    /** Ticks between checks that the jukebox is still standing. */
    private static final int SOURCE_CHECK_INTERVAL = 10;
    private static int sourceCheckTimer;

    /**
     * Suspends playback when the block it belongs to stops being a jukebox.
     *
     * Block.breakBlock covers a player mining it and nothing else. A jukebox that
     * goes up with a creeper, gets replaced by a piston, or is removed by a command
     * never runs it -- and the music carrying on from an empty patch of air is the
     * same bug however the block left.
     */
    private void checkSourceStillThere(Minecraft game) {
        if (!haveSource || !DirectAudio.isActive()) return;
        if (++sourceCheckTimer < SOURCE_CHECK_INTERVAL) return;
        sourceCheckTimer = 0;

        if (game.theWorld == null) return;

        int x = net.minecraft.util.MathHelper.floor_double(sx);
        int y = net.minecraft.util.MathHelper.floor_double(sy);
        int z = net.minecraft.util.MathHelper.floor_double(sz);

        // Out of loaded range is not gone -- it is just too far away to ask about,
        // and it is silent out there anyway.
        if (!game.theWorld.blockExists(x, y, z)) return;

        if (!(game.theWorld.getBlock(x, y, z) instanceof BlockJukebox)) {
            Playback.suspend();
        }
    }

    /**
     * Silences the game's background music while the jukebox is playing nearby.
     *
     * This goes through GameSettings rather than SoundHandler, which looks like the
     * more invasive choice and is in fact the only one that works.
     * SoundManager.setSoundCategoryVolume ignores the level it is handed for every
     * category except MASTER: it recomputes each playing sound from
     * options.getSoundLevel instead. So calling the sound handler with zero is
     * discarded, and the music simply keeps playing.
     *
     * Writing the level into GameSettings is what the engine actually reads, and it
     * stops the playing music as a side effect. The player's own value is captured
     * first and handed back on the way out, so their setting survives -- including
     * across a crash, via the stash in {@link JukeboxSettings}.
     */
    private void updateDucking(Minecraft game) {
        if (game.gameSettings == null || game.getSoundHandler() == null) return;

        boolean shouldDuck = DirectAudio.isActive()
                && !DirectAudio.isPaused()
                && DirectAudio.audibleLevel() >= DUCK_THRESHOLD;

        if (shouldDuck) {
            if (!ducked) {
                restoreMusicLevel = game.gameSettings.getSoundLevel(SoundCategory.MUSIC);
                // Recorded before the change, so a crash mid-duck is recoverable.
                JukeboxSettings.stashMusicLevel(Float.valueOf(restoreMusicLevel));
                ducked = true;
                com.questforge.content.QuestForgeContent.log.info(
                        "[jukebox] ducking game music (was " + restoreMusicLevel + ")");
            }
            // Re-asserted every tick rather than once on the way in. Anything that
            // writes the level back -- the options screen, another mod, the game
            // itself -- would otherwise silently undo this and the music would
            // return for good.
            if (game.gameSettings.getSoundLevel(SoundCategory.MUSIC) != 0f) {
                game.gameSettings.setSoundLevel(SoundCategory.MUSIC, 0f);
            }
            stopPlayingMusic(game);

        } else if (ducked) {
            game.gameSettings.setSoundLevel(SoundCategory.MUSIC, restoreMusicLevel);
            JukeboxSettings.clearMusicStash();
            ducked = false;
            com.questforge.content.QuestForgeContent.log.info(
                    "[jukebox] restored game music to " + restoreMusicLevel);
        }
    }

    /**
     * Stops whatever music is already sounding.
     *
     * Setting the level to zero keeps new music from starting, but a track that
     * was already playing when the jukebox started is a separate problem: it is
     * mid-stream in the sound system and nothing recomputes its volume on its own.
     * MusicTicker holds that sound, so it is asked for it directly.
     */
    private void stopPlayingMusic(Minecraft game) {
        ISound music = MusicTickerAccess.currentMusic(game);
        if (music == null) return;
        if (!game.getSoundHandler().isSoundPlaying(music)) return;
        game.getSoundHandler().stopSound(music);
    }

    /** Diagnostic state, for /jb duck. */
    public static String[] duckDiag(Minecraft game) {
        return new String[] {
            "audio active : " + DirectAudio.isActive() + "  paused=" + DirectAudio.isPaused(),
            "audible      : " + DirectAudio.audibleLevel() + "   (duck at " + DUCK_THRESHOLD + ")",
            "ducked flag  : " + ducked + "   saved level=" + restoreMusicLevel,
            "MUSIC level  : " + (game.gameSettings == null ? "?"
                    : String.valueOf(game.gameSettings.getSoundLevel(SoundCategory.MUSIC))),
            "MC music     : " + MusicTickerAccess.describe(game)
        };
    }

    /**
     * Gives back a music level left at zero by a crash while ducked. Runs once,
     * on the first tick, before anything can duck again.
     */
    private void recoverStashedMusicLevel(Minecraft game) {
        checkedStash = true;
        if (game.gameSettings == null) return;

        Float stashed = JukeboxSettings.stashedMusicLevel();
        if (stashed == null) return;

        game.gameSettings.setSoundLevel(SoundCategory.MUSIC, stashed.floatValue());
        JukeboxSettings.clearMusicStash();
    }
}
