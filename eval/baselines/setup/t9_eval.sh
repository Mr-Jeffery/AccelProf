#!/usr/bin/env bash
#SBATCH --job-name=t9-eval
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t9-eval-%j.log
# T9 step 6 (CLAUDE.md section C): one GPU sweep of P5 (the 33 ScoR litmus + canary) and E2
# (the P6 memcpy/* and intersubwarp/* programs; its asyncmemcpy/* four are out of scope and
# not re-run) in both modes, with the main runtime (pre-T9: the 3331d35 build) and the T9
# worktree runtime on the same node, one rep each; then every (id, mode) whose verdict or
# report ids differ between the two, with the T9 row's report classes.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_eval.sh
set -u
W=/home/fzheng4/wt-T9; A=/home/fzheng4/AccelProf
IDS=$W/eval/baselines/setup/t9_eval_ids.txt
for which in main t9; do
  R=$A; [ $which = t9 ] && R=$W
  TAG=t9-eval-$which
  (
    cd $R || exit 1
    export ACCEL_PROF_HOME=$R
    source $W/eval/baselines/gpu_env.sh
    export PATH=/usr/local/cuda-13.3/bin:$PATH
    [ -n "${PIN8G:-}" ] && source $W/eval/baselines/setup/pin8g.sh
    echo "== $which: host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader) collector $(sha256sum $R/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $R/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')"
    rm -rf /mnt/beegfs/$USER/cuvein_traces/$TAG $W/eval/results/$TAG $W/eval/baselines/confirm_$TAG
    BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG $W/.env/bin/python $R/eval/baselines/parallel.py run \
        --manifest $W/eval/baselines/manifest.csv --id-file $IDS \
        --reps 1 --confirm --tag $TAG --results-dir $W/eval/results/$TAG \
        --confirm-dir $W/eval/baselines/confirm_$TAG 2>&1 | tail -3
  )
done
cd $W
.env/bin/python - <<'PY'
import csv, glob, sys
sys.path.insert(0, "eval/baselines")
import make_tables as mt
man = {r["id"]: r for r in csv.DictReader(open("eval/baselines/manifest.csv"))}
def load(tag):
    out = {}
    for p in glob.glob(f"eval/results/{tag}/baselines-cuvein-shard*.csv"):
        for r in csv.DictReader(open(p)):
            out[(r["id"], r["mode"])] = r
    return out
b, a = load("t9-eval-main"), load("t9-eval-t9")
chg = 0
for k in sorted(set(a) | set(b)):
    rb, ra = b.get(k, {}), a.get(k, {})
    vb, va = rb.get("verdict", "-"), ra.get("verdict", "-")
    lab = man.get(k[0], {}).get("label", "")
    ra1 = mt.race_alone_verdict({"verdict": va, "notes": ra.get("notes", "")}) if ra else None
    same = vb == va and rb.get("report_ids") == ra.get("report_ids")
    chg += not same
    print(f"{'CHANGED' if not same else 'same   '} {k[0]:55} {k[1]:13} label={lab:5} {vb:7} -> {va:7} "
          f"race-alone={ra1} {mt.report_classes(ra) if ra else None}"
          + ("" if same else f"  ids: {rb.get('report_ids', '')[:100]} -> {ra.get('report_ids', '')[:100]}"))
print(f"{len(set(a) | set(b))} (id, mode) rows; {chg} differ between the main and the T9 runtime")
PY
echo "== done $(date -Is)"
