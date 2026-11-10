#!/usr/bin/env python3
"""X13 step 2: cuRace's reports per kernel. For every (program-input id, mode) of the table, run the verdict
layer's per-kernel-JSON step (run_cuvein._kernel_report: the same function _analyze_reports calls) on each kept
kernel JSON and record, per kernel JSON, its kernel name and the RACE reports it holds.
Usage: curace_kernels.py CODE_ROOT MODE OUT.csv SHARD/NSHARDS IDS_FILE STORE[:prio]...  (later stores override earlier)
  MODE: vector-clock | scalar-clock | collector-only. collector-only runs with chain closure, co_async, co_r3=strict
  (the S1 setting of co-chain-b), CODE_ROOT = the co-chain-b worktree; the clock modes use this worktree's code."""
import csv, glob, json, os, sys, time
code, mode, out, shard, idsf = sys.argv[1:6]
stores = sys.argv[6:]
k, n = map(int, shard.split("/"))
sys.argv = sys.argv[:1]
sys.path.insert(0, f"{code}/python"); sys.path.insert(0, f"{code}/eval/baselines"); sys.path.insert(0, f"{code}/eval")
import run_cuvein as rc
import aggregate as agg
ids = [l.strip() for l in open(idsf) if l.strip()]
ids = [i for j, i in enumerate(sorted(ids)) if j % n == k]
CO = mode == "collector-only"
fh = open(out, "w", newline="")
w = csv.writer(fh)
w.writerow(["id", "mode", "store", "kjson", "kernel_id", "kernel_name", "n_races", "pairs", "classes", "status", "secs"])
ALL = os.environ.get("X13_ALL") == "1"     # X11 stores: one store per rep, every rep reported (mode dir may be <mode>-partial-rep1)
def mdir(c):
    if os.path.isdir(f"{c}/{mode}"):
        return f"{c}/{mode}"
    g = sorted(glob.glob(f"{c}/{mode}-partial*"))
    return g[0] if g else None
jobs = []
for i in ids:
    cand = [(i, f"{st}/{i}") for st in stores if mdir(f"{st}/{i}")]
    if not cand:
        jobs.append((i, None, None))
    elif ALL:
        jobs += [(i, c, mdir(c)) for i, c in cand]
    else:
        jobs.append((i, cand[-1][1], mdir(cand[-1][1])))     # later stores override
for i, d, md in jobs:
    if d is None:
        w.writerow([i, mode, "", "", "", "", "", "", "", "no-store", ""]); continue
    dots = sorted(glob.glob(f"{d}/dots/*.dot"))
    kjs = sorted(glob.glob(f"{md}/kernel_*.json"), key=lambda p: int(os.path.basename(p)[7:-5]))
    if os.environ.get("X13_KJ"):                       # shard of the kernel JSONs of one store (the 46k-60k-JSON atomicCAS stores)
        k2, n2 = map(int, os.environ["X13_KJ"].split("/"))
        kjs = [x for j, x in enumerate(kjs) if j % n2 == k2]
    if not kjs:
        w.writerow([i, mode, os.path.dirname(d), "", "", "", "", "", "", "no-kernel-json", ""]); continue
    for kj in kjs:
        t0 = time.time()
        try:
            head = json.load(open(kj))["kernel"]
            kid, kname = head["kernel_id"], head["kernel_name"]
        except Exception as e:
            kid, kname = "", f"UNREADABLE:{type(e).__name__}"
        try:
            if CO and os.environ.get("X13_CO_C6") == "1":      # X11's stage A: chain closure only (eval/co-chain, C6), no co_async / co_r3
                rep = rc._kernel_report(kj, dots, True)
            elif CO:
                rep = rc._kernel_report(kj, dots, True, (True, "strict"))
            else:
                rep = rc._kernel_report(kj, dots)
            if rep is None:
                status, pairs, cls = "no-aligned-dot", [], []
            else:
                ded, cl = {}, {}
                for v in rep["verdicts"]:
                    if v["verdict"] == "RACE":
                        key = agg._dedup_key(v)
                        ded.setdefault(key, v)
                        cl[key] = v.get("matrix_class", v.get("hb_class")) or "race"
                pairs = sorted(f"{s}:{hex(a)}-{hex(b)}" for (a, b, s) in ded)
                cls = sorted({f"{s}:{hex(a)}-{hex(b)}={cl[(a, b, s)]}" for (a, b, s) in ded})
                status = "ok"
        except Exception as e:
            status, pairs, cls = f"error:{type(e).__name__}:{str(e)[:80]}", [], []
        fh.flush()
        w.writerow([i, mode, os.path.dirname(d), os.path.basename(kj), kid, kname, len(pairs), " ".join(pairs), " ".join(cls),
                    status, f"{time.time()-t0:.2f}"])
