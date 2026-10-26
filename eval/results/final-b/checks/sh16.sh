#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH -t 00:20:00
#SBATCH -o /home/fzheng4/x1b/sh16-%j.log
hostname
B=/mnt/beegfs/fzheng4/cuvein_traces
python3 - <<'PY'
import json, glob
B = "/mnt/beegfs/fzheng4/cuvein_traces"
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            q = f"{p}.{k}" if p else k
            if "shard" in k.lower():
                yield q, v if not isinstance(v, (dict, list)) else json.dumps(v)[:200]
            yield from walk(v, q)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            yield from walk(v, f"{p}[{i}]")
for st, i in (("final-2026-11-24h-sc", "P7-heartwall-cuda"), ("final-2026-11", "P4-graph-connectivity-racy-small"),
              ("final-2026-11", "P7-nbody-cuda")):
    for md in ("scalar-clock", "vector-clock"):
        ks = sorted(glob.glob(f"{B}/{st}/{i}/{md}/kernel_*.json"))[:1]
        for k in ks:
            t = json.load(open(k))
            hits = list(walk(t))
            print(st, i, md, k.split("/")[-1], "shard keys:", hits[:8])
    m = json.load(open(f"{B}/{st}/{i}/meta.json"))
    print("   meta hb_shards", m.get("hb_shards"), "node", m.get("node"))
PY
for f in $B/final-2026-11-24h-sc/P7-heartwall-cuda/logs/*; do echo "== $f"; grep -i -m3 "shard" $f; done 2>/dev/null | head -20
ls $B/final-2026-11-24h-sc/P7-heartwall-cuda/logs/ | head
