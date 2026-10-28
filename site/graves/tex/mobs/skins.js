// The Krypt's mob skins, in order of preference:
//   1. tex/mobs-local/ (index.json): a local-only layer on the owner's machine, written by
//      tools/textures/mobs/import_patrix.py. Git-ignored, never committed or deployed; looked for only when the page
//      is served locally, and a missing index just means there is none.
//   2. tex/mobs/: our own horror skins, painted by tools/textures/mobs/paint_mobs.py (original art). Paused pilots,
//      so visitors do not see them yet (OWN_LIVE); ?ownskins previews them.
//   3. vanilla, which is all the other pages ever show.
// Loaded by graves/index.html before app.js, so the scares', mood's and dressing's mobs all wear them.
// ?vanillaskins turns every override off (side-by-side review). ?dump=1&skinreview=<Mob> renders one (review.js).
import { setSkinOverrides } from "../../../lib/mc/mobs.js";

const QS = new URLSearchParams(location.search);
const OWN_LIVE = false;
const own = (f) => new URL("./" + f, import.meta.url).href;
const OWN = { Zombie: [own("zombie.png")], Spider: [own("spider.png"), own("spider_eyes.png")] };
const LOCAL = location.protocol === "file:" ||
  /^(localhost|\[::1\]|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|[^.]+|.+\.local)$/.test(location.hostname);

async function localLayer() {
  const base = new URL("../mobs-local/", import.meta.url);
  try {
    const r = await fetch(new URL("index.json", base), { cache: "no-store" });
    if (!r.ok) return null;
    const j = await r.json(), map = {};
    for (const [k, v] of Object.entries(j.mobs || {})) {
      map[k] = { layers: (v.layers || []).map((f) => (f ? new URL(f, base).href : null)), glow: v.glow ? new URL(v.glow, base).href : null };
    }
    return map;
  } catch (e) { return null; }
}

if (!QS.has("vanillaskins")) {
  if (OWN_LIVE || QS.has("ownskins")) setSkinOverrides(OWN);
  const map = LOCAL && !QS.has("ownskins") ? await localLayer() : null;
  if (map) setSkinOverrides(map);
}
if (QS.has("skinreview") && QS.has("dump")) import("./review.js").then((m) => m.review()).catch((e) => console.error("skinreview", e));
