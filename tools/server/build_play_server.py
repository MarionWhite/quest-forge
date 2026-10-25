#!/usr/bin/env python3
"""Assemble the multiplayer server friends play on, from the live pack instance.

WHY THIS IS SEPARATE FROM tools/survey/build_server.py. That server exists to
measure worldgen and drops only what cannot place a block. A play server has a
different rule -- drop what cannot run without a screen -- and different
settings: monsters on, survival, a whitelist, flight allowed. Sharing one
script would make every change to one quietly change the other.

WHY IT IS A SCRIPT AT ALL. The same reason as the survey server: a hand-built
server drifts from the pack, and a client that differs from the server by one
mod cannot join, while one that differs by one config value joins and then
plays with the wrong enchantments. So the server is never edited in place. It is
rebuilt from the instance, and configs are copied verbatim -- never overlaid
with server/config, whose enchantment IDs differ from the clients'.

Usage:
    build_play_server.py --instance <.crazycraft4 dir> --forge-install <dir> --out <server dir>
    build_play_server.py --java25 --instance <dir> [--tweaks <qf-tweaks jar>] --out <server dir>

--forge-install is a directory holding a stock Forge 1.7.10-10.13.4.1558 server
install: the universal jar, minecraft_server.1.7.10.jar and libraries/. The
client's own Forge jar is hand-patched for the splash screen and must not be
used here.

--java25 builds the slim Java 25 server instead (docs/design/angelica-decision.md):
Temurin 25 + lwjgl3ify + UniMixins on Forge 10.13.4.1614, and nothing else from
the GTNH stack. Today's Java 8 OptiFine clients join it unchanged. The pinned
jars are downloaded once into --cache and checked by sha256; Forge 1614 is
installed there from its installer unless --forge-install names an install.
Without --java25 the build is the Java 8 server it has always been, so going
back is one rebuild.

CodeChickenCore: the server takes whatever the instance runs, and must, because
NEI's packets differ between stock CCC and GTNH CCC. Since 2026-10-18 that is GTNH
CodeChickenCore 1.4.22 (CodeChickenLib merged in, its unloadChunk null-guarded, so
pregeneration needs no patch) and no --ccl. --ccl remains only for an instance still
on stock CCC + CodeChickenLib, and is refused otherwise.
"""
import argparse, fnmatch, glob, hashlib, json, os, re, shutil, socket, subprocess, sys
import urllib.request, uuid, zipfile

# Mods that only run with a screen. Each stays on every client -- FML lets a
# client carry mods the server lacks, but never the reverse. Matched as a
# filename prefix.
CLIENT_ONLY = [
    ("OptiFine",            "client renderer; does not run on a dedicated server"),
    ("SoundFilters",        "client audio; crashes the server on FMLServerStopped"),
    ("CustomMenu",          "replaces the client main menu; references client classes"),
    ("DamageIndicators",    "client HUD; common code references client classes"),
    ("MobDismemberment",    "client gore rendering"),
    ("MobAmputation",       "client gore rendering"),
    ("InventoryTweaks",     "client inventory sorting"),
    ("Controlling",         "client keybind search"),
    ("journeymap",          "client map; the server half does nothing without JourneyMapServer"),
]

# QuestForgeTweaks stays: most of its patches target client classes and are
# inert here, but GraveBaublesTransformer fixes GraveStones on the server side,
# where without it every death disconnects every player.

# Kept deliberately, unlike the survey server: HatStand adds a block (clients
# with it would be refused by a server without it), Hats depends on it the other
# way round, and ColorfulMobs syncs dyed mobs from the server.

# Backups people leave next to jars. FML ignores them, but they make "which jar
# is the server running" a question with more than one answer.
JUNK = ["*.broken-*", "*.pre-*", "*.bak*", "*.disabled"]

SERVER_PROPERTIES = """\
level-name=world
level-type=DEFAULT
level-seed=
gamemode=0
difficulty=2
hardcore=false
pvp=true
online-mode={online}
white-list=true
max-players={max_players}
spawn-protection=0
view-distance={view_distance}
allow-flight=true
allow-nether=true
generate-structures=true
spawn-npcs=true
spawn-animals=true
spawn-monsters=true
enable-command-block=true
motd=Quest Forge
server-port={port}
"""

# allow-flight=true is not a cheat switch here: vanilla kicks anyone airborne for
# four seconds without creative flight, and half the pack flies -- Transformers
# jet modes, Legends heroes, OreSpawn gliding, TragicMC's Flight effect.

# view-distance is the server's biggest single cost: every player keeps
# (2r+1)^2 chunks loaded and ticking, so 8 costs 289 chunks a player and 6 costs
# 169. It must match the "Distance (in Chunks) to perform entity spawning" and
# "...counting" in config/JustAnotherSpawner/GlobalProperties.cfg. JAS scales
# each mob cap by the chunks it counts / 256, so counting 8 while only 6 are
# loaded packs the full cap into 58% of the area.

# The JVM flags shared by both start scripts. Xms equals Xmx because a server
# owns its memory: growing the heap later costs pauses and buys nothing. The GC
# log is how a pause gets told apart from a slow tick after the fact; it costs
# nothing measurable and rotates at 5 x 20 MB.
JVM_FLAGS = [
    "-Xms{xmx}", "-Xmx{xmx}",
    "-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:G1HeapRegionSize=16M",
    "-XX:+UseSplitVerifier", "-XX:+FailOverToOldVerifier", "-XX:+DisableExplicitGC",
    "-Xloggc:logs/gc.log", "-XX:+PrintGCDetails", "-XX:+PrintGCDateStamps",
    "-XX:+PrintGCApplicationStoppedTime",
    "-XX:+UseGCLogFileRotation", "-XX:NumberOfGCLogFiles=5", "-XX:GCLogFileSize=20M",
    "-Dfml.ignoreInvalidMinecraftCertificates=true", "-Dfml.ignorePatchDiscrepancies=true",
    "-Dlog4j2.formatMsgNoLookups=true",
]

# --- the slim Java 25 server ------------------------------------------------
#
# Pinned to the versions the 2026-10-17 decision tests ran (test 1 and the slim
# bench in docs/design/angelica-decision.md). A different version is a new
# test, not a drop-in: lwjgl3ify replaces Forge's ASM and Gson, and its server
# launcher names the Forge universal jar by its exact file name.
J25_FORGE = "forge-1.7.10-10.13.4.1614-1.7.10-universal.jar"
J25_LAUNCHER = "lwjgl3ify-forgePatches.jar"   # the name lwjgl3ify's README asks for
J25_DEPS = {
    # cache name: (url, sha256, where it goes in the server)
    "lwjgl3ify-3.0.39-forgePatches.jar": (
        "https://github.com/GTNewHorizons/lwjgl3ify/releases/download/3.0.39/"
        "lwjgl3ify-3.0.39-forgePatches.jar",
        "7428fdbe6f85d7c092aecd9169ff8d5e83327edd6e8ef1c2ee517f739c5388b0", J25_LAUNCHER),
    "lwjgl3ify-3.0.39.jar": (
        "https://github.com/GTNewHorizons/lwjgl3ify/releases/download/3.0.39/lwjgl3ify-3.0.39.jar",
        "c120ef93dfda5bd54e2b16ffae3265fc8bb188e952790cb886999896a70a52c6",
        "mods/lwjgl3ify-3.0.39.jar"),
    "+unimixins-all-1.7.10-0.3.2.jar": (
        "https://github.com/LegacyModdingMC/UniMixins/releases/download/0.3.2/"
        "%2Bunimixins-all-1.7.10-0.3.2.jar",
        "2687b776c8503e0b60cd8413cf70eaabb836c19f9fc726280ef61d6612257034",
        "mods/+unimixins-all-1.7.10-0.3.2.jar"),
    # The JVM's --add-opens list, from the same lwjgl3ify tag.
    "java9args-3.0.39.txt": (
        "https://raw.githubusercontent.com/GTNewHorizons/lwjgl3ify/3.0.39/java9args.txt",
        "4323ca4203c84371d4fe1698dad306f81858be97bfe6da2606e7fd1b81749c9d", "java9args.txt"),
}
J25_FORGE_INSTALLER = (
    "forge-1.7.10-10.13.4.1614-1.7.10-installer.jar",
    "https://maven.minecraftforge.net/net/minecraftforge/forge/1.7.10-10.13.4.1614-1.7.10/"
    "forge-1.7.10-10.13.4.1614-1.7.10-installer.jar",
    "a5d60757d8b305939233a942d5097fa78816d116ef9082c03066fe669e010c7f")

