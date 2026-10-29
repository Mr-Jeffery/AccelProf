#!/usr/bin/env python3
"""C3 item 9 data: the per-pair verdict records of two separate recordings of every program -- X1b's scalar-clock recording
and C1's collector-only recording -- by the harness's own verdict path (run_cuvein._analyze_reports, what parallel.py
analyze runs), captured the way X5 does it (x5_common.Capture).  Nothing here changes a rule or a verdict.
One jsonl line per (program, mode): the pairs (space, lo pc, hi pc) with the set of `verdict:hb_class` they took over the
launches, and whether some launch left them unresolved by R1 and R3.
usage: co_pairs_collect.py K/N   (shard K of N, by kernel bytes)"""
import sys, os, json, csv, glob, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # eval/baselines/setup/x5_common.py (X5, checked out from origin/eval/x5-byte-pairs)
import x5_common as xc
from x5_common import rc
B = "/mnt/beegfs/fzheng4/cuvein_traces"
RECS = (("scalar-clock", "final-2026-11"), ("collector-only", "final-2026-11-co"))
SUFFIX = {"scalar-clock": ("", "-long", "-long-sc", "-24h-sc"), "collector-only": ("", "-long", "-24h")}
def store_of(base, pid, mode):
    for sfx in SUFFIX[mode]:
        d = f"{B}/{base}{sfx}/{pid}/{mode}"
        if os.path.isdir(d) and any(n.startswith("kernel_") for n in os.listdir(d)): return f"{base}{sfx}"
    return None
k, n = (int(x) for x in sys.argv[1].split("/"))
OUT = f"eval/results/collector-only-tables/pairs/shard{k}.jsonl"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
ids = sorted(r["id"] for r in csv.DictReader(open("eval/baselines/manifest.csv")))
jobs = []
for pid in ids:
    for mode, base in RECS:
        st = store_of(base, pid, mode)
        if st:
            d = f"{B}/{st}/{pid}/{mode}"
            kb = sum(e.stat().st_size for e in os.scandir(d) if e.name.startswith("kernel_"))
            jobs.append((kb, pid, mode, st, d))
jobs.sort(reverse=True)
mine = [j for i, j in enumerate(jobs) if i % n == k]            # round robin over the size-sorted list
done = set()
if os.path.exists(OUT):
    for ln in open(OUT): r = json.loads(ln); done.add((r["id"], r["mode"]))
print(f"shard {k}/{n}: {len(mine)} recordings, {len(done)} done", flush=True)
for kb, pid, mode, st, d in mine:
    if (pid, mode) in done: continue
    t0 = time.time()
    def work():
        pairs = {}
        def fn(dot, kj, rep):
            for v in rep["verdicts"]:
                key = (v["space"].split("/")[0], min(v["ancient_pc"], v["current_pc"]), max(v["ancient_pc"], v["current_pc"]))
                e = pairs.setdefault(key, {"cls": set(), "unres": False})
                e["cls"].add(f"{v['verdict']}:{v['hb_class']}")
                if not xc.static_resolved(v): e["unres"] = True
        with xc.Capture(fn):
            rc._analyze_reports(d, f"{B}/{st}/{pid}/dots")
        return sorted([sp, lo, hi, sorted(e["cls"]), e["unres"]] for (sp, lo, hi), e in pairs.items())
    pay, reason = xc.run_capped(work, 900, 40)
    rec = {"id": pid, "mode": mode, "store": st, "kbytes": kb, "reason": reason, "elapsed": round(time.time() - t0, 1), "pairs": pay}
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    print(pid[:70], mode, reason or "ok", rec["elapsed"], flush=True)

