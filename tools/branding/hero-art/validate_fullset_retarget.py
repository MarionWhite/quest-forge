# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retune_hero_rewards as R
import retarget_fullset_rewards as T

SRC = R.SRC
BAK = os.path.join(
    os.path.dirname(SRC), "DefaultQuests.json.bak-fullset-retarget"
)
WORK = R.WORK


def stacks(q):
    return T.current_reward_stacks(q)


def main():
    with open(SRC, "rb") as f:
        head = f.read(4)
    print("bom", head.startswith(b"\xef\xbb\xbf"))
    with open(SRC, "r", encoding="utf-8") as f:
        cur = json.load(f, object_pairs_hook=OrderedDict)
    with open(BAK, "r", encoding="utf-8") as f:
        old = json.load(f, object_pairs_hook=OrderedDict)

    edit = cur["questSettings:10"]["betterquesting:10"].get("editMode:1")
    print("editMode", edit)

    recipes, skipped, lang = R.load_recipes()

    def qmap(data):
        return {q["questID:3"]: q for q in data["questDatabase:9"].values()}

    cm, om = qmap(cur), qmap(old)
    print("quest counts", len(cm), len(om))

    armor = []
    banned = []
    unique_in_full = []
    wrappers = []
    lang_bad = []
    piece_mismatch = []
    other_chapter_mismatch = []
    full_same_set_left = []

    for qid, q in cm.items():
        oq = om.get(qid)
        name = q.get("properties:10", {}).get("betterquesting:10", {}).get("name:8", "")
        kind, char = T.classify(q) if 300 <= qid <= 400 else (None, None)
        now = stacks(q)
        was = stacks(oq) if oq else None

        if qid < 300 or qid > 400:
            if was != now:
                other_chapter_mismatch.append((qid, name))
            continue

        for iid, c, d in now:
            if R.is_armor_id(iid):
                armor.append((qid, iid))
            if iid in R.BANNED_IDS or any(b in iid.lower() for b in R.BANNED_SUBSTR):
                banned.append((qid, iid))
            if iid.startswith("legends:") and not R.lang_item_ok(iid, lang):
                base = iid.split(":")[1]
                if base not in lang and ("item.%s.name" % base) not in lang and ("tile.%s.name" % base) not in lang:
                    lang_bad.append((qid, iid))

        rew = q.get("rewards:9") or {}
        for rv in rew.values():
            inner = (rv or {}).get("rewards:9") or {}
            for item in inner.values():
                extra = set(item.keys()) - {"id:8", "Count:3", "Damage:2", "OreDict:8"}
                if extra:
                    wrappers.append((qid, sorted(extra)))

        if kind != "full":
            if was != now:
                piece_mismatch.append((qid, name, was, now))
        else:
            src_ids = T.source_strip_ids(char, recipes, lang)
            leftover = [(i, c, d) for i, c, d in now if i in src_ids and i not in T.KEEP_EXTRA_IDS]
            # leftover same-set IDs are OK if they are also the donor's mats (shared family)
            donor = T.RETARGET.get(char)
            donor_ids = set()
            if donor and donor in recipes:
                for m in recipes[donor]["mats"]:
                    donor_ids.add(m["id"])
            true_left = [x for x in leftover if x[0] not in donor_ids]
            if true_left:
                full_same_set_left.append((qid, name, true_left))
            for i, c, d in now:
                if R.is_unique_key(i):
                    unique_in_full.append((qid, i, c, d))

    print("armor", armor)
    print("banned", banned)
    print("wrappers", wrappers)
    print("lang_bad", lang_bad)
    print("piece_mismatch", len(piece_mismatch), piece_mismatch[:3])
    print("other_chapter_mismatch", other_chapter_mismatch)
    print("full_same_set_only leftover", full_same_set_left[:8], "count", len(full_same_set_left))
    print("unique_in_full", unique_in_full)

    # sample piece still same-set
    for qid in (307, 313, 317, 302, 300, 301):
        q = cm[qid]
        kind, char = T.classify(q)
        print("SAMPLE", qid, q["properties:10"]["betterquesting:10"]["name:8"], kind, char, stacks(q)[:5])

    # extras on a few full sets
    for qid in (304, 314, 308, 386, 382):
        q = cm[qid]
        print("FULL", qid, stacks(q))


if __name__ == "__main__":
    main()
