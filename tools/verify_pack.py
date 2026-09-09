#!/usr/bin/env python3
"""Check an installed Quest Forge instance against what it is supposed to be.

WHY THIS EXISTS. On 2026-09-09 the pack was found to have been shipping a jar
that was missing an entire feature -- the tower speaker block, the JBL shoulder
mount, the audio routing and seven textures -- for two days. It was found by
booting the game and noticing things were wrong. Nothing compared the installed
files against the artifacts they were built from, so a build that was produced
and never deployed looked exactly like a build that was deployed.

The same blindness covers the loading sequence, which is worse, because it does
not live in a mod at all. It lives in a hand-ASM-patched Forge jar under
`libraries/` carrying qf/splash/{QFBars,SplashMusic,SplashChantFade,
SplashMenuPreload}, plus loose textures under `resources/`. Neither is in the
repository -- *.jar is gitignored and resources/ was never tracked -- so a fresh
Prism instance resolves stock Forge and silently reverts the whole splash to
vanilla. Nothing errors. It just quietly stops being the pack.

Every check here corresponds to something that actually went wrong.

Usage:
    verify_pack.py --instance <prism instance dir> [--repo <repo root>]

Exit status is 1 if any check fails, so it can gate a release.
"""
import argparse, os, sys, zipfile

OK, WARN, FAIL = "ok", "warn", "FAIL"
results = []


def check(name, status, detail=""):
    results.append((status, name, detail))


def jar_entries(path):
    try:
        with zipfile.ZipFile(path) as z:
            return set(z.namelist())
    except Exception as e:
        return None


# --- the loading sequence -------------------------------------------------
#
# Four classes patched into the Forge jar by tools/branding/splash-bars and
# tools/music. Losing them is silent: the game boots, the splash is just
# vanilla again.
SPLASH_CLASSES = [
    "qf/splash/QFBars.class",
    "qf/splash/SplashMusic.class",
    "qf/splash/SplashChantFade.class",
    "qf/splash/SplashMenuPreload.class",
]

# Referenced by config/splash.properties, loaded from resources/ at boot.
SPLASH_TEXTURES = [
    "resources/assets/minecraft/textures/gui/title/splash/trough.png",
    "resources/assets/minecraft/textures/gui/title/splash/rim.png",
    "resources/assets/minecraft/textures/gui/title/splash/magma.png",
    "resources/assets/minecraft/textures/gui/title/splash/head.png",
    "resources/assets/minecraft/textures/gui/title/splash/plaque.png",
    "resources/assets/minecraft/textures/font/ascii.png",
    "resources/assets/minecraft/textures/gui/title/loading_mural.png",
]

# Custom mods, and where their authoritative build lands.
CUSTOM_MODS = {
    "QuestForgeContent-1.0.0.jar": "mods/qf-content/build/libs/QuestForgeContent-1.0.0.jar",
    "TransformersMod-0.6.3-qf1.jar": "mods/transformers/build/libs/TransformersMod-0.6.3-qf1.jar",
}

# Classes whose absence means a whole feature is missing rather than broken.
FEATURE_CLASSES = {
    "QuestForgeContent-1.0.0.jar": [
        "com/questforge/content/jukebox/BlockTowerSpeaker.class",
        "com/questforge/content/jukebox/TileEntityTowerSpeaker.class",
        "com/questforge/content/jukebox/RenderTowerSpeaker.class",
        "com/questforge/content/jukebox/SpeakerArm.class",
        "com/questforge/content/jukebox/RenderSpeaker.class",
        "com/questforge/content/jukebox/DirectAudio.class",
        "com/questforge/content/jukebox/SpeakerRegistry.class",
        "assets/qfcontent/textures/blocks/tower_speaker.png",
        "assets/qfcontent/textures/entity/jbl_shell.png",
        "assets/qfcontent/textures/entity/jbl_cap.png",
        "assets/qfcontent/textures/entity/jbl_sleeve.png",
        "assets/qfcontent/textures/entity/tower_cabinet.png",
        "assets/qfcontent/textures/entity/tower_cone.png",
        "assets/qfcontent/textures/entity/tower_grille.png",
    ],
    "TransformersMod-0.6.3-qf1.jar": [
        # The coremod half. Without the manifest and this class, FML loads
        # neither the transformers nor the @Mod, and the jar is inert.
        "fiskfille/tf/asm/TFLoadingPlugin.class",
        # Ground bridge. Its Teleporter subclass lived in a package called
        # "world", which an unanchored .gitignore rule excluded, so the class
        # was absent from a clean checkout and the mod would not compile.
        "fiskfille/tf/common/world/TeleporterGroundBridge.class",
        "fiskfille/tf/common/block/BlockGroundBridgeTeleporter.class",
    ],
}

