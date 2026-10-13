#!/usr/bin/env bash
#SBATCH --job-name=t3b-green-before
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-T3b/eval/baselines/setup/build_logs/t3b-green-before-%j.log
# T3b: the "before" green set (A4) -- the base worktree (0251780, detector = cuVein 3331d35 +
# PR #4's tests) on the installed runtime, with the same extra test files as t3b_check.sh
# (test_barrier_exit.py here is T3's version: 3 passed + 4 strict xfails expected).
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t3b_green_before.sh
set -u
B=/home/fzheng4/wt-T3b-base
cd $B || exit 1
export ACCEL_PROF_HOME=$B
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -- python sanalyzer | wc -l) collector $(sha256sum $B/lib/libcompute_sanitizer.so | cut -c1-16)"
rm -rf ScoR/microbenchmarks/artifacts/*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    -rxXs -p no:cacheprovider -W ignore 2>&1 | tail -15
echo "== done $(date -Is)"
