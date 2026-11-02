#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH -t 00:20:00
#SBATCH -o /home/fzheng4/x1b/pf-%j.log
hostname
python3 - <<'PY'
import json, glob, os
B = "/mnt/beegfs/fzheng4/cuvein_traces"
for st, i, md in (("final-2026-11-long", "P7-particlefilter-cuda", "vector-clock"),
                  ("final-2026-10-long", "P7-particlefilter-cuda", "vector-clock"),
                  ("final-2026-11-long", "P7-haversine-cuda", "vector-clock"),
                  ("final-2026-10-long", "P7-haversine-cuda", "vector-clock")):
    d = f"{B}/{st}/{i}"
    try:
        m = json.load(open(f"{d}/meta.json"))
    except Exception as e:
        print(st, i, "no meta", e); continue
    reps = m.get("modes", {}).get(md, {}).get("reps") if isinstance(m.get("modes"), dict) else None
    print(st, i, md, "node", m.get("node"), "mem_total_gb", m.get("mem_total_gb"), "cap", m.get("tool_timeout"))
    if reps:
        for r in reps:
            print("   rep", {k: r.get(k) for k in ("rc", "timed_out", "complete", "nkernels", "peak_mb", "wall")})
    ks = sorted(glob.glob(f"{d}/{md}/kernel_*.json"))
    tot = 0
    for k in ks:
        try:
            t = json.load(open(k))
        except Exception as e:
            print("   ", os.path.basename(k), "unreadable", str(e)[:60]); continue
        n = len(t.get("hb_races") or [])
        tot += n
        print("   ", os.path.basename(k), t.get("kernel", "")[:40] if isinstance(t.get("kernel"), str) else "", "hb_races", n)
    print("   kernel JSONs", len(ks), "hb_races total", tot)
PY