# Any of these on the server becomes required on every client. GTNHLib is a
# required mod and crashes OptiFine E7 at load; Hodgepodge and ArchaicFix change
# the login packet, so clients without them are dropped (decision doc, test 1).
J25_FORBIDDEN = ["hodgepodge", "archaicfix", "gtnhlib", "angelica"]

# qf-tweaks patches the Java 25 server cannot run without; each is inert on
# Java 8. Checked in the jar the build installs, by class name.
J25_TWEAKS = [
    ("com/questforge/LuckyScriptTransformer.class",
     "Lucky Block drop expressions (301 errors at boot without it)"),
    ("com/questforge/RecNbtTransformer.class",
     "Recurrent Complex loot with NBT (4 inventory generators fail without it)"),
    ("com/questforge/AsieNickTransformer.class",
     "AsieLib nicknames.json (fails to load from the second boot on)"),
]

# The Java 8 flags above do not exist on Java 25 (-XX:+UseSplitVerifier,
# -Xloggc and the PrintGC family make the JVM refuse to start). The GC log
# moves to unified logging: the same file, rotated the same way; `safepoint`
# adds the total stop time of every pause, which is what the decision bench
# compared. @java9args.txt must come before -jar.
JVM_FLAGS_J25 = [
    "-Xms{xmx}", "-Xmx{xmx}",
    "-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:G1HeapRegionSize=16M",
    "-XX:+DisableExplicitGC",
    "-Xlog:gc,safepoint:file=logs/gc.log:time,uptime:filecount=5,filesize=20M",
    "-Dfml.ignoreInvalidMinecraftCertificates=true", "-Dfml.ignorePatchDiscrepancies=true",
    "-Dlog4j2.formatMsgNoLookups=true",
    "@java9args.txt",
]

JAVA8_DEFAULT = r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe"

# --- optional server-only additions ----------------------------------------
#
# Each of these declares acceptableRemoteVersions="*" in its @Mod annotation
# (read from the jars with javap, 2026-10-25). FML 1614's NetworkModHolder picks
# its IgnoredChecker for "*", which accepts every client, so a client without
# the mod joins. None adds a block or an item, so each can join a running world.
# Pinned by sha256 like the Java 25 deps: a file whose hash differs is never used.
ADDONS = {
    # The profiler (docs/design/server-readiness.md, 4d). Depends on
    # MobiusCore@[1.2.5] exactly; the pack ships MobiusCore 1.2.5 (mods/MobiusCore.jar).
    # Console commands: opis_start, opis_stop, opis_te, opis_ents, opis_chunks,
    # opis_ticks, opis_help. The bundled MapWriter (client map) also says "*".
    "opis": ("Opis-1.2.5_1.7.10.jar",
             "https://mediafilez.forgecdn.net/files/2232/520/Opis-1.2.5_1.7.10.jar",
             "76905f92f829a960500ebe038924290e2757930102963920a3a347922c3402cf"),
    # Sleep vote (section 6/8). Sleepy Head 1.0 was the other candidate, but its
    # @Mod has no acceptableRemoteVersions, so every client would need it too.
    "morpheus": ("Morpheus-1.7.10-1.6.21.jar",
                 "https://mediafilez.forgecdn.net/files/2280/761/Morpheus-1.7.10-1.6.21.jar",
                 "37014340a0400277b1202233f75619d53e84c0cf37d2d3561a993241a45cb412"),
    # RoyCurtis's Forge port of Brettflan's WorldBorder (section 4a).
    "worldborder": ("WorldBorder-Forge-1.0.2.jar",
                    "https://github.com/RoyCurtis/WorldBorder-Forge/releases/download/1.0.2/"
                    "WorldBorder-Forge-1.0.2.jar",
                    "1bd5a2de22b02245120bf0cccb73664b0abd7242bde653132c57a8693623d40b"),
}

# Options that must survive a --force rebuild, because a rebuild recopies
# config/ and mods/ from the instance and would otherwise silently drop them.
# Kept next to supervisor.json; the command line updates it.
PLAY_OPTIONS = "play-options.json"

# The owner's social and load decisions (docs/design/server-readiness.md,
# sections 4 and 6), keyed by decision id. Each becomes an edit to the server's
# own copy of a config, a server.properties key, a supervisor.json key or a
# pinned mod. The client's configs are untouched: none of these is an ID entry,
# so the pack fingerprint clients must match does not change. --rules FILE
# applies a JSON file of {id: value}; tools/server/rules.example.json lists
# every key with its choices.
RULE_IDS = {
    "srv-pvp":     '"team" (everyone on one vanilla team, friendly fire off; the Gravity Gun '
                   'cannot grab players), "off" (pvp=false), or "on" (vanilla)',
    "srv-quests":  '"personal" (BetterQuesting parties off) or "parties"',
    "srv-sleep":   'percent of players that must sleep to skip the night (Morpheus); 0 = no sleep vote',
    "srv-afk":     'minutes before an idle player is kicked (player-idle-timeout); 0 = never',
    "srv-hub":     'spawn-protection radius in blocks around spawn (non-ops cannot build); 0 = off',
    "srv-loaders": '{"world_anchors": "off" | "capped" | "on", "sync_shells": true | false}',
    "srv-graves":  '"shared" or "owner-only": a rule for the rules post only (GraveStones has no '
                   'owner-only option); nothing is configured',
    "srv-tools":   '{"chest_transporter_spawners": true | false, "projecte_time_watch_pedestal": '
                   '<bonus ticks, 0 = none>, "lycanites_first_event_day": <day>}',
}


def set_cfg(path, key, value, section=None):
    """Set one `T:key=value` line of a Forge .cfg (the B:/I:/S:/D: prefix is kept),
    inside the top-level `section { ... }` when given. Line endings are kept.
    Exits if the key is not there: a missing key means the mod's config has
    changed and the rule needs a look, not a silent no-op."""
    with open(path, encoding="latin-1", newline="") as fh:
        text = fh.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    start, end = 0, len(lines)
    if section:
        heads = {section + " {", '"%s" {' % section}
        sec = next((i for i, l in enumerate(lines) if l.strip() in heads), None)
        if sec is None:
            sys.exit("%s: no section %s {" % (path, section))
        depth, start, end = 1, sec + 1, None
        for j in range(sec + 1, len(lines)):
            s = lines[j].strip()
            if s.endswith("{"):
                depth += 1
            elif s == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:
            sys.exit("%s: section %s never closes" % (path, section))
    pat = re.compile(r'^(\s*[A-Z]:"?%s"?=)(.*)$' % re.escape(key))
    for i in range(start, end):
        m = pat.match(lines[i])
        if m:
            if m.group(2) == str(value):
                return False
            lines[i] = m.group(1) + str(value)
            with open(path, "w", encoding="latin-1", newline="") as fh:
                fh.write(nl.join(lines))
            return True
    sys.exit("%s: no key %s%s" % (path, key, " in section %s" % section if section else ""))


