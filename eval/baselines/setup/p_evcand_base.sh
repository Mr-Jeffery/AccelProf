#!/usr/bin/env bash
#SBATCH --job-name=cv-evbase
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/evbase-%A_%a.log
# BEFORE rows on the IDENTICAL traces p_evcand.sh kept on BeeGFS: analysis only (no GPU
# work, no collection) with the two new rules switched off. Same 32-way sharding as the
# collect so shards align. Compare:
#   python3 eval/baselines/compare_fpfix.py \
#       --before 'eval/results/evcand_base/*.csv' --after-glob 'eval/results/evcand/*.csv'
# manifest pinned to the snapshot this re-run was sharded with (the live manifest.csv changes)
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/evcand
export CUVEIN_EVENT_CANDIDATES=0 CUVEIN_R3_PAST_RELEASE=0
$PY eval/baselines/parallel.py analyze --manifest eval/baselines/setup/manifest.evcand.csv --pset P1,P2,P3,P4,P5,P6 \
    --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm --tag evbase \
    --results-dir /home/fzheng4/AccelProf/eval/results/evcand_base \
    --confirm-dir /home/fzheng4/AccelProf/eval/baselines/confirm_evcand_base
