"""Tests for tools/release/build_prism_instance.py. Run from the repo root:

    python3.10 -I -m unittest discover -s tools/release/tests -v

Builds a tiny fake raw game folder in a temp dir, runs the builder, and checks the zip. The real Mac
Prism instance (if present) is read only and compared for the same keys and components.
"""
import configparser
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.dirname(HERE)
sys.path.insert(0, RELEASE)
import build_prism_instance as bpi  # noqa: E402

REAL = os.path.expanduser("~/Library/Application Support/PrismLauncher/instances/Quest Forge")
FORGE_1558 = "forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
FORGE_1614 = "forge-1.7.10-10.13.4.1614-1.7.10-universal.jar"


def write(path, data=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def make_raw(root, forge=FORGE_1558):
    """A raw game folder shaped like build_client_release.py's output, with things that must be excluded."""
    p = lambda *a: os.path.join(root, *a)
    write(p("bin", "minecraft.jar"), b"vanilla")
    write(p("bin", "natives", "liblwjgl.dylib"))
    write(p("bin", "lib", forge), b"forge-jar")
    write(p("bin", "lib", "guava-16.0.jar"))
    write(p("mods", "AlphaMod-1.jar"), b"alpha")
    write(p("mods", "AlphaMod-1.jar.pre-fix"), b"old")          # excluded: snapshot
    write(p("mods_disabled", "Morph.jar"))                       # excluded
    write(p("config", "alpha.cfg"), "A:x=1\n")
    write(p("config", "Sub", "beta.cfg"), "B:y=2\n")
    write(p("scripts", "s.zs"))
    write(p("resources", "pack", "a.png"))
    write(p("assets", "mcheli", "helicopters", "heli.txt"))
    write(p("assets", "indexes", "1.7.10.json"), "{}")
    write(p("assets", "objects", "ab", "abcdef"))                # excluded: vanilla objects
    write(p("assets", "skins", "s.png"))                         # excluded
    write(p("saves", "World", "level.dat"))                      # excluded
    write(p("logs", "latest.log"))                               # excluded
    write(p("screenshots", "s.png"))                             # excluded
    write(p("options.txt"), "fov:0.5\n")
    write(p("optionsof.txt"), "ofFastRender:false\n")
    write(p("log4j2_17-111.xml"), "<Configuration/>")
    write(p("questforge.ico"), b"ico")
    write(p("journeymap", "config", "jm.cfg"), "k=v")
    write(p("journeymap", "data", "map.png"))                    # excluded: map cache
    write(p("PLAY.bat"), "@echo off")                            # excluded: Windows launcher
    write(p("player-name.txt"), "Someone")                       # excluded: personal
    write(p("SHA1SUMS.txt"), "old")                              # excluded: regenerated
    write(p("minetweaker.log"))                                  # excluded
    return root


def read_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return {n: z.read(n) for n in z.namelist()}


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_cfg(text):
    out = {}
    for line in text.splitlines():
        if "=" in line and not line.startswith("["):
            k, v = line.split("=", 1)
            out[k] = v
    return out


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="qf-prism-test-")
        cls.raw = make_raw(os.path.join(cls.tmp, "QuestForge-OptiFine"))
        cls.out = os.path.join(cls.tmp, "out")
        cls.zip = bpi.build(cls.raw, cls.out, "optifine", "2026-10-25", "2026-10-25",
                            os.path.join(bpi.REPO, "pack", "resourcepack", "pack.png"))
        cls.files = read_zip(cls.zip)
        cls.names = sorted(cls.files)
        cls.I = "Quest Forge/"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def has(self, rel):
        self.assertIn(self.I + rel, self.files, "missing %s in the zip" % rel)
        return self.files[self.I + rel]

    def test_single_top_folder_with_instance_cfg(self):
        tops = {n.split("/")[0] for n in self.names}
        self.assertEqual(tops, {"Quest Forge"})
        self.assertIn(self.I + "instance.cfg", self.names)

    def test_instance_layout(self):
        for rel in ["mmc-pack.json", "instance.cfg", "patches/net.minecraftforge.json",
                    "libraries/" + FORGE_1558, "questforge-release.json", "SHA1SUMS.txt",
                    "perf-preset.command", "icon.png",
                    "questforge-tools/lite-client/apply-lite.ps1",
                    "questforge-tools/lite-client/client-only-drop.txt",
                    "questforge-tools/lite-client/jvm-args.txt",
                    "questforge-tools/lite-client/profiles/lite/options.txt",
                    "minecraft/mods/AlphaMod-1.jar", "minecraft/config/alpha.cfg",
                    "minecraft/config/Sub/beta.cfg", "minecraft/scripts/s.zs",
                    "minecraft/resources/pack/a.png", "minecraft/assets/mcheli/helicopters/heli.txt",
                    "minecraft/assets/indexes/1.7.10.json", "minecraft/options.txt",
                    "minecraft/optionsof.txt", "minecraft/log4j2_17-111.xml", "minecraft/questforge.ico",
                    "minecraft/journeymap/config/jm.cfg"]:
            self.has(rel)

    def test_excludes(self):
        bad = [n for n in self.names if re.search(
            r"/(minecraft/bin/|minecraft/assets/objects/|minecraft/assets/skins/|minecraft/saves/|"
            r"minecraft/logs/|minecraft/screenshots/|minecraft/mods_disabled/|minecraft/journeymap/data/|"
            r"minecraft/PLAY\.bat|minecraft/player-name\.txt|minecraft/SHA1SUMS\.txt|minecraft/minetweaker\.log)"
            r"|\.pre-|natives|minecraft\.jar|guava-16", n)]
        self.assertEqual(bad, [])
        # The only jar in libraries/ is the Forge jar; nothing Prism downloads is shipped.
        libs = [n for n in self.names if "/libraries/" in n]
        self.assertEqual(libs, [self.I + "libraries/" + FORGE_1558])
        self.assertFalse(any("/lib/" in n for n in self.names))

    def test_mmc_pack(self):
        pack = json.loads(self.has("mmc-pack.json"))
        comps = {c["uid"]: c for c in pack["components"]}
        self.assertEqual([c["uid"] for c in pack["components"]],
                         ["org.lwjgl", "net.minecraft", "net.minecraftforge"])
        self.assertEqual(comps["org.lwjgl"]["version"], "2.9.4-nightly-20150209")
        self.assertEqual(comps["net.minecraft"]["version"], "1.7.10")
        self.assertEqual(comps["net.minecraftforge"]["version"], "10.13.4.1558")
        self.assertEqual(comps["net.minecraftforge"]["cachedRequires"][0]["equals"], "1.7.10")

    def test_patch(self):
        patch = json.loads(self.has("patches/net.minecraftforge.json"))
        self.assertEqual(patch["uid"], "net.minecraftforge")
        self.assertEqual(patch["version"], "10.13.4.1558")
        self.assertEqual(patch["mainClass"], "net.minecraft.launchwrapper.Launch")
        self.assertEqual(patch["+tweakers"], ["cpw.mods.fml.common.launcher.FMLTweaker"])
        first = patch["libraries"][0]
        self.assertEqual(first, {"name": "net.minecraftforge:forge:1.7.10-10.13.4.1558-1.7.10:universal",
                                 "MMC-hint": "local"})
        names = [lib["name"] for lib in patch["libraries"]]
        self.assertIn("org.apache.commons:commons-lang3:3.3.2", names)
        self.assertEqual(len(names), len(set(names)))

    def test_cfg(self):
        cfg = parse_cfg(self.has("instance.cfg").decode("utf-8"))
        self.assertEqual(cfg["name"], "Quest Forge")
        self.assertEqual(cfg["InstanceType"], "OneSix")
        self.assertEqual(cfg["MaxMemAlloc"], "3072")
        self.assertEqual(cfg["MinMemAlloc"], "1024")
        self.assertEqual(cfg["OverrideMemory"], "true")
        self.assertEqual(cfg["OverrideJavaArgs"], "true")
        self.assertEqual(cfg["OverrideJavaLocation"], "false")
        self.assertEqual(cfg["iconKey"], "questforge")
        self.assertRegex(cfg["uuid"], r"^[0-9a-f]{32}$")
        jvm = cfg["JvmArgs"]
        self.assertTrue(jvm.startswith('"-XX:+UseG1GC') and jvm.endswith('"'))
        self.assertIn("-Dfml.ignorePatchDiscrepancies=true", jvm)
        self.assertIn("-Dfml.ignoreInvalidMinecraftCertificates=true", jvm)

    def test_release_json_and_sha1sums(self):
        rel = json.loads(self.has("questforge-release.json"))
        self.assertEqual(rel["edition"], "optifine")
        self.assertEqual(rel["forge"], "10.13.4.1558")
        self.assertEqual(rel["release"], "2026-10-25")
        self.assertRegex(rel["pack"]["fingerprint"], r"^[0-9a-f]{12}$")
        sums = self.has("SHA1SUMS.txt").decode("utf-8").splitlines()
        listed = {}
        for line in sums:
            digest, path = line.split("  ", 1)
            listed[path] = digest
        expected = {n[len(self.I):] for n in self.names if n != self.I + "SHA1SUMS.txt"}
        self.assertEqual(set(listed), expected)
        for path, digest in listed.items():
            self.assertEqual(hashlib.sha1(self.files[self.I + path]).hexdigest(), digest, path)

    def test_sidecar_matches_zip(self):
        with open(self.zip + ".sha1", encoding="utf-8") as f:
            digest, name = f.read().split()
        self.assertEqual(name, os.path.basename(self.zip))
        with open(self.zip, "rb") as f:
            self.assertEqual(hashlib.sha1(f.read()).hexdigest(), digest)

    def test_refuses_to_overwrite(self):
        with self.assertRaises(SystemExit):
            bpi.build(self.raw, self.out, "optifine", "x", "2026-10-25", None)

    def test_mac_instance_structure_matches(self):
        """The shipped instance has the same keys and components as the live Mac instance (read only)."""
        if not os.path.isdir(REAL):
            self.skipTest("no live Mac instance here")
        real_pack = read_json(os.path.join(REAL, "mmc-pack.json"))
        ours = json.loads(self.has("mmc-pack.json"))
        self.assertEqual([(c["uid"], c["version"]) for c in real_pack["components"]],
                         [(c["uid"], c["version"]) for c in ours["components"]])
        real_patch = read_json(os.path.join(REAL, "patches", "net.minecraftforge.json"))
        self.assertEqual([lib["name"] for lib in real_patch["libraries"]],
                         [lib["name"] for lib in json.loads(self.has("patches/net.minecraftforge.json"))["libraries"]])
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(os.path.join(REAL, "instance.cfg"), encoding="utf-8")
        real = cp["General"]
        ours_cfg = parse_cfg(self.has("instance.cfg").decode("utf-8"))
        missing = [k for k in ours_cfg if k not in real]
        self.assertEqual(missing, [], "instance.cfg keys the live instance does not have")
        self.assertTrue(os.path.isfile(os.path.join(REAL, "libraries", FORGE_1558)))


