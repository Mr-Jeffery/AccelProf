#!/usr/bin/env python3
"""T21b: per (store flavor, id, mode) count of kernel JSONs carrying tv_violation (fact only). Writes eval/results/realworld/tv_violation.json"""
import glob, json, os, sys
S0 = "/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10"
out = {}
def find(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            if k == "tv_violation":
                return path + "/" + k, v
            r = find(v, path + "/" + k) if isinstance(v, (dict, list)) and k not in ("races", "verdicts", "records") else None
            if r: return r
    elif isinstance(d, list):
        for i, v in enumerate(d[:3]):
            if isinstance(v, dict):
                r = find(v, path + "[]")
                if r: return r
    return None
for fl, base in (("main", S0), ("certain", S0 + "/certain"), ("vc5400", S0 + "/vc5400"), ("longcap-vc", S0 + "/longcap-vc"), ("longcap-sc", S0 + "/longcap-sc")):
    for idd in sorted(glob.glob(base + "/*-buggy") + glob.glob(base + "/*-fixed")):
        id_ = os.path.basename(idd)
        for md in sorted(glob.glob(idd + "/*-clock")):
            n = tv = 0; ex = None
            for kj in glob.glob(md + "/kernel_*.json"):
                n += 1
                try: d = json.load(open(kj))
                except Exception: continue
                r = find(d)
                if r and r[1]:
                    tv += 1
                    ex = ex or (os.path.basename(kj), r[0], str(r[1])[:200])
            out[f"{fl}/{id_}/{os.path.basename(md)}"] = dict(n_kernel_jsons=n, n_tv_violation=tv, example=ex)
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(len(out), "mode dirs;", sum(1 for v in out.values() if v["n_tv_violation"]), "with tv_violation")
