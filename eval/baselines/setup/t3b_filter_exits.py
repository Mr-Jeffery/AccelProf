#!/usr/bin/env python3
"""T3b: copy a collector dump directory with the exit records and the `hb_exits` marker
removed from every kernel_*.json, so a T3b dump can be compared with a pre-T3b one by
dump_compare.py (everything else must match up to device addresses).
  t3b_filter_exits.py <src dir> <dst dir>   -> prints '<n> exit records removed'"""
import glob
import json
import os
import shutil
import sys

src, dst = sys.argv[1], sys.argv[2]
shutil.rmtree(dst, ignore_errors=True)
shutil.copytree(src, dst)
n = 0
for f in glob.glob(os.path.join(dst, "kernel_*.json")):
    j = json.load(open(f))
    if "hb_events" in j:
        ev = j["hb_events"]
        j["hb_events"] = [e for e in ev if e.get("type") != "exit"]
        n += len(ev) - len(j["hb_events"])
        # seq stays: the pre-T3b collector numbered a BlockExit record too and then dropped
        # it, so its dumps have a gap at every exit position already
    j.pop("hb_exits", None)
    json.dump(j, open(f, "w"))
print(f"{n} exit records removed")
