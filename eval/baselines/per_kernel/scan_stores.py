#!/usr/bin/env python3
"""X13 step 0c: for every kept store, per id and mode: number of kernel JSONs, meta.json presence/mode summary.
Usage: scan_stores.py OUT.csv STORE_DIR..."""
import csv, json, os, sys
out = sys.argv[1]
w = csv.writer(open(out, "w", newline=""))
w.writerow(["store", "id", "mode", "n_files", "n_kernel_json", "bytes", "saved", "partial", "events", "reps", "reps_complete", "has_meta"])
for st in sys.argv[2:]:
    base = os.path.basename(st.rstrip("/"))
    if not os.path.isdir(st):
        w.writerow([base, "(store missing)"]); continue
    for i in sorted(os.listdir(st)):
        d = os.path.join(st, i)
        if not os.path.isdir(d):
            continue
        meta = None
        try:
            meta = json.load(open(os.path.join(d, "meta.json")))
        except Exception:
            pass
        modes = sorted(set(os.listdir(d)) & {"vector-clock", "scalar-clock", "collector-only"})
        for m in modes:
            try:
                fs = os.listdir(os.path.join(d, m))
            except Exception:
                fs = []
            kj = [f for f in fs if f.endswith(".json")]
            size = 0
            for f in kj:
                try: size += os.path.getsize(os.path.join(d, m, f))
                except OSError: pass
            mm = (meta or {}).get("modes", {}).get(m, {})
            reps = mm.get("reps", [])
            w.writerow([base, i, m, len(fs), len(kj), size, mm.get("saved", ""), mm.get("partial", ""), mm.get("events", ""),
                        len(reps), sum(1 for r in reps if r.get("complete")), meta is not None])
