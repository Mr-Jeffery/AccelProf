#!/bin/bash
# WARPSYNC join gap: smoke test of wjg_scan.py + wjg_census.py on one X5 program (t16-certain).
#   sbatch eval/baselines/setup/p_wjg_smoke.sh
#SBATCH -p normal
#SBATCH -J wjg-smoke
#SBATCH -t 01:00:00
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -o /home/fzheng4/wt-warpsync-join-gap/eval/x_logs/wjg-smoke-%j.log
W=${W:-/home/fzheng4/wt-warpsync-join-gap}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
unset ACCEL_PROF_HOME
export CUVEIN_HOME=$W
S=eval/baselines/setup
R=eval/results/wjg/smoke
mkdir -p $R
export TMPDIR=/mnt/local/fzheng4-wjg-$SLURM_JOB_ID
mkdir -p $TMPDIR || export TMPDIR=/tmp
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is) TMPDIR=$TMPDIR"; git rev-parse HEAD; df -h /mnt/local | tail -1
$PY $S/wjg_scan.py list --out $R/files.jsonl --only t16-certain \
    --id-glob 'P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp*'
$PY $S/wjg_scan.py scan --files $R/files.jsonl --out $R/scan.jsonl --procs 8
$PY $S/wjg_census.py run --scan $R/scan.jsonl --out $R/census.jsonl --slots 4 --mem-gb 30
$PY $S/wjg_census.py run --scan $R/scan.jsonl --out $R/validate.jsonl --slots 4 --mem-gb 30 --select validate
rm -rf /mnt/local/fzheng4-wjg-$SLURM_JOB_ID
echo "done $(date -Is)"
