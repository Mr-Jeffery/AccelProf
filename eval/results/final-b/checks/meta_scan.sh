#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH -t 00:20:00
#SBATCH -o /home/fzheng4/x1b/meta_scan-%j.log
hostname
python3 - <<PY
import json,glob,collections
B="/mnt/beegfs/fzheng4/cuvein_traces"
for st in ("final-2026-11","final-2026-11-24h-vc","final-2026-11-24h-sc"):
    c=collections.Counter(); n=0; ex=None
    for f in glob.glob(f"{B}/{st}/*/meta.json"):
        try: m=json.load(open(f))
        except Exception as e: c["bad:"+str(e)[:30]]+=1; continue
        n+=1; hs=m.get("hb_shards"); c[("shards",json.dumps(hs,sort_keys=True),"dump",m.get("hb_dump"),"cap",m.get("tool_timeout"),"rt",str(m.get("runtime"))[:60])]+=1
        ex=ex or m
    print(st,n)
    for k,v in c.most_common(8): print("  ",v,k)
    if ex: print("  keys:",sorted(ex.keys()))
PY
grep -l -i "HB_SHARDS\|shards" $B/final-2026-11/*/logs/*rep1.txt 2>/dev/null | head -2
