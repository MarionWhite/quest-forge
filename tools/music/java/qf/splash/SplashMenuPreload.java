package qf.splash;

/** Named preload worker so jar uf cannot drop an anonymous SplashMusic$1. */
public final class SplashMenuPreload implements Runnable {
    public void run() {
        SplashMusic.preloadMenuClip();
    }
}
