#!/usr/bin/env bash
#SBATCH --job-name=x8-sc
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-x8/eval/x_logs/x8-sc-%A_%a.log
# X8: SuperCollider on the 594 new rows (99 shipped codes x 6 HiRace graphs), artifact protocol
# (--reps 5, RACE if any attempt reports). Shard k/N = SLURM_ARRAY_TASK_ID / X8_NSHARD.
# Dry run: X8_ID=<manifest id> X8_OUT=<csv> sbatch ... (no shard, no exclusion).
export ACCEL_PROF_HOME=/home/fzheng4/wt-x8
cd /home/fzheng4/wt-x8 || exit 1
source eval/baselines/gpu_env.sh
export PY=/home/fzheng4/AccelProf/.env/bin/python
export SINGULARITY_BIND=/mnt/beegfs
echo "node=$(hostname) gpu=$(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader | tr '\n' ' ')"
LR=/mnt/local/$USER/sc_logs_x8
mkdir -p $LR 2>/dev/null || { echo "no /mnt/local/$USER on $(hostname)"; }
if [ -n "$X8_ID" ]; then
  $PY eval/baselines/run_supercollider.py --pset PI --id "$X8_ID" --reps 5 --log-root $LR --out "$X8_OUT"
else
  K=${SLURM_ARRAY_TASK_ID}; N=${X8_NSHARD:-20}
  $PY eval/baselines/run_supercollider.py --pset PI --exclude-input DAG_100n_100e --reps 5 \
      --shard $K/$N --log-root $LR \
      --out /home/fzheng4/wt-x8/eval/results/baselines-supercollider-allinputs-shard${K}_${N}.csv
fi
