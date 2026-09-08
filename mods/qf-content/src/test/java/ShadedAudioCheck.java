import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.spi.AudioFileReader;
import javax.sound.sampled.spi.FormatConversionProvider;
import java.util.ArrayList;
import java.util.List;
import java.util.ServiceLoader;

/**
 * Checks that the built jar can decode mp3 and Ogg on its own.
 *
 * This one is worth having because the failure it catches cannot happen in the dev
 * client. There the decoders sit on the system classpath, so playback works whatever
 * the jar contains; in a packed instance the jar is all there is. The gap between
 * those two is a whole class of bug that only ever appears on someone else's machine.
 *
 * Run with the built jar as the entire classpath, so a pass means the jar is
 * genuinely self-sufficient rather than being propped up by the build's own
 * dependencies.
 *
 * The specific trap is that mp3spi and vorbisspi declare the same two service files.
 * Copying them in with any duplicate strategy other than merging keeps one of each,
 * which leaves the jar playing exactly one of the two formats -- and nothing about
 * that failure says "packaging": it surfaces as one player's music not working.
 */
public final class ShadedAudioCheck {

    /** What the shading is supposed to have put in reach, and why each matters. */
    private static final String[][] REQUIRED = {
        { "javazoom.spi.mpeg.sampled.file.MpegAudioFileReader", "reads mp3" },
        { "javazoom.spi.vorbis.sampled.file.VorbisAudioFileReader", "reads Ogg Vorbis" },
        { "javazoom.spi.mpeg.sampled.convert.MpegFormatConversionProvider",
          "decodes mp3 to PCM" },
        { "javazoom.spi.vorbis.sampled.convert.VorbisFormatConversionProvider",
          "decodes Vorbis to PCM" },
    };

    public static void main(String[] args) {
        List<String> found = new ArrayList<String>();
        for (AudioFileReader reader : ServiceLoader.load(AudioFileReader.class)) {
            found.add(reader.getClass().getName());
        }
        for (FormatConversionProvider provider
                : ServiceLoader.load(FormatConversionProvider.class)) {
            found.add(provider.getClass().getName());
        }

        System.out.println("Service providers visible to the built jar:");
        for (String name : found) System.out.println("    " + name);

        List<String> missing = new ArrayList<String>();
        for (String[] required : REQUIRED) {
            if (!found.contains(required[0])) {
                missing.add(required[0] + "  (" + required[1] + ")");
            }
        }

        if (!missing.isEmpty()) {
            System.err.println();
            System.err.println("Missing from the built jar:");
            for (String name : missing) System.err.println("    " + name);
            System.err.println();
            System.err.println("Either the decoder libraries were not shaded in, or the "
                    + "two META-INF/services files they share were overwritten instead "
                    + "of merged. See ShadeLibraries in build.gradle.kts.");
            System.exit(1);
        }

        // Reaching a provider is not the same as being able to run it: the service
        // file can name a class whose own dependencies -- jlayer, jorbis,
        // tritonus-share -- were left out of the jar. Those are only touched once the
        // provider is asked to do something, so they are checked directly.
        //
        // Asking each converter which encodings it accepts is the closest thing to
        // running it that needs no sample file. It reads the provider's own tables,
        // which is where the decoder classes get pulled in, and unlike probing
        // isConversionSupported with a hand-built AudioFormat it does not depend on
        // Tritonus's format matching accepting a format nobody actually produced.
        requireClass("javazoom.jl.decoder.Decoder", "jlayer, the mp3 decoder");
        requireClass("com.jcraft.jorbis.Info", "jorbis, the Vorbis decoder");
        requireClass("org.tritonus.share.sampled.TAudioFormat",
                     "tritonus-share, which both providers are built on");

        // The names the providers actually advertise, read off them rather than
        // guessed: mp3spi reports "MP3", not the "MPEG1L3" that appears on the
        // individual frame encodings.
        requireEncoding("MP3", "mp3");
        requireEncoding("VORBISENC", "Ogg Vorbis");

        System.out.println();
        System.out.println("OK: the jar offers mp3 and Ogg Vorbis with nothing else "
                + "on the classpath.");
    }

    private static void requireClass(String name, String what) {
        try {
            Class.forName(name);
        } catch (Throwable t) {
            System.err.println("Missing " + what + ": " + name);
            System.err.println("It is a transitive dependency of the audio providers "
                    + "and has to be shaded alongside them.");
            System.exit(1);
        }
    }

    /** Checks some converter in the jar claims to accept the named source encoding. */
    private static void requireEncoding(String encoding, String what) {
        for (FormatConversionProvider provider
                : ServiceLoader.load(FormatConversionProvider.class)) {
            for (AudioFormat.Encoding source : provider.getSourceEncodings()) {
                if (source.toString().equals(encoding)) {
                    System.out.println("  " + what + ": " + encoding + " accepted by "
                            + provider.getClass().getSimpleName());
                    return;
                }
            }
        }
        System.err.println("No converter in the jar accepts " + encoding
                + ", so " + what + " will not play.");
        System.exit(1);
    }
}
