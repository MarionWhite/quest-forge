#!/usr/bin/env python3
"""Populate a painted (WorldPainter) world and pregenerate outskirts on a trial server.

Boots the server dir through tools/survey/pregen.py's stdin-driven Server, then runs one
Chunk Pregenerator task per argument, timing each, and stops cleanly.

    py -3.10 tools/world/pregen_island.py SERVER_DIR XMX TASK [TASK ...]
    TASK = RADIUS_IN_CHUNKS[:RULE], e.g. 112 (generate missing chunks)
           or 81:PostProcessingOnly (populate chunks that exist but are unpopulated)

WHY PostProcessingOnly. A plain `pregen gen` treats every chunk already in a region file as
done: on the 2560x2560 painted export it "finished" 25,600 chunks in 1 s and left all of
them unpopulated (TerrainPopulated=0), except the spawn area and the rim next to newly
generated outskirts. PostProcessingOnly loads them so the game populates them.

Check the heap budget first (`trial.py status`): this launches its own JVM, not via trial.py.
"""
import json, os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "survey"))
import pregen  # noqa: E402

JAVA = r"C:\Program Files\Java\jre1.8.0_241\bin\java.exe"


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    d, xmx, tasks = sys.argv[1], sys.argv[2], sys.argv[3:]
    srv = pregen.Server(d, JAVA, xmx, os.path.join(d, "pregen.log"))
    t0 = time.time()
    if not srv.wait_for(pregen.DONE_BOOT, 900, "boot"):
        srv.stop()
        sys.exit("server did not boot; see pregen.log")
    print(f"booted in {time.time() - t0:.0f} s", flush=True)
    srv.send("pregen stop")
    srv.send("pregen clear")
    mark = len(srv.lines)
    srv.send("pregen timepertick 250")
    srv.wait_for(pregen.DONE_TPT, 60, "timepertick", since=mark)
    res = []
    for task in tasks:
        rad, _, rule = task.partition(":")
        mark, t = len(srv.lines), time.time()
        srv.send(f"pregen gen startradius square 0 0 {rad} 0" + (f" {rule}" if rule else ""))
        m = srv.wait_for(pregen.DONE_TASK, 4 * 3600, task, since=mark)
        row = {"task": task, "seconds": round(time.time() - t, 1), "result": m.group(0) if m else None}
        res.append(row)
        print(row, flush=True)
    srv.send("save-all")
    time.sleep(10)
    srv.stop()
    with open(os.path.join(d, f"pregen-result-{int(time.time())}.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
