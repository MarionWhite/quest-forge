"""Reference photos for the Shader Lab: find, check, fetch and list Wikimedia Commons files.

The set lives in tools/shaders/review/reference-frames.json (one list per view of
views-world-master.txt) and the images in C:\\qfb\\shaderdev\\refs\\<view>-<n>.<ext>, outside the
repo; publish_round.py resizes a reference and copies it into a round when a round uses it.
docs/design/shaders/research/briefs/reference-frames.md is generated from the JSON by `doc`.

  py -3.10 -I tools/shaders/review/commons_refs.py search sun glitter lake      # 2-3 words
  py -3.10 -I tools/shaders/review/commons_refs.py search --cat "Category:Belt of Venus"
  py -3.10 -I tools/shaders/review/commons_refs.py sheet out.jpg "File:A.jpg" "File:B.jpg" ...
  py -3.10 -I tools/shaders/review/commons_refs.py inspect "File:Sunset sea Tenerife.JPG"
  py -3.10 -I tools/shaders/review/commons_refs.py add lake_glow "File:X.jpg" --why "..." --sun 6
  py -3.10 -I tools/shaders/review/commons_refs.py fetch [view ...] [--force]
  py -3.10 -I tools/shaders/review/commons_refs.py check [view ...]
  py -3.10 -I tools/shaders/review/commons_refs.py doc

Rules the tool encodes, learned on 2026-10-25:
- Only files whose own file page states CC0, public domain, CC BY or CC BY-SA. The licence
  is read from the page's licence-template span (`licensetpl_short`, HTML-escaped as
  `licensetpl&#95;short`), never from a category and never by grepping the page: every
  Commons page footer mentions "Creative Commons CC0" for structured data.
- The API answers 429 to quick requests and to anonymous User-Agents: one descriptive UA,
  3.5 s between API calls, 1.2 s between image downloads, 3 s between page fetches, backoff
  on 429.
- Thumbnails are served only at the standard widths (STD_WIDTHS); any other width is a 400.
  The API's `thumburl` carries a `?utm_...` query that must be stripped before the extension
  is taken from it.
- CirrusSearch ANDs every word: two or three words find things, six find nothing. Use
  `--cat` to list a category (50 files per API call) or `incategory:Name` in the words.
- CC BY and CC BY-SA need the credit line next to the image; CC BY-SA may be resized, never
  cropped, graded or composited. Nothing from the set ships in the pack.
"""
import argparse
import datetime
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
JSON_PATH = HERE / "reference-frames.json"
VIEWS_PATH = HERE / "views-world-master.txt"
DOC_PATH = REPO / "docs" / "design" / "shaders" / "research" / "briefs" / "reference-frames.md"
REFS_DIR = Path(r"C:\qfb\shaderdev\refs")
CACHE_DIR = Path(os.environ.get("TEMP", ".")) / "qf-commons-refs-cache"

UA = "QuestForgeShaderRefs/1.1 (https://github.com/MarionWhite/quest-forge; shader reference research)"
API = "https://commons.wikimedia.org/w/api.php"
API_GAP, THUMB_GAP, PAGE_GAP = 3.5, 1.2, 3.0
STD_WIDTHS = (20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840)
FETCH_WIDTH = 1920          # >= publish_round's 1600 px reference width
SHEET_WIDTH = 500
EXTMETA = ("LicenseShortName|License|LicenseUrl|Artist|ObjectName|ImageDescription|"
           "DateTimeOriginal|Credit|AttributionRequired")
OK_LICENCE = re.compile(r"^(CC0(\s1\.0)?|Public domain|CC BY(-SA)? \d\.\d( [a-z]{2,3})?)$", re.I)
PAGE_CHECK_VERSION = 2      # bump when the page check changes; older records get re-checked

_last = {"api": 0.0, "thumb": 0.0, "page": 0.0}


# ---------------------------------------------------------------- HTTP, API, cache

