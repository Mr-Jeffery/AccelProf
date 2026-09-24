#!/usr/bin/env python3
"""T3: how far does the exited-thread barrier bug reach? Every vector-clock kernel dump in
the kept BeeGFS stores whose engine recorded a trace-validity violation (the `tv_violation`
field HbEngine writes at the end of kernel_N.json) -> one row per (store, program) with the
violation kinds and kernel counts. Reads only each file's last 64 KiB.
  t3_tv_scan.py [store ...] > eval/baselines/setup/t3_crs/tv_scan.tsv"""
import collections
import glob
import os
import re
import sys

ROOT = "/mnt/beegfs/" + os.environ["USER"] + "/cuvein_traces"
TAIL = 1 << 16
stores = sys.argv[1:] or sorted(os.path.basename(p) for p in glob.glob(f"{ROOT}/*"))
rx = re.compile(r'"tv_violation": "((TV-[a-z-]+)[^"]*)"')
print("store\tid\tkernel_dumps\tkernels_with_tv\tkinds\tfirst")
for st in stores:
    for idir in sorted(glob.glob(f"{ROOT}/{st}/*/")):
        kjs = glob.glob(f"{idir}vector-clock/kernel_*.json")
        if not kjs:
            continue
        kinds, first, n = collections.Counter(), "", 0
        for kj in kjs:
            with open(kj, "rb") as f:
                f.seek(max(0, os.path.getsize(kj) - TAIL))
                m = rx.search(f.read().decode("utf-8", "replace"))
            if m:
                n += 1
                kinds[m.group(2)] += 1
                first = first or m.group(1)[:120]
        if n:
            print(f"{st}\t{os.path.basename(idir.rstrip('/'))}\t{len(kjs)}\t{n}\t"
                  f"{';'.join(f'{k}={v}' for k, v in sorted(kinds.items()))}\t{first}", flush=True)
