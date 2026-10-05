#!/usr/bin/env bash
#SBATCH --job-name=t3-repro
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t3-repro-%j.log
# T3: the early-exit barrier reproducer (python/test_barrier_exit.py) with the installed
# detector (the T3 worktree's lib/ is the main checkout's); plus racecheck on it.
#   sbatch -p rtx4060ti16g eval/baselines/setup/t3_repro.sh
W=/home/fzheng4/wt-T3
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader)"
$PY -m pytest python/test_barrier_exit.py -rxXs -p no:cacheprovider 2>&1 | tail -15
T=$(mktemp -d); nvcc -arch=native -lineinfo --cudart shared python/testdata/barrier_exited_threads.cu -o $T/b
echo "== racecheck"; compute-sanitizer --tool racecheck $T/b 2>&1 | tail -4
echo "== synccheck"; compute-sanitizer --tool synccheck $T/b 2>&1 | tail -4
rm -rf $T
