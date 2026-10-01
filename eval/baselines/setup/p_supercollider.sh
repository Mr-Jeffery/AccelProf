#!/usr/bin/env bash
#SBATCH --job-name=sc-run
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-15
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/sc-%A_%a.log
# SuperCollider (pre-instrumented artifact binaries, Singularity ubuntu22.04 --nv)
# over P6 cuHadron, P8 Indigo-99, P9 HeCBench-10; 5 attempts per program.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/run_supercollider.py --pset P6,P8,P9 --shard ${SLURM_ARRAY_TASK_ID}/16
