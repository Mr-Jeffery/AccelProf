#!/usr/bin/env python3
"""C1 step 3 (eval/COLLECTOR_ONLY.md): sanity and the report tables over the merged collector-only rows.
  post_co.py <wt> [--stores]    reads <wt>/eval/results/collector-only/merged/baselines-cuvein.csv"""
import collections
import csv
import glob
import json
import math
import os
import re
import statistics
import subprocess
import sys

W = sys.argv[1]
STORES = "--stores" in sys.argv
O = f"{W}/eval/results/collector-only/merged"
rows = list(csv.DictReader(open(f"{O}/baselines-cuvein.csv", newline="")))
man = list(csv.DictReader(open(f"{W}/eval/baselines/manifest.csv", newline="")))
PS = ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9")
want = [m for m in man if m["pset"] in PS]
out = []


def p(s=""):
    out.append(s)


by = collections.defaultdict(list)
for r in rows:
    by[r["id"]].append(r)


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def ev(r):
    m = re.search(r"events=(\d+)", r["notes"])
    return int(m.group(1)) if m else None


def cap(r):
    m = re.search(r"cap=(\d+)", r["notes"])
    return m.group(1) if m else ""


# ---- sanity
missing = [m["id"] for m in want if m["id"] not in by]
p("## Sanity")
p(f"- manifest ids in the 8 psets: {len(want)}; with a row: {len(want) - len(missing)}; without: {len(missing)}")
p(f"- modes in the rows: {dict(collections.Counter(r['mode'] for r in rows))}")
bad = [r for r in rows if r["verdict"] in ("TIMEOUT", "ERROR") and not r["notes"].strip()]
p(f"- TIMEOUT/ERROR rows without a reason in notes: {len(bad)}")
reasons = collections.Counter()
for r in rows:
    if r["verdict"] in ("TIMEOUT", "ERROR"):
        n = r["notes"]
        if n.startswith("cap=") and ";" in n:
            n = n.split(";", 1)[1]
        k = "timeout" if r["verdict"] == "TIMEOUT" else re.sub(r"[=(].*", "", n)
        reasons[(r["verdict"], r["pset"], k[:40])] += 1
for k, v in sorted(reasons.items()):
    p(f"  - {k[0]} {k[1]} `{k[2]}`: {v} rows")


def prog_verdict(rs):
    vs = {r["verdict"] for r in rs}
    for v in ("RACE", "TIMEOUT", "ERROR", "CLEAN"):
        if v in vs:
            return v
    return "none"


