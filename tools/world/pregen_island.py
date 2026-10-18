#!/usr/bin/env python3
"""Populate a painted (WorldPainter) world and pregenerate outskirts on a trial server.

Boots the server dir through tools/survey/pregen.py's stdin-driven Server, then runs one
Chunk Pregenerator task per argument, timing each, and stops cleanly.

    py -3.10 tools/world/pregen_island.py SERVER_DIR XMX TASK [TASK ...]
    TASK = [NAME=]RADIUS[:RULE][@X,Z]
           112                                generate missing chunks, 112-chunk radius around 0,0
           81:PostProcessingOnly              populate chunks that exist but are unpopulated
           sun=b1200:PostProcessingOnly@b0,b10000   block units ('b' prefix, passed through to
                                              Chunk Pregenerator), centred on block 0,10000

WHY PostProcessingOnly. A plain `pregen gen` treats every chunk already in a region file as
done: on the 2560x2560 painted export it "finished" 25,600 chunks in 1 s and left all of
them unpopulated (TerrainPopulated=0), except the spawn area and the rim next to newly
generated outskirts. PostProcessingOnly loads them so the game populates them.

While a task runs, `forge tps` is sent once a minute and the server JVM's working set is
sampled; both go into pregen-result-*.json with the task's time.

Check the heap budget first (`trial.py status`): this launches its own JVM, not via trial.py.
"""
import ctypes, json, os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "survey"))
import pregen  # noqa: E402

JAVA = r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe"
TPS = re.compile(r"Overall\s*:\s*Mean tick time:\s*([\d.]+)\s*ms\.\s*Mean TPS:\s*([\d.]+)")


def working_set_gb(proc):
    """Current working set of the server JVM (Windows only; None elsewhere)."""
    if os.name != "nt":
        return None

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + \
                   [(n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "a", "b", "c", "d",
                                                     "PagefileUsage", "PeakPagefileUsage")]
    c = PMC()
    c.cb = ctypes.sizeof(c)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(proc._handle)), ctypes.byref(c), c.cb)
    return round(c.WorkingSetSize / 2**30, 2) if ok else None


def parse_task(task):
    name, eq, rest = task.partition("=")
    if not eq:
        name, rest = task, task
    rest, _, centre = rest.partition("@")
    rad, _, rule = rest.partition(":")
    cx, cz = centre.split(",") if centre else ("0", "0")
    return name, f"pregen gen startradius square {cx} {cz} {rad} 0" + (f" {rule}" if rule else "")


def run_task(srv, name, cmd, timeout=4 * 3600):
    with srv.lock:
        mark = len(srv.lines)
    t = time.time()
    srv.send(cmd)
    tps, ws, nxt, m = [], [], t + 30, None
    while time.time() - t < timeout:
        if srv.proc.poll() is not None:
            print(f"  server died during {name}", flush=True)
            break
        with srv.lock:
            new = srv.lines[mark:]
        for line in new:
            if m is None:
                m = pregen.DONE_TASK.search(line)
            mt = TPS.search(line)
            if mt:
                tps.append((round(time.time() - t), float(mt.group(1)), float(mt.group(2))))
        mark += len(new)
        if m:
            break
        if time.time() >= nxt:
            srv.send("forge tps")
            ws.append((round(time.time() - t), working_set_gb(srv.proc)))
            nxt += 60
        time.sleep(2)
    dt = time.time() - t
    row = {"task": name, "command": cmd, "seconds": round(dt, 1), "result": m.group(0) if m else None}
    if m:
        made = int(m.group(1))
        row["chunks"] = made
        row["chunks_per_s"] = round(made / max(dt, 1), 1)
    if tps:
        row["mean_tick_ms"] = round(sum(x[1] for x in tps) / len(tps), 1)
        row["mean_tps"] = round(sum(x[2] for x in tps) / len(tps), 2)
        row["tps_samples"] = tps
    gbs = [x[1] for x in ws if x[1] is not None]
    if gbs:
        row["working_set_gb_max"] = max(gbs)
        row["working_set_samples"] = ws
    return row


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    d, xmx, tasks = sys.argv[1], sys.argv[2], sys.argv[3:]
    srv = pregen.Server(d, JAVA, xmx, os.path.join(d, "pregen.log"))
    t0 = time.time()
    if not srv.wait_for(pregen.DONE_BOOT, 1200, "boot"):
        srv.stop()
        sys.exit("server did not boot; see pregen.log")
    res = [{"task": "boot", "seconds": round(time.time() - t0, 1), "working_set_gb": working_set_gb(srv.proc)}]
    print(res[0], flush=True)
    srv.send("pregen stop")
    srv.send("pregen clear")
    mark = len(srv.lines)
    srv.send("pregen timepertick 250")
    srv.wait_for(pregen.DONE_TPT, 60, "timepertick", since=mark)
    out = os.path.join(d, f"pregen-result-{int(time.time())}.json")
    for task in tasks:
        name, cmd = parse_task(task)
        row = run_task(srv, name, cmd)
        res.append(row)
        print({k: v for k, v in row.items() if not k.endswith("_samples")}, flush=True)
        with open(out, "w") as f:
            json.dump(res, f, indent=1)
        if srv.proc.poll() is not None:
            break
    srv.send("save-all")
    time.sleep(15)
    srv.stop()
    print(f"results -> {out}", flush=True)


if __name__ == "__main__":
    main()
