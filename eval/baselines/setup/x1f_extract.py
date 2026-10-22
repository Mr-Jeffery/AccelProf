#!/usr/bin/env python3
"""X1-follow: read-only extraction from X1's BeeGFS stores (needs a node with BeeGFS; no GPU).
(1) Part 4: for every (store, id, mode) whose meta.json has a rep that timed out or did not complete,
    the per-rep record (rc, timed_out, complete, nkernels, peak_mb, wall, err tail) and the tail of the
    accelprof stderr log; for each such id, nkernels of every COMPLETE rep in any X1 store and mode.
(2) Parts 1-3: per-kernel mtime, size, hb_events_count, hb_lanes_count and hb_stats of the kernel
    JSONs of the given ids in the given stores (kernel JSONs are moved, not copied, so mtimes are the
    times the run wrote them).
  x1f_extract.py --out <json> [--ids P7-bfs-cuda,...]
"""
import argparse
import glob
import json
import os
import re

ROOT = f"/mnt/beegfs/{os.environ['USER']}/cuvein_traces"
STORES = ["final-2026-10", "final-2026-10-long", "final-2026-10-long-sc", "final-2026-10-24h-vc",
          "final-2026-10-24h-sc"]


def tail(p, n=4000):
    try:
        with open(p, "rb") as f:
            f.seek(max(0, os.path.getsize(p) - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default="P7-bfs-cuda,P7-nbody-cuda,P7-heartwall-cuda,P9-knn-cuda")
    a = ap.parse_args()
    partial, complete_nk, metas = [], {}, {}
    for st in STORES:
        for mp in glob.glob(f"{ROOT}/{st}/*/meta.json"):
            try:
                m = json.load(open(mp))
            except ValueError:
                continue
            i = m.get("id")
            metas[(st, i)] = m
            for mode, mm in (m.get("modes") or {}).items():
                for k, rm in enumerate(mm.get("reps") or [], 1):
                    if rm.get("complete"):
                        complete_nk.setdefault(i, set()).add(rm.get("nkernels"))
    for (st, i), m in metas.items():
        for mode, mm in (m.get("modes") or {}).items():
            for k, rm in enumerate(mm.get("reps") or [], 1):
                if rm.get("timed_out") or not rm.get("complete"):
                    partial.append(dict(store=st, id=i, mode=mode, rep=k, node=m.get("node"),
                                        mem_total_gb=m.get("mem_total_gb"), native_rc=m.get("native_rc"),
                                        tool_timeout=m.get("tool_timeout"), cap=m.get("tool_timeout_cap"),
                                        partial_dump=mm.get("partial_dump"), saved=mm.get("saved"),
                                        partial=mm.get("partial"), **rm,
                                        log_tail=tail(f"{ROOT}/{st}/{i}/logs/{mode}_rep{k}.txt", 1500)))
    kern = {}
    for st in STORES:
        for i in a.ids.split(","):
            for mode in ("vector-clock", "scalar-clock"):
                kjs = sorted(glob.glob(f"{ROOT}/{st}/{i}/{mode}/kernel_*.json"),
                             key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1)))
                if not kjs:
                    continue
                rows = []
                for kj in kjs:
                    r = dict(file=os.path.basename(kj), mtime=os.path.getmtime(kj), mb=round(os.path.getsize(kj) / 1e6, 3))
                    try:
                        j = json.load(open(kj))
                        r.update(name=j.get("kernel_name") or j.get("name") or j.get("kernel"),
                                 hb_events_count=j.get("hb_events_count"), hb_lanes_count=j.get("hb_lanes_count"),
                                 hb_stats=j.get("hb_stats"), keys=sorted(j.keys()))
                    except ValueError as e:
                        r["error"] = str(e)[:200]
                    rows.append(r)
                m = metas.get((st, i), {})
                kern[f"{st}/{i}/{mode}"] = dict(started=m.get("started"), finished=m.get("finished"), node=m.get("node"),
                                                reps=(m.get("modes") or {}).get(mode, {}).get("reps"),
                                                native_walls=m.get("native_walls"), kernels=rows)
    json.dump(dict(partial=partial, complete_nkernels={k: sorted(x for x in v if x is not None)
                                                       for k, v in complete_nk.items()},
                   kernels=kern), open(a.out, "w"), indent=1, default=str)
    print(f"partial reps {len(partial)}; ids with complete reps {len(complete_nk)}; kernel sets {len(kern)}")


if __name__ == "__main__":
    main()
