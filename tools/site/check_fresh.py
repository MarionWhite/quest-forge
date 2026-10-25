#!/usr/bin/env python3
"""Report which generated site data lags the pack, and why.

    py -3.10 -I tools/site/check_fresh.py              text: one line per area, reasons under it
    py -3.10 -I tools/site/check_fresh.py --json       the same as JSON on stdout
    py -3.10 -I tools/site/check_fresh.py --out F.json the same as JSON, written to F.json
    py -3.10 -I tools/site/check_fresh.py --strict     exit 1 when anything is stale

Three areas are checked:

  items        site/items/data/ against the pack's sources. The build date is items.json's
               "built"; once build_site.py records it, "source" names the commit it was built
               from (git short hash, "-dirty" when the tree had changes). The baseline is that
               commit, else the last commit on or before "built". Reasons: jars added, removed
               or re-versioned in pack/mods.tsv since the baseline; a jar in the index that
               mods.tsv no longer lists; commits since the baseline to the paths that define
               items (pack/scripts, the quest book, and in qf-content / qf-commands the Item*,
               Block*, Mod* classes, the enchantments and the assets); uncommitted changes there.
               The index's own version strings are NOT compared with mods.tsv: they come from
               the jars' @Mod annotations and mods.tsv from mcmod.info, and the two disagree
               for a dozen mods that are the same jar.
  mods         tools/modlist/catalog.json against pack/mods.tsv (by jar name, and version), and
               site/mods/index.html against the newest of catalog.json and render-page.py.
  enchantments the keys in the page's `const ENCH` line against the add(cfg, "key", ...) calls
               in QFEnchantments.java.
  lucky        site/lucky/data/lucky.json (the Lucky Block page's table, built by
               tools/site/build_lucky.py) committed no earlier than the pack's
               pack/config/lucky/LuckyBlockProperties.txt and the builder itself.

A check that cannot run (no git history, a file missing) reports an "unknown:" reason, and
that area counts as stale: the point of this script is that a gap is never silent.

Nothing here rebuilds anything. The fix is printed as a hint; see tools/items/README.md.
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, 'site', 'items', 'data')
ENCH_PAGE = os.path.join(REPO, 'site', 'enchantments', 'index.html')
ENCH_SRC = os.path.join(REPO, 'mods', 'qf-content', 'src', 'main', 'java', 'com', 'questforge',
                        'content', 'ench', 'QFEnchantments.java')
LUCKY_SRC = 'pack/config/lucky/LuckyBlockProperties.txt'
LUCKY_BUILD = 'tools/site/build_lucky.py'
LUCKY_DATA = 'site/lucky/data/lucky.json'
CATALOG = 'tools/modlist/catalog.json'
RENDER = 'tools/modlist/render-page.py'
MODS_PAGE = 'site/mods/index.html'
MODS_TSV = 'pack/mods.tsv'
# What a commit must touch to make the item index stale: (label, git glob pathspecs). Only the
# classes that register items, blocks and recipes, the enchantments, and the assets (lang,
# textures) count; a FrameBench or census commit in the same mod does not change an item.
# Keep these in step with the `paths:` lists in .github/workflows/pages.yml and site-fresh.yml.
PACK_PATHS = [
    ('pack/scripts', ['pack/scripts/**']),
    ('the quest book', ['pack/config/betterquesting/DefaultQuests.json']),
    ('qf-content items, blocks, recipes, enchantments or assets', [
        'mods/qf-content/src/main/java/**/Item*.java',
        'mods/qf-content/src/main/java/**/Block*.java',
        'mods/qf-content/src/main/java/**/Mod*.java',
        'mods/qf-content/src/main/java/**/ench/**',
        'mods/qf-content/src/main/resources/assets/**']),
    ('qf-commands tickets or assets', [
        'mods/qf-commands/src/main/java/**/Item*.java',
        'mods/qf-commands/src/main/java/**/Unlockables.java',
        'mods/qf-commands/src/main/resources/assets/**']),
]
PATHSPECS = [':(glob)' + g for _, globs in PACK_PATHS for g in globs]
MAX_LOG_REASONS = 5
HINT = 'On the Windows PC, from the repo root, run: py -3.10 -I tools/items/refresh.py'


class Git:
    """Read-only git queries. run() returns stdout, or None when git or the history is missing."""

    def __init__(self):
        self.ok = shutil.which('git') is not None

    def run(self, *args):
        if not self.ok:
            return None
        try:
            p = subprocess.run(['git', '-C', REPO, *args], capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
        except OSError:
            return None
        return p.stdout if p.returncode == 0 else None


def basename(path):
    return (path or '').replace('\\', '/').rsplit('/', 1)[-1]


def read_tsv(text):
    """pack/mods.tsv -> {lower-case jar name: (jar name, version)}. Subfolders ("1.7.10/x.jar") are dropped."""
    rows = {}
    for line in text.splitlines()[1:]:
        cols = line.split('\t')
        if len(cols) >= 3 and basename(cols[0]):
            jar = basename(cols[0])
            rows[jar.lower()] = (jar, cols[2].strip())
    return rows


def is_pack_built(jar):
    """The pack's own jars. refresh.py builds them from repo source for the dump, so their
    version and presence come from the repo, not from what the pack ships; their changes are
    caught by the source-path commits in check_items instead."""
    return jar.lower().startswith(('questforge', 'qfcommands'))


def version_match(item_ver, tsv_ver):
    """Do two version strings name the same version? The item index takes the version from the
    jar's own @Mod annotation and mods.tsv from its file name or mcmod.info, so the formats differ
    ("1.7.10-0.8b" vs "1.0.8", "1.7.10.20.3" vs "1.7.10-20.2"). Compare the numeric parts."""
    a = re.findall(r'\d+(?:\.\d+)+', item_ver or '')
    b = re.findall(r'\d+(?:\.\d+)+', tsv_ver or '')
    if not a or not b:
        return True  # nothing numeric to compare (blank, "RC9", "beta"): no evidence either way
    def same(x, y):
        return x == y or x.startswith(y + '.') or y.startswith(x + '.')
    return any(same(x, y) for x in a for y in b)


def read_text(rel):
    with open(os.path.join(REPO, rel), encoding='utf-8') as f:
        return f.read()


def read_items():
    with open(os.path.join(DATA, 'items.json'), encoding='utf-8') as f:
        return json.load(f)


def glob_re(g):
    """A git-style glob to a regex: ** crosses directories, * stays inside one."""
    out = ''
    i = 0
    while i < len(g):
        if g.startswith('**/', i):
            out += '(?:.*/)?'; i += 3
        elif g.startswith('**', i):
            out += '.*'; i += 2
        elif g[i] == '*':
            out += '[^/]*'; i += 1
        else:
            out += re.escape(g[i]); i += 1
    return re.compile('^' + out + '$')


GROUP_RES = [(label, [glob_re(g) for g in globs]) for label, globs in PACK_PATHS]


def groups_of(path):
    """The PACK_PATHS labels a repo-relative path falls under."""
    path = path.replace('\\', '/')
    return [label for label, res in GROUP_RES if any(r.match(path) for r in res)]


def collapse(reasons, limit=MAX_LOG_REASONS):
    if len(reasons) <= limit:
        return reasons
    return reasons[:limit] + ['and %d more' % (len(reasons) - limit)]


def baseline(git, source, built):
    """The commit the item index was built from, or None when it cannot be told."""
    if source:
        rev = source[:-len('-dirty')] if source.endswith('-dirty') else source
        sha = git.run('rev-parse', '--verify', '--quiet', rev + '^{commit}')
        if sha and sha.strip():
            return sha.strip()
    if built:
        sha = git.run('rev-list', '-1', '--before=%sT23:59:59' % built, 'HEAD')
        if sha and sha.strip():
            return sha.strip()
    return None


def check_items(git):
    items = read_items()
    built, source = items.get('built'), items.get('source')
    reasons = []
    base = baseline(git, source, built)
    if base is None:
        reasons.append('unknown: cannot tell which commit the item index was built from '
                       '(built=%s, source=%s, git history %s)'
                       % (built, source, 'available' if git.ok else 'not available'))
    short = base[:7] if base else None

    # (i) the jar set and versions the pack shipped at the baseline, against now
    cur = read_tsv(read_text(MODS_TSV))
    if base:
        old_text = git.run('show', '%s:%s' % (base, MODS_TSV))
        if old_text is None:
            reasons.append('unknown: %s is not readable at %s' % (MODS_TSV, short))
        else:
            old = read_tsv(old_text)
            for k in sorted(cur.keys() - old.keys()):
                reasons.append('%s: %s was added since %s' % (MODS_TSV, cur[k][0], short))
            for k in sorted(old.keys() - cur.keys()):
                reasons.append('%s: %s was removed since %s' % (MODS_TSV, old[k][0], short))
            for k in sorted(old.keys() & cur.keys()):
                if old[k][1] != cur[k][1]:
                    reasons.append('%s: %s version %s -> %s since %s'
                                   % (MODS_TSV, cur[k][0], old[k][1] or '(none)', cur[k][1] or '(none)', short))

    # (i) a jar the index was built from that the pack no longer lists (by name only: the
    # index's version strings come from @Mod annotations and are not comparable with mods.tsv)
    for m in items.get('mods', []):
        jar = basename(m.get('file'))
        if not jar or is_pack_built(jar):
            continue
        if jar.lower() not in cur:
            reasons.append('%s (%s) is in the item index but not in %s' % (m.get('id'), jar, MODS_TSV))

    # (ii) commits to the item-defining sources since the baseline
    if base:
        log = git.run('log', '--format=@@%h%x09%ad%x09%s', '--date=short', '--name-only',
                      '%s..HEAD' % base, '--', *PATHSPECS)
        if log is None:
            reasons.append('unknown: git log failed for the pack sources since %s' % short)
        else:
            commits = []
            for line in log.splitlines():
                if line.startswith('@@'):
                    h, d, s = (line[2:].split('\t', 2) + ['', ''])[:3]
                    commits.append((h, d, s, []))
                elif line.strip() and commits:
                    for g in groups_of(line.strip()):
                        if g not in commits[-1][3]:
                            commits[-1][3].append(g)
            hits = []
            for h, d, s, groups in commits:
                for g in groups:
                    hits.append('%s changed on %s (%s %s)' % (g, d, h, s))
            reasons.extend(collapse(hits))

    # (ii) uncommitted changes to those paths
    if git.ok:
        st = git.run('status', '--porcelain', '--untracked-files=all', '--', *PATHSPECS)
        if st is not None:
            dirty = []
            for line in st.splitlines():
                p = line[3:].split(' -> ')[-1].strip().strip('"')
                for g in groups_of(p):
                    if g not in dirty:
                        dirty.append(g)
            for g in dirty:
                reasons.append('%s: uncommitted changes' % g)
    return list(dict.fromkeys(reasons))  # Lycanites' sub-mods share one jar: say it once


def check_mods(git):
    reasons = []
    with open(os.path.join(REPO, CATALOG), encoding='utf-8') as f:
        catalog = json.load(f)
    cat = {}
    for m in catalog['mods']:
        cat[basename(m.get('file')).lower()] = (basename(m.get('file')), (m.get('ver') or '').strip())
    tsv = read_tsv(read_text(MODS_TSV))
    for k in sorted(cat.keys() - tsv.keys()):
        reasons.append('%s is in %s but not in %s' % (cat[k][0], CATALOG, MODS_TSV))
    for k in sorted(tsv.keys() - cat.keys()):
        reasons.append('%s is in %s but not in %s' % (tsv[k][0], MODS_TSV, CATALOG))
    for k in sorted(cat.keys() & tsv.keys()):
        if not version_match(cat[k][1], tsv[k][1]):
            reasons.append('%s: %s says %s, %s says %s'
                           % (cat[k][0], CATALOG, cat[k][1] or '(none)', MODS_TSV, tsv[k][1] or '(none)'))

    # the page is generated from the catalog by render-page.py: it must be committed after both
    if not git.ok:
        reasons.append('unknown: git history not available; cannot compare %s with %s and %s'
                       % (MODS_PAGE, CATALOG, RENDER))
        return reasons
    times = {}
    for p in (MODS_PAGE, CATALOG, RENDER):
        out = (git.run('log', '-1', '--format=%ct', '--', p) or '').strip()
        times[p] = int(out) if out.isdigit() else None
    if times[MODS_PAGE] is None:
        reasons.append('unknown: %s has no commit in git history' % MODS_PAGE)
    else:
        for p in (CATALOG, RENDER):
            if times[p] is None:
                reasons.append('unknown: %s has no commit in git history' % p)
            elif times[p] > times[MODS_PAGE]:
                reasons.append('%s (committed %s) is older than %s (committed %s)'
                               % (MODS_PAGE, _day(times[MODS_PAGE]), p, _day(times[p])))
    return reasons


def _day(ts):
    return datetime.date.fromtimestamp(ts).isoformat()


def check_enchantments():
    page = read_text(os.path.relpath(ENCH_PAGE, REPO))
    with open(ENCH_SRC, encoding='utf-8') as f:
        java = f.read()
    m = re.search(r'^const ENCH = (.*);\r?$', page, re.M)
    if not m:
        return ['unknown: no "const ENCH = ..." line in site/enchantments/index.html']
    roster = json.loads(m.group(1))
    page_keys = {e['key'] for e in roster}
    src_keys = set(re.findall(r'add\(cfg,\s*"([^"]+)"', java))
    reasons = []
    if not src_keys:
        reasons.append('unknown: no add(cfg, "key", ...) calls found in QFEnchantments.java')
    missing = sorted(src_keys - page_keys)
    extra = sorted(page_keys - src_keys)
    if missing:
        reasons.append('in QFEnchantments.java but not in the roster: ' + ', '.join(missing))
    if extra:
        reasons.append('in the roster but not in QFEnchantments.java: ' + ', '.join(extra))
    return reasons


def when(git, rel):
    """When a repo file last changed: its last commit time, or its mtime when it is uncommitted
    (so a file just regenerated and not yet committed counts as current). None when absent."""
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        return None
    if git.ok:
        st = git.run('status', '--porcelain', '--', rel)
        if st is not None and st.strip():
            return int(os.path.getmtime(p))
        out = (git.run('log', '-1', '--format=%ct', '--', rel) or '').strip()
        if out.isdigit():
            return int(out)
    return int(os.path.getmtime(p))


def check_lucky(git):
    """The Lucky Block page's table must be rebuilt after the pack's drop table or the builder changes."""
    data = when(git, LUCKY_DATA)
    if data is None:
        return ['unknown: %s is missing; run python3 -I %s' % (LUCKY_DATA, LUCKY_BUILD)]
    reasons = []
    for src in (LUCKY_SRC, LUCKY_BUILD):
        t = when(git, src)
        if t is None:
            reasons.append('unknown: %s is missing' % src)
        elif t > data:
            reasons.append('%s (%s) is newer than %s (%s); run python3 -I %s'
                           % (src, _day(t), LUCKY_DATA, _day(data), LUCKY_BUILD))
    return reasons


def guard(name, fn):
    try:
        return fn()
    except Exception as e:  # a broken check reports itself; it must not hide the others
        return ['unknown: the %s check could not run (%s: %s)' % (name, type(e).__name__, e)]


def items_meta():
    try:
        items = read_items()
        return items.get('built'), items.get('source')
    except (OSError, ValueError):
        return None, None


def build_result():
    git = Git()
    built, source = items_meta()
    checks = {
        'items': guard('item index', lambda: check_items(git)),
        'mods': guard('mod list', lambda: check_mods(git)),
        'enchantments': guard('enchantment roster', check_enchantments),
        'lucky': guard('Lucky Block table', lambda: check_lucky(git)),
    }
    result = {'checked': datetime.date.today().isoformat(), 'built': built, 'source': source,
              'stale': any(checks[k] for k in checks)}
    for k in AREAS:
        result[k] = {'stale': bool(checks[k]), 'reasons': checks[k]}
    return result


AREAS = ('items', 'mods', 'enchantments', 'lucky')


def text_report(r):
    lines = ['checked %s; item index built %s, source %s'
             % (r['checked'], r['built'] or 'unknown', r['source'] or 'unknown')]
    for k in AREAS:
        lines.append('%s: %s' % (k, 'STALE' if r[k]['stale'] else 'fresh'))
        lines.extend('  - ' + reason for reason in r[k]['reasons'])
    lines.append('Everything is fresh.' if not r['stale'] else
                 'Stale: %s. %s.' % (', '.join(k for k in AREAS if r[k]['stale']), HINT))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', action='store_true', help='print the result as JSON')
    ap.add_argument('--out', metavar='PATH', help='write the result as JSON to PATH (and print the text report)')
    ap.add_argument('--strict', action='store_true', help='exit 1 when anything is stale')
    a = ap.parse_args()

    r = build_result()
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(text_report(r))
    elif a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(text_report(r))
    sys.exit(1 if (a.strict and r['stale']) else 0)


if __name__ == '__main__':
    main()
