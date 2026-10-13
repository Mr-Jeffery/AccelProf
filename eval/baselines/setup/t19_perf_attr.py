#!/usr/bin/env python3
"""T19 step 5: group the self-time lines of t19_perf_lines.sh (perf report --sort dso,sym,srcline)
into the parts of a lane access. A line inside pc_dependency_analysis.cpp is placed by its line
number (the ranges of the T19 source, commit 6f6adcf); an inlined STL/libc line by its symbol.

    python3 eval/baselines/setup/t19_perf_attr.py eval/baselines/setup/t19_perf/*.lines.txt
"""
import collections
import re
import sys

RANGES = [  # (first, last, category) in sanalyzer/src/tools/pc_dependency_analysis.cpp @ 6f6adcf
    (108, 244, "clocks: vc/pd lookup, join, merge (T5b)"),
    (262, 394, "buckets: location table probe + slot arrays (T19)"),
    (395, 442, "race aggregation"),
    (443, 485, "R3 trace points, rmw_note (T4)"),
    (486, 665, "barrier/exit/async assembly"),
    (666, 934, "A2 windows + instance gate (T14, T12)"),
    (935, 950, "reset at kernel start"),
    (951, 1076, "clocks: vc/pd lookup, join, merge (T5b)"),
    (1077, 1130, "conflict test + report"),
    (1131, 1183, "buckets: Check scan + replace (T19)"),
    (1184, 1292, "sidecar / kernel selection"),
    (1293, 1529, "record decode + per-lane dispatch (process)"),
    (1530, 1653, "HB_STATS scan (measurement only)"),
    (1654, 1800, "emit at kernel end"),
]
SYM = [  # (regex on the symbol, category) for lines outside the file
    (r"HbClock::stats", "HB_STATS scan (measurement only)"),
    (r"HbClock::emit", "emit at kernel end"),
    (r"SyncClock|VClock|base_get|HbClock::V\b|sync_group|join_", "clocks: vc/pd lookup, join, merge (T5b)"),
    (r"RmwThread|RmwPc", "R3 trace points, rmw_note (T4)"),
    (r"array<unsigned int, 32", "A2 windows + instance gate (T14, T12)"),
    (r"Win>|PendKey|Clu>|Comp>", "A2 windows + instance gate (T14, T12)"),
    (r"Pending|exited|bar_warps|warp_waiting", "barrier/exit/async assembly"),
    # std::set<const Base*> is stats()' distinct-base count; std::set<Tid> a barrier's arrivals;
    # maps keyed (block, warp) / (block, bar) the barrier/exit bookkeeping
    (r"_Rb_tree<std::vector<std::pair<unsigned long, unsigned long>", "HB_STATS scan (measurement only)"),
    (r"_Rb_tree<unsigned long, unsigned long, std::_Identity", "barrier/exit/async assembly"),
    (r"_Rb_tree<std::pair<unsigned long, unsigned int>|map<std::pair<unsigned long, unsigned int>", "barrier/exit/async assembly"),
    (r"hb_clock_reset|HbClock::reset", "reset at kernel start"),
    (r"^(cfree|malloc|_int_|unlink_chunk|free|realloc)", "allocator (malloc/free)"),
    (r"PcDependency::|phmap", "dependency tool (not HbClock)"),
    (r"LaunchEndCallback|compute_sanitizer", "collector callback / drain"),
    (r"HbClock::process", "process: inlined STL (unattributed)"),
    (r"HbClock::check", "buckets: Check scan + replace (T19)"),
]


def category(sym, src):
    m = re.match(r"pc_dependency_analysis\.cpp:(\d+)", src)
    if m:
        n = int(m.group(1))
        for a, b, c in RANGES:
            if a <= n <= b:
                return c
        return f"pc_dependency_analysis.cpp:{n}"
    for rx, c in SYM:
        if re.search(rx, sym):
            return c
    return "other"


for path in sys.argv[1:]:
    tot = collections.Counter()
    listed = 0.0
    for line in open(path):
        m = re.match(r"\s*([\d.]+)%\s+(\S+)\s+\[\.\]\s+(.*\S)\s+(\S+)\s*$", line)
        if not m:
            continue
        pct, dso, sym, src = float(m.group(1)), m.group(2), m.group(3), m.group(4)
        tot[category(sym, src)] += pct
        listed += pct
    print(f"== {path.split('/')[-1]}: {listed:.1f} % of samples in lines >= 0.2 %")
    for c, p in tot.most_common():
        print(f"  {p:5.1f} %  {c}")
