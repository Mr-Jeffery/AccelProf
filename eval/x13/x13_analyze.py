#!/usr/bin/env python
"""X13: per-shard record counts -> markdown tables (eval/SHARD_BALANCE.md section 2) and a JSON summary.

  x13_analyze.py RUNS_DIR OUT_PREFIX [--over ADDR[:SIZE]]
RUNS_DIR holds one directory per run: <prog>__<size>__<mode>/ with run.json and shards/shards_*.json
(pcdep pass) or shards/shards_sync_*.json (sync pass) -- the output of x13_run.py.

Per run (program x size x pass): sums over the kernels of each shard's lane_records / warp_records;
total, max shard, max/total, max/mean (= N * max/total, N the shard count; the bound speed-up <= N / (max/mean)
= total/max); split fraction = split_warp_records / warp_records_distinct; per-kernel critical path
sum_k(max_s lanes_k,s) / total (what a barrier between kernels waits for); the top segment of the top shard.
"""
import glob, json, os, sys
from collections import defaultdict

runs_dir, prefix = sys.argv[1], sys.argv[2]
over = None
if "--over" in sys.argv:
    over = sys.argv[sys.argv.index("--over") + 1]


def load(d):
    rid = os.path.basename(d.rstrip("/"))
    prog, size, mode = rid.split("__")
    run = json.load(open(f"{d}/run.json"))
    out = {"prog": prog, "size": size, "mode": mode, "run": run}
    for pas, pat in (("pcdep", "shards_[0-9]*.json"), ("sync", "shards_sync_[0-9]*.json")):
        files = sorted(glob.glob(f"{d}/shards/{pat}"), key=lambda f: int(f.rsplit("_", 1)[1].split(".")[0]))
        if not files:
            continue
        ks = [json.load(open(f)) for f in files]
        n = ks[0]["shards"]
        lane = [sum(k["lane_records"][i] for k in ks) for i in range(n)]
        warp = [sum(k["warp_records"][i] for k in ks) for i in range(n)]
        crit_l = sum(max(k["lane_records"]) for k in ks)
        crit_w = sum(max(k["warp_records"]) for k in ks)
        distinct = sum(k["warp_records_distinct"] for k in ks)
        split = sum(k["split_warp_records"] for k in ks)
        segs = [sum(k["distinct_segments_per_shard"][i] for k in ks) for i in range(n)]
        types = defaultdict(int)
        for k in ks:
            for t, c in k["record_types"].items():
                types[t] += c
        ti = max(range(n), key=lambda i: lane[i])
        agg = defaultdict(int)
        for k in ks:
            t = k["top_segment_per_shard"][ti]
            if t:
                agg[(t["space"], t["block_or_object"], t["offset"])] += t["lanes"]
        top = max(agg.items(), key=lambda kv: kv[1]) if agg else None
        out[pas] = dict(n=n, kernels=len(ks), lane=lane, warp=warp, crit_l=crit_l, crit_w=crit_w, distinct=distinct,
                        split=split, segs=segs, types=dict(types), top_shard=ti, top=top,
                        top_by_kernel=[(k["top_segment_per_shard"][ti], k["lane_records"][ti]) for k in ks])
    return out


