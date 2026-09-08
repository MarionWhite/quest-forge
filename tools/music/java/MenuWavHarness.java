import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.Clip;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.Line;
import javax.sound.sampled.SourceDataLine;

/**
 * Java 8 proof that menu.wav opens the same way SplashMusic does.
 * Does not play through speakers for more than a short Clip.start pulse.
 */
public final class MenuWavHarness {
    public static void main(String[] args) throws Exception {
        File f = new File(args.length > 0 ? args[0]
                : "/Users/suaz/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/resources/assets/minecraft/sounds/music/menu.wav");
        System.out.println("file=" + f.getAbsolutePath() + " exists=" + f.isFile() + " bytes=" + f.length());
        AudioInputStream in = AudioSystem.getAudioInputStream(new BufferedInputStream(new FileInputStream(f)));
        AudioFormat base = in.getFormat();
        System.out.println("format=" + base);
        AudioFormat pcm = new AudioFormat(
                AudioFormat.Encoding.PCM_SIGNED,
                base.getSampleRate(),
                16,
                base.getChannels(),
                base.getChannels() * 2,
                base.getSampleRate(),
                false);
        if (!base.matches(pcm)) {
            in = AudioSystem.getAudioInputStream(pcm, in);
            System.out.println("converted=" + in.getFormat());
        }
        Line.Info clipInfo = new DataLine.Info(Clip.class, in.getFormat());
        Line.Info sdlInfo = new DataLine.Info(SourceDataLine.class, in.getFormat());
        System.out.println("clipSupported=" + AudioSystem.isLineSupported(clipInfo));
        System.out.println("sdlSupported=" + AudioSystem.isLineSupported(sdlInfo));
        Clip c = AudioSystem.getClip();
        c.open(in);
        in.close();
        System.out.println("clipOpen frames=" + c.getFrameLength() + " us=" + c.getMicrosecondLength());
        if (c.getFrameLength() > 1) {
            c.setLoopPoints(0, c.getFrameLength() - 1);
        }
        c.start();
        Thread.sleep(400);
        boolean running = c.isRunning();
        boolean active = c.isActive();
        c.stop();
        c.close();
        System.out.println("clipPulse running=" + running + " active=" + active + " OK");
    }
}
