#!/usr/bin/env bash
#SBATCH --job-name=review-rescore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=02:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/review-rescore-%j.log
# T1a review (eval/CP_ASYNC_REPORT.md §6): CPU re-score with the review worktree's detector of
#  (1) the T1a evaluation store t1a-p56 (marked dumps, P5 + P6, both modes) against the rows
#      the T1a detector gave on the same dumps (eval/results/t1a-p56): the verdict deltas
#      of the review fixes on the corpus;
#  (2) the pre-T1a store evcand (unmarked dumps) against the merged detector's re-score
#      (eval/results/t1a-oldstore-evcand-head): must be 0 differences.
# The review's engine change (two copies of one thread) is not in these dumps' hb_races;
# no kept program has such a pair (only the six P6 memcpy programs contain LDGSTS).
#   sbatch eval/baselines/setup/review_rescore.sh
set -u
W=${W:-/home/fzheng4/wt-T1a-review}
cd $W && export ACCEL_PROF_HOME=$W && source eval/baselines/gpu_env.sh
export BASELINE_MODES=vector-clock,scalar-clock
echo "host=$(hostname) $W at $(git rev-parse --short HEAD), python/ diff $(git diff HEAD -- python | sha256sum | cut -c1-12)"
for TAG in t1a-p56 evcand; do
  OUT=$W/eval/results/review-rescore-$TAG; rm -rf $OUT $W/eval/baselines/confirm_review-rescore-$TAG
  BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG $PY eval/baselines/parallel.py analyze \
      --manifest eval/baselines/manifest.csv --id-file eval/baselines/setup/t1a_eval_ids.txt \
      --shard 0/1 --confirm --tag review-rescore-$TAG --results-dir $OUT \
      --confirm-dir $W/eval/baselines/confirm_review-rescore-$TAG 2>&1 | tail -1
done
$PY - <<'PY'
import csv, glob
def rows(pattern, rep1=False):
    out = {}
    for f in glob.glob(pattern):
        for r in csv.DictReader(open(f)):
            if rep1 and r["rep"] != "1":
                continue
            out[(r["id"], r["mode"], r["rep"])] = (r["verdict"], r["report_ids"])
    return out
for name, before, after in [
        ("t1a-p56: T1a detector -> review", "/home/fzheng4/AccelProf/eval/results/t1a-p56/*.csv",
         "eval/results/review-rescore-t1a-p56/*.csv"),
        ("evcand: merged detector -> review", "/home/fzheng4/AccelProf/eval/results/t1a-oldstore-evcand-head/*.csv",
         "eval/results/review-rescore-evcand/*.csv")]:
    b, a = rows(before), rows(after)
    diff = [k for k in sorted(set(b) | set(a)) if b.get(k) != a.get(k)]
    print(f"== {name}: {len(b)} -> {len(a)} rows, {len(diff)} differ")
    for k in diff:
        print("   DIFF", k, b.get(k), "->", a.get(k))
PY
echo "== done $(date -Is)"
