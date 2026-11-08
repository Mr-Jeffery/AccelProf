#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH -t 00:10:00
#SBATCH -o /home/fzheng4/x1b/rtraw2-%j.log
python3 - <<PY
import json,glob
B="/mnt/beegfs/fzheng4/cuvein_traces"
i="P5-race_interblock_none-lock_rtraw"
for st in ("final-2026-10","final-2026-11"):
    m=json.load(open(f"{B}/{st}/{i}/meta.json")); print(st,"node",m["node"],"runtime",m["runtime"])
    for md in ("vector-clock","scalar-clock"):
        for f in sorted(glob.glob(f"{B}/{st}/{i}/{md}/kernel_*.json")):
            t=json.load(open(f)); print(" ",md,f.split('/')[-1],"keys",sorted(t.keys())[:40])
            for k in ("hb_chain","hb_races","hb_a2","hb_rmw_points","hb_exits","hb_gate"):
                if k in t: print("   ",k,json.dumps(t[k])[:1500])
PY
