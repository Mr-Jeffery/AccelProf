#!/usr/bin/env bash
#SBATCH --job-name=t2-eval
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t2-eval-%j.log
# T2 steps 4-5 (eval/HOST_MEMCPY_STUDY.md §4-5), T2 worktree runtime:
#   (a) the reduced-size cuHadron host/inter-kernel programs (setup/t2_small_build.sh,
#       manifest.t2small.csv) through parallel.py in both modes, YOSEMITE_HB_HOST_MEMCPY=1
#       (store/results tag t2-host) and without it (t2-host-off: today's picture);
#   (b) cost: five P6 programs with the flag on and off, same node (t2-cost-on / -off);
#   (c) the green set with the T2 runtime.
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t2_eval.sh
set -u
W=/home/fzheng4/wt-T2; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16)"
[ -z "${NOBUILD:-}" ] && bash eval/baselines/setup/t2_small_build.sh 2>&1 | tail -12
harness() {   # harness <tag> <manifest> <extra parallel.py args...>  (env set by the caller)
  local tag=$1 man=$2; shift 2
  rm -rf /mnt/beegfs/$USER/cuvein_traces/$tag $W/eval/results/$tag $W/eval/baselines/confirm_$tag
  BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$tag $PY eval/baselines/parallel.py run \
      --manifest $man --reps 1 --confirm --tag $tag "$@" \
      --results-dir $W/eval/results/$tag --confirm-dir $W/eval/baselines/confirm_$tag 2>&1 | tail -3
  cut -d, -f1,7,9,10,11,13,15 $W/eval/results/$tag/*.csv | column -s, -t | cut -c1-230
}
echo "== (a) reduced-size host/inter-kernel programs"
YOSEMITE_HB_HOST_MEMCPY=1 harness t2-host eval/baselines/setup/manifest.t2small.csv
harness t2-host-off eval/baselines/setup/manifest.t2small.csv
echo "== (b) cost: five P6 programs, flag on / off"
IDS=eval/baselines/setup/t2_cost_ids.txt
YOSEMITE_HB_HOST_MEMCPY=1 harness t2-cost-on eval/baselines/manifest.csv --id-file $IDS
harness t2-cost-off eval/baselines/manifest.csv --id-file $IDS
echo "== (c) green set (T2 runtime)"
rm -rf ScoR/microbenchmarks/artifacts/*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py python/test_host_hb.py -rxXs 2>&1 | tail -4
echo "== done $(date -Is)"
