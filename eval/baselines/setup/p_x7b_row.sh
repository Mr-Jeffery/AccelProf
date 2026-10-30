#!/usr/bin/env bash
#SBATCH --job-name=x7b-row
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=24:00:00
# X7 Part B: ONE row of racecheck or iGUARD at a fixed tool cap (run_sanitizer.py / run_iguard.py --timeout 84600),
# native wall measured in the same job. TOOL=racecheck|iguard ID=<manifest id>. Output eval/results/cap84600/<tool>-<id>.csv.
# CUDA: gpu_env.sh default (CUDA_HOME=/usr/local/cuda), the same as the original sanitizer / iGUARD jobs.
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d not readable"; exit 2; }; done
W=/home/fzheng4/wt-x7b
TOOL=${TOOL:?}; ID=${ID:?}; CAP=${CAP:-84600}
cd $W || exit 1
source eval/baselines/gpu_env.sh
export IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
gpu=$(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
echo "host=$(hostname) gpu=[$gpu] mem=$(free -g | awk '/Mem:/{print $2}')G CUDA_HOME=$CUDA_HOME ($(readlink -f $CUDA_HOME)) job=${SLURM_JOB_ID:-} tool=$TOOL id=$ID cap=$CAP harness=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) $(date -Is)"
mkdir -p eval/results/cap84600
OUT=eval/results/cap84600/$TOOL-$ID.csv
if [ $TOOL = iguard ]; then
  $PY eval/baselines/run_iguard.py --id $ID --reps 1 --timeout $CAP --out $OUT
else
  $PY eval/baselines/run_sanitizer.py --tools $TOOL --id $ID --timeout $CAP --out $OUT
fi
echo "== done rc=$? $(date -Is)"