class AngelicaTests(unittest.TestCase):
    def test_angelica_uses_1614_and_its_own_name(self):
        tmp = tempfile.mkdtemp(prefix="qf-prism-ang-")
        try:
            raw = make_raw(os.path.join(tmp, "QuestForge-Angelica"), forge=FORGE_1614)
            zp = bpi.build(raw, os.path.join(tmp, "out"), "angelica", "2026-10-25", "2026-10-25", None)
            files = read_zip(zp)
            cfg = parse_cfg(files["Quest Forge Angelica/instance.cfg"].decode("utf-8"))
            self.assertEqual(cfg["name"], "Quest Forge Angelica")
            self.assertEqual(cfg["iconKey"], "default")
            pack = json.loads(files["Quest Forge Angelica/mmc-pack.json"])
            self.assertEqual(pack["components"][2]["version"], "10.13.4.1614")
            self.assertIn("Quest Forge Angelica/libraries/" + FORGE_1614, files)
            self.assertNotIn("Quest Forge Angelica/icon.png", files)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_wrong_forge_for_edition_is_refused(self):
        tmp = tempfile.mkdtemp(prefix="qf-prism-bad-")
        try:
            raw = make_raw(os.path.join(tmp, "raw"), forge=FORGE_1614)
            with self.assertRaises(SystemExit):
                bpi.build(raw, os.path.join(tmp, "out"), "optifine", "x", "2026-10-25", None)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
