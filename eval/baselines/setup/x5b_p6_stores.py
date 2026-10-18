#!/usr/bin/env python3
"""X5 byte pairs: the P6 cp.async program in every store that has it (read only).

  x5b_p6_stores.py [<program id>]

Per store and mode: the dot md5, the dump markers (hb_async, hb_exits, hb_gate), whether
hb_events is present, the census of non-memory records by (type, pc), the hb_races and
hb_races_sync_only entries, and for the first warp the records in trace order.
"""
import collections
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
pid = sys.argv[1] if len(sys.argv) > 1 else "P6-memcpy-shared_writewrite_race-racy"
for d in sorted(glob.glob(f"{ROOT}/*/{pid}")):
    store = d.split("/")[-2]
    dots = glob.glob(f"{d}/dots/*.dot")
    md5 = hashlib.md5(Path(dots[0]).read_bytes()).hexdigest()[:12] if dots else None
    for mode in ("vector-clock", "scalar-clock"):
        for kj in sorted(glob.glob(f"{d}/{mode}/kernel_*.json")):
            t = json.loads(Path(kj).read_text())
            ev = t.get("hb_events")
            marks = {k: t.get(k) for k in ("hb_async", "hb_exits", "hb_gate", "hb_aggregates")}
            print(f"== {store} {mode} {os.path.basename(kj)} dot={md5} {marks} "
                  f"events={'absent' if ev is None else len(ev)}")
            print("   races", [(hex(r["a_pc"]) if r.get("a_pc") is not None else None,
                              hex(r["b_pc"]), r.get("kind"), r.get("async"), r.get("count"))
                             for r in t.get("hb_races") or []])
            print("   sync_only", t.get("hb_races_sync_only"), "sync_pass", t.get("hb_sync_pass"))
            if ev:
                c = collections.Counter((e["type"], hex(e["pc"])) for e in ev
                                        if e["type"] not in ("read", "write", "atomic"))
                print("   census", dict(c))
                for e in sorted(ev, key=lambda e: e["seq"]):
                    if e.get("warp") == 0:
                        x = {k: e[k] for k in e if k != "lanes"}
                        if "lanes" in e:
                            x["lanes"] = [(ln["lane"], ln["addr"]) for ln in e["lanes"]][:3]
                        print("  ", x)
