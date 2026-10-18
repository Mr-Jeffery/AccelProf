#!/usr/bin/env python3
"""X5 byte pairs: every pc that carries a sync record, and the instruction there (read only).

  x5b_syncpcs.py <store> <program id> <mode> [<program id> <mode> ...]

For each launch of the kernels of the program in <store>: the census of non-memory records by
(type, pc) and the opcode the program's dot prints at that pc; then, per kernel, the
instructions whose opcode is NOP or starts with VOTE/SHFL/MATCH/REDUX/WARPSYNC/BAR/BSYNC/BSSY/
ELECT, with pcs. Shows which instructions the Sanitizer reports as syncwarps.
"""
import collections
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402,F401
from x5_common import sd                     # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
WATCH = ("NOP", "VOTE", "SHFL", "MATCH", "REDUX", "WARPSYNC", "BAR", "BSYNC", "BSSY", "ELECT",
         "VOTEU", "CREDUX")
store = sys.argv[1]
args = sys.argv[2:]
for pid, mode in zip(args[::2], args[1::2]):
    d = f"{ROOT}/{store}/{pid}"
    dots = glob.glob(f"{d}/dots/*.dot")
    kernels = {}
    for dot in dots:
        kernels.update(sd.parse_dot(dot))
    print(f"##### {store} {pid} {mode}")
    census = collections.defaultdict(collections.Counter)
    for kj in sorted(glob.glob(f"{d}/{mode}/kernel_*.json")):
        t = json.loads(Path(kj).read_text())
        try:
            m = sd.select_kernel(kernels, t["kernel"]["kernel_name"])
        except sd.AlignmentError:
            continue
        for e in t.get("hb_events") or ():
            if e["type"] not in ("read", "write", "atomic"):
                census[m][(e["type"], e["pc"], e.get("sync_mask", e.get("active_mask")))] += 1
    for m, c in census.items():
        op = {pc: o for ins in kernels[m][0].values() for pc, o in ins}
        print(f"== kernel {m}")
        for (ty, pc, mask), n in sorted(c.items(), key=lambda kv: kv[0][1]):
            print(f"   {ty:16s} pc {pc:#06x} mask {mask:#010x} records {n:7d}   dot: {op.get(pc)}")
        print("   watched instructions in the dot:",
              ", ".join(f"{pc:#x} {o}" for pc, o in sorted(op.items())
                        if o.split(".")[0] in WATCH))
