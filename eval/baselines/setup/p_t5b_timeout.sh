#!/usr/bin/env bash
#SBATCH --job-name=t5b-timeout
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --array=0-15
# T5b acceptance (CLAUDE.md section C): the 58 programs of setup/engine_timeout_ids.txt
# (vector-clock TIMEOUT/OOM in the baselines) with the T5b worktree runtime, both modes,
# one rep, every trace kept on BeeGFS. Tool cap = the harness rule min(max(10 x native,
# floor), 1200 s) with the floor at 1200 s (the 20-min protocol P7/P9 were recorded under),
# so a row says both whether the run finishes at all and, from its wall, whether it finishes
# under 120 s. Scalar-clock rows tell whether the trace itself fits (the engine not running).
# The same script records the engine==oracle set (setup/t5b_parity_ids.txt, vector-clock only):
#   IDS=eval/baselines/setup/t5b_parity_ids.txt TAG=t5b-parity BASELINE_MODES=vector-clock FLOOR=120 \
#     sbatch --array=0-7 -o <W>/build_logs/t5b-parity-%A_%a.log eval/baselines/setup/p_t5b_timeout.sh
#   W=<worktree> sbatch -o <W>/build_logs/t5b-timeout-%A_%a.log eval/baselines/setup/p_t5b_timeout.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/t5b-shared-base-clock}
TAG=${TAG:-t5b-timeout}
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
mkdir -p eval/results/$TAG eval/baselines/confirm_$TAG /mnt/beegfs/$USER/cuvein_traces/$TAG
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
$PY eval/baselines/parallel.py run --id-file ${IDS:-eval/baselines/setup/engine_timeout_ids.txt} \
    --shard ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT} --reps 1 --confirm --keep-all \
    --timeout-floor ${FLOOR:-1200} --analysis-timeout 3600 --tag $TAG \
    --results-dir $W/eval/results/$TAG --confirm-dir $W/eval/baselines/confirm_$TAG 2>&1 | tail -20
echo "== done $(date -Is)"