def append_cfg_block(path, name, body):
    """Add a top-level `name { body }` block to a Forge .cfg unless one exists."""
    with open(path, encoding="latin-1", newline="") as fh:
        text = fh.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    if any(l.strip() == name + " {" for l in text.split(nl)):
        return False
    block = [name + " {"] + ["    " + b for b in body] + ["}", "", ""]
    with open(path, "w", encoding="latin-1", newline="") as fh:
        fh.write(text.rstrip(nl) + nl + nl + nl + nl.join(block))
    return True


def write_world_border(out, radius, level):
    """config/WorldBorder/borders.cfg with one square border, radius blocks
    around 0,0 in the overworld. The layout is what WorldBorder-Forge 1.0.2
    itself wrote after `wb world set 3000 0 0` and `wb wshape world square` on
    the scratch server (2026-10-25), so the mod reads it back as if the commands
    had been typed. The overworld's name to the mod is the level name from
    server.properties ("world"); other dimensions are "DIM<id>". main.cfg is
    left to the mod's defaults (knockback 3 blocks, check every 20 ticks,
    ender pearls past the border cancelled, block place and mob spawn outside
    it prevented)."""
    d = os.path.join(out, "config", "WorldBorder")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "borders.cfg"), "w", newline="\n") as fh:
        fh.write(WORLD_BORDER_CFG.format(radius=int(radius), level=level))


WORLD_BORDER_CFG = """\
# Configuration file

{level} {{
    I:radiusX={radius}
    I:radiusZ={radius}
    B:shape-round=false
    B:wrapping=false
    D:x=0.0
    D:z=0.0
}}


"""


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def update_supervisor_json(out, updates):
    """Set keys in the server's supervisor.json, creating it from the defaults."""
    path = os.path.join(out, "supervisor.json")
    cfg = load_json(path, dict(SUPERVISOR_JSON))
    changed = {k: v for k, v in updates.items() if cfg.get(k) != v}
    cfg.update(updates)
    with open(path, "w") as fh:
        json.dump(cfg, fh, indent=2)
    for k, v in changed.items():
        print("supervisor.json: %s = %r" % (k, v))


def apply_rules(out, rules, props, sup):
    """Apply the owner's decisions to the server's copies. Fills `props`
    (server.properties keys) and `sup` (supervisor.json keys), returns the
    list of what was done for BUILT-FROM.txt. `rules` keys are decision ids."""
    unknown = sorted(set(rules) - set(RULE_IDS) - {k for k in rules if k.startswith("_")})
    if unknown:
        sys.exit("--rules: unknown decision id(s) %s. Known:\n  %s" % (
            ", ".join(unknown), "\n  ".join("%-12s %s" % kv for kv in RULE_IDS.items())))
    cfg = lambda *p: os.path.join(out, "config", *p)
    done = []

    def need(path):
        if not os.path.exists(path):
            sys.exit("--rules: %s is not in the pack's config; is that mod still installed?" % path)
        return path

    v = rules.get("srv-pvp")
    if v is not None:
        if v not in ("team", "off", "on"):
            sys.exit('--rules: srv-pvp must be "team", "off" or "on", not %r' % v)
        sup["team"] = "qf" if v == "team" else ""
        props["pvp"] = "false" if v == "off" else "true"
        # iChun's GraviGun checks this on the server when a player is targeted.
        set_cfg(need(cfg("GraviGun.cfg")), "grabablePlayers", 0 if v != "on" else 1)
        done.append("srv-pvp=%s: pvp=%s, Gravity Gun grabablePlayers=%d%s" % (
            v, props["pvp"], 0 if v != "on" else 1,
            "; the supervisor keeps every player on team qf with friendly fire off" if v == "team" else ""))

    v = rules.get("srv-quests")
    if v is not None:
        if v not in ("personal", "parties"):
            sys.exit('--rules: srv-quests must be "personal" or "parties", not %r' % v)
        # BetterQuesting copies DefaultQuests.json into the world only when the
        # world is created; an existing world takes it with `/bq_admin default load`.
        path = need(cfg("betterquesting", "DefaultQuests.json"))
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
        new, n = re.subn(r'("party_enable:1":\s*)\d', r"\g<1>%d" % (v == "parties"), text, count=1)
        if n != 1:
            sys.exit("--rules: no party_enable in %s" % path)
        if new != text:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
        done.append("srv-quests=%s: BetterQuesting party_enable=%d (DefaultQuests.json; an existing "
                    "world needs /bq_admin default load)" % (v, v == "parties"))

    v = rules.get("srv-sleep")
    if v is not None:
        if not isinstance(v, int) or not 0 <= v <= 100:
            sys.exit("--rules: srv-sleep is a percentage 0-100, not %r" % v)
        if v:
            done.append(("addon", "morpheus"))
            # Morpheus reads settings{} from config/Morpheus.cfg; Forge adds the
            # keys we leave out at boot.
            with open(cfg("Morpheus.cfg"), "w", newline="\n") as fh:
                fh.write("# Configuration file\n\nsettings {\n    B:AlertEnabled=true\n"
                         "    I:SleeperPerc=%d\n}\n\n" % v)
            done.append("srv-sleep=%d: Morpheus installed, SleeperPerc=%d" % (v, v))
        else:
            done.append("srv-sleep=0: no sleep vote mod")

    v = rules.get("srv-afk")
    if v is not None:
        if not isinstance(v, int) or v < 0:
            sys.exit("--rules: srv-afk is minutes (0 = never), not %r" % v)
        props["player-idle-timeout"] = str(v)
        done.append("srv-afk=%d: player-idle-timeout=%d" % (v, v))

    v = rules.get("srv-hub")
    if v is not None:
        if not isinstance(v, int) or v < 0:
            sys.exit("--rules: srv-hub is a spawn-protection radius in blocks (0 = off), not %r" % v)
        props["spawn-protection"] = str(v)
        done.append("srv-hub=%d: spawn-protection=%d" % (v, v))

    v = rules.get("srv-loaders")
    if v is not None:
        if not isinstance(v, dict):
            sys.exit("--rules: srv-loaders is an object %s" % RULE_IDS["srv-loaders"])
        wa = v.get("world_anchors", "on")
        if wa not in ("off", "capped", "on"):
            sys.exit('--rules: srv-loaders.world_anchors must be "off", "capped" or "on"')
        rc = need(cfg("railcraft", "railcraft.cfg"))
        set_cfg(rc, "craftable", "false" if wa == "off" else "true", section="anchors")
        if wa == "capped":
            # Forge's per-mod ticket cap: 20 anchors per world, each a 3x3.
            append_cfg_block(need(cfg("forgeChunkLoading.cfg")), "Railcraft",
                             ["I:maximumChunksPerTicket=9", "I:maximumTicketCount=20"])
        done.append("srv-loaders.world_anchors=%s: Railcraft anchors.craftable=%s%s" % (
            wa, "false" if wa == "off" else "true",
            "; forgeChunkLoading.cfg Railcraft { 20 tickets x 9 chunks }" if wa == "capped" else ""))
        if "sync_shells" in v:
            set_cfg(need(cfg("Sync.cfg")), "allowChunkLoading", 1 if v["sync_shells"] else 0)
            done.append("srv-loaders.sync_shells=%s: Sync allowChunkLoading=%d"
                        % (v["sync_shells"], 1 if v["sync_shells"] else 0))

    v = rules.get("srv-graves")
    if v is not None:
        done.append("srv-graves=%s: rules post only (GraveStones has no owner-only option)" % v)

    v = rules.get("srv-tools")
    if v is not None:
        if not isinstance(v, dict):
            sys.exit("--rules: srv-tools is an object %s" % RULE_IDS["srv-tools"])
        if "chest_transporter_spawners" in v:
            on = bool(v["chest_transporter_spawners"])
            set_cfg(need(cfg("ChestTransporter.cfg")), "pickupSpawners", "true" if on else "false")
            done.append("srv-tools.chest_transporter_spawners=%s: ChestTransporter pickupSpawners=%s"
                        % (on, "true" if on else "false"))
        if "projecte_time_watch_pedestal" in v:
            b = v["projecte_time_watch_pedestal"]
            if not isinstance(b, int) or b < 0:
                sys.exit("--rules: srv-tools.projecte_time_watch_pedestal is a tick bonus (0 = none)")
            set_cfg(need(cfg("ProjectE", "ProjectE.cfg")), "timePedBonus", b)
            done.append("srv-tools.projecte_time_watch_pedestal=%d: ProjectE timePedBonus=%d" % (b, b))
        if "lycanites_first_event_day" in v:
            d = v["lycanites_first_event_day"]
            if not isinstance(d, int) or d < 0:
                sys.exit("--rules: srv-tools.lycanites_first_event_day is a day number")
            set_cfg(need(cfg("LycanitesMobs", "lycanitesmobs-mobevents.cfg")),
                    "Random Mob Events Day Minimum Overworld (0)", d)
            done.append("srv-tools.lycanites_first_event_day=%d: Lycanites 'Random Mob Events Day "
                        "Minimum Overworld (0)'=%d" % (d, d))
    return done


