#!/usr/bin/env python3
"""Refresh everything the site generates from the pack, in one command. Windows PC.

    py -3.10 -I tools/items/refresh.py [--skip-dump] [--dump-dir DIR] [--dry-run]
                                       [--xmx 5G] [--timeout 600]

Steps, each printed before it runs. Any failure stops the run and says which step:

  a  preflight: repo root, git on PATH, a dirty tree (a warning: the index is then
     stamped "-dirty")
  b  build qf-content's debug jar (mods/qf-content, gradlew.bat build -PqfDebugTools=true),
     copy it to a temp dir, then rebuild without the flag so build/libs never holds a
     debug jar that `trial.py install` could pick up
  c  build the "itemdump" trial with every key in tools/trial/catalog.json "mods"
  d  put the debug jar in the trial's mods/ in place of the release jar: the old file is
     deleted first and refused if it has another hard link (writing through a link would
     overwrite the live pack's jar)
  e  launch the trial; the game writes items, icons and recipes to the dump folder, then quits
  f  build the item index from the dump (tools/items/build_site.py)
  g  rebuild the enchantment roster (tools/site/build_enchant_roster.py)
  h  rebuild the mod list from the live instance: read-mod-metadata, build-catalog, render-page
  i  check_fresh.py: the report that CI (site-fresh.yml) will apply
  j  git status, and a suggested commit message (nothing is committed)

--skip-dump starts at (f) against --dump-dir, an existing dump (for example after a build
failed on the mod list). --dry-run prints each step and command and runs none of them.

Untested on the Mac: written against tools/trial/trial.py and tools/items/README.md as of
2026-10-25. Every trial.py call here is one the README already documents, so a change to
trial.py's options shows up as that step failing, not as silent damage.
"""
import argparse, datetime, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))           # tools/items
REPO = os.path.dirname(os.path.dirname(HERE))
TRIAL_PY = os.path.join(REPO, 'tools', 'trial', 'trial.py')
TRIAL_CATALOG = os.path.join(REPO, 'tools', 'trial', 'catalog.json')
BUILD_SITE = os.path.join(HERE, 'build_site.py')
ROSTER = os.path.join(REPO, 'tools', 'site', 'build_enchant_roster.py')
CHECK = os.path.join(REPO, 'tools', 'site', 'check_fresh.py')
MODLIST = os.path.join(REPO, 'tools', 'modlist')
QFC = os.path.join(REPO, 'mods', 'qf-content')
JAR = 'QuestForgeContent-1.0.0.jar'
TRIAL = 'itemdump'

APPDATA = os.environ.get('APPDATA', os.path.expanduser('~/AppData/Roaming'))
LIVE = os.path.join(APPDATA, '.crazycraft4')
LIVE_MODS = os.path.join(LIVE, 'mods')
TRIALS = os.path.join(APPDATA, '.qf-trials')
TRIAL_DIR = os.path.join(TRIALS, TRIAL)
TRIAL_MODS = os.path.join(TRIAL_DIR, 'mods')


class Stop(Exception):
    """A refusal or a failed check: stop, say why, exit 1."""


class Refresh:
    def __init__(self, dry_run):
        self.dry = dry_run

    def step(self, letter, title):
        print('\n== (%s) %s' % (letter, title), flush=True)

    def skipped(self, letter, title):
        print('\n== (%s) %s: skipped' % (letter, title), flush=True)

    def say(self, msg):
        print('   ' + msg, flush=True)

    def run(self, cmd, cwd=REPO):
        where = '' if os.path.normcase(cwd) == os.path.normcase(REPO) else '   [in %s]' % cwd
        print('   $ ' + subprocess.list2cmdline(cmd) + where, flush=True)
        if not self.dry:
            subprocess.run(cmd, cwd=cwd, check=True)

    def git(self, *args):
        """Read-only git, run even in a dry run (it changes nothing)."""
        return subprocess.run(['git', '-C', REPO, *args], capture_output=True, text=True,
                              encoding='utf-8', errors='replace')


def trial_keys():
    with open(TRIAL_CATALOG, encoding='utf-8') as f:
        return list(json.load(f)['mods'].keys())


def preflight(r, args):
    r.step('a', 'preflight')
    if not (os.path.isfile(TRIAL_PY) and os.path.isfile(os.path.join(REPO, 'pack', 'mods.tsv'))):
        raise Stop('%s is not the Quest Forge repo root (tools/trial/trial.py or pack/mods.tsv missing)' % REPO)
    if shutil.which('git') is None:
        raise Stop('git is not on PATH; install Git for Windows or open a shell where `git` works')
    st = r.git('status', '--porcelain')
    if st.returncode != 0:
        raise Stop('git status failed: %s' % st.stderr.strip())
    n = len([l for l in st.stdout.splitlines() if l.strip()])
    if n:
        print('   warning: the tree has %d changed path(s); the item index will be stamped "-dirty" '
              'and check_fresh.py will list uncommitted pack changes.' % n)
    else:
        print('   the tree is clean')
    if not os.path.isdir(LIVE_MODS):
        msg = '%s is not there; the mod list (step h) reads the live instance' % LIVE_MODS
        if args.dry_run:
            print('   note: ' + msg)
        else:
            raise Stop(msg)
    print('   python %s' % sys.version.split()[0])


