#!/usr/bin/env bash
#SBATCH --job-name=sc-others
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/scothers-%A_%a.log
# The other detectors on the SuperCollider-matched sets P8+P9 (our builds of the
# same sources): cuVein vector-clock+scalar-clock, compute-sanitizer family, iGUARD.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/sc   # BeeGFS, every trace kept (eval/STORAGE.md)
K=${SLURM_ARRAY_TASK_ID}
$PY eval/baselines/parallel.py run --pset P8,P9 --shard $K/16 --confirm --tag sc \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 300
$PY eval/baselines/run_sanitizer.py --pset P8,P9 --shard $K/16 \
    --out eval/results/baselines-sanitizer-shardsc${K}_16.csv
# run_iguard.py keeps per-id log dirs under $BASELINE_TRACE_DIR: give it its own tree so
# they never land inside (or collide with) the cuVein store's <id>/ directories
BASELINE_TRACE_DIR=/mnt/beegfs/$USER/tool_logs/iguard-sc $PY eval/baselines/run_iguard.py --pset P8,P9 --shard $K/16 \
    --out eval/results/baselines-iguard-shardsc${K}_16.csv