def _strip_html(s):
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def http_get(url, kind, binary=False):
    """GET with the project User-Agent, spaced per kind, backing off on 429."""
    gap = {"api": API_GAP, "thumb": THUMB_GAP, "page": PAGE_GAP}[kind]
    wait = _last[kind] + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                back = 20 * (attempt + 1)
                print(f"  429 from Commons, backing off {back}s", file=sys.stderr)
                time.sleep(back)
                continue
            raise
    _last[kind] = time.time()
    return data if binary else data.decode("utf-8")


def api(params, cache=True):
    params = dict(params, format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(params)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:20] + ".json")
    if cache and path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    text = http_get(url, "api")
    path.write_text(text, encoding="utf-8")
    return json.loads(text)


def _summarise(page):
    ii = (page.get("imageinfo") or [{}])[0]
    em = ii.get("extmetadata", {}) or {}
    g = lambda k: (em.get(k, {}) or {}).get("value", "") or ""  # noqa: E731
    lic = _strip_html(g("LicenseShortName"))
    return {
        "title": page["title"], "w": ii.get("width"), "h": ii.get("height"),
        "url": (ii.get("url") or "").split("?")[0],
        "thumb": (ii.get("thumburl") or "").split("?")[0],
        "descurl": ii.get("descriptionurl"),
        "licence": lic, "licence_url": _strip_html(g("LicenseUrl")),
        "artist": _strip_html(g("Artist")), "credit_field": _strip_html(g("Credit")),
        "desc": _strip_html(g("ImageDescription")), "date": _strip_html(g("DateTimeOriginal")),
        "ok": bool(OK_LICENCE.match(lic)),
    }


def _imageinfo_params():
    return {"prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": FETCH_WIDTH,
            "iiextmetadatafilter": EXTMETA}


def info(titles):
    out = []
    for i in range(0, len(titles), 50):
        d = api({"action": "query", "titles": "|".join(titles[i:i + 50]), **_imageinfo_params()})
        out += [_summarise(p) for p in d.get("query", {}).get("pages", []) if p.get("imageinfo")]
    return {e["title"]: e for e in out}


def list_category(cat, limit):
    out, cont = [], {}
    while len(out) < limit:
        d = api({"action": "query", "generator": "categorymembers", "gcmtitle": cat, "gcmtype": "file",
                 "gcmlimit": min(50, limit - len(out)), **_imageinfo_params(), **cont})
        out += [_summarise(p) for p in d.get("query", {}).get("pages", []) if p.get("imageinfo")]
        if "continue" not in d:
            break
        cont = d["continue"]
    return out


def search_files(words, limit):
    out, cont = [], {}
    while len(out) < limit:
        d = api({"action": "query", "generator": "search", "gsrsearch": words, "gsrnamespace": 6,
                 "gsrlimit": min(50, limit - len(out)), **_imageinfo_params(), **cont})
        out += [_summarise(p) for p in d.get("query", {}).get("pages", []) if p.get("imageinfo")]
        if "continue" not in d:
            break
        cont = d["continue"]
    return out


def rendition_url(meta, width):
    """URL of the standard-width rendition, or the original when it is no wider than that."""
    if width not in STD_WIDTHS:
        raise ValueError(f"width {width} is not a standard Commons thumbnail width {STD_WIDTHS}")
    if not meta["w"] or meta["w"] <= width or "px-" not in meta["thumb"]:
        return meta["url"]
    return re.sub(r"/\d+px-", f"/{width}px-", meta["thumb"])


# ---------------------------------------------------------------- licence check on the file page

def file_page_licences(title):
    """Licence short names printed by the licence templates on the file's own page."""
    url = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    page = http_get(url, "page")
    shorts = re.findall(r'class="licensetpl(?:&#95;|_)short"[^>]*>(.*?)</span>', page, flags=re.S)
    return [_strip_html(s) for s in shorts], url


