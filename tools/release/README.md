# Release tooling: the friends' client

What a friend installs, how it is built, and what to upload. The friend's side is
[`docs/setup/joining-the-server.md`](../../docs/setup/joining-the-server.md).

## What is here

| File | What it does |
|---|---|
| `build_client_release.py` | Builds the raw OptiFine and Angelica game folders from the live Windows instance (`%APPDATA%\.crazycraft4`). With `--prism` it also builds the Prism zips. |
| `build_prism_instance.py` | Turns one raw game folder into `QuestForge-client-instance-<edition>.zip` plus its `.sha1`. |
| `install/Install-QuestForge.ps1` | The friend installer for Windows (PowerShell 5.1 or 7). |
| `install/install-questforge.command` | The friend installer for macOS (Intel Java 8 only). |
| `tests/` | Unit tests for the builder, and installer tests that run both installers against a fake Prism folder and a fake Java. |

## Cut a release on the PC

1. Make sure the instance is current and the repo is up to date (`git pull`).
2. Build the raw folders and the Prism zips in one go:

   ```
   py -3.10 -I tools\release\build_client_release.py --out C:\qfs\release-2026-10-25 ^
       --jars C:\qfb\dl --prism
   ```

   This writes `C:\qfs\release-2026-10-25\QuestForge-OptiFine\`,
   `...\QuestForge-Angelica\`, and `...\prism\` holding
   `QuestForge-client-instance-optifine.zip`, `...-angelica.zip` and their
   `.sha1` files. Add `--no-angelica` to build the OptiFine edition only.

   To build one edition's zip by hand:

   ```
   py -3.10 -I tools\release\build_prism_instance.py --raw C:\qfs\release-2026-10-25\QuestForge-OptiFine ^
       --out C:\qfs\release-2026-10-25\prism --release 2026-10-25
   ```

   The builder refuses to overwrite a zip that is already there. Delete it first
   if you are rebuilding the same release.

3. Check the pack. Extract one zip to a scratch folder and run the existing check
   against it:

   ```
   py -3.10 -I tools\verify_pack.py --instance C:\qfs\scratch\Quest Forge
   py -3.10 -I tools\pack_fingerprint.py --config C:\qfs\scratch\Quest Forge\minecraft\config
   ```

   The fingerprint must equal the one in `questforge-release.json` and the
   `/qfpack` output in the game.

4. Run the tests (they need no GitHub and no real pack):

   ```
   py -3.10 -I -m unittest discover -s tools\release\tests -v
   ```

   On a PC with PowerShell 7 they also run the Windows installer's cases.

5. Publish on GitHub (see the next section).

## What to upload

Create a GitHub release. Its **name must contain "client instance"**, for example
`Quest Forge client instance 2026-10-25`. The installers pick the newest release
with that name that is not a draft, so do not put server payloads or artwork in
the same release.

Attach these files, with these exact names:

| Asset | Source |
|---|---|
| `QuestForge-client-instance-optifine.zip` | `prism\` |
| `QuestForge-client-instance-optifine.zip.sha1` | `prism\` |
| `QuestForge-client-instance-angelica.zip` | `prism\` (optional, for the Angelica edition) |
| `QuestForge-client-instance-angelica.zip.sha1` | `prism\` |
| `Install-QuestForge.ps1` | `tools\release\install\` |
| `install-questforge.command` | `tools\release\install\` |

The installers match the edition by name: an asset whose name contains
`optifine` or `angelica` and ends in `.zip` is that edition. A zip without its
`.sha1` makes the installer refuse (on purpose: the checksum is the only proof
the download is the release).

Upload nothing else: not the raw folders, not `SHA1SUMS.txt`, not the
`questforge-release.json` (both are inside the zip).

## What the zip is

One Prism instance in one top folder, `Quest Forge/`:

| Path | Notes |
|---|---|
| `instance.cfg` | Name, icon, JVM arguments, 8 GB memory defaults. The installer sets this PC's Java and memory. |
| `mmc-pack.json`, `patches/net.minecraftforge.json` | LWJGL 2.9.4-nightly-20150209, Minecraft 1.7.10, Forge as a local component. Same as the live instance. |
| `libraries/forge-...jar` | The hand-patched Forge jar (OptiFine) or stock 1614 (Angelica). Prism finds it there because of `MMC-hint: local`. |
| `minecraft/` | The game folder: mods, config, scripts, resources, `assets/mcheli`, options. |
| `questforge-release.json` | Release name, edition, build date, Forge build, pack date and fingerprint. |
| `SHA1SUMS.txt` | sha1 of every file above. The installer checks each one. |
| `questforge-tools/lite-client/` | `apply-lite.ps1` and its profiles, for the Windows installer's lite and potato options. |
| `perf-preset.command` | The Mac preset switcher. |
| `icon.png` | The instance icon. |

What is **left out** and why is in the docstring of `build_prism_instance.py`. In
short: Prism downloads the vanilla client, the LWJGL natives for each friend's OS,
and the vanilla sound and texture objects; only `assets/mcheli` (no mod jar has
it) and `assets/indexes` are shipped.

The zip imports both ways: **Add instance -> Import** in Prism, or unzipping into
the instances folder. Prism finds `instance.cfg` anywhere in the zip and uses its
folder as the instance root, so the top folder works in both cases.

## What the installers expect

Both installers read the release as a zip and do the same things in the same
order. The details are in the header of each script; the summary:

- **Prism's folder.** Windows: `%APPDATA%\PrismLauncher`, or `-PrismDir` for a
  portable install. Mac: `~/Library/Application Support/PrismLauncher`, or
  `--prism-dir`. `InstanceDir` in `prismlauncher.cfg` is honoured.
- **Java 8 (64-bit).** Windows: the locations the release's launch `.bat` files
  use. Mac: an `x86_64` Java 8 (checked with `-XshowSettings:properties`).
- **Memory.** From installed RAM: Windows 8 GB -> 1024/3072 MiB, 12 GB ->
  1024/4096, 16 GB -> 2048/5120, 32 GB+ -> 2048/6144. Mac: 1024/4096 below 12 GB,
  2048/6144 from 12 GB up.
- **Update.** Keeps `saves/`, `screenshots/`, `options*.txt`, `servers.dat`,
  `journeymap/`, the player's resource and shader packs, and the instance's own
  `instance.cfg` keys. Replaces `mods/`, `config/`, `scripts/`, `resources/`,
  `assets/`, `fonts/`, the release files and the instance's `mmc-pack.json`,
  `patches/`, `libraries/`. Old copies go to `instances\Quest Forge\_qf-backups\<date-time>\`.
- **Lite and potato.** An update keeps the profile the instance is on: it is
  read from `minecraft\mods-lite-removed\` (a potato install moved JourneyMap out).
- **Refusals.** A missing or mismatched `.sha1`, a `SHA1SUMS.txt` mismatch, the
  wrong edition, no Java 8, a folder with the name that is not a Quest Forge
  install, Prism open, or the game running from the instance.
- **Dry run.** `-WhatIf` (PowerShell) or `--dry-run` (Mac) downloads and checks,
  then prints the plan and changes nothing.

## Known gaps

- The Windows installer has only been run under PowerShell 7 on a Mac, against the
  fake Prism folder. The Windows-only paths (CIM for RAM and the running-process
  check, the Java search in `Program Files`, Windows PowerShell 5.1, and
  `apply-lite.ps1` after an install) are not exercised by the tests.
- The Prism import (**Add instance -> Import**) has not been run against a built
  zip. The layout matches Prism's importer as read from its source.
- The Mac lite profile is the `perf-preset.command low` preset. It does not move
  mods the way the Windows `apply-lite.ps1` does.