def default_cache():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "quest-forge", "server-deps")


def find_java25():
    pats = [r"C:\Program Files\Eclipse Adoptium\jdk-25*\bin\java.exe",
            r"C:\Program Files\Eclipse Adoptium\jre-25*\bin\java.exe",
            r"C:\Program Files\Java\jdk-25*\bin\java.exe",
            "/usr/lib/jvm/*25*/bin/java"]
    for pat in pats:
        hits = sorted(glob.glob(pat), reverse=True)
        if hits:
            return hits[0]
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(cache, name, url, sha):
    """The cached file, downloaded first if it is missing. A file whose sha256
    is not the pinned one is never used: it is deleted and fetched again."""
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, name)
    if os.path.exists(path):
        if sha256_file(path) == sha:
            return path
        print("cache:   %s has the wrong sha256; fetching it again" % name)
        os.remove(path)
    print("fetch:   %s" % url)
    part = path + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "quest-forge-build_play_server"})
    with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as fh:
        shutil.copyfileobj(r, fh)
    got = sha256_file(part)
    if got != sha:
        os.remove(part)
        sys.exit("%s: sha256 %s, expected %s. Not using it." % (url, got, sha))
    os.replace(part, path)
    return path


def forge1614_install(cache, java8):
    """A stock Forge 1614 server install in the cache, made by its installer."""
    d = os.path.join(cache, "forge-1.7.10-10.13.4.1614-server")
    if os.path.exists(os.path.join(d, J25_FORGE)) and os.path.isdir(os.path.join(d, "libraries")):
        return d
    name, url, sha = J25_FORGE_INSTALLER
    inst = fetch(cache, name, url, sha)
    if not os.path.exists(java8):
        sys.exit("the Forge installer needs Java 8 (--java8; %s does not exist)" % java8)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    print("forge:   installing 1614 into %s" % d)
    # The installer downloads minecraft_server.1.7.10.jar and the libraries.
    res = subprocess.run([java8, "-jar", inst, "--installServer", d], cwd=d,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if res.returncode != 0 or not os.path.exists(os.path.join(d, J25_FORGE)):
        print(res.stdout[-3000:])
        shutil.rmtree(d, ignore_errors=True)
        sys.exit("the Forge 1614 installer failed")
    return d


def packcheck_ignore_forge(cfg):
    """Let Java 8 clients (Forge 1558) past qf-content's login check on the
    Forge 1614 server.

    qf-content's packcheck refuses a client whose version of any mod both sides
    have differs, and Forge is a mod to it: "Your mods differ from the server's.
    Mods: Minecraft Forge 10.13.4.1558 (server 10.13.4.1614)". FML's own
    handshake accepts that pair (decision doc, test 1), so the server lists
    Forge in packcheck's ignoreMods. It is a server-only setting and not an ID
    entry, so the config fingerprint clients are checked against is unchanged.
    Found 2026-10-17 by joining the --java25 test server."""
    if not os.path.exists(cfg):
        return
    with open(cfg, encoding="latin-1", newline="") as fh:
        text = fh.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    sec = next((i for i, l in enumerate(lines) if l.strip() == "packcheck {"), None)
    if sec is None:
        # A pack whose qf-content has not booted since packcheck arrived: add
        # the section with just this key; Forge fills in the rest at boot.
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "", "packcheck {", "    S:ignoreMods <", "     >", "}", "", ""]
        sec = len(lines) - 6
    start = next((i for i in range(sec, len(lines)) if lines[i].strip() == "S:ignoreMods <"), None)
    if start is None:
        lines.insert(sec + 1, "    S:ignoreMods <")
        lines.insert(sec + 2, "     >")
        start = sec + 1
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == ">")
    if "Forge" in [l.strip() for l in lines[start + 1:end]]:
        return
    lines.insert(end, "        Forge")
    with open(cfg, "w", encoding="latin-1", newline="") as fh:
        fh.write(nl.join(lines))
    print("qfcontent.cfg: packcheck ignoreMods += Forge (clients run 1558, this server 1614)")


def tweaks_jar_missing(jar):
    """Which J25_TWEAKS fixes the qf-tweaks jar lacks."""
    try:
        with zipfile.ZipFile(jar) as z:
            names = set(z.namelist())
    except (OSError, zipfile.BadZipFile):
        return [why for _, why in J25_TWEAKS]
    return [why for cls, why in J25_TWEAKS if cls not in names]


START_BAT = """\
@echo off
rem Saintscore reads mods\\saintspack\\Packs.txt relative to the working
rem directory and crashes preInit without it, so always start from here.
cd /d "%~dp0"
if not exist logs mkdir logs
"{java}" {flags} ^
 -jar {forge} nogui
pause
"""

# Rented hosts almost always run Linux. A panel host (Pterodactyl and the like)
# ignores this file and asks for the same flags in its own startup field; copy
# them from here. A Java 8 build must run on Java 8: Forge 1.7.10 does not start
# on anything newer by itself. A --java25 build must run on Java 25 (the `java`
# on the host's PATH, or edit the line).
# The supervised way to run it (tools/server/supervisor.py, copied next to it):
# crash restart, hang detection, hourly backups, a daily restart, graceful stop.
START_SUPERVISED_BAT = """\
@echo off
rem Runs the server under supervisor.py: restart on crash, hang detection,
rem hourly backups into backups\\, a daily restart. This window is the server
rem console. Stop with Ctrl+C or by typing stop; both save the world first.
rem Settings (and the optional Discord webhook) are in supervisor.json.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -I supervisor.py %*
) else (
  python -I supervisor.py %*
)
pause
"""

SUPERVISOR_JSON = {
    "_comment": "Supervisor settings, kept across rebuilds. `py -3 supervisor.py "
                "--print-defaults` lists every key. Put the Discord webhook URL here or in "
                "the QF_DISCORD_WEBHOOK environment variable; never commit it.",
    "restart_at": "05:00",
    "backup_interval_min": 60,
    "keep_hourly": 24,
    "keep_daily": 7,
    "discord_webhook": "",
    "status_publisher": "",
    "status_gist_id": "",
    "status_gist_token": "",
}

START_SH = """\
#!/bin/sh
# Saintscore reads mods/saintspack/Packs.txt relative to the working
# directory and crashes preInit without it, so always start from here.
cd "$(dirname "$0")"
mkdir -p logs
exec java {flags} \\
 -jar {forge} nogui
"""


def offline_uuid(name):
    """The UUID an offline-mode server gives a player: Java's
    UUID.nameUUIDFromBytes("OfflinePlayer:" + name).

    WHY. With online-mode=false, the console's `whitelist add <name>` still asks
    Mojang for the UUID of the *paid* account with that name, while the joining
    player is identified by this name-derived one. They never match, so every
    whitelisted friend is refused with "You are not white-listed" -- found by
    joining the server, not by reading it.
    """
    h = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    h[6] = (h[6] & 0x0F) | 0x30
    h[8] = (h[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(h)))


