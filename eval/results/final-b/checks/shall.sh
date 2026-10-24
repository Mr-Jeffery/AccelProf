#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH --cpus-per-task=4
#SBATCH -t 01:00:00
#SBATCH -o /home/fzheng4/x1b/shall-%j.log
hostname; date -Is
python3 - <<'PY'
import json, glob, collections, os
B = "/mnt/beegfs/fzheng4/cuvein_traces"
c = collections.Counter(); bad = []
for st in ("final-2026-11", "final-2026-11-long", "final-2026-11-long-sc", "final-2026-11-24h-vc", "final-2026-11-24h-sc"):
    for md in ("scalar-clock", "vector-clock"):
        for k in glob.glob(f"{B}/{st}/*/{md}/kernel_*.json"):
            try:
                t = json.load(open(k))
            except Exception as e:
                c[(st, md, "unreadable")] += 1; continue
            sh = ((t.get("hb_stats") or {}).get("hb_clock") or {}).get("sharded")
            if md == "scalar-clock":
                ok = isinstance(sh, dict) and sh.get("shards") == 16 and len(sh.get("busy_s") or []) == 16
                c[(st, md, "sharded=16" if ok else "OTHER")] += 1
                if not ok and len(bad) < 20: bad.append((k, json.dumps(sh)[:150]))
            else:
                c[(st, md, "no sharded block" if sh is None else "HAS sharded")] += 1
                if sh is not None and len(bad) < 20: bad.append((k, json.dumps(sh)[:150]))
for k in sorted(c): print(k, c[k])
print("bad:", len(bad)); [print("  ", b) for b in bad]
PY
date -Is