# The jukebox decodes ogg/mp3 through shaded libraries. If the service files are
# not merged the decoders vanish at runtime and playback silently does nothing.
SERVICE_FILES = [
    "META-INF/services/javax.sound.sampled.spi.AudioFileReader",
    "META-INF/services/javax.sound.sampled.spi.FormatConversionProvider",
]


def declared_sounds(entries, jar_path):
    """Every sound file a jar's sounds.json promises, as jar entry paths.

    A mod declares its sounds in assets/<domain>/sounds.json and the game
    resolves each name to assets/<domain>/sounds/<name>.ogg. Nothing checks
    that the file is actually there: a jar whose sounds.json survived while its
    .ogg files did not loads without complaint and plays nothing. That is not
    hypothetical -- .gitignore's "*.ogg" rule, written for generated music
    renders, also excluded the Transformers mod's 19 shipped sound effects, and
    the only visible symptom was a jar 630 KB smaller than it should be.

    So this is derived from the jar's own manifest of intent rather than from a
    hardcoded list, and it keeps working when sounds are added.
    """
    import json

    wanted = []
    for entry in entries:
        parts = entry.split("/")
        if len(parts) != 3 or parts[0] != "assets" or parts[2] != "sounds.json":
            continue
        domain = parts[1]
        try:
            with zipfile.ZipFile(jar_path) as z:
                spec = json.loads(z.read(entry).decode("utf-8", "replace"))
        except Exception:
            continue
        if not isinstance(spec, dict):
            continue
        for event in spec.values():
            if not isinstance(event, dict):
                continue
            for snd in event.get("sounds", []):
                name = snd if isinstance(snd, str) else snd.get("name")
                if not name:
                    continue
                # "domain:path" overrides the file's own domain.
                dom, _, path = name.rpartition(":")
                wanted.append("assets/%s/sounds/%s.ogg"
                              % (dom or domain, path))
    return wanted


def verify_forge(instance):
    libs = os.path.join(instance, "libraries")
    jars = []
    if os.path.isdir(libs):
        jars = [os.path.join(libs, f) for f in os.listdir(libs)
                if f.startswith("forge-1.7.10") and f.endswith(".jar")]
    if not jars:
        check("Forge jar present", FAIL, "no forge-1.7.10*.jar under libraries/")
        return
    entries = jar_entries(jars[0]) or set()
    missing = [c for c in SPLASH_CLASSES if c not in entries]
    if missing:
        check("Forge jar is the PATCHED build", FAIL,
              "missing %s -- the splash will be vanilla Forge. Rebuild with "
              "tools/branding/splash-bars and tools/music." % ", ".join(missing))
    else:
        check("Forge jar is the PATCHED build", OK,
              "all 4 qf/splash classes present")


def verify_resources(instance):
    mc = os.path.join(instance, "minecraft")
    missing = [p for p in SPLASH_TEXTURES if not os.path.exists(os.path.join(mc, p))]
    if missing:
        check("Splash resources", FAIL,
              "%d missing, e.g. %s" % (len(missing), missing[0]))
    else:
        check("Splash resources", OK, "%d files" % len(SPLASH_TEXTURES))

    props = os.path.join(mc, "config", "splash.properties")
    if not os.path.exists(props):
        check("config/splash.properties", FAIL, "absent")
        return
    text = open(props, errors="replace").read()
    if "enabled=true" not in text:
        check("config/splash.properties", WARN, "splash is disabled")
    else:
        check("config/splash.properties", OK, "enabled")


