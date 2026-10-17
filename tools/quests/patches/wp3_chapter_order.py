#!/usr/bin/env python3
"""WP-3 of docs/design/questline-audit.md: put the chapter order into the data.

Before this, quest 6 "Diamond Gear" opened Twilight, the End, OreSpawn, TragicMC and
ICBM at the same moment, and Witchery opened before Twilight, so the chapter numbers
were advice. This patch adds the cross-chapter prerequisites the audit proposes, hides
the later chapters until they open, and makes the chapter texts say what the data does.
Applied to both books (pack and server). Safe to re-run.

    py -3.10 -I tools/quests/patches/wp3_chapter_order.py [--book pack|server|all] [--dry-run]

The order it enforces (check it with `qb.py path`):
  Ch 1 Start -> Ch 3 Twilight (Diamond Gear) -> Ch 4 Witchery (the Naga)
  -> Ch 5 Dark Paths (the Circle Talisman) -> Ch 6 The End (the Hydra + the Talisman)
  -> Ch 7 OreSpawn (the Endstone Temple) -> Ch 8 TragicMC (Mobzilla).
  Ch 2 Base is a side tab. Ch 9 ProjectE is a ladder: each rung needs its boss and the
  rung before it.

Visibility (BQ 3.0.328, QuestCache.isQuestShown and GuiQuestLines):
  - a line set to UNLOCKED is not drawn until one of its quests is unlocked;
  - a quest set to NORMAL shows once it is unlocked, or once all its prerequisites are
    unlocked, so the next step is visible one step ahead but not the whole chapter.
  Ch 3-9 get both. Side tabs stay ALWAYS; only their end-game quests become NORMAL.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qb
from qb import set_prereqs, set_visibility, edit_text, move_in_line

# (quest, prerequisites before, prerequisites after, why)
PREREQS = [
    (9, [5], [15], 'Ch 4 Witchery opens after the Naga (its text: "after Twilight on purpose")'),
    (56, [6], [17, 105], 'Ch 6 The End: the Hydra and the Circle Talisman, the Act II finale (4.1)'),
    (20, [6], [114], 'Ch 7 OreSpawn opens at the Endstone Temple'),
    (74, [21], [20], 'Mantis follows First Contact now that Ultimate moved'),
    (21, [20], [79], 'Ultimate gear after the Kraken, not at step 2 (J2)'),
    (22, [79], [21], 'Mobzilla after Ultimate gear'),
    (58, [6], [22], 'Ch 8 TragicMC opens after the first titan'),
    (150, [6], [6, 126], 'ICBM waits for Railcraft steel as well (the Engineering line, 4.4)'),
    (12, [22], [22, 11], 'ProjectE ladder: the Table recipe needs the Stone'),
    (13, [23], [23, 12], 'ProjectE ladder: Dark Matter needs the Table rung'),
    (34, [24], [24, 13], 'ProjectE ladder: Red Matter is made from Dark Matter'),
    (401, [4], [6], 'Bestiary opens at Diamond Gear'),
    (405, [404], [404, 22], 'the Rahovart summon (and its Epic bag) waits for Mobzilla (J9)'),
]

SPINE_LINES = {3: 'Ch 3: Twilight', 2: 'Ch 4: Witchery', 8: 'Ch 5: Dark Paths', 14: 'Ch 6: The End',
               4: 'Ch 7: OreSpawn', 16: 'Ch 8: TragicMC', 6: 'Ch 9: ProjectE'}
# End-game quests on side tabs: they stay where they are, but are not shown until
# they are one step away.
SIDE_LATE = [62, 63, 405, 406]

TEXTS = [  # (line id, old, new)
    (2, 'Witchery sits after Twilight on purpose: you have a real kit now',
        'Witchery opens once the Naga is dead, on purpose: you have a real kit now'),
    (14, 'The End comes after the craft, before the OreSpawn gods.',
         'The End opens once the Hydra is dead and the Circle Talisman is made: after the craft, '
         'before the OreSpawn gods, who wait until you have found its temple.'),
    (4, 'This is late. Twilight, Witchery, and the End were the warm-up.',
        'This is late: it opens once you have found the Endstone Temple. Twilight, Witchery, and the End '
        'were the warm-up.'),
    (16, 'After the titans. Crystal to core',
         'After the first titan: this road opens when Mobzilla is dead. Crystal to core'),
]
QUEST_TEXTS = [  # (quest, old, new)
    (405, 'Do not wait for them.',
          'Do not wait for them. The book keeps this page shut until Mobzilla is dead; that is about the '
          'loadout Rahovart respects.'),
]


def apply(book):
    log = qb.Log(book)
    for qid, old, new, _why in PREREQS:
        set_prereqs(log, book.quest(qid), old, new)
    # OreSpawn layout: Ultimate now sits after the Kraken.
    move_in_line(log, book, 4, 21, 96, 96)

    for lid, lname in SPINE_LINES.items():
        line = book.line(lid)
        if qb.strip(book.line_name(lid)) != lname:
            raise SystemExit('line %d is %r, expected %r' % (lid, qb.strip(book.line_name(lid)), lname))
        set_visibility(log, line, 'UNLOCKED', 'line %d %s' % (lid, lname))
        for e in sorted(line['quests:9'].values(), key=lambda e: e['id:3']):
            q = book.quest(e['id:3'])
            if qb.props(q)['visibility:8'] == 'ALWAYS':
                set_visibility(log, q, 'NORMAL', 'q%d' % e['id:3'])
    for qid in SIDE_LATE:
        set_visibility(log, book.quest(qid), 'NORMAL', 'q%d' % qid)

    for lid, old, new in TEXTS:
        edit_text(log, book.line(lid), 'desc:8', old, new, 'line %d' % lid)
    for qid, old, new in QUEST_TEXTS:
        edit_text(log, book.quest(qid), 'desc:8', old, new, 'q%d' % qid)

    qb.set_pack_version(log, book, 7)
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', choices=['pack', 'server', 'all'], default='all')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for book in qb.books_for(a.book):
        print('==', book.label)
        apply(book)
        if not a.dry_run:
            book.save()


if __name__ == '__main__':
    main()
