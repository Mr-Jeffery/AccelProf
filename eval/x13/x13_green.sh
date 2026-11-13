#!/usr/bin/env bash
# X13: the green set (CLAUDE.md A4's seven files + test_collector_only.py) on the worktree runtime, as t26_green.sh runs it,
# with the counter compiled in (YOSEMITE_SHARD_STATS unset: the tests run the counter off). Run inside the GPU job:
#   srun --jobid=<job> --overlap -n1 -c16 bash eval/x13/x13_green.sh
set -u
W=${W:-/home/fzheng4/wt-shard-balance}
source $W/eval/x13/x13_env.sh
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
echo "host=$(hostname) gpu=[$gpu] nproc=$(nproc) job=${SLURM_JOB_ID:-} $(date -Is)"
echo "worktree HEAD=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) libsanalyzer=$(sha256sum $S/san-install/lib/libsanalyzer.so | cut -c1-16) collector=$(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16)"
cd $W
rm -rf ScoR/microbenchmarks/artifacts/*
echo "== A4 seven + test_collector_only.py $(date -Is)"
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    python/test_collector_only.py -q -p no:cacheprovider 2>&1 | tail -15
echo "== done $(date -Is)"
