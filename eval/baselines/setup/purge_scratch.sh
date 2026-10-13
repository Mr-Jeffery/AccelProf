#!/usr/bin/env bash
# Purge orphaned cuVein trace dumps from node-local scratch.
#
# parallel.py `run` deletes each program's trace right after analysis, but shards
# that SLURM cancelled/timed out were SIGKILLed before their `finally: rmtree`, so
# raw multi-GB dumps were left under /mnt/local/$USER/cvtraces on every GPU node
# used (22 GB observed on c1). Those dumps belong to TP/TN/FP/FN programs alike and
# carry no verdict; the verdict rows live in eval/results/*.csv (never deleted).
# FP/FN traces are re-collected deliberately by parallel.py --keep-mismatch.
#
# One tiny sbatch per node (so a busy node just queues instead of blocking).
#   bash eval/baselines/setup/purge_scratch.sh            # nodes from CSV notes
#   bash eval/baselines/setup/purge_scratch.sh c1 c2      # explicit nodes
set -u
REPO=/home/fzheng4/AccelProf
LOGD=$REPO/eval/baselines/setup/build_logs; mkdir -p "$LOGD"
LOG=$REPO/eval/baselines/setup/purge.log
if [ $# -gt 0 ]; then
  NODES="$*"
else
  NODES=$( (cut -d, -f17 "$REPO"/eval/results/baselines-cuvein*.csv 2>/dev/null | grep -o "node=c[0-9]*" | sed 's/node=//'; echo c48) | sort -u -V | tr '\n' ' ')
fi
echo "purge_scratch $(date -Is) nodes: $NODES" | tee -a "$LOG"
for n in $NODES; do
  part=$(sinfo -N -h -n "$n" -o "%P" | tr -d '*' | grep -E "rtx|a[0-9]|p4000|h100" | head -1)
  [ -z "$part" ] && part=$(sinfo -N -h -n "$n" -o "%P" | tr -d '*' | head -1)
  jid=$(sbatch --parsable -p "$part" -w "$n" -N1 -n1 -t 00:10:00 -J purge-$n \
        -o "$LOGD/purge-$n.log" --wrap "set -x; hostname; du -sh /mnt/local/\$USER 2>/dev/null; \
        rm -rf /mnt/local/\$USER/cvtraces /mnt/local/\$USER/cuvein_traces; du -sh /mnt/local/\$USER 2>/dev/null; \
        echo PURGE-DONE") || { echo "  $n: sbatch failed (partition=$part)" | tee -a "$LOG"; continue; }
  echo "  $n -> job $jid (partition=$part)" | tee -a "$LOG"
done
