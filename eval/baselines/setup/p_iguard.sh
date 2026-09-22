#!/usr/bin/env bash
#SBATCH --job-name=iguard-run
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/iguard-%A_%a.log
# iGUARD (NVBit tool, LD_PRELOAD) over P1-P6, 3 reps, sharded ->
# eval/results/baselines-iguard-shard{k}_32.csv. Exits 3 (no rows) if the tool
# was not built -- nothing is simulated.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
$PY eval/baselines/run_iguard.py --pset P1,P2,P3,P4,P5,P6 --shard ${SLURM_ARRAY_TASK_ID}/32
