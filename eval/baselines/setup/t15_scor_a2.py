#!/usr/bin/env python3
"""T15 step 3: per program and late-key variant (stores cuvein_traces/t15-<variant>, vector-clock
dumps of t15_scor.sh), the engine's hb_races instances by class and how many carry
a2_uncertain, the late-key marker, W0 (late_seq.check) and tv_violation. CPU, BeeGFS node."""
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import late_seq  # noqa: E402

ROOT = f"/mnt/beegfs/{os.environ.get('USER', 'fzheng4')}/cuvein_traces"
for v in ("off", "atomic", "timer"):
    for pdir in sorted(glob.glob(f"{ROOT}/t15-{v}/P4-*")):
        c = Counter()
        for kj in glob.glob(f"{pdir}/vector-clock/kernel_*.json"):
            t = json.load(open(kj))
            c["kernels"] += 1
            c["late_keyed"] += bool(t.get("hb_late_seq"))
            c["tv"] += bool(t.get("tv_violation"))
            for r in t.get("hb_races", ()):
                cls = r.get("class", "DR")
                c[f"{cls}_inst"] += r.get("count", 1)
                c[f"{cls}_flagged"] += r.get("a2_uncertain") or 0
            if t.get("hb_late_seq"):
                w = late_seq.check(t)
                c["w0_violations"] += w["w0_violations"]
                c["seq_order_bad"] += not w["seq_order_ok"]
        print(v, os.path.basename(pdir), dict(sorted(c.items())), flush=True)
