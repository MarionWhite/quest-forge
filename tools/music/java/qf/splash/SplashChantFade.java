package qf.splash;

import javax.sound.sampled.Clip;
import javax.sound.sampled.FloatControl;

/**
 * Named fade worker so jar uf cannot drop an anonymous SplashMusic$1.
 * Equal-power MASTER_GAIN fade: choir stays under the menu swell, then air, then gone.
 */
public final class SplashChantFade implements Runnable {
    private final Clip clip;
    private final float startDb;
    private final float fadeSec;

    public SplashChantFade(Clip clip, float startDb, float fadeSec) {
        this.clip = clip;
        this.startDb = startDb;
        this.fadeSec = fadeSec;
    }

    public void run() {
        try {
            fade();
        } catch (Throwable ignored) {
        } finally {
            try {
                clip.stop();
            } catch (Throwable ignored) {
            }
            try {
                clip.close();
            } catch (Throwable ignored) {
            }
        }
    }

    private void fade() {
        FloatControl gain = null;
        float min = -80.0f;
        try {
            if (clip.isControlSupported(FloatControl.Type.MASTER_GAIN)) {
                gain = (FloatControl) clip.getControl(FloatControl.Type.MASTER_GAIN);
                min = gain.getMinimum();
            }
        } catch (Throwable ignored) {
        }
        int steps = (int) (fadeSec * 50.0f);
        if (steps < 8) {
            steps = 8;
        }
        long stepMs = (long) (fadeSec * 1000.0f / (float) steps);
        if (stepMs < 10L) {
            stepMs = 10L;
        }
        int i;
        for (i = 1; i <= steps; i++) {
            if (gain != null) {
                float t = (float) i / (float) steps;
                /* equal-power: amp = cos(pi/2 * t). Choir still there at 2 s of a 3 s fade. */
                double amp = Math.cos((double) t * Math.PI * 0.5);
                float db;
                if (amp <= 1.0e-4) {
                    db = min;
                } else {
                    db = startDb + (float) (20.0 * Math.log10(amp));
                    if (db < min) {
                        db = min;
                    }
                }
                try {
                    gain.setValue(db);
                } catch (Throwable ignored) {
                    break;
                }
            }
            try {
                Thread.sleep(stepMs);
            } catch (InterruptedException ie) {
                break;
            }
        }
    }
}