def licence_matches(recorded, shorts):
    rec = recorded.replace(" ", "").lower()
    for s in shorts:
        t = s.replace(" ", "").lower()
        if t == rec:
            return True
        if rec.startswith("publicdomain") and (t.startswith("publicdomain") or t.startswith("pd")):
            return True
        if rec.startswith("cc0") and t.startswith("cc0"):
            return True
    return False


def credit_line(artist, licence):
    lic = "public domain" if licence.lower().startswith("public domain") else licence
    return f"{artist}, {lic}, via Wikimedia Commons"


# ---------------------------------------------------------------- the set

def load_set():
    if not JSON_PATH.exists():
        return {}
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def save_set(data):
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    JSON_PATH.write_text(text, encoding="utf-8", newline="\n")


def view_names():
    names = []
    for line in VIEWS_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            names.append(s.split()[0])
    return names


def view_params():
    d = {}
    for line in VIEWS_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            p = s.split()
            d[p[0]] = p
    return d


def local_name(view, n, download_url):
    ext = os.path.splitext(urllib.parse.unquote(download_url.split("?")[0]))[1].lower() or ".jpg"
    if ext == ".jpeg":
        ext = ".jpg"
    return str(REFS_DIR / f"{view}-{n}{ext}")


def fetch_entry(entry, force=False):
    """Download the entry's rendition if missing, open it with PIL, record the pixel size."""
    dest = Path(entry["local_file"])
    if force or not dest.exists():
        REFS_DIR.mkdir(parents=True, exist_ok=True)
        data = http_get(entry["download"], "thumb", binary=True)
        dest.write_bytes(data)
    im = Image.open(dest)
    im.load()
    entry["pixel_size"] = [im.width, im.height]
    if im.width < 1600 and im.height < 1600:
        print(f"  warning: {dest.name} is only {im.width}x{im.height} (publish_round wants 1600 px)")
    return entry


def check_entry(entry):
    shorts, _ = file_page_licences(entry["file"])
    entry["licence_on_file_page"] = shorts
    entry["page_check_version"] = PAGE_CHECK_VERSION
    entry["licence_check"] = "match" if licence_matches(entry["licence"], shorts) else "MISMATCH"
    entry["checked"] = datetime.date.today().isoformat()
    return entry


def make_entry(view, n, meta, why, sun=None, notes="", author=None):
    dl = rendition_url(meta, FETCH_WIDTH)
    artist = author or meta["artist"]
    thumb330 = rendition_url(meta, 330)
    return {
        "file": meta["title"], "source": meta["descurl"], "download": dl, "title": meta["title"][5:],
        "author": artist, "author_as_printed": meta["artist"][:200],
        "licence": meta["licence"], "licence_url": meta["licence_url"],
        "licence_on_file_page": [], "page_check_version": 0, "licence_check": "unchecked",
        "credit": credit_line(artist, meta["licence"]),
        "why": why, "sun_elevation_deg_estimate": sun, "notes": notes,
        "local_file": local_name(view, n, dl), "pixel_size": None,
        "original_size": [meta["w"], meta["h"]], "thumb_330": thumb330, "taken": meta["date"],
        "checked": "",
    }


def fmt(e, i=None):
    tag = "OK " if e["ok"] else "-- "
    pre = f"[{i}] " if i is not None else ""
    return (f"{tag}{pre}{e['title'][5:]} | {e['w']}x{e['h']} | {e['licence']} | {e['artist'][:40]} | "
            f"{e['date'][:19]} | {e['desc'][:120]}")


# ---------------------------------------------------------------- contact sheets

def thumb_file(title, width):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{hashlib.sha1(title.encode('utf-8')).hexdigest()[:16]}_{width}.jpg"


