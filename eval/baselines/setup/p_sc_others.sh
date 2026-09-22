#!/usr/bin/env bash
#SBATCH --job-name=sc-others
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/scothers-%A_%a.log
# The other detectors on the SuperCollider-matched sets P8+P9 (our builds of the
# same sources): cuVein engine+trace-only, compute-sanitizer family, iGUARD.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/local/$USER/cvtraces
K=${SLURM_ARRAY_TASK_ID}
$PY eval/baselines/parallel.py run --pset P8,P9 --shard $K/16 --confirm --tag sc \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep --keep-cap-mb 300
$PY eval/baselines/run_sanitizer.py --pset P8,P9 --shard $K/16 \
    --out eval/results/baselines-sanitizer-shardsc${K}_16.csv
$PY eval/baselines/run_iguard.py --pset P8,P9 --shard $K/16 \
    --out eval/results/baselines-iguard-shardsc${K}_16.csv
