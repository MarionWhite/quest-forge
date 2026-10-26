"""Helpers a round's spec_scenes.py is exec'd with (finish_round.py), so a round needs no make_spec.py.

r005-r007 each had a hand-written make_spec.py: the same o()/oc()/cost()/crit() helpers plus a
hand-coded "which shaders-off run is this tag's baseline" table. These are those helpers once,
with the baseline found from the render itself: renderq writes rounds/bench/<tag>.meta.json
(preset, size, world, resource packs, mods), and cost() subtracts the p50 of the newest
shaders-off render with the same size, world, packs and mods that has the scene. A tag rendered
by the old bench_round.py has no meta file; name its baseline in round.json "base".

Names a spec_scenes.py may use: o, oc, og, ov, cost, crit, worst, ref, ref3, ref4, S, ROUNDS, D.
ov() is an option with a motion clip (a renderq burst made into an animated WebP).
"""
import glob, json, os, re

ROUNDS = r"C:\qfb\shaderdev\rounds"
SHADERDEV = r"C:\qfb\shaderdev"
S = os.path.join(ROUNDS, "screenshots", "bench-%s.png")
LINE = re.compile(r"(\w+)\s+frames\s+\d+\s+mean\s+[\d.]+\s+fps\s+p50\s+([\d.]+)")


