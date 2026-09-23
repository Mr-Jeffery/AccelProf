#!/usr/bin/env bash
#SBATCH --job-name=t8-green
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/wt-T8/eval/baselines/setup/t8_check/green-%j.log
# T8 green set (Claude.md A4) run from the T8 worktree: its python/ (renamed tests, hb_modes)
# and its lib/ (private collector relinked against the T8 libsanalyzer.so). getall.sh sets
# ACCEL_PROF_HOME=$(pwd) = the worktree, so every trace is recorded with the T8 library.
cd /home/fzheng4/wt-T8 || exit 1
export ACCEL_PROF_HOME=/home/fzheng4/wt-T8
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader)"
echo "engine lib: $(.env/bin/python -c "import sys; sys.path.insert(0,'python'); import hb_modes; print(hb_modes.engine_library('/home/fzheng4/wt-T8'))")"
rm -rf ScoR/microbenchmarks/artifacts/*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py -rxXs 2>&1 | tail -25
echo "== renamed tests collected:"
.env/bin/python -m pytest python/test_sync_dominance.py python/test_coherent_ldst.py --collect-only -q 2>/dev/null | grep -c "scalar_clock"
