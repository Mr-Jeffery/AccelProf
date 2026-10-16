#!/usr/bin/env python3
"""T22: summarise t22_diag.sh logs -- per (program, N): kernels completed under the cap, the
completion interval of the repeating big kernel (median of the intervals between consecutive
kernels of the same size class, from the kernel JSONs' mtimes), and the sharded stats of the
largest kernel (drain, route, wait, busy max/min, broadcast records).

  t22_diag_summary.py <t22-diag log>...
"""
import re
import statistics
import sys

SEC = re.compile(r"^==== (\S+) YOSEMITE_HB_SHARDS=(\d+)")
MT = re.compile(r"^(\d+) \S+/kernel_(\d+)\.json$")
KJ = re.compile(r"^\S+/kernel_(\d+)\.json: events (\d+) lanes (\d+)")
SH = re.compile(r"^  sharded (\d+) drain ([\d.]+)s route ([\d.]+)s wait ([\d.]+)s bcast (\d+) busy \[([^\]]*)\](?: stall \[([^\]]*)\])?")


def summarise(path):
    runs, cur = [], None
    for line in open(path):
        line = line.rstrip("\n")
        m = SEC.match(line)
        if m:
            cur = {"id": m.group(1), "n": int(m.group(2)), "mt": {}, "k": {}, "last": None}
            runs.append(cur)
            continue
        if cur is None:
            continue
        m = KJ.match(line)
        if m:
            cur["last"] = int(m.group(1))
            cur["k"][cur["last"]] = {"events": int(m.group(2)), "lanes": int(m.group(3))}
            continue
        m = SH.match(line)
        if m and cur["last"] is not None:
            busy = [float(x) for x in m.group(6).split(",") if x.strip()]
            cur["k"][cur["last"]].update(drain=float(m.group(2)), route=float(m.group(3)),
                                         wait=float(m.group(4)), bcast=int(m.group(5)),
                                         busy_max=max(busy), busy_min=min(busy),
                                         stall_max=max([float(x) for x in (m.group(7) or "").split(",") if x.strip()] or [0.0]))
            continue
        m = MT.match(line)
        if m:
            cur["mt"][int(m.group(2))] = int(m.group(1))
    for r in runs:
        ks = sorted(r["mt"])
        big = max(r["k"].values(), key=lambda v: v["events"], default=None)
        ivs = []
        if big:
            bigk = sorted(k for k, v in r["k"].items() if v["events"] >= 0.9 * big["events"])
            ivs = [r["mt"][b] - r["mt"][a] for a, b in zip(bigk, bigk[1:]) if a in r["mt"] and b in r["mt"]]
            # an iteration = the big kernel's period (other kernels in between included)
        if not ivs and len(ks) > 2:   # no stats (unreadable kernel JSON): every kernel after the first
            ivs = [r["mt"][b] - r["mt"][a] for a, b in zip(ks[1:], ks[2:])]
        med = statistics.median(ivs) if ivs else None
        s = f"{r['id']} N={r['n']}: {len(ks)} kernels;"
        if med is not None:
            s += f" big-kernel period {med:.0f} s;"
        if big and "drain" in big:
            s += (f" big kernel: drain {big['drain']:.1f} route {big['route']:.1f} wait {big['wait']:.1f} "
                  f"busy {big['busy_min']:.1f}-{big['busy_max']:.1f} stall<={big['stall_max']:.1f} bcast {big['bcast']} "
                  f"events {big['events']}")
        print(s)


for p in sys.argv[1:]:
    print(f"## {p}")
    summarise(p)
