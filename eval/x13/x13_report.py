#!/usr/bin/env python
"""X13: eval/SHARD_BALANCE.md = eval/x13/SHARD_BALANCE.template.md with the generated tables of eval/x13/results/ filled in.
  x13_report.py <worktree>
"""
import re, sys
w = sys.argv[1]
R = f"{w}/eval/x13/results"
rd = lambda p: open(p).read().strip()
t = rd(f"{w}/eval/x13/SHARD_BALANCE.template.md")
over = ["| bfs size | run | pass | top shard of the run | d_over's segment (allocation offset in the 2 MiB arena) | d_over's shard | its lanes | kernels where it is the shard's top segment | share of that shard | share of all lane-records | is the top segment of the top shard |", "|---|---|---|---|---|---|---|---|---|---|---|"]
cur = None
for line in open(f"{R}/bfs_over.txt"):
    m = re.match(r"#### bfs (\S+) (\S+)", line)
    if m:
        cur = (m.group(1), m.group(2)); continue
    m = re.match(r"-- (\w+): (\d+) kernels, lane-records ([\d,]+); top shard (\d+)", line)
    if m:
        ps, top = m.group(1), m.group(4); continue
    m = re.match(r"\s+d_over's segment (0x[0-9a-f]+) on shard (\d+): ([\d,]+) lanes over (\d+) kernels .* = ([\d.]+) % of shard \d+, ([\d.]+) % of all lane-records", line)
    if m:
        seg, sh, lanes, k, p1, p2 = m.groups()
        over.append(f"| {cur[0]} | {cur[1]} | {ps} | {top} | {seg[:-3] and '…' + seg[-6:]} | {sh} | {lanes} | {k} | {p1} % | {p2} % | {'yes' if sh == top else 'NO'} |")
t = t.replace("@@over@@", "\n".join(over))
for k, f in (("main", "shard_balance.md"), ("hot", "shard_balance_hot.md"), ("types", "shard_balance_types.md"),
             ("stability", "shard_balance_stability.md"), ("timing", "shard_balance_timing.md")):
    t = t.replace(f"@@{k}@@", rd(f"{R}/{f}"))
assert "@@" not in t
open(f"{w}/eval/SHARD_BALANCE.md", "w").write(t + "\n")
print("wrote", f"{w}/eval/SHARD_BALANCE.md", len(t))
