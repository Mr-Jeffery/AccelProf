#!/usr/bin/env python3
"""X11 stage B, analysis half of a cuRace clock-mode run (CPU, `normal`). 1) parallel.py analyze on the store
(the verdict step; a rep that hit the cap is TIMEOUT there). 2) if the recording left a partial dump
(<store>/<id>/<mode>-partial-rep*/, a prefix of the kernels), judge that prefix too: kernel JSONs that do not parse
are dropped, the rest go through the same verdict step; the reports found are written to partial.json. A report in the prefix is a
report (rule: RACE if any run reports); no report in the prefix proves nothing (the cell stays TO).
  python x11_b_analyze.py HARNESS_WT MANIFEST ID MODE LOGD TAG ANALYSIS_CAP_S [WORKERS]
WORKERS (optional): --analysis-workers of the verdict step (needs a harness with the parallel verdict code, origin/cuVein 98371ee1)."""
import glob, json, os, subprocess, sys, tempfile
W, manifest, pid, mode, logd, tag, cap = sys.argv[1:8]
cap = int(cap)
workers = int(sys.argv[8]) if len(sys.argv) > 8 else None
os.makedirs(f"{logd}/confirm", exist_ok=True)
cmd = [sys.executable, f"{W}/eval/baselines/parallel.py", "analyze", "--manifest", manifest, "--id", pid, "--confirm",
       "--confirm-dir", f"{logd}/confirm", "--tag", tag, "--results-dir", logd, "--analysis-timeout", str(cap)] + (["--analysis-workers", str(workers)] if workers else [])
print("[analyze]", " ".join(cmd), flush=True)
rc = subprocess.run(cmd).returncode
print(f"[analyze] parallel.py analyze rc={rc}", flush=True)
sys.path.insert(0, f"{W}/eval/baselines")
import parallel
store = parallel._store_root()
idir = f"{store}/{pid}"
out = dict(id=pid, mode=mode, store=idir, partial_dirs=[])
for pd in sorted(glob.glob(f"{idir}/{mode}-partial-rep*")):
    kjs = sorted(glob.glob(f"{pd}/kernel_*.json"), key=os.path.getmtime)
    bad = []
    for kj in kjs[-3:]:                      # a killed run truncates the file being written: the newest ones
        try:
            json.load(open(kj))
        except Exception:
            bad.append(os.path.basename(kj))
    good = [k for k in kjs if os.path.basename(k) not in bad]
    d = dict(dir=os.path.basename(pd), kernel_jsons=len(kjs), dropped_truncated=bad, partial_marker=open(f"{pd}/PARTIAL").read()[:300] if os.path.exists(f"{pd}/PARTIAL") else "")
    if good:
        tmp = tempfile.mkdtemp(dir=f"{store}")
        for k in good:
            os.symlink(k, f"{tmp}/{os.path.basename(k)}")
        try:
            (ids, pcs, raw), reason = (parallel._analyze_capped(tmp, f"{idir}/dots", cap, -1, workers) if workers else parallel._analyze_capped(tmp, f"{idir}/dots", cap, -1))
            d.update(reports=len(ids), report_ids=ids[:200], reason=reason)
        except Exception as e:
            d.update(error=f"{type(e).__name__}: {str(e)[:200]}")
        subprocess.run(["rm", "-rf", tmp])
    out["partial_dirs"].append(d)
json.dump(out, open(f"{logd}/partial.json", "w"), indent=1)
print("[partial]", json.dumps(out)[:600], flush=True)
