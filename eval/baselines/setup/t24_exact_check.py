"""T24: classify the exact-count compare (t4_parity.py compare without --counts-le) results: is every
MISMATCH a scalar-clock count-only difference with aggregates < records, all other checks true?
  t24_exact_check.py <shard json>...
"""
import json, re, sys, collections
tot = collections.Counter()
for f in sys.argv[1:]:
    for prog in json.load(open(f)):
        for mode in prog.get("modes", prog.get("results", [])) if isinstance(prog, dict) else []:
            pass
def walk(x, path=()):
    if isinstance(x, dict):
        if "status" in x and "checks" in x:
            yield path, x
        for k, v in x.items():
            yield from walk(v, path + (k,))
    elif isinstance(x, list):
        for v in x:
            yield from walk(v, path)
for f in sys.argv[1:]:
    data = json.load(open(f))
    for prog in data:
        pid = prog.get("id") or prog.get("program")
        for _, k in walk(prog):
            tot[k["status"]] += 1
            if k["status"] != "MISMATCH":
                continue
            others = {c: v for c, v in k["checks"].items() if c != "sync"}
            le = all((m := re.search(r"agg=(\d+) rec=(\d+)", d)) and int(m[1]) <= int(m[2])
                     for d in k.get("sync_diff", []))
            only_counts = all(re.search(r"agg=\d+ rec=\d+", d) for d in k.get("sync_diff", []))
            tot["mismatch: other checks all true"] += all(others.values())
            if not all(others.values()):
                print(pid, {c: v for c, v in others.items() if not v}, str(k.get("verdict_diff"))[:400])
            tot["mismatch: sync diffs all counts with agg <= rec"] += le and only_counts
print(dict(tot))
