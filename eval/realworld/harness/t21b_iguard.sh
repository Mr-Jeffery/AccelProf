#!/usr/bin/env bash
#SBATCH --job-name=t21b-iguard
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --array=0-1
#SBATCH --exclude=c0,c1,c22,c34
#SBATCH --output=/home/fzheng4/wt-t21b/eval/realworld/logs/iguard-%A_%a.log
# iGUARD (global memory only) on the T21b targets whose oracle race is in global
# memory (oracle field space=global), buggy and fixed, 3 reps, 2 shards.
cd /home/fzheng4/wt-t21b || exit 1
export CUDA_HOME=/usr/local/cuda-13.4
source eval/baselines/gpu_env.sh
export IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/realworld_t21b/iguard_logs
hostname; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
IDS=$(for t in amrex-1 cccl-3 cccl-4 cmssw-1 ginkgo-5 pytorch-3 pytorch-4 raft-1; do printf "%s-buggy,%s-fixed," $t $t; done)
$PY eval/baselines/run_iguard.py --manifest eval/realworld/manifest_t21b.csv \
    --id "${IDS%,}" --reps 3 --shard ${SLURM_ARRAY_TASK_ID}/2 \
    --out eval/results/realworld/iguard-shard${SLURM_ARRAY_TASK_ID}_2.csv
