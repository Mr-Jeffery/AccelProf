#!/bin/bash
# WARPSYNC join gap, phase 2 (wjg_census.py run): the census and merged replay of every kernel JSON
# the scan found with a partial syncwarp record, in one size class per job:
#   MINMB=0 MAXMB=500 SLOTS=16 MEMGB=10 TAG=a sbatch eval/baselines/setup/p_wjg_census.sh
# SELECT=validate re-reads files with syncwarp records but no partial one (count check only).
# SHARD=i/n takes every n-th file of the class; STAGE=1 copies the class's large dumps to local
# disk before the first census (BeeGFS is shared and slow, ~500 MB/s in total).
#SBATCH -p normal
#SBATCH -J wjg-census
#SBATCH -t 1-00:00:00
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -o /home/fzheng4/wt-warpsync-join-gap/eval/x_logs/wjg-census-%j.log
W=${W:-/home/fzheng4/wt-warpsync-join-gap}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
# after the 10-18 restart some nodes lack /home or BeeGFS: fail at once, naming the node
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  [ -d "$d" ] || { echo "PREFLIGHT FAIL $(hostname): $d missing"; exit 3; }
done
cd "$W" || exit 1
unset ACCEL_PROF_HOME
export CUVEIN_HOME=$W
S=eval/baselines/setup
R=${R:-eval/results/wjg}
SELECT=${SELECT:-partial}
PFX=$([ "$SELECT" = validate ] && echo validate || echo census)
if [ "${MEMGB:-auto}" = auto ]; then          # one child at a time: the node's RAM less 16 GB
  MEMGB=$(( $(free -g | awk '/^Mem:/{print $2}') - 16 ))
fi
export TMPDIR=/mnt/local/fzheng4-wjg-$SLURM_JOB_ID
mkdir -p "$TMPDIR" 2>/dev/null || { export TMPDIR=/mnt/beegfs/fzheng4/wjg_tmp/$SLURM_JOB_ID; mkdir -p "$TMPDIR"; }
trap 'rm -rf "$TMPDIR"' EXIT TERM
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is) select=$SELECT ${MINMB}-${MAXMB} MB" \
     "slots=$SLOTS mem=${MEMGB}G timeout=${TIMEOUT:-21600} TMPDIR=$TMPDIR"
git rev-parse HEAD; df -h /mnt/local | tail -1; free -g | head -2
cat $R/scan_*.jsonl > $TMPDIR/scan_all.jsonl
$PY $S/wjg_census.py run --scan $TMPDIR/scan_all.jsonl --out $R/${PFX}_${TAG}.jsonl --select "$SELECT" \
    --min-mb "${MINMB:-0}" --max-mb "${MAXMB:-1e12}" --slots "${SLOTS:-8}" --mem-gb "${MEMGB:-20}" \
    --timeout "${TIMEOUT:-21600}" --tmpdir "$TMPDIR" --shard "${SHARD:-0/1}" ${STAGE:+--stage-all} ${CHECK:+--check-stream} ${MATCH:+--match "$MATCH"} ${NOORACLE:+--no-oracle} ${REDO:+--done-glob "$R/census_*.jsonl"} ${LENIENT:+--tv-lenient}
rm -rf "$TMPDIR"
echo "done $(date -Is)"
