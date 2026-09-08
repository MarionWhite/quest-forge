#!/usr/bin/env python3
"""Install a main-menu music track into the QuestForge.zip resource pack (1.7.10).

Mechanism: assets/minecraft/sounds.json overriding the vanilla `music.menu` event with
`replace: true`, so the four vanilla menu tracks are dropped and ours is the only
candidate. Vanilla MusicTicker still decides *when* it plays (first play ~5 s after the
title screen appears, then 1-30 s gaps between repeats) -- see README.md for the
coremod tweak that makes it hit immediately.

Usage:
  python3 install_menu_music.py <track.ogg> [--live]
    default target: the Desktop bundle's minecraft/resourcepacks/QuestForge.zip
    --live: the Prism instance copy instead
A backup of the zip is written next to it before modification.
"""
import json, os, shutil, sys, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLE_ZIP = HERE.parents[1] / "minecraft" / "resourcepacks" / "QuestForge.zip"
LIVE_ZIP = Path.home() / "Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/resourcepacks/QuestForge.zip"
EVENT = "music.menu"
INNER_OGG = "assets/minecraft/sounds/music/menu/questforge_menu.ogg"

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    target = LIVE_ZIP if "--live" in sys.argv else BUNDLE_ZIP
    if not src.suffix == ".ogg":
        sys.exit("track must be an .ogg (Vorbis); convert with: ffmpeg -i in.wav -c:a libvorbis -q:a 5 out.ogg")
    if not target.exists():
        sys.exit(f"missing {target}")
    backup = target.with_name(f"QuestForge.zip.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(target, backup)
    print("backup:", backup)

    with zipfile.ZipFile(target) as z:
        entries = {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}
        infos = {i.filename: i for i in z.infolist()}
    sounds = json.loads(entries.get("assets/minecraft/sounds.json", b"{}").decode("utf-8") or "{}")
    sounds[EVENT] = {
        "category": "music",
        "replace": True,
        "sounds": [{"name": "music/menu/questforge_menu", "stream": True}],
    }
    entries["assets/minecraft/sounds.json"] = json.dumps(sounds, indent=2).encode("utf-8")
    entries[INNER_OGG] = src.read_bytes()

    tmp = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    os.replace(tmp, target)
    print(f"installed {src.name} as {INNER_OGG} in {target}")
    print("sounds.json now:", json.dumps(sounds[EVENT]))

if __name__ == "__main__":
    main()