def verify_mods(instance, repo):
    mods = os.path.join(instance, "minecraft", "mods")
    for jar, built_rel in CUSTOM_MODS.items():
        path = os.path.join(mods, jar)
        if not os.path.exists(path):
            check("mod %s" % jar, FAIL, "not installed")
            continue
        size = os.path.getsize(path)

        # Staleness: compare against the build output it should have come from.
        if built_rel and repo:
            built = os.path.join(repo, built_rel)
            if os.path.exists(built):
                bsize = os.path.getsize(built)
                if bsize != size:
                    check("mod %s is current" % jar, FAIL,
                          "installed %d bytes, build output %d bytes -- a newer "
                          "build exists and was never deployed" % (size, bsize))
                else:
                    check("mod %s is current" % jar, OK, "%d bytes" % size)
            else:
                check("mod %s is current" % jar, WARN,
                      "no build output at %s to compare against" % built_rel)

        # Feature completeness: specific classes and textures, not just a size.
        entries = jar_entries(path)
        if entries is None:
            check("mod %s readable" % jar, FAIL, "not a readable zip")
            continue
        for want in FEATURE_CLASSES.get(jar, []):
            if want not in entries:
                check("%s :: %s" % (jar, want.split("/")[-1]), FAIL, "missing")
        if FEATURE_CLASSES.get(jar) and all(w in entries for w in FEATURE_CLASSES[jar]):
            check("mod %s feature set" % jar, OK,
                  "%d required entries present" % len(FEATURE_CLASSES[jar]))

        # Declared-but-absent sounds. See declared_sounds() -- this is the check
        # that catches a jar which builds, loads, and is silently mute.
        wanted = declared_sounds(entries, path)
        if wanted:
            gone = [w for w in wanted if w not in entries]
            if gone:
                check("mod %s sounds" % jar, FAIL,
                      "sounds.json declares %d sound(s) the jar does not "
                      "contain, e.g. %s -- the mod will load and play nothing"
                      % (len(gone), gone[0]))
            else:
                check("mod %s sounds" % jar, OK,
                      "all %d declared sounds present" % len(wanted))

        if jar.startswith("QuestForgeContent"):
            for svc in SERVICE_FILES:
                if svc not in entries:
                    check("%s :: %s" % (jar, os.path.basename(svc)), FAIL,
                          "shaded service file missing -- audio decoders will "
                          "not register and playback will silently fail")
            if all(s in entries for s in SERVICE_FILES):
                check("%s audio shading" % jar, OK, "both service files present")


def verify_resourcepack(instance, repo):
    zp = os.path.join(instance, "minecraft", "resourcepacks", "QuestForge.zip")
    if not os.path.exists(zp):
        check("resourcepack QuestForge.zip", FAIL, "absent -- menu art and menu music")
        return
    entries = jar_entries(zp) or set()
    wanted = ["pack.mcmeta", "assets/custommenu/background.jpg",
              "assets/minecraft/sounds.json"]
    missing = [w for w in wanted if w not in entries]
    if missing:
        check("resourcepack contents", FAIL, "missing %s" % ", ".join(missing))
    else:
        check("resourcepack contents", OK, "%d entries" % len(entries))

    if repo:
        # The repo is supposed to hold the shipped pack verbatim.
        src = os.path.join(repo, "pack", "resourcepack")
        if os.path.isdir(src):
            tracked = set()
            for dp, _, fs in os.walk(src):
                for f in fs:
                    tracked.add(os.path.relpath(os.path.join(dp, f), src))
            drift = sorted(e for e in entries
                           if not e.endswith("/") and e not in tracked)
            if drift:
                check("resourcepack matches repo", WARN,
                      "%d file(s) shipped but not tracked, e.g. %s"
                      % (len(drift), drift[0]))
            else:
                check("resourcepack matches repo", OK, "no drift")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True,
                    help="Prism instance directory (holds minecraft/ and libraries/)")
    ap.add_argument("--repo", help="repo root, to compare against build output")
    args = ap.parse_args()

    inst = os.path.abspath(args.instance)
    repo = os.path.abspath(args.repo) if args.repo else None
    if not os.path.isdir(os.path.join(inst, "minecraft")):
        sys.exit("no minecraft/ under %s" % inst)

    print("instance: %s" % inst)
    print("repo    : %s\n" % (repo or "(not given -- staleness unchecked)"))

    verify_forge(inst)
    verify_resources(inst)
    verify_mods(inst, repo)
    verify_resourcepack(inst, repo)

    width = max(len(n) for _, n, _ in results)
    bad = 0
    for status, name, detail in results:
        if status == FAIL:
            bad += 1
        mark = {OK: "  ok  ", WARN: " warn ", FAIL: " FAIL "}[status]
        print("[%s] %-*s %s" % (mark, width, name, detail))

    fails = sum(1 for s, _, _ in results if s == FAIL)
    warns = sum(1 for s, _, _ in results if s == WARN)
    print("\n%d checks, %d failed, %d warnings" % (len(results), fails, warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