class Round:
    def __init__(self, d, conf):
        self.d, self.conf = d, conf
        self.rounds = conf.get("rounds", ROUNDS)
        self.S = os.path.join(self.rounds, "screenshots", "bench-%s.png")
        self.base = conf.get("base", {})          # tag (or prefix*) -> baseline tag(s)
        self.crit_files = [os.path.join(d, c) for c in conf.get("critic", ["critic.json"])]
        self.critic = {}
        for c in self.crit_files:
            if os.path.exists(c):
                self.critic.update(json.load(open(c, encoding="utf-8")))
        self.missing_critic = []
        self.missing_cost = []
        self.used = []
        self.refs = {k: json.load(open(os.path.join(d, v), encoding="utf-8")) for k, v in conf.get("refs", {}).items()}
        self.ref_dirs = {k: os.path.dirname(os.path.normpath(os.path.join(d, v))) for k, v in conf.get("refs", {}).items()}
        self._p50 = {}

    # ---------------------------------------------------------------- costs
    def p50(self, tag):
        if tag not in self._p50:
            out = {}
            p = os.path.join(self.rounds, "bench", tag + ".txt")
            if os.path.exists(p):
                for l in open(p, encoding="utf-8", errors="replace"):
                    m = LINE.match(l)
                    if m:
                        out[m.group(1)] = float(m.group(2))
            self._p50[tag] = out
        return self._p50[tag]

    def meta(self, tag):
        p = os.path.join(self.rounds, "bench", tag + ".meta.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    def baseline(self, tag, scene):
        """The shaders-off tag whose p50 this tag's scene is measured against."""
        for k, v in self.base.items():
            if k == tag or (k.endswith("*") and tag.startswith(k[:-1])):
                for b in ([v] if isinstance(v, str) else v):
                    if scene in self.p50(b):
                        return b
                return None
        m = self.meta(tag)
        if not m:
            return None
        same = ("size", "world", "resourcepacks", "mods")
        best = None
        for p in glob.glob(os.path.join(self.rounds, "bench", "*.meta.json")):
            o = json.load(open(p, encoding="utf-8"))
            if o.get("preset") != "off" or any(o.get(k) != m.get(k) for k in same):
                continue
            if scene not in self.p50(o["tag"]):
                continue
            t = os.path.getmtime(os.path.join(self.rounds, "bench", o["tag"] + ".txt"))
            if not best or t > best[0]:
                best = (t, o["tag"])
        return best[1] if best else None

    def cost(self, tag, scene):
        b = self.baseline(tag, scene)
        d = self.p50(tag)
        if not b or scene not in d:
            self.missing_cost.append(f"{tag}/{scene}")
            return None
        return round(d[scene] - self.p50(b)[scene], 2)

    def worst(self, tag, scenes):
        v = [c for c in (self.cost(tag, s) for s in scenes) if c is not None]
        return max(v) if v else None

    # ---------------------------------------------------------------- critic
    def crit(self, tag, scene):
        c = self.critic.get(f"{tag}/{scene}")
        if not c:
            self.missing_critic.append({"key": f"{tag}/{scene}", "img": self.S % f"{tag}-{scene}"})
            return "?: (critic note missing)"
        return f"{c['score']}: {c['note']}"

    # ---------------------------------------------------------------- options
    def o(self, k, label, tag, scene, r=None, desc=None, clip=None):
        img = self.S % f"{tag}-{scene}"
        self.used.append(img)
        d = {"key": k, "label": label, "img": img, "critic": "Critic " + self.crit(tag, scene),
             "ms": self.cost(tag, scene)}
        if desc:
            d["desc"] = desc
        if r:
            d["ref"] = r
        if clip:
            d["clip"] = clip
        return d

    def ov(self, k, label, tag, scene, box=None, still=True, r=None, desc=None, clip_note=None, **clip_kw):
        """An option with a motion clip: tag's burst frames (bench-TAG-SCENE-f000.png ..., a renderq
        job with "burst") made into an animated WebP in <round>/clips/ by make_clip.py, shown first on
        the Lab, with the still (the full frame, or with box a crop the size of the burst's) one tap
        away. clip_kw goes to make_clip.make_clip (scale, max_mb, fps...)."""
        import make_clip
        out = os.path.join(self.d, "clips", f"{tag}-{scene}.webp")
        frames = make_clip.find_frames(self.rounds, tag, scene)
        if frames:
            self.used.extend(frames[:1])
            make_clip.make_clip(frames, out, times=make_clip.bench_times(self.rounds, tag, scene), quiet=True, **clip_kw)
        else:
            self.used.append(os.path.join(self.rounds, "screenshots", f"bench-{tag}-{scene}-f000.png"))
        d = self.oc(k, label, tag, scene, box, desc=desc) if box else self.o(k, label, tag, scene, r=r, desc=desc)
        if box and r:
            d["ref"] = r
        if not still:
            d["img"] = make_clip.poster_path(out)
        d["clip"] = out
        if clip_note:
            d["clipNote"] = clip_note
        return d

    def og(self, k, label, tag):
        """The block gallery's close shot (bench-<tag>-close.png)."""
        img = self.S % f"{tag}-close"
        self.used.append(img)
        return {"key": k, "label": label, "img": img, "critic": "Critic " + self.crit(tag, "gallery"),
                "ms": self.cost(tag, "gallery")}

    def oc(self, k, label, tag, scene, box, desc=None):
        """A 2x crop (box = x0, y0, w, h in the frame) for detail too small for the full frame."""
        from PIL import Image
        crops = os.path.join(self.d, "crops")
        os.makedirs(crops, exist_ok=True)
        out = os.path.join(crops, f"{tag}-{scene}-crop.png")
        src = self.S % f"{tag}-{scene}"
        if os.path.exists(src):
            im = Image.open(src).convert("RGB")
            x, y, w, h = box
            im.crop((x, y, x + w, y + h)).resize((w * 2, h * 2), Image.LANCZOS).save(out)
        d = self.o(k, label, tag, scene, desc=desc)
        d["img"] = out
        return d

    # ---------------------------------------------------------------- references
    def ref(self, table, key):
        """An openly licensed reference photo from a refs.json table named in round.json "refs"
        ({name: {"artist", "lic", "source", "title", "file"?}}); key may be a substring."""
        refs = self.refs[table]
        k, c = next((k, v) for k, v in refs.items() if key == k or key in k)
        img = os.path.join(self.ref_dirs[table], c.get("file") or k)
        return {"img": img, "credit": f"{c['artist']}, {c['lic']}, via Wikimedia Commons", "source": c["source"],
                "title": c["title"]}

    def ref3(self, name):
        """r003-style table: key = file name under the table's folder."""
        return self.ref("r003", name)

    def ref4(self, sub):
        """r004-style table: key 'folder/x', file refdl/<folder>/<title with _>."""
        refs = self.refs["r004"]
        k, c = next((k, v) for k, v in refs.items() if sub in k)
        img = os.path.join(self.ref_dirs["r004"], "refdl", k.split("/")[0], c["title"].replace(" ", "_"))
        return {"img": img, "credit": f"{c['artist']}, {c['lic']}, via Wikimedia Commons", "source": c["source"],
                "title": c["title"]}

    def namespace(self):
        return {"o": self.o, "oc": self.oc, "og": self.og, "ov": self.ov, "cost": self.cost, "crit": self.crit, "worst": self.worst,
                "ref": self.ref, "ref3": self.ref3, "ref4": self.ref4, "S": self.S, "ROUNDS": self.rounds,
                "D": self.d, "p50": self.p50, "os": os, "json": json}
