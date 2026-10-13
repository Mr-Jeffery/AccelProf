#!/usr/bin/env bash
#SBATCH --job-name=t1a-oldstore
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=02:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t1a-oldstore-%j.log
# T1a (eval/CP_ASYNC_REPORT.md): a pre-T1a trace store -- no hb_async marker, no
# pipeline_commit / pipeline_wait records -- re-scored from the same dumps by the merged
# detector (the main checkout) and by the T1a detector, for the T1a evaluation ids. The
# async-agent model applies only to marked dumps, so every (id, mode) row must agree.
# CPU only (BeeGFS is mounted on every compute node). The evcand store holds all 59 ids;
# full-2026-09-22 only 6 of them.
#   sbatch eval/baselines/setup/t1a_oldstore.sh          (TAG=evcand: the store with every id)
set -u
W=/home/fzheng4/wt-T1a; A=/home/fzheng4/AccelProf; TAG=${TAG:-full-2026-09-22}
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
export BASELINE_MODES=vector-clock,scalar-clock
echo "host=$(hostname) store=$BASELINE_TRACE_DIR"
for side in head t1a; do
  CV=$A; [ $side = t1a ] && CV=$W
  OUT=$W/eval/results/t1a-oldstore-$TAG-$side
  rm -rf $OUT $W/eval/baselines/confirm_t1a-oldstore-$TAG-$side
  ( cd $CV && export ACCEL_PROF_HOME=$CV && source eval/baselines/gpu_env.sh && \
    echo "== $side: $CV at $(git -C $CV rev-parse --short HEAD), python/ diff $(git -C $CV diff HEAD -- python | sha256sum | cut -c1-12)" && \
    $PY eval/baselines/parallel.py analyze --manifest eval/baselines/manifest.csv \
        --id-file $W/eval/baselines/setup/t1a_eval_ids.txt --shard 0/1 --confirm \
        --tag t1a-oldstore-$TAG-$side --results-dir $OUT \
        --confirm-dir $W/eval/baselines/confirm_t1a-oldstore-$TAG-$side 2>&1 | tail -1 )
done
cd $W && ACCEL_PROF_HOME=$W source eval/baselines/gpu_env.sh
TAG=$TAG $PY - <<'PY'
import csv, glob, os
def rows(side):
    out = {}
    for f in glob.glob(f"eval/results/t1a-oldstore-{os.environ['TAG']}-{side}/*.csv"):
        for r in csv.DictReader(open(f)):
            out[(r["id"], r["mode"], r["rep"])] = (r["verdict"], r["report_ids"])
    return out
h, t = rows("head"), rows("t1a")
diff = [k for k in sorted(set(h) | set(t)) if h.get(k) != t.get(k)]
for k in diff:
    print("DIFF", k, h.get(k), "->", t.get(k))
print(f"{len(h)} head rows, {len(t)} T1a rows, {len(diff)} differ;",
      "verdicts:", dict(sorted(__import__("collections").Counter(v for v, _ in t.values()).items())))
PY
echo "== done $(date -Is)"
