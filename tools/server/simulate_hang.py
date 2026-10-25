#!/usr/bin/env python3
"""Freeze a running server's main thread, to test the supervisor's hang detection.

    simulate_hang.py <java pid> [--jstack PATH] [--thread "Server thread"]

The server has no debug hook for a hang, and killing the JVM tests the crash
path, not the hang path. This script takes a `jstack` of the JVM, finds the OS
thread id (nid) of the thread named "Server thread" (the main tick thread) and
suspends only that thread with SuspendThread. Every other thread keeps running:
the console reader still accepts `list`, but the answer never comes, because
commands run on the frozen main thread. That is what a real hung tick looks
like from the outside. The JVM's attach listener also keeps running, so the
supervisor's own jstack-on-hang still produces a dump (with the frozen thread
in it). The supervisor then kills the JVM, so the thread is never resumed; pass
--resume to undo instead.

Windows only (the OpenThread/SuspendThread API). Dev tool: never run it against
the friends' server.
"""
import argparse, ctypes, glob, os, re, subprocess, sys

THREAD_SUSPEND_RESUME = 0x0002


def find_jstack():
    for pat in (r"C:\Program Files\Eclipse Adoptium\jdk-25*\bin\jstack.exe",
                r"C:\Program Files\Eclipse Adoptium\jdk-*\bin\jstack.exe",
                r"C:\Program Files\Java\jdk*\bin\jstack.exe"):
        hits = sorted(glob.glob(pat), reverse=True)
        if hits:
            return hits[0]
    return "jstack"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pid", type=int)
    ap.add_argument("--jstack", default=find_jstack())
    ap.add_argument("--thread", default="Server thread")
    ap.add_argument("--resume", action="store_true", help="resume the thread instead")
    args = ap.parse_args()
    if os.name != "nt":
        sys.exit("Windows only")
    dump = subprocess.run([args.jstack, str(args.pid)], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True, timeout=60).stdout
    # Java 8 prints nid=0x1a2b; Java 21+ prints it in decimal.
    m = re.search(r'^"%s".*?nid=(0x[0-9a-f]+|\d+)' % re.escape(args.thread), dump, re.M)
    if not m:
        print(dump[-2000:])
        sys.exit("no thread named %r in the jstack output" % args.thread)
    tid = int(m.group(1), 0)
    k32 = ctypes.windll.kernel32
    h = k32.OpenThread(THREAD_SUSPEND_RESUME, False, tid)
    if not h:
        sys.exit("OpenThread(%d) failed: error %d" % (tid, k32.GetLastError()))
    try:
        if args.resume:
            r = k32.ResumeThread(h)
            print("resumed %r (tid %d); previous suspend count %d" % (args.thread, tid, r))
        else:
            r = k32.SuspendThread(h)
            if r == 0xFFFFFFFF:
                sys.exit("SuspendThread failed: error %d" % k32.GetLastError())
            print("suspended %r (tid %d) of pid %d; previous suspend count %d. The supervisor "
                  "should report a hang within probe_interval_s + probe_timeout_s."
                  % (args.thread, tid, args.pid, r))
    finally:
        k32.CloseHandle(h)


if __name__ == "__main__":
    main()