def build_debug_jar(r):
    """Returns the path of the debug jar (in a temp dir), leaving build/libs with the release jar."""
    r.step('b', 'build the debug jar, then the release jar again')
    gradlew = os.path.join(QFC, 'gradlew.bat')
    libs_jar = os.path.join(QFC, 'build', 'libs', JAR)
    tmp = '<temp dir>' if r.dry else tempfile.mkdtemp(prefix='qf-debugjar-')
    debug_jar = os.path.join(tmp, JAR)
    r.run([gradlew, 'build', '-PqfDebugTools=true'], cwd=QFC)
    r.say('copy %s -> %s' % (libs_jar, debug_jar))
    if not r.dry:
        if not os.path.isfile(libs_jar):
            raise Stop('the debug build left no %s' % libs_jar)
        shutil.copy2(libs_jar, debug_jar)
    try:
        r.run([gradlew, 'build'], cwd=QFC)
    except subprocess.CalledProcessError:
        # never leave a debug jar where trial.py install could pick it up
        if not r.dry and os.path.isfile(libs_jar):
            os.remove(libs_jar)
        raise
    return debug_jar


def build_trial(r):
    r.step('c', 'build the itemdump trial with every catalog mod')
    keys = trial_keys()
    r.run([sys.executable, TRIAL_PY, 'build', TRIAL, *keys, '--overlay', 'pack', '--shader', 'off', '--force'])


def swap_debug_jar(r, debug_jar):
    r.step('d', 'put the debug jar in the trial')
    dst = os.path.join(TRIAL_MODS, JAR)
    if os.path.normcase(os.path.abspath(dst)).startswith(os.path.normcase(os.path.abspath(LIVE))):
        raise Stop('refusing: %s is inside the live instance' % dst)
    if r.dry:
        r.say('delete %s if present (refused if it has another hard link), then copy the debug jar in' % dst)
        return
    if os.path.lexists(dst):
        links = os.stat(dst).st_nlink
        if links > 1:
            raise Stop('%s has %d hard links; refusing to overwrite it, since a write through a link '
                       'is a write to the live jar. Delete the trial (trial.py remove %s) and rerun.'
                       % (dst, links, TRIAL))
        os.remove(dst)
    os.makedirs(TRIAL_MODS, exist_ok=True)
    shutil.copy2(debug_jar, dst)
    r.say('copied the debug jar to %s' % dst)


def launch_dump(r, dump, xmx, timeout):
    r.step('e', 'launch the trial; the game writes the dump, then quits')
    if not r.dry and os.path.isdir(dump) and os.listdir(dump):
        raise Stop('%s is not empty; give --dump-dir a new folder so two dumps never mix' % dump)
    r.run([sys.executable, TRIAL_PY, 'launch', TRIAL, '--xmx', xmx, '--wait', '--timeout', str(timeout),
           '-D', 'qf.itemdump=%s' % dump, '-D', 'qf.itemdump.quit=1'])
    if not r.dry and not os.path.isfile(os.path.join(dump, 'items.json')):
        raise Stop('the game did not write %s' % os.path.join(dump, 'items.json'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skip-dump', action='store_true', help='start at step f, from --dump-dir')
    ap.add_argument('--dump-dir', metavar='DIR', help='the dump to build from (required with --skip-dump)')
    ap.add_argument('--dry-run', action='store_true', help='print every step and command; run none')
    ap.add_argument('--xmx', default='5G', help='heap for the dump client (default 5G)')
    ap.add_argument('--timeout', type=int, default=600, help='seconds to wait for the dump (default 600)')
    args = ap.parse_args()

    if args.skip_dump and not args.dump_dir:
        ap.error('--skip-dump needs --dump-dir (the dump to build from)')
    dump = args.dump_dir or os.path.join(
        TRIAL_DIR, 'dump-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    r = Refresh(args.dry_run)
    if args.dry_run:
        print('dry run: nothing below is executed')
    try:
        preflight(r, args)

        if args.skip_dump:
            for letter, title in (('b', 'build the debug jar'), ('c', 'build the itemdump trial'),
                                  ('d', 'put the debug jar in the trial'), ('e', 'launch the dump')):
                r.skipped(letter, title)
            print('   reading the dump in %s' % dump)
            if not args.dry_run and not os.path.isfile(os.path.join(dump, 'items.json')):
                raise Stop('no items.json in %s' % dump)
        else:
            debug_jar = build_debug_jar(r)
            build_trial(r)
            swap_debug_jar(r, debug_jar)
            launch_dump(r, dump, args.xmx, args.timeout)

        r.step('f', 'build the item index from the dump')
        r.run([sys.executable, '-I', BUILD_SITE, '--dump', dump])

        r.step('g', 'rebuild the enchantment roster')
        r.run([sys.executable, '-I', ROSTER])

        r.step('h', 'rebuild the mod list from the live instance')
        r.run([sys.executable, '-I', 'read-mod-metadata.py', '--mods', LIVE_MODS], cwd=MODLIST)
        r.run([sys.executable, '-I', 'build-catalog.py'], cwd=MODLIST)
        r.run([sys.executable, '-I', 'render-page.py'], cwd=MODLIST)

        r.step('i', 'check that everything is fresh now')
        r.run([sys.executable, '-I', CHECK])

        r.step('j', 'what changed, and a commit message (nothing is committed)')
        r.run(['git', '-C', REPO, 'status', '--short'])
        today = datetime.date.today().isoformat()
        print('\n   suggested commit message:')
        print('   Refresh the item index, mod list and enchantment roster (%s)' % today)
        print('\nDone. Review the diff, then commit site/items/data, site/mods and site/enchantments.')
    except Stop as e:
        print('\nSTOPPED: %s' % e, file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print('\nSTOPPED: a step failed (exit %d): %s' % (e.returncode, subprocess.list2cmdline(e.cmd)),
              file=sys.stderr)
        sys.exit(e.returncode or 1)


if __name__ == '__main__':
    main()
