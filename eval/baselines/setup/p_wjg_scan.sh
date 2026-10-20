#!/bin/bash
# WARPSYNC join gap, phase 1 (wjg_scan.py): STEP=list enumerates the kept stores' kernel JSONs;
# STEP=scan byte-scans them with PROCS processes on one node; any number of scan jobs share one
# queue through the claims directory (CLAIMS, on BeeGFS), so jobs that start late take the rest.
# BeeGFS reads at ~120 MB/s per node here (1 GbE), so the scan is spread over nodes.
#   STEP=list sbatch eval/baselines/setup/p_wjg_scan.sh
#   for i in 1 2 3 4 5 6 7 8; do STEP=scan sbatch eval/baselines/setup/p_wjg_scan.sh; done
#SBATCH -p normal
#SBATCH -J wjg-scan
#SBATCH -t 1-00:00:00
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -o /home/fzheng4/wt-warpsync-join-gap/eval/x_logs/wjg-scan-%j.log
W=${W:-/home/fzheng4/wt-warpsync-join-gap}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
unset ACCEL_PROF_HOME
export CUVEIN_HOME=$W
S=eval/baselines/setup
R=eval/results/wjg
echo "node $(hostname) job ${SLURM_JOB_ID} step ${STEP} shard ${SHARD} $(date -Is)"; git rev-parse HEAD
case "$STEP" in
  list) $PY $S/wjg_scan.py list --out $R/files.jsonl ;;
  scan) $PY $S/wjg_scan.py scan --files $R/files.jsonl --out $R/scan_${SLURM_JOB_ID}.jsonl \
            --claims "${CLAIMS:-/mnt/beegfs/fzheng4/wjg_claims}" --done-glob "$R/scan_*.jsonl" \
            --procs "${PROCS:-16}" ;;
  *) echo "STEP must be list or scan"; exit 2 ;;
esac
echo "done $(date -Is)"
