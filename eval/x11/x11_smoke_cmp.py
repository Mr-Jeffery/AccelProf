#!/usr/bin/env python3
"""X11 smoke test: overlap, scalar-clock, 1 run, 1,200 s cap, artifact binary through the container + patched accelprof,
against the old row (P9-overlap-cuda scalar-clock, eval/results/cap-84600/baselines-cuvein.csv of origin/eval/cap-84600).
  python x11_smoke_cmp.py LOGD OUT.txt     exit 0 = verdict and report ids equal, 1 = differ, 2 = no new row"""
import csv, glob, io, subprocess, sys
L, OUT = sys.argv[1:3]
t = subprocess.run(["git", "-C", "/home/fzheng4/AccelProf", "show", "origin/eval/cap-84600:eval/results/cap-84600/baselines-cuvein.csv"], capture_output=True, text=True).stdout
old = [r for r in csv.DictReader(io.StringIO(t)) if r["id"] == "P9-overlap-cuda" and r["mode"] == "scalar-clock"]
new = []
for f in glob.glob(f"{L}/baselines-cuvein-shard*.csv"):
    new += [r for r in csv.DictReader(open(f)) if r["mode"] == "scalar-clock"]
ov = sorted({r["verdict"] for r in old}); nv = sorted({r["verdict"] for r in new})
msg = f"old overlap scalar-clock rows: {len(old)} verdicts {ov} reports {[r['reports_dedup'] for r in old]} | new rows: {len(new)} verdicts {nv} reports {[r['reports_dedup'] for r in new]} notes {[r['notes'][:80] for r in new]}"
rc = 2 if not new else (0 if (ov == nv and [r['report_ids'] for r in old][:1] == [r['report_ids'] for r in new][:1]) else 1)
open(OUT, "w").write(("EQUAL " if rc == 0 else "DIFFERENT " if rc == 1 else "NO-NEW-ROW ") + msg + "\n"); print(open(OUT).read()); sys.exit(rc)
