#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 05:30:00
#SBATCH -J x15-sc
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-x15/eval/results/x15/x15-sc-%j.log
# X15: colmap-new-1-buggy scalar-clock: attribution (T21c's rw_attribute as C6 had it, RW_MODES=scalar-clock, timeout 14400 s) and rw_score.
# The scalar-clock verdict is not re-run: the existing T21c per-id CSV row is used.
. /home/fzheng4/wt-x15/eval/baselines/setup/x15_common.sh
cd $W || exit 1
D=$OUT/sc; mkdir -p $D/attrib
echo "host=$(hostname) job=$SLURM_JOB_ID nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) cuda=$CUDA_HOME start=$(date -Is)"
lscpu | grep -E "Model name|^Socket|^Core|^Thread"
STORE=$B/realworld-2026-10-t21c
ls -l $STORE/$ID | head; du -sh $STORE/$ID 2>/dev/null
cp /home/fzheng4/wt-t21c/eval/results/realworld_t21c/baselines-cuvein-shard$ID-all.csv $D/ || echo "CSV copy failed"
export RW_MODES=scalar-clock
KD=$(ls -d $STORE/$ID/scalar-clock* 2>/dev/null | head -1); echo "kernel jsons ($KD):"; ls -l $KD/kernel_*.json 2>/dev/null
mkdir -p /tmp/x15sc; export TMPDIR=/tmp/x15sc
echo "== attribution start $(date -Is)"
ta0=$(date +%s)
timeout -s TERM 14400 $PY $SU/x15_launch.py $HD/rw_attribute_sc.py --id $ID --store $STORE --manifest $HX/eval/realworld/manifest_t21c.csv --out $D/attrib/$ID.json > $D/attrib.log 2>&1
arc=$?; ta1=$(date +%s)
echo "== attribution rc=$arc wall_s=$((ta1-ta0)) end $(date -Is)"; tail -3 $D/attrib.log
echo "attrib_rc=$arc attrib_wall_s=$((ta1-ta0))" > $D/attrib_wall.txt
if [ $arc -eq 0 ] && [ -s $D/attrib/$ID.json ]; then
  $PY $HD/rw_score.py --results $D --manifest $HX/eval/realworld/manifest_t21c.csv --pairs $HX/eval/realworld/recall_pairs.json --write > $D/score.out 2>&1; echo "score rc=$?"; tail -20 $D/score.out
fi
rm -rf /tmp/x15sc
echo "end $(date -Is)"
