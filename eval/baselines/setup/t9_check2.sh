#!/usr/bin/env bash
#SBATCH --job-name=t9-check2
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t9-check2-%j.log
# T9: the suites outside the green set that exercise the engine -- cp.async agents (T1a),
# barrier exits (T3's strict xfails, fixed by T3b), host operations (T2) -- with the T9
# worktree runtime; expected: unchanged from before T9 (test_cp_async/test_host_hb pass,
# test_barrier_exit's strict xfails still xfail).
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_check2.sh
set -u
W=/home/fzheng4/wt-T9
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16)"
$PY -m pytest python/test_cp_async.py python/test_barrier_exit.py python/test_host_hb.py \
    -rxXs -p no:cacheprovider -W ignore 2>&1 | tail -15
echo "== done $(date -Is)"
