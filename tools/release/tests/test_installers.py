"""Tests for the friend installers: install-questforge.command (macOS) and Install-QuestForge.ps1 (Windows).

    python3.10 -I -m unittest discover -s tools/release/tests -v

The macOS installer runs everywhere bash does. The PowerShell one runs when pwsh is on PATH (or
QF_PWSH points at it); on a Mac without it those cases are skipped. Each case builds a real zip with
build_prism_instance.py from a fake raw folder, against a temp Prism folder and a fake Java 8.
Process checks are skipped in the installer tests except for the macOS "game is running" case.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.dirname(HERE)
sys.path.insert(0, RELEASE)
sys.path.insert(0, HERE)
import build_prism_instance as bpi  # noqa: E402
from test_build_prism_instance import make_raw, FORGE_1558, FORGE_1614  # noqa: E402

MAC = os.path.join(RELEASE, "install", "install-questforge.command")
WIN = os.path.join(RELEASE, "install", "Install-QuestForge.ps1")
PWSH = os.environ.get("QF_PWSH") or shutil.which("pwsh")

FAKE_JAVA = """#!/bin/sh
# A stand-in for a Java 8 x64 (the installers ask it for -version and -XshowSettings:properties).
echo 'java version "1.8.0_162"' 1>&2
echo 'Java HotSpot(TM) 64-Bit Server VM (build 25.162-b12, mixed mode)' 1>&2
echo '    java.version = 1.8.0_162' 1>&2
echo '    os.arch = x86_64' 1>&2
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_zip(raw, out, edition, date):
    return bpi.build(raw, out, edition, date, date, os.path.join(bpi.REPO, "pack", "resourcepack", "pack.png"))


