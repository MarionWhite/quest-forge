"""Quest Forge: install 3840x2160 LANCZOS upscale of the current 1920 ant background + blur mcmeta
into the live resource pack zip and CustomMenu.jar. Picture content unchanged. Backups in backup-before/."""
import io, os, sys, zipfile, shutil, json
from pathlib import Path
from PIL import Image
LIVE = Path(os.path.expanduser("~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft"))
W = Path(__file__).resolve().parent
ZIP = LIVE / "resourcepacks" / "QuestForge.zip"; JAR = LIVE / "mods" / "CustomMenu.jar"
ENTRY = "assets/custommenu/background.jpg"; META = ENTRY + ".mcmeta"

def replace_entries(path, mapping):
    tmp = path.with_suffix(path.suffix + ".tmpqf")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        done = set()
        for info in zin.infolist():
            if info.filename in mapping:
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time); zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, mapping[info.filename]); done.add(info.filename)
            else:
                zout.writestr(info, zin.read(info.filename))
        for name, data in mapping.items():
            if name not in done:
                zi = zipfile.ZipInfo(name); zi.compress_type = zipfile.ZIP_DEFLATED; zout.writestr(zi, data)
    os.replace(tmp, path)

with zipfile.ZipFile(ZIP) as z:
    src = Image.open(io.BytesIO(z.read(ENTRY))).convert("RGB")
assert src.size == (1920, 1080), src.size
big = src.resize((3840, 2160), Image.Resampling.LANCZOS)
buf = io.BytesIO(); big.save(buf, "JPEG", quality=93, optimize=True, subsampling=0); jpg = buf.getvalue()
(W / "background_3840.jpg").write_bytes(jpg)
meta = json.dumps({"texture": {"blur": True, "clamp": True}}).encode("utf-8")
(W / "background.jpg.mcmeta").write_bytes(meta)
for target in (ZIP, JAR):
    replace_entries(target, {ENTRY: jpg, META: meta})
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        im = Image.open(io.BytesIO(z.read(ENTRY))); m = json.loads(z.read(META))
        print(target.name, "->", ENTRY, im.size, len(jpg), "bytes;", META, m, "; total entries", len(z.namelist()))
print("DONE")
