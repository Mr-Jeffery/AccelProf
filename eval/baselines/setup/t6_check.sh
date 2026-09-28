#!/usr/bin/env bash
#SBATCH --job-name=t6-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/wt-T6/eval/baselines/setup/build_logs/t6-check-%j.log
# T6: (1) the green set (CLAUDE.md A4) on this worktree (installed runtime); (2) the strict
# xfails of python/test_hb_substitutions.py (I1, I2, I5) and their controls; (3)
# design/algorithms_check.py over the regenerated ScoR corpus and the canary.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t6_check.sh
set -u
W=${W:-/home/fzheng4/wt-T6}
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | head -1) rev=$(git rev-parse --short HEAD)"
echo "collector $(sha256sum lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)"
echo "== (1) green set $(date -Is)"
rm -rf ScoR/microbenchmarks/artifacts/*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py -rxX -p no:cacheprovider 2>&1 | tail -8
echo "== (2) test_hb_substitutions.py $(date -Is)"
$PY -m pytest python/test_hb_substitutions.py -v -rxXs -p no:cacheprovider 2>&1 | grep -v Warning | tail -24
echo "== (3) algorithms_check $(date -Is)"
$PY design/algorithms_check.py ScoR/microbenchmarks/artifacts/* t6_runs/canary_pc_level_false_negative
echo "== done $(date -Is)"
