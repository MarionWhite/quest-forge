#!/usr/bin/env python3
"""Drive a headless Forge server to pregenerate chunks, then shut it down.

HOW IT WORKS. A dedicated server reads console commands from stdin, so the whole
thing is: start the server with a pipe on stdin, wait for "Done (", write
`pregen gen startradius ...`, wait for Chunk Pregenerator to report the task
finished, write `stop`. No GUI, no player, no mods beyond the ones the pack
already ships.

WHY NOT TerrainOnly. Chunk Pregenerator will happily generate terrain without
running population, and it is much faster that way -- but ores are placed during
POPULATION, by WorldGenMinable, not during terrain generation. A TerrainOnly
world contains no ore at all. The generation type is deliberately left at the
default so the full population pass runs.

WHY THE CHUNKS ARE KEPT. The region files are the measurement. Keeping them
means a new question -- per biome, per depth, a different definition of "ore" --
is a re-scan of data already on disk rather than another multi-hour generation
run. See scan_regions.py.

Usage:
    pregen.py --server DIR --dim 0 --radius 100
    pregen.py --server DIR --dim 0 --dim -1 --dim 7 --radius 200
"""
import argparse, os, re, subprocess, sys, threading, time

DONE_BOOT = re.compile(r'Done \([\d.]+s\)')
DONE_TASK = re.compile(r'Pregenerated:\s+(\d+)\s+Chunks.*?(\d+)\s+Chunks Skipped,\s*(\d+)\s+Failed')
# Chunk Pregenerator prints progress lines; used only to show life, not parsed.
PROGRESS = re.compile(r'(Pregenerating|Task|Chunks)', re.I)


def find_java(explicit):
    """A Java 8 runtime. A dedicated server needs no LWJGL, so on Apple silicon
    a native arm64 JDK 8 works and avoids the Rosetta penalty entirely."""
    if explicit:
        return explicit
    for env in ("JAVA8_HOME", "JAVA_HOME"):
        home = os.environ.get(env)
        if home:
            cand = os.path.join(home, "bin", "java" + (".exe" if os.name == "nt" else ""))
            if os.path.exists(cand):
                return cand
    for cand in (
        "/Library/Java/JavaVirtualMachines/zulu-8.jdk/Contents/Home/bin/java",
        "/Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home/bin/java",
        r"C:\Program Files\Java\jre1.8.0_351\bin\java.exe",
        r"C:\Program Files\Zulu\zulu-8\bin\java.exe",
    ):
        if os.path.exists(cand):
            return cand
    return "java"


def forge_jar(server_dir):
    for fn in sorted(os.listdir(server_dir)):
        if fn.startswith("forge-1.7.10") and fn.endswith(".jar"):
            return fn
    sys.exit("no forge-1.7.10*.jar in %s -- run build_server.py first" % server_dir)


class Server(object):
    """A running dedicated server, driven over stdin."""

    def __init__(self, server_dir, java, xmx, log_path):
        self.dir = server_dir
        self.log = open(log_path, "w", encoding="utf-8", errors="replace")
        self.lines = []
        self.lock = threading.Lock()
        jar = forge_jar(server_dir)
        self.proc = subprocess.Popen(
            [java, "-Xmx%s" % xmx, "-Xms1G", "-XX:+UseG1GC", "-jar", jar, "nogui"],
            cwd=server_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True)
        self.reader = threading.Thread(target=self._pump, daemon=True)
        self.reader.start()

    def _pump(self):
        for line in self.proc.stdout:
            self.log.write(line)
            self.log.flush()
            with self.lock:
                self.lines.append(line)

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def wait_for(self, pattern, timeout, label, since=0):
        """Scan output for a regex. Returns the match, or None on timeout/death."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                print("  server exited unexpectedly while waiting for %s" % label)
                return None
            with self.lock:
                chunk = self.lines[since:]
            for line in chunk:
                m = pattern.search(line)
                if m:
                    return m
            time.sleep(2)
        print("  timed out after %ds waiting for %s" % (timeout, label))
        return None

    def stop(self):
        try:
            self.send("stop")
        except Exception:
            pass
        try:
            self.proc.wait(timeout=180)
        except Exception:
            self.proc.kill()
        self.log.close()


def region_count(server_dir, level):
    n = 0
    for dirpath, _, files in os.walk(os.path.join(server_dir, level)):
        n += sum(1 for f in files if f.endswith(".mca"))
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", required=True, help="assembled server directory")
    ap.add_argument("--dim", type=int, action="append", required=True,
                    help="dimension id to generate; repeatable")
    ap.add_argument("--radius", type=int, default=100,
                    help="chunk radius around 0,0 (100 => ~40,000 chunks)")
    ap.add_argument("--shape", default="square", choices=("square", "circle"))
    ap.add_argument("--java", help="path to a Java 8 runtime")
    ap.add_argument("--xmx", default="6G")
    ap.add_argument("--level", default="survey", help="world folder name")
    ap.add_argument("--boot-timeout", type=int, default=900)
    ap.add_argument("--task-timeout", type=int, default=36000)
    args = ap.parse_args()

    server = os.path.abspath(args.server)
    java = find_java(args.java)
    log_path = os.path.join(server, "pregen.log")
    print("server : %s" % server)
    print("java   : %s" % java)
    print("dims   : %s   radius %d (%s)" % (args.dim, args.radius, args.shape))
    print("log    : %s\n" % log_path)

    started = time.time()
    srv = Server(server, java, args.xmx, log_path)
    print("booting...")
    if not srv.wait_for(DONE_BOOT, args.boot_timeout, "server boot"):
        srv.stop()
        sys.exit("server did not boot; see %s" % log_path)
    print("booted in %.1fs\n" % (time.time() - started))

    total = 0
    for dim in args.dim:
        with srv.lock:
            mark = len(srv.lines)
        cmd = "pregen gen startradius %s 0 0 %d %d" % (args.shape, args.radius, dim)
        print("dim %-5d %s" % (dim, cmd))
        srv.send(cmd)
        t0 = time.time()
        m = srv.wait_for(DONE_TASK, args.task_timeout, "dim %d to finish" % dim, since=mark)
        if not m:
            print("  dim %d did not report completion; moving on" % dim)
            continue
        made, skipped, failed = (int(x) for x in m.groups())
        total += made
        print("  %d chunks, %d skipped, %d failed, %.1f min  (%.0f chunks/s)"
              % (made, skipped, failed, (time.time() - t0) / 60,
                 made / max(1.0, time.time() - t0)))

    print("\nstopping...")
    srv.stop()
    print("done. %d chunks generated in %.1f min, %d region files on disk."
          % (total, (time.time() - started) / 60, region_count(server, args.level)))
    print("scan them with:\n  python3 tools/survey/scan_regions.py %s -o scan.json"
          % os.path.join(server, args.level))


if __name__ == "__main__":
    main()
