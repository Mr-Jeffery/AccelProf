#!/usr/bin/env python3
"""X7 step 6: time the verdict step (run_cuvein._analyze_reports) per (id, mode) in its own
process, N = 1, for the code at --home. Without --workers the call has no workers/cache argument
(the pre-X7 code); with --workers W it passes workers=W and cache=not --no-cache.
  x7_old.py select --out list.tsv               the sample (see below)
  x7_old.py run --home H --list list.tsv --out o.csv [--workers 1] [--no-cache] [--jobs 8] [--limit 7200]
select: from final-b-merged (rep 1, rows with analysis_s), ids that no long/24h pass re-ran:
  non-HeCBench suites P1 8, P3 4, P4 8, P5 4, P6 4, PI 12 = 40 programs (vector-clock), evenly spaced
  over the sorted new-code analysis_s and including the slowest; every HeCBench (P7, P9) key, both modes."""
import argparse, csv, glob, hashlib, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
W = "/home/fzheng4/wt-x7a"
T = "/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11"
ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["select", "run", "child"])
ap.add_argument("--out"); ap.add_argument("--list"); ap.add_argument("--home")
ap.add_argument("--workers", type=int, default=None); ap.add_argument("--no-cache", action="store_true")
ap.add_argument("--jobs", type=int, default=8); ap.add_argument("--limit", type=int, default=7200)
ap.add_argument("--mode-dir"); ap.add_argument("--dots-dir")
a = ap.parse_args()

if a.cmd == "select":
    longids = set()
    for f in glob.glob(W + "/eval/baselines/setup/x7_a5_*.txt"):
        longids |= {l.strip() for l in open(f) if l.strip()}
    rows = [r for r in csv.DictReader(open(W + "/eval/results/verdict-timing/final-b-merged/baselines-cuvein.csv"))
            if r["rep"] == "1" and "analysis_s=" in r["notes"] and r["id"] not in longids]
    def s(r): return float(re.search(r"analysis_s=([0-9.]+)", r["notes"]).group(1))
    out = []
    for ps, q in [("P1", 8), ("P3", 4), ("P4", 8), ("P5", 4), ("P6", 4), ("PI", 12)]:
        v = sorted((r for r in rows if r["pset"] == ps and r["mode"] == "vector-clock"), key=lambda r: (s(r), r["id"]))
        idx = sorted({round(i * (len(v) - 1) / (q - 1)) for i in range(q)})
        out += [(v[i]["id"], v[i]["mode"], ps) for i in idx]
    for ps in ("P7", "P9"):
        out += [(r["id"], r["mode"], ps) for r in sorted(rows, key=lambda r: (r["id"], r["mode"])) if r["pset"] == ps]
    with open(a.out, "w") as fh:
        for t in out: fh.write("\t".join(t) + "\n")
    print(len(out), "items;", sum(1 for t in out if t[2] in ("P7", "P9")), "HeCBench")
    sys.exit(0)

if a.cmd == "child":
    sys.path.insert(0, a.home + "/eval/baselines")
    import run_cuvein as rc
    t0 = time.time()
    kw = {} if a.workers is None else {"workers": a.workers, "cache": not a.no_cache}
    ids, pcs, raw = rc._analyze_reports(a.mode_dir, a.dots_dir, **kw)
    el = time.time() - t0
    canon = json.dumps([ids, sorted(pcs), raw], sort_keys=True, default=repr)
    print(json.dumps({"s": round(el, 3), "race_ids": len(ids), "raw": len(raw),
                      "sha256": hashlib.sha256(canon.encode()).hexdigest()}))
    sys.exit(0)

items = [l.rstrip("\n").split("\t") for l in open(a.list) if l.strip()]
def one(it):
    i, m, ps = it
    md, dd = f"{T}/{i}/{m}", f"{T}/{i}/dots"
    nk = len(glob.glob(md + "/kernel_*.json"))
    cmd = [sys.executable, os.path.abspath(__file__), "child", "--home", a.home, "--mode-dir", md, "--dots-dir", dd]
    if a.workers is not None: cmd += ["--workers", str(a.workers)] + (["--no-cache"] if a.no_cache else [])
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=a.limit)
        res = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else {}
        st = "ok" if res else f"rc={p.returncode}:{p.stderr.strip()[-120:]}"
    except subprocess.TimeoutExpired:
        res, st = {}, f"limit{a.limit}"
    r = {"id": i, "mode": m, "pset": ps, "kernels": nk, "status": st, "s": res.get("s", ""),
         "wall_s": round(time.time() - t0, 1), "race_ids": res.get("race_ids", ""), "raw": res.get("raw", ""),
         "sha256": res.get("sha256", "")}
    print(r, flush=True)
    return r
with ThreadPoolExecutor(a.jobs) as ex: rs = list(ex.map(one, items))
with open(a.out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs)