def write_whitelist(out, players):
    path = os.path.join(out, "whitelist.json")
    entries = []
    if os.path.exists(path):
        with open(path) as fh:
            entries = json.load(fh)
    known = {e["name"].lower() for e in entries}
    for name in players:
        if name.lower() not in known:
            entries.append({"uuid": offline_uuid(name), "name": name})
    with open(path, "w") as fh:
        json.dump(entries, fh, indent=2)
    print("whitelist: %s" % ", ".join(e["name"] for e in entries))


def read_properties(path):
    props = {}
    if os.path.exists(path):
        with open(path, encoding="latin-1") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
    return props


def java_command_lines():
    """(pid, command line) of every running java/javaw process."""
    if os.name != "nt":
        res = subprocess.run(["ps", "-eo", "pid=,args="], stdout=subprocess.PIPE,
                             universal_newlines=True).stdout
        rows = [l.strip().split(None, 1) for l in res.splitlines()]
        return [tuple(r) for r in rows if len(r) == 2 and "java" in r[1]]
    ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'java%'\" | "
          "ForEach-Object { [string]$_.ProcessId + [char]9 + $_.CommandLine }")
    res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    # A failed listing must not read as "no java running": under memory
    # pressure PowerShell itself dies ("The paging file is too small", seen
    # 2026-10-17), and an empty list would wave a rebuild through.
    if res.returncode != 0:
        sys.exit("could not list running java processes (PowerShell exit %d); not rebuilding "
                 "without that check. Try again." % res.returncode)
    return [tuple(l.split("\t", 1)) for l in res.stdout.splitlines() if "\t" in l]


def pid_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes          # os.kill(pid, 0) on Windows sends CTRL_C_EVENT; it is no probe
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return bool(ok) and code.value == 259          # STILL_ACTIVE


def refuse_if_running(out):
    """--force on a running server moves world/ out from under the JVM and then
    fails partway on locked jars (server-readiness.md, gap 1). Any one of these
    means something is still using the directory."""
    problems = []
    pidfile = os.path.join(out, "supervisor.pid")
    if os.path.exists(pidfile):
        try:
            with open(pidfile) as fh:
                info = json.load(fh)
        except (OSError, ValueError):
            info = {}
        for key in ("supervisor_pid", "java_pid"):
            if info.get(key) and pid_alive(info[key]):
                problems.append("%s %s (from supervisor.pid) is running" % (key, info[key]))
    props = read_properties(os.path.join(out, "server.properties"))
    port = int(props.get("server-port") or 25565)
    s = socket.socket()
    s.settimeout(1)
    if s.connect_ex(("127.0.0.1", port)) == 0:
        problems.append("something is listening on its port %d" % port)
    s.close()
    norm = os.path.normcase(os.path.abspath(out))
    for pid, cmd in java_command_lines():
        if norm in os.path.normcase(cmd):
            problems.append("java pid %s names this directory on its command line" % pid)
    # A server started from start.bat has nothing absolute on its command line,
    # so these catch it: Windows will not rename a file a process holds open
    # (the session lock, the open log), nor a directory that is a process's
    # working directory or holds an open file (the server's jars).
    level = props.get("level-name") or "world"
    for rel in (os.path.join(level, "session.lock"), os.path.join("logs", "latest.log"),
                os.path.join("logs", "fml-server-latest.log"), "."):
        p = os.path.normpath(os.path.join(out, rel))
        if not os.path.exists(p):
            continue
        probe = p + ".running-probe"
        try:
            os.rename(p, probe)
        except OSError as e:
            problems.append("cannot rename %s (%s): a process holds it open" % (p, e.strerror))
            break
        os.rename(probe, p)
    if problems:
        sys.exit("refusing to rebuild %s while it is in use:\n  %s\nStop the server first "
                 "(type stop, or Ctrl+C in the supervisor window)." % (out, "\n  ".join(problems)))


JNDI = "org/apache/logging/log4j/core/lookup/JndiLookup.class"

# Log4Shell. The server's log4j is 2.0-beta9, inside minecraft_server.1.7.10.jar.
# -Dlog4j2.formatMsgNoLookups exists only from 2.10, so that flag in the start
# scripts does nothing here.
#
# The usual fix, deleting JndiLookup.class, KILLS THIS SERVER AT LAUNCH:
# beta9's Interpolator constructs JndiLookup directly, so the first logger
# throws NoClassDefFoundError (found by booting it, 2026-10-17; later log4j
# versions catch the missing class, this one does not). So the class is
# replaced by an inert one with the same name that resolves nothing. Its source,
# compiled with JDK 8 `javac -source 1.6 -target 1.6 -g:none` against the
# server jar:
#
#   package org.apache.logging.log4j.core.lookup;
#   import org.apache.logging.log4j.core.LogEvent;
#   public class JndiLookup implements StrLookup {
#       public String lookup(String key) { return null; }
#       public String lookup(LogEvent event, String key) { return null; }
#   }
JNDI_STUB_SHA256 = "a4c9009432d21647ca48dc5b06f38e338ef5a196d772d5e162e3f20065cc05cc"
JNDI_STUB = (
    "yv66vgAAADIADwoAAwALBwAMBwANBwAOAQAGPGluaXQ+AQADKClWAQAEQ29kZQEABmxvb2t1cAEA"
    "JihMamF2YS9sYW5nL1N0cmluZzspTGphdmEvbGFuZy9TdHJpbmc7AQBOKExvcmcvYXBhY2hlL2xv"
    "Z2dpbmcvbG9nNGovY29yZS9Mb2dFdmVudDtMamF2YS9sYW5nL1N0cmluZzspTGphdmEvbGFuZy9T"
    "dHJpbmc7DAAFAAYBAC9vcmcvYXBhY2hlL2xvZ2dpbmcvbG9nNGovY29yZS9sb29rdXAvSm5kaUxv"
    "b2t1cAEAEGphdmEvbGFuZy9PYmplY3QBAC5vcmcvYXBhY2hlL2xvZ2dpbmcvbG9nNGovY29yZS9s"
    "b29rdXAvU3RyTG9va3VwACEAAgADAAEABAAAAAMAAQAFAAYAAQAHAAAAEQABAAEAAAAFKrcAAbEA"
    "AAAAAAEACAAJAAEABwAAAA4AAQACAAAAAgGwAAAAAAABAAgACgABAAcAAAAOAAEAAwAAAAIBsAAA"
    "AAAAAA==")


def neuter_jndi(jar):
    """Swap the real JndiLookup for the inert stub. Returns True if it changed
    the jar, False if the jar has no JndiLookup or already has the stub."""
    import base64
    stub = base64.b64decode(JNDI_STUB)
    assert hashlib.sha256(stub).hexdigest() == JNDI_STUB_SHA256
    with zipfile.ZipFile(jar) as z:
        if JNDI not in z.namelist() or z.read(JNDI) == stub:
            return False
        tmp = jar + ".tmp"
        with zipfile.ZipFile(tmp, "w") as dst:
            for info in z.infolist():
                data = stub if info.filename == JNDI else z.read(info.filename)
                dst.writestr(info, data, compress_type=info.compress_type)
    os.replace(tmp, jar)
    with zipfile.ZipFile(jar) as z:
        if z.read(JNDI) != stub or z.testzip() is not None:
            sys.exit("rewriting %s failed" % jar)
    return True


def jars_with_live_jndi(root):
    """Every jar under root holding a JndiLookup that is not the stub."""
    hits = []
    for r, _, files in os.walk(root):
        for f in files:
            if f.endswith(".jar"):
                try:
                    with zipfile.ZipFile(os.path.join(r, f)) as z:
                        if JNDI in z.namelist() and hashlib.sha256(
                                z.read(JNDI)).hexdigest() != JNDI_STUB_SHA256:
                            hits.append(os.path.join(r, f))
                except (zipfile.BadZipFile, OSError):
                    pass
    return hits


