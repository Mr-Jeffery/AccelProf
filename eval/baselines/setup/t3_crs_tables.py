#!/usr/bin/env python3
"""T3: summarize eval/baselines/setup/t3_crs/triage.json for eval/CRS_CUDA_TRIAGE.md --
per mode: reports by kernel with the kernel's barrier diagnostics and tv_violation, the
w (group width) of each gcrs kernel, pc pairs with source lines, hb_class counts, and the
thread relations of the engine records behind the vector-clock reports."""
import collections
import json
import re
import sys

d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "eval/baselines/setup/t3_crs/triage.json"))
for mode, m in d["modes"].items():
    ks = m["kernels"]
    print(f"\n## {mode}: {len(ks)} kernel dumps, {m['dedup_reports']} deduped reports (harness key)")
    tot = collections.Counter()
    by_w = collections.defaultdict(lambda: [0, 0, 0])      # w -> [kernels, with reports, with tv]
    print("| kernel | w | grid×block | reports | classes | tv | barrier fired / released short (arr/exp) / left open | threads never seen/block |")
    print("|---|---|---|---|---|---|---|---|")
    for k in ks:
        w = int(re.search(r"_w_(\d+)", k["short"]).group(1)) if "_w_" in k["short"] else None
        reps = k.get("reports", [])
        cls = collections.Counter(r["hb_class"] for r in reps)
        tot.update(cls)
        by_w[w][0] += 1
        by_w[w][1] += bool(reps)
        by_w[w][2] += bool(k.get("tv_violation"))
        bd = k["barrier"]
        if reps or k.get("tv_violation"):
            print(f"| {k['file'].replace('.json','')} {k['short']} | {w} | {k['grid_dim'][0]}×{k['block_dim'][0]} | "
                  f"{len(reps)} | {dict(cls)} | {'yes' if k.get('tv_violation') else ''} | "
                  f"{bd['instances_fired']} / {bd['instances_released_short']} {bd['released_short_by_arrived_expected']} / "
                  f"{bd['instances_left_open']} | {bd['threads_never_seen_per_block']} |")
    print(f"\nclasses total: {dict(tot)}")
    print("by w: kernels / with reports / with tv_violation:", {w: v for w, v in sorted(by_w.items(), key=lambda x: (x[0] is None, x[0]))})
    # distinct pc pairs with lines
    pairs = collections.Counter()
    rel = collections.Counter()
    for k in ks:
        for r in k.get("reports", []):
            pairs[(k["short"], r["ancient_pc_hex"], r["ancient_line"], r["current_pc_hex"], r["current_line"],
                   r["space"], r["race_type"], r["hb_class"], r["event_candidate"], bool(r["hb_chain"]))] += 1
            er = r.get("engine_records")
            if er:
                rel.update(er["relation"])
    lines = collections.Counter((p[2], p[4], p[5], p[6], p[7]) for p in pairs)
    print("\nreports by (anc line, cur line, space, type, class):")
    for k, v in sorted(lines.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    if rel:
        print("\nengine race records behind the reports, by thread relation:", dict(rel))
    ev = collections.Counter((p[8], p[9]) for p in pairs)
    print("event_candidate / has chain:", dict(ev))
