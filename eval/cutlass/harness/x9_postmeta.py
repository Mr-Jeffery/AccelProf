#!/usr/bin/env python3
"""X9 (copy of T21b's rw_postmeta.py): add the run's facts to a trace store's meta.json (parallel.py does not record
them): runtime hashes (install commit f551ca0), the shard count N of the scalar-clock sync pass (SHARDED_SYNC.md II.10:
N = 16), node/core count, knobs, the CUTLASS tag and commit.
Usage: x9_postmeta.py --meta <store>/<id>/meta.json --flavor main --shards 16 ..."""
import argparse, json, os, socket
ap = argparse.ArgumentParser()
ap.add_argument("--meta", required=True)
ap.add_argument("--flavor", required=True)
ap.add_argument("--shards", type=int, required=True)
ap.add_argument("--nproc", type=int, required=True)
ap.add_argument("--libsanalyzer", required=True)
ap.add_argument("--collector", required=True)
ap.add_argument("--fatbin", required=True)
ap.add_argument("--fatbin-late", dest="fatbin_late", default="")
ap.add_argument("--cuda-home", dest="cuda_home", required=True)
ap.add_argument("--gpu", default="")
ap.add_argument("--job", default="")
ap.add_argument("--head", default="")
ap.add_argument("--timeout", type=int, default=0)
a = ap.parse_args()
try:
    m = json.load(open(a.meta))
except (OSError, ValueError) as e:
    raise SystemExit(f"postmeta: cannot read {a.meta}: {e}")
m["x9"] = dict(
    flavor=a.flavor, node=socket.gethostname(), nproc=a.nproc, slurm_job=a.job, worktree_head=a.head,
    runtime=dict(libsanalyzer=a.libsanalyzer, collector=a.collector, fatbin=a.fatbin, fatbin_late=a.fatbin_late,
                 checkout="/home/fzheng4/AccelProf", install_commit="f551ca0", runtime_built_from="e0e6431"),
    hb_shards=a.shards, hb_shards_source="SHARDED_SYNC.md II.10 (N = 16)", hb_shards_applies_to="scalar-clock",
    hb_stats=int(os.environ.get("YOSEMITE_HB_STATS", "0")), hb_dump=int(os.environ.get("BASELINE_HB_DUMP", "1")),
    atomic_scope_sidecar="accelprof -n 1 + sidecar (parallel.py collect)",
    tool_timeout_s=a.timeout, cuda_home=a.cuda_home, gpu=a.gpu,
    cutlass=dict(tag="v4.8.1", commit="2c85f497547eb441f0fe80bfb0fb2e6f9add1719"),
    knobs={k: v for k, v in sorted(os.environ.items()) if k.startswith(("YOSEMITE_", "CUVEIN_", "BASELINE_"))})
tmp = a.meta + ".x9.tmp"
json.dump(m, open(tmp, "w"))
os.replace(tmp, a.meta)
print(f"postmeta: {a.meta} hb_shards={a.shards} libsanalyzer={a.libsanalyzer} scope_present={m.get('scope_present')}")