def write_manifest(out):
    """sha256 of every server jar, mod and config file. The world is only valid
    with exactly these: Transformers assigns material IDs at first load, and a
    missing mod deletes its items. Each backup carries a copy, so a restore can
    rebuild the same set. Check it with `sha256sum -c MANIFEST.sha256`."""
    lines = []
    tops = [f for f in os.listdir(out) if f.endswith(".jar")] + ["mods", "config"]
    for top in sorted(tops):
        p = os.path.join(out, top)
        files = [p] if os.path.isfile(p) else sorted(
            os.path.join(r, f) for r, _, fs in os.walk(p) for f in fs)
        for f in files:
            h = hashlib.sha256()
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            lines.append("%s *%s" % (h.hexdigest(), os.path.relpath(f, out).replace(os.sep, "/")))
    with open(os.path.join(out, "MANIFEST.sha256"), "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(lines)


def drop_reason(name):
    for prefix, why in CLIENT_ONLY:
        if name.startswith(prefix):
            return why
    return None


def is_junk(name):
    return any(fnmatch.fnmatch(name, pat) for pat in JUNK)


def copy_tree(src, dst):
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if is_junk(n)])


def codechicken_of(inst):
    """Which CodeChickenCore the instance runs: 'GTNH CodeChickenCore <ver>', 'stock', or exit.

    Since 2026-10-18 the pack runs GTNH CodeChickenCore 1.4.22 (CodeChickenLib merged
    in) so Angelica clients can join; its NEI packets differ from stock CCC's, so the
    server must run exactly what the clients run, and never both."""
    mods = os.path.join(inst, "mods")
    top = [e for e in os.listdir(mods) if e.startswith("CodeChickenCore") and e.endswith(".jar")]
    lib = os.path.join(mods, "1.7.10")
    ccl = [e for e in os.listdir(lib) if e.startswith("CodeChickenLib")] if os.path.isdir(lib) else []
    gtnh = [e for e in top if e != "CodeChickenCore.jar"]
    if len(top) != 1:
        sys.exit("the instance has %s CodeChickenCore jars (%s); it needs exactly one"
                 % (len(top), ", ".join(top) or "no"))
    if gtnh:
        if ccl:
            sys.exit("the instance has GTNH %s and %s: CodeChickenLib is merged into GTNH "
                     "CodeChickenCore, so this is a duplicate mod" % (gtnh[0], ", ".join(ccl)))
        return "GTNH " + gtnh[0][:-4]
    return "stock"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instance", required=True, help="the client instance (mods/, config/ live here)")
    ap.add_argument("--forge-install",
                    help="stock Forge 1.7.10 server install: 1558, or with --java25 1614 "
                         "(optional then: the build installs one into --cache)")
    ap.add_argument("--out", required=True, help="server directory to create")
    ap.add_argument("--ccl", help="only for a pack on stock CodeChickenCore + CodeChickenLib (before "
                                  "2026-10-18): patched CodeChickenLib jar to use instead of the "
                                  "client's. Refused with GTNH CodeChickenCore, which needs no patch")
    ap.add_argument("--java", help="the java.exe start.bat runs; default: the Java 8 JRE, or "
                                   "with --java25 the newest Temurin 25 found")
    ap.add_argument("--java25", action="store_true",
                    help="build the slim Java 25 server (lwjgl3ify + UniMixins on Forge 1614) "
                         "instead of the Java 8 one")
    ap.add_argument("--cache", default=default_cache(),
                    help="where --java25 keeps its pinned downloads (default: %(default)s)")
    ap.add_argument("--java8", default=JAVA8_DEFAULT,
                    help="Java 8 for the Forge 1614 installer (--java25 only)")
    ap.add_argument("--tweaks",
                    help="QuestForgeTweaks jar to install instead of the instance's (a build "
                         "newer than the live pack's)")
    ap.add_argument("--xmx", default="10G",
                    help="server heap; 10G suits 10-15 players on a 12 GB host")
    # These four default to None: on a rebuild the kept server.properties wins
    # unless the option is given. First build: 25565, 15, 6, true.
    ap.add_argument("--port", type=int)
    ap.add_argument("--max-players", type=int)
    ap.add_argument("--view-distance", type=int,
                    help="keep equal to JAS's spawning/counting distance (see SERVER_PROPERTIES)")
    ap.add_argument("--online-mode",
                    help="false only for a local test with offline-launched clients; a "
                         "public offline server lets anyone join under any name")
    ap.add_argument("--player", action="append", default=[],
                    help="whitelist this name (repeatable). With online-mode=false this is "
                         "the only reliable way: the console's `whitelist add` stores the "
                         "wrong UUID. With online-mode=true use `whitelist add` instead.")
    ap.add_argument("--force", action="store_true",
                    help="rebuild an existing --out; its world, player lists, server.properties, "
                         "logs, crash reports, backups, supervisor.json and play-options.json are kept")
    # Server-only additions and the owner's decisions. Each is remembered in
    # play-options.json, so a rebuild without the option keeps the last choice.
    ap.add_argument("--opis", dest="opis", action="store_const", const=True, default=None,
                    help="add Opis 1.2.5, the profiler (pinned download, sha256-checked); "
                         "clients need nothing. --no-opis removes it")
    ap.add_argument("--no-opis", dest="opis", action="store_const", const=False)
    ap.add_argument("--world-border", type=int, metavar="RADIUS",
                    help="add WorldBorder-Forge 1.0.2 with a square border of this radius (blocks) "
                         "around 0,0 in the overworld; 0 removes it. Clients need nothing")
    ap.add_argument("--rules", metavar="FILE",
                    help="apply the owner's decisions from this JSON file ({decision id: value}; "
                         "see tools/server/rules.example.json); 'none' forgets them")
    ap.add_argument("--backup-mirror", metavar="DIR",
                    help="the supervisor copies every daily backup into this folder as well "
                         "(a Syncthing or cloud folder gives an off-machine copy); 'none' stops it")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    old_props = read_properties(os.path.join(out, "server.properties"))
    defaults = {"server-port": "25565", "max-players": "15", "view-distance": "6",
                "online-mode": "true"}
    given = {"server-port": args.port, "max-players": args.max_players,
             "view-distance": args.view_distance, "online-mode": args.online_mode}
    eff = {k: str(v).lower() if v is not None else old_props.get(k, defaults[k])
           for k, v in given.items()}

    opts = load_json(os.path.join(out, PLAY_OPTIONS), {})
    if args.opis is not None:
        opts["opis"] = args.opis
    if args.world_border is not None:
        if args.world_border < 0:
            sys.exit("--world-border is a radius in blocks (0 removes the border)")
        opts["world_border"] = args.world_border or None
    if args.rules:
        if args.rules.lower() == "none":
            opts["rules"] = None
            opts.pop("rules_file", None)
        else:
            rules = load_json(os.path.abspath(args.rules), None)
            if not isinstance(rules, dict):
                sys.exit("--rules %s: not a JSON object" % args.rules)
            opts["rules"] = rules
            opts["rules_file"] = os.path.abspath(args.rules)
    rules = opts.get("rules") or {}
    rule_props, sup_updates = {}, {}
    if args.backup_mirror:
        sup_updates["backup_mirror"] = "" if args.backup_mirror.lower() == "none" \
            else os.path.abspath(args.backup_mirror)
    # Checked before anything is deleted, so a bad command line costs nothing.
    if args.player and eff["online-mode"] == "true":
        sys.exit("--player writes offline-mode UUIDs; with --online-mode true add players "
                 "with `whitelist add <name>` in the server console instead")

    inst = os.path.abspath(args.instance)
    if not os.path.isdir(os.path.join(inst, "mods")):
        sys.exit("no mods/ under %s" % inst)
    if not args.forge_install and not args.java25:
        sys.exit("--forge-install is required (a stock Forge 1558 server install)")
    java = args.java or (find_java25() if args.java25 else JAVA8_DEFAULT)
    if not java:
        sys.exit("--java25: no Temurin 25 found; pass --java <path to java.exe>")

    # These checks need nothing but the inputs, so a refused build costs nothing.
    tweaks = args.tweaks and os.path.abspath(args.tweaks)
    if tweaks and not os.path.isfile(tweaks):
        sys.exit("--tweaks %s does not exist" % tweaks)
    ccc = codechicken_of(inst)
    print("ccc:     %s" % ccc)
    if args.ccl and ccc != "stock":
        sys.exit("--ccl patches stock CodeChickenLib, but the instance runs %s (CodeChickenLib "
                 "merged in, unloadChunk already null-guarded). Adding a CodeChickenLib jar "
                 "would load it twice. Drop --ccl." % ccc)
    if ccc == "stock" and not args.ccl:
        print("WARNING: the instance runs stock CodeChickenCore + CodeChickenLib. Without --ccl "
              "every pregeneration run dies in seconds (WorldExtension.unloadChunk NPE), and "
              "Angelica clients are kicked 5 s after login (NEI packets differ).")
    if args.java25:
        entries = [e for e in os.listdir(os.path.join(inst, "mods")) if not is_junk(e)]
        bad = [e for e in entries if any(e.lower().startswith(f) for f in J25_FORBIDDEN)]
        if bad:
            sys.exit("--java25 builds the slim server, which must not carry %s: on the server "
                     "they become required on every client, and GTNHLib crashes OptiFine "
                     "clients (docs/design/angelica-decision.md, test 1)" % ", ".join(bad))
        tj = tweaks or next((os.path.join(inst, "mods", e) for e in entries
                             if e.startswith("QuestForgeTweaks")), None)
        missing = tweaks_jar_missing(tj) if tj else ["no QuestForgeTweaks jar at all"]
        if missing:
            sys.exit("--java25: the qf-tweaks jar %s lacks the Java 25 fixes for:\n  %s\n"
                     "Install the current qf-tweaks build in the pack first (tools/trial/trial.py "
                     "install), or pass it with --tweaks." % (tj, "\n  ".join(missing)))
        deps = {name: fetch(args.cache, name, url, sha)
                for name, (url, sha, _) in J25_DEPS.items()}
        fi = os.path.abspath(args.forge_install) if args.forge_install else \
            forge1614_install(args.cache, args.java8)
        if not os.path.exists(os.path.join(fi, J25_FORGE)):
            sys.exit("--java25 needs Forge 1614: %s has no %s (lwjgl3ify's launcher loads that "
                     "exact file)" % (fi, J25_FORGE))
    else:
        fi = os.path.abspath(args.forge_install)

    # A rebuild must never cost the friends their world. Everything else in the
    # directory is derived and is thrown away; these are carried across:
    # server.properties, because console and hand changes (MOTD, idle timeout,
    # RCON) would vanish otherwise; logs/ and crash-reports/, because they are
    # the evidence for whatever prompted the rebuild; backups/, obviously.
    level = old_props.get("level-name") or "world"
    keep = [level, "ops.json", "whitelist.json", "banned-players.json", "banned-ips.json",
            "usercache.json", "server.properties", "logs", "crash-reports", "backups",
            "supervisor.json", PLAY_OPTIONS]
    stash = out + ".keep"
    if os.path.exists(out):
        if not args.force:
            sys.exit("%s already exists (use --force to rebuild it; the world is kept)" % out)
        refuse_if_running(out)
        if os.path.exists(stash):
            sys.exit("%s exists from an interrupted rebuild; restore it by hand first" % stash)
        os.makedirs(stash)
        for name in keep:
            if os.path.exists(os.path.join(out, name)):
                shutil.move(os.path.join(out, name), os.path.join(stash, name))
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "mods"))

    # --- Forge server -----------------------------------------------------
    forge = None
    for fn in os.listdir(fi):
        if args.java25 and fn.startswith("forge-1.7.10") and fn != J25_FORGE:
            continue
        if fn.startswith("forge-1.7.10") and fn.endswith("-universal.jar"):
            forge = fn
            shutil.copy2(os.path.join(fi, fn), os.path.join(out, fn))
        elif fn.startswith("minecraft_server") and fn.endswith(".jar"):
            shutil.copy2(os.path.join(fi, fn), os.path.join(out, fn))
    if not forge or not os.path.isdir(os.path.join(fi, "libraries")):
        sys.exit("%s is not a Forge server install (universal jar + libraries/)" % fi)
    shutil.copytree(os.path.join(fi, "libraries"), os.path.join(out, "libraries"))
    print("forge:   %s" % forge)
    for fn in os.listdir(out):
        if fn.startswith("minecraft_server") and fn.endswith(".jar"):
            if neuter_jndi(os.path.join(out, fn)):
                print("log4j:   JndiLookup in %s replaced by an inert stub (Log4Shell)" % fn)
    # Mods are only reported: some check their own signatures, and FML does not
    # put a second log4j in front of the server's anyway.
    left = jars_with_live_jndi(out)
    if [p for p in left if not p.startswith(os.path.join(out, "mods"))]:
        sys.exit("a live JndiLookup is still in: %s" % ", ".join(left))
    for p in left:
        print("WARNING: %s bundles its own JndiLookup (not modified)" % p)

    # --- mods ---------------------------------------------------------------
    kept = dropped = 0
    for entry in sorted(os.listdir(os.path.join(inst, "mods"))):
        src = os.path.join(inst, "mods", entry)
        if is_junk(entry):
            continue
        why = drop_reason(entry)
        if why:
            print("  drop %-40s %s" % (entry, why))
            dropped += 1
            continue
        dst = os.path.join(out, "mods", entry)
        copy_tree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
        kept += 1
    print("mods:    %d kept, %d dropped" % (kept, dropped))

    if tweaks:
        for fn in os.listdir(os.path.join(out, "mods")):
            if fn.startswith("QuestForgeTweaks"):
                os.remove(os.path.join(out, "mods", fn))
        shutil.copy2(tweaks, os.path.join(out, "mods", "QuestForgeTweaks-1.0.jar"))
        print("tweaks:  %s (sha256 %s)" % (tweaks, sha256_file(tweaks)[:12]))

    # The slim Java 25 server, laid out as lwjgl3ify's README says: the
    # launcher jar next to the Forge universal and minecraft_server jars (its
    # manifest Class-Path names both, and libraries/), java9args.txt beside
    # them, the lwjgl3ify mod jar and UniMixins in mods/.
    if args.java25:
        for name, (_, _, dest) in J25_DEPS.items():
            shutil.copy2(deps[name], os.path.join(out, dest))
            print("java25:  %s" % dest)
        forge = J25_LAUNCHER

    # Stock CodeChickenLib's WorldExtension.unloadChunk NPEs when a chunk unloads
    # mid-generation; the patched build guards it. CCL has no @Mod, so the
    # server may differ from clients here without refusing anyone. Only for a
    # pack still on stock CCC (before 2026-10-18): GTNH CodeChickenCore 1.4.22
    # merges CCL in with that guard already, and 40,000 chunks pregenerated on it
    # with 0 failures where stock CCL crashed in a second (2026-10-18).
    if args.ccl:
        libdir = os.path.join(out, "mods", "1.7.10")
        for fn in os.listdir(libdir):
            if fn.startswith("CodeChickenLib"):
                os.remove(os.path.join(libdir, fn))
        shutil.copy2(args.ccl, os.path.join(libdir, "CodeChickenLib-1.7.10-1.1.3.138-universal.jar"))
        print("ccl:     patched build from %s" % args.ccl)

    # --- config, scripts and content ----------------------------------------
    # config/ is copied verbatim from the client. Enchantment, potion and biome
    # IDs are not synced in 1.7.10; they agree only because both sides read the
    # same files. legends/ holds the prebuilt maps six Legends dimensions copy
    # out on first load (see tools/survey/build_server.py).
    for name in ("config", "scripts", "legends", "structures"):
        src = os.path.join(inst, name)
        if os.path.isdir(src):
            copy_tree(src, os.path.join(out, name))
            print("%-8s copied" % (name + ":"))
    if args.java25:
        packcheck_ignore_forge(os.path.join(out, "config", "qfcontent.cfg"))

    # --- the owner's decisions and the server-only additions -------------------
    applied = apply_rules(out, rules, rule_props, sup_updates) if rules else []
    addons = [a[1] for a in applied if isinstance(a, tuple)]
    applied = [a for a in applied if not isinstance(a, tuple)]
    if opts.get("opis"):
        addons.append("opis")
    if opts.get("world_border"):
        addons.append("worldborder")
        write_world_border(out, opts["world_border"], level)
        applied.append("world border: square, radius %d around 0,0 in the overworld "
                       "(config/WorldBorder/borders.cfg; `wb` commands in the console)" % opts["world_border"])
    for key in addons:
        name, url, sha = ADDONS[key]
        shutil.copy2(fetch(args.cache, name, url, sha), os.path.join(out, "mods", name))
        print("addon:   %s" % name)
    for line in applied:
        print("rule:    %s" % line)
    given.update(rule_props)
    eff.update(rule_props)

    for name in keep:
        if os.path.exists(os.path.join(stash, name)):
            shutil.move(os.path.join(stash, name), os.path.join(out, name))
            print("kept:    %s" % name)
    if os.path.isdir(stash):
        os.rmdir(stash)
    # Java 25 refuses to start at all when the -Xlog file's directory is
    # missing (Java 8's -Xloggc just logs nothing). start.bat and the
    # supervisor create it, but a panel host or a hand-typed command would not.
    os.makedirs(os.path.join(out, 'logs'), exist_ok=True)

    if args.player:
        write_whitelist(out, args.player)

    with open(os.path.join(out, "eula.txt"), "w") as fh:
        fh.write("eula=true\n")
    props_path = os.path.join(out, "server.properties")
    template = SERVER_PROPERTIES.format(online=eff["online-mode"], port=eff["server-port"],
                                        max_players=eff["max-players"],
                                        view_distance=eff["view-distance"])
    if os.path.exists(props_path):
        # Kept from the last build: change only what this command line asked
        # for, and add any key the template has gained since.
        with open(props_path, encoding="latin-1") as fh:
            lines = fh.read().splitlines()
        have = {l.split("=", 1)[0] for l in lines if "=" in l and not l.startswith("#")}
        for i, l in enumerate(lines):
            k = l.split("=", 1)[0]
            if given.get(k) is not None and l != "%s=%s" % (k, eff[k]):
                print("server.properties: %s -> %s" % (l, eff[k]))
                lines[i] = "%s=%s" % (k, eff[k])
        for l in template.splitlines():
            if l.split("=", 1)[0] not in have:
                print("server.properties: added %s" % l)
                lines.append(l)
                have.add(l.split("=", 1)[0])
        for k, v in rule_props.items():
            if k not in have:
                print("server.properties: added %s=%s" % (k, v))
                lines.append("%s=%s" % (k, v))
        with open(props_path, "w", encoding="latin-1") as fh:
            fh.write("\n".join(lines) + "\n")
    else:
        lines = template.splitlines()
        for k, v in rule_props.items():
            idx = next((i for i, l in enumerate(lines) if l.split("=", 1)[0] == k), None)
            if idx is None:
                lines.append("%s=%s" % (k, v))
            else:
                lines[idx] = "%s=%s" % (k, v)
        with open(props_path, "w") as fh:
            fh.write("\n".join(lines) + "\n")
    flags = [f.format(xmx=args.xmx) for f in (JVM_FLAGS_J25 if args.java25 else JVM_FLAGS)]
    with open(os.path.join(out, "start.bat"), "w", newline="\r\n") as fh:
        fh.write(START_BAT.format(java=java, forge=forge,
                                  flags=" ^\n ".join(" ".join(flags[i:i + 4])
                                                     for i in range(0, len(flags), 4))))
    with open(os.path.join(out, "start.sh"), "w", newline="\n") as fh:
        fh.write(START_SH.format(forge=forge,
                                 flags=" \\\n ".join(" ".join(flags[i:i + 4])
                                                     for i in range(0, len(flags), 4))))

    # JAS keeps its own spawn radius; a mismatch with view-distance silently
    # changes mob density (see the note above SERVER_PROPERTIES).
    jas = os.path.join(out, "config", "JustAnotherSpawner", "GlobalProperties.cfg")
    if os.path.exists(jas):
        with open(jas) as fh:
            props = json.load(fh)
        for key in ("Distance (in Chunks) to perform entity spawning",
                    "Distance (in Chunks) to perform entity counting"):
            if props.get(key) != int(eff["view-distance"]):
                print("WARNING: JAS %r is %s but view-distance is %s"
                      % (key, props.get(key), eff["view-distance"]))

    # --- supervisor -----------------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    shutil.copy2(os.path.join(here, "supervisor.py"), os.path.join(out, "supervisor.py"))
    with open(os.path.join(out, "start-supervised.bat"), "w", newline="\r\n") as fh:
        fh.write(START_SUPERVISED_BAT)
    if not os.path.exists(os.path.join(out, "supervisor.json")):
        with open(os.path.join(out, "supervisor.json"), "w") as fh:
            json.dump(SUPERVISOR_JSON, fh, indent=2)
    if sup_updates:
        update_supervisor_json(out, sup_updates)
    with open(os.path.join(out, PLAY_OPTIONS), "w") as fh:
        json.dump(opts, fh, indent=2)
    print("supervisor: installed; start the server with start-supervised.bat")

    print("manifest: %d files hashed into MANIFEST.sha256" % write_manifest(out))

    with open(os.path.join(out, "BUILT-FROM.txt"), "w") as fh:
        fh.write("Assembled by tools/server/build_play_server.py\n")
        fh.write("Source instance: %s\n" % inst)
        if args.java25:
            fh.write("Mode: slim Java 25 (%s): Forge 1614, lwjgl3ify 3.0.39, UniMixins 0.3.2.\n"
                     "      Back to Java 8: rebuild without --java25.\n" % java)
        else:
            fh.write("Mode: Java 8 (%s), Forge %s\n" % (java, forge))
        fh.write("CodeChickenCore: %s%s\n" % (ccc, ", CodeChickenLib patched from %s" % args.ccl
                                                  if args.ccl else ""))
        if tweaks:
            fh.write("QuestForgeTweaks: %s, not the instance's\n" % tweaks)
        fh.write("Mods kept: %d   dropped: %d\n" % (kept, dropped))
        if addons:
            fh.write("Server-only additions (clients need nothing): %s\n"
                     % ", ".join(ADDONS[a][0] for a in addons))
        if applied:
            fh.write("Decisions applied (%s%s):\n" % (PLAY_OPTIONS, "; from %s" % opts["rules_file"]
                                                       if opts.get("rules_file") else ""))
            for line in applied:
                fh.write("  %s\n" % line)
        fh.write("\nDropped from the server (every client keeps them):\n")
        for prefix, why in CLIENT_ONLY:
            fh.write("  %-18s %s\n" % (prefix, why))
        fh.write("\nminecraft_server jar: JndiLookup.class replaced by an inert stub (Log4Shell).\n")
        fh.write("sha256 of every jar and config file: MANIFEST.sha256 (`sha256sum -c`).\n")
        fh.write("\nRebuild after ANY mod or config change on the clients; never edit here.\n")

    print("\nserver ready at %s -- start it with start-supervised.bat" % out)


if __name__ == "__main__":
    main()