pv = {i: prog_verdict(rs) for i, rs in by.items()}
disagree = {i for i, rs in by.items() if len({r["verdict"] for r in rs if r["verdict"] in ("RACE", "CLEAN")}) > 1}
p()
p("## Per-suite verdict counts (programs; RACE if any rep RACE)")
p("| pset | programs | RACE | CLEAN | TIMEOUT | ERROR | no row | reps disagree |")
p("|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
for ps in PS:
    ids = [m["id"] for m in want if m["pset"] == ps]
    c = collections.Counter(pv.get(i, "none") for i in ids)
    d = sum(1 for i in ids if i in disagree)
    p(f"| {ps} | {len(ids)} | {c['RACE']} | {c['CLEAN']} | {c['TIMEOUT']} | {c['ERROR']} | {c['none']} | {d} |")
    tot.update(c)
    tot["dis"] += d
p(f"| all | {len(want)} | {tot['RACE']} | {tot['CLEAN']} | {tot['TIMEOUT']} | {tot['ERROR']} | {tot['none']} | {tot['dis']} |")

p()
p("## Per-suite geometric-mean slowdown (median tool wall / native wall per program, RACE/CLEAN rows) and median peak RSS")
p("| pset | programs measured | geomean slowdown | median peak RSS (MB) | max peak RSS (MB) |")
p("|---|---|---|---|---|")
for ps in PS:
    sl, rss = [], []
    for m in want:
        if m["pset"] != ps:
            continue
        rs = [r for r in by.get(m["id"], []) if r["verdict"] in ("RACE", "CLEAN")]
        w = [f(r["wall_s"]) for r in rs if f(r["wall_s"]) is not None]
        n = [f(r["native_wall_s"]) for r in rs if f(r["native_wall_s"])]
        pk = [f(r["peak_mb"]) for r in rs if f(r["peak_mb"]) is not None]
        if w and n:
            sl.append(statistics.median(w) / n[0])
        if pk:
            rss.append(statistics.median(pk))
    g = math.exp(sum(map(math.log, sl)) / len(sl)) if sl else float("nan")
    if rss:
        p(f"| {ps} | {len(sl)} | {g:.2f} | {statistics.median(rss):.0f} | {max(rss):.0f} |")
    else:
        p(f"| {ps} | 0 | | | |")

p()
p("## HeCBench rows (P7, P9)")
p("| id | verdict | reports | tool wall (s, median) | native (s) | peak RSS (MB) | records drained | cap (s) |")
p("|---|---|---|---|---|---|---|---|")
for m in want:
    if m["pset"] not in ("P7", "P9"):
        continue
    rs = by.get(m["id"], [])
    done = [r for r in rs if r["verdict"] in ("RACE", "CLEAN")]
    use = done or rs
    w = [f(r["wall_s"]) for r in use if f(r["wall_s"]) is not None]
    pk = [f(r["peak_mb"]) for r in use if f(r["peak_mb"]) is not None]
    e = next((ev(r) for r in done if ev(r)), None)
    wm = statistics.median(w) if w else None
    p(f"| {m['id']} | {pv.get(m['id'])} | {max((int(r['reports_dedup'] or 0) for r in done), default='')} | "
      f"{'' if wm is None else round(wm, 1)} | {use[0]['native_wall_s'] if use else ''} | "
      f"{round(statistics.median(pk)) if pk else ''} | {e if e is not None else 'missing'} | {cap(use[0]) if use else ''} |")

p()
p("## µs per recorded access against X1-follow's collector-only runs (`-n 1`, eval/x1_follow/table1.md)")
p("| program | this run: wall (s) / records / µs per record / node | X1-follow µs per record | difference |")
p("|---|---|---|---|")
BFS = "P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n"
XF = {"P7-heartwall-cuda": 0.2905, "P9-knn-cuda": 0.2965, BFS: 1449.0, "P7-bfs-cuda": None, "P7-nbody-cuda": None}
for i, x in XF.items():
    rs = [r for r in by.get(i, []) if r["verdict"] in ("RACE", "CLEAN")]
    if not rs:
        p(f"| {i[:48]} | missing | {x if x is not None else 'missing'} | |")
        continue
    w = statistics.median(f(r["wall_s"]) for r in rs)
    e = ev(rs[0])
    node = re.search(r"node=(\w+)", rs[0]["notes"])
    us = w / e * 1e6 if e else None
    if x is None:
        d = "no X1-follow collector-only number"
    else:
        d = f"{(us - x) / x * 100:+.1f} %" + (" (above 20 %: finding)" if abs((us - x) / x) > 0.2 else "")
    p(f"| {i[:48]} | {w:.1f} / {e} / {us:.4g} / {node.group(1) if node else '?'} | {x if x is not None else 'missing'} | {d} |")

if STORES:
    p()
    p("## Stores: meta.json and kernel JSON checks")
    B = f"/mnt/beegfs/{os.environ.get('USER', 'fzheng4')}/cuvein_traces"
    frozen = dict(collector="b746b4dd23e90f46", libsanalyzer="5a20fd14ab6c6806",
                  fatbin="a2d7368bc1c61986", fatbin_late="e96343121c74ca0a")
    for tag in ("final-2026-11-co", "final-2026-11-co-long", "final-2026-11-co-24h",
                "final-2026-11-co-parity-a", "final-2026-11-co-parity-b"):
        metas = glob.glob(f"{B}/{tag}/*/meta.json")
        rt, bad_rt, nmodes, ntrace = collections.Counter(), 0, collections.Counter(), 0
        harness, nodes = collections.Counter(), collections.Counter()
        for mp in metas:
            m = json.load(open(mp))
            r = m.get("runtime", {})
            if any(r.get(k) != v for k, v in frozen.items()):
                bad_rt += 1
            rt[r.get("runtime_head")] += 1
            harness[(r.get("harness_head"), r.get("harness_dirty"))] += 1
            nodes[m.get("node")] += 1
            for mo, mm in m.get("modes", {}).items():
                nmodes[mo] += 1
                if mm.get("hb_trace") is not False:
                    ntrace += 1
        g = subprocess.run(f"grep -rl --include='kernel_*.json' -m1 '\"hb_' {B}/{tag} | wc -l",
                           shell=True, capture_output=True, text=True).stdout.strip()
        nk = subprocess.run(f"find {B}/{tag} -name 'kernel_*.json' | wc -l",
                            shell=True, capture_output=True, text=True).stdout.strip()
        p(f"- `{tag}`: {len(metas)} meta.json; runtime hashes differing from the frozen four: {bad_rt}; "
          f"runtime_head {dict(rt)}; harness (head, dirty) {dict(harness)}; modes {dict(nmodes)}; "
          f"modes with hb_trace not false: {ntrace}; kernel JSONs {nk}, of them with an hb_ key: {g}; nodes {dict(nodes)}")
os.makedirs(O, exist_ok=True)
open(f"{O}/report_tables.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