rows = [load(d) for d in sorted(glob.glob(f"{runs_dir}/*__*__*")) if os.path.exists(f"{d}/run.json")]
pct = lambda x: f"{100 * x:.2f} %"
md = []
md.append("| program | size | pass | kernels | lane-records | max shard | max/total | max/mean | per-kernel crit. path / total | warp-records | max shard | max/total | max/mean | split frac. | top shard | top segment (space, block/object, offset) | its lanes | share of shard |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
summary = []
for r in rows:
    for pas in ("pcdep", "sync"):
        if pas not in r:
            continue
        s = r[pas]
        n = s["n"]
        TL, ML = sum(s["lane"]), max(s["lane"])
        TW, MW = sum(s["warp"]), max(s["warp"])
        top = s["top"]
        topl = f"{top[0][0]}, {top[0][1]}, {top[0][2]:#x}" if top else "n/a"
        share = f"{100 * top[1] / s['lane'][s['top_shard']]:.2f} %" if top else "n/a"
        md.append(f"| {r['prog']} | {r['size']} | {pas} ({r['mode']}) | {s['kernels']} | {TL:,} | {ML:,} | {pct(ML / TL)} | {n * ML / TL:.3f} | {pct(s['crit_l'] / TL)} | {TW:,} | {MW:,} | {pct(MW / TW)} | {n * MW / TW:.3f} | {pct(s['split'] / s['distinct'])} | {s['top_shard']} | {topl} | {top[1]:,} | {share} |" if top else
                  f"| {r['prog']} | {r['size']} | {pas} ({r['mode']}) | {s['kernels']} | {TL:,} | {ML:,} | {pct(ML / TL)} | {n * ML / TL:.3f} | {pct(s['crit_l'] / TL)} | {TW:,} | {MW:,} | {pct(MW / TW)} | {n * MW / TW:.3f} | {pct(s['split'] / s['distinct'])} | {s['top_shard']} | n/a | n/a | n/a |")
        T = s["types"]
        tot_rec = sum(T.values())
        sync_rec = T.get("barrier", 0) + T.get("block_exit", 0) + T.get("syncwarp", 0) + T.get("pipeline_commit", 0) + T.get("pipeline_wait", 0)
        summary.append(dict(prog=r["prog"], size=r["size"], mode=r["mode"], pas=pas, n=n, kernels=s["kernels"], total_lane=TL, max_lane=ML,
                            max_over_total=ML / TL, max_over_mean=n * ML / TL, crit_over_total=s["crit_l"] / TL,
                            total_warp=TW, max_warp=MW, warp_max_over_total=MW / TW, warp_max_over_mean=n * MW / TW,
                            split_frac=s["split"] / s["distinct"], distinct=s["distinct"], top_shard=s["top_shard"],
                            top_segment=top[0] if top else None, top_lanes=top[1] if top else None,
                            top_share_of_shard=top[1] / s["lane"][s["top_shard"]] if top else None,
                            record_types=T, drained_records=tot_rec, sync_event_records=sync_rec,
                            sync_event_frac=sync_rec / tot_rec if tot_rec else None,
                            segs_per_shard=s["segs"], lane=s["lane"], warp=s["warp"],
                            wall=r["run"].get("wall"), native=r["run"].get("native_wall"), peak_mb=r["run"].get("peak_mb"),
                            rc=r["run"].get("rc"), timed_out=r["run"].get("timed_out"), cmd=r["run"].get("cmd"),
                            job=r["run"].get("slurm_job")))
open(f"{prefix}.md", "w").write("\n".join(md) + "\n")
json.dump(summary, open(f"{prefix}.json", "w"), indent=1)

# stability: per (prog, mode, pas) the max/total at the sizes, ratio of the larger-size value to the smaller-size one
by = defaultdict(list)
for x in summary:
    by[(x["prog"], x["mode"], x["pas"])].append(x)
st = ["| program | pass | sizes | lane max/total | ratio (larger / smaller size) | flag (>10 % apart) | warp max/total | ratio |", "|---|---|---|---|---|---|---|---|"]
PAIRS = {"stencil1d": ("L10", "L20"), "pathfinder": ("R10", "R20"), "bfs": ("500K", "1M"), "atomicCAS": ("r100", "r200")}
for (prog, mode_, pas), xs in sorted(by.items()):
    xs = [x for x in xs if x["size"] in PAIRS.get(prog, ())]
    if len(xs) < 2:
        continue
    xs = sorted(xs, key=lambda x: x["total_lane"])
    a, b = xs[0], xs[-1]
    ra = b["max_over_total"] / a["max_over_total"]
    rw = b["warp_max_over_total"] / a["warp_max_over_total"]
    st.append(f"| {prog} | {pas} ({mode_}) | {a['size']} -> {b['size']} | {pct(a['max_over_total'])} -> {pct(b['max_over_total'])} | {ra:.4f} | {'YES' if abs(ra - 1) > 0.10 else 'no'} | {pct(a['warp_max_over_total'])} -> {pct(b['warp_max_over_total'])} | {rw:.4f} |")
open(f"{prefix}_stability.md", "w").write("\n".join(st) + "\n")

ty = ["| program | size | pass | drained records | global | shared | local | barrier | block_exit | syncwarp | pipeline | sync-event fraction (barrier+exit+syncwarp+pipeline) |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for x in summary:
    if x["pas"] != "pcdep":          # the sync pass's router does not count record types
        continue
    T = x["record_types"]
    ty.append(f"| {x['prog']} | {x['size']} | {x['pas']} ({x['mode']}) | {x['drained_records']:,} | {T.get('global', 0):,} | {T.get('shared', 0):,} | {T.get('local', 0):,} | {T.get('barrier', 0):,} | {T.get('block_exit', 0):,} | {T.get('syncwarp', 0):,} | {T.get('pipeline_commit', 0) + T.get('pipeline_wait', 0):,} | {pct(x['sync_event_frac'])} |")
open(f"{prefix}_types.md", "w").write("\n".join(ty) + "\n")

tm = ["| program | size | mode | N | wall (s, counter on) | native (s) | peak RSS (MB) | rc | timed out | job |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    ru = r["run"]
    tm.append(f"| {r['prog']} | {r['size']} | {r['mode']} | {ru['workers']} | {ru.get('wall')} | {ru.get('native_wall')} | {ru.get('peak_mb')} | {ru.get('rc')} | {ru.get('timed_out')} | {ru.get('slurm_job')} |")
open(f"{prefix}_runs.md", "w").write("\n".join(tm) + "\n")

# the hottest (shard, segment) pairs: a shard's top segment of each kernel, summed over the kernels where it is that shard's top
hot = ["| program | size | pass | hottest segments (shard: space, block/object, offset -> lanes, share of all lane-records) |", "|---|---|---|---|"]
for r in rows:
    for pas in ("pcdep", "sync"):
        if pas not in r:
            continue
        pat = "shards_[0-9]*.json" if pas == "pcdep" else "shards_sync_[0-9]*.json"
        ks = [json.load(open(f)) for f in glob.glob(f"{runs_dir}/{r['prog']}__{r['size']}__{r['mode']}/shards/{pat}")]
        agg = defaultdict(int)
        tot = sum(sum(k["lane_records"]) for k in ks)
        for k in ks:
            for i, t in enumerate(k["top_segment_per_shard"]):
                if t:
                    agg[(i, t["space"], t["block_or_object"], t["offset"])] += t["lanes"]
        top = sorted(agg.items(), key=lambda kv: -kv[1])[:4]
        hot.append(f"| {r['prog']} | {r['size']} | {pas} ({r['mode']}) | " + "; ".join(f"{k[0]}: {k[1]}, {k[2]}, {k[3]:#x} -> {v:,} ({100 * v / tot:.2f} %)" for k, v in top) + " |")
open(f"{prefix}_hot.md", "w").write("\n".join(hot) + "\n")
print(open(f"{prefix}.md").read())
print(open(f"{prefix}_stability.md").read())
print(open(f"{prefix}_types.md").read())
