#!/usr/bin/env bash
#SBATCH --job-name=t20-shard
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2,c37
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
# T20: re-record ONE shard k of N of a p_t5b_timeout.sh store (a node failure lost it) without an
# array: an array of only some task ids would change SLURM_ARRAY_TASK_COUNT and so the shard split.
#   W=<wt> IDS=... TAG=... BASELINE_MODES=... FLOOR=... SHARD=k NSHARDS=N sbatch -o <log> t20_shard.sh
export SLURM_ARRAY_TASK_ID=$SHARD SLURM_ARRAY_TASK_COUNT=$NSHARDS
bash ${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t20}/eval/baselines/setup/p_t5b_timeout.sh
