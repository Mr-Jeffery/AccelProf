#!/usr/bin/env python3
"""T22 cont.: totals of t4_parity.py --counts-le results -- kernels by status, and the summed hb_sync_pass
counts (aggregates, records) over the compared scalar-clock kernels, with the kernels where they differ.
  t22c_parity_sum.py <result json>...
"""
import json
import sys

st, agg, rec, lower = {}, 0, 0, []
for f in sys.argv[1:]:
    for prog in json.load(open(f)):
        for mode, m in prog["modes"].items():
            for k in m["kernels"]:
                s = k.get("status", "?")
                st[s] = st.get(s, 0) + 1
                c = k.get("counts")
                if c:
                    agg += c[0]
                    rec += c[1]
                    if c[0] < c[1]:
                        lower.append((prog["id"], k["kernel"], c[0], c[1]))
print("status:", st)
print(f"summed counts over compared kernels: aggregates {agg:,} records {rec:,}")
print(f"kernels with aggregate < records: {len(lower)}")
for x in sorted(lower, key=lambda x: -x[3])[:15]:
    print("  ", x)
