#!/usr/bin/env python3
"""C4 pair level: the per-pair verdict records of X1b's scalar-clock recording of every program, with the barrier-ordered rule
ON (scalar-clock as recorded) and OFF (CO-R), by the harness's own verdict path (run_cuvein._analyze_reports), captured the way X5
and C3 do it (x5_common.Capture).  One jsonl line per program:
  {"id", "store", "kbytes", "on": {"reason", "elapsed", "pairs"}, "off": {...}}
a pair = [space, lo pc, hi pc, sorted tags, unresolved]; a tag = "<verdict>:<hb_class>:<flags>" over the launches, flags
  c = ordered by an R3 chain (hb_chain, which reads the RMW points), e = an event-stream candidate (no edge names the pair),
  r = the edge was rescued (distance from the sync pass).  `unresolved` = some launch left it to neither R1 nor R3.
usage: co_offline_pairs.py K/N   (shard K of N, by kernel bytes)   env PAIRS_CAP (s, default 3600), PAIRS_MEM (GB, default 40)"""
import csv
import json
import os
import sys
import time

sys.path.insert(0, "/home/fzheng4/wt-c4/eval/baselines/setup")
sys.path.insert(0, "/home/fzheng4/wt-c4/eval/baselines")
import x5_common as xc            # noqa: E402
from x5_common import rc          # noqa: E402

B = "/mnt/beegfs/fzheng4/cuvein_traces"
SUFFIX = ("", "-long", "-long-sc", "-24h-sc")


def store_of(pid):
    for sfx in SUFFIX:
        d = f"{B}/final-2026-11{sfx}/{pid}/scalar-clock"
        if os.path.isdir(d) and any(n.startswith("kernel_") for n in os.listdir(d)):
            return f"final-2026-11{sfx}"
    return None


k, n = (int(x) for x in sys.argv[1].split("/"))
CAP = int(os.environ.get("PAIRS_CAP", "3600"))
MEM = int(os.environ.get("PAIRS_MEM", "40"))
OUTD = "/home/fzheng4/wt-c4/eval/results/co-offline/pairs"
os.makedirs(OUTD, exist_ok=True)
IDS = [x for x in os.environ.get("PAIRS_IDS", "").split(",") if x]       # a re-run of named recordings with a longer cap
OUT = f"{OUTD}/shard_long_{os.environ.get('PAIRS_TAG', 'x')}.jsonl" if IDS else f"{OUTD}/shard{k}.jsonl"
ids = sorted(r["id"] for r in csv.DictReader(open("/home/fzheng4/wt-c4/eval/baselines/manifest.csv")))
jobs = []
for pid in ids:
    st = store_of(pid)
    if st:
        d = f"{B}/{st}/{pid}/scalar-clock"
        kb = sum(e.stat().st_size for e in os.scandir(d) if e.name.startswith("kernel_"))
        jobs.append((kb, pid, st, d))
jobs.sort(reverse=True)
mine = [j for j in jobs if j[1] in IDS] if IDS else [j for i, j in enumerate(jobs) if i % n == k]
done = set()
if os.path.exists(OUT):
    for ln in open(OUT):
        done.add(json.loads(ln)["id"])
print(f"shard {k}/{n}: {len(mine)} recordings, {len(done)} done", flush=True)


def tag(v):
    return (f"{v['verdict']}:{v['hb_class']}:" + ("c" if v.get("hb_chain") is not None else "")
            + ("e" if v.get("event_candidate") else "") + ("r" if v.get("edge_rescued") else ""))


for kb, pid, st, d in mine:
    if pid in done:
        continue
    rec = {"id": pid, "store": st, "kbytes": kb}
    for half, env in (("on", "1"), ("off", "0")):
        os.environ["CUVEIN_BARRIER_ORDER"] = env
        t0 = time.time()

        def work():
            pairs = {}

            def fn(dot, kj, rep):
                for v in rep["verdicts"]:
                    key = (v["space"].split("/")[0], min(v["ancient_pc"], v["current_pc"]), max(v["ancient_pc"], v["current_pc"]))
                    e = pairs.setdefault(key, {"tags": set(), "unres": False})
                    e["tags"].add(tag(v))
                    if not xc.static_resolved(v):
                        e["unres"] = True
            with xc.Capture(fn):
                rc._analyze_reports(d, f"{B}/{st}/{pid}/dots")
            return sorted([sp, lo, hi, sorted(e["tags"]), e["unres"]] for (sp, lo, hi), e in pairs.items())
        pay, reason = xc.run_capped(work, CAP, MEM)
        rec[half] = {"reason": reason, "elapsed": round(time.time() - t0, 1), "pairs": pay}
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(pid[:70], rec["on"]["reason"] or "ok", rec["off"]["reason"] or "ok", rec["on"]["elapsed"], rec["off"]["elapsed"], flush=True)
