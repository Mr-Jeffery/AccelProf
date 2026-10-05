#!/usr/bin/env python3
"""T19 tables (eval/FLAT_BUCKETS.md) from the BeeGFS outputs of t19_time.sh and t19_long.sh.

  time    before/after wall, peak RSS, lane-accesses (hb_lanes_count summed over the kernel JSONs)
          and wall per lane-access, from setup/t19_time/<label>.json (t5a_stats.py) and
          /mnt/beegfs/$USER/t19-time-{before,after}/<id>/<mode>/ (t19_long.sh)
  memory  per program and mode of /mnt/beegfs/$USER/<dir>/<id>/<mode>/ (t19_long.sh): rc, wall,
          kernels written, peak RSS, the last hb_stats line's bucket entries / bytes / bytes_est

    .env/bin/python eval/baselines/setup/t19_tables.py time
    .env/bin/python eval/baselines/setup/t19_tables.py memory [--dir t19-long] [--ref t4-long]
"""
import argparse
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BG = f"/mnt/beegfs/{os.environ['USER']}"
TAIL = 1 << 20
RTS = tuple(os.environ.get("T19_RUNTIMES", "before after").split())


def tail_json_field(path, key):
    """The value of a top-level numeric field or object near the end of a kernel JSON."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - TAIL))
        tail = f.read().decode("utf-8", "replace")
    m = re.search(rf'"{key}": (\d+)', tail)
    return int(m.group(1)) if m else None


def lanes(dirpath):
    tot, n = 0, 0
    for kj in glob.glob(f"{dirpath}/dependency_*/kernel_*.json"):
        v = tail_json_field(kj, "hb_lanes_count")
        if v is None:
            with open(kj) as f:
                v = json.load(f).get("hb_lanes_count")
        tot += v or 0
        n += 1
    return tot, n


def stats_lines(d):
    out = []
    for f in glob.glob(f"{d}/*.accelprof.log") + [f"{d}/stdout.txt"]:
        if os.path.exists(f):
            for line in open(f, errors="replace"):
                if "HB_STATS" in line:
                    out.append(line.strip())
    return out


def bucket_of(line):
    m = re.search(r'"buckets": (\{[^}]*\})', line)
    return json.loads(m.group(1)) if m else {}


def rss_of(line):
    m = re.search(r'rss_kb"?:? (\d+)', line)
    return int(m.group(1)) if m else None


def long_row(d):
    rc = open(f"{d}/rc.txt").read().strip() if os.path.exists(f"{d}/rc.txt") else "?"
    tm = open(f"{d}/time.txt").read().strip() if os.path.exists(f"{d}/time.txt") else ""
    wall = re.search(r"wall_s=([\d.]+)", tm)
    mrss = re.search(r"maxrss_kb=(\d+)", tm)
    st = stats_lines(d)
    last = st[-1] if st else ""
    b = bucket_of(last)
    ln, nk = lanes(d)
    return {"rc": rc, "wall_s": float(wall.group(1)) if wall else None,
            "maxrss_gb": round(int(mrss.group(1)) / 2**20, 1) if mrss else None,
            "last_rss_gb": round(rss_of(last) / 2**20, 1) if last and rss_of(last) else None,
            "kernels": nk, "lanes": ln, "entries": b.get("entries"), "locations": b.get("locations"),
            "bytes_gb": round(b["bytes"] / 1e9, 2) if "bytes" in b else None,
            "bytes_est_gb": round(b["bytes_est"] / 1e9, 2) if "bytes_est" in b else None}


def cmd_time(_a):
    print("| program (mode) | " + " | ".join(f"{rt}: wall, peak" for rt in RTS)
          + f" | lane-accesses | µs per lane-access {' / '.join(RTS)} |")
    print("|---" * (len(RTS) + 3) + "|")
    for lab in ("tiled_gemm-256", "reduction-norace-large", "cc-push-1296n"):
        r = {}
        for rt in RTS:
            p = f"{HERE}/t19_time/{lab}-{rt}.json"
            if not os.path.exists(p):
                continue
            j = json.load(open(p))
            ln, _ = lanes(f"{BG}/t5a_stats/{lab}-{rt}")
            r[rt] = (j["wall_s"], j["peak_rss_mb"] / 1024, ln, j["rc"], j["timed_out"])
        _row(f"{lab} (vector-clock)", r)
    for pid, mode in (("P7-hotspot-cuda", "vector-clock"), ("P9-fpc-cuda", "scalar-clock")):
        r = {}
        for rt in RTS:
            d = f"{BG}/t19-time-{rt}/{pid}/{mode}"
            if os.path.isdir(d):
                x = long_row(d)
                r[rt] = (x["wall_s"], x["maxrss_gb"] or x["last_rss_gb"] or 0, x["lanes"], x["rc"], x["rc"] != "rc=0")
        _row(f"{pid} ({mode})", r)


def _row(name, r):
    def cell(rt):
        if rt not in r:
            return "—"
        w, m, _, rc, to = r[rt]
        return f"{w:.0f} s, {m:.2f} GB" + (f" ({rc}{', timeout' if to is True else ''})" if to else "")
    ln = (r.get("after") or r.get("before") or (0, 0, 0, 0, 0))[2]
    us = " / ".join(f"{r[rt][0] / r[rt][2] * 1e6:.2f}" if rt in r and r[rt][2] else "—" for rt in RTS)
    print(f"| {name} | " + " | ".join(cell(rt) for rt in RTS) + f" | {ln:,} | {us} |")


def cmd_memory(a):
    print("| program | mode | rc | wall | kernels | peak RSS | bucket entries | locations | bytes (flat) | bytes_est (old layout) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for idd in sorted(glob.glob(f"{BG}/{a.dir}/*/")):
        pid = os.path.basename(idd.rstrip("/"))
        for mode in ("scalar-clock", "vector-clock"):
            d = f"{idd}{mode}"
            if not os.path.isdir(d):
                continue
            x = long_row(d)
            print(f"| {pid} | {mode} | {x['rc']} | {x['wall_s']} | {x['kernels']} | "
                  f"{x['maxrss_gb'] or x['last_rss_gb']} GB | {x['entries']} | {x['locations']} | "
                  f"{x['bytes_gb']} GB | {x['bytes_est_gb']} GB |")


ap = argparse.ArgumentParser()
sp = ap.add_subparsers(dest="cmd", required=True)
sp.add_parser("time").set_defaults(f=cmd_time)
m = sp.add_parser("memory")
m.add_argument("--dir", default="t19-long")
m.set_defaults(f=cmd_memory)
a = ap.parse_args()
a.f(a)