class Fixtures(unittest.TestCase):
    """Builds the zips and fake tools once for the whole module."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="qf-installers-")
        t = cls.tmp
        raw1 = make_raw(os.path.join(t, "raw1"))
        cls.zip1 = build_zip(raw1, os.path.join(t, "out1"), "optifine", "2026-10-25")
        raw2 = make_raw(os.path.join(t, "raw2"))
        os.remove(os.path.join(raw2, "mods", "AlphaMod-1.jar"))
        write(os.path.join(raw2, "mods", "AlphaMod-2.jar"), "alpha2")
        write(os.path.join(raw2, "config", "alpha.cfg"), "A:x=99\n")
        cls.zip2 = build_zip(raw2, os.path.join(t, "out2"), "optifine", "2026-10-26")
        rawa = make_raw(os.path.join(t, "rawa"), forge=FORGE_1614)
        cls.zip_ang = bpi.build(rawa, os.path.join(t, "outa"), "angelica", "2026-10-26", "2026-10-26", None)
        cls.java = os.path.join(t, "jdk", "bin", "java")
        write(cls.java, FAKE_JAVA)
        os.chmod(cls.java, 0o755)
        cls.releases = os.path.join(t, "releases.json")
        listing = [
            {"name": "Quest Forge server payload", "draft": False,
             "assets": [{"name": "QuestForge-server.zip", "browser_download_url": "file:///nope.zip"}]},
            {"name": "Quest Forge client instance (draft)", "draft": True,
             "assets": [{"name": "QuestForge-client-instance-optifine.zip",
                         "browser_download_url": "file:///nope.zip"},
                        {"name": "QuestForge-client-instance-optifine.zip.sha1",
                         "browser_download_url": "file:///nope.sha1"}]},
            {"name": "Quest Forge client instance 2026-10-26", "draft": False,
             "assets": [{"name": "QuestForge-client-instance-optifine.zip",
                         "browser_download_url": "file://" + cls.zip2},
                        {"name": "QuestForge-client-instance-optifine.zip.sha1",
                         "browser_download_url": "file://" + cls.zip2 + ".sha1"}]},
            {"name": "Quest Forge client instance 2026-10-25", "draft": False,
             "assets": [{"name": "QuestForge-client-instance-optifine.zip",
                         "browser_download_url": "file://" + cls.zip1},
                        {"name": "QuestForge-client-instance-optifine.zip.sha1",
                         "browser_download_url": "file://" + cls.zip1 + ".sha1"}]},
        ]
        write(cls.releases, json.dumps(listing))
        write(os.path.join(t, "releases-none.json"), json.dumps(listing[:1]))
        cls.releases_none = os.path.join(t, "releases-none.json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class InstallerMixin:
    """Cases that every installer must pass. Subclasses supply invoke() and the memory rule."""

    # Set by subclasses.
    MEM = None          # callable: installed GB -> (min MiB, max MiB)

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="qf-case-", dir=self.tmp)
        self.prism = os.path.join(self.work, "Prism")
        self.instances = os.path.join(self.prism, "instances")
        os.makedirs(self.instances)
        write(os.path.join(self.prism, "prismlauncher.cfg"), "[General]\nConfigVersion=1.3\n")
        self.target = os.path.join(self.instances, "Quest Forge")
        self.mc = os.path.join(self.target, "minecraft")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    # ---- helpers ----
    def invoke(self, dry=False, skip_process=True, ram=8, profile="none", zip_path=None, releases=None,
               edition=None, instance_name=None, java=None):
        raise NotImplementedError

    def install(self, **kw):
        kw.setdefault("zip_path", self.zip1)
        return self.invoke(**kw)

    def cfg(self):
        return read(os.path.join(self.target, "instance.cfg"))

    def cfg_value(self, key):
        for line in self.cfg().splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1]
        return None

    def player_state(self):
        m = self.mc
        write(os.path.join(m, "options.txt"), "fov:0.9\n")
        write(os.path.join(m, "saves", "World", "level.dat"), "level")
        write(os.path.join(m, "servers.dat"), "servers")
        write(os.path.join(m, "screenshots", "s1.png"), "shot")
        write(os.path.join(m, "journeymap", "data", "map.png"), "map")
        write(os.path.join(m, "resourcepacks", "MyPack.zip"), "rp")
        write(os.path.join(m, "shaderpacks", "Mine.zip"), "sp")
        write(os.path.join(m, "mods", "OldMod.jar"), "old")
        write(os.path.join(m, "config", "player-own.cfg"), "mine")
        write(os.path.join(m, "mods-lite-removed", "SoundFilters.jar"), "sf")
        # a per-instance uuid and a UI section the update must keep
        cfgp = os.path.join(self.target, "instance.cfg")
        with open(cfgp, "a", encoding="utf-8") as f:
            f.write("[UI]\nmods_Page\\Columns=\"keep\"\n")

    # ---- cases ----
    def test_dry_run_changes_nothing(self):
        r = self.install(dry=True)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("nothing was changed", r.out.lower())
        self.assertEqual(os.listdir(self.instances), [])

    def test_fresh_install_layout_and_cfg(self):
        r = self.install(ram=8)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue(os.path.isfile(os.path.join(self.mc, "mods", "AlphaMod-1.jar")))
        self.assertTrue(os.path.isfile(os.path.join(self.target, "libraries", FORGE_1558)))
        self.assertFalse(os.path.exists(os.path.join(self.mc, "bin")))
        text = self.cfg()
        self.assertTrue(text.splitlines()[0] == "[General]")
        self.assertEqual(self.cfg_value("name"), "Quest Forge")
        self.assertEqual(self.cfg_value("JavaPath"), self.java)
        self.assertEqual(self.cfg_value("OverrideJavaLocation"), "true")
        self.assertEqual(self.cfg_value("OverrideMemory"), "true")
        mn, mx = self.MEM(8)
        self.assertEqual(self.cfg_value("MinMemAlloc"), str(mn))
        self.assertEqual(self.cfg_value("MaxMemAlloc"), str(mx))
        self.assertIn("-Dfml.ignorePatchDiscrepancies=true", self.cfg_value("JvmArgs"))
        self.assertRegex(self.cfg_value("uuid"), r"^[0-9a-f]{32}$")
        self.assertTrue(os.path.isfile(os.path.join(self.prism, "icons", "questforge.png")))

    def test_memory_follows_the_ram_table(self):
        r = self.install(ram=16)
        self.assertEqual(r.returncode, 0, r.out)
        mn, mx = self.MEM(16)
        self.assertEqual(self.cfg_value("MaxMemAlloc"), str(mx))
        self.assertEqual(self.cfg_value("MinMemAlloc"), str(mn))

    def test_update_keeps_player_state_and_replaces_mods_and_config(self):
        self.assertEqual(self.install().returncode, 0)
        self.player_state()
        r = self.install(zip_path=self.zip2)
        self.assertEqual(r.returncode, 0, r.out)
        m = self.mc
        self.assertEqual(read(os.path.join(m, "options.txt")), "fov:0.9\n")
        self.assertEqual(read(os.path.join(m, "saves", "World", "level.dat")), "level")
        self.assertEqual(read(os.path.join(m, "servers.dat")), "servers")
        self.assertEqual(read(os.path.join(m, "screenshots", "s1.png")), "shot")
        self.assertEqual(read(os.path.join(m, "journeymap", "data", "map.png")), "map")
        self.assertEqual(read(os.path.join(m, "resourcepacks", "MyPack.zip")), "rp")
        self.assertEqual(read(os.path.join(m, "shaderpacks", "Mine.zip")), "sp")
        # replaced
        self.assertTrue(os.path.isfile(os.path.join(m, "mods", "AlphaMod-2.jar")))
        self.assertFalse(os.path.exists(os.path.join(m, "mods", "AlphaMod-1.jar")))
        self.assertFalse(os.path.exists(os.path.join(m, "mods", "OldMod.jar")))
        self.assertEqual(read(os.path.join(m, "config", "alpha.cfg")), "A:x=99\n")
        self.assertFalse(os.path.exists(os.path.join(m, "config", "player-own.cfg")))
        # the cfg keeps the player's own keys and sections
        self.assertIn("[UI]", self.cfg())
        self.assertIn("mods_Page", self.cfg())
        self.assertEqual(self.cfg_value("JavaPath"), self.java)
        self.assertIn("2026-10-26", read(os.path.join(self.target, "questforge-release.json")))

    def test_update_backs_up_what_it_replaced(self):
        self.install()
        self.player_state()
        self.assertEqual(self.install(zip_path=self.zip2).returncode, 0)
        backups = glob.glob(os.path.join(self.target, "_qf-backups", "*"))
        self.assertEqual(len(backups), 1)
        b = backups[0]
        self.assertTrue(os.path.isfile(os.path.join(b, "minecraft", "mods", "OldMod.jar")))
        self.assertTrue(os.path.isfile(os.path.join(b, "minecraft", "config", "player-own.cfg")))
        self.assertTrue(os.path.isfile(os.path.join(b, "minecraft", "mods-lite-removed", "SoundFilters.jar")))
        self.assertTrue(os.path.isfile(os.path.join(b, "instance.cfg")))

    def test_tampered_zip_is_refused_and_nothing_is_created(self):
        bad = os.path.join(self.work, "bad.zip")
        shutil.copy(self.zip1, bad)
        write(bad + ".sha1", "0" * 40 + "  bad.zip\n")
        r = self.install(zip_path=bad)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("damaged", r.out.lower())
        self.assertFalse(os.path.exists(self.target))

    def test_file_that_does_not_match_its_sha1sums_is_refused(self):
        # A zip whose own checksum is right but one shipped file is not what SHA1SUMS.txt says.
        src = os.path.join(self.work, "src")
        with zipfile.ZipFile(self.zip1) as z:
            z.extractall(src)
        write(os.path.join(src, "Quest Forge", "minecraft", "mods", "AlphaMod-1.jar"), "tampered")
        bad = os.path.join(self.work, "tampered.zip")
        with zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(src):
                for f in files:
                    p = os.path.join(root, f)
                    z.write(p, os.path.relpath(p, src).replace(os.sep, "/"))
        digest = hashlib.sha1()
        with open(bad, "rb") as f:
            digest.update(f.read())
        write(bad + ".sha1", digest.hexdigest() + "  tampered.zip\n")
        r = self.install(zip_path=bad)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("do not match", r.out)
        self.assertFalse(os.path.exists(self.target))

    def test_missing_sha1_sidecar_is_refused(self):
        lone = os.path.join(self.work, "lone.zip")
        shutil.copy(self.zip1, lone)
        r = self.install(zip_path=lone)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(".sha1", r.out)

    def test_wrong_edition_is_refused(self):
        r = self.install(edition="angelica", zip_path=self.zip1)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("edition", r.out)
        self.assertFalse(os.path.exists(self.target))

    def test_angelica_installs_as_its_own_instance(self):
        r = self.install(edition="angelica", zip_path=self.zip_ang)
        self.assertEqual(r.returncode, 0, r.out)
        ang = os.path.join(self.instances, "Quest Forge Angelica")
        self.assertTrue(os.path.isfile(os.path.join(ang, "libraries", FORGE_1614)))
        self.assertIn("Quest Forge Angelica", read(os.path.join(ang, "instance.cfg")))

    def test_unrelated_folder_with_the_name_is_not_touched(self):
        write(os.path.join(self.target, "notes.txt"), "mine")
        r = self.install()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a Quest Forge install", r.out)
        self.assertEqual(read(os.path.join(self.target, "notes.txt")), "mine")

    def test_java_missing_stops_before_anything_is_written(self):
        r = self.install(java=os.path.join(self.work, "no-such-java"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Java 8", r.out)
        self.assertFalse(os.path.exists(self.target))

    def test_release_is_chosen_from_the_listing(self):
        r = self.invoke(releases=self.releases, zip_path=None)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("2026-10-26", read(os.path.join(self.target, "questforge-release.json")))

    def test_no_client_release_in_listing_is_refused(self):
        r = self.invoke(releases=self.releases_none, zip_path=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("client instance", r.out)
        self.assertFalse(os.path.exists(self.target))


@unittest.skipUnless(os.path.exists(MAC), "macOS installer missing")
class MacInstaller(InstallerMixin, Fixtures):
    @staticmethod
    def MEM(gb):
        # tools/release/install/install-questforge.command: below 12 GB -> 1024/4096, else 2048/6144.
        return (1024, 4096) if gb < 12 else (2048, 6144)

    def invoke(self, dry=False, skip_process=True, ram=8, profile="none", zip_path=None, releases=None,
               edition=None, instance_name=None, java=None):
        args = ["/bin/bash", MAC, "--prism-dir", self.prism, "--java", java or self.java,
                "--ram-gb", str(ram), "--profile", profile, "--no-prompt"]
        if zip_path:
            args += ["--zip", zip_path]
        if releases:
            args += ["--releases-json", releases]
        if edition:
            args += ["--edition", edition]
        if instance_name:
            args += ["--instance-name", instance_name]
        if dry:
            args.append("--dry-run")
        if skip_process:
            args.append("--skip-process-check")
        return self._run(args)

    def _run(self, args):
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)

        class R:
            pass
        r = R()
        r.returncode, r.out = p.returncode, p.stdout
        return r

    def test_script_is_executable(self):
        self.assertTrue(os.access(MAC, os.X_OK))

    def test_perf_preset_ships_next_to_the_instance(self):
        self.install()
        self.assertTrue(os.path.isfile(os.path.join(self.target, "perf-preset.command")))

    def test_intel_java_is_required(self):
        arm = os.path.join(self.work, "arm-java")
        write(arm, FAKE_JAVA.replace("os.arch = x86_64", "os.arch = aarch64"))
        os.chmod(arm, 0o755)
        r = self.install(java=arm)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("x86_64", r.out)

    def test_keep_lite_state_reapplies_the_mac_preset(self):
        self.install()
        self.player_state()
        r = self.install(zip_path=self.zip2, profile="keep")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("lite profile is applied", r.out)
        opts = read(os.path.join(self.mc, "options.txt"))
        self.assertIn("fov:0.9", opts)            # the player's own setting is not touched
        self.assertIn("fancyGraphics:false", opts)

    def test_running_minecraft_is_refused(self):
        self.install()
        proc = subprocess.Popen(["bash", "-c", 'exec -a "java -gameDir %s" sleep 60' % self.mc])
        try:
            time.sleep(0.5)
            r = self.invoke(skip_process=False, zip_path=self.zip2)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("Minecraft is running", r.out)
            self.assertEqual(read(os.path.join(self.mc, "mods", "AlphaMod-1.jar")), "alpha")
        finally:
            proc.kill()
            proc.wait()


@unittest.skipUnless(PWSH and os.path.exists(WIN), "pwsh not available (set QF_PWSH or install PowerShell 7)")
class WindowsInstaller(InstallerMixin, Fixtures):
    @staticmethod
    def MEM(gb):
        # Install-QuestForge.ps1 Get-Memory: the RAM table, 8 / 12 / 16 / 32 GB rows.
        if gb < 11:
            return (1024, 3072)
        if gb < 15:
            return (1024, 4096)
        if gb < 28:
            return (2048, 5120)
        return (2048, 6144)

    def invoke(self, dry=False, skip_process=True, ram=8, profile="none", zip_path=None, releases=None,
               edition=None, instance_name=None, java=None):
        args = [PWSH, "-NoProfile", "-File", WIN, "-PrismDir", self.prism, "-JavaPath", java or self.java,
                "-RamGB", str(ram), "-Profile", profile, "-NoPrompt"]
        if zip_path:
            args += ["-Zip", zip_path]
        if releases:
            args += ["-ReleasesJson", releases]
        if edition:
            args += ["-Edition", edition]
        if instance_name:
            args += ["-InstanceName", instance_name]
        if dry:
            args.append("-WhatIf")
        if skip_process:
            args.append("-SkipProcessCheck")
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)

        class R:
            pass
        r = R()
        r.returncode, r.out = p.returncode, p.stdout
        return r

    def test_keep_profile_without_lite_state_is_normal(self):
        self.install()
        r = self.install(zip_path=self.zip2, profile="keep")
        self.assertEqual(r.returncode, 0, r.out)


if __name__ == "__main__":
    unittest.main()
