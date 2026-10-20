#!/usr/bin/env bash
#SBATCH --job-name=t23-summary
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-summary-%j.log
# T23 (eval/R3_CLOSURE.md): the counts of every scan and diff directory, for the report.
W=${W:-/home/fzheng4/wt-t23}
cd "$W" || exit 1
T="$W/.env/bin/python eval/baselines/setup/t23_closure.py"
echo "head=$(git rev-parse HEAD) date=$(date -Is)"
for d in eval/results/t23/scan/*/; do
  echo "== scan $(basename "$d"): $(ls "$d"/shard*.jsonl | wc -l) shard file(s)"
  $T scan-summary "$d"shard*.jsonl
  echo "   scan errors: $(cat "$d"shard*.jsonl | grep -c '"status": "error"')"
done
for d in eval/results/t23/diff/*/; do
  echo "== diff $(basename "$d"): $(ls "$d"/shard*.jsonl | wc -l) shard file(s)"
  $T summary "$d"shard*.jsonl
done
echo "== branch heads: final-sweep $(git -C /home/fzheng4/AccelProf rev-parse eval/final-sweep) final-certain $(git -C /home/fzheng4/AccelProf rev-parse eval/final-certain) cuVein $(git -C /home/fzheng4/AccelProf rev-parse cuVein)"
