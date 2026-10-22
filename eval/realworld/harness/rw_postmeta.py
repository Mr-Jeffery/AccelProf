#!/usr/bin/env python3
"""T21b: add the run's facts to a trace store's meta.json (parallel.py does not record them):
runtime hashes, the shard count N of the scalar-clock sync pass, node/core count, knobs.
Usage: rw_postmeta.py --meta <store>/<id>/meta.json --flavor main --shards 16 ..."""
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
ap.add_argument("--policy", default="recorded")
ap.add_argument("--timeout", type=int, default=0)
a = ap.parse_args()
try:
    m = json.load(open(a.meta))
except (OSError, ValueError) as e:
    raise SystemExit(f"postmeta: cannot read {a.meta}: {e}")
m["t21b"] = dict(
    flavor=a.flavor, node=socket.gethostname(), nproc=a.nproc, slurm_job=a.job, worktree_head=a.head,
    runtime=dict(libsanalyzer=a.libsanalyzer, collector=a.collector, fatbin=a.fatbin, fatbin_late=a.fatbin_late,
                 checkout="/home/fzheng4/AccelProf", install_commit="f551ca0", runtime_built_from="e0e6431"),
    hb_shards=a.shards, hb_shards_applies_to="scalar-clock (vector-clock mode runs the serial pass)",
    hb_stats=1, hb_dump=0, gate_policy=a.policy, atomic_scope_sidecar="accelprof -n 1 + sidecar (parallel.py)",
    tool_timeout_s=a.timeout, cuda_home=a.cuda_home, gpu=a.gpu,
    knobs={k: v for k, v in sorted(os.environ.items()) if k.startswith(("YOSEMITE_", "CUVEIN_", "BASELINE_"))})
tmp = a.meta + ".t21b.tmp"
json.dump(m, open(tmp, "w"))
os.replace(tmp, a.meta)
print(f"postmeta: {a.meta} hb_shards={a.shards} libsanalyzer={a.libsanalyzer}")