def build_sheet(out, titles, cols=3, w=SHEET_WIDTH):
    meta = info(titles)
    imgs = []
    for t in titles:
        try:
            m = meta[t]
            path = thumb_file(t, w)
            if not path.exists():
                data = http_get(rendition_url(m, w), "thumb", binary=True)
                Image.open(io.BytesIO(data)).convert("RGB").save(path, quality=85)
            im = Image.open(path).convert("RGB")
        except Exception as e:  # noqa: BLE001
            print(f"  thumb failed for {t}: {e}", file=sys.stderr)
            im = Image.new("RGB", (w, w * 2 // 3), (60, 60, 60))
        if im.width != w:
            im = im.resize((w, max(1, round(im.height * w / im.width))))
        imgs.append(im)
    rows = (len(imgs) + cols - 1) // cols
    row_h = [max(im.height for im in imgs[r * cols:(r + 1) * cols]) + 22 for r in range(rows)]
    canvas = Image.new("RGB", (cols * (w + 6), sum(row_h) + 6), (20, 20, 20))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    y = 3
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(imgs):
                break
            x = 3 + c * (w + 6)
            canvas.paste(imgs[i], (x, y + 22))
            draw.rectangle([x, y, x + w, y + 22], fill=(0, 0, 0))
            draw.text((x + 4, y + 1), f"[{i}] {titles[i][5:][:48]}", fill=(255, 230, 80), font=font)
        y += row_h[r]
    canvas.save(out, quality=82)
    print(out, canvas.size)


# ---------------------------------------------------------------- the doc

DOC_HEADER = """# Reference photos, one set per Shader Lab view

Written 2026-10-25 for the render-loop agent, so that every round can put a real-world frame
beside our render without a fresh search. One primary and one alternate per view where Commons
had a match; the file list is `tools/shaders/review/reference-frames.json` (the source of truth:
file page, download URL, author, licence, credit line, why it was chosen, an estimated sun
elevation, pixel size) and the images themselves are in `C:\\qfb\\shaderdev\\refs\\<view>-<n>.<ext>`
(not in the repo: `publish_round.py` resizes a reference to 1600 px and copies it into the round
when a round uses it). Every photo was checked on its own Commons file page: the licence
recorded here is the one the file page's licence template prints, not the category's. This
page is generated from the JSON by `tools/shaders/review/commons_refs.py doc`; edit the JSON
(or the tool's header text), not this file.

## How to use them in a round

In the round spec, attach a reference to the option it should sit beside:

```
"ref": {"img": "C:/qfb/shaderdev/refs/ocean_sunset-1.jpg",
        "credit": "<credit from the JSON>",
        "source": "<source from the JSON>",
        "title": "<title from the JSON>"}
```

`publish_round.py` refuses a reference without `credit` and `source`. Copy both from the JSON
verbatim; the credit line is in the house style the round-6 publisher already writes
(`<Artist>, <licence>, via Wikimedia Commons`). The `why` field says what the photo is for; the
critic and the owner should read it as the question the photo answers, not as a target to copy.
The `sun_elevation_deg_estimate` is read off the photo (horizon, shadow length, the disc's
height) and is only there so a photo is not put beside a view whose sun is at a different
height; the view file's own numbers (`views-world-master.txt`, header) are the authority for
our side.

Which brief and scene each set supports:

- **Water** (`water.md`): `ocean_sunset`, `lake_glitter`, `lake_glow`, `shore_sunset`,
  `shore_noon`, `river_noon`, `beach_noon`, `biome_ocean`, `biome_swamp`, `ocean_swamp`,
  `river_swamp`, `underwater`. The sun-glitter pair (ocean_sunset) is the one to show beside
  any change to the glitter or path terms; the confluence pair (ocean_swamp, river_swamp) shows
  what a real colour boundary in water looks like, which is a soft mixing front, never a line
  across the surface.
- **Clouds** (`clouds.md`): `sky_noon`, `plains_noon`, `golden_lit`, `dawn_wide`, `night_full`,
  `night_moon`.
- **Sky** (`sky.md`): `dawn_wide`, `shore_dusk` (the twilight gradient toward the sun and the
  Earth-shadow side away from it), `biome_hills`, `biome_hillsplus` (aerial perspective),
  `night_sky`, `night_new`, `night_full`, `night_moon`.
- **Light shafts** (`light-shafts.md`): `forest_golden`, `forest_lit`, `leafview`,
  `biome_roofed`, `underwater`.
- **Tone mapping**, **bloom**, **AO**: no photo stands in for a display transform or for
  restraint; `golden_lit` (amber faces against blue shade), `plains_noon` (grass that must not
  go lime) and the night sets are the frames to judge those on. `texture_wall` and `glass_close`
  have no reference by design.
- **Biome fog** (the owner's per-biome asks): `biome_desert`, `biome_savanna`, `biome_taiga`,
  `biome_roofed`, `biome_swamp`, `biome_hills`, `biome_hillsplus`.

## The licence rule, restated

Only files whose own Commons file page states CC0, public domain, CC BY or CC BY-SA are in this
set; the rule in `README.md` applies to every future addition too. CC BY and CC BY-SA references
need the credit line next to the image wherever it is shown (the Lab page, the round JSON, this
doc) and a link to the file page; CC BY-SA ones may be resized for the page but not otherwise
edited (no crops, no colour work, no compositing with our render): if a crop is wanted, show the
whole frame and point at the region in the question text. CC0 and public-domain files carry no
obligation, but we credit them the same way so the page reads consistently and the owner can
find the original. Nothing from this set goes into the pack itself: these are references for
judging renders, not textures or sky images to ship.

## Views and picks

Thumbnail links open a 330 px rendition on Commons; the file page is the `source` link.
"""

DOC_FOOTER = """
## Not covered

- `texture_wall`, `glass_close`: no photographic reference by design (tone-mapping and
  texture questions are judged on the owner's phone against the look bible).
- Known compromises, kept because nothing closer was openly licensed: `night_new` uses two
  moonless starfields whose land is near black (the view's land should stay readable, so judge
  the sky on them, not the ground); `lake_glitter` 2 and `ocean_swamp` 2 are drone and
  aerial views, higher than any Shader Lab camera; `shore_dusk` 1 has no water in frame;
  `leafview` 1 and `night_moon` 1 are portrait frames.

## How to extend the set

Everything goes through `tools/shaders/review/commons_refs.py` (run it with `py -3.10 -I`); it
carries the project User-Agent, spaces its requests (Commons answers 429 to quick ones), uses
only the standard thumbnail widths, strips the `?utm` query the API puts on rendition URLs, and
reads the licence from the file page's own licence template, never from a category or a grep.

1. Find candidates: `commons_refs.py search sun glitter lake` (two or three words; the search
   ANDs every word, so long queries find nothing) or `commons_refs.py search --cat
   "Category:Belt of Venus"`. Lines starting `OK` have an acceptable licence in the API
   metadata; `--` do not. Look at them before choosing: `commons_refs.py sheet out.jpg
   "File:A.jpg" "File:B.jpg" ...` makes a labelled contact sheet of 500 px thumbnails.
2. Check one: `commons_refs.py inspect "File:A.jpg"` prints the metadata, the licence the file
   page prints (`licence_on_file_page`) and whether the two agree. Only `match` goes in.
3. Add it: `commons_refs.py add <view> "File:A.jpg" --why "<one sentence on the match>"
   --sun <deg> [--notes ...] [--author "<name>"] [--rank 1]`. This re-checks the page, writes the
   record to `reference-frames.json`, downloads the 1920 px rendition (or the original when it
   is smaller) to `C:\\qfb\\shaderdev\\refs\\<view>-<n>.<ext>`, opens it with PIL and records the
   pixel size. `--author` trims an author field that Commons prints as a paragraph or with a
   Flickr "from <city>" suffix; the printed form is kept in `author_as_printed`.
4. Regenerate this page: `commons_refs.py doc`. Commit the JSON and the page together.

`commons_refs.py fetch [view ...]` re-downloads anything missing from the refs folder (a new
machine, a wiped folder) and `commons_refs.py check [view ...]` re-reads every file page and
updates `licence_on_file_page` and `checked`: do that before reusing a record older than a few
months, because Commons files get relicensed and deleted.
"""


def write_doc():
    data = load_set()
    order = view_names()
    vp = view_params()
    out = [DOC_HEADER]
    for v in order + [k for k in data if k not in order]:
        entries = data.get(v)
        if not entries:
            continue
        p = vp.get(v)
        head = f"### `{v}`"
        if p:
            head += f" (yaw {p[4]}, pitch {p[5]}, worldTime {p[6]})"
        out.append(head + "\n")
        out.append("| # | Photo | Credit | Why |")
        out.append("|---|---|---|---|")
        for i, e in enumerate(entries, 1):
            title = e["title"].replace("|", "\\|")
            why = e["why"].replace("|", "\\|")
            sun = e.get("sun_elevation_deg_estimate")
            sun_s = f" Sun ~{sun} deg." if isinstance(sun, (int, float)) else ""
            size = e.get("pixel_size") or ["?", "?"]
            out.append(f"| {i} | [{title}]({e['thumb_330']}) ([file page]({e['source']}), "
                       f"{size[0]}x{size[1]} local) | {e['credit']} | {why}{sun_s} |")
        out.append("")
    out.append(DOC_FOOTER)
    DOC_PATH.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print("wrote", DOC_PATH)


# ---------------------------------------------------------------- commands

def cmd_search(a):
    if a.cat:
        res = list_category(a.cat if a.cat.startswith("Category:") else "Category:" + a.cat, a.limit)
    else:
        words = " ".join(a.words)
        if not words:
            sys.exit("search: give two or three words, or --cat")
        if len([w for w in a.words if not w.startswith("incategory:")]) > 3:
            print("note: the search ANDs every word; more than three usually finds nothing", file=sys.stderr)
        res = search_files(words, a.limit)
    for e in res:
        if a.ok_only and not e["ok"]:
            continue
        print(fmt(e))
    print(f"{len(res)} results ({sum(e['ok'] for e in res)} with an acceptable licence)", file=sys.stderr)


def cmd_sheet(a):
    titles = [t if t.startswith("File:") else "File:" + t for t in a.titles]
    build_sheet(a.out, titles)


def cmd_inspect(a):
    title = a.title if a.title.startswith("File:") else "File:" + a.title
    meta = info([title]).get(title)
    if not meta:
        sys.exit(f"no imageinfo for {title}")
    shorts, url = file_page_licences(title)
    match = licence_matches(meta["licence"], shorts)
    print(json.dumps({**meta, "licence_on_file_page": shorts, "file_page": url,
                      "licence_check": "match" if (match and meta["ok"]) else "MISMATCH",
                      "download_1920": rendition_url(meta, FETCH_WIDTH),
                      "credit": credit_line(meta["artist"], meta["licence"])},
                     ensure_ascii=False, indent=1))
    if not meta["ok"]:
        print("REJECT: the API licence is not CC0 / public domain / CC BY / CC BY-SA", file=sys.stderr)
    elif not match:
        print("REJECT: the file page's licence template does not print that licence", file=sys.stderr)


def cmd_add(a):
    if a.view not in view_names():
        sys.exit(f"{a.view} is not a view in {VIEWS_PATH.name}")
    title = a.title if a.title.startswith("File:") else "File:" + a.title
    meta = info([title]).get(title)
    if not meta:
        sys.exit(f"no imageinfo for {title}")
    if not meta["ok"]:
        sys.exit(f"refused: API licence is {meta['licence']!r}")
    data = load_set()
    entries = data.setdefault(a.view, [])
    if any(e["file"] == title for e in entries):
        sys.exit(f"{title} is already in {a.view}")
    rank = a.rank if a.rank else len(entries) + 1
    rank = max(1, min(rank, len(entries) + 1))
    entry = make_entry(a.view, rank, meta, a.why, a.sun, a.notes, a.author)
    check_entry(entry)
    if entry["licence_check"] != "match":
        sys.exit(f"refused: file page prints {entry['licence_on_file_page']}, API says {meta['licence']!r}")
    entries.insert(rank - 1, entry)
    # renumber the view's local files (all inside REFS_DIR) to match the new order
    REFS_DIR.mkdir(parents=True, exist_ok=True)
    moves = []
    for i, e in enumerate(entries, 1):
        want = local_name(a.view, i, e["download"])
        have = str(REFS_DIR / Path(e["local_file"]).name)
        if have != want:
            moves.append((have, want))
        e["local_file"] = want
    tmp = []
    for src, dst in moves:
        if os.path.exists(src):
            t = src + ".moving"
            os.replace(src, t)
            tmp.append((t, dst))
    for t, dst in tmp:
        os.replace(t, dst)
    fetch_entry(entry)
    save_set(data)
    print(f"added {a.view}-{rank}: {title[5:]} | {entry['licence']} | page says {entry['licence_on_file_page']} "
          f"| {entry['pixel_size']} -> {entry['local_file']}")
    print("now run: commons_refs.py doc")


def _selected(data, views):
    for v, entries in data.items():
        if views and v not in views:
            continue
        for e in entries:
            yield v, e


def cmd_fetch(a):
    data = load_set()
    n = 0
    for v, e in _selected(data, a.views):
        before = e.get("pixel_size")
        fetch_entry(e, force=a.force)
        n += 1
        print(f"{Path(e['local_file']).name}: {e['pixel_size']}" + ("" if before == e["pixel_size"] else " (updated)"))
    save_set(data)
    print(f"{n} files present and readable")


def cmd_check(a):
    data = load_set()
    bad = 0
    for v, e in _selected(data, a.views):
        check_entry(e)
        bad += e["licence_check"] != "match"
        print(f"{v}: {e['file'][5:][:60]} | {e['licence']} | page says {e['licence_on_file_page']} -> {e['licence_check']}")
    save_set(data)
    print(f"{bad} mismatches" if bad else "all file pages still print the recorded licence")


def main():
    global JSON_PATH, REFS_DIR, DOC_PATH
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", help=f"the set to read and write (default {JSON_PATH})")
    ap.add_argument("--refs", help=f"folder for the downloaded images (default {REFS_DIR})")
    ap.add_argument("--doc-path", help=f"where `doc` writes (default {DOC_PATH})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="list candidate files with their API licence")
    s.add_argument("words", nargs="*")
    s.add_argument("--cat", help="list a category instead of searching")
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--ok-only", action="store_true", help="print only acceptable licences")
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("sheet", help="contact sheet of 500 px thumbnails")
    s.add_argument("out")
    s.add_argument("titles", nargs="+")
    s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("inspect", help="metadata, file-page licence and the check for one file")
    s.add_argument("title")
    s.set_defaults(fn=cmd_inspect)
    s = sub.add_parser("add", help="add a checked file to a view, fetch it, record it")
    s.add_argument("view")
    s.add_argument("title")
    s.add_argument("--why", required=True, help="one sentence on why it matches the view")
    s.add_argument("--sun", type=float, help="estimated sun elevation in degrees")
    s.add_argument("--notes", default="")
    s.add_argument("--author", help="override the printed author (trim paragraphs, Flickr suffixes)")
    s.add_argument("--rank", type=int, help="1 = primary; default appends")
    s.set_defaults(fn=cmd_add)
    s = sub.add_parser("fetch", help="download missing local files and verify them with PIL")
    s.add_argument("views", nargs="*")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("check", help="re-read every file page's licence template")
    s.add_argument("views", nargs="*")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("doc", help="regenerate reference-frames.md from the JSON")
    s.set_defaults(fn=write_doc)
    a = ap.parse_args()
    if a.json:
        JSON_PATH = Path(a.json)
    if a.refs:
        REFS_DIR = Path(a.refs)
    if a.doc_path:
        DOC_PATH = Path(a.doc_path)
    a.fn(a) if a.cmd != "doc" else write_doc()


if __name__ == "__main__":
    main()
